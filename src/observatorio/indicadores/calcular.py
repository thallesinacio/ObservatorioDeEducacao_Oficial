"""Cálculo dos indicadores (core.fato_indicador).

O cálculo é versionado como uma fonte à parte ("calculo_observatorio"): a assinatura da versão
junta as versões vigentes de todas as fontes e a versão do método (config/projeto.yaml,
metodologia.versao_calculo_indicadores). Se nada mudou, a versão vigente é mantida e nada é
recalculado; se algo mudou, uma nova versão é gravada e passa a ser a vigente — a anterior fica
no histórico.

Os indicadores são escritos em SQL (sql/indicadores/*.sql, executados em ordem alfabética) e
gravam numa tabela temporária; esta função completa as colunas comuns (fonte, cálculo próprio,
versão), aplica a regra "lacuna nunca vira zero" e grava no core numa única transação.
"""

from __future__ import annotations

from decimal import Decimal

import psycopg

from observatorio import config
from observatorio.carga.dimensoes import garantir_recortes
from observatorio.coleta import ORDEM_PIPELINE
from observatorio.db import DIR_SQL, conectar
from observatorio.execucao import Execucao, obter_versao, tornar_vigente, versao_vigente
from observatorio.log import obter_logger

log = obter_logger(__name__)

ID_FONTE = "calculo_observatorio"

TMP = """
CREATE TEMP TABLE tmp_indicador (
  cod_indicador   TEXT NOT NULL,
  cod_territorio  TEXT NOT NULL,
  co_entidade     CHAR(8),
  ano             SMALLINT NOT NULL,
  cod_etapa       TEXT NOT NULL DEFAULT 'total',
  cod_recorte     TEXT NOT NULL DEFAULT 'total',
  valor           NUMERIC,
  numerador       NUMERIC,
  denominador     NUMERIC,
  status_valor    TEXT NOT NULL,
  data_coleta     DATE,
  referencia      TEXT,
  nota            TEXT,
  cod_fonte_valor TEXT
) ON COMMIT DROP
"""


def _substituicoes() -> dict[str, str]:
    s = config.carregar_yaml("siope.yaml")["indicadores"]
    return {"{{siope_mde}}": str(int(s["mde_percentual"])),
            "{{siope_investimento}}": str(int(s["investimento_por_aluno"]))}


def _sql_indicadores() -> list[tuple[str, str]]:
    subs = _substituicoes()
    saida = []
    for arq in sorted((DIR_SQL / "indicadores").glob("*.sql")):
        texto = arq.read_text(encoding="utf-8")
        for k, v in subs.items():
            texto = texto.replace(k, v)
        saida.append((arq.name, texto))
    return saida


def _f4_fundeb(conn: psycopg.Connection) -> int:
    """F4: soma das rubricas de receita do Fundeb (códigos por período em config/siope.yaml)."""
    cfg = config.carregar_yaml("siope.yaml")["fundeb"]
    with conn.cursor() as cur:
        cur.execute("""SELECT s.ano, s.cod_territorio, s.cod_rubrica, s.coluna, s.valor, a.data_coleta::date
                       FROM staging.siope_receita s JOIN etl.etl_arquivo a USING (id_arquivo)""")
        linhas = cur.fetchall()
    por_chave: dict[tuple[int, str], dict] = {}
    for ano, terr, rubrica, coluna, valor, data in linhas:
        d = por_chave.setdefault((ano, terr), {"valores": {}, "data": data})
        if coluna == cfg["coluna"]:
            d["valores"].setdefault(rubrica, []).append(valor)
    n = 0
    with conn.cursor() as cur:
        for (ano, terr), d in sorted(por_chave.items()):
            periodo = next((p for p in cfg["por_periodo"] if p["anos"][0] <= ano <= p["anos"][1]), None)
            if periodo is None:
                valor, status = None, "sem_dado"
                nota = "Códigos das rubricas do Fundeb não verificados para este ano (config/siope.yaml)."
                ref = "SIOPE Receita"
            else:
                faltando = [c for c in periodo["codigos"] if c not in d["valores"]]
                partes = [v for c in periodo["codigos"] for v in d["valores"].get(c, []) if v is not None]
                valor = sum(partes, Decimal(0)) if partes and not faltando else None
                status = "observado" if valor is not None else "sem_dado"
                nota = (f"Rubrica(s) {', '.join(faltando)} não declarada(s) no ano." if faltando else None)
                ref = f"SIOPE Receita, {cfg['coluna']}: {', '.join(periodo['codigos'])}. {periodo.get('nota', '')}".strip()
            cur.execute(
                """INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, valor, status_valor, data_coleta,
                       referencia, nota) VALUES ('F4', %s, %s, %s, %s, %s, %s, %s)""",
                (terr, ano, valor, status, d["data"], ref, nota))
            n += 1
    return n


