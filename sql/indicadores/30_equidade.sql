-- Eixo D - Equidade, jornada e inclusão (cálculos sobre os microdados do Censo Escolar).
-- Base comum: contagens por escola (core.v_contagem_escola) somadas por recorte de rede x localização
-- (core.v_escola_recorte), só escolas em atividade. Uma soma só existe se ao menos uma escola tem a
-- variável preenchida no ano; variável ausente no layout = sem_dado.

CREATE TEMP TABLE tmp_soma ON COMMIT DROP AS
SELECT r.cod_territorio, c.ano, r.cod_recorte, c.variavel,
       sum(c.valor) AS soma, count(c.valor) AS n, max(c.data_coleta) AS data_coleta
FROM core.v_contagem_escola c
JOIN core.v_escola_recorte r USING (ano, co_entidade)
JOIN core.v_escola_ano e USING (ano, co_entidade)
WHERE e.em_atividade
  AND c.variavel IN ('QT_MAT_INF', 'QT_MAT_FUND', 'QT_MAT_MED', 'QT_MAT_INF_INT', 'QT_MAT_FUND_INT', 'QT_MAT_MED_INT',
                     'QT_MAT_ESP', 'QT_MAT_ESP_CC', 'QT_MAT_EJA', 'QT_MAT_EJA_FUND', 'QT_MAT_EJA_MED',
                     'QT_MAT_EJA_FUND_FIC', 'QT_MAT_EJA_MED_FIC', 'QT_MAT_EJA_MED_TEC', 'QT_MAT_BAS',
                     'QT_MAT_BAS_FEM', 'QT_MAT_BAS_MASC', 'QT_MAT_BAS_BRANCA', 'QT_MAT_BAS_PRETA', 'QT_MAT_BAS_PARDA',
                     'QT_MAT_BAS_AMARELA', 'QT_MAT_BAS_INDIGENA', 'QT_MAT_BAS_ND', 'QT_DOC_BAS')
GROUP BY r.cod_territorio, c.ano, r.cod_recorte, c.variavel;

CREATE TEMP TABLE tmp_piv ON COMMIT DROP AS
SELECT cod_territorio, ano, cod_recorte, max(data_coleta) AS data_coleta,
       jsonb_object_agg(variavel, soma) FILTER (WHERE n > 0) AS v
FROM tmp_soma
GROUP BY cod_territorio, ano, cod_recorte;

-- D1: % de matrículas em tempo integral (infantil + fundamental + médio), redes públicas.
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_recorte, valor, numerador, denominador,
                           status_valor, data_coleta, referencia)
SELECT 'D1', cod_territorio, ano, cod_recorte,
       100.0 * num / NULLIF(den, 0), num, den,
       CASE WHEN num IS NULL OR den IS NULL OR den = 0 THEN 'sem_dado' ELSE 'observado' END, data_coleta,
       'QT_MAT_INF_INT + QT_MAT_FUND_INT + QT_MAT_MED_INT sobre QT_MAT_INF + QT_MAT_FUND + QT_MAT_MED'
FROM (
  SELECT cod_territorio, ano, cod_recorte, data_coleta,
         (v->>'QT_MAT_INF_INT')::numeric + (v->>'QT_MAT_FUND_INT')::numeric + (v->>'QT_MAT_MED_INT')::numeric AS num,
         (v->>'QT_MAT_INF')::numeric + (v->>'QT_MAT_FUND')::numeric + (v->>'QT_MAT_MED')::numeric AS den
  FROM tmp_piv
  WHERE cod_recorte ~ '^rede:(publica|federal|estadual|municipal)'
) x;

-- D2: % de escolas públicas (com matrícula regular) que têm alguma matrícula em tempo integral.
WITH esc AS (
  SELECT c.ano, c.co_entidade,
         sum(c.valor) FILTER (WHERE c.variavel IN ('QT_MAT_INF_INT', 'QT_MAT_FUND_INT', 'QT_MAT_MED_INT')) AS integral,
         count(c.valor) FILTER (WHERE c.variavel IN ('QT_MAT_INF_INT', 'QT_MAT_FUND_INT', 'QT_MAT_MED_INT')) AS n_integral,
         sum(c.valor) FILTER (WHERE c.variavel IN ('QT_MAT_INF', 'QT_MAT_FUND', 'QT_MAT_MED')) AS regular
  FROM core.v_contagem_escola c
  WHERE c.variavel IN ('QT_MAT_INF_INT', 'QT_MAT_FUND_INT', 'QT_MAT_MED_INT', 'QT_MAT_INF', 'QT_MAT_FUND', 'QT_MAT_MED')
  GROUP BY c.ano, c.co_entidade
)
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_recorte, valor, numerador, denominador,
                           status_valor, data_coleta, referencia)
