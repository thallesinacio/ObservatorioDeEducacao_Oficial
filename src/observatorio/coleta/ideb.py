"""Ideb - resultados (INEP).

A página de resultados lista um ZIP por etapa (anos iniciais, anos finais, ensino médio) e nível
(municípios, escolas), mais um de regiões/UFs e um do Brasil. Cada planilha está em formato largo:
os anos ficam nas colunas. A linha de códigos de variável (SG_UF, CO_MUNICIPIO, REDE,
VL_APROVACAO_2017_SI_4, VL_NOTA_MATEMATICA_2019, VL_OBSERVADO_2023, VL_PROJECAO_2021...) é a
especificação legível por máquina e é o que este coletor usa para identificar cada valor; o texto
do cabeçalho muda entre edições (inclusive com notas de rodapé coladas ao ano: "IDEB 20211").

Cada edição baixada é guardada: o INEP revisa valores já publicados, então o fato guarda a edição
de onde o valor foi lido.
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
from observatorio.coleta.inep_indicadores import _territorios_uf_brasil
from observatorio.db import copiar_linhas
from observatorio.execucao import ArquivoRegistrado
from observatorio.http import obter_texto
from observatorio.log import obter_logger
from observatorio.transformacao import recortes as rc
from observatorio.transformacao.leitores import (
    ErroLeitura,
    abas_xlsx,
    extrair_membro,
    ler_xlsx,
    listar_membros,
)
from observatorio.transformacao.normalizacao import (
    codigo_escola,
    codigo_municipio,
    converter_numero,
    normalizar_rede,
    normalizar_rotulo,
)

log = obter_logger(__name__)

_RX_LINK = re.compile(
    r"https?://download\.inep\.gov\.br/ideb/resultados/"
    r"(divulgacao_(anos_iniciais|anos_finais|ensino_medio)_(municipios|escolas)_(\d{4})"
    r"|divulgacao_regioes_ufs_ideb_(\d{4})|divulgacao_brasil_ideb_(\d{4}))\.zip$",
    re.IGNORECASE,
)

ETAPA_POR_NOME = {"anos_iniciais": "fund_ai", "anos_finais": "fund_af", "ensino_medio": "med"}

# Código de variável -> medida.
_RX_VL = re.compile(
    r"^VL_(APROVACAO|INDICADOR_REND|NOTA_MATEMATICA|NOTA_PORTUGUES|NOTA_MEDIA|OBSERVADO|PROJECAO)_(\d{4})(?:_(.+))?$"
)
MEDIDAS = {
    "APROVACAO": "aprovacao",
    "INDICADOR_REND": "indicador_rendimento",
    "NOTA_MATEMATICA": "matematica",
    "NOTA_PORTUGUES": "lingua_portuguesa",
    "NOTA_MEDIA": "nota_padronizada",
    "OBSERVADO": "ideb",
    "PROJECAO": "meta_ideb",
}

_ID_POR_CODIGO = {
    "SG_UF": "sg_uf",
    "CO_MUNICIPIO": "cod_municipio",
    "ID_ESCOLA": "cod_escola",
    "CO_ENTIDADE": "cod_escola",
    "CO_ESCOLA": "cod_escola",
    "REDE": "rede",
}


def descobrir_links(html: str) -> list[dict]:
    """Links de download da página de resultados: [{url, edicao, etapa, nivel}]."""
    sopa = BeautifulSoup(html, "html.parser")
    vistos, links = set(), []
    for a in sopa.find_all("a", href=True):
        href = a["href"].strip()
        m = _RX_LINK.match(href)
        if not m or href in vistos:
            continue
        vistos.add(href)
        if m.group(2):
            links.append({"url": href, "edicao": int(m.group(4)), "etapa": ETAPA_POR_NOME[m.group(2).lower()],
                          "nivel": "municipio" if m.group(3).lower() == "municipios" else "escola"})
        elif m.group(5):
            links.append({"url": href, "edicao": int(m.group(5)), "etapa": None, "nivel": "uf"})
        else:
            links.append({"url": href, "edicao": int(m.group(6)), "etapa": None, "nivel": "brasil"})
    return links


def slug_da_aba(data_id: str) -> str:
    """'2005 | 2025' -> '2005-2025' (endereço da sub-página que o portal gov.br carrega na aba)."""
    return re.sub(r"[^0-9a-z]+", "-", normalizar_rotulo(data_id)).strip("-")


def descobrir_links_com_abas(pagina: str) -> list[dict]:
    """Links da página de resultados. Os arquivos ficam dentro de abas carregadas depois
    (a[data-id], ex.: "2005 | 2025" -> <pagina>/2005-2025, verificado em 29/09/2026)."""
    html = obter_texto(pagina)
    links = descobrir_links(html)
    sopa = BeautifulSoup(html, "html.parser")
    for a in sopa.select("a[data-id]"):
        slug = slug_da_aba(a.get("data-id", ""))
        if not slug:
            continue
        try:
            links += descobrir_links(obter_texto(f"{pagina.rstrip('/')}/{slug}"))
        except Exception as e:
            log.warning("Aba da página do Ideb indisponível", aba=slug, erro=str(e))
    unicos = {lk["url"]: lk for lk in links}
    return list(unicos.values())


def etapa_do_texto(texto: str) -> str | None:
    t = normalizar_rotulo(texto)
    if "anos iniciais" in t:
        return "fund_ai"
    if "anos finais" in t:
        return "fund_af"
    if "ensino medio" in t:
        return "med"
    return None


def etapa_da_aprovacao(base: str, rotulo: str, sufixo: str | None) -> str | None:
    """Etapa de uma coluna de taxa de aprovação, pelo RÓTULO do cabeçalho:
    "1º ao 5º ano" / "6º a 9º ano" / "Total" = etapa inteira; "3º" = 3º ano; "2ª" / "2ª série" = série do médio.
    Sem rótulo reconhecível, a coluna é ignorada (os códigos não são confiáveis para a série)."""
    t = normalizar_rotulo(rotulo)
    if re.search(r"\bao\b|\ba\b \d|total", t):
        return base
    m = re.fullmatch(r"(\d)\s*[oº°]?( ano)?", t)
    if m and base in ("fund_ai", "fund_af"):
        return f"fund_ano_{m.group(1)}"
    m = re.fullmatch(r"(\d)\s*[aª]?( serie)?", t)
    if m and base == "med":
        return f"med_serie_{m.group(1)}"
    if not t and (sufixo is None):
        return base
    return None


@dataclass
class ValorIdeb:
    nivel: str
    cod_territorio: str
    co_entidade: str | None
    rede: str
    cod_etapa: str
    ano: int
    medida: str
    coluna_origem: str
    bruto: object


def ler_planilha_ideb(linhas: Iterator[list], etapa_arquivo: str | None, municipios: set[str],
                      mapa_ufs: dict[str, str], contexto: str) -> tuple[list[tuple[int, dict]], list[ValorIdeb], list[str]]:
    """Lê uma aba do Ideb. Devolve (linhas brutas, valores, avisos)."""
    buffer: list[list] = []
    k = None
    for linha in linhas:
        buffer.append(linha)
        if any(isinstance(v, str) and v.strip().startswith("VL_") for v in linha):
            k = len(buffer) - 1
            break
        if len(buffer) > 60:
            break
    if k is None:
        return [], [], [f"{contexto}: linha de códigos de variável (VL_*) não encontrada; aba ignorada"]
    codigos = [str(v).strip() if v not in (None, "") else "" for v in buffer[k]]
    titulo = " ".join(str(v) for linha in buffer[:k] for v in linha if v not in (None, ""))
    etapa = etapa_arquivo or etapa_do_texto(titulo)
    if etapa is None:
        return [], [], [f"{contexto}: etapa não identificada (nem pelo nome do arquivo nem pelo título); aba ignorada"]

    # Rótulo de cada coluna: o texto mais baixo do cabeçalho acima da linha de códigos. Serve para as
    # colunas sem código (arquivo de UFs: "Região/Unidade da Federação", "Rede") e para a série da
    # aprovação, porque nos anos iniciais os códigos estão deslocados em relação aos rótulos
    # (VL_APROVACAO_2005_SI = "1º", VL_APROVACAO_2005_1 = "2º"...; verificado na edição 2025).
    largura = len(codigos)
    rotulos = []
    for i in range(largura):
        r = ""
        for j in range(k - 1, max(-1, k - 7), -1):
            v = buffer[j][i] if i < len(buffer[j]) else None
            if isinstance(v, str) and v.strip():
                r = " ".join(v.split())
                break
        rotulos.append(r)
    primeiro_vl = next((i for i, c in enumerate(codigos) if _RX_VL.match(c)), largura)

    papeis: dict[str, int] = {}
    unidade_cols: list[int] = []
    vl_cols: list[tuple[int, str, int, str | None]] = []
    avisos: list[str] = []
    for i, c in enumerate(codigos):
        m = _RX_VL.match(c) if c else None
        if m:
            vl_cols.append((i, MEDIDAS[m.group(1)], int(m.group(2)), m.group(3)))
        elif c and c.upper() in _ID_POR_CODIGO:
            papeis.setdefault(_ID_POR_CODIGO[c.upper()], i)
        elif c and c.upper().startswith("VL_"):
            avisos.append(f"{contexto}: código {c} não reconhecido; coluna ignorada")
        elif i < primeiro_vl and normalizar_rotulo(rotulos[i]) == "rede":
            papeis.setdefault("rede", i)
        elif i < primeiro_vl and (c or rotulos[i]):
            unidade_cols.append(i)
    if "rede" not in papeis:
        return [], [], [f"{contexto}: coluna REDE não encontrada; aba ignorada"]

    brutas: list[tuple[int, dict]] = []
    valores: list[ValorIdeb] = []
    num = k + 1
    for linha in linhas:
        num += 1
        if not linha or all(v in (None, "") for v in linha):
            continue

        def cel(i: int | None):
            return linha[i] if i is not None and i < len(linha) else None

        co_ent = None
        if "cod_escola" in papeis:
            try:
                co_ent = codigo_escola(cel(papeis["cod_escola"]))
            except ValueError:
                co_ent = None
        cod_mun = None
        if "cod_municipio" in papeis:
            try:
                cod_mun = codigo_municipio(cel(papeis["cod_municipio"]))
            except ValueError:
                cod_mun = None
        if cod_mun:
            if cod_mun not in municipios:
                continue
            nivel, territorio = ("escola" if co_ent else "municipio"), cod_mun
        else:
            territorio = None
            for i in unidade_cols + ([papeis["sg_uf"]] if "sg_uf" in papeis else []):
                nome = re.sub(r"\s*\(\d+\)$", "", normalizar_rotulo(cel(i)))
                if nome in mapa_ufs:
                    territorio = mapa_ufs[nome]
                    break
            if territorio is None:
                continue  # rodapé, região ou UF fora do recorte
            nivel = "brasil" if territorio == "1" else "uf"
        rede_txt = cel(papeis["rede"])
        try:
            rede = normalizar_rede(rede_txt) or "total"
        except ValueError:
            avisos.append(f"{contexto}, linha {num}: rede '{rede_txt}' não reconhecida; linha ignorada")
            continue
        brutas.append((num, {codigos[i] or f"coluna_{i + 1}": cel(i) for i in range(len(codigos))}))
        for i, medida, ano, sufixo in vl_cols:
            cod_etapa = etapa_da_aprovacao(etapa, rotulos[i], sufixo) if medida == "aprovacao" else etapa
            if cod_etapa is None:
                continue
            valores.append(ValorIdeb(nivel, territorio, co_ent, rede, cod_etapa, ano, medida, codigos[i], cel(i)))
    return brutas, valores, avisos


class Ideb(Fonte):
    id_fonte = "ideb"
    tabelas_core = ("core.fato_avaliacao",)
    versao_transformacao = "2026.09.1"

    def coletar(self, conn: psycopg.Connection, ctx: Contexto) -> list[ArquivoRegistrado]:
        pagina = config.fonte(self.id_fonte)["pagina_oficial"]
        links = descobrir_links_com_abas(pagina)
        if not links:
            raise RuntimeError(f"Nenhum arquivo do Ideb encontrado em {pagina}; a página pode ter mudado")
        por_escola = config.opcao_coleta("ideb_por_escola", True)
        registrados = []
        for lk in sorted(links, key=lambda x: (x["edicao"], x["url"])):
            if not ctx.ano_desejado(lk["edicao"]):
                continue
            if lk["nivel"] == "escola" and not por_escola:
                continue
            nome = lk["url"].rsplit("/", 1)[-1]
            registrados.append(self.baixar_registrar(
                conn, ctx, lk["url"], lk["edicao"], nome,
                descricao=f"etapa={lk['etapa'] or 'todas'};nivel={lk['nivel']}"))
        return registrados

    def processar(self, conn: psycopg.Connection, arquivo: ArquivoRegistrado, ctx: Contexto) -> int:
        municipios = set(config.municipios_de_interesse())
        mapa_ufs = _territorios_uf_brasil()
        m = re.search(r"divulgacao_(anos_iniciais|anos_finais|ensino_medio)_", arquivo.url, re.IGNORECASE)
        etapa_arquivo = ETAPA_POR_NOME[m.group(1).lower()] if m else None
        edicao = arquivo.ano
        staging, avisos, total_brutas = [], [], 0
        with conn.cursor() as cur:
            cur.execute("DELETE FROM raw.linha WHERE id_arquivo = %s", (arquivo.id_arquivo,))
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            membros = [(n, i) for n, i in listar_membros(arquivo.caminho) if n.lower().endswith(".xlsx")]
            if not membros:
                raise ErroLeitura(f"{arquivo.caminho.name}: nenhuma planilha .xlsx no ZIP")
            for j, (nome, info) in enumerate(membros):
                xlsx = extrair_membro(arquivo.caminho, info, Path(tmp) / f"ideb_{j}.xlsx")
                etapa_membro = etapa_arquivo or etapa_do_texto(nome.replace("_", " "))
                for aba in abas_xlsx(xlsx):
                    etapa_aba = etapa_membro or etapa_do_texto(aba)
                    contexto = f"{Path(nome).name}/{aba}"
                    brutas, valores, av = ler_planilha_ideb(ler_xlsx(xlsx, aba), etapa_aba, municipios, mapa_ufs, contexto)
                    avisos += av
                    if brutas:
                        gravar_raw(conn, arquivo.id_arquivo, contexto[:200], brutas)
                        total_brutas += len(brutas)
                    for v in valores:
                        t = converter_numero(v.bruto, self.id_fonte)
                        staging.append((edicao, v.nivel, v.cod_territorio, v.co_entidade, v.rede, v.cod_etapa, v.ano,
                                        v.medida, v.coluna_origem, t.valor, t.texto, t.status, arquivo.id_arquivo))
        for a in avisos[:20]:
            ctx.alertar(a)
        # Mesma planilha baixada de novo (outra versão do arquivo na mesma URL) substitui a anterior.
        with conn.cursor() as cur:
            cur.execute(
                """DELETE FROM staging.ideb WHERE id_arquivo IN
                     (SELECT id_arquivo FROM etl.etl_arquivo WHERE id_fonte = %s AND url = %s)""",
                (self.id_fonte, arquivo.url))
        # Um arquivo pode repetir a mesma chave em abas diferentes: fica o primeiro valor.
        unicos = {}
        for r in staging:
            unicos.setdefault((r[0], r[1], r[2], r[3], r[4], r[5], r[8]), r)
        n = copiar_linhas(
            conn, "staging.ideb",
            ["edicao", "nivel", "cod_territorio", "co_entidade", "rede", "cod_etapa", "ano", "medida",
             "coluna_origem", "valor", "valor_texto", "status_valor", "id_arquivo"],
            unicos.values(),
        )
        ctx.execucao.linhas_lidas += total_brutas
        ctx.execucao.linhas_gravadas += n
        if not total_brutas:
            ctx.alertar(f"ideb {arquivo.url.rsplit('/', 1)[-1]}: nenhuma linha dos territórios de interesse")
        log.info("Planilha do Ideb processada", arquivo=arquivo.caminho.name, linhas=total_brutas, valores=n)
        return n

    def carregar_core(self, conn: psycopg.Connection, id_versao: int, ctx: Contexto) -> int:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT rede FROM staging.ideb")
            garantir_recortes(conn, {rc.montar(None if r == "total" else r) for (r,) in cur.fetchall()})
        id_num = id_fonte_numerico(conn, self.id_fonte)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO core.fato_avaliacao (ano, cod_territorio, co_entidade, cod_etapa, cod_recorte, componente,
                       instrumento, edicao, valor, status_valor, id_fonte, id_versao, data_coleta)
                   SELECT s.ano, s.cod_territorio, s.co_entidade, s.cod_etapa,
                          CASE WHEN s.rede = 'total' THEN 'total' ELSE 'rede:' || s.rede END,
                          s.medida, 'Saeb/Ideb', s.edicao,
                          CASE WHEN s.status_valor = 'observado' THEN round(s.valor, 4) END, s.status_valor,
                          %s, %s, a.data_coleta::date
                   FROM staging.ideb s
                   JOIN etl.etl_arquivo a USING (id_arquivo)
                   JOIN core.dim_tempo t ON t.ano = s.ano
                   WHERE s.id_arquivo IN (SELECT id_arquivo FROM etl.etl_arquivo
                                          WHERE id_fonte = %s AND processado_em IS NOT NULL AND NOT arquivo_removido)
                   ON CONFLICT (ano, cod_territorio, co_entidade, cod_etapa, cod_recorte, componente, instrumento,
                                edicao, id_versao) DO NOTHING""",
                (id_num, id_versao, self.id_fonte),
            )
            return cur.rowcount
