"""Indicadores Educacionais do INEP: rendimento, distorção idade-série, AFD, ATU e DSU.

Cada indicador tem uma página com uma aba por ano (sub-página ``<pagina>/<ano>``) e três arquivos
por ano: Brasil/regiões/UFs, municípios e escolas. Os nomes dos arquivos mudam entre anos
(ex.: tx_rendimento_municipios_2015.zip, TAXA_REND_2016_MUNICIPIOS.zip, tx_rend_municipios_2019.zip),
por isso os links são lidos das páginas.

As planilhas são lidas em streaming e interpretadas pelo texto do cabeçalho (ver
observatorio.transformacao.cabecalho). Só as linhas dos territórios de interesse são gravadas.
"""

from __future__ import annotations

import re
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import psycopg
from bs4 import BeautifulSoup

from observatorio import config
from observatorio.carga.dimensoes import garantir_recortes, id_fonte_numerico
from observatorio.coleta.base import Contexto, Fonte, gravar_raw
from observatorio.db import copiar_linhas
from observatorio.execucao import ArquivoRegistrado
from observatorio.http import obter_texto
from observatorio.log import obter_logger
from observatorio.transformacao import cabecalho as cb
from observatorio.transformacao import recortes as rc
from observatorio.transformacao.leitores import (
    ErroLeitura,
    extrair_membro,
    ler_xlsx,
    listar_membros,
)
from observatorio.transformacao.normalizacao import (
    codigo_escola,
    codigo_municipio,
    converter_numero,
    normalizar_localizacao,
    normalizar_rede,
    normalizar_rotulo,
)

log = obter_logger(__name__)

_RX_ZIP = re.compile(r"https?://download\.inep\.gov\.br/.+\.zip$", re.IGNORECASE)


def classificar_link(url: str) -> str | None:
    nome = url.rsplit("/", 1)[-1].lower()
    if "escola" in nome:
        return "escola"
    if "munic" in nome:
        return "municipio"
    if "brasil" in nome or "regio" in nome or "ufs" in nome or re.search(r"(^|_)uf(s)?(_|\.)", nome):
        return "uf"
    return None


def descobrir_links_por_ano(pagina: str) -> dict[int, dict[str, str]]:
    """Lê a página do indicador e cada aba de ano; devolve {ano: {nivel: url}}."""
    html = obter_texto(pagina)
    sopa = BeautifulSoup(html, "html.parser")
    anos = []
    for a in sopa.select("a[data-id]"):
        digitos = re.sub(r"\D", "", a.get("data-id", ""))
        if len(digitos) == 4:
            anos.append(int(digitos))
    resultado: dict[int, dict[str, str]] = {}
    for ano in sorted(set(anos)):
        try:
            sub = BeautifulSoup(obter_texto(f"{pagina.rstrip('/')}/{ano}"), "html.parser")
        except Exception as e:
            log.warning("Aba do ano indisponível", pagina=pagina, ano=ano, erro=str(e))
            continue
        for a in sub.find_all("a", href=True):
            href = a["href"].strip()
            if _RX_ZIP.match(href):
                nivel = classificar_link(href)
                if nivel:
                    resultado.setdefault(ano, {}).setdefault(nivel, href)
    return resultado


# ------------------------------------------------------------------ leitura das planilhas

@dataclass
class LinhaPlanilha:
    num_linha: int
    nivel: str
    cod_territorio: str
    co_entidade: str | None
    ano: int | None
    localizacao: str   # 'total', 'urbana', 'rural'
    rede: str          # 'total', 'municipal', ...
    valores: list[tuple[cb.Coluna, object]]
    original: dict[str, object]


def _territorios_uf_brasil() -> dict[str, str]:
    """Nome normalizado -> código, para as linhas de Brasil e UFs de comparação."""
    from observatorio.db import conectar
    mapa = {"brasil": "1"}
    try:
        with conectar() as conn, conn.cursor() as cur:
            cur.execute("SELECT cod_territorio, nome, sg_uf FROM core.dim_territorio WHERE nivel = 'uf'")
            for cod, nome, sg in cur.fetchall():
                mapa[normalizar_rotulo(nome)] = cod
                if sg:
                    mapa[normalizar_rotulo(sg)] = cod
    except Exception:
        pass
    return mapa


