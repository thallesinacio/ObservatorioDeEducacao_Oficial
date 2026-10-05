"""Testes de qualidade do dado, gravados em etl.dq_resultado.

Severidades: "erro" (o dado está errado ou ambíguo), "alerta" (merece conferência, mas não
impede a publicação) e "info". Nenhum teste altera dados: só registra.

Testes:
* unicidade das chaves naturais nos fatos vigentes;
* faixa válida (0 a 100) dos percentuais — taxas de atendimento acima de 100% são só alerta,
  porque o Censo conta a matrícula no município da escola;
* coerência de status: valor presente com status de lacuna (e vice-versa);
* soma das partes (creche + pré-escola = infantil; anos iniciais + finais = fundamental;
  feminino + masculino = 100%);
* variação anual acima do limiar (config/projeto.yaml);
* conferência cruzada microdados do Censo x Sinopse (matrículas) e SIOPE x SICONFI (despesa
  liquidada em educação);
* divergência entre rótulo e código de coluna nas planilhas do INEP (registrada na transformação);
* cobertura: indicador automático sem nenhum valor para o município-alvo.
"""

from __future__ import annotations

from dataclasses import dataclass

import psycopg

from observatorio import config
from observatorio.db import conectar
from observatorio.execucao import Execucao
from observatorio.log import obter_logger

log = obter_logger(__name__)


@dataclass
class Resultado:
    teste: str
    tabela: str
    coluna: str | None
    severidade: str
    ocorrencias: int
    detalhe: str

    @property
    def resultado(self) -> str:
        return "falha" if self.ocorrencias else "ok"


def _amostra(linhas: list[tuple], n: int = 5) -> str:
    return "; ".join(" | ".join("" if v is None else str(v) for v in l) for l in linhas[:n])


def _consulta(conn: psycopg.Connection, sql: str, params: tuple = ()) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _teste(conn, teste, tabela, coluna, severidade, sql, explicacao, params=()) -> Resultado:
    linhas = _consulta(conn, sql, params)
    detalhe = explicacao if not linhas else f"{explicacao} Exemplos: {_amostra(linhas)}"
    return Resultado(teste, tabela, coluna, severidade, len(linhas), detalhe)


def testes_unicidade(conn) -> list[Resultado]:
    chaves = {
        "core.v_fato_indicador": "cod_indicador, cod_territorio, co_entidade, ano, cod_etapa, cod_recorte",
        "core.v_fato_matricula": "ano, co_entidade, cod_etapa, cod_recorte",
        "core.v_fato_rendimento": "ano, cod_territorio, co_entidade, cod_etapa, cod_recorte, medida",
        "core.v_fato_populacao": "ano, cod_territorio, sexo, idade, origem",
    }
    return [
        _teste(conn, "unicidade", tabela, chave, "erro",
               f"SELECT {chave}, count(*) FROM {tabela} GROUP BY {chave} HAVING count(*) > 1 LIMIT 50",
               f"Chave natural ({chave}) repetida na versão vigente.")
        for tabela, chave in chaves.items()
    ]


def testes_faixa(conn) -> list[Resultado]:
    return [
        _teste(conn, "faixa_percentual", "core.fato_indicador", "valor", "erro",
               """SELECT f.cod_indicador, f.cod_territorio, f.co_entidade, f.ano, f.cod_etapa, f.cod_recorte, f.valor
                  FROM core.v_fato_indicador f JOIN core.dim_indicador i USING (cod_indicador)
                  WHERE i.unidade = '%%' AND f.cod_indicador NOT IN ('A1', 'A2', 'A3', 'A4')
                    AND (f.valor < 0 OR f.valor > 100) LIMIT 50""",
               "Percentual fora de 0 a 100."),
        _teste(conn, "atendimento_acima_de_100", "core.fato_indicador", "valor", "alerta",
               """SELECT cod_indicador, cod_territorio, ano, valor FROM core.v_fato_indicador
                  WHERE cod_indicador IN ('A1', 'A2', 'A3', 'A4') AND valor > 100 LIMIT 50""",
               "Taxa de atendimento acima de 100%: esperado quando alunos de outros municípios estudam aqui "
               "(Censo conta no município da escola); conferir antes de publicar."),
        _teste(conn, "valor_negativo", "core.fato_indicador", "valor", "erro",
               """SELECT cod_indicador, cod_territorio, ano, valor FROM core.v_fato_indicador
                  WHERE valor < 0 AND cod_indicador NOT LIKE 'F%%' LIMIT 50""",
               "Valor negativo em indicador que só admite valores positivos."),
    ]


def testes_status(conn) -> list[Resultado]:
    return [
        _teste(conn, "status_coerente", "core.fato_indicador", "status_valor", "erro",
               """SELECT cod_indicador, cod_territorio, ano, status_valor, valor FROM core.v_fato_indicador
                  WHERE (status_valor IN ('observado', 'estimado', 'proxy_estadual') AND valor IS NULL)
                     OR (status_valor IN ('sem_dado', 'nao_se_aplica') AND valor IS NOT NULL) LIMIT 50""",
               "Lacuna com valor ou valor observado sem número."),
    ]


