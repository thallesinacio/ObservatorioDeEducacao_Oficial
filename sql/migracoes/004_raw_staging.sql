-- 004 - Camadas raw e staging

-- ---------------------------------------------------------------- raw
-- Uma tabela genérica: cada linha do recorte de cada arquivo, com todas as colunas como texto.
CREATE TABLE IF NOT EXISTS raw.linha (
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo) ON DELETE CASCADE,
  tabela_origem    TEXT NOT NULL,
  num_linha        INTEGER NOT NULL,
  dados            JSONB NOT NULL,
  PRIMARY KEY (id_arquivo, tabela_origem, num_linha)
);
COMMENT ON TABLE raw.linha IS 'Camada bruta: recorte (territórios de interesse) de cada arquivo, uma linha por registro de origem, todas as colunas em texto exatamente como vieram. O arquivo inteiro fica em disco em data/raw/<fonte>/<ano>/.';
COMMENT ON COLUMN raw.linha.tabela_origem IS 'Tabela ou planilha de origem dentro do arquivo (ex.: microdados_ed_basica, Tabela_Matricula, municipios).';
COMMENT ON COLUMN raw.linha.num_linha IS 'Número da linha no arquivo de origem (1 = primeira linha de dados).';
COMMENT ON COLUMN raw.linha.dados IS 'Objeto {coluna: valor em texto} com a linha original.';

-- ---------------------------------------------------------------- staging: Censo Escolar
CREATE TABLE IF NOT EXISTS staging.censo_escola (
  ano                          SMALLINT NOT NULL,
  co_entidade                  CHAR(8) NOT NULL,
  co_municipio                 CHAR(7) NOT NULL,
  no_entidade                  TEXT,
  tp_dependencia               SMALLINT,
  tp_categoria_escola_privada  SMALLINT,
  tp_localizacao               SMALLINT,
  tp_localizacao_diferenciada  SMALLINT,
  tp_situacao_funcionamento    SMALLINT,
  no_bairro                    TEXT,
  co_distrito                  TEXT,
  in_internet                  SMALLINT,
  in_banda_larga               SMALLINT,
  in_biblioteca                SMALLINT,
  in_biblioteca_sala_leitura   SMALLINT,
  in_sala_leitura              SMALLINT,
  in_laboratorio_ciencias      SMALLINT,
  in_laboratorio_informatica   SMALLINT,
  in_quadra_esportes           SMALLINT,
  in_acessibilidade_inexistente SMALLINT,
  in_banheiro_pne              SMALLINT,
  in_agua_potavel              SMALLINT,
  in_energia_rede_publica      SMALLINT,
  in_esgoto_rede_publica       SMALLINT,
  in_sala_atendimento_especial SMALLINT,
  in_alimentacao               SMALLINT,
  tp_aee                       SMALLINT,
  versao_layout                TEXT NOT NULL,
  id_arquivo                   BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  PRIMARY KEY (ano, co_entidade)
);
COMMENT ON TABLE staging.censo_escola IS 'Cadastro e infraestrutura das escolas dos municípios de interesse, por ano do Censo Escolar (tipado). Coluna ausente no layout do ano fica nula.';

CREATE TABLE IF NOT EXISTS staging.censo_contagem (
  ano              SMALLINT NOT NULL,
  co_entidade      CHAR(8) NOT NULL,
  variavel         TEXT NOT NULL,
  valor            INTEGER,
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  PRIMARY KEY (ano, co_entidade, variavel)
);
COMMENT ON TABLE staging.censo_contagem IS 'Todas as contagens QT_* do Censo Escolar por escola e ano, em formato longo (variável, valor). Célula vazia na origem fica nula, nunca zero.';

CREATE TABLE IF NOT EXISTS staging.censo_layout (
  ano              SMALLINT NOT NULL,
  versao_layout    TEXT NOT NULL,
  variavel         TEXT NOT NULL,
  tabela_origem    TEXT NOT NULL,
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  PRIMARY KEY (ano, variavel)
);
COMMENT ON TABLE staging.censo_layout IS 'Variáveis presentes no arquivo de cada ano: permite distinguir "variável não existe no layout" (sem_dado por quebra de série) de "valor vazio".';