def ler_planilha_inep(xlsx: Path, municipios: set[str], mapa_ufs: dict[str, str] | None = None,
                      aba: str | None = None) -> tuple[list[cb.Coluna], Iterator[LinhaPlanilha]]:
    """Abre a planilha, identifica o cabeçalho e devolve as colunas e um gerador de linhas filtradas."""
    gerador = ler_xlsx(xlsx, aba)
    primeiras = []
    for linha in gerador:
        primeiras.append(linha)
        if len(primeiras) >= 40:
            break
    ini, fim = cb.localizar_cabecalho(primeiras)
    colunas = cb.montar_colunas(primeiras[ini:fim])
    papeis = {c.indice: cb.papel_da_coluna(c) for c in colunas}
    idx = {p: i for i, p in papeis.items() if p}
    valores_col = [c for c in colunas if not papeis[c.indice]]
    mapa_ufs = mapa_ufs if mapa_ufs is not None else {}

    def linhas() -> Iterator[LinhaPlanilha]:
        todas = iter(primeiras[fim:])
        num = fim
        for linha in _encadear(todas, gerador):
            num += 1
            if not linha or all(v in (None, "") for v in linha):
                continue

            def val(papel):
                i = idx.get(papel)
                return linha[i] if i is not None and i < len(linha) else None

            co_ent = None
            if "cod_escola" in idx:
                try:
                    co_ent = codigo_escola(val("cod_escola"))
                except ValueError:
                    co_ent = None
            cod_mun = None
            if "cod_municipio" in idx:
                try:
                    cod_mun = codigo_municipio(val("cod_municipio"))
                except ValueError:
                    cod_mun = None
            if cod_mun:
                if cod_mun not in municipios:
                    continue
                nivel = "escola" if co_ent else "municipio"
                territorio = cod_mun
            elif "unidade" in idx or "sg_uf" in idx:
                # Tenta a UF antes da região: em 2016 o arquivo tem "Região" e "UF" (nome por extenso).
                territorio = None
                for papel in ("sg_uf", "unidade"):
                    if papel in idx:
                        nome = re.sub(r"\s*\(\d+\)$", "", normalizar_rotulo(val(papel)))
                        territorio = mapa_ufs.get(nome)
                        if territorio:
                            break
                if not territorio:
                    continue
                nivel = "brasil" if territorio == "1" else "uf"
            else:
                continue
            try:
                loc = normalizar_localizacao(val("localizacao")) if "localizacao" in idx else None
                rede = normalizar_rede(val("rede")) if "rede" in idx else None
            except ValueError as e:
                raise ErroLeitura(f"{xlsx.name}, linha {num}: {e}") from e
            ano_txt = val("ano")
            ano = int(float(ano_txt)) if ano_txt not in (None, "") and re.match(r"^\d{4}(\.0)?$", str(ano_txt)) else None
            original = {c.nome_origem: (linha[c.indice] if c.indice < len(linha) else None) for c in colunas}
            yield LinhaPlanilha(
                num, nivel, territorio, co_ent, ano, loc or "total", rede or "total",
                [(c, linha[c.indice] if c.indice < len(linha) else None) for c in valores_col], original,
            )

    return colunas, linhas()


def _encadear(*iteraveis):
    for it in iteraveis:
        yield from it


# ------------------------------------------------------------------ fonte genérica

