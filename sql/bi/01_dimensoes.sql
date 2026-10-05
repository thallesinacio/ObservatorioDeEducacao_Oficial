-- Camada bi: dimensões (esquema estrela para o Power BI). Chaves de uma coluna só, em texto.
-- Este arquivo é executado por "db migrar" depois de recriar o esquema bi.

CREATE VIEW bi.dim_territorio AS
SELECT cod_territorio, nome, nivel, sg_uf, cod_uf, cod_municipio_6, eh_alvo, eh_comparacao,
       CASE nivel WHEN 'municipio' THEN nome || ' (' || sg_uf || ')' ELSE nome END AS nome_exibicao,
       CASE WHEN eh_alvo THEN 1 WHEN nivel = 'municipio' THEN 2 WHEN nivel = 'uf' THEN 3 ELSE 4 END AS ordem
FROM core.dim_territorio;
COMMENT ON VIEW bi.dim_territorio IS 'Territórios: município-alvo, municípios de comparação, UF e Brasil. Chave: cod_territorio.';
COMMENT ON COLUMN bi.dim_territorio.cod_territorio IS 'Chave. Código IBGE em texto (7 dígitos município, 2 UF, "1" Brasil).';
COMMENT ON COLUMN bi.dim_territorio.nome IS 'Nome do território.';
COMMENT ON COLUMN bi.dim_territorio.nivel IS 'municipio, uf ou brasil.';
COMMENT ON COLUMN bi.dim_territorio.sg_uf IS 'Sigla da UF.';
COMMENT ON COLUMN bi.dim_territorio.cod_uf IS 'Código IBGE da UF.';
COMMENT ON COLUMN bi.dim_territorio.cod_municipio_6 IS 'Código do município com 6 dígitos (DATASUS/SIOPE).';
COMMENT ON COLUMN bi.dim_territorio.eh_alvo IS 'Município-alvo do Observatório.';
COMMENT ON COLUMN bi.dim_territorio.eh_comparacao IS 'Território de comparação.';
COMMENT ON COLUMN bi.dim_territorio.nome_exibicao IS 'Nome com a UF, para rótulos de gráfico.';
COMMENT ON COLUMN bi.dim_territorio.ordem IS 'Ordem sugerida de exibição (alvo primeiro).';

CREATE VIEW bi.dim_tempo AS
SELECT ano, rotulo, data_referencia_censo, eh_ano_pme FROM core.dim_tempo;
COMMENT ON VIEW bi.dim_tempo IS 'Anos. Chave: ano.';
COMMENT ON COLUMN bi.dim_tempo.ano IS 'Chave. Ano de referência.';
COMMENT ON COLUMN bi.dim_tempo.rotulo IS 'Rótulo do ano.';
COMMENT ON COLUMN bi.dim_tempo.data_referencia_censo IS 'Data de referência do Censo Escolar no ano.';
COMMENT ON COLUMN bi.dim_tempo.eh_ano_pme IS 'Ano da vigência do PME 2015-2025.';

CREATE VIEW bi.dim_etapa AS
SELECT cod_etapa, nome, faixa_etaria_referencia, agrupamento, ordem FROM core.dim_etapa;
COMMENT ON VIEW bi.dim_etapa IS 'Etapas e modalidades de ensino. Chave: cod_etapa ("total" = não se aplica).';
COMMENT ON COLUMN bi.dim_etapa.cod_etapa IS 'Chave. Código da etapa.';
COMMENT ON COLUMN bi.dim_etapa.nome IS 'Nome da etapa.';
COMMENT ON COLUMN bi.dim_etapa.faixa_etaria_referencia IS 'Faixa etária de referência.';
COMMENT ON COLUMN bi.dim_etapa.agrupamento IS 'Etapa-mãe (para hierarquia no Power BI).';
COMMENT ON COLUMN bi.dim_etapa.ordem IS 'Ordem de exibição (use "Classificar por coluna").';

CREATE VIEW bi.dim_recorte AS
SELECT r.cod_recorte, r.rotulo, COALESCE(r.rede, 'todas') AS rede, COALESCE(r.localizacao, 'todas') AS localizacao,
       r.tipo_outro, r.valor_outro, r.ordem
