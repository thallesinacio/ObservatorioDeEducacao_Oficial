"""Orquestração: migrar, coletar, transformar, calcular indicadores, testar qualidade.

Regras de robustez:
* cada fonte roda na sua própria execução (etl.etl_execucao); a falha de uma não derruba as outras;
* cada arquivo é processado em transação própria; a carga no core também;
* mesma entrada = mesma versão (etl.versao_dados): rodar duas vezes não duplica nada;
* no fim, um resumo e código de saída diferente de zero se alguma fonte falhou.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

import psycopg

from observatorio import config
from observatorio.coleta import ORDEM_PIPELINE, registro
from observatorio.coleta.base import Contexto, Fonte
from observatorio.db import (
    aplicar_migracoes,
    conectar,
    configurar_papel_leitor,
    recriar_views_bi,
)
from observatorio.execucao import (
    ArquivoRegistrado,
    Execucao,
    arquivos_vigentes,
    caminho_absoluto,
    marcar_processado,
    obter_versao,
    registrar_arquivo,
    tornar_vigente,
)
from observatorio.http import registrar_arquivo_local
from observatorio.log import obter_logger

log = obter_logger(__name__)


@dataclass
class Resumo:
    sucesso: list[str] = field(default_factory=list)
    falha: dict[str, str] = field(default_factory=dict)
    alertas: dict[str, list[str]] = field(default_factory=dict)

    @property
    def codigo_saida(self) -> int:
        return 1 if self.falha else 0

    def texto(self) -> str:
        linhas = ["", "===== Resumo ====="]
        for f in self.sucesso:
            extra = f" ({len(self.alertas.get(f, []))} alerta(s))" if self.alertas.get(f) else ""
            linhas.append(f"  OK     {f}{extra}")
        for f, erro in self.falha.items():
            linhas.append(f"  FALHA  {f}: {erro.splitlines()[0][:160]}")
        return "\n".join(linhas)


# ------------------------------------------------------------------ banco

def migrar(offline: bool = False) -> dict:
    from observatorio.carga.dimensoes import carregar_referencias

    with conectar() as conn:
        aplicadas = aplicar_migracoes(conn)
        refs = carregar_referencias(conn, offline=offline)
        configurar_papel_leitor(conn, config.configuracoes().powerbi_senha)
        n_views = recriar_views_bi(conn)
    return {"migrations_aplicadas": aplicadas, "referencias": refs, "views_bi": n_views}


# ------------------------------------------------------------------ por fonte

def _selecionar(fontes: list[str] | None) -> list[Fonte]:
    reg = registro()
    ids = fontes or ORDEM_PIPELINE
    desconhecidas = [f for f in ids if f not in reg]
    if desconhecidas:
        raise KeyError(f"Fonte(s) desconhecida(s): {', '.join(desconhecidas)}. Use 'fontes listar'.")
    return [reg[f] for f in ids]


def coletar_fonte(fonte: Fonte, anos: list[int] | None, ano_inicial: int, forcar: bool) -> list[ArquivoRegistrado]:
    parametros = f"anos={anos or f'{ano_inicial}+'}; forcar={forcar}"
    with Execucao("coletar", fonte.id_fonte, parametros) as ex, conectar() as conn:
        ctx = Contexto(ex, anos, ano_inicial, forcar)
        arquivos = fonte.coletar(conn, ctx)
        conn.commit()
        if not arquivos:
            ex.alertar(f"{fonte.id_fonte}: nenhum arquivo coletado para os anos pedidos")
        return arquivos


def _arquivos_a_processar(conn: psycopg.Connection, fonte: Fonte, forcar: bool) -> list[ArquivoRegistrado]:
    with conn.cursor() as cur:
        if forcar:
            vigentes = {r[0] for r in arquivos_vigentes(conn, fonte.id_fonte)}
            cur.execute(
                """SELECT id_arquivo FROM etl.etl_arquivo a WHERE id_fonte = %s AND NOT arquivo_removido
                     AND (processado_em IS NULL OR id_arquivo = ANY(%s))""",
                (fonte.id_fonte, list(vigentes)),
            )
        else:
            cur.execute(
                """SELECT id_arquivo FROM etl.etl_arquivo WHERE id_fonte = %s AND processado_em IS NULL
                     AND NOT arquivo_removido""",
                (fonte.id_fonte,),
            )
        ids = [r[0] for r in cur.fetchall()]
        if not ids:
            return []
        cur.execute(
            """SELECT id_arquivo, id_fonte, ano_referencia, url, caminho_local, sha256, data_coleta, versao_layout, descricao
               FROM etl.etl_arquivo WHERE id_arquivo = ANY(%s) ORDER BY ano_referencia NULLS FIRST, id_arquivo""",
            (ids,),
        )
        saida = []
        for id_arq, id_f, ano, url, caminho, sha, data, layout, desc in cur.fetchall():
            saida.append(ArquivoRegistrado(id_arq, id_f, ano, url, caminho_absoluto(caminho), sha, data,
                                           False, layout, desc))
        return saida


def transformar_fonte(fonte: Fonte, forcar: bool = False) -> dict:
    """Processa os arquivos pendentes (raw + staging) e carrega o core numa versão."""
    with Execucao("transformar", fonte.id_fonte, f"forcar={forcar}") as ex:
        ctx = Contexto(ex, forcar=forcar)
        processados = 0
        with conectar() as conn:
            for arq in _arquivos_a_processar(conn, fonte, forcar):
                if not arq.caminho.exists():
                    ex.alertar(f"Arquivo do manifesto não está no disco: {arq.caminho} (rode coletar)")
                    continue
                try:
                    fonte.processar(conn, arq, ctx)
                    marcar_processado(conn, arq.id_arquivo, arq.versao_layout)
                    conn.commit()
                    processados += 1
                except Exception:
                    conn.rollback()
                    raise
                apos = getattr(fonte, "apos_processar", None)
                if apos:
                    apos(conn, arq)
                    conn.commit()

            vigentes = arquivos_vigentes(conn, fonte.id_fonte)
            if not vigentes:
                ex.ignorar("Nenhum arquivo processado para esta fonte")
                return {"processados": 0, "versao": None}
            partes = [f"{ano}|{url}|{sha}" for _, ano, sha, url, _ in vigentes]
            partes.append(f"transformacao={fonte.versao_transformacao}")
            id_versao, nova = obter_versao(conn, fonte.id_fonte, partes,
                                           f"{len(vigentes)} arquivo(s); transformação {fonte.versao_transformacao}",
                                           ex.id_execucao)
            if not nova and not forcar and processados == 0:
                conn.rollback()
                tornar_vigente(conn, fonte.id_fonte, id_versao)
                conn.commit()
                ex.ignorar(f"Sem mudança nas entradas: versão {id_versao} mantida")
                return {"processados": 0, "versao": id_versao, "nova": False}
            try:
                with conn.cursor() as cur:
                    for tabela in fonte.tabelas_core:
                        cur.execute(f"DELETE FROM {tabela} WHERE id_versao = %s", (id_versao,))
                linhas = fonte.carregar_core(conn, id_versao, ctx)
                tornar_vigente(conn, fonte.id_fonte, id_versao)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            ex.linhas_gravadas += linhas
            return {"processados": processados, "versao": id_versao, "nova": nova, "linhas_core": linhas}


def executar_fontes(fontes: list[str] | None, anos: list[int] | None, ano_inicial: int, forcar: bool,
                    coletar: bool = True, transformar: bool = True) -> Resumo:
    resumo = Resumo()
    for fonte in _selecionar(fontes):
        try:
            if coletar:
                coletar_fonte(fonte, anos, ano_inicial, forcar)
            if transformar:
                transformar_fonte(fonte, forcar)
            resumo.sucesso.append(fonte.id_fonte)
        except Exception as e:  # uma fonte não derruba as outras
            log.error("Fonte falhou", fonte=fonte.id_fonte, erro=str(e))
            resumo.falha[fonte.id_fonte] = f"{type(e).__name__}: {e}"
    return resumo


def pipeline(fontes: list[str] | None, anos: list[int] | None, ano_inicial: int, forcar: bool = False) -> Resumo:
    from observatorio.indicadores.calcular import calcular_indicadores
    from observatorio.qualidade.testes import executar_testes

    resumo = executar_fontes(fontes, anos, ano_inicial, forcar)
    try:
        calcular_indicadores(forcar=forcar)
        resumo.sucesso.append("indicadores")
    except Exception as e:
        log.error("Cálculo de indicadores falhou", erro=str(e))
        resumo.falha["indicadores"] = f"{type(e).__name__}: {e}"
    try:
        r = executar_testes()
        resumo.sucesso.append("qualidade")
        if r.get("erros"):
            resumo.alertas.setdefault("qualidade", []).append(f"{r['erros']} teste(s) com erro")
    except Exception as e:
        resumo.falha["qualidade"] = f"{type(e).__name__}: {e}"
    return resumo


# ------------------------------------------------------------------ arquivo baixado à mão

def importar_arquivo(id_fonte: str, arquivo: Path, ano: int | None, url: str, descricao: str | None = None) -> int:
    """Registra no manifesto um arquivo obtido fora do coletor (ex.: baixado no navegador quando o site
    bloqueia a coleta automática, ou uma fixture de teste). O arquivo é copiado para
    data/raw/<fonte>/<ano>/ e fica pendente para o próximo ``transformar``. Devolve o id_arquivo."""
    fonte = registro()[id_fonte]
    destino = fonte.pasta_ano(ano) / arquivo.name
    destino.parent.mkdir(parents=True, exist_ok=True)
    if arquivo.resolve() != destino.resolve():
        shutil.copyfile(arquivo, destino)
    with Execucao("importar", id_fonte, f"arquivo={arquivo.name}") as ex, conectar() as conn:
        reg = registrar_arquivo(conn, id_fonte, ano, registrar_arquivo_local(url, destino),
                                id_execucao=ex.id_execucao, descricao=descricao)
        if reg.ja_processado:
            ex.alertar(f"{arquivo.name} já tinha sido importado e processado (mesmo sha256 e URL)")
        return reg.id_arquivo
