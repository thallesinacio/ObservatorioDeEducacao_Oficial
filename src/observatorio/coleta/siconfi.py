"""SICONFI - Tesouro Nacional (API ORDS https://apidatalake.tesouro.gov.br/ords/siconfi/tt/).

* DCA Anexo I-E (despesa por função/subfunção) de cada exercício: função 12 - Educação e suas
  subfunções (F3) e conferência com a despesa liquidada declarada ao SIOPE (F1/F2).
* RREO Anexo 08 (MDE), 6º bimestre: consultado para registrar a disponibilidade. Em 29/09/2026 ele
  NÃO constava para Juazeiro (2016, 2019, 2023, 2024) nem para Petrolina (2023); quando vier vazio,
  a execução registra um alerta e segue.

A API é paginada (items, hasMore, offset). Todas as páginas de uma consulta são gravadas juntas
num único JSON em data/raw/siconfi/<ano>/.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from decimal import Decimal

import psycopg

from observatorio import config
from observatorio.carga.dimensoes import id_fonte_numerico
from observatorio.coleta.base import Contexto, Fonte, gravar_raw
from observatorio.db import copiar_linhas
from observatorio.execucao import ArquivoRegistrado, registrar_arquivo
from observatorio.http import obter_json, salvar_bytes
from observatorio.log import obter_logger

log = obter_logger(__name__)

URL_BASE = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"

CONSULTAS = {
    "dca_anexo_i_e": {"endpoint": "dca", "params": {"no_anexo": "DCA-Anexo I-E"}, "demonstrativo": "DCA", "periodo": 0},
    "rreo_anexo_08": {"endpoint": "rreo", "params": {"nr_periodo": 6, "co_tipo_demonstrativo": "RREO",
                                                     "no_anexo": "RREO-Anexo 08"}, "demonstrativo": "RREO", "periodo": 6},
}


def consultar_paginado(endpoint: str, params: dict) -> list[dict]:
    itens, offset = [], 0
    while True:
        p = dict(params)
        if offset:
            p["offset"] = offset
        resp = obter_json(f"{URL_BASE}/{endpoint}", p)
        lote = resp.get("items", [])
        itens += lote
        if not resp.get("hasMore") or not lote:
            return itens
        offset += len(lote)


def codigo_da_conta(conta: str) -> str:
    """'12.361 - Ensino Fundamental' -> '12.361'; 'Total Geral' -> 'Total Geral'."""
    m = re.match(r"^\s*([\d.]+)\s*-", conta or "")
    return m.group(1) if m else (conta or "").strip()


class Siconfi(Fonte):
    id_fonte = "siconfi"
    tabelas_core = ("core.fato_financiamento",)
    versao_transformacao = "2026.09.1"

    def coletar(self, conn: psycopg.Connection, ctx: Contexto) -> list[ArquivoRegistrado]:
        ultimo = dt.date.today().year - 1
        anos = [a for a in range(2015, ultimo + 1) if ctx.ano_desejado(a)]
        registrados = []
        for ano in anos:
            for cod7 in config.municipios_de_interesse():
                for chave, q in CONSULTAS.items():
                    params = {"an_exercicio": ano, **q["params"], "id_ente": cod7}
                    itens = consultar_paginado(q["endpoint"], params)
                    if not itens:
                        ctx.alertar(f"SICONFI {q['params'].get('no_anexo')} {ano} {cod7}: não consta na API")
                        continue
                    url = f"{URL_BASE}/{q['endpoint']}?" + "&".join(f"{k}={v}" for k, v in params.items())
                    conteudo = json.dumps({"url": url, "items": itens}, ensure_ascii=False, sort_keys=True).encode("utf-8")
                    baixado = salvar_bytes(url, conteudo, self.pasta_ano(ano) / f"{chave}_{cod7}.json")
                    registrados.append(registrar_arquivo(conn, self.id_fonte, ano, baixado, id_execucao=ctx.id_execucao,
                                                         descricao=f"consulta={chave};ente={cod7}"))
        return registrados

    def processar(self, conn: psycopg.Connection, arquivo: ArquivoRegistrado, ctx: Contexto) -> int:
        desc = dict(p.split("=", 1) for p in (arquivo.descricao or "").split(";") if "=" in p)
        q = CONSULTAS[desc["consulta"]]
        dados = json.loads(arquivo.caminho.read_text(encoding="utf-8"))
        itens = dados["items"] if isinstance(dados, dict) else dados
        gravar_raw(conn, arquivo.id_arquivo, desc["consulta"], ((i + 1, r) for i, r in enumerate(itens)))
        linhas: dict[tuple, tuple] = {}
        for r in itens:
            cod = str(r.get("cod_ibge") or desc.get("ente"))
            ano = int(r.get("exercicio") or arquivo.ano)
            chave = (q["demonstrativo"], ano, int(r.get("periodo") or q["periodo"]), cod, r.get("anexo") or "",
                     r.get("rotulo") or "", r.get("coluna") or "", r.get("cod_conta") or "", r.get("conta") or "")
            valor = Decimal(str(r["valor"])) if r.get("valor") is not None else None
            if chave in linhas and linhas[chave][9] != valor:
                ctx.alertar(f"SICONFI {chave}: item repetido com valores diferentes; mantido o primeiro")
                continue
            linhas.setdefault(chave, (*chave, valor, arquivo.id_arquivo))
        with conn.cursor() as cur:
            cur.execute("""DELETE FROM staging.siconfi WHERE demonstrativo = %s AND ano = %s AND periodo = %s
                           AND cod_territorio = %s""", (q["demonstrativo"], arquivo.ano, q["periodo"], desc.get("ente")))
        n = copiar_linhas(conn, "staging.siconfi",
                          ["demonstrativo", "ano", "periodo", "cod_territorio", "anexo", "rotulo", "coluna", "cod_conta",
                           "conta", "valor", "id_arquivo"], linhas.values())
        ctx.execucao.linhas_lidas += len(itens)
        ctx.execucao.linhas_gravadas += n
        return n

    def carregar_core(self, conn: psycopg.Connection, id_versao: int, ctx: Contexto) -> int:
        id_num = id_fonte_numerico(conn, self.id_fonte)
        with conn.cursor() as cur:
            cur.execute(
                """SELECT s.ano, s.cod_territorio, s.anexo, s.rotulo, s.coluna, s.cod_conta, s.conta, s.valor,
                          a.data_coleta::date
                   FROM staging.siconfi s JOIN etl.etl_arquivo a USING (id_arquivo)
                   JOIN core.dim_territorio t ON t.cod_territorio = s.cod_territorio
                   WHERE s.demonstrativo = 'DCA' AND (s.conta ~ '^\\s*12(\\.|\\s)' )""")
            linhas = [(ano, terr, id_num, anexo, codigo_da_conta(conta), conta, coluna, f"{cod_conta}|{rotulo}", valor,
                       id_versao, data)
                      for ano, terr, anexo, rotulo, coluna, cod_conta, conta, valor, data in cur.fetchall()]
        return copiar_linhas(conn, "core.fato_financiamento",
                             ["ano", "cod_territorio", "id_fonte", "demonstrativo", "rubrica_codigo", "rubrica_nome",
                              "coluna", "ordem", "valor", "id_versao", "data_coleta"], linhas)