FROM core.dim_recorte r;
COMMENT ON VIEW bi.dim_recorte IS 'Recortes (rede, localização e um terceiro eixo). Chave: cod_recorte ("total" = sem recorte).';
COMMENT ON COLUMN bi.dim_recorte.cod_recorte IS 'Chave. Ex.: total, rede:municipal, rede:publica|localizacao:rural, raca_cor:parda.';
COMMENT ON COLUMN bi.dim_recorte.rotulo IS 'Rótulo legível do recorte.';
COMMENT ON COLUMN bi.dim_recorte.rede IS 'Rede do recorte ("todas" quando não há recorte de rede).';
COMMENT ON COLUMN bi.dim_recorte.localizacao IS 'Localização do recorte ("todas" quando não há).';
COMMENT ON COLUMN bi.dim_recorte.tipo_outro IS 'Terceiro eixo (sexo, raca_cor, porte, subfuncao, escolaridade, faixa_populacao...).';
COMMENT ON COLUMN bi.dim_recorte.valor_outro IS 'Valor do terceiro eixo.';
COMMENT ON COLUMN bi.dim_recorte.ordem IS 'Ordem de exibição.';

CREATE VIEW bi.dim_fonte AS
SELECT cod_fonte, nome, orgao, prioridade, url, tipo_acesso, formato, periodicidade, anos_disponiveis, licenca,
       latencia_tipica, observacoes
FROM core.dim_fonte;
COMMENT ON VIEW bi.dim_fonte IS 'Fontes de dados. Chave: cod_fonte.';
COMMENT ON COLUMN bi.dim_fonte.cod_fonte IS 'Chave. Identificador da fonte.';
COMMENT ON COLUMN bi.dim_fonte.nome IS 'Nome da fonte.';
COMMENT ON COLUMN bi.dim_fonte.orgao IS 'Órgão produtor.';
COMMENT ON COLUMN bi.dim_fonte.prioridade IS 'P1, P2 ou P3.';
COMMENT ON COLUMN bi.dim_fonte.url IS 'Página oficial.';
COMMENT ON COLUMN bi.dim_fonte.tipo_acesso IS 'download, api, derivado ou manual.';
COMMENT ON COLUMN bi.dim_fonte.formato IS 'Formato do arquivo/resposta.';
COMMENT ON COLUMN bi.dim_fonte.periodicidade IS 'Periodicidade de publicação.';
COMMENT ON COLUMN bi.dim_fonte.anos_disponiveis IS 'Anos disponíveis na fonte.';
COMMENT ON COLUMN bi.dim_fonte.licenca IS 'Licença/condições de uso.';
COMMENT ON COLUMN bi.dim_fonte.latencia_tipica IS 'Defasagem típica de publicação.';
COMMENT ON COLUMN bi.dim_fonte.observacoes IS 'Observações.';

CREATE VIEW bi.dim_indicador AS
SELECT i.cod_indicador, i.grupo, i.eixo, i.nome, i.definicao, i.formula, i.unidade, i.polaridade, i.meta_pme,
       i.meta_valor, i.nivel_agregacao, i.cod_fonte, f.nome AS nome_fonte, i.eh_calculo_proprio, i.cobertura,
       i.nota_metodologica, i.ordem
FROM core.dim_indicador i JOIN core.dim_fonte f USING (cod_fonte);
COMMENT ON VIEW bi.dim_indicador IS 'Catálogo de indicadores com fórmula e nota metodológica. Chave: cod_indicador.';
COMMENT ON COLUMN bi.dim_indicador.cod_indicador IS 'Chave. Código do indicador (ex.: A1, B1.aprovacao).';
COMMENT ON COLUMN bi.dim_indicador.grupo IS 'Código do plano ao qual o indicador pertence (ex.: B1).';
COMMENT ON COLUMN bi.dim_indicador.eixo IS 'Eixo temático.';
COMMENT ON COLUMN bi.dim_indicador.nome IS 'Nome do indicador.';
COMMENT ON COLUMN bi.dim_indicador.definicao IS 'Definição.';
COMMENT ON COLUMN bi.dim_indicador.formula IS 'Fórmula ou origem do número.';
COMMENT ON COLUMN bi.dim_indicador.unidade IS 'Unidade de medida.';
COMMENT ON COLUMN bi.dim_indicador.polaridade IS 'maior_melhor, menor_melhor ou neutro.';
COMMENT ON COLUMN bi.dim_indicador.meta_pme IS 'Meta/estratégia do PME relacionada.';
COMMENT ON COLUMN bi.dim_indicador.meta_valor IS 'Valor da meta do PME, quando houver.';
COMMENT ON COLUMN bi.dim_indicador.nivel_agregacao IS 'Menor nível em que o indicador existe.';
COMMENT ON COLUMN bi.dim_indicador.cod_fonte IS 'Fonte principal.';
COMMENT ON COLUMN bi.dim_indicador.nome_fonte IS 'Nome da fonte principal.';
COMMENT ON COLUMN bi.dim_indicador.eh_calculo_proprio IS 'Cálculo do Observatório (não é número oficial).';
COMMENT ON COLUMN bi.dim_indicador.cobertura IS 'automatica, pendente ou manual_futura.';
COMMENT ON COLUMN bi.dim_indicador.nota_metodologica IS 'Nota metodológica (limitações e cuidados de leitura).';
COMMENT ON COLUMN bi.dim_indicador.ordem IS 'Ordem de exibição.';

