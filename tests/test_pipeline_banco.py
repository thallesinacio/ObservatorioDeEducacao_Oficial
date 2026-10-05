"""Pipeline completo contra um PostgreSQL de teste, com as fixtures no lugar da internet.

Verifica: carga de todas as fontes, valores conhecidos, regra "lacuna nunca vira zero",
idempotência (rodar duas vezes não cria versão nem duplica linhas) e o isolamento do papel
powerbi_leitor (só enxerga o esquema bi).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.banco


@pytest.fixture(scope="module")
def carregado(banco_teste):
    from carga_fixtures import carregar_tudo

    from observatorio.pipeline import migrar

    migrar(offline=True)
    resumo, ind, dq = carregar_tudo()
    return resumo, ind, dq


def _um(sql, params=()):
    from observatorio.db import conectar

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def _contagens():
    return _um("""SELECT (SELECT count(*) FROM core.fato_indicador), (SELECT count(*) FROM core.fato_matricula),
                         (SELECT count(*) FROM etl.versao_dados), (SELECT count(*) FROM etl.etl_arquivo),
                         (SELECT count(*) FROM raw.linha), (SELECT count(*) FROM core.fato_rendimento)""")


def test_todas_as_fontes_carregam(carregado):
    resumo, ind, dq = carregado
    assert not resumo.falha, resumo.falha
    assert ind["linhas"] > 0
    assert dq["erros"] == 0


def test_valores_conhecidos(carregado):
    ind = lambda cod, terr, ano, etapa="total", recorte="total": _um(  # noqa: E731
        """SELECT valor, status_valor FROM bi.fato_indicador WHERE cod_indicador = %s AND cod_territorio = %s
           AND ano = %s AND cod_etapa = %s AND cod_recorte = %s AND co_entidade IS NULL""",
        (cod, terr, ano, etapa, recorte))
    assert float(ind("F1", "2918407", 2023)[0]) == pytest.approx(25.57)
    assert float(ind("F2.siope", "2918407", 2023)[0]) == pytest.approx(9601.27)
    assert float(ind("F3", "2918407", 2023)[0]) == pytest.approx(352481793.69)          # = SIOPE liquidada
    assert float(ind("F4", "2918407", 2023)[0]) == pytest.approx(117558344.15 + 167200041.8)
    assert float(ind("G2", "2918407", 2022)[0]) == pytest.approx(100 * 163658 / 181185, abs=1e-3)
    assert float(ind("E3", "2918407", 2024, "bas")[0]) == pytest.approx(100 * 1843 / 2765, abs=1e-3)
    assert float(ind("B2", "2918407", 2024, "fund")[0]) == pytest.approx(13.9)
    assert float(ind("B1.aprovacao", "2918407", 2015, "fund")[0]) == pytest.approx(84.8)
    assert float(ind("C1", "2918407", 2023, "med", "rede:estadual")[0]) == pytest.approx(3.6)
    # Soma dos QT_MAT_BAS das escolas do recorte (fixture com 8 escolas de Juazeiro).
    assert float(ind("A6", "2918407", 2024, "bas")[0]) == pytest.approx(1552)


def test_lacuna_nunca_vira_zero(carregado):
    valor, status = _um("""SELECT valor, status_valor FROM bi.fato_indicador WHERE cod_indicador = 'C1'
                           AND cod_territorio = '2918407' AND ano = 2021 AND cod_recorte = 'rede:estadual'""")
    assert valor is None and status == "sem_dado"
    assert _um("""SELECT count(*) FROM core.fato_indicador WHERE status_valor IN ('sem_dado', 'nao_se_aplica')
                  AND valor IS NOT NULL""")[0] == 0
    # "--" do INEP (recorte sem a etapa) = não se aplica
    assert _um("""SELECT count(*) FROM core.fato_rendimento WHERE status_valor = 'nao_se_aplica'""")[0] > 0


def test_idempotencia(carregado):
    from carga_fixtures import carregar_tudo

    antes = _contagens()
    resumo, ind, _ = carregar_tudo()
    assert not resumo.falha
    assert ind["nova"] is False
    assert _contagens() == antes


def test_powerbi_leitor_so_enxerga_bi(carregado):
    assert _um("SELECT has_schema_privilege('powerbi_leitor', 'bi', 'USAGE')")[0]
    assert not _um("SELECT has_schema_privilege('powerbi_leitor', 'core', 'USAGE')")[0]
    assert not _um("SELECT has_schema_privilege('powerbi_leitor', 'staging', 'USAGE')")[0]
    assert _um("SELECT has_table_privilege('powerbi_leitor', 'bi.fato_indicador', 'SELECT')")[0]


def test_tudo_comentado(carregado):
    sem = _um("""SELECT count(*), string_agg(n.nspname || '.' || c.relname || '.' || a.attname, ', ')
                 FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace
                 WHERE n.nspname IN ('core', 'bi') AND c.relkind IN ('r', 'v') AND a.attnum > 0 AND NOT a.attisdropped
                   AND c.relname NOT LIKE 'v\\_%%' AND col_description(c.oid, a.attnum) IS NULL""")
    assert sem[0] == 0, sem[1]
    sem_tabela = _um("""SELECT count(*), string_agg(n.nspname || '.' || c.relname, ', ') FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname IN ('core', 'bi') AND c.relkind IN ('r', 'v')
                          AND obj_description(c.oid, 'pg_class') IS NULL""")
    assert sem_tabela[0] == 0, sem_tabela[1]


def test_nenhum_dado_pessoal(carregado):
    colunas = _um("""SELECT string_agg(table_schema || '.' || table_name || '.' || column_name, ', ')
                     FROM information_schema.columns
                     WHERE column_name ~* '(cpf|nome_profissional|no_profissional|nome_aluno|nu_cpf|responsavel)'""")[0]
    assert colunas is None
