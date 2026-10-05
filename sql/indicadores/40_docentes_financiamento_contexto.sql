-- Eixos E (docentes e condições), F (financiamento) e G (contexto).
-- Marcadores {{...}} são trocados pelo observatorio.indicadores.calcular a partir de config/siope.yaml.

-- E1, E2, E5.alunos_por_turma: números oficiais do INEP (Indicadores Educacionais), território e escola.
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, co_entidade, ano, cod_etapa, cod_recorte, valor, status_valor,
                           data_coleta, referencia, cod_fonte_valor)
SELECT DISTINCT ON (s.id_fonte, s.cod_territorio, s.co_entidade, s.ano, s.cod_etapa, s.rede, s.localizacao)
       CASE s.id_fonte WHEN 'inep_dsu' THEN 'E1' WHEN 'inep_afd' THEN 'E2' ELSE 'E5.alunos_por_turma' END,
       s.cod_territorio, s.co_entidade, s.ano, s.cod_etapa,
       COALESCE(NULLIF(concat_ws('|', CASE WHEN s.rede <> 'total' THEN 'rede:' || s.rede END,
                                      CASE WHEN s.localizacao <> 'total' THEN 'localizacao:' || s.localizacao END), ''),
                'total'),
       CASE WHEN s.status_valor = 'observado' THEN s.valor END, s.status_valor, a.data_coleta::date,
       'INEP - Indicadores Educacionais; coluna ' || s.coluna_origem, s.id_fonte
FROM staging.inep_indicador s
JOIN etl.etl_arquivo a USING (id_arquivo)
WHERE (s.id_fonte = 'inep_dsu' AND s.medida = 'pct_docentes_superior')
   OR (s.id_fonte = 'inep_afd' AND s.medida = 'afd_grupo_1')
   OR (s.id_fonte = 'inep_atu' AND s.medida = 'media_alunos_turma')
ORDER BY s.id_fonte, s.cod_territorio, s.co_entidade, s.ano, s.cod_etapa, s.rede, s.localizacao,
         (s.status_valor = 'observado') DESC, split_part(s.coluna_origem, ':', 1)::int;

-- E3: % de docentes com pós-graduação (Sinopse, docente único no município).
-- A partir de 2025 a Sinopse traz o total de docentes com pós-graduação (cada docente contado uma
-- vez): valor observado. Até 2024 só há as colunas de especialização, mestrado e doutorado, que não
-- são exclusivas: a soma (limitada ao total de graduados) é um LIMITE SUPERIOR, com status estimado.
WITH d AS (
  SELECT cod_territorio, ano, max(data_coleta) AS data_coleta,
         max(qt_docentes) FILTER (WHERE cod_recorte = 'total') AS total,
         max(qt_docentes) FILTER (WHERE cod_recorte = 'escolaridade:superior') AS superior,
         max(qt_docentes) FILTER (WHERE cod_recorte = 'escolaridade:pos_graduacao') AS pos,
         max(qt_docentes) FILTER (WHERE cod_recorte = 'escolaridade:especializacao') AS espec,
         max(qt_docentes) FILTER (WHERE cod_recorte = 'escolaridade:mestrado') AS mestr,
         max(qt_docentes) FILTER (WHERE cod_recorte = 'escolaridade:doutorado') AS dout
  FROM core.v_fato_docente d
  JOIN core.dim_fonte f USING (id_fonte)
  WHERE f.cod_fonte = 'sinopse_estatistica' AND d.co_entidade IS NULL
  GROUP BY cod_territorio, ano
)
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_etapa, valor, numerador, denominador, status_valor,
                           data_coleta, referencia, nota)
SELECT 'E3', cod_territorio, ano, 'bas', 100.0 * num / NULLIF(total, 0), num, total,
       CASE WHEN num IS NULL OR total IS NULL OR total = 0 THEN 'sem_dado'
            WHEN pos IS NOT NULL THEN 'observado' ELSE 'estimado' END,
       data_coleta,
       'Sinopse Estatística da Educação Básica (docentes por nível de escolaridade e formação acadêmica)',
       CASE WHEN pos IS NULL THEN 'Limite superior: especialização, mestrado e doutorado não são categorias exclusivas (um docente pode estar em mais de uma).' END
FROM (SELECT *, COALESCE(pos, LEAST(espec + mestr + dout, COALESCE(superior, espec + mestr + dout))) AS num FROM d) x;

-- E5.alunos_por_docente: matrículas ÷ docentes (soma por escola: o docente de duas escolas conta duas vezes).
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, co_entidade, ano, cod_etapa, valor, numerador, denominador,
                           status_valor, data_coleta, referencia, nota)
