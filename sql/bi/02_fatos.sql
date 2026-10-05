-- Camada bi: fatos, só a versão vigente. Relacione no Power BI pelas colunas cod_* e ano.

CREATE VIEW bi.fato_indicador AS
SELECT f.cod_indicador, f.cod_territorio, f.co_entidade, f.ano, f.cod_etapa, f.cod_recorte,
       f.valor, f.numerador, f.denominador, f.status_valor,
       f.status_valor IN ('sem_dado', 'nao_se_aplica') AS eh_lacuna,
       f.status_valor = 'estimado' AS eh_estimado,
       f.status_valor = 'proxy_estadual' AS eh_proxy_estadual,
       f.eh_calculo_proprio,
       fo.cod_fonte, f.data_coleta, f.id_versao, f.referencia, f.nota,
       CASE WHEN f.co_entidade IS NULL THEN 'territorio' ELSE 'escola' END AS nivel
FROM core.v_fato_indicador f
JOIN core.dim_fonte fo USING (id_fonte);
COMMENT ON VIEW bi.fato_indicador IS 'Fato central: um valor por indicador x território (ou escola) x ano x etapa x recorte, versão vigente. Lacuna tem valor vazio e status sem_dado/nao_se_aplica (nunca zero).';
COMMENT ON COLUMN bi.fato_indicador.cod_indicador IS 'Indicador (bi.dim_indicador).';
COMMENT ON COLUMN bi.fato_indicador.cod_territorio IS 'Território (bi.dim_territorio).';
COMMENT ON COLUMN bi.fato_indicador.co_entidade IS 'Escola (bi.dim_escola); vazio = agregado do território.';
COMMENT ON COLUMN bi.fato_indicador.ano IS 'Ano (bi.dim_tempo).';
COMMENT ON COLUMN bi.fato_indicador.cod_etapa IS 'Etapa (bi.dim_etapa).';
COMMENT ON COLUMN bi.fato_indicador.cod_recorte IS 'Recorte (bi.dim_recorte).';
COMMENT ON COLUMN bi.fato_indicador.valor IS 'Valor do indicador. Vazio quando é lacuna.';
COMMENT ON COLUMN bi.fato_indicador.numerador IS 'Numerador usado (quando aplicável).';
COMMENT ON COLUMN bi.fato_indicador.denominador IS 'Denominador usado (quando aplicável).';
COMMENT ON COLUMN bi.fato_indicador.status_valor IS 'Status do valor (bi.dim_status).';
COMMENT ON COLUMN bi.fato_indicador.eh_lacuna IS 'Verdadeiro para sem_dado e nao_se_aplica.';
COMMENT ON COLUMN bi.fato_indicador.eh_estimado IS 'Verdadeiro quando o valor usa estimativa (ex.: população projetada).';
COMMENT ON COLUMN bi.fato_indicador.eh_proxy_estadual IS 'Verdadeiro quando o valor é da UF usado no lugar do municipal.';
COMMENT ON COLUMN bi.fato_indicador.eh_calculo_proprio IS 'Verdadeiro quando é cálculo do Observatório (não é número oficial).';
COMMENT ON COLUMN bi.fato_indicador.cod_fonte IS 'Fonte do valor (bi.dim_fonte).';
COMMENT ON COLUMN bi.fato_indicador.data_coleta IS 'Data da coleta mais recente das entradas.';
COMMENT ON COLUMN bi.fato_indicador.id_versao IS 'Versão do cálculo (etl.versao_dados).';
COMMENT ON COLUMN bi.fato_indicador.referencia IS 'Procedência detalhada (arquivo, coluna, edição da estimativa).';
COMMENT ON COLUMN bi.fato_indicador.nota IS 'Observação sobre o valor.';
COMMENT ON COLUMN bi.fato_indicador.nivel IS 'territorio ou escola.';

CREATE VIEW bi.fato_matricula AS
SELECT m.ano, m.co_entidade, m.cod_territorio, m.cod_etapa, m.cod_recorte, m.qt_matriculas, m.status_valor,
       m.variavel_origem, m.data_coleta
FROM core.v_fato_matricula m;
COMMENT ON VIEW bi.fato_matricula IS 'Matrículas por escola, ano, etapa e recorte (microdados do Censo Escolar), versão vigente.';
COMMENT ON COLUMN bi.fato_matricula.ano IS 'Ano do Censo.';
COMMENT ON COLUMN bi.fato_matricula.co_entidade IS 'Escola.';
COMMENT ON COLUMN bi.fato_matricula.cod_territorio IS 'Município.';
COMMENT ON COLUMN bi.fato_matricula.cod_etapa IS 'Etapa.';
COMMENT ON COLUMN bi.fato_matricula.cod_recorte IS 'Recorte (sexo, cor/raça, faixa etária, turno...).';
COMMENT ON COLUMN bi.fato_matricula.qt_matriculas IS 'Matrículas; vazio = célula vazia na origem.';
COMMENT ON COLUMN bi.fato_matricula.status_valor IS 'observado ou sem_dado.';
COMMENT ON COLUMN bi.fato_matricula.variavel_origem IS 'Variável do Censo.';
COMMENT ON COLUMN bi.fato_matricula.data_coleta IS 'Data da coleta.';