CREATE TABLE IF NOT EXISTS staging.censo_dicionario (
  ano              SMALLINT NOT NULL,
  variavel         TEXT NOT NULL,
  descricao        TEXT,
  tipo             TEXT,
  categorias       TEXT,
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  PRIMARY KEY (ano, variavel)
);
COMMENT ON TABLE staging.censo_dicionario IS 'Dicionário de dados do INEP (ANEXO I do ZIP do Censo Escolar), por ano.';

-- ---------------------------------------------------------------- staging: Indicadores Educacionais, Sinopse e Ideb
CREATE TABLE IF NOT EXISTS staging.inep_indicador (
  id_fonte         TEXT NOT NULL,
  ano              SMALLINT NOT NULL,
  nivel            TEXT NOT NULL,
  cod_territorio   TEXT NOT NULL,
  co_entidade      CHAR(8),
  localizacao      TEXT NOT NULL,
  rede             TEXT NOT NULL,
  coluna_origem    TEXT NOT NULL,
  rotulo_origem    TEXT,
  medida           TEXT NOT NULL,
  cod_etapa        TEXT NOT NULL,
  valor            NUMERIC(20, 6),
  valor_texto      TEXT,
  status_valor     TEXT NOT NULL,
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  UNIQUE NULLS NOT DISTINCT (id_fonte, ano, nivel, cod_territorio, co_entidade, localizacao, rede, coluna_origem)
);
COMMENT ON TABLE staging.inep_indicador IS 'Planilhas dos Indicadores Educacionais do INEP (rendimento, distorção, AFD, ATU, DSU) e tabelas da Sinopse, em formato longo. A etapa e a medida são identificadas pelo texto do cabeçalho.';

CREATE TABLE IF NOT EXISTS staging.ideb (
  edicao           SMALLINT NOT NULL,
  nivel            TEXT NOT NULL,
  cod_territorio   TEXT NOT NULL,
  co_entidade      CHAR(8),
  rede             TEXT NOT NULL,
  cod_etapa        TEXT NOT NULL,
  ano              SMALLINT NOT NULL,
  medida           TEXT NOT NULL,
  coluna_origem    TEXT NOT NULL,
  valor            NUMERIC(20, 6),
  valor_texto      TEXT,
  status_valor     TEXT NOT NULL,
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  UNIQUE NULLS NOT DISTINCT (edicao, nivel, cod_territorio, co_entidade, rede, cod_etapa, coluna_origem)
);
COMMENT ON TABLE staging.ideb IS 'Planilhas do Ideb convertidas de formato largo (anos em colunas) para longo, guardando a edição de onde cada valor veio.';

-- ---------------------------------------------------------------- staging: população, SIDRA
CREATE TABLE IF NOT EXISTS staging.populacao (
  origem           TEXT NOT NULL,
  edicao           TEXT NOT NULL,
  ano              SMALLINT NOT NULL,
  cod_territorio   TEXT NOT NULL,
  sexo             TEXT NOT NULL,
  idade            SMALLINT NOT NULL,
  populacao        INTEGER,
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  PRIMARY KEY (origem, edicao, ano, cod_territorio, sexo, idade)
);
COMMENT ON TABLE staging.populacao IS 'População por idade simples e sexo. origem: ripsa_ftp, ripsa_tabnet ou ibge_censo2022. idade 80 = 80 anos ou mais (RIPSA). sexo: M, F ou T (total).';

CREATE TABLE IF NOT EXISTS staging.sidra (
  tabela           TEXT NOT NULL,
  variavel         TEXT NOT NULL,
  cod_territorio   TEXT NOT NULL,
  ano              SMALLINT NOT NULL,
  classificacao    TEXT NOT NULL DEFAULT '',
  valor            NUMERIC(20, 4),
  valor_texto      TEXT,
  unidade          TEXT,
  status_valor     TEXT NOT NULL,
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  PRIMARY KEY (tabela, variavel, cod_territorio, ano, classificacao)
);
COMMENT ON TABLE staging.sidra IS 'Valores das tabelas do SIDRA/IBGE. classificacao guarda as categorias da consulta (ex.: c287=6558 para a idade de 1 ano).';