SELECT 'E5.alunos_por_docente', e.cod_territorio, e.co_entidade, e.ano, 'bas',
       m.valor::numeric / NULLIF(d.valor, 0), m.valor, d.valor,
       CASE WHEN m.valor IS NULL OR d.valor IS NULL OR d.valor = 0 THEN 'sem_dado' ELSE 'observado' END,
       e.data_coleta, 'QT_MAT_BAS / QT_DOC_BAS', NULL
FROM core.v_escola_ano e
LEFT JOIN core.v_contagem_escola m ON m.ano = e.ano AND m.co_entidade = e.co_entidade AND m.variavel = 'QT_MAT_BAS'
LEFT JOIN core.v_contagem_escola d ON d.ano = e.ano AND d.co_entidade = e.co_entidade AND d.variavel = 'QT_DOC_BAS'
WHERE e.em_atividade;

INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_etapa, cod_recorte, valor, numerador, denominador,
                           status_valor, data_coleta, referencia, nota)
SELECT 'E5.alunos_por_docente', cod_territorio, ano, 'bas', cod_recorte, num / NULLIF(den, 0), num, den,
       CASE WHEN num IS NULL OR den IS NULL OR den = 0 THEN 'sem_dado' ELSE 'observado' END, data_coleta,
       'Soma de QT_MAT_BAS / soma de QT_DOC_BAS (escolas em atividade)',
       'Docentes somados por escola: quem atua em mais de uma escola conta mais de uma vez (a razão fica subestimada).'
FROM (SELECT cod_territorio, ano, cod_recorte, data_coleta, (v->>'QT_MAT_BAS')::numeric AS num,
             (v->>'QT_DOC_BAS')::numeric AS den FROM tmp_piv) x;

-- F1 e F2.siope: indicadores declarados ao SIOPE.
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, valor, status_valor, data_coleta, referencia)
SELECT CASE s.cod_indi WHEN {{siope_mde}} THEN 'F1' ELSE 'F2.siope' END, s.cod_territorio, s.ano, s.valor,
       CASE WHEN s.valor IS NULL THEN 'sem_dado' ELSE 'observado' END, a.data_coleta::date,
       'SIOPE, indicador ' || COALESCE(s.cod_exib, s.cod_indi::text) || ' - ' || COALESCE(s.nom_indi, '')
FROM staging.siope_indicador s
JOIN etl.etl_arquivo a USING (id_arquivo)
WHERE s.cod_indi IN ({{siope_mde}}, {{siope_investimento}});

-- F2: despesa liquidada em educação (SIOPE) ÷ matrículas da rede municipal (Censo do mesmo ano).
WITH mat AS (
  SELECT cod_territorio, ano, (v->>'QT_MAT_BAS')::numeric AS matriculas, data_coleta
  FROM tmp_piv WHERE cod_recorte = 'rede:municipal'
)
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_recorte, valor, numerador, denominador, status_valor,
                           data_coleta, referencia, nota)
SELECT 'F2', g.cod_territorio, g.ano, 'rede:municipal', g.desp_educacao_liquidada / NULLIF(m.matriculas, 0),
       g.desp_educacao_liquidada, m.matriculas,
       CASE WHEN g.desp_educacao_liquidada IS NULL OR m.matriculas IS NULL OR m.matriculas = 0 THEN 'sem_dado'
            ELSE 'observado' END,
       GREATEST(a.data_coleta::date, m.data_coleta),
       'SIOPE Dados Gerais (VL_DESP_LIQU_EDU) / QT_MAT_BAS das escolas municipais em atividade',
       CASE WHEN m.matriculas IS NULL THEN 'Censo Escolar do mesmo ano não carregado.' END
FROM staging.siope_dados_gerais g
JOIN etl.etl_arquivo a USING (id_arquivo)
LEFT JOIN mat m USING (cod_territorio, ano);

-- F3: despesa liquidada na função 12 - Educação e por subfunção (SICONFI, DCA Anexo I-E).
WITH dca AS (
  SELECT DISTINCT ON (ano, cod_territorio, rubrica_codigo)
         ano, cod_territorio, rubrica_codigo, rubrica_nome, valor, data_coleta
  FROM core.v_fato_financiamento
  WHERE demonstrativo = 'DCA-Anexo I-E' AND coluna = 'Despesas Liquidadas' AND rubrica_codigo ~ '^12(\.|$)'
  ORDER BY ano, cod_territorio, rubrica_codigo, (ordem LIKE 'TotalDespesas|%') DESC, ordem
)
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_recorte, valor, status_valor, data_coleta,
                           referencia)
