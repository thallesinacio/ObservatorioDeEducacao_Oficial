-- 006 - Views de apoio no core: só a versão vigente de cada fato e o cadastro da escola por ano.
-- Usadas pelo cálculo dos indicadores (sql/indicadores) e pelos testes de qualidade.

CREATE OR REPLACE VIEW core.v_escola_ano AS
SELECT e.ano,
       e.co_entidade,
       e.co_municipio AS cod_territorio,
       e.no_entidade,
       e.tp_dependencia,
       CASE e.tp_dependencia WHEN 1 THEN 'federal' WHEN 2 THEN 'estadual' WHEN 3 THEN 'municipal'
                             WHEN 4 THEN 'privada' END AS rede,
       e.tp_dependencia IN (1, 2, 3) AS eh_publica,
       CASE e.tp_localizacao WHEN 1 THEN 'urbana' WHEN 2 THEN 'rural' END AS localizacao,
       e.tp_situacao_funcionamento,
       e.tp_situacao_funcionamento = 1 AS em_atividade,
       e.in_internet,
       CASE WHEN e.in_biblioteca IS NULL AND e.in_biblioteca_sala_leitura IS NULL AND e.in_sala_leitura IS NULL THEN NULL
            ELSE GREATEST(COALESCE(e.in_biblioteca, 0), COALESCE(e.in_biblioteca_sala_leitura, 0), COALESCE(e.in_sala_leitura, 0)) END
         AS tem_biblioteca_ou_sala_leitura,
       CASE WHEN e.in_laboratorio_ciencias IS NULL AND e.in_laboratorio_informatica IS NULL THEN NULL
            ELSE GREATEST(COALESCE(e.in_laboratorio_ciencias, 0), COALESCE(e.in_laboratorio_informatica, 0)) END
         AS tem_laboratorio,
       e.in_quadra_esportes,
       CASE WHEN e.in_acessibilidade_inexistente IS NULL THEN NULL
            WHEN e.in_acessibilidade_inexistente = 0 THEN 1 ELSE 0 END AS tem_acessibilidade,
       e.in_sala_atendimento_especial,
       e.tp_aee,
       e.versao_layout,
       a.data_coleta::date AS data_coleta
FROM staging.censo_escola e
JOIN etl.etl_arquivo a ON a.id_arquivo = e.id_arquivo;
COMMENT ON VIEW core.v_escola_ano IS 'Cadastro da escola em cada ano do Censo Escolar (rede, localização, situação e itens de infraestrutura já combinados). Indicadores IN_* ausentes no layout do ano ficam nulos.';

CREATE OR REPLACE VIEW core.v_escola_recorte AS
SELECT DISTINCT e.ano, e.co_entidade, e.cod_territorio,
       COALESCE(NULLIF(concat_ws('|', 'rede:' || rd, 'localizacao:' || lc), ''), 'total') AS cod_recorte
FROM core.v_escola_ano e
CROSS JOIN LATERAL unnest(ARRAY[NULL, e.rede, CASE WHEN e.eh_publica THEN 'publica' END]) AS rd
CROSS JOIN LATERAL unnest(ARRAY[NULL, e.localizacao]) AS lc;
COMMENT ON VIEW core.v_escola_recorte IS 'Para cada escola e ano, os recortes de rede x localização aos quais ela pertence (total, rede:municipal, rede:publica, localizacao:rural, rede:municipal|localizacao:rural...). Base para somar escolas por recorte.';

CREATE OR REPLACE VIEW core.v_fato_matricula AS
SELECT f.* FROM core.fato_matricula f JOIN etl.versao_dados v ON v.id_versao = f.id_versao AND v.vigente;
COMMENT ON VIEW core.v_fato_matricula IS 'core.fato_matricula, só a versão vigente.';

CREATE OR REPLACE VIEW core.v_fato_docente AS
SELECT f.* FROM core.fato_docente f JOIN etl.versao_dados v ON v.id_versao = f.id_versao AND v.vigente;
COMMENT ON VIEW core.v_fato_docente IS 'core.fato_docente, só a versão vigente.';

CREATE OR REPLACE VIEW core.v_fato_turma AS
SELECT f.* FROM core.fato_turma f JOIN etl.versao_dados v ON v.id_versao = f.id_versao AND v.vigente;
COMMENT ON VIEW core.v_fato_turma IS 'core.fato_turma, só a versão vigente.';

CREATE OR REPLACE VIEW core.v_fato_rendimento AS
SELECT f.* FROM core.fato_rendimento f JOIN etl.versao_dados v ON v.id_versao = f.id_versao AND v.vigente;
COMMENT ON VIEW core.v_fato_rendimento IS 'core.fato_rendimento, só a versão vigente.';

CREATE OR REPLACE VIEW core.v_fato_avaliacao AS
SELECT f.* FROM core.fato_avaliacao f JOIN etl.versao_dados v ON v.id_versao = f.id_versao AND v.vigente;
COMMENT ON VIEW core.v_fato_avaliacao IS 'core.fato_avaliacao, só a versão vigente (todas as edições do Ideb carregadas).';

CREATE OR REPLACE VIEW core.v_fato_financiamento AS
SELECT f.* FROM core.fato_financiamento f JOIN etl.versao_dados v ON v.id_versao = f.id_versao AND v.vigente;
COMMENT ON VIEW core.v_fato_financiamento IS 'core.fato_financiamento, só a versão vigente de cada fonte.';

CREATE OR REPLACE VIEW core.v_fato_populacao AS
SELECT f.* FROM core.fato_populacao f JOIN etl.versao_dados v ON v.id_versao = f.id_versao AND v.vigente;
COMMENT ON VIEW core.v_fato_populacao IS 'core.fato_populacao, só a versão vigente de cada fonte.';

CREATE OR REPLACE VIEW core.v_fato_indicador AS
SELECT f.* FROM core.fato_indicador f JOIN etl.versao_dados v ON v.id_versao = f.id_versao AND v.vigente;
COMMENT ON VIEW core.v_fato_indicador IS 'core.fato_indicador, só a versão vigente do cálculo.';

-- Contagens do Censo por escola, com o nome da variável de origem (formato longo).
CREATE OR REPLACE VIEW core.v_contagem_escola AS
SELECT ano, co_entidade, cod_territorio, variavel_origem AS variavel, qt_matriculas AS valor, data_coleta
FROM core.v_fato_matricula
UNION ALL
SELECT ano, co_entidade, cod_territorio, variavel_origem, qt_docentes, data_coleta
FROM core.v_fato_docente WHERE co_entidade IS NOT NULL
UNION ALL
SELECT ano, co_entidade, cod_territorio, variavel_origem, qt_turmas, data_coleta
FROM core.v_fato_turma;
COMMENT ON VIEW core.v_contagem_escola IS 'Contagens do Censo Escolar (matrículas, docentes e turmas) por escola e variável de origem, versão vigente. Valor nulo = célula vazia na origem.';