class _IndicadorInep(Fonte):
    medida_fixa: str | None = None
    tabelas_core: tuple = ()
    versao_transformacao = "2026.09.1"
    usa_arquivo_escola = False

    def medida(self, col: cb.Coluna) -> str | None:
        return self.medida_fixa

    def coletar(self, conn: psycopg.Connection, ctx: Contexto) -> list[ArquivoRegistrado]:
        pagina = config.fonte(self.id_fonte)["pagina_oficial"]
        links = descobrir_links_por_ano(pagina)
        if not links:
            raise RuntimeError(f"Nenhum link encontrado em {pagina}; a página pode ter mudado de formato")
        niveis = ["municipio", "uf"]
        if self.usa_arquivo_escola and config.opcao_coleta("indicadores_por_escola", True):
            niveis.append("escola")
        registrados = []
        for ano, por_nivel in sorted(links.items()):
            if not ctx.ano_desejado(ano):
                continue
            for nivel in niveis:
                url = por_nivel.get(nivel)
                if not url:
                    if nivel == "municipio":
                        ctx.alertar(f"{self.id_fonte} {ano}: arquivo de municípios não encontrado na página")
                    continue
                registrados.append(self.baixar_registrar(conn, ctx, url, ano, url.rsplit("/", 1)[-1],
                                                         descricao=f"nivel={nivel}"))
        return registrados

    def processar(self, conn: psycopg.Connection, arquivo: ArquivoRegistrado, ctx: Contexto) -> int:
        municipios = set(config.municipios_de_interesse())
        mapa_ufs = _territorios_uf_brasil()
        # O ZIP de Brasil/regiões/UFs de 2015 e 2016 traz uma planilha para cada abrangência
        # (TX_REND_BRASIL, TX_REND_REG, TX_REND_UFS): todas as .xlsx do ZIP são lidas.
        membros = [(n, i) for n, i in listar_membros(arquivo.caminho)
                   if n.lower().endswith(".xlsx") and not Path(n).name.startswith("~$")]
        if not membros:
            raise ErroLeitura(f"{arquivo.caminho.name}: nenhuma planilha .xlsx no ZIP")
        staging, raw_por_membro, niveis, vistos = [], [], set(), set()
        divergentes: list[str] = []
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            for j, (nome, info) in enumerate(membros):
                xlsx = extrair_membro(arquivo.caminho, info, Path(tmp) / f"planilha_{j}.xlsx")
                colunas, linhas = ler_planilha_inep(xlsx, municipios, mapa_ufs)
                ident = {}
                for c in colunas:
                    if cb.papel_da_coluna(c):
                        continue
                    e = cb.identificar_etapa(c)
                    ident[c.indice] = e
                    if e.divergente:
                        divergentes.append(f"{c.nome_origem}: rótulo='{c.rotulo}' ({e.pelo_rotulo}) x código ({e.pelo_codigo})")
                raw = []
                for ln in linhas:
                    niveis.add(ln.nivel)
                    raw.append((ln.num_linha, ln.original))
                    ano = ln.ano or arquivo.ano
                    for col, bruto in ln.valores:
                        medida = self.medida(col)
                        etapa = ident[col.indice].etapa
                        if medida is None or etapa is None:
                            continue
                        chave = (ano, ln.nivel, ln.cod_territorio, ln.co_entidade, ln.localizacao, ln.rede,
                                 f"{col.indice}:{col.nome_origem}")
                        if chave in vistos:
                            continue
                        vistos.add(chave)
                        t = converter_numero(bruto, self.id_fonte)
                        staging.append((self.id_fonte, ano, ln.nivel, ln.cod_territorio, ln.co_entidade, ln.localizacao,
                                        ln.rede, f"{col.indice}:{col.nome_origem}", col.rotulo, medida, etapa, t.valor,
                                        t.texto, t.status, arquivo.id_arquivo))
                raw_por_membro.append((Path(nome).name, raw))
        if divergentes:
            ctx.alertar(f"{self.id_fonte} {arquivo.ano}: {len(divergentes)} coluna(s) com rótulo e código divergentes; "
                        f"vale o código. Ex.: {divergentes[0]}")
        raw = [r for _, rs in raw_por_membro for r in rs]
        with conn.cursor() as cur:
            cur.execute("DELETE FROM staging.inep_indicador WHERE id_fonte = %s AND ano = %s AND id_arquivo IN "
                        "(SELECT id_arquivo FROM etl.etl_arquivo WHERE id_fonte = %s AND ano_referencia = %s "
                        "AND COALESCE(descricao,'') = COALESCE(%s,''))",
                        (self.id_fonte, arquivo.ano, self.id_fonte, arquivo.ano, arquivo.descricao))
        with conn.cursor() as cur:
            cur.execute("DELETE FROM raw.linha WHERE id_arquivo = %s", (arquivo.id_arquivo,))
        for nome_membro, linhas_raw in raw_por_membro:
            if linhas_raw:
                gravar_raw(conn, arquivo.id_arquivo, nome_membro[:200], linhas_raw)
        n = copiar_linhas(
            conn, "staging.inep_indicador",
            ["id_fonte", "ano", "nivel", "cod_territorio", "co_entidade", "localizacao", "rede", "coluna_origem",
             "rotulo_origem", "medida", "cod_etapa", "valor", "valor_texto", "status_valor", "id_arquivo"],
            staging,
        )
        ctx.execucao.linhas_lidas += len(raw)
        ctx.execucao.linhas_gravadas += n
        if not raw:
            ctx.alertar(f"{self.id_fonte} {arquivo.ano} ({arquivo.descricao}): nenhuma linha dos territórios de interesse")
        log.info("Planilha INEP processada", fonte=self.id_fonte, ano=arquivo.ano, niveis=",".join(sorted(niveis)),
                 linhas=len(raw), valores=n)
        return n

    def carregar_core(self, conn: psycopg.Connection, id_versao: int, ctx: Contexto) -> int:
        return 0