def testes_soma_partes(conn) -> list[Resultado]:
    return [
        _teste(conn, "soma_partes_etapas", "core.fato_indicador", "A6", "alerta",
               """WITH a AS (SELECT cod_territorio, ano, cod_recorte, cod_etapa, valor FROM core.v_fato_indicador
                             WHERE cod_indicador = 'A6'),
                       regras(total, parte1, parte2) AS (VALUES ('inf', 'inf_cre', 'inf_pre'), ('fund', 'fund_ai', 'fund_af'))
                  SELECT r.total, t.cod_territorio, t.ano, t.cod_recorte, t.valor, p1.valor + p2.valor
                  FROM regras r
                  JOIN a t ON t.cod_etapa = r.total
                  JOIN a p1 ON p1.cod_etapa = r.parte1 AND (p1.cod_territorio, p1.ano, p1.cod_recorte) = (t.cod_territorio, t.ano, t.cod_recorte)
                  JOIN a p2 ON p2.cod_etapa = r.parte2 AND (p2.cod_territorio, p2.ano, p2.cod_recorte) = (t.cod_territorio, t.ano, t.cod_recorte)
                  WHERE t.valor <> p1.valor + p2.valor LIMIT 50""",
               "Total da etapa diferente da soma das partes (creche + pré-escola; anos iniciais + finais)."),
        _teste(conn, "soma_partes_redes", "core.fato_indicador", "A6", "alerta",
               """WITH a AS (SELECT cod_territorio, ano, cod_etapa, cod_recorte, valor FROM core.v_fato_indicador
                             WHERE cod_indicador = 'A6')
                  SELECT t.cod_territorio, t.ano, t.cod_etapa, t.valor, sum(p.valor)
                  FROM a t JOIN a p ON (p.cod_territorio, p.ano, p.cod_etapa) = (t.cod_territorio, t.ano, t.cod_etapa)
                       AND p.cod_recorte IN ('rede:federal', 'rede:estadual', 'rede:municipal', 'rede:privada')
                  WHERE t.cod_recorte = 'total'
                  GROUP BY t.cod_territorio, t.ano, t.cod_etapa, t.valor
                  HAVING t.valor <> sum(p.valor) LIMIT 50""",
               "Matrículas do município diferentes da soma das quatro redes."),
        _teste(conn, "soma_partes_sexo", "core.fato_indicador", "D7", "alerta",
               """SELECT cod_territorio, ano, regexp_replace(cod_recorte, '\\|?sexo:(feminino|masculino)', '') AS base,
                         sum(valor)
                  FROM core.v_fato_indicador WHERE cod_indicador = 'D7' AND cod_recorte ~ 'sexo:(feminino|masculino)'
                  GROUP BY 1, 2, 3
                  HAVING count(*) = 2 AND abs(sum(valor) - 100) > 0.5 LIMIT 50""",
               "Feminino + masculino diferente de 100% das matrículas."),
    ]


def testes_variacao(conn) -> list[Resultado]:
    lim_pp = float(config.opcao_qualidade("limiar_variacao_percentual_pp", 15.0))
    lim_rel = float(config.opcao_qualidade("limiar_variacao_relativa", 0.30))
    return [
        _teste(conn, "variacao_anual", "core.fato_indicador", "valor", "alerta",
               """WITH s AS (
                    SELECT f.cod_indicador, f.cod_territorio, f.cod_etapa, f.cod_recorte, f.ano, f.valor, i.unidade,
                           lag(f.valor) OVER w AS anterior, lag(f.ano) OVER w AS ano_anterior
                    FROM core.v_fato_indicador f JOIN core.dim_indicador i USING (cod_indicador)
                    JOIN core.dim_territorio t USING (cod_territorio)
                    WHERE f.co_entidade IS NULL AND t.eh_alvo AND f.valor IS NOT NULL
                    WINDOW w AS (PARTITION BY f.cod_indicador, f.cod_territorio, f.cod_etapa, f.cod_recorte ORDER BY f.ano))
                  SELECT cod_indicador, cod_territorio, cod_etapa, cod_recorte, ano_anterior, anterior, ano, valor
                  FROM s
                  WHERE anterior IS NOT NULL AND ano = ano_anterior + 1 AND (
                        (unidade = '%%' AND abs(valor - anterior) > %s)
                     OR (unidade <> '%%' AND anterior <> 0 AND abs(valor - anterior) / abs(anterior) > %s))
                  ORDER BY cod_indicador, ano LIMIT 200""",
               f"Variação de um ano para o outro acima de {lim_pp} p.p. (percentuais) ou {lim_rel:.0%} (demais). "
               "Pode ser real (ex.: pandemia, mudança de metodologia) — conferir.",
               (lim_pp, lim_rel)),
    ]


