-- Eixo A - Acesso e atendimento.
-- Cada bloco grava em tmp_indicador (tabela temporária criada por observatorio.indicadores.calcular).
-- Regras gerais: valor nulo = lacuna (status sem_dado); nunca se troca lacuna por zero.

-- A1 a A4: taxa de atendimento por faixa etária (matrículas da educação básica na faixa ÷ população
-- estimada na faixa). Só entra a soma quando TODAS as variáveis da faixa existem no ano.
WITH faixas(cod_indicador, idade_min, idade_max, variaveis) AS (
  VALUES ('A1', 0, 3, ARRAY['QT_MAT_BAS_0_3']),
         ('A2', 4, 5, ARRAY['QT_MAT_BAS_4_5']),
         ('A3', 6, 14, ARRAY['QT_MAT_BAS_6_10', 'QT_MAT_BAS_11_14']),
         ('A4', 15, 17, ARRAY['QT_MAT_BAS_15_17'])
),
mat AS (
  SELECT f.cod_indicador, c.cod_territorio, c.ano,
         sum(c.valor) AS matriculas,
         count(DISTINCT c.variavel) FILTER (WHERE c.valor IS NOT NULL) AS n_variaveis,
         cardinality(f.variaveis) AS n_esperado,
         max(c.data_coleta) AS data_coleta
  FROM faixas f
  JOIN core.v_contagem_escola c ON c.variavel = ANY (f.variaveis)
  GROUP BY f.cod_indicador, c.cod_territorio, c.ano, f.variaveis
),
pop AS (
  SELECT f.cod_indicador, p.cod_territorio, p.ano,
         sum(p.populacao) AS populacao,
         count(p.populacao) AS n_idades,
         f.idade_max - f.idade_min + 1 AS n_esperado,
         string_agg(DISTINCT p.edicao, '; ') AS edicao,
         max(p.data_coleta) AS data_coleta
  FROM faixas f
  JOIN core.v_fato_populacao p ON p.idade BETWEEN f.idade_min AND f.idade_max
  WHERE p.sexo = 'T' AND p.origem IN ('ripsa_ftp', 'ripsa_tabnet')
  GROUP BY f.cod_indicador, p.cod_territorio, p.ano, f.idade_min, f.idade_max
),
junto AS (
  SELECT m.cod_indicador, m.cod_territorio, m.ano,
         CASE WHEN m.n_variaveis = m.n_esperado THEN m.matriculas END AS numerador,
         CASE WHEN p.n_idades = p.n_esperado THEN p.populacao END AS denominador,
         p.edicao, GREATEST(m.data_coleta, p.data_coleta) AS data_coleta
  FROM mat m
  LEFT JOIN pop p USING (cod_indicador, cod_territorio, ano)
)
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, valor, numerador, denominador, status_valor,
                           data_coleta, referencia, nota)
SELECT cod_indicador, cod_territorio, ano,
       100.0 * numerador / NULLIF(denominador, 0), numerador, denominador,
       CASE WHEN numerador IS NULL OR denominador IS NULL OR denominador = 0 THEN 'sem_dado' ELSE 'estimado' END,
       data_coleta,
       'Matrículas: microdados do Censo Escolar ' || ano || '. População: ' || COALESCE(edicao, 'sem estimativa carregada'),
       concat_ws(' ',
         CASE WHEN denominador IS NULL THEN 'Sem estimativa populacional para o ano.' END,
         CASE WHEN numerador IS NULL THEN 'Variável de matrícula por idade ausente no layout do ano.' END,
         CASE WHEN 100.0 * numerador / NULLIF(denominador, 0) > 100
              THEN 'Acima de 100%: o Censo conta a matrícula no município da escola (fluxo Juazeiro-Petrolina) e a população é estimativa.' END)
FROM junto;

-- A6: matrículas por etapa e recorte de rede x localização (soma das escolas do município).
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_etapa, cod_recorte, valor, numerador, status_valor,
                           data_coleta, referencia)
SELECT 'A6', r.cod_territorio, m.ano, m.cod_etapa, r.cod_recorte,
       sum(m.qt_matriculas), sum(m.qt_matriculas),
       CASE WHEN count(m.qt_matriculas) > 0 THEN 'observado' ELSE 'sem_dado' END,
       max(m.data_coleta), 'Soma de ' || min(m.variavel_origem) || ' (microdados do Censo Escolar)'
FROM core.v_fato_matricula m
JOIN core.v_escola_recorte r USING (ano, co_entidade)
WHERE m.cod_recorte = 'total'
GROUP BY r.cod_territorio, m.ano, m.cod_etapa, r.cod_recorte;

-- A7: escolas em atividade por rede x localização e por porte (matrículas de escolarização, QT_MAT_BAS).
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_recorte, valor, numerador, status_valor, data_coleta,
                           referencia)
SELECT 'A7', r.cod_territorio, e.ano, r.cod_recorte, count(*), count(*), 'observado', max(e.data_coleta),
       'Escolas com TP_SITUACAO_FUNCIONAMENTO = 1'
FROM core.v_escola_ano e
JOIN core.v_escola_recorte r USING (ano, co_entidade)
WHERE e.em_atividade
GROUP BY r.cod_territorio, e.ano, r.cod_recorte;

WITH esc AS (
  SELECT e.ano, e.co_entidade, e.cod_territorio, e.rede, e.eh_publica, e.data_coleta,
         CASE WHEN COALESCE(m.valor, 0) = 0 THEN 'sem_matricula'
              WHEN m.valor <= 50 THEN 'ate_50' WHEN m.valor <= 200 THEN '51_200'
              WHEN m.valor <= 500 THEN '201_500' WHEN m.valor <= 1000 THEN '501_1000'
              ELSE 'mais_1000' END AS porte
  FROM core.v_escola_ano e
  LEFT JOIN core.v_contagem_escola m ON m.ano = e.ano AND m.co_entidade = e.co_entidade AND m.variavel = 'QT_MAT_BAS'
  WHERE e.em_atividade
)
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_recorte, valor, numerador, status_valor, data_coleta,
                           referencia)
SELECT 'A7', esc.cod_territorio, esc.ano, concat_ws('|', 'rede:' || rd.rede, 'porte:' || esc.porte),
       count(*), count(*), 'observado', max(esc.data_coleta),
       'Escolas em atividade por porte (QT_MAT_BAS; vazio = sem matrícula de escolarização)'
FROM esc
CROSS JOIN LATERAL (SELECT DISTINCT x AS rede FROM unnest(ARRAY[NULL, esc.rede,
                     CASE WHEN esc.eh_publica THEN 'publica' END]) AS x) rd
GROUP BY esc.cod_territorio, esc.ano, rd.rede, esc.porte;
