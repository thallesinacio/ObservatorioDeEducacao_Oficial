-- Camada bi: visões prontas para o painel de apresentação.
-- Cada linha de bi.painel_serie já é UM ponto de UM gráfico: basta filtrar a coluna "grafico" e
-- usar ano no eixo X, valor no eixo Y e serie na legenda. Não precisa de relações nem de outros
-- filtros. A lista de gráficos (e o que entra em cada um) está na tabela de mapeamento abaixo.

CREATE VIEW bi.painel_serie AS
WITH mapa (pagina, ordem_pagina, grafico, titulo, cod_indicador, cod_etapa, cod_recorte, cod_territorio, serie, ordem_serie) AS (
  VALUES
  -- 1. Acesso e matrículas ------------------------------------------------------------------------
  ('1. Acesso e matrículas', 1, 'acesso_taxas', 'Taxa de atendimento escolar por faixa etária (%) - Juazeiro', 'A1', 'total', 'total', '2918407', '0 a 3 anos', 1),
  ('1. Acesso e matrículas', 1, 'acesso_taxas', 'Taxa de atendimento escolar por faixa etária (%) - Juazeiro', 'A2', 'total', 'total', '2918407', '4 a 5 anos', 2),
  ('1. Acesso e matrículas', 1, 'acesso_taxas', 'Taxa de atendimento escolar por faixa etária (%) - Juazeiro', 'A3', 'total', 'total', '2918407', '6 a 14 anos', 3),
  ('1. Acesso e matrículas', 1, 'acesso_taxas', 'Taxa de atendimento escolar por faixa etária (%) - Juazeiro', 'A4', 'total', 'total', '2918407', '15 a 17 anos', 4),
  ('1. Acesso e matrículas', 1, 'matriculas_total', 'Matrículas na educação básica - Juazeiro', 'A6', 'bas', 'total', '2918407', 'Total', 1),
  ('1. Acesso e matrículas', 1, 'matriculas_etapa', 'Matrículas por etapa - Juazeiro', 'A6', 'inf_cre', 'total', '2918407', 'Creche', 1),
  ('1. Acesso e matrículas', 1, 'matriculas_etapa', 'Matrículas por etapa - Juazeiro', 'A6', 'inf_pre', 'total', '2918407', 'Pré-escola', 2),
  ('1. Acesso e matrículas', 1, 'matriculas_etapa', 'Matrículas por etapa - Juazeiro', 'A6', 'fund_ai', 'total', '2918407', 'Fundamental - anos iniciais', 3),
  ('1. Acesso e matrículas', 1, 'matriculas_etapa', 'Matrículas por etapa - Juazeiro', 'A6', 'fund_af', 'total', '2918407', 'Fundamental - anos finais', 4),
  ('1. Acesso e matrículas', 1, 'matriculas_etapa', 'Matrículas por etapa - Juazeiro', 'A6', 'med', 'total', '2918407', 'Ensino médio', 5),
  ('1. Acesso e matrículas', 1, 'matriculas_etapa', 'Matrículas por etapa - Juazeiro', 'A6', 'eja', 'total', '2918407', 'EJA', 6),
  ('1. Acesso e matrículas', 1, 'matriculas_rede', 'Matrículas por rede - Juazeiro', 'A6', 'bas', 'rede:municipal', '2918407', 'Municipal', 1),
  ('1. Acesso e matrículas', 1, 'matriculas_rede', 'Matrículas por rede - Juazeiro', 'A6', 'bas', 'rede:estadual', '2918407', 'Estadual', 2),
  ('1. Acesso e matrículas', 1, 'matriculas_rede', 'Matrículas por rede - Juazeiro', 'A6', 'bas', 'rede:federal', '2918407', 'Federal', 3),
  ('1. Acesso e matrículas', 1, 'matriculas_rede', 'Matrículas por rede - Juazeiro', 'A6', 'bas', 'rede:privada', '2918407', 'Privada', 4),
  ('1. Acesso e matrículas', 1, 'escolas_total', 'Escolas em atividade - Juazeiro', 'A7', 'total', 'total', '2918407', 'Total', 1),
  ('1. Acesso e matrículas', 1, 'escolas_rede', 'Escolas em atividade por rede - Juazeiro', 'A7', 'total', 'rede:municipal', '2918407', 'Municipal', 1),
  ('1. Acesso e matrículas', 1, 'escolas_rede', 'Escolas em atividade por rede - Juazeiro', 'A7', 'total', 'rede:estadual', '2918407', 'Estadual', 2),
  ('1. Acesso e matrículas', 1, 'escolas_rede', 'Escolas em atividade por rede - Juazeiro', 'A7', 'total', 'rede:federal', '2918407', 'Federal', 3),
  ('1. Acesso e matrículas', 1, 'escolas_rede', 'Escolas em atividade por rede - Juazeiro', 'A7', 'total', 'rede:privada', '2918407', 'Privada', 4),
  -- 2. Rendimento e fluxo -------------------------------------------------------------------------
  ('2. Rendimento e fluxo', 2, 'aprovacao_etapa', 'Taxa de aprovação por etapa (%) - Juazeiro', 'B1.aprovacao', 'fund_ai', 'total', '2918407', 'Fundamental - anos iniciais', 3),
  ('2. Rendimento e fluxo', 2, 'aprovacao_etapa', 'Taxa de aprovação por etapa (%) - Juazeiro', 'B1.aprovacao', 'fund_af', 'total', '2918407', 'Fundamental - anos finais', 4),
  ('2. Rendimento e fluxo', 2, 'aprovacao_etapa', 'Taxa de aprovação por etapa (%) - Juazeiro', 'B1.aprovacao', 'med', 'total', '2918407', 'Ensino médio', 5),
  ('2. Rendimento e fluxo', 2, 'abandono_etapa', 'Taxa de abandono por etapa (%) - Juazeiro', 'B1.abandono', 'fund_ai', 'total', '2918407', 'Fundamental - anos iniciais', 3),
  ('2. Rendimento e fluxo', 2, 'abandono_etapa', 'Taxa de abandono por etapa (%) - Juazeiro', 'B1.abandono', 'fund_af', 'total', '2918407', 'Fundamental - anos finais', 4),
  ('2. Rendimento e fluxo', 2, 'abandono_etapa', 'Taxa de abandono por etapa (%) - Juazeiro', 'B1.abandono', 'med', 'total', '2918407', 'Ensino médio', 5),
  ('2. Rendimento e fluxo', 2, 'distorcao_etapa', 'Distorção idade-série por etapa (%) - Juazeiro', 'B2', 'fund_ai', 'total', '2918407', 'Fundamental - anos iniciais', 3),
  ('2. Rendimento e fluxo', 2, 'distorcao_etapa', 'Distorção idade-série por etapa (%) - Juazeiro', 'B2', 'fund_af', 'total', '2918407', 'Fundamental - anos finais', 4),
  ('2. Rendimento e fluxo', 2, 'distorcao_etapa', 'Distorção idade-série por etapa (%) - Juazeiro', 'B2', 'med', 'total', '2918407', 'Ensino médio', 5),
  ('2. Rendimento e fluxo', 2, 'distorcao_comparacao', 'Distorção idade-série no ensino fundamental (%) - comparação', 'B2', 'fund', 'total', '2918407', 'Juazeiro', 1),
  ('2. Rendimento e fluxo', 2, 'distorcao_comparacao', 'Distorção idade-série no ensino fundamental (%) - comparação', 'B2', 'fund', 'total', '29', 'Bahia', 2),
  ('2. Rendimento e fluxo', 2, 'distorcao_comparacao', 'Distorção idade-série no ensino fundamental (%) - comparação', 'B2', 'fund', 'total', '1', 'Brasil', 3),
  -- 3. Aprendizagem (Ideb) ------------------------------------------------------------------------
  ('3. Aprendizagem (Ideb)', 3, 'ideb_ai', 'Ideb - anos iniciais (rede pública)', 'C1', 'fund_ai', 'rede:publica', '2918407', 'Juazeiro', 1),
  ('3. Aprendizagem (Ideb)', 3, 'ideb_ai', 'Ideb - anos iniciais (rede pública)', 'C1', 'fund_ai', 'rede:publica', '29', 'Bahia', 2),
  ('3. Aprendizagem (Ideb)', 3, 'ideb_ai', 'Ideb - anos iniciais (rede pública)', 'C1', 'fund_ai', 'rede:publica', '1', 'Brasil', 3),
  ('3. Aprendizagem (Ideb)', 3, 'ideb_af', 'Ideb - anos finais (rede pública)', 'C1', 'fund_af', 'rede:publica', '2918407', 'Juazeiro', 1),
  ('3. Aprendizagem (Ideb)', 3, 'ideb_af', 'Ideb - anos finais (rede pública)', 'C1', 'fund_af', 'rede:publica', '29', 'Bahia', 2),
  ('3. Aprendizagem (Ideb)', 3, 'ideb_af', 'Ideb - anos finais (rede pública)', 'C1', 'fund_af', 'rede:publica', '1', 'Brasil', 3),
  ('3. Aprendizagem (Ideb)', 3, 'ideb_em', 'Ideb - ensino médio (rede pública)', 'C1', 'med', 'rede:publica', '2918407', 'Juazeiro', 1),
  ('3. Aprendizagem (Ideb)', 3, 'ideb_em', 'Ideb - ensino médio (rede pública)', 'C1', 'med', 'rede:publica', '29', 'Bahia', 2),
  ('3. Aprendizagem (Ideb)', 3, 'ideb_em', 'Ideb - ensino médio (rede pública)', 'C1', 'med', 'rede:publica', '1', 'Brasil', 3),
  ('3. Aprendizagem (Ideb)', 3, 'ideb_meta_municipal', 'Ideb anos iniciais - rede municipal de Juazeiro: observado x meta', 'C1', 'fund_ai', 'rede:municipal', '2918407', 'Ideb observado', 1),
  ('3. Aprendizagem (Ideb)', 3, 'ideb_meta_municipal', 'Ideb anos iniciais - rede municipal de Juazeiro: observado x meta', 'C1.meta', 'fund_ai', 'rede:municipal', '2918407', 'Meta do INEP', 2),
  ('3. Aprendizagem (Ideb)', 3, 'saeb_ai_municipal', 'Saeb 5º ano - rede municipal de Juazeiro (proficiência média)', 'C2.matematica', 'fund_ai', 'rede:municipal', '2918407', 'Matemática', 1),
  ('3. Aprendizagem (Ideb)', 3, 'saeb_ai_municipal', 'Saeb 5º ano - rede municipal de Juazeiro (proficiência média)', 'C2.lingua_portuguesa', 'fund_ai', 'rede:municipal', '2918407', 'Língua Portuguesa', 2),
  -- 4. Inclusão, jornada e infraestrutura ---------------------------------------------------------
  ('4. Inclusão e infraestrutura', 4, 'tempo_integral', 'Matrículas em tempo integral (%) - Juazeiro', 'D1', 'total', 'rede:publica', '2918407', 'Rede pública', 1),
  ('4. Inclusão e infraestrutura', 4, 'tempo_integral', 'Matrículas em tempo integral (%) - Juazeiro', 'D1', 'total', 'rede:municipal', '2918407', 'Rede municipal', 2),
  ('4. Inclusão e infraestrutura', 4, 'educacao_especial', 'Educação especial em classes comuns (%) - Juazeiro', 'D4', 'esp', 'total', '2918407', 'Classes comuns', 1),
  ('4. Inclusão e infraestrutura', 4, 'infraestrutura', 'Índice de infraestrutura escolar (0 a 100) - Juazeiro', 'D3', 'total', 'rede:municipal', '2918407', 'Rede municipal', 2),
  ('4. Inclusão e infraestrutura', 4, 'infraestrutura', 'Índice de infraestrutura escolar (0 a 100) - Juazeiro', 'D3', 'total', 'rede:estadual', '2918407', 'Rede estadual', 3),
  ('4. Inclusão e infraestrutura', 4, 'infraestrutura', 'Índice de infraestrutura escolar (0 a 100) - Juazeiro', 'D3', 'total', 'rede:privada', '2918407', 'Rede privada', 4),
  -- 5. Docentes -----------------------------------------------------------------------------------
  ('5. Docentes', 5, 'docentes_superior', 'Docentes com curso superior (%) - comparação', 'E1', 'bas', 'total', '2918407', 'Juazeiro', 1),
  ('5. Docentes', 5, 'docentes_superior', 'Docentes com curso superior (%) - comparação', 'E1', 'bas', 'total', '29', 'Bahia', 2),
  ('5. Docentes', 5, 'docentes_superior', 'Docentes com curso superior (%) - comparação', 'E1', 'bas', 'total', '1', 'Brasil', 3),
  ('5. Docentes', 5, 'docentes_pos', 'Docentes com pós-graduação (%) - comparação', 'E3', 'bas', 'total', '2918407', 'Juazeiro', 1),
  ('5. Docentes', 5, 'docentes_pos', 'Docentes com pós-graduação (%) - comparação', 'E3', 'bas', 'total', '29', 'Bahia', 2),
  ('5. Docentes', 5, 'docentes_pos', 'Docentes com pós-graduação (%) - comparação', 'E3', 'bas', 'total', '1', 'Brasil', 3),
  ('5. Docentes', 5, 'afd_grupo1', 'Docentes com formação adequada à disciplina - grupo 1 (%) - Juazeiro', 'E2', 'fund_ai', 'total', '2918407', 'Fundamental - anos iniciais', 3),
  ('5. Docentes', 5, 'afd_grupo1', 'Docentes com formação adequada à disciplina - grupo 1 (%) - Juazeiro', 'E2', 'fund_af', 'total', '2918407', 'Fundamental - anos finais', 4),
  ('5. Docentes', 5, 'afd_grupo1', 'Docentes com formação adequada à disciplina - grupo 1 (%) - Juazeiro', 'E2', 'med', 'total', '2918407', 'Ensino médio', 5),
  ('5. Docentes', 5, 'alunos_turma', 'Média de alunos por turma - Juazeiro', 'E5.alunos_por_turma', 'fund_ai', 'total', '2918407', 'Fundamental - anos iniciais', 3),
  ('5. Docentes', 5, 'alunos_turma', 'Média de alunos por turma - Juazeiro', 'E5.alunos_por_turma', 'fund_af', 'total', '2918407', 'Fundamental - anos finais', 4),
  ('5. Docentes', 5, 'alunos_turma', 'Média de alunos por turma - Juazeiro', 'E5.alunos_por_turma', 'med', 'total', '2918407', 'Ensino médio', 5),
  -- 6. Financiamento ------------------------------------------------------------------------------
  ('6. Financiamento', 6, 'mde', 'Receita de impostos aplicada em educação - MDE (%) - Juazeiro', 'F1', 'total', 'total', '2918407', 'Aplicado em MDE', 1),
  ('6. Financiamento', 6, 'investimento_aluno', 'Investimento por aluno (R$) - Juazeiro', 'F2.siope', 'total', 'total', '2918407', 'SIOPE (indicador 4.8)', 1),
  ('6. Financiamento', 6, 'investimento_aluno', 'Investimento por aluno (R$) - Juazeiro', 'F2', 'total', 'rede:municipal', '2918407', 'Cálculo do Observatório (rede municipal)', 2),
  ('6. Financiamento', 6, 'fundeb', 'Recursos do Fundeb recebidos (R$) - Juazeiro', 'F4', 'total', 'total', '2918407', 'Fundeb', 1),
  ('6. Financiamento', 6, 'despesa_educacao', 'Despesa liquidada em educação (R$) - Juazeiro', 'F3', 'total', 'total', '2918407', 'Função 12 - Educação', 1)
)
SELECT m.pagina, m.ordem_pagina, m.grafico, m.titulo, m.serie, m.ordem_serie,
       f.ano, f.valor, i.unidade, f.status_valor,
       f.status_valor = 'estimado' AS eh_estimado,
       f.status_valor IN ('sem_dado', 'nao_se_aplica') AS eh_lacuna,
       f.eh_calculo_proprio, i.nome AS indicador, i.formula, i.nota_metodologica,
       fo.nome AS fonte, f.referencia, f.nota, f.data_coleta
