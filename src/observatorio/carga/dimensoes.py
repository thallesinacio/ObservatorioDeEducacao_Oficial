"""Carga das dimensões e tabelas de referência a partir de config/ e das APIs do IBGE."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterable
from pathlib import Path

import psycopg

from observatorio import config
from observatorio.http import obter_json
from observatorio.log import obter_logger
from observatorio.transformacao import recortes as rc
from observatorio.transformacao.normalizacao import regras_ausencia

log = obter_logger(__name__)

URL_LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades"


def carregar_fontes(conn: psycopg.Connection) -> int:
    n = 0
    with conn.cursor() as cur:
        for f in config.fontes():
            cur.execute(
                """INSERT INTO core.dim_fonte (cod_fonte, nome, orgao, prioridade, url, tipo_acesso, formato,
                       periodicidade, anos_disponiveis, licenca, latencia_tipica, observacoes)
                   VALUES (%(id)s, %(nome)s, %(orgao)s, %(prioridade)s, %(pagina_oficial)s, %(tipo_acesso)s,
                       %(formato)s, %(periodicidade)s, %(anos_disponiveis)s, %(licenca)s, %(latencia_tipica)s, %(observacoes)s)
                   ON CONFLICT (cod_fonte) DO UPDATE SET nome = EXCLUDED.nome, orgao = EXCLUDED.orgao,
                       prioridade = EXCLUDED.prioridade, url = EXCLUDED.url, tipo_acesso = EXCLUDED.tipo_acesso,
                       formato = EXCLUDED.formato, periodicidade = EXCLUDED.periodicidade,
                       anos_disponiveis = EXCLUDED.anos_disponiveis, licenca = EXCLUDED.licenca,
                       latencia_tipica = EXCLUDED.latencia_tipica, observacoes = EXCLUDED.observacoes""",
                {k: (str(v).strip() if v is not None else None) for k, v in {
                    "id": f["id"], "nome": f["nome"], "orgao": f.get("orgao"), "prioridade": f.get("prioridade"),
                    "pagina_oficial": f.get("pagina_oficial"), "tipo_acesso": f.get("tipo_acesso"),
                    "formato": f.get("formato"), "periodicidade": f.get("periodicidade"),
                    "anos_disponiveis": f.get("anos_disponiveis"), "licenca": f.get("licenca"),
                    "latencia_tipica": f.get("latencia_tipica"), "observacoes": f.get("observacoes"),
                }.items()},
            )
            n += 1
    return n


def carregar_indicadores(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        for i, ind in enumerate(config.indicadores()):
            cur.execute(
                """INSERT INTO core.dim_indicador (cod_indicador, grupo, eixo, nome, definicao, formula, unidade,
                       polaridade, meta_pme, meta_valor, nivel_agregacao, cod_fonte, eh_calculo_proprio, cobertura,
                       nota_metodologica, ordem)
                   VALUES (%(codigo)s, %(grupo)s, %(eixo)s, %(nome)s, %(definicao)s, %(formula)s, %(unidade)s,
                       %(polaridade)s, %(meta_pme)s, %(meta_valor)s, %(nivel_agregacao)s, %(fonte)s,
                       %(eh_calculo_proprio)s, %(cobertura)s, %(nota_metodologica)s, %(ordem)s)
                   ON CONFLICT (cod_indicador) DO UPDATE SET grupo = EXCLUDED.grupo, eixo = EXCLUDED.eixo,
                       nome = EXCLUDED.nome, definicao = EXCLUDED.definicao, formula = EXCLUDED.formula,
                       unidade = EXCLUDED.unidade, polaridade = EXCLUDED.polaridade, meta_pme = EXCLUDED.meta_pme,
                       meta_valor = EXCLUDED.meta_valor, nivel_agregacao = EXCLUDED.nivel_agregacao,
                       cod_fonte = EXCLUDED.cod_fonte, eh_calculo_proprio = EXCLUDED.eh_calculo_proprio,
                       cobertura = EXCLUDED.cobertura, nota_metodologica = EXCLUDED.nota_metodologica,
                       ordem = EXCLUDED.ordem""",
                {**{k: (str(v).strip() if isinstance(v, str) else v) for k, v in ind.items()}, "ordem": i + 1,
                 "meta_pme": str(ind.get("meta_pme") or "") or None, "meta_valor": ind.get("meta_valor") or None,
                 "nota_metodologica": (ind.get("nota_metodologica") or "").strip() or None},
            )
    return len(config.indicadores())


def carregar_etapas(conn: psycopg.Connection) -> int:
    etapas = config.carregar_yaml("etapas.yaml")["etapas"]
    with conn.cursor() as cur:
        for e in etapas:
            cur.execute(
                """INSERT INTO core.dim_etapa (cod_etapa, nome, faixa_etaria_referencia, agrupamento, ordem)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (cod_etapa) DO UPDATE SET nome = EXCLUDED.nome,
                     faixa_etaria_referencia = EXCLUDED.faixa_etaria_referencia,
                     agrupamento = EXCLUDED.agrupamento, ordem = EXCLUDED.ordem""",
                (e["codigo"], e["nome"], str(e.get("faixa") or "") or None, e["agrupamento"], e["ordem"]),
            )
    return len(etapas)


def _ultima_quarta_de_maio(ano: int) -> dt.date:
    d = dt.date(ano, 5, 31)
    while d.weekday() != 2:
        d -= dt.timedelta(days=1)
    return d


def carregar_tempo(conn: psycopg.Connection, inicio: int = 2000, fim: int = 2035) -> int:
    with conn.cursor() as cur:
        for ano in range(inicio, fim + 1):
            cur.execute(
                """INSERT INTO core.dim_tempo (ano, data_referencia_censo, rotulo, eh_ano_pme)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (ano) DO UPDATE SET data_referencia_censo = EXCLUDED.data_referencia_censo,
                     rotulo = EXCLUDED.rotulo, eh_ano_pme = EXCLUDED.eh_ano_pme""",
                (ano, _ultima_quarta_de_maio(ano), str(ano), 2015 <= ano <= 2025),
            )
    return fim - inicio + 1


def garantir_recortes(conn: psycopg.Connection, codigos: Iterable[str]) -> int:
    """Insere em core.dim_recorte os códigos que ainda não existem."""
    codigos = sorted(set(codigos))
    if not codigos:
        return 0
    with conn.cursor() as cur:
        for c in codigos:
            d = rc.decompor(c)
            cur.execute(
                """INSERT INTO core.dim_recorte (cod_recorte, rotulo, rede, localizacao, tipo_outro, valor_outro, ordem)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (cod_recorte) DO NOTHING""",
                (c, rc.rotulo(c), d["rede"], d["localizacao"], d["tipo_outro"], d["valor_outro"], rc.ordem(c)),
            )
    return len(codigos)


def carregar_recortes_base(conn: psycopg.Connection) -> int:
    eixos = config.carregar_yaml("recortes.yaml")["eixos"]
    codigos = {rc.TOTAL}
    redes = list(eixos["rede"]["valores"])
    locs = list(eixos["localizacao"]["valores"])
    for r in [None, *redes]:
        for loc in [None, *locs]:
            codigos.add(rc.montar(r, loc))
    for tipo, eixo in eixos.items():
        if tipo in ("rede", "localizacao"):
            continue
        for v in (eixo.get("valores") or {}):
            codigos.add(rc.montar(outro=f"{tipo}:{v}"))
    return garantir_recortes(conn, codigos)


def carregar_regras_ausencia(conn: psycopg.Connection) -> int:
    n = 0
    fontes = config.carregar_yaml("regras_ausencia.yaml").get("fontes", {})
    with conn.cursor() as cur:
        cur.execute("DELETE FROM etl.regra_ausencia")
        for id_fonte in fontes:
            for marcador, regra in regras_ausencia(id_fonte).items():
                cur.execute(
                    "INSERT INTO etl.regra_ausencia (id_fonte, marcador, status_valor, descricao) VALUES (%s, %s, %s, %s)",
                    (id_fonte, marcador, regra.status + (f" (valor {regra.valor})" if regra.valor is not None else ""),
                     regra.descricao),
                )
                n += 1
    return n


def carregar_de_para_base(conn: psycopg.Connection) -> int:
    """Conciliações conhecidas entre fontes (nomes de rede e localização)."""
    itens = [
        ("dependencia", "Particular", "privada", "INEP (rendimento até 2018)", "Planilhas antigas chamam a rede privada de Particular"),
        ("dependencia", "Privada", "privada", "INEP", None),
        ("dependencia", "Pública", "publica", "INEP", "Federal + estadual + municipal"),
        ("dependencia", "Municipal", "municipal", "INEP", None),
        ("dependencia", "Estadual", "estadual", "INEP", None),
        ("dependencia", "Federal", "federal", "INEP", None),
        ("dependencia", "Total", "", "INEP", "Todas as redes (sem recorte)"),
        ("localizacao", "Urbana", "urbana", "INEP", None),
        ("localizacao", "Rural", "rural", "INEP", None),
        ("localizacao", "Total", "", "INEP", "Todas as localizações (sem recorte)"),
    ]
    with conn.cursor() as cur:
        for dominio, origem, canonico, fonte, obs in itens:
            cur.execute(
                """INSERT INTO etl.de_para (dominio, valor_origem, valor_canonico, fonte, observacao)
                   VALUES (%s, %s, %s, %s, %s) ON CONFLICT (dominio, valor_origem) DO NOTHING""",
                (dominio, origem, canonico, fonte, obs),
            )
    return len(itens)


# ------------------------------------------------------------------ territórios

def _caminho_cache_localidades() -> Path:
    return config.configuracoes().caminho_raw / "ibge_localidades"


def buscar_localidades(offline: bool = False) -> tuple[list[dict], list[dict]]:
    """Nomes oficiais de municípios e UFs pela API de localidades do IBGE (com cache em disco)."""
    pasta = _caminho_cache_localidades()
    arq_mun, arq_uf = pasta / "municipios.json", pasta / "estados.json"
    municipios = config.municipios_de_interesse()
    ufs = sorted(set(config.ufs_comparacao()) | {m[:2] for m in municipios})
    if not offline:
        try:
            mun = obter_json(f"{URL_LOCALIDADES}/municipios/{'|'.join(municipios)}")
            if isinstance(mun, dict):
                mun = [mun]
            est = obter_json(f"{URL_LOCALIDADES}/estados/{'|'.join(ufs)}")
            if isinstance(est, dict):
                est = [est]
            pasta.mkdir(parents=True, exist_ok=True)
            arq_mun.write_text(json.dumps(mun, ensure_ascii=False, indent=1), encoding="utf-8")
            arq_uf.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")
            return mun, est
        except Exception as e:  # sem rede: usa o cache
            log.warning("API de localidades do IBGE indisponível; usando cache local", erro=str(e))
    if arq_mun.exists() and arq_uf.exists():
        return json.loads(arq_mun.read_text(encoding="utf-8")), json.loads(arq_uf.read_text(encoding="utf-8"))
    raise RuntimeError(
        "Não foi possível obter os nomes dos territórios: sem acesso à API de localidades do IBGE e sem cache em "
        f"{pasta}. Rode com internet uma vez."
    )


def carregar_territorios(conn: psycopg.Connection, offline: bool = False,
                         municipios_json: list[dict] | None = None, estados_json: list[dict] | None = None) -> int:
    if municipios_json is None or estados_json is None:
        municipios_json, estados_json = buscar_localidades(offline)
    alvo = set(config.territorios_alvo())
    comparacao = set(config.territorios_comparacao())
    ufs_comp = set(config.ufs_comparacao())
    n = 0
    with conn.cursor() as cur:
        if config.incluir_brasil():
            cur.execute(
                """INSERT INTO core.dim_territorio (cod_territorio, nome, nivel, eh_alvo, eh_comparacao)
                   VALUES ('1', 'Brasil', 'brasil', false, true)
                   ON CONFLICT (cod_territorio) DO UPDATE SET nome = EXCLUDED.nome, eh_comparacao = true"""
            )
            n += 1
        for uf in estados_json:
            cod = str(uf["id"])
            cur.execute(
                """INSERT INTO core.dim_territorio (cod_territorio, nome, nivel, sg_uf, cod_uf, eh_alvo, eh_comparacao)
                   VALUES (%s, %s, 'uf', %s, %s, false, %s)
                   ON CONFLICT (cod_territorio) DO UPDATE SET nome = EXCLUDED.nome, sg_uf = EXCLUDED.sg_uf,
                     eh_comparacao = EXCLUDED.eh_comparacao""",
                (cod, uf["nome"], uf["sigla"], cod, cod in ufs_comp),
            )
            n += 1
        for m in municipios_json:
            cod = str(m["id"])
            uf = (m.get("microrregiao") or {}).get("mesorregiao", {}).get("UF") or \
                 (m.get("regiao-imediata") or {}).get("regiao-intermediaria", {}).get("UF")
            cur.execute(
                """INSERT INTO core.dim_territorio (cod_territorio, nome, nivel, sg_uf, cod_uf, cod_municipio_6, eh_alvo, eh_comparacao)
                   VALUES (%s, %s, 'municipio', %s, %s, %s, %s, %s)
                   ON CONFLICT (cod_territorio) DO UPDATE SET nome = EXCLUDED.nome, sg_uf = EXCLUDED.sg_uf,
                     cod_uf = EXCLUDED.cod_uf, cod_municipio_6 = EXCLUDED.cod_municipio_6,
                     eh_alvo = EXCLUDED.eh_alvo, eh_comparacao = EXCLUDED.eh_comparacao""",
                (cod, m["nome"], uf["sigla"] if uf else None, str(uf["id"]) if uf else cod[:2], cod[:6],
                 cod in alvo, cod in comparacao),
            )
            n += 1
        # Município que saiu da configuração deixa de ser alvo/comparação (os dados antigos ficam no histórico).
        cur.execute("""UPDATE core.dim_territorio SET eh_alvo = false, eh_comparacao = false
                       WHERE nivel = 'municipio' AND NOT (cod_territorio = ANY(%s))""",
                    ([str(m["id"]) for m in municipios_json],))
    return n


def carregar_referencias(conn: psycopg.Connection, offline: bool = False) -> dict[str, int]:
    """Tudo o que vem de config/: fontes, indicadores, etapas, anos, recortes, regras e territórios."""
    resumo = {
        "fontes": carregar_fontes(conn),
        "indicadores": carregar_indicadores(conn),
        "etapas": carregar_etapas(conn),
        "anos": carregar_tempo(conn),
        "recortes": carregar_recortes_base(conn),
        "regras_ausencia": carregar_regras_ausencia(conn),
        "de_para": carregar_de_para_base(conn),
        "territorios": carregar_territorios(conn, offline=offline),
    }
    conn.commit()
    return resumo


def id_fonte_numerico(conn: psycopg.Connection, cod_fonte: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id_fonte FROM core.dim_fonte WHERE cod_fonte = %s", (cod_fonte,))
        r = cur.fetchone()
    if not r:
        raise KeyError(f"Fonte {cod_fonte} não está em core.dim_fonte (rode db migrar)")
    return r[0]
