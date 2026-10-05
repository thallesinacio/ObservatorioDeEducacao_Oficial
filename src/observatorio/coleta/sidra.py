"""IBGE SIDRA (API https://apisidra.ibge.gov.br).

Consultas definidas em config/sidra.yaml. A resposta é uma lista JSON cuja primeira linha traz os
rótulos das colunas (D1C = "Município (Código)", D3N = "Ano"...). A posição das dimensões muda de
tabela para tabela, por isso as colunas são identificadas pelo rótulo, não pela posição.

Convenções do IBGE para células sem número (config/regras_ausencia.yaml): "-" é zero absoluto,
".." não se aplica, "..." não disponível, "X" sigilo.
"""

from __future__ import annotations

import json
import re

import psycopg

from observatorio import config
from observatorio.carga.dimensoes import id_fonte_numerico
from observatorio.coleta.base import Contexto, Fonte, gravar_raw, nome_seguro
from observatorio.db import copiar_linhas
from observatorio.execucao import ArquivoRegistrado, registrar_arquivo
from observatorio.http import obter, salvar_bytes
from observatorio.log import obter_logger
from observatorio.transformacao.normalizacao import (
    codigo_municipio,
    converter_numero,
    normalizar_rotulo,
)

log = obter_logger(__name__)

URL_BASE = "https://apisidra.ibge.gov.br/values"


def montar_url(tabela: str, municipios: list[str], caminho: str) -> str:
    return f"{URL_BASE}/t/{tabela}/n6/{','.join(municipios)}/{caminho.strip('/')}"


def tabela_da_url(url: str) -> str:
    m = re.search(r"/t/(\d+)/", url)
    if not m:
        raise ValueError(f"URL do SIDRA sem tabela: {url}")
    return m.group(1)


def interpretar_resposta(dados: list[dict]) -> list[dict]:
    """Converte a resposta do SIDRA em registros {territorio, ano, variavel, classificacao, unidade, valor_bruto}."""
    if not dados:
        return []
    cab = dados[0]
    papeis: dict[str, str] = {}
    classificacoes: list[tuple[str, str, str]] = []   # (chave código, chave nome, rótulo)
    for chave, rotulo in cab.items():
        if not re.fullmatch(r"D\d+C", chave):
            continue
        r = normalizar_rotulo(rotulo)
        nome = re.sub(r"\s*\(codigo\)$", "", r)
        if nome in ("municipio", "brasil", "unidade da federacao", "grande regiao"):
            papeis["territorio"] = chave
        elif nome == "ano":
            papeis["ano"] = chave
        elif nome == "variavel":
            papeis["variavel"] = chave
        else:
            classificacoes.append((chave, chave[:-1] + "N", re.sub(r"\s*\(Código\)$", "", rotulo)))
    faltam = {"territorio", "ano", "variavel"} - set(papeis)
    if faltam:
        raise ValueError(f"Resposta do SIDRA sem as colunas {sorted(faltam)}; cabeçalho: {cab}")
    registros = []
    for linha in dados[1:]:
        cls = ";".join(f"{rot}={linha.get(kc)}:{linha.get(kn)}" for kc, kn, rot in sorted(classificacoes, key=lambda x: x[2]))
        registros.append({
            "territorio": linha.get(papeis["territorio"]),
            "ano": int(linha.get(papeis["ano"])),
            "variavel": linha.get(papeis["variavel"]),
            "classificacao": cls,
            "unidade": linha.get("MN"),
            "valor_bruto": linha.get("V"),
        })
    return registros


def idade_do_rotulo(rotulo: str) -> int | None:
    """'Menos de 1 ano' -> 0; '1 ano' -> 1; '100 anos ou mais' -> 100; grupos ('0 a 4 anos') -> None."""
    t = normalizar_rotulo(rotulo)
    if re.fullmatch(r"menos de 1 ano( de idade)?", t):
        return 0
    m = re.fullmatch(r"(\d+) anos?( ou mais)?", t)
    return int(m.group(1)) if m else None


