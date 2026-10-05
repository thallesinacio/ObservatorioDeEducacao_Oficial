"""Microdados do Censo Escolar (INEP).

Os ZIPs anuais têm de 26 MB (2015) a 537 MB (2025). O CSV nacional é lido em blocos, filtrando
os municípios de interesse já na leitura; só o recorte vai para o banco. O layout de cada ano
(nomes de arquivo e colunas) está em config/layouts/censo_escolar.yaml e é conferido contra o
cabeçalho real: faltou coluna obrigatória, o coletor para com mensagem clara.
"""

from __future__ import annotations

import re
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import psycopg
from bs4 import BeautifulSoup

from observatorio import config
from observatorio.carga.dimensoes import garantir_recortes
from observatorio.coleta.base import Contexto, Fonte, gravar_raw
from observatorio.db import copiar_linhas
from observatorio.execucao import ArquivoRegistrado, marcar_removido
from observatorio.http import obter_texto
from observatorio.log import obter_logger
from observatorio.transformacao.leitores import (
    ErroLeitura,
    abas_xlsx,
    cabecalho_csv,
    extrair_membro,
    ler_csv_em_blocos,
    ler_xlsx,
    membro_zip,
)
from observatorio.transformacao.normalizacao import (
    codigo_escola,
    codigo_municipio,
    inteiro,
    normalizar_rotulo,
    texto_limpo,
)

log = obter_logger(__name__)

_RX_LINK = re.compile(r"microdados_censo_escolar_(\d{4})_?\.zip$", re.IGNORECASE)


def layouts() -> dict:
    return config.carregar_yaml("layouts/censo_escolar.yaml")


def mapa_variaveis() -> dict:
    return config.carregar_yaml("layouts/censo_escolar_variaveis.yaml")


def escolher_layout(ano: int, nomes_no_zip: list[str] | None = None) -> tuple[str, dict]:
    cfg = layouts()["layouts"]
    for nome, lay in cfg.items():
        if ano in lay["anos"]:
            return nome, lay
    # Ano novo, ainda não configurado: tenta o layout mais recente cujos arquivos existam no ZIP.
    if nomes_no_zip is not None:
        for nome in reversed(list(cfg)):
            lay = cfg[nome]
            if all(any(re.search(p, n, re.IGNORECASE) for n in nomes_no_zip) for p in lay["tabelas"].values()):
                log.warning("Ano sem layout configurado; usando o layout compatível mais recente", ano=ano, layout=nome)
                return nome, lay
    raise ErroLeitura(
        f"Ano {ano} sem layout em config/layouts/censo_escolar.yaml e nenhum layout conhecido é compatível "
        "com os arquivos do ZIP. Leia o 'Leia-me' do INEP e acrescente o ano (ou um layout novo)."
    )


def _parse_categorias(texto: str | None) -> list[tuple[str, str]]:
    """'1 - Federal\\n2 - Estadual' -> [('1','Federal'), ('2','Estadual')]"""
    if not texto:
        return []
    pares = []
    for linha in re.split(r"[\r\n]+", str(texto)):
        m = re.match(r"^\s*(-?\d+)\s*[-–]\s*(.+?)\s*$", linha)
        if m:
            pares.append((m.group(1), m.group(2)))
    return pares