SELECT 'F3', cod_territorio, ano,
       CASE WHEN rubrica_codigo = '12' THEN 'total' ELSE 'subfuncao:' || rubrica_codigo END,
       valor, CASE WHEN valor IS NULL THEN 'sem_dado' ELSE 'observado' END, data_coleta,
       'SICONFI DCA Anexo I-E, Despesas Liquidadas, ' || rubrica_nome
FROM dca;

-- G1: população por faixa etária (RIPSA) e G1.censo2022 (Censo 2022, idades simples do SIDRA 9514).
WITH faixas(recorte, idade_min, idade_max) AS (
  VALUES ('faixa_populacao:0_3', 0, 3), ('faixa_populacao:4_5', 4, 5), ('faixa_populacao:6_14', 6, 14),
         ('faixa_populacao:15_17', 15, 17), ('total', 0, 200)
)
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, cod_recorte, valor, status_valor, data_coleta, referencia)
SELECT CASE WHEN p.origem LIKE 'ripsa%' THEN 'G1' ELSE 'G1.censo2022' END, p.cod_territorio, p.ano, f.recorte,
       sum(p.populacao),
       CASE WHEN count(p.populacao) < count(*) THEN 'sem_dado'
            WHEN p.origem LIKE 'ripsa%' THEN 'estimado' ELSE 'observado' END,
       max(p.data_coleta), string_agg(DISTINCT p.edicao, '; ')
FROM core.v_fato_populacao p
JOIN faixas f ON p.idade BETWEEN f.idade_min AND f.idade_max
WHERE p.sexo = 'T' AND (p.origem LIKE 'ripsa%' OR p.origem = 'ibge_censo2022')
GROUP BY 1, p.cod_territorio, p.ano, f.recorte, p.origem;

-- G1.ibge_total, G3.pib (SIDRA) e G2 (alfabetização, Censo 2022).
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, valor, status_valor, data_coleta, referencia, nota)
SELECT CASE s.tabela WHEN '6579' THEN 'G1.ibge_total' ELSE 'G3.pib' END, s.cod_territorio, s.ano,
       CASE WHEN s.status_valor = 'observado' THEN s.valor END,
       CASE WHEN s.tabela = '6579' AND s.status_valor = 'observado' THEN 'estimado' ELSE s.status_valor END,
       a.data_coleta::date, 'SIDRA/IBGE tabela ' || s.tabela || ', variável ' || s.variavel,
       CASE WHEN s.status_valor = 'observado' AND s.valor_texto = '-' THEN 'Zero absoluto (marcador "-" do IBGE).' END
FROM staging.sidra s
JOIN etl.etl_arquivo a USING (id_arquivo)
WHERE s.tabela IN ('6579', '5938');

WITH alf AS (
  SELECT s.cod_territorio, s.ano, max(a.data_coleta::date) AS data_coleta,
         max(s.valor) FILTER (WHERE s.classificacao ~ '(^|;)Alfabetização=1023:') AS alfabetizadas,
         max(s.valor) FILTER (WHERE s.classificacao ~ '(^|;)Alfabetização=93024:') AS total
  FROM staging.sidra s JOIN etl.etl_arquivo a USING (id_arquivo)
  WHERE s.tabela = '9542'
  GROUP BY s.cod_territorio, s.ano
)
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, valor, numerador, denominador, status_valor, data_coleta,
                           referencia)
SELECT 'G2', cod_territorio, ano, 100.0 * alfabetizadas / NULLIF(total, 0), alfabetizadas, total,
       CASE WHEN alfabetizadas IS NULL OR total IS NULL OR total = 0 THEN 'sem_dado' ELSE 'observado' END, data_coleta,
       'SIDRA/IBGE tabela 9542 (Censo 2022), pessoas de 15 anos ou mais'
FROM alf;

-- G3.pib_per_capita: PIB (mil R$) ÷ população estimada do IBGE no mesmo ano.
WITH pib AS (SELECT cod_territorio, ano, valor FROM staging.sidra WHERE tabela = '5938' AND status_valor = 'observado'),
     pop AS (SELECT cod_territorio, ano, valor FROM staging.sidra WHERE tabela = '6579' AND status_valor = 'observado')
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, ano, valor, numerador, denominador, status_valor, data_coleta,
                           referencia, nota)
SELECT 'G3.pib_per_capita', pib.cod_territorio, pib.ano, 1000 * pib.valor / NULLIF(pop.valor, 0), 1000 * pib.valor,
       pop.valor, CASE WHEN pop.valor IS NULL THEN 'sem_dado' ELSE 'estimado' END, current_date,
       'SIDRA 5938 (PIB) / SIDRA 6579 (população estimada)',
       CASE WHEN pop.valor IS NULL THEN 'Sem estimativa populacional do IBGE no ano.' END
FROM pib LEFT JOIN pop USING (cod_territorio, ano);