class _ComFatoRendimento(_IndicadorInep):
    tabelas_core = ("core.fato_rendimento",)
    usa_arquivo_escola = True

    def carregar_core(self, conn: psycopg.Connection, id_versao: int, ctx: Contexto) -> int:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT localizacao, rede FROM staging.inep_indicador WHERE id_fonte = %s""", (self.id_fonte,))
            codigos = {rc.montar(None if r == "total" else r, None if l == "total" else l) for l, r in cur.fetchall()}
        garantir_recortes(conn, codigos)
        id_num = id_fonte_numerico(conn, self.id_fonte)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO core.fato_rendimento (ano, cod_territorio, co_entidade, cod_etapa, cod_recorte, medida,
                       valor, status_valor, id_fonte, id_versao, data_coleta)
                   SELECT DISTINCT ON (s.ano, s.cod_territorio, s.co_entidade, s.cod_etapa, s.rede, s.localizacao, s.medida)
                          s.ano, s.cod_territorio, s.co_entidade, s.cod_etapa,
                          CASE WHEN s.rede = 'total' AND s.localizacao = 'total' THEN 'total'
                               ELSE concat_ws('|', CASE WHEN s.rede <> 'total' THEN 'rede:' || s.rede END,
                                                   CASE WHEN s.localizacao <> 'total' THEN 'localizacao:' || s.localizacao END) END,
                          s.medida, CASE WHEN s.status_valor = 'observado' THEN s.valor END, s.status_valor, %s, %s,
                          a.data_coleta::date
                   FROM staging.inep_indicador s JOIN etl.etl_arquivo a USING (id_arquivo)
                   JOIN core.dim_tempo t ON t.ano = s.ano
                   WHERE s.id_fonte = %s AND s.medida IN ('aprovacao', 'reprovacao', 'abandono', 'distorcao_idade_serie')
                   -- Duas colunas com a mesma etapa e medida: vale a que tem número (e, entre elas, a de menor posição).
                   ORDER BY s.ano, s.cod_territorio, s.co_entidade, s.cod_etapa, s.rede, s.localizacao, s.medida,
                            (s.status_valor = 'observado') DESC, split_part(s.coluna_origem, ':', 1)::int""",
                (id_num, id_versao, self.id_fonte),
            )
            return cur.rowcount


class TaxasRendimento(_ComFatoRendimento):
    id_fonte = "inep_rendimento"

    def medida(self, col: cb.Coluna) -> str | None:
        return cb.classificar_medida_rendimento(col.rotulo)


class DistorcaoIdadeSerie(_ComFatoRendimento):
    id_fonte = "inep_distorcao"
    medida_fixa = "distorcao_idade_serie"


class AdequacaoFormacaoDocente(_IndicadorInep):
    id_fonte = "inep_afd"

    def medida(self, col: cb.Coluna) -> str | None:
        g = cb.grupo_afd_da_coluna(col)
        return f"afd_grupo_{g}" if g else None


class MediaAlunosTurma(_IndicadorInep):
    id_fonte = "inep_atu"
    medida_fixa = "media_alunos_turma"


class DocentesSuperior(_IndicadorInep):
    id_fonte = "inep_dsu"
    medida_fixa = "pct_docentes_superior"