SELECT 'D2', r.cod_territorio, e.ano, r.cod_recorte,
       CASE WHEN sum(esc.n_integral) > 0 THEN 100.0 * count(*) FILTER (WHERE esc.integral > 0) / count(*) END,
       CASE WHEN sum(esc.n_integral) > 0 THEN count(*) FILTER (WHERE esc.integral > 0) END, count(*),
       CASE WHEN sum(esc.n_integral) > 0 THEN 'observado' ELSE 'sem_dado' END, max(e.data_coleta),
       'Escolas públicas em atividade com QT_MAT_INF + QT_MAT_FUND + QT_MAT_MED > 0'
FROM esc
JOIN core.v_escola_ano e USING (ano, co_entidade)
JOIN core.v_escola_recorte r USING (ano, co_entidade)
WHERE e.em_atividade AND e.eh_publica AND esc.regular > 0
  AND r.cod_recorte ~ '^rede:(publica|federal|estadual|municipal)'
GROUP BY r.cod_territorio, e.ano, r.cod_recorte;

-- D3: índice de infraestrutura (0 a 100), por escola e média municipal das escolas em atividade.
CREATE TEMP TABLE tmp_infra ON COMMIT DROP AS
SELECT e.ano, e.co_entidade, e.cod_territorio, e.data_coleta,
       20.0 * (e.in_internet + e.tem_biblioteca_ou_sala_leitura + e.tem_laboratorio + e.in_quadra_esportes
               + e.tem_acessibilidade) AS indice
FROM core.v_escola_ano e
WHERE e.em_atividade;

INSERT INTO tmp_indicador (cod_indicador, cod_territorio, co_entidade, ano, valor, status_valor, data_coleta, referencia)
SELECT 'D3', cod_territorio, co_entidade, ano, indice, CASE WHEN indice IS NULL THEN 'sem_dado' ELSE 'observado' END,
       data_coleta, 'IN_INTERNET, biblioteca/sala de leitura, laboratório, IN_QUADRA_ESPORTES, acessibilidade'
FROM tmp_infra;

INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_recorte, valor, denominador, status_valor, data_coleta,
                           referencia)
SELECT 'D3', r.cod_territorio, i.ano, r.cod_recorte, avg(i.indice), count(i.indice),
       CASE WHEN count(i.indice) > 0 THEN 'observado' ELSE 'sem_dado' END, max(i.data_coleta),
       'Média do índice das escolas em atividade (denominador = escolas com todos os itens informados)'
FROM tmp_infra i
JOIN core.v_escola_recorte r USING (ano, co_entidade)
GROUP BY r.cod_territorio, i.ano, r.cod_recorte;

-- D4: % das matrículas da educação especial em classes comuns.
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_etapa, cod_recorte, valor, numerador, denominador,
                           status_valor, data_coleta, referencia)
SELECT 'D4', cod_territorio, ano, 'esp', cod_recorte, 100.0 * num / NULLIF(den, 0), num, den,
       CASE WHEN num IS NULL OR den IS NULL OR den = 0 THEN 'sem_dado' ELSE 'observado' END, data_coleta,
       '100 x QT_MAT_ESP_CC / QT_MAT_ESP'
FROM (SELECT cod_territorio, ano, cod_recorte, data_coleta, (v->>'QT_MAT_ESP_CC')::numeric AS num,
             (v->>'QT_MAT_ESP')::numeric AS den FROM tmp_piv) x;

-- D5: sala de atendimento especial (escolas públicas), oferta de AEE (todas) e matrículas da educação especial.
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_recorte, valor, numerador, denominador,
                           status_valor, data_coleta, referencia)
SELECT 'D5.escolas_sala_recursos', r.cod_territorio, e.ano, r.cod_recorte,
       100.0 * count(*) FILTER (WHERE e.in_sala_atendimento_especial = 1) / NULLIF(count(e.in_sala_atendimento_especial), 0),
       count(*) FILTER (WHERE e.in_sala_atendimento_especial = 1), count(e.in_sala_atendimento_especial),
       CASE WHEN count(e.in_sala_atendimento_especial) > 0 THEN 'observado' ELSE 'sem_dado' END, max(e.data_coleta),
       'IN_SALA_ATENDIMENTO_ESPECIAL = 1, escolas públicas em atividade'
FROM core.v_escola_ano e
JOIN core.v_escola_recorte r USING (ano, co_entidade)
WHERE e.em_atividade AND e.eh_publica AND r.cod_recorte ~ '^rede:(publica|federal|estadual|municipal)'
GROUP BY r.cod_territorio, e.ano, r.cod_recorte;

INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_recorte, valor, numerador, denominador,
                           status_valor, data_coleta, referencia)
SELECT 'D5.escolas_oferta_aee', r.cod_territorio, e.ano, r.cod_recorte,
       100.0 * count(*) FILTER (WHERE e.tp_aee IN (1, 2)) / NULLIF(count(e.tp_aee), 0),
       count(*) FILTER (WHERE e.tp_aee IN (1, 2)), count(e.tp_aee),
       CASE WHEN count(e.tp_aee) > 0 THEN 'observado' ELSE 'sem_dado' END, max(e.data_coleta),
       'TP_AEE = 1 (não exclusivamente) ou 2 (exclusivamente), escolas em atividade'