CREATE VIEW bi.fato_docente AS
SELECT d.ano, d.cod_territorio, d.co_entidade, d.cod_etapa, d.cod_recorte, d.qt_docentes, d.status_valor,
       f.cod_fonte, d.variavel_origem, d.data_coleta
FROM core.v_fato_docente d JOIN core.dim_fonte f USING (id_fonte);
COMMENT ON VIEW bi.fato_docente IS 'Docentes por escola (Censo, soma conta duplicado quem atua em mais de uma escola) ou por município (Sinopse, docente único), versão vigente.';
COMMENT ON COLUMN bi.fato_docente.ano IS 'Ano do Censo.';
COMMENT ON COLUMN bi.fato_docente.cod_territorio IS 'Território.';
COMMENT ON COLUMN bi.fato_docente.co_entidade IS 'Escola (vazio para número municipal da Sinopse).';
COMMENT ON COLUMN bi.fato_docente.cod_etapa IS 'Etapa.';
COMMENT ON COLUMN bi.fato_docente.cod_recorte IS 'Recorte (ex.: escolaridade:mestrado).';
COMMENT ON COLUMN bi.fato_docente.qt_docentes IS 'Número de docentes.';
COMMENT ON COLUMN bi.fato_docente.status_valor IS 'observado ou sem_dado.';
COMMENT ON COLUMN bi.fato_docente.cod_fonte IS 'censo_escolar ou sinopse_estatistica.';
COMMENT ON COLUMN bi.fato_docente.variavel_origem IS 'Variável/coluna de origem.';
COMMENT ON COLUMN bi.fato_docente.data_coleta IS 'Data da coleta.';

CREATE VIEW bi.fato_rendimento AS
SELECT r.ano, r.cod_territorio, r.co_entidade, r.cod_etapa, r.cod_recorte, r.medida, r.valor, r.status_valor,
       f.cod_fonte, r.data_coleta
FROM core.v_fato_rendimento r JOIN core.dim_fonte f USING (id_fonte);
COMMENT ON VIEW bi.fato_rendimento IS 'Taxas de rendimento e distorção idade-série do INEP (formato longo), versão vigente.';
COMMENT ON COLUMN bi.fato_rendimento.ano IS 'Ano.';
COMMENT ON COLUMN bi.fato_rendimento.cod_territorio IS 'Território.';
COMMENT ON COLUMN bi.fato_rendimento.co_entidade IS 'Escola (vazio = território).';
COMMENT ON COLUMN bi.fato_rendimento.cod_etapa IS 'Etapa / ano / série.';
COMMENT ON COLUMN bi.fato_rendimento.cod_recorte IS 'Rede x localização.';
COMMENT ON COLUMN bi.fato_rendimento.medida IS 'aprovacao, reprovacao, abandono ou distorcao_idade_serie.';
COMMENT ON COLUMN bi.fato_rendimento.valor IS 'Taxa em %.';
COMMENT ON COLUMN bi.fato_rendimento.status_valor IS 'observado, sem_dado ou nao_se_aplica.';
COMMENT ON COLUMN bi.fato_rendimento.cod_fonte IS 'Fonte.';
COMMENT ON COLUMN bi.fato_rendimento.data_coleta IS 'Data da coleta.';

CREATE VIEW bi.fato_avaliacao AS
SELECT a.ano, a.cod_territorio, a.co_entidade, a.cod_etapa, a.cod_recorte, a.componente, a.instrumento, a.edicao,
       a.valor, a.status_valor, a.data_coleta,
       a.edicao = max(a.edicao) OVER (PARTITION BY a.ano, a.cod_territorio, a.co_entidade, a.cod_etapa, a.cod_recorte,
                                                   a.componente) AS eh_edicao_mais_recente
FROM core.v_fato_avaliacao a;
COMMENT ON VIEW bi.fato_avaliacao IS 'Ideb, metas, notas do Saeb e taxas de aprovação usadas no Ideb, com todas as edições carregadas. Filtre eh_edicao_mais_recente para ter um valor por chave.';
COMMENT ON COLUMN bi.fato_avaliacao.ano IS 'Ano de aplicação.';
COMMENT ON COLUMN bi.fato_avaliacao.cod_territorio IS 'Território.';
COMMENT ON COLUMN bi.fato_avaliacao.co_entidade IS 'Escola (vazio = território).';
COMMENT ON COLUMN bi.fato_avaliacao.cod_etapa IS 'Etapa avaliada.';
COMMENT ON COLUMN bi.fato_avaliacao.cod_recorte IS 'Rede.';
COMMENT ON COLUMN bi.fato_avaliacao.componente IS 'ideb, meta_ideb, matematica, lingua_portuguesa, nota_padronizada, indicador_rendimento, aprovacao.';
COMMENT ON COLUMN bi.fato_avaliacao.instrumento IS 'Instrumento de medida.';
COMMENT ON COLUMN bi.fato_avaliacao.edicao IS 'Edição da divulgação de onde o valor foi lido.';
COMMENT ON COLUMN bi.fato_avaliacao.valor IS 'Valor publicado.';
COMMENT ON COLUMN bi.fato_avaliacao.status_valor IS 'observado ou sem_dado.';
COMMENT ON COLUMN bi.fato_avaliacao.data_coleta IS 'Data da coleta.';
COMMENT ON COLUMN bi.fato_avaliacao.eh_edicao_mais_recente IS 'Verdadeiro para o valor da edição mais recente.';