class _SidraBase(Fonte):
    chave_config = ""
    versao_transformacao = "2026.09.1"

    def consultas(self) -> list[dict]:
        return config.carregar_yaml("sidra.yaml")[self.chave_config]

    def coletar(self, conn: psycopg.Connection, ctx: Contexto) -> list[ArquivoRegistrado]:
        municipios = config.municipios_de_interesse()
        registrados = []
        for q in self.consultas():
            url = montar_url(q["tabela"], municipios, q["caminho"])
            resp = obter(url)
            dados = resp.json()
            if not isinstance(dados, list) or len(dados) < 2:
                ctx.alertar(f"SIDRA {q['tabela']} ({q['id']}): resposta sem dados")
                continue
            baixado = salvar_bytes(url, resp.content, self.pasta_ano(None) / f"{nome_seguro(q['id'])}_t{q['tabela']}.json",
                                   resp.status_code)
            registrados.append(registrar_arquivo(conn, self.id_fonte, None, baixado, id_execucao=ctx.id_execucao,
                                                 descricao=q["id"]))
        return registrados

    def processar(self, conn: psycopg.Connection, arquivo: ArquivoRegistrado, ctx: Contexto) -> int:
        dados = json.loads(arquivo.caminho.read_text(encoding="utf-8"))
        tabela = tabela_da_url(arquivo.url)
        registros = interpretar_resposta(dados)
        gravar_raw(conn, arquivo.id_arquivo, f"t{tabela}", ((i + 1, d) for i, d in enumerate(dados[1:])))
        linhas, vistos = [], set()
        for r in registros:
            try:
                territorio = codigo_municipio(r["territorio"])
            except ValueError:
                territorio = str(r["territorio"])
            chave = (tabela, r["variavel"], territorio, r["ano"], r["classificacao"])
            if chave in vistos:
                continue
            vistos.add(chave)
            t = converter_numero(r["valor_bruto"], self.id_fonte, casas=4)
            linhas.append((*chave, t.valor, t.texto, r["unidade"], t.status, arquivo.id_arquivo))
        with conn.cursor() as cur:
            cur.execute("DELETE FROM staging.sidra WHERE tabela = %s AND id_arquivo IN "
                        "(SELECT id_arquivo FROM etl.etl_arquivo WHERE id_fonte = %s AND url = %s)",
                        (tabela, self.id_fonte, arquivo.url))
            # Mesma tabela consultada por outra URL (ex.: municípios de interesse mudaram): a nova substitui.
            cur.execute("DELETE FROM staging.sidra WHERE tabela = %s", (tabela,))
        n = copiar_linhas(conn, "staging.sidra",
                          ["tabela", "variavel", "cod_territorio", "ano", "classificacao", "valor", "valor_texto",
                           "unidade", "status_valor", "id_arquivo"], linhas)
        ctx.execucao.linhas_lidas += len(registros)
        ctx.execucao.linhas_gravadas += n
        return n


class Sidra(_SidraBase):
    id_fonte = "sidra_ibge"
    chave_config = "sidra_ibge"
    tabelas_core = ("core.fato_populacao",)

    def carregar_core(self, conn: psycopg.Connection, id_versao: int, ctx: Contexto) -> int:
        cfg = {q["tabela"]: q for q in self.consultas() if q.get("populacao_por_idade")}
        tabelas = list(cfg)
        if not tabelas:
            return 0
        id_num = id_fonte_numerico(conn, self.id_fonte)
        with conn.cursor() as cur:
            cur.execute(
                """SELECT s.tabela, s.cod_territorio, s.ano, s.classificacao, s.valor, s.status_valor, a.data_coleta::date
                   FROM staging.sidra s JOIN etl.etl_arquivo a USING (id_arquivo)
                   JOIN core.dim_territorio t ON t.cod_territorio = s.cod_territorio
                   WHERE s.tabela = ANY(%s)""",
                (tabelas,),
            )
            linhas = []
            for tabela, terr, ano, cls, valor, status, data in cur.fetchall():
                partes = dict(p.split("=", 1) for p in cls.split(";") if "=" in p)
                idade_txt = next((v for k, v in partes.items() if normalizar_rotulo(k) == "idade"), None)
                sexo_txt = next((v for k, v in partes.items() if normalizar_rotulo(k) == "sexo"), None)
                if idade_txt is None:
                    continue
                idade = idade_do_rotulo(idade_txt.split(":", 1)[-1])
                if idade is None:
                    continue
                sexo_nome = normalizar_rotulo(sexo_txt.split(":", 1)[-1]) if sexo_txt else "total"
                sexo = {"total": "T", "homens": "M", "mulheres": "F"}.get(sexo_nome)
                if sexo is None:
                    continue
                linhas.append((ano, terr, sexo, idade, int(valor) if valor is not None else None,
                               cfg[tabela].get("origem", f"ibge_t{tabela}"),
                               cfg[tabela].get("edicao", f"SIDRA tabela {tabela}"),
                               "observado" if status == "observado" else "sem_dado", id_num, id_versao, data))
        return copiar_linhas(conn, "core.fato_populacao",
                             ["ano", "cod_territorio", "sexo", "idade", "populacao", "origem", "edicao", "status_valor",
                              "id_fonte", "id_versao", "data_coleta"], linhas)


class SidraAlfabetizacao(_SidraBase):
    id_fonte = "sidra_alfabetizacao"
    chave_config = "sidra_alfabetizacao"
    tabelas_core = ()

    def carregar_core(self, conn: psycopg.Connection, id_versao: int, ctx: Contexto) -> int:
        return 0  # usado direto do staging no cálculo de G2