FROM mapa m
JOIN core.v_fato_indicador f
  ON f.cod_indicador = m.cod_indicador AND f.cod_etapa = m.cod_etapa AND f.cod_recorte = m.cod_recorte
 AND f.cod_territorio = m.cod_territorio AND f.co_entidade IS NULL
JOIN core.dim_indicador i ON i.cod_indicador = f.cod_indicador
JOIN core.dim_fonte fo ON fo.id_fonte = f.id_fonte
UNION ALL
-- Despesa por subfunção (as subfunções existentes variam por ano: entram todas as que vierem na DCA).
SELECT '6. Financiamento', 6, 'despesa_subfuncao', 'Despesa liquidada em educação por subfunção (R$) - Juazeiro',
       replace(r.rotulo, 'Subfunção: ', ''), 20,
       f.ano, f.valor, i.unidade, f.status_valor, f.status_valor = 'estimado',
       f.status_valor IN ('sem_dado', 'nao_se_aplica'), f.eh_calculo_proprio, i.nome, i.formula, i.nota_metodologica,
       fo.nome, f.referencia, f.nota, f.data_coleta
FROM core.v_fato_indicador f
JOIN core.dim_recorte r ON r.cod_recorte = f.cod_recorte
JOIN core.dim_indicador i ON i.cod_indicador = f.cod_indicador
JOIN core.dim_fonte fo ON fo.id_fonte = f.id_fonte
WHERE f.cod_indicador = 'F3' AND f.cod_territorio = '2918407' AND f.co_entidade IS NULL
  AND f.cod_recorte LIKE 'subfuncao:%';