CREATE VIEW bi.dim_escola AS
SELECT e.co_entidade, e.no_entidade, e.cod_territorio,
       CASE e.tp_dependencia WHEN 1 THEN 'Federal' WHEN 2 THEN 'Estadual' WHEN 3 THEN 'Municipal' WHEN 4 THEN 'Privada' END AS rede,
       CASE e.tp_localizacao WHEN 1 THEN 'Urbana' WHEN 2 THEN 'Rural' END AS localizacao,
       COALESCE(s.rotulo, e.tp_situacao_funcionamento::text) AS situacao_funcionamento,
       e.no_bairro, e.valid_from AS primeiro_ano_atributos, e.ultimo_ano_censo
FROM core.dim_escola e
LEFT JOIN core.dim_codigo_inep s ON s.variavel = 'TP_SITUACAO_FUNCIONAMENTO' AND s.codigo = e.tp_situacao_funcionamento::text
WHERE e.eh_vigente;
COMMENT ON VIEW bi.dim_escola IS 'Escolas (atributos da versão mais recente). Chave: co_entidade. O histórico de atributos fica em core.dim_escola.';
COMMENT ON COLUMN bi.dim_escola.co_entidade IS 'Chave. Código INEP da escola (8 dígitos, texto).';
COMMENT ON COLUMN bi.dim_escola.no_entidade IS 'Nome da escola.';
COMMENT ON COLUMN bi.dim_escola.cod_territorio IS 'Município da escola.';
COMMENT ON COLUMN bi.dim_escola.rede IS 'Dependência administrativa.';
COMMENT ON COLUMN bi.dim_escola.localizacao IS 'Urbana ou Rural.';
COMMENT ON COLUMN bi.dim_escola.situacao_funcionamento IS 'Situação de funcionamento no último Censo (rótulo do dicionário do INEP).';
COMMENT ON COLUMN bi.dim_escola.no_bairro IS 'Bairro (não publicado em 2025).';
COMMENT ON COLUMN bi.dim_escola.primeiro_ano_atributos IS 'Primeiro ano com os atributos atuais.';
COMMENT ON COLUMN bi.dim_escola.ultimo_ano_censo IS 'Último ano em que a escola aparece no Censo carregado.';

CREATE VIEW bi.dim_status AS
SELECT * FROM (VALUES
  ('observado', 'Observado', 'Número publicado pela fonte ou calculado só com números observados.', false, 1),
  ('estimado', 'Estimado', 'Usa estimativa (ex.: população projetada) ou aproximação; ver nota.', false, 2),
  ('proxy_estadual', 'Proxy estadual', 'Valor da UF usado na falta do municipal.', false, 3),
  ('sem_dado', 'Sem dado', 'Lacuna: a fonte não tem o número (nunca é zero).', true, 4),
  ('nao_se_aplica', 'Não se aplica', 'Recorte sem o que medir (ex.: rede municipal no ensino médio).', true, 5)
) AS s(status_valor, rotulo, descricao, eh_lacuna, ordem);
COMMENT ON VIEW bi.dim_status IS 'Status possíveis de um valor. Chave: status_valor.';
COMMENT ON COLUMN bi.dim_status.status_valor IS 'Chave. Código do status.';
COMMENT ON COLUMN bi.dim_status.rotulo IS 'Rótulo.';
COMMENT ON COLUMN bi.dim_status.descricao IS 'O que o status significa.';
COMMENT ON COLUMN bi.dim_status.eh_lacuna IS 'Verdadeiro para sem_dado e nao_se_aplica.';
COMMENT ON COLUMN bi.dim_status.ordem IS 'Ordem de exibição.';