-- ---------------------------------------------------------------- staging: SIOPE e SICONFI
CREATE TABLE IF NOT EXISTS staging.siope_indicador (
  ano              SMALLINT NOT NULL,
  cod_territorio   TEXT NOT NULL,
  tipo             TEXT NOT NULL,
  cod_indi         INTEGER NOT NULL,
  cod_exib         TEXT,
  nom_indi         TEXT,
  nom_grupo        TEXT,
  valor            NUMERIC(20, 4),
  valor_texto      TEXT,
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  PRIMARY KEY (ano, cod_territorio, tipo, cod_indi)
);
COMMENT ON TABLE staging.siope_indicador IS 'Indicadores legais e de gasto declarados ao SIOPE (6º bimestre).';

CREATE TABLE IF NOT EXISTS staging.siope_receita (
  ano              SMALLINT NOT NULL,
  cod_territorio   TEXT NOT NULL,
  cod_rubrica      TEXT NOT NULL,
  nom_item         TEXT,
  idn_clas         TEXT,
  coluna           TEXT NOT NULL,
  num_nive         TEXT,
  num_orde         TEXT,
  linha            INTEGER NOT NULL,
  valor            NUMERIC(20, 2),
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  PRIMARY KEY (ano, cod_territorio, linha)
);
COMMENT ON TABLE staging.siope_receita IS 'Receitas declaradas ao SIOPE (rubrica, coluna e valor). A mesma rubrica pode aparecer mais de uma vez com NUM_ORDE igual, por isso a chave é a posição da linha na resposta da API (linha).';

CREATE TABLE IF NOT EXISTS staging.siope_despesa_funcao (
  ano              SMALLINT NOT NULL,
  cod_territorio   TEXT NOT NULL,
  num_orde         TEXT NOT NULL,
  subfuncao        TEXT NOT NULL,
  empenhada        NUMERIC(20, 2),
  liquidada        NUMERIC(20, 2),
  paga             NUMERIC(20, 2),
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  PRIMARY KEY (ano, cod_territorio, num_orde, subfuncao)
);
COMMENT ON TABLE staging.siope_despesa_funcao IS 'Despesas da função Educação por subfunção declaradas ao SIOPE.';

CREATE TABLE IF NOT EXISTS staging.siope_dados_gerais (
  ano                    SMALLINT NOT NULL,
  cod_territorio         TEXT NOT NULL,
  populacao_declarada    INTEGER,
  desp_educacao_orcada   NUMERIC(20, 2),
  desp_educacao_empenhada NUMERIC(20, 2),
  desp_educacao_liquidada NUMERIC(20, 2),
  desp_educacao_paga     NUMERIC(20, 2),
  desp_total_liquidada   NUMERIC(20, 2),
  receita_realizada      NUMERIC(20, 2),
  data_declaracao        DATE,
  id_arquivo             BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  PRIMARY KEY (ano, cod_territorio)
);
COMMENT ON TABLE staging.siope_dados_gerais IS 'Totais declarados ao SIOPE (sem dados do responsável pela declaração).';

CREATE TABLE IF NOT EXISTS staging.siconfi (
  demonstrativo    TEXT NOT NULL,
  ano              SMALLINT NOT NULL,
  periodo          SMALLINT NOT NULL,
  cod_territorio   TEXT NOT NULL,
  anexo            TEXT NOT NULL,
  rotulo           TEXT NOT NULL DEFAULT '',
  coluna           TEXT NOT NULL,
  cod_conta        TEXT NOT NULL,
  conta            TEXT NOT NULL,
  valor            NUMERIC(20, 2),
  id_arquivo       BIGINT NOT NULL REFERENCES etl.etl_arquivo (id_arquivo),
  PRIMARY KEY (demonstrativo, ano, periodo, cod_territorio, anexo, rotulo, coluna, cod_conta, conta)
);
COMMENT ON TABLE staging.siconfi IS 'Itens das declarações fiscais do SICONFI (DCA e RREO) dos municípios de interesse.';
