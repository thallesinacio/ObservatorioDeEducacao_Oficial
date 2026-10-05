-- Camada bi: visões de qualidade do dado (para a página "Sobre os dados" do painel).

CREATE VIEW bi.cobertura_indicador_ano AS
WITH base AS (
  SELECT i.cod_indicador, t.cod_territorio, a.ano
  FROM core.dim_indicador i
  CROSS JOIN core.dim_territorio t
  CROSS JOIN core.dim_tempo a
  WHERE (t.eh_alvo OR t.eh_comparacao) AND t.nivel = 'municipio'
    AND a.ano BETWEEN 2015 AND EXTRACT(YEAR FROM current_date)::int
),
fatos AS (
  SELECT cod_indicador, cod_territorio, ano, count(*) AS linhas, count(valor) AS com_valor,
         count(*) FILTER (WHERE status_valor = 'estimado') AS estimados
  FROM core.v_fato_indicador WHERE co_entidade IS NULL
  GROUP BY cod_indicador, cod_territorio, ano
)
SELECT b.cod_indicador, b.cod_territorio, b.ano, COALESCE(f.linhas, 0) AS linhas, COALESCE(f.com_valor, 0) AS com_valor,
       CASE WHEN COALESCE(f.com_valor, 0) > 0 AND f.estimados > 0 THEN 'com valor (estimado)'
            WHEN COALESCE(f.com_valor, 0) > 0 THEN 'com valor'
            WHEN COALESCE(f.linhas, 0) > 0 THEN 'lacuna registrada'
            WHEN i.cobertura = 'manual_futura' THEN 'coleta manual (etapa futura)'
            WHEN i.cobertura = 'pendente' THEN 'fonte pendente'
            ELSE 'não carregado' END AS situacao
FROM base b
JOIN core.dim_indicador i USING (cod_indicador)
LEFT JOIN fatos f USING (cod_indicador, cod_territorio, ano);
COMMENT ON VIEW bi.cobertura_indicador_ano IS 'Matriz de cobertura: para cada indicador, município (alvo e comparação) e ano, se há valor, lacuna registrada ou nada.';
COMMENT ON COLUMN bi.cobertura_indicador_ano.cod_indicador IS 'Indicador.';
COMMENT ON COLUMN bi.cobertura_indicador_ano.cod_territorio IS 'Município.';
COMMENT ON COLUMN bi.cobertura_indicador_ano.ano IS 'Ano.';
COMMENT ON COLUMN bi.cobertura_indicador_ano.linhas IS 'Linhas no fato (todas as etapas e recortes).';
COMMENT ON COLUMN bi.cobertura_indicador_ano.com_valor IS 'Linhas com valor.';
COMMENT ON COLUMN bi.cobertura_indicador_ano.situacao IS 'com valor, com valor (estimado), lacuna registrada, fonte pendente, coleta manual ou não carregado.';

CREATE VIEW bi.qualidade_status AS
SELECT cod_indicador, cod_territorio, status_valor, count(*) AS linhas,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY cod_indicador, cod_territorio), 1) AS percentual
FROM core.v_fato_indicador
GROUP BY cod_indicador, cod_territorio, status_valor;
COMMENT ON VIEW bi.qualidade_status IS 'Percentual de linhas por status (observado, estimado, sem_dado...) em cada indicador e território.';
COMMENT ON COLUMN bi.qualidade_status.cod_indicador IS 'Indicador.';
COMMENT ON COLUMN bi.qualidade_status.cod_territorio IS 'Território.';
COMMENT ON COLUMN bi.qualidade_status.status_valor IS 'Status.';
COMMENT ON COLUMN bi.qualidade_status.linhas IS 'Quantidade de linhas.';
COMMENT ON COLUMN bi.qualidade_status.percentual IS 'Percentual das linhas do indicador no território.';