def testes_conferencia(conn) -> list[Resultado]:
    tol = float(config.opcao_qualidade("tolerancia_conferencia_percentual", 1.0))
    return [
        _teste(conn, "conferencia_censo_sinopse", "core.fato_indicador", "A6", "alerta",
               """SELECT a.cod_territorio, a.ano, a.cod_etapa, a.valor AS microdados, s.valor AS sinopse
                  FROM core.v_fato_indicador a
                  JOIN staging.inep_indicador s ON s.id_fonte = 'sinopse_estatistica' AND s.medida = 'matriculas'
                       AND s.cod_territorio = a.cod_territorio AND s.ano = a.ano AND s.cod_etapa = a.cod_etapa
                  WHERE a.cod_indicador = 'A6' AND a.cod_recorte = 'total' AND s.valor IS NOT NULL
                    AND abs(a.valor - s.valor) > %s / 100.0 * s.valor LIMIT 50""",
               f"Matrículas somadas dos microdados diferentes da Sinopse Estatística em mais de {tol}%.", (tol,)),
        _teste(conn, "conferencia_siope_siconfi", "core.fato_financiamento", "valor", "alerta",
               """SELECT s.cod_territorio, s.ano, s.valor AS siope_liquidada, d.valor AS dca_liquidada
                  FROM core.v_fato_financiamento s
                  JOIN core.v_fato_financiamento d ON d.cod_territorio = s.cod_territorio AND d.ano = s.ano
                       AND d.demonstrativo = 'DCA-Anexo I-E' AND d.rubrica_codigo = '12'
                       AND d.coluna = 'Despesas Liquidadas'
                  WHERE s.demonstrativo = 'SIOPE-Dados-Gerais' AND s.rubrica_codigo = 'VL_DESP_LIQU_EDU'
                    AND abs(s.valor - d.valor) > %s / 100.0 * d.valor LIMIT 50""",
               f"Despesa liquidada em educação declarada ao SIOPE diferente da DCA (SICONFI) em mais de {tol}%.",
               (tol,)),
    ]


def testes_divergencia_rotulo(conn) -> list[Resultado]:
    return [
        _teste(conn, "rotulo_x_codigo", "etl.etl_execucao", "mensagem_erro", "alerta",
               """SELECT DISTINCT ON (id_fonte) id_fonte, inicio::date, left(mensagem_erro, 300)
                  FROM etl.etl_execucao
                  WHERE job = 'transformar' AND mensagem_erro ILIKE '%%rótulo e código divergentes%%'
                  ORDER BY id_fonte, inicio DESC""",
               "Planilha do INEP com coluna cujo rótulo não corresponde ao código de variável (vale o código)."),
    ]


def testes_cobertura(conn) -> list[Resultado]:
    return [
        _teste(conn, "cobertura_indicador", "core.fato_indicador", "cod_indicador", "alerta",
               """SELECT i.cod_indicador, i.nome FROM core.dim_indicador i
                  WHERE i.cobertura = 'automatica' AND NOT EXISTS (
                    SELECT 1 FROM core.v_fato_indicador f JOIN core.dim_territorio t USING (cod_territorio)
                    WHERE f.cod_indicador = i.cod_indicador AND t.eh_alvo AND f.valor IS NOT NULL)
                  ORDER BY i.ordem""",
               "Indicador de cobertura automática sem nenhum valor para o município-alvo (fonte não coletada?)."),
    ]


def executar_testes() -> dict:
    with Execucao("qualidade", None, None) as ex, conectar() as conn:
        resultados: list[Resultado] = []
        for grupo in (testes_unicidade, testes_faixa, testes_status, testes_soma_partes, testes_variacao,
                      testes_conferencia, testes_divergencia_rotulo, testes_cobertura):
            resultados += grupo(conn)
        with conn.cursor() as cur:
            for r in resultados:
                cur.execute(
                    """INSERT INTO etl.dq_resultado (id_execucao, teste, tabela, coluna, severidade, resultado, ocorrencias,
                           detalhe) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (ex.id_execucao, r.teste, r.tabela, r.coluna, r.severidade, r.resultado, r.ocorrencias, r.detalhe))
        conn.commit()
        erros = sum(1 for r in resultados if r.resultado == "falha" and r.severidade == "erro")
        alertas = sum(1 for r in resultados if r.resultado == "falha" and r.severidade == "alerta")
        for r in resultados:
            if r.resultado == "falha":
                (ex.alertar if r.severidade != "info" else log.info)(f"[{r.severidade}] {r.teste} ({r.coluna}): "
                                                                      f"{r.ocorrencias} ocorrência(s)")
        ex.linhas_gravadas = len(resultados)
        return {"testes": len(resultados), "erros": erros, "alertas": alertas}