def assinatura_entradas(conn: psycopg.Connection) -> list[str]:
    partes = [f"{f}={versao_vigente(conn, f)}" for f in sorted(ORDEM_PIPELINE)]
    partes.append(f"metodo={config.versao_calculo_indicadores()}")
    for nome, texto in _sql_indicadores():
        import hashlib
        partes.append(f"sql:{nome}={hashlib.sha256(texto.encode('utf-8')).hexdigest()}")
    return partes


def calcular_indicadores(forcar: bool = False) -> dict:
    with Execucao("indicadores", ID_FONTE, f"forcar={forcar}") as ex, conectar() as conn:
        partes = assinatura_entradas(conn)
        id_versao, nova = obter_versao(conn, ID_FONTE, partes,
                                       f"Cálculo {config.versao_calculo_indicadores()}", ex.id_execucao)
        if not nova and not forcar:
            tornar_vigente(conn, ID_FONTE, id_versao)
            conn.commit()
            ex.ignorar(f"Entradas e método sem mudança: versão {id_versao} mantida")
            return {"versao": id_versao, "nova": False, "linhas": 0}
        with conn.cursor() as cur:
            cur.execute("DELETE FROM core.fato_indicador WHERE id_versao = %s", (id_versao,))
            cur.execute(TMP)
            for nome, texto in _sql_indicadores():
                cur.execute(texto)
                log.info("Indicadores calculados", arquivo=nome)
        _f4_fundeb(conn)
        with conn.cursor() as cur:
            # Linhas repetidas = erro de definição: a execução falha em vez de gravar algo ambíguo.
            cur.execute("""SELECT cod_indicador, cod_territorio, co_entidade, ano, cod_etapa, cod_recorte, count(*)
                           FROM tmp_indicador GROUP BY 1, 2, 3, 4, 5, 6 HAVING count(*) > 1 LIMIT 5""")
            dup = cur.fetchall()
            if dup:
                raise RuntimeError(f"Indicadores com linhas repetidas (erro de definição): {dup}")
            cur.execute("""SELECT DISTINCT t.cod_indicador FROM tmp_indicador t
                           LEFT JOIN core.dim_indicador i USING (cod_indicador) WHERE i.cod_indicador IS NULL""")
            faltam = [r[0] for r in cur.fetchall()]
            if faltam:
                raise RuntimeError(f"Indicadores calculados sem cadastro em config/indicadores.yaml: {faltam}")
            cur.execute("SELECT DISTINCT cod_recorte FROM tmp_indicador")
            garantir_recortes(conn, [r[0] for r in cur.fetchall()])
            cur.execute(
                """UPDATE core.dim_recorte r SET rotulo = 'Subfunção: ' || f.rubrica_nome
                   FROM (SELECT DISTINCT ON (rubrica_codigo) rubrica_codigo, rubrica_nome FROM core.v_fato_financiamento
                         WHERE demonstrativo = 'DCA-Anexo I-E' ORDER BY rubrica_codigo, ano DESC) f
                   WHERE r.cod_recorte = 'subfuncao:' || f.rubrica_codigo""")
            cur.execute(
                """INSERT INTO core.fato_indicador (cod_indicador, cod_territorio, co_entidade, ano, cod_etapa, cod_recorte,
                       valor, numerador, denominador, status_valor, eh_calculo_proprio, id_fonte, data_coleta, id_versao,
                       referencia, nota)
                   SELECT t.cod_indicador, t.cod_territorio, t.co_entidade, t.ano, t.cod_etapa, t.cod_recorte,
                          CASE WHEN t.status_valor IN ('sem_dado', 'nao_se_aplica') THEN NULL ELSE round(t.valor, 4) END,
                          round(t.numerador, 4), round(t.denominador, 4),
                          CASE WHEN t.status_valor = 'nao_se_aplica' THEN 'nao_se_aplica'
                               WHEN t.valor IS NULL THEN 'sem_dado' ELSE t.status_valor END,
                          i.eh_calculo_proprio, f.id_fonte, COALESCE(t.data_coleta, current_date), %s,
                          t.referencia, NULLIF(t.nota, '')
                   FROM tmp_indicador t
                   JOIN core.dim_indicador i USING (cod_indicador)
                   JOIN core.dim_fonte f ON f.cod_fonte = COALESCE(t.cod_fonte_valor, i.cod_fonte)
                   JOIN core.dim_territorio USING (cod_territorio)
                   JOIN core.dim_tempo USING (ano)
                   JOIN core.dim_etapa USING (cod_etapa)""",
                (id_versao,))
            n = cur.rowcount
            cur.execute("SELECT count(*) FROM tmp_indicador")
            n_tmp = cur.fetchone()[0]
        if n != n_tmp:
            ex.alertar(f"{n_tmp - n} linha(s) de indicador descartada(s) por território, ano ou etapa fora das dimensões")
        tornar_vigente(conn, ID_FONTE, id_versao)
        conn.commit()
        ex.linhas_gravadas = n
        log.info("Indicadores gravados", versao=id_versao, linhas=n)
        return {"versao": id_versao, "nova": nova, "linhas": n}