class CensoEscolar(Fonte):
    id_fonte = "censo_escolar"
    tabelas_core = ("core.fato_matricula", "core.fato_docente", "core.fato_turma")
    versao_transformacao = "2026.09.1"

    # -------------------------------------------------------------- descoberta e download

    def descobrir_links(self) -> dict[int, str]:
        f = config.fonte(self.id_fonte)
        links: dict[int, str] = {}
        try:
            html = obter_texto(f["pagina_oficial"])
            for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
                m = _RX_LINK.search(a["href"])
                if m:
                    links.setdefault(int(m.group(1)), a["href"])
        except Exception as e:
            log.warning("Não foi possível ler a página do Censo Escolar; usando o padrão de URL", erro=str(e))
        return links

    def coletar(self, conn: psycopg.Connection, ctx: Contexto) -> list[ArquivoRegistrado]:
        links = self.descobrir_links()
        padrao = config.fonte(self.id_fonte)["padrao_url"]
        anos = sorted(a for a in (links or {}) if ctx.ano_desejado(a))
        if not links:
            anos = sorted(ctx.anos or [])
            if not anos:
                raise RuntimeError("Página do INEP indisponível e nenhum ano informado (--ano) para usar o padrão de URL")
        registrados = []
        for ano in anos:
            url = links.get(ano) or padrao.format(ano=ano)
            nome = url.rsplit("/", 1)[-1]
            registrados.append(self.baixar_registrar(conn, ctx, url, ano, nome, descricao="ZIP de microdados"))
        return registrados

    # -------------------------------------------------------------- processamento de um ano

    def processar(self, conn: psycopg.Connection, arquivo: ArquivoRegistrado, ctx: Contexto) -> int:
        zip_path = arquivo.caminho
        ano = int(arquivo.ano)
        import zipfile
        with zipfile.ZipFile(zip_path) as z:
            nomes = [i.filename for i in z.infolist()]
        nome_layout, lay = escolher_layout(ano, nomes)
        cfg = layouts()
        municipios = set(config.municipios_de_interesse())

        # 1) Tabelas do layout: localizar, conferir colunas
        tabelas = {}
        colunas_todas: set[str] = set()
        for chave, padrao in lay["tabelas"].items():
            info = membro_zip(zip_path, padrao)
            colunas, _, _ = cabecalho_csv(zip_path, info)
            tabelas[chave] = (info, colunas)
            colunas_todas.update(colunas)
        faltando = [c for c in cfg["colunas_obrigatorias"] if c not in colunas_todas]
        if faltando:
            raise ErroLeitura(
                f"Censo Escolar {ano} (layout {nome_layout}): colunas obrigatórias ausentes: {', '.join(faltando)}. "
                "Confira o dicionário de dados do ano e ajuste config/layouts/censo_escolar.yaml."
            )

        # 2) Leitura filtrada + raw
        linhas_por_escola: dict[str, dict[str, Any]] = defaultdict(dict)
        total_raw = 0
        for chave, (info, colunas) in tabelas.items():
            registros = []
            for bloco in ler_csv_em_blocos(zip_path, info, cfg["coluna_municipio"], municipios):
                for rec in bloco.to_dict("records"):
                    num = int(rec.pop("__linha__"))
                    registros.append((num, rec))
                    co = codigo_escola(rec.get(cfg["coluna_escola"]))
                    linhas_por_escola[co].update({k: v for k, v in rec.items() if v is not None or k not in linhas_por_escola[co]})
            total_raw += gravar_raw(conn, arquivo.id_arquivo, chave, registros)
            ctx.execucao.linhas_lidas += len(registros)

        # 3) staging (substitui o ano)
        with conn.cursor() as cur:
            for t in ("staging.censo_escola", "staging.censo_contagem", "staging.censo_layout", "staging.censo_dicionario"):
                cur.execute(f"DELETE FROM {t} WHERE ano = %s", (ano,))
        mapa_escola = cfg["colunas_escola"]
        linhas_escola = []
        linhas_contagem = []
        for co, rec in linhas_por_escola.items():
            cod_mun = codigo_municipio(rec.get("CO_MUNICIPIO"))
            linha = {
                "ano": ano, "co_entidade": co, "co_municipio": cod_mun,
                "no_entidade": texto_limpo(rec.get("NO_ENTIDADE")),
                "tp_dependencia": inteiro(rec.get("TP_DEPENDENCIA")),
                "tp_localizacao": inteiro(rec.get("TP_LOCALIZACAO")),
                "tp_situacao_funcionamento": inteiro(rec.get("TP_SITUACAO_FUNCIONAMENTO")),
            }
            for col_origem, col_destino in mapa_escola.items():
                v = rec.get(col_origem)
                linha[col_destino] = texto_limpo(v) if col_destino in ("no_bairro", "co_distrito") else inteiro(v)
            linha["versao_layout"] = nome_layout
            linha["id_arquivo"] = arquivo.id_arquivo
            linhas_escola.append(linha)
            for var, v in rec.items():
                if var.startswith("QT_"):
                    linhas_contagem.append((ano, co, var, inteiro(v), arquivo.id_arquivo))
        colunas_escola = list(linhas_escola[0].keys()) if linhas_escola else []
        if linhas_escola:
            copiar_linhas(conn, "staging.censo_escola", colunas_escola, ([l[c] for c in colunas_escola] for l in linhas_escola))
        copiar_linhas(conn, "staging.censo_contagem", ["ano", "co_entidade", "variavel", "valor", "id_arquivo"], linhas_contagem)
        variaveis_layout: dict[str, str] = {}
        for chave, (_, cols) in tabelas.items():
            for c in cols:
                variaveis_layout.setdefault(c, chave)
        copiar_linhas(
            conn, "staging.censo_layout", ["ano", "versao_layout", "variavel", "tabela_origem", "id_arquivo"],
            ((ano, nome_layout, c, chave, arquivo.id_arquivo) for c, chave in variaveis_layout.items()),
        )
        # 4) dicionário de dados
        n_dic = self._carregar_dicionario(conn, zip_path, ano, arquivo.id_arquivo)
        if n_dic == 0:
            ctx.alertar(f"Censo Escolar {ano}: dicionário de dados não encontrado ou vazio no ZIP")
        gravadas = len(linhas_escola) + len(linhas_contagem)
        ctx.execucao.linhas_gravadas += gravadas
        log.info("Censo Escolar processado", ano=ano, layout=nome_layout, escolas=len(linhas_escola),
                 contagens=len(linhas_contagem), raw=total_raw)
        arquivo.versao_layout = nome_layout
        return gravadas

    def _carregar_dicionario(self, conn: psycopg.Connection, zip_path: Path, ano: int, id_arquivo: int) -> int:
        cfg = layouts()["dicionario"]
        info = membro_zip(zip_path, cfg["padrao_arquivo"], obrigatorio=False)
        if info is None:
            return 0
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            xlsx = extrair_membro(zip_path, info, Path(tmp) / "dicionario.xlsx")
            registros: dict[str, tuple] = {}
            for aba in abas_xlsx(xlsx):
                cab = None
                for linha in ler_xlsx(xlsx, aba):
                    rot = [normalizar_rotulo(v) for v in linha]
                    if cab is None:
                        if cfg["coluna_nome"] in rot:
                            cab = {n: rot.index(n) for n in (cfg["coluna_nome"], cfg["coluna_descricao"],
                                                              cfg["coluna_tipo"], cfg["coluna_categoria"]) if n in rot}
                        continue
                    nome = texto_limpo(linha[cab[cfg["coluna_nome"]]]) if cab[cfg["coluna_nome"]] < len(linha) else None
                    if not nome or not re.fullmatch(r"[A-Z][A-Z0-9_]+", nome):
                        continue

                    def pegar(chave):
                        i = cab.get(cfg[chave])
                        return linha[i] if i is not None and i < len(linha) else None
                    registros.setdefault(nome, (ano, nome, texto_limpo(pegar("coluna_descricao")),
                                                texto_limpo(pegar("coluna_tipo")), pegar("coluna_categoria"), id_arquivo))
        return copiar_linhas(conn, "staging.censo_dicionario",
                             ["ano", "variavel", "descricao", "tipo", "categorias", "id_arquivo"], registros.values())

    # -------------------------------------------------------------- core

    def carregar_core(self, conn: psycopg.Connection, id_versao: int, ctx: Contexto) -> int:
        self._atualizar_codigos_inep(conn)
        self._reconstruir_dim_escola(conn)
        mapa = mapa_variaveis()
        total = 0
        destinos = {
            "matricula": ("core.fato_matricula", "qt_matriculas"),
            "docente": ("core.fato_docente", "qt_docentes"),
            "turma": ("core.fato_turma", "qt_turmas"),
        }
        recortes_usados = {rec for grupo in mapa.values() for _, rec in grupo.values()}
        garantir_recortes(conn, recortes_usados)
        id_fonte_num = self._id_fonte_num(conn)
        with conn.cursor() as cur:
            cur.execute("CREATE TEMP TABLE tmp_mapa_censo (grupo TEXT, variavel TEXT, cod_etapa TEXT, cod_recorte TEXT) ON COMMIT DROP")
        copiar_linhas(conn, "pg_temp.tmp_mapa_censo", ["grupo", "variavel", "cod_etapa", "cod_recorte"],
                      [(g, v, e, r) for g, itens in mapa.items() for v, (e, r) in itens.items()])
        for grupo, (tabela, medida) in destinos.items():
            extra_cols = ", id_fonte" if tabela == "core.fato_docente" else ""
            extra_vals = f", {id_fonte_num}" if tabela == "core.fato_docente" else ""
            with conn.cursor() as cur:
                cur.execute(
                    f"""INSERT INTO {tabela} (ano, co_entidade, cod_territorio, cod_etapa, cod_recorte, {medida},
                                              variavel_origem, status_valor, id_versao, data_coleta{extra_cols})
                        SELECT c.ano, c.co_entidade, e.co_municipio, m.cod_etapa, m.cod_recorte, c.valor, c.variavel,
                               CASE WHEN c.valor IS NULL THEN 'sem_dado' ELSE 'observado' END, %s, a.data_coleta::date{extra_vals}
                        FROM staging.censo_contagem c
                        JOIN tmp_mapa_censo m ON m.variavel = c.variavel AND m.grupo = %s
                        JOIN staging.censo_escola e ON e.ano = c.ano AND e.co_entidade = c.co_entidade
                        JOIN etl.etl_arquivo a ON a.id_arquivo = c.id_arquivo""",
                    (id_versao, grupo),
                )
                total += cur.rowcount
        return total

    def _id_fonte_num(self, conn) -> int:
        from observatorio.carga.dimensoes import id_fonte_numerico
        return id_fonte_numerico(conn, self.id_fonte)

    def _atualizar_codigos_inep(self, conn: psycopg.Connection) -> None:
        variaveis = layouts()["dicionario"]["variaveis_decodificadas"]
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT ON (variavel) variavel, categorias, ano FROM staging.censo_dicionario
                   WHERE variavel = ANY(%s) AND categorias IS NOT NULL ORDER BY variavel, ano DESC""",
                (variaveis,),
            )
            for variavel, categorias, ano in cur.fetchall():
                for codigo, rotulo in _parse_categorias(categorias):
                    cur.execute(
                        """INSERT INTO core.dim_codigo_inep (variavel, codigo, rotulo, ano_dicionario) VALUES (%s, %s, %s, %s)
                           ON CONFLICT (variavel, codigo) DO UPDATE SET rotulo = EXCLUDED.rotulo, ano_dicionario = EXCLUDED.ano_dicionario
                           WHERE core.dim_codigo_inep.ano_dicionario <= EXCLUDED.ano_dicionario""",
                        (variavel, codigo, rotulo, ano),
                    )

    def _reconstruir_dim_escola(self, conn: psycopg.Connection) -> None:
        """Dimensão de mudança lenta (tipo 2): agrupa anos consecutivos com os mesmos atributos."""
        with conn.cursor() as cur:
            cur.execute("DELETE FROM core.dim_escola")
            cur.execute(
                """
                WITH base AS (
                  SELECT e.*, md5(concat_ws('|', e.no_entidade, e.co_municipio, e.tp_dependencia,
                           e.tp_categoria_escola_privada, e.tp_localizacao, e.tp_localizacao_diferenciada,
                           e.tp_situacao_funcionamento, e.co_distrito)) AS h
                  FROM staging.censo_escola e
                ), marcado AS (
                  SELECT *, CASE WHEN h IS DISTINCT FROM lag(h) OVER (PARTITION BY co_entidade ORDER BY ano)
                                 THEN 1 ELSE 0 END AS novo
                  FROM base
                ), grupos AS (
                  SELECT *, sum(novo) OVER (PARTITION BY co_entidade ORDER BY ano) AS g FROM marcado
                ), ilhas AS (
                  SELECT co_entidade, g, min(ano) AS de, max(ano) AS ate,
                         (array_agg(no_entidade ORDER BY ano DESC))[1] AS no_entidade,
                         (array_agg(co_municipio ORDER BY ano DESC))[1] AS co_municipio,
                         (array_agg(tp_dependencia ORDER BY ano DESC))[1] AS tp_dependencia,
                         (array_agg(tp_categoria_escola_privada ORDER BY ano DESC))[1] AS tp_categoria_escola_privada,
                         (array_agg(tp_localizacao ORDER BY ano DESC))[1] AS tp_localizacao,
                         (array_agg(tp_localizacao_diferenciada ORDER BY ano DESC))[1] AS tp_localizacao_diferenciada,
                         (array_agg(tp_situacao_funcionamento ORDER BY ano DESC))[1] AS tp_situacao_funcionamento,
                         (array_agg(no_bairro ORDER BY (no_bairro IS NULL), ano DESC))[1] AS no_bairro,
                         (array_agg(co_distrito ORDER BY ano DESC))[1] AS co_distrito,
                         (array_agg(h ORDER BY ano DESC))[1] AS h
                  FROM grupos GROUP BY co_entidade, g
                ), ultimo AS (
                  SELECT co_entidade, max(ano) AS ultimo_ano FROM staging.censo_escola GROUP BY co_entidade
                ), maior_ano AS (SELECT max(ano) AS a FROM staging.censo_escola)
                INSERT INTO core.dim_escola (co_entidade, valid_from, valid_to, eh_vigente, no_entidade, cod_territorio,
                    tp_dependencia, tp_categoria_escola_privada, tp_localizacao, tp_localizacao_diferenciada,
                    tp_situacao_funcionamento, no_bairro, co_distrito, ultimo_ano_censo, hash_atributos)
                SELECT i.co_entidade, i.de,
                       CASE WHEN i.ate = u.ultimo_ano AND u.ultimo_ano = (SELECT a FROM maior_ano) THEN NULL ELSE i.ate END,
                       i.ate = u.ultimo_ano, i.no_entidade, i.co_municipio, i.tp_dependencia, i.tp_categoria_escola_privada,
                       i.tp_localizacao, i.tp_localizacao_diferenciada, i.tp_situacao_funcionamento, i.no_bairro,
                       i.co_distrito, u.ultimo_ano, i.h
                FROM ilhas i JOIN ultimo u USING (co_entidade)
                """
            )

    def apos_processar(self, conn: psycopg.Connection, arquivo: ArquivoRegistrado) -> None:
        if not config.configuracoes().manter_zip_bruto and arquivo.caminho.exists():
            arquivo.caminho.unlink()
            marcar_removido(conn, arquivo.id_arquivo)
            log.info("ZIP bruto apagado após o processamento (manter_zip_bruto = false)", arquivo=str(arquivo.caminho))