CREATE VIEW bi.fonte_situacao AS
WITH arq AS (
  SELECT id_fonte, max(data_coleta) AS ultima_coleta, count(*) FILTER (WHERE processado_em IS NOT NULL) AS arquivos,
         min(ano_referencia) AS primeiro_ano, max(ano_referencia) AS ultimo_ano
  FROM etl.etl_arquivo WHERE NOT arquivo_removido GROUP BY id_fonte
),
exe AS (
  SELECT DISTINCT ON (id_fonte) id_fonte, job, status, inicio, fim, left(mensagem_erro, 500) AS mensagem
  FROM etl.etl_execucao WHERE id_fonte IS NOT NULL ORDER BY id_fonte, inicio DESC
)
SELECT f.cod_fonte, f.nome, f.prioridade, a.ultima_coleta, a.arquivos, a.primeiro_ano, a.ultimo_ano,
       e.job AS ultima_tarefa, e.status AS ultimo_status, e.fim AS ultima_execucao, e.mensagem AS ultima_mensagem,
       v.id_versao AS versao_vigente, v.criado_em AS versao_criada_em
FROM core.dim_fonte f
LEFT JOIN arq a ON a.id_fonte = f.cod_fonte
LEFT JOIN exe e ON e.id_fonte = f.cod_fonte
LEFT JOIN etl.versao_dados v ON v.id_fonte = f.cod_fonte AND v.vigente;
COMMENT ON VIEW bi.fonte_situacao IS 'Situação de cada fonte: última coleta, anos disponíveis, última execução e versão vigente.';
COMMENT ON COLUMN bi.fonte_situacao.cod_fonte IS 'Fonte.';
COMMENT ON COLUMN bi.fonte_situacao.nome IS 'Nome da fonte.';
COMMENT ON COLUMN bi.fonte_situacao.prioridade IS 'Prioridade (P1, P2, P3).';
COMMENT ON COLUMN bi.fonte_situacao.ultima_coleta IS 'Momento da coleta mais recente.';
COMMENT ON COLUMN bi.fonte_situacao.arquivos IS 'Arquivos/consultas processados.';
COMMENT ON COLUMN bi.fonte_situacao.primeiro_ano IS 'Primeiro ano coletado.';
COMMENT ON COLUMN bi.fonte_situacao.ultimo_ano IS 'Último ano coletado.';
COMMENT ON COLUMN bi.fonte_situacao.ultima_tarefa IS 'Última tarefa executada (coletar, transformar...).';
COMMENT ON COLUMN bi.fonte_situacao.ultimo_status IS 'Status da última tarefa.';
COMMENT ON COLUMN bi.fonte_situacao.ultima_execucao IS 'Fim da última tarefa.';
COMMENT ON COLUMN bi.fonte_situacao.ultima_mensagem IS 'Alertas ou erro da última tarefa (resumo).';
COMMENT ON COLUMN bi.fonte_situacao.versao_vigente IS 'Versão de dados exibida.';
COMMENT ON COLUMN bi.fonte_situacao.versao_criada_em IS 'Quando a versão vigente foi criada.';

CREATE VIEW bi.dq_resultado AS
SELECT r.teste, r.tabela, r.coluna, r.severidade, r.resultado, r.ocorrencias, r.detalhe, r.executado_em
FROM etl.dq_resultado r
WHERE r.id_execucao = (SELECT max(id_execucao) FROM etl.dq_resultado);
COMMENT ON VIEW bi.dq_resultado IS 'Resultado da última rodada dos testes de qualidade.';
COMMENT ON COLUMN bi.dq_resultado.teste IS 'Nome do teste.';
COMMENT ON COLUMN bi.dq_resultado.tabela IS 'Tabela testada.';
COMMENT ON COLUMN bi.dq_resultado.coluna IS 'Coluna ou indicador testado.';
COMMENT ON COLUMN bi.dq_resultado.severidade IS 'info, alerta ou erro.';
COMMENT ON COLUMN bi.dq_resultado.resultado IS 'ok ou falha.';
COMMENT ON COLUMN bi.dq_resultado.ocorrencias IS 'Linhas que violaram a regra.';
COMMENT ON COLUMN bi.dq_resultado.detalhe IS 'Explicação e exemplos.';
COMMENT ON COLUMN bi.dq_resultado.executado_em IS 'Momento do teste.';