COMMENT ON VIEW bi.painel_serie IS 'Painel de apresentação: cada linha é um ponto de um gráfico. Filtre "grafico" e use ano (eixo X), valor (eixo Y) e serie (legenda). Lacunas têm valor vazio.';
COMMENT ON COLUMN bi.painel_serie.pagina IS 'Página sugerida do painel.';
COMMENT ON COLUMN bi.painel_serie.ordem_pagina IS 'Ordem da página.';
COMMENT ON COLUMN bi.painel_serie.grafico IS 'Identificador do gráfico (use como filtro do visual).';
COMMENT ON COLUMN bi.painel_serie.titulo IS 'Título sugerido para o gráfico.';
COMMENT ON COLUMN bi.painel_serie.serie IS 'Nome da linha/barra (legenda).';
COMMENT ON COLUMN bi.painel_serie.ordem_serie IS 'Ordem da série na legenda.';
COMMENT ON COLUMN bi.painel_serie.ano IS 'Ano.';
COMMENT ON COLUMN bi.painel_serie.valor IS 'Valor (vazio = sem dado).';
COMMENT ON COLUMN bi.painel_serie.unidade IS 'Unidade do indicador.';
COMMENT ON COLUMN bi.painel_serie.status_valor IS 'observado, estimado, sem_dado...';
COMMENT ON COLUMN bi.painel_serie.eh_estimado IS 'Valor usa estimativa (ex.: população projetada).';
COMMENT ON COLUMN bi.painel_serie.eh_lacuna IS 'Sem dado ou não se aplica.';
COMMENT ON COLUMN bi.painel_serie.eh_calculo_proprio IS 'Cálculo do Observatório (não é número oficial).';
COMMENT ON COLUMN bi.painel_serie.indicador IS 'Nome do indicador.';
COMMENT ON COLUMN bi.painel_serie.formula IS 'Fórmula ou origem do número.';
COMMENT ON COLUMN bi.painel_serie.nota_metodologica IS 'Cuidados de leitura.';
COMMENT ON COLUMN bi.painel_serie.fonte IS 'Fonte do valor.';
COMMENT ON COLUMN bi.painel_serie.referencia IS 'Procedência detalhada.';
COMMENT ON COLUMN bi.painel_serie.nota IS 'Observação sobre o valor.';
COMMENT ON COLUMN bi.painel_serie.data_coleta IS 'Data da coleta.';

