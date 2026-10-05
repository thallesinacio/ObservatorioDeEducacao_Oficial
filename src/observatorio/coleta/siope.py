"""SIOPE - dados abertos do FNDE (serviço OData "Olinda").

Uma consulta por recurso, ano (6º bimestre) e UF, filtrada pelos municípios de interesse
(COD_MUNI tem 6 dígitos, sem o dígito verificador). Recursos e códigos em config/siope.yaml.

Dado pessoal: o recurso Remuneracao_Siope (nome de cada profissional) e os dados do responsável
pela declaração NÃO são coletados. Dados_Gerais_Siope é pedido com $select só das colunas de
valores.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

import psycopg

from observatorio import config
from observatorio.carga.dimensoes import id_fonte_numerico
from observatorio.coleta.base import Contexto, Fonte, gravar_raw
from observatorio.db import copiar_linhas
from observatorio.execucao import ArquivoRegistrado, registrar_arquivo
from observatorio.http import obter, salvar_bytes
from observatorio.log import obter_logger
from observatorio.transformacao.normalizacao import codigo_municipio_6

log = obter_logger(__name__)

# Código IBGE da UF -> sigla (tabela fixa do IBGE).
SIGLAS_UF = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI",
    "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}


def cfg() -> dict:
    return config.carregar_yaml("siope.yaml")


def decimal_ou_none(v) -> Decimal | None:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        return Decimal(str(v).strip())
    except InvalidOperation:
        return None


def montar_url(recurso: str, ano: int, uf: str, cod_munis6: list[str], select: str | None = None) -> str:
    base = cfg()["url_base"].rstrip("/")
    periodo = cfg()["periodo"]
    filtro = " or ".join(f"COD_MUNI eq {c}" for c in cod_munis6)
    partes = [f"@Ano_Consulta={ano}", f"@Num_Peri={periodo}", f"@Sig_UF='{uf}'", "$format=json",
              f"$filter={quote(filtro)}"]
    if select:
        partes.append(f"$select={select}")
    return f"{base}/{recurso}(Ano_Consulta=@Ano_Consulta,Num_Peri=@Num_Peri,Sig_UF=@Sig_UF)?" + "&".join(partes)


def municipios_por_uf() -> dict[str, dict[str, str]]:
    """{sigla: {cod6: cod7}}"""
    saida: dict[str, dict[str, str]] = {}
    for cod7 in config.municipios_de_interesse():
        saida.setdefault(SIGLAS_UF[cod7[:2]], {})[codigo_municipio_6(cod7)] = cod7
    return saida


def fundeb_do_ano(ano: int) -> dict | None:
    for p in cfg()["fundeb"]["por_periodo"]:
        ini, fim = p["anos"]
        if ini <= ano <= fim:
            return p
    return None


class Siope(Fonte):
    id_fonte = "siope"
    tabelas_core = ("core.fato_financiamento",)
    versao_transformacao = "2026.09.1"

    def coletar(self, conn: psycopg.Connection, ctx: Contexto) -> list[ArquivoRegistrado]:
        c = cfg()
        ultimo = dt.date.today().year - 1
        anos = [a for a in range(max(c["ano_minimo"], 2000), ultimo + 1) if ctx.ano_desejado(a)]
        registrados = []
        for ano in anos:
            for uf, munis in municipios_por_uf().items():
                for chave, rec in c["recursos"].items():
                    url = montar_url(rec["nome"], ano, uf, sorted(munis), rec.get("select"))
                    resp = obter(url)
                    dados = resp.json()
                    if not dados.get("value"):
                        ctx.alertar(f"SIOPE {rec['nome']} {ano} {uf}: sem declaração para os municípios de interesse")
                        continue
                    baixado = salvar_bytes(url, resp.content, self.pasta_ano(ano) / f"{chave}_{uf}.json", resp.status_code)
                    registrados.append(registrar_arquivo(conn, self.id_fonte, ano, baixado, id_execucao=ctx.id_execucao,
                                                         descricao=f"recurso={chave};uf={uf}"))
        return registrados

    def processar(self, conn: psycopg.Connection, arquivo: ArquivoRegistrado, ctx: Contexto) -> int:
        desc = dict(p.split("=", 1) for p in (arquivo.descricao or "").split(";") if "=" in p)
        recurso, uf = desc.get("recurso"), desc.get("uf")
        munis = municipios_por_uf().get(uf, {})
        registros = json.loads(arquivo.caminho.read_text(encoding="utf-8")).get("value", [])
        gravar_raw(conn, arquivo.id_arquivo, recurso, ((i + 1, r) for i, r in enumerate(registros)))
        ano = arquivo.ano
        linhas = []
        for i, r in enumerate(registros):
            cod7 = munis.get(str(r.get("COD_MUNI")))
            if cod7 is None or int(r.get("NUM_ANO", ano)) != ano:
                continue
            if recurso == "indicadores":
                v = decimal_ou_none(r.get("VAL_INDI"))
                linhas.append((ano, cod7, r.get("TIPO") or "", int(r["COD_INDI"]), r.get("COD_EXIB"), r.get("NOM_INDI"),
                               r.get("NOM_GRUP_INDI"), v, r.get("VAL_INDI"), arquivo.id_arquivo))
            elif recurso == "receita":
                linhas.append((ano, cod7, str(r.get("COD_EXIB_FORMATADO") or ""), (r.get("NOM_ITEM") or "").strip(),
                               r.get("IDN_CLAS"), r.get("NOM_COLU") or "", r.get("NUM_NIVE"), r.get("NUM_ORDE"), i + 1,
                               decimal_ou_none(r.get("VAL_DECL")), arquivo.id_arquivo))
            elif recurso == "despesa_funcao":
                linhas.append((ano, cod7, str(r.get("NUM_ORDE") or ""), (r.get("DES_SUBF") or "").strip(),
                               decimal_ou_none(r.get("VAL_DESP_EMPE")), decimal_ou_none(r.get("VAL_DESP_LIQU")),
                               decimal_ou_none(r.get("VAL_DESP_PAGA")), arquivo.id_arquivo))
            elif recurso == "dados_gerais":
                linhas.append((ano, cod7, r.get("NUM_POPU"), decimal_ou_none(r.get("VL_DESP_ORCA_EDU")),
                               decimal_ou_none(r.get("VL_DESP_EMPE_EDU")), decimal_ou_none(r.get("VL_DESP_LIQU_EDU")),
                               decimal_ou_none(r.get("VL_DESP_PAGA_EDU")), decimal_ou_none(r.get("VAL_DESP_LIQU")),
                               decimal_ou_none(r.get("VAL_RECE_REAL")), r.get("DAT_DECL"), arquivo.id_arquivo))
        tabela, colunas, chave = {
            "indicadores": ("staging.siope_indicador",
                            ["ano", "cod_territorio", "tipo", "cod_indi", "cod_exib", "nom_indi", "nom_grupo", "valor",
                             "valor_texto", "id_arquivo"], (0, 1, 2, 3)),
            "receita": ("staging.siope_receita",
                        ["ano", "cod_territorio", "cod_rubrica", "nom_item", "idn_clas", "coluna", "num_nive", "num_orde",
                         "linha", "valor", "id_arquivo"], (0, 1, 8)),
            "despesa_funcao": ("staging.siope_despesa_funcao",
                               ["ano", "cod_territorio", "num_orde", "subfuncao", "empenhada", "liquidada", "paga",
                                "id_arquivo"], (0, 1, 2, 3)),
            "dados_gerais": ("staging.siope_dados_gerais",
                             ["ano", "cod_territorio", "populacao_declarada", "desp_educacao_orcada",
                              "desp_educacao_empenhada", "desp_educacao_liquidada", "desp_educacao_paga",
                              "desp_total_liquidada", "receita_realizada", "data_declaracao", "id_arquivo"], (0, 1)),
        }[recurso]
        unicos = {}
        for l in linhas:
            k = tuple(l[j] for j in chave)
            if k in unicos:
                ctx.alertar(f"SIOPE {recurso} {ano}: linha repetida {k}; mantida a primeira")
                continue
            unicos[k] = l
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {tabela} WHERE ano = %s AND cod_territorio = ANY(%s)", (ano, list(munis.values())))
        n = copiar_linhas(conn, tabela, colunas, unicos.values())
        ctx.execucao.linhas_lidas += len(registros)
        ctx.execucao.linhas_gravadas += n
        return n

    def carregar_core(self, conn: psycopg.Connection, id_versao: int, ctx: Contexto) -> int:
        id_num = id_fonte_numerico(conn, self.id_fonte)
        total = 0
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO core.fato_financiamento (ano, cod_territorio, id_fonte, demonstrativo, rubrica_codigo,
                       rubrica_nome, coluna, ordem, valor, id_versao, data_coleta)
                   SELECT s.ano, s.cod_territorio, %s, 'SIOPE-Receita', s.cod_rubrica, s.nom_item, s.coluna,
                          s.linha::text, s.valor, %s, a.data_coleta::date
                   FROM staging.siope_receita s JOIN etl.etl_arquivo a USING (id_arquivo)""",
                (id_num, id_versao))
            total += cur.rowcount
            cur.execute(
                """INSERT INTO core.fato_financiamento (ano, cod_territorio, id_fonte, demonstrativo, rubrica_codigo,
                       rubrica_nome, coluna, ordem, valor, id_versao, data_coleta)
                   SELECT s.ano, s.cod_territorio, %s, 'SIOPE-Despesa-Funcao', split_part(s.subfuncao, ' - ', 1),
                          s.subfuncao, c.coluna, s.num_orde, c.valor, %s, a.data_coleta::date
                   FROM staging.siope_despesa_funcao s JOIN etl.etl_arquivo a USING (id_arquivo)
                   CROSS JOIN LATERAL (VALUES ('Despesas Empenhadas', s.empenhada), ('Despesas Liquidadas', s.liquidada),
                                              ('Despesas Pagas', s.paga)) AS c(coluna, valor)""",
                (id_num, id_versao))
            total += cur.rowcount
            cur.execute(
                """INSERT INTO core.fato_financiamento (ano, cod_territorio, id_fonte, demonstrativo, rubrica_codigo,
                       rubrica_nome, coluna, ordem, valor, id_versao, data_coleta)
                   SELECT s.ano, s.cod_territorio, %s, 'SIOPE-Dados-Gerais', c.codigo, c.nome, 'Valor declarado', '',
                          c.valor, %s, a.data_coleta::date
                   FROM staging.siope_dados_gerais s JOIN etl.etl_arquivo a USING (id_arquivo)
                   CROSS JOIN LATERAL (VALUES
                     ('VL_DESP_ORCA_EDU', 'Despesa com educação - orçada', s.desp_educacao_orcada),
                     ('VL_DESP_EMPE_EDU', 'Despesa com educação - empenhada', s.desp_educacao_empenhada),
                     ('VL_DESP_LIQU_EDU', 'Despesa com educação - liquidada', s.desp_educacao_liquidada),
                     ('VL_DESP_PAGA_EDU', 'Despesa com educação - paga', s.desp_educacao_paga),
                     ('VAL_DESP_LIQU', 'Despesa total liquidada', s.desp_total_liquidada),
                     ('VAL_RECE_REAL', 'Receita realizada', s.receita_realizada)) AS c(codigo, nome, valor)""",
                (id_num, id_versao))
            total += cur.rowcount
        return total