FROM core.v_escola_ano e
JOIN core.v_escola_recorte r USING (ano, co_entidade)
WHERE e.em_atividade
GROUP BY r.cod_territorio, e.ano, r.cod_recorte;

INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_etapa, cod_recorte, valor, numerador, status_valor,
                           data_coleta, referencia)
SELECT 'D5.matriculas_educacao_especial', cod_territorio, ano, 'esp', cod_recorte, (v->>'QT_MAT_ESP')::numeric,
       (v->>'QT_MAT_ESP')::numeric, CASE WHEN v ? 'QT_MAT_ESP' THEN 'observado' ELSE 'sem_dado' END, data_coleta,
       'Soma de QT_MAT_ESP (escolas em atividade)'
FROM tmp_piv;

-- D6: matrículas da EJA e % integrada à educação profissional.
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_etapa, cod_recorte, valor, numerador, status_valor,
                           data_coleta, referencia)
SELECT 'D6.matriculas_eja', p.cod_territorio, p.ano, e.cod_etapa, p.cod_recorte, (p.v->>e.variavel)::numeric,
       (p.v->>e.variavel)::numeric, CASE WHEN p.v ? e.variavel THEN 'observado' ELSE 'sem_dado' END, p.data_coleta,
       'Soma de ' || e.variavel
FROM tmp_piv p
CROSS JOIN (VALUES ('eja', 'QT_MAT_EJA'), ('eja_fund', 'QT_MAT_EJA_FUND'), ('eja_med', 'QT_MAT_EJA_MED')) AS e(cod_etapa, variavel);

INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_etapa, cod_recorte, valor, numerador, denominador,
                           status_valor, data_coleta, referencia, nota)
SELECT 'D6.pct_eja_integrada', cod_territorio, ano, cod_etapa, cod_recorte, 100.0 * num / NULLIF(den, 0), num, den,
       CASE WHEN num IS NULL OR den IS NULL OR den = 0 THEN 'sem_dado' ELSE 'observado' END, data_coleta, referencia,
       CASE WHEN num IS NULL THEN 'Variáveis de EJA integrada (FIC/TEC) só existem nos microdados a partir de 2023.' END
FROM (
  SELECT cod_territorio, ano, cod_recorte, data_coleta, 'eja_fund' AS cod_etapa,
         (v->>'QT_MAT_EJA_FUND_FIC')::numeric AS num, (v->>'QT_MAT_EJA_FUND')::numeric AS den,
         '100 x QT_MAT_EJA_FUND_FIC / QT_MAT_EJA_FUND' AS referencia
  FROM tmp_piv
  UNION ALL
  SELECT cod_territorio, ano, cod_recorte, data_coleta, 'eja_med',
         (v->>'QT_MAT_EJA_MED_TEC')::numeric + (v->>'QT_MAT_EJA_MED_FIC')::numeric, (v->>'QT_MAT_EJA_MED')::numeric,
         '100 x (QT_MAT_EJA_MED_TEC + QT_MAT_EJA_MED_FIC) / QT_MAT_EJA_MED'
  FROM tmp_piv
) x;

-- D7: distribuição das matrículas por cor/raça e sexo (redes, sem localização).
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_etapa, cod_recorte, valor, numerador, denominador,
                           status_valor, data_coleta, referencia)
SELECT 'D7', p.cod_territorio, p.ano, 'bas',
       CASE WHEN p.cod_recorte = 'total' THEN c.recorte ELSE p.cod_recorte || '|' || c.recorte END,
       100.0 * (p.v->>c.variavel)::numeric / NULLIF((p.v->>'QT_MAT_BAS')::numeric, 0),
       (p.v->>c.variavel)::numeric, (p.v->>'QT_MAT_BAS')::numeric,
       CASE WHEN p.v ? c.variavel AND (p.v->>'QT_MAT_BAS')::numeric > 0 THEN 'observado' ELSE 'sem_dado' END,
       p.data_coleta, '100 x ' || c.variavel || ' / QT_MAT_BAS'
FROM tmp_piv p
CROSS JOIN (VALUES ('QT_MAT_BAS_FEM', 'sexo:feminino'), ('QT_MAT_BAS_MASC', 'sexo:masculino'),
                   ('QT_MAT_BAS_BRANCA', 'raca_cor:branca'), ('QT_MAT_BAS_PRETA', 'raca_cor:preta'),
                   ('QT_MAT_BAS_PARDA', 'raca_cor:parda'), ('QT_MAT_BAS_AMARELA', 'raca_cor:amarela'),
                   ('QT_MAT_BAS_INDIGENA', 'raca_cor:indigena'), ('QT_MAT_BAS_ND', 'raca_cor:nao_declarada'))
     AS c(variavel, recorte)
WHERE p.cod_recorte NOT LIKE '%localizacao:%';