-- Cartões de destaque: o valor mais recente (com número) de cada série, e o ano a que se refere.
CREATE VIEW bi.painel_destaque AS
SELECT DISTINCT ON (grafico, serie)
       grafico, serie, titulo, ano AS ano_mais_recente, valor, unidade, eh_estimado, fonte,
       serie || ' (' || ano || ')' AS rotulo
FROM bi.painel_serie
WHERE valor IS NOT NULL
ORDER BY grafico, serie, ano DESC;
COMMENT ON VIEW bi.painel_destaque IS 'Valor mais recente de cada série do painel, para cartões (ex.: matrículas em 2025).';
COMMENT ON COLUMN bi.painel_destaque.grafico IS 'Identificador do gráfico de origem.';
COMMENT ON COLUMN bi.painel_destaque.serie IS 'Série.';
COMMENT ON COLUMN bi.painel_destaque.titulo IS 'Título do gráfico de origem.';
COMMENT ON COLUMN bi.painel_destaque.ano_mais_recente IS 'Ano do valor mais recente.';
COMMENT ON COLUMN bi.painel_destaque.valor IS 'Valor mais recente.';
COMMENT ON COLUMN bi.painel_destaque.unidade IS 'Unidade.';
COMMENT ON COLUMN bi.painel_destaque.eh_estimado IS 'Usa estimativa.';
COMMENT ON COLUMN bi.painel_destaque.fonte IS 'Fonte.';
COMMENT ON COLUMN bi.painel_destaque.rotulo IS 'Série com o ano, para o rótulo do cartão.';

