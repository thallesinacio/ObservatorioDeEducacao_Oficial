"""Sinopse Estatística da Educação Básica (INEP).

Um ZIP por ano com uma planilha XLSX grande (uma aba por tabela, uma linha por município). Usamos:

* matrículas por etapa de ensino (tabela 1.1 em 2024): conferência dos totais dos microdados;
* docentes por nível de escolaridade e formação acadêmica (tabela 2.4 em 2024): E3 e conferência.

A Sinopse conta o DOCENTE ÚNICO no município (quem dá aula em duas escolas conta uma vez), o que os
microdados por escola não permitem. As categorias de pós-graduação NÃO são exclusivas (um docente
com especialização e mestrado aparece nas duas colunas; nota de rodapé da própria tabela).

As tabelas são achadas pelo título (config/sinopse.yaml), porque a numeração muda entre anos.
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import psycopg
from bs4 import BeautifulSoup

from observatorio import config
from observatorio.carga.dimensoes import garantir_recortes, id_fonte_numerico
from observatorio.coleta.base import Contexto, Fonte, gravar_raw
from observatorio.coleta.inep_indicadores import _territorios_uf_brasil
from observatorio.db import copiar_linhas
from observatorio.execucao import ArquivoRegistrado
from observatorio.http import obter_texto
from observatorio.log import obter_logger
from observatorio.transformacao import cabecalho as cb
from observatorio.transformacao.leitores import (
    ErroLeitura,
    abas_xlsx,
    extrair_membro,
    ler_xlsx,
    listar_membros,
)
from observatorio.transformacao.normalizacao import (
    codigo_municipio,
    converter_numero,
    normalizar_rotulo,
)

log = obter_logger(__name__)

_RX_ZIP = re.compile(r"https?://download\.inep\.gov\.br/.*sinopse[^/]*?(\d{4})[^/]*\.zip$", re.IGNORECASE)
_RX_TITULO = re.compile(r"^\s*(\d+(?:\.\d+)*)\s*[–—-]\s*(.+)$")


def descobrir_links(html: str) -> dict[int, str]:
    """{ano: url} a partir da página de Sinopses da Educação Básica."""
    sopa = BeautifulSoup(html, "html.parser")
    links: dict[int, str] = {}
    for a in sopa.find_all("a", href=True):
        href = a["href"].strip()
        m = _RX_ZIP.match(href)
        if m:
            links.setdefault(int(m.group(1)), href)
    return links


def limpar(texto: str | None) -> str:
    """Rótulo normalizado sem a nota de rodapé colada no fim ("Total1-8" -> "total")."""
    t = normalizar_rotulo(texto)
    return re.sub(r"[\d\s\-–,]+$", "", t).strip()


def _partes_uteis(col: cb.Coluna) -> list[str]:
    return [p for p in (limpar(x) for x in col.partes)
            if p and not p.startswith("numero de") and not p.startswith("etapa de ensino")
            and not p.startswith("nivel de escolaridade")]


_FILHAS = {"inf": {"inf_cre", "inf_pre"}, "fund": {"fund_ai", "fund_af"}, "eja": {"eja_fund", "eja_med"}}


def etapa_matricula(col: cb.Coluna) -> tuple[str | None, bool]:
    """(etapa, principal). principal = é o total da etapa (e não um subitem, como "Ensino Médio Normal")."""
    partes = _partes_uteis(col)
    if not partes or partes == ["total"]:
        # "Total" logo abaixo de "Etapa de Ensino" (sem o nome do grupo, que falta em alguns anos, ex.:
        # Educação Profissional em 2015) não é o total da educação básica: fica como detalhe.
        dentro_de_etapa = any(limpar(p).startswith("etapa de ensino") for p in col.partes)
        return "bas", not dentro_de_etapa
    grupo = partes[0]
    etapa_grupo = cb.classificar_etapa(grupo)
    folha = partes[-1]
    if len(partes) == 1 or (folha == "total" and len(partes) == 2):
        return etapa_grupo, True
    if etapa_grupo == "prof" and len(partes) == 3 and folha == "total" and "tecnica" in partes[1]:
        return "prof_tec", True
    combinada = cb.classificar_etapa(f"{grupo} > {folha}")
    if combinada in _FILHAS.get(etapa_grupo or "", set()):
        return combinada, True
    return etapa_grupo, False


def escolaridade_docente(col: cb.Coluna) -> str | None:
    partes = _partes_uteis(col)
    if not partes or partes == ["total"]:
        return "total"
    t = " > ".join(partes)
    folha = partes[-1]
    for chave in ("doutorado", "mestrado", "especializacao"):
        if chave in folha:
            return chave
    if "pos-graduacao" in t or "pos graduacao" in t:
        return "pos_graduacao" if folha in ("total", "pos-graduacao", "pos graduacao") else None
    if "sem licenciatura" in folha:
        return "superior_sem_licenciatura"
    if "com licenciatura" in folha or folha == "licenciatura":
        return "superior_licenciatura"
    if "graduacao" in t or "superior" in t:
        return "superior" if folha in ("total", "graduacao", "ensino superior", "superior") else None
    if "medio" in folha:
        return "medio"
    if "fundamental" in folha:
        return "fundamental"
    return None


@dataclass
class TabelaEncontrada:
    chave: str
    numero: str
    titulo: str
    aba: str


def titulo_da_aba(xlsx: Path, aba: str, max_linhas: int = 10) -> tuple[str, str] | None:
    gerador = ler_xlsx(xlsx, aba)
    try:
        for i, linha in enumerate(gerador):
            for v in linha:
                if isinstance(v, str):
                    m = _RX_TITULO.match(v.strip())
                    if m and len(m.group(2)) > 20:
                        return m.group(1), v.strip()
            if i >= max_linhas:
                break
        return None
    finally:
        gerador.close()  # fecha o arquivo já (no Windows, arquivo aberto não pode ser apagado)


def tem_tabela_municipal(xlsx: Path, aba: str, max_linhas: int = 40) -> bool:
    gerador = ler_xlsx(xlsx, aba)
    try:
        for i, linha in enumerate(gerador):
            if any(normalizar_rotulo(v) == "codigo do municipio" for v in linha if isinstance(v, str)):
                return True
            if i >= max_linhas:
                return False
        return False
    finally:
        gerador.close()


def localizar_tabelas(xlsx: Path) -> list[TabelaEncontrada]:
    cfg = config.carregar_yaml("sinopse.yaml")["tabelas"]
    achadas: dict[str, TabelaEncontrada] = {}
    for aba in abas_xlsx(xlsx):
        if len(achadas) == len(cfg):
            break
        t = titulo_da_aba(xlsx, aba)
        if not t:
            continue
        numero, titulo = t
        tn = normalizar_rotulo(titulo)
        for chave, regra in cfg.items():
            if chave in achadas:
                continue
            if re.search(regra["titulo"], tn) and not (regra.get("excluir") and re.search(regra["excluir"], tn)):
                # O "Sumário" lista todos os títulos: só vale a aba que tem a tabela de verdade.
                if not tem_tabela_municipal(xlsx, aba):
                    continue
                achadas[chave] = TabelaEncontrada(chave, numero, titulo, aba)
                break
    return list(achadas.values())


def ler_tabela(xlsx: Path, tabela: TabelaEncontrada, municipios: set[str], mapa_ufs: dict[str, str]):
    """Devolve (colunas de valor, linhas brutas, linhas [(nivel, territorio, [(coluna, valor)])])."""
    gerador = ler_xlsx(xlsx, tabela.aba)
    primeiras = []
    for linha in gerador:
        primeiras.append(linha)
        if len(primeiras) >= 40:
            break
    ini, fim = cb.localizar_cabecalho(primeiras)
    colunas = cb.montar_colunas(primeiras[ini:fim])
    ids: dict[str, int] = {}
    for c in colunas:
        n = limpar(c.partes[0]) if c.partes else ""
        if n in ("regiao geografica", "regiao", "brasil"):
            ids.setdefault("regiao", c.indice)
        elif n in ("unidade da federacao", "uf"):
            ids.setdefault("uf", c.indice)
        elif n in ("codigo do municipio", "codigo"):
            ids.setdefault("codigo", c.indice)
        elif n in ("municipio", "nome do municipio"):
            ids.setdefault("municipio", c.indice)
    if "codigo" not in ids:
        raise ErroLeitura(f"Sinopse {tabela.numero}: coluna 'Código do Município' não encontrada no cabeçalho")
    ultimo_id = max(ids.values())
    valores_col = [c for c in colunas if c.indice > ultimo_id]

    def todas():
        yield from primeiras[fim:]
        yield from gerador

    brutas, linhas = [], []
    num = fim
    for linha in todas():
        num += 1
        if not linha:
            continue

        def cel(i):
            return linha[i] if i is not None and i < len(linha) else None

        try:
            cod = codigo_municipio(cel(ids["codigo"]))
        except ValueError:
            cod = None
        if cod:
            if cod not in municipios:
                continue
            nivel, territorio = "municipio", cod
        else:
            uf = normalizar_rotulo(cel(ids.get("uf")))
            regiao = normalizar_rotulo(cel(ids.get("regiao")))
            if uf and not normalizar_rotulo(cel(ids.get("municipio"))):
                territorio = mapa_ufs.get(uf)
                nivel = "uf"
            elif regiao == "brasil":
                territorio, nivel = "1", "brasil"
            else:
                territorio = None
            if not territorio:
                continue
        brutas.append((num, {c.nome_origem: cel(c.indice) for c in colunas}))
        linhas.append((nivel, territorio, [(c, cel(c.indice)) for c in valores_col]))
    return valores_col, brutas, linhas


class SinopseEstatistica(Fonte):
    id_fonte = "sinopse_estatistica"
    tabelas_core = ("core.fato_docente",)
    versao_transformacao = "2026.09.1"

    def coletar(self, conn: psycopg.Connection, ctx: Contexto) -> list[ArquivoRegistrado]:
        pagina = config.fonte(self.id_fonte)["pagina_oficial"]
        links = descobrir_links(obter_texto(pagina))
        if not links:
            raise RuntimeError(f"Nenhum ZIP da Sinopse encontrado em {pagina}; a página pode ter mudado")
        registrados = []
        for ano, url in sorted(links.items()):
            if ctx.ano_desejado(ano):
                registrados.append(self.baixar_registrar(conn, ctx, url, ano, url.rsplit("/", 1)[-1]))
        return registrados

    def processar(self, conn: psycopg.Connection, arquivo: ArquivoRegistrado, ctx: Contexto) -> int:
        municipios = set(config.municipios_de_interesse())
        mapa_ufs = _territorios_uf_brasil()
        cfg = config.carregar_yaml("sinopse.yaml")["tabelas"]
        staging, faltando = [], set(cfg)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM raw.linha WHERE id_arquivo = %s", (arquivo.id_arquivo,))
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            membros = [(n, i) for n, i in listar_membros(arquivo.caminho) if n.lower().endswith(".xlsx")]
            if not membros:
                raise ErroLeitura(f"{arquivo.caminho.name}: nenhuma planilha .xlsx no ZIP")
            for j, (nome, info) in enumerate(membros):
                if not faltando:
                    break
                xlsx = extrair_membro(arquivo.caminho, info, Path(tmp) / f"sinopse_{j}.xlsx")
                for tab in localizar_tabelas(xlsx):
                    if tab.chave not in faltando:
                        continue
                    faltando.discard(tab.chave)
                    staging += self._processar_tabela(conn, arquivo, ctx, xlsx, tab, municipios, mapa_ufs,
                                                      cfg[tab.chave]["medida"])
        for chave in sorted(faltando):
            ctx.alertar(f"Sinopse {arquivo.ano}: tabela '{chave}' não encontrada pelo título (config/sinopse.yaml)")
        with conn.cursor() as cur:
            cur.execute("DELETE FROM staging.inep_indicador WHERE id_fonte = %s AND ano = %s", (self.id_fonte, arquivo.ano))
        n = copiar_linhas(
            conn, "staging.inep_indicador",
            ["id_fonte", "ano", "nivel", "cod_territorio", "co_entidade", "localizacao", "rede", "coluna_origem",
             "rotulo_origem", "medida", "cod_etapa", "valor", "valor_texto", "status_valor", "id_arquivo"],
            staging,
        )
        ctx.execucao.linhas_gravadas += n
        return n

    def _processar_tabela(self, conn, arquivo, ctx, xlsx, tab, municipios, mapa_ufs, medida_base) -> list[tuple]:
        colunas, brutas, linhas = ler_tabela(xlsx, tab, municipios, mapa_ufs)
        gravar_raw(conn, arquivo.id_arquivo, f"{tab.numero} {tab.chave}", brutas)
        ctx.execucao.linhas_lidas += len(brutas)
        classif: dict[int, tuple[str, str]] = {}
        usadas: set[str] = set()
        for c in colunas:
            if medida_base == "matriculas":
                etapa, principal = etapa_matricula(c)
                if etapa is None:
                    ctx.alertar(f"Sinopse {arquivo.ano} {tab.numero}: etapa não identificada para '{c.rotulo}'")
                    continue
                if principal and etapa in usadas:
                    ctx.alertar(f"Sinopse {arquivo.ano} {tab.numero}: duas colunas para a etapa {etapa}; "
                                f"'{c.rotulo}' ficou como detalhe")
                    principal = False
                if principal:
                    usadas.add(etapa)
                classif[c.indice] = ("matriculas" if principal else "matriculas_detalhe", etapa)
            else:
                esc = escolaridade_docente(c)
                if esc is None:
                    ctx.alertar(f"Sinopse {arquivo.ano} {tab.numero}: escolaridade não identificada para '{c.rotulo}'")
                    continue
                if esc in usadas:
                    ctx.alertar(f"Sinopse {arquivo.ano} {tab.numero}: coluna repetida para {esc}: '{c.rotulo}'")
                    continue
                usadas.add(esc)
                classif[c.indice] = (f"docentes_escolaridade:{esc}", "bas")
        saida = []
        for nivel, territorio, valores in linhas:
            for c, bruto in valores:
                if c.indice not in classif:
                    continue
                medida, etapa = classif[c.indice]
                t = converter_numero(bruto, self.id_fonte)
                saida.append((self.id_fonte, arquivo.ano, nivel, territorio, None, "total", "total",
                              f"{tab.numero}:{c.indice}:{c.rotulo}"[:300], c.rotulo, medida, etapa, t.valor, t.texto,
                              t.status, arquivo.id_arquivo))
        if not linhas:
            ctx.alertar(f"Sinopse {arquivo.ano} {tab.numero}: nenhuma linha dos territórios de interesse")
        log.info("Tabela da Sinopse processada", ano=arquivo.ano, tabela=tab.numero, linhas=len(linhas))
        return saida

    def carregar_core(self, conn: psycopg.Connection, id_versao: int, ctx: Contexto) -> int:
        with conn.cursor() as cur:
            cur.execute("""SELECT DISTINCT split_part(medida, ':', 2) FROM staging.inep_indicador
                           WHERE id_fonte = %s AND medida LIKE 'docentes_escolaridade:%%'""", (self.id_fonte,))
            garantir_recortes(conn, {("total" if v == "total" else f"escolaridade:{v}") for (v,) in cur.fetchall()})
        id_num = id_fonte_numerico(conn, self.id_fonte)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO core.fato_docente (ano, cod_territorio, co_entidade, cod_etapa, cod_recorte, qt_docentes,
                       variavel_origem, id_fonte, status_valor, id_versao, data_coleta)
                   SELECT s.ano, s.cod_territorio, NULL, s.cod_etapa,
                          CASE WHEN split_part(s.medida, ':', 2) = 'total' THEN 'total'
                               ELSE 'escolaridade:' || split_part(s.medida, ':', 2) END,
                          CASE WHEN s.status_valor = 'observado' THEN s.valor::integer END, s.coluna_origem, %s,
                          CASE WHEN s.status_valor = 'observado' THEN 'observado' ELSE 'sem_dado' END,
                          %s, a.data_coleta::date
                   FROM staging.inep_indicador s JOIN etl.etl_arquivo a USING (id_arquivo)
                   WHERE s.id_fonte = %s AND s.medida LIKE 'docentes_escolaridade:%%'
                   ON CONFLICT DO NOTHING""",
                (id_num, id_versao, self.id_fonte),
            )
            return cur.rowcount