CREATE VIEW bi.fato_financiamento AS
SELECT x.ano, x.cod_territorio, f.cod_fonte, x.demonstrativo, x.rubrica_codigo, x.rubrica_nome, x.coluna, x.ordem,
       x.valor, x.data_coleta
FROM core.v_fato_financiamento x JOIN core.dim_fonte f USING (id_fonte);
COMMENT ON VIEW bi.fato_financiamento IS 'Receitas e despesas declaradas ao SIOPE e à DCA (SICONFI), versão vigente, em R$ correntes.';
COMMENT ON COLUMN bi.fato_financiamento.ano IS 'Exercício.';
COMMENT ON COLUMN bi.fato_financiamento.cod_territorio IS 'Município.';
COMMENT ON COLUMN bi.fato_financiamento.cod_fonte IS 'siope ou siconfi.';
COMMENT ON COLUMN bi.fato_financiamento.demonstrativo IS 'Demonstrativo de origem.';
COMMENT ON COLUMN bi.fato_financiamento.rubrica_codigo IS 'Código da rubrica/conta.';
COMMENT ON COLUMN bi.fato_financiamento.rubrica_nome IS 'Nome da rubrica/conta.';
COMMENT ON COLUMN bi.fato_financiamento.coluna IS 'Coluna do demonstrativo (ex.: Receitas Realizadas, Despesas Liquidadas).';
COMMENT ON COLUMN bi.fato_financiamento.ordem IS 'Ordem/identificação da linha no demonstrativo.';
COMMENT ON COLUMN bi.fato_financiamento.valor IS 'Valor em R$ correntes.';
COMMENT ON COLUMN bi.fato_financiamento.data_coleta IS 'Data da coleta.';

CREATE VIEW bi.fato_populacao AS
SELECT p.ano, p.cod_territorio, p.sexo, p.idade, p.populacao, p.origem, p.edicao, p.status_valor, p.data_coleta
FROM core.v_fato_populacao p;
COMMENT ON VIEW bi.fato_populacao IS 'População por idade simples (RIPSA estimada; Censo 2022 observada), versão vigente.';
COMMENT ON COLUMN bi.fato_populacao.ano IS 'Ano.';
COMMENT ON COLUMN bi.fato_populacao.cod_territorio IS 'Município.';
COMMENT ON COLUMN bi.fato_populacao.sexo IS 'T = total.';
COMMENT ON COLUMN bi.fato_populacao.idade IS 'Idade em anos (80 = 80 ou mais na RIPSA; 100 = 100 ou mais no Censo).';
COMMENT ON COLUMN bi.fato_populacao.populacao IS 'Pessoas.';
COMMENT ON COLUMN bi.fato_populacao.origem IS 'ripsa_ftp, ripsa_tabnet ou ibge_censo2022.';
COMMENT ON COLUMN bi.fato_populacao.edicao IS 'Edição da estimativa.';
COMMENT ON COLUMN bi.fato_populacao.status_valor IS 'estimado ou observado.';
COMMENT ON COLUMN bi.fato_populacao.data_coleta IS 'Data da coleta.';

CREATE VIEW bi.meta_pme AS
SELECT meta_pme, indicador_pme, ano, cod_indicador, valor_publicado, valor_publicado_texto, valor_meta,
       situacao_declarada, fonte_declarada, documento, observacao
FROM core.fato_meta_pme;
COMMENT ON VIEW bi.meta_pme IS 'Série do PME como publicada no relatório de avaliação (preenchimento manual em etapa futura).';
COMMENT ON COLUMN bi.meta_pme.meta_pme IS 'Meta do PME.';
COMMENT ON COLUMN bi.meta_pme.indicador_pme IS 'Indicador do PME.';
COMMENT ON COLUMN bi.meta_pme.ano IS 'Ano.';
COMMENT ON COLUMN bi.meta_pme.cod_indicador IS 'Indicador equivalente do Observatório.';
COMMENT ON COLUMN bi.meta_pme.valor_publicado IS 'Valor publicado.';
COMMENT ON COLUMN bi.meta_pme.valor_publicado_texto IS 'Valor como aparece no relatório.';
COMMENT ON COLUMN bi.meta_pme.valor_meta IS 'Meta.';
COMMENT ON COLUMN bi.meta_pme.situacao_declarada IS 'Situação declarada.';
COMMENT ON COLUMN bi.meta_pme.fonte_declarada IS 'Fonte informada no relatório.';
COMMENT ON COLUMN bi.meta_pme.documento IS 'Documento de origem.';
COMMENT ON COLUMN bi.meta_pme.observacao IS 'Observação.';