-- Resumo do que foi carregado (página "Sobre os dados").
CREATE VIEW bi.painel_fontes AS
SELECT f.nome AS fonte, f.orgao, s.primeiro_ano, s.ultimo_ano, s.arquivos, s.ultima_coleta::date AS ultima_coleta,
       s.ultimo_status
FROM bi.fonte_situacao s
JOIN core.dim_fonte f ON f.cod_fonte = s.cod_fonte
WHERE s.arquivos > 0;
COMMENT ON VIEW bi.painel_fontes IS 'Fontes efetivamente carregadas, com anos e data da última coleta.';
COMMENT ON COLUMN bi.painel_fontes.fonte IS 'Fonte.';
COMMENT ON COLUMN bi.painel_fontes.orgao IS 'Órgão produtor.';
COMMENT ON COLUMN bi.painel_fontes.primeiro_ano IS 'Primeiro ano coletado.';
COMMENT ON COLUMN bi.painel_fontes.ultimo_ano IS 'Último ano coletado.';
COMMENT ON COLUMN bi.painel_fontes.arquivos IS 'Arquivos ou consultas processados.';
COMMENT ON COLUMN bi.painel_fontes.ultima_coleta IS 'Data da última coleta.';
COMMENT ON COLUMN bi.painel_fontes.ultimo_status IS 'Status da última execução.';
