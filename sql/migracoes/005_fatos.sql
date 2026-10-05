-- 005 - Fatos (esquema core)
-- Todos os fatos guardam a versão de carga (id_versao) e a data da coleta. O histórico de
-- versões fica aqui; a camada bi mostra só a versão vigente (etl.versao_dados.vigente).

CREATE TABLE IF NOT EXISTS core.fato_matricula (
  id               BIGSERIAL PRIMARY KEY,
  ano              SMALLINT NOT NULL REFERENCES core.dim_tempo (ano),
  co_entidade      CHAR(8) NOT NULL,
  cod_territorio   TEXT NOT NULL REFERENCES core.dim_territorio (cod_territorio),
  cod_etapa        TEXT NOT NULL REFERENCES core.dim_etapa (cod_etapa),
  cod_recorte      TEXT NOT NULL REFERENCES core.dim_recorte (cod_recorte),
  qt_matriculas    INTEGER,
  variavel_origem  TEXT NOT NULL,
  status_valor     TEXT NOT NULL CHECK (status_valor IN ('observado', 'sem_dado')),
  id_versao        INTEGER NOT NULL REFERENCES etl.versao_dados (id_versao),
  data_coleta      DATE NOT NULL,
  UNIQUE (ano, co_entidade, cod_etapa, cod_recorte, id_versao)
);
COMMENT ON TABLE core.fato_matricula IS 'Matrículas por escola, ano, etapa e recorte (sexo, cor/raça, faixa etária, turno, localização de residência), a partir das contagens QT_MAT_* do Censo Escolar.';
COMMENT ON COLUMN core.fato_matricula.id IS 'Chave técnica.';
COMMENT ON COLUMN core.fato_matricula.ano IS 'Ano do Censo Escolar.';
COMMENT ON COLUMN core.fato_matricula.co_entidade IS 'Código INEP da escola (8 dígitos).';
COMMENT ON COLUMN core.fato_matricula.cod_territorio IS 'Município da escola.';
COMMENT ON COLUMN core.fato_matricula.cod_etapa IS 'Etapa/modalidade (core.dim_etapa).';
COMMENT ON COLUMN core.fato_matricula.cod_recorte IS 'Recorte (core.dim_recorte); total = sem recorte.';
COMMENT ON COLUMN core.fato_matricula.qt_matriculas IS 'Número de matrículas; nulo quando a célula veio vazia (nunca zero por ausência).';
COMMENT ON COLUMN core.fato_matricula.variavel_origem IS 'Variável do Censo de onde veio o número (ex.: QT_MAT_FUND_AI).';
COMMENT ON COLUMN core.fato_matricula.status_valor IS 'observado ou sem_dado.';
COMMENT ON COLUMN core.fato_matricula.id_versao IS 'Versão de carga (etl.versao_dados).';
COMMENT ON COLUMN core.fato_matricula.data_coleta IS 'Data em que o arquivo de origem foi baixado.';
CREATE INDEX IF NOT EXISTS ix_fato_matricula_versao ON core.fato_matricula (id_versao);
CREATE INDEX IF NOT EXISTS ix_fato_matricula_consulta ON core.fato_matricula (cod_territorio, ano, cod_etapa);

CREATE TABLE IF NOT EXISTS core.fato_turma (
  id               BIGSERIAL PRIMARY KEY,
  ano              SMALLINT NOT NULL REFERENCES core.dim_tempo (ano),
  co_entidade      CHAR(8) NOT NULL,
  cod_territorio   TEXT NOT NULL REFERENCES core.dim_territorio (cod_territorio),
  cod_etapa        TEXT NOT NULL REFERENCES core.dim_etapa (cod_etapa),
  cod_recorte      TEXT NOT NULL REFERENCES core.dim_recorte (cod_recorte),
  qt_turmas        INTEGER,
  variavel_origem  TEXT NOT NULL,
  status_valor     TEXT NOT NULL CHECK (status_valor IN ('observado', 'sem_dado')),
  id_versao        INTEGER NOT NULL REFERENCES etl.versao_dados (id_versao),
  data_coleta      DATE NOT NULL,
  UNIQUE (ano, co_entidade, cod_etapa, cod_recorte, id_versao)
);
COMMENT ON TABLE core.fato_turma IS 'Turmas por escola, ano, etapa e recorte (contagens QT_TUR_* do Censo Escolar).';
COMMENT ON COLUMN core.fato_turma.id IS 'Chave técnica.';
COMMENT ON COLUMN core.fato_turma.ano IS 'Ano do Censo Escolar.';
COMMENT ON COLUMN core.fato_turma.co_entidade IS 'Código INEP da escola.';
COMMENT ON COLUMN core.fato_turma.cod_territorio IS 'Município da escola.';
COMMENT ON COLUMN core.fato_turma.cod_etapa IS 'Etapa/modalidade.';
COMMENT ON COLUMN core.fato_turma.cod_recorte IS 'Recorte (turno, tempo integral).';
COMMENT ON COLUMN core.fato_turma.qt_turmas IS 'Número de turmas.';
COMMENT ON COLUMN core.fato_turma.variavel_origem IS 'Variável do Censo de origem.';
COMMENT ON COLUMN core.fato_turma.status_valor IS 'observado ou sem_dado.';
COMMENT ON COLUMN core.fato_turma.id_versao IS 'Versão de carga.';
COMMENT ON COLUMN core.fato_turma.data_coleta IS 'Data da coleta do arquivo.';
CREATE INDEX IF NOT EXISTS ix_fato_turma_versao ON core.fato_turma (id_versao);

CREATE TABLE IF NOT EXISTS core.fato_docente (
  id               BIGSERIAL PRIMARY KEY,
  ano              SMALLINT NOT NULL REFERENCES core.dim_tempo (ano),
  cod_territorio   TEXT NOT NULL REFERENCES core.dim_territorio (cod_territorio),
  co_entidade      CHAR(8),
  cod_etapa        TEXT NOT NULL REFERENCES core.dim_etapa (cod_etapa),
  cod_recorte      TEXT NOT NULL REFERENCES core.dim_recorte (cod_recorte),
  qt_docentes      INTEGER,
  variavel_origem  TEXT NOT NULL,
  id_fonte         INTEGER NOT NULL REFERENCES core.dim_fonte (id_fonte),
  status_valor     TEXT NOT NULL CHECK (status_valor IN ('observado', 'sem_dado')),
  id_versao        INTEGER NOT NULL REFERENCES etl.versao_dados (id_versao),
  data_coleta      DATE NOT NULL,
  UNIQUE NULLS NOT DISTINCT (ano, cod_territorio, co_entidade, cod_etapa, cod_recorte, id_fonte, id_versao)
);
COMMENT ON TABLE core.fato_docente IS 'Docentes por escola (Censo Escolar, QT_DOC_*) ou por município (Sinopse Estatística, docentes únicos), por etapa e recorte (ex.: escolaridade).';
COMMENT ON COLUMN core.fato_docente.id IS 'Chave técnica.';
COMMENT ON COLUMN core.fato_docente.ano IS 'Ano do Censo Escolar.';
COMMENT ON COLUMN core.fato_docente.cod_territorio IS 'Município.';
COMMENT ON COLUMN core.fato_docente.co_entidade IS 'Código INEP da escola; nulo quando o número é municipal (Sinopse).';
COMMENT ON COLUMN core.fato_docente.cod_etapa IS 'Etapa em que o docente atua.';
COMMENT ON COLUMN core.fato_docente.cod_recorte IS 'Recorte, ex.: escolaridade:pos_graduacao, rede:municipal.';
COMMENT ON COLUMN core.fato_docente.qt_docentes IS 'Número de docentes. Somar escolas conta duas vezes o docente que atua em mais de uma.';
COMMENT ON COLUMN core.fato_docente.variavel_origem IS 'Variável ou coluna de origem.';
COMMENT ON COLUMN core.fato_docente.id_fonte IS 'Fonte (Censo Escolar ou Sinopse).';
COMMENT ON COLUMN core.fato_docente.status_valor IS 'observado ou sem_dado.';
COMMENT ON COLUMN core.fato_docente.id_versao IS 'Versão de carga.';
COMMENT ON COLUMN core.fato_docente.data_coleta IS 'Data da coleta do arquivo.';
CREATE INDEX IF NOT EXISTS ix_fato_docente_versao ON core.fato_docente (id_versao);

CREATE TABLE IF NOT EXISTS core.fato_rendimento (
  id               BIGSERIAL PRIMARY KEY,
  ano              SMALLINT NOT NULL REFERENCES core.dim_tempo (ano),
  cod_territorio   TEXT NOT NULL REFERENCES core.dim_territorio (cod_territorio),
  co_entidade      CHAR(8),
  cod_etapa        TEXT NOT NULL REFERENCES core.dim_etapa (cod_etapa),
  cod_recorte      TEXT NOT NULL REFERENCES core.dim_recorte (cod_recorte),
  medida           TEXT NOT NULL CHECK (medida IN ('aprovacao', 'reprovacao', 'abandono', 'distorcao_idade_serie')),
  valor            NUMERIC(9, 4),
  status_valor     TEXT NOT NULL CHECK (status_valor IN ('observado', 'sem_dado', 'nao_se_aplica')),
  id_fonte         INTEGER NOT NULL REFERENCES core.dim_fonte (id_fonte),
  id_versao        INTEGER NOT NULL REFERENCES etl.versao_dados (id_versao),
  data_coleta      DATE NOT NULL,
  UNIQUE NULLS NOT DISTINCT (ano, cod_territorio, co_entidade, cod_etapa, cod_recorte, medida, id_versao)
);
COMMENT ON TABLE core.fato_rendimento IS 'Taxas de rendimento (aprovação, reprovação, abandono) e de distorção idade-série publicadas pelo INEP, por território ou escola, etapa e recorte (rede x localização). Formato longo: uma linha por medida.';
COMMENT ON COLUMN core.fato_rendimento.id IS 'Chave técnica.';
COMMENT ON COLUMN core.fato_rendimento.ano IS 'Ano de referência.';
COMMENT ON COLUMN core.fato_rendimento.cod_territorio IS 'Território.';
COMMENT ON COLUMN core.fato_rendimento.co_entidade IS 'Escola; nulo quando é agregado do território.';
COMMENT ON COLUMN core.fato_rendimento.cod_etapa IS 'Etapa (inclui ano/série).';
COMMENT ON COLUMN core.fato_rendimento.cod_recorte IS 'Recorte rede x localização.';
COMMENT ON COLUMN core.fato_rendimento.medida IS 'aprovacao, reprovacao, abandono ou distorcao_idade_serie.';
COMMENT ON COLUMN core.fato_rendimento.valor IS 'Taxa em %.';
COMMENT ON COLUMN core.fato_rendimento.status_valor IS 'observado, sem_dado ou nao_se_aplica (marcador do INEP para recorte sem matrícula).';
COMMENT ON COLUMN core.fato_rendimento.id_fonte IS 'Fonte.';
COMMENT ON COLUMN core.fato_rendimento.id_versao IS 'Versão de carga.';
COMMENT ON COLUMN core.fato_rendimento.data_coleta IS 'Data da coleta do arquivo.';
CREATE INDEX IF NOT EXISTS ix_fato_rendimento_versao ON core.fato_rendimento (id_versao);

CREATE TABLE IF NOT EXISTS core.fato_avaliacao (
  id               BIGSERIAL PRIMARY KEY,
  ano              SMALLINT NOT NULL REFERENCES core.dim_tempo (ano),
  cod_territorio   TEXT NOT NULL REFERENCES core.dim_territorio (cod_territorio),
  co_entidade      CHAR(8),
  cod_etapa        TEXT NOT NULL REFERENCES core.dim_etapa (cod_etapa),
  cod_recorte      TEXT NOT NULL REFERENCES core.dim_recorte (cod_recorte),
  componente       TEXT NOT NULL,
  instrumento      TEXT NOT NULL,
  edicao           SMALLINT NOT NULL,
  valor            NUMERIC(12, 4),
  status_valor     TEXT NOT NULL CHECK (status_valor IN ('observado', 'sem_dado', 'nao_se_aplica', 'estimado')),
  id_fonte         INTEGER NOT NULL REFERENCES core.dim_fonte (id_fonte),
  id_versao        INTEGER NOT NULL REFERENCES etl.versao_dados (id_versao),
  data_coleta      DATE NOT NULL,
  UNIQUE NULLS NOT DISTINCT (ano, cod_territorio, co_entidade, cod_etapa, cod_recorte, componente, instrumento, edicao, id_versao)
);
COMMENT ON TABLE core.fato_avaliacao IS 'Resultados de avaliação (Ideb, notas do Saeb, indicador de rendimento, metas). O instrumento aplicado fica gravado para marcar quebra de série (ex.: ANA -> Saeb 2º ano -> ICA).';
COMMENT ON COLUMN core.fato_avaliacao.id IS 'Chave técnica.';
COMMENT ON COLUMN core.fato_avaliacao.ano IS 'Ano de aplicação/referência.';
COMMENT ON COLUMN core.fato_avaliacao.cod_territorio IS 'Território.';
COMMENT ON COLUMN core.fato_avaliacao.co_entidade IS 'Escola; nulo para agregado do território.';
COMMENT ON COLUMN core.fato_avaliacao.cod_etapa IS 'Etapa avaliada (fund_ai = 5º ano, fund_af = 9º ano, med = ensino médio).';
COMMENT ON COLUMN core.fato_avaliacao.cod_recorte IS 'Rede.';
COMMENT ON COLUMN core.fato_avaliacao.componente IS 'ideb, meta_ideb, matematica, lingua_portuguesa, nota_padronizada, indicador_rendimento ou aprovacao.';
COMMENT ON COLUMN core.fato_avaliacao.instrumento IS 'Instrumento de medida (ex.: Saeb/Ideb).';
COMMENT ON COLUMN core.fato_avaliacao.edicao IS 'Edição da publicação de onde o valor foi lido (o INEP revisa valores já publicados).';
COMMENT ON COLUMN core.fato_avaliacao.valor IS 'Valor publicado.';
COMMENT ON COLUMN core.fato_avaliacao.status_valor IS 'observado, sem_dado ou nao_se_aplica.';
COMMENT ON COLUMN core.fato_avaliacao.id_fonte IS 'Fonte.';
COMMENT ON COLUMN core.fato_avaliacao.id_versao IS 'Versão de carga.';
COMMENT ON COLUMN core.fato_avaliacao.data_coleta IS 'Data da coleta do arquivo.';
CREATE INDEX IF NOT EXISTS ix_fato_avaliacao_versao ON core.fato_avaliacao (id_versao);

CREATE TABLE IF NOT EXISTS core.fato_financiamento (
  id               BIGSERIAL PRIMARY KEY,
  ano              SMALLINT NOT NULL REFERENCES core.dim_tempo (ano),
  cod_territorio   TEXT NOT NULL REFERENCES core.dim_territorio (cod_territorio),
  id_fonte         INTEGER NOT NULL REFERENCES core.dim_fonte (id_fonte),
  demonstrativo    TEXT NOT NULL,
  rubrica_codigo   TEXT NOT NULL,
  rubrica_nome     TEXT NOT NULL,
  coluna           TEXT NOT NULL,
  ordem            TEXT NOT NULL DEFAULT '',
  valor            NUMERIC(20, 2),
  id_versao        INTEGER NOT NULL REFERENCES etl.versao_dados (id_versao),
  data_coleta      DATE NOT NULL,
  UNIQUE (ano, cod_territorio, id_fonte, demonstrativo, rubrica_codigo, coluna, ordem, id_versao)
);
COMMENT ON TABLE core.fato_financiamento IS 'Valores financeiros por ano, território, fonte e rubrica (SIOPE: receitas, despesas por subfunção, totais; SICONFI: DCA Anexo I-E, função 12 - Educação).';
COMMENT ON COLUMN core.fato_financiamento.id IS 'Chave técnica.';
COMMENT ON COLUMN core.fato_financiamento.ano IS 'Exercício.';
COMMENT ON COLUMN core.fato_financiamento.cod_territorio IS 'Município.';
COMMENT ON COLUMN core.fato_financiamento.id_fonte IS 'Fonte (SIOPE ou SICONFI).';
COMMENT ON COLUMN core.fato_financiamento.demonstrativo IS 'Demonstrativo de origem, ex.: SIOPE-Receita, SIOPE-Despesa-Funcao, SIOPE-Dados-Gerais, DCA-Anexo I-E.';
COMMENT ON COLUMN core.fato_financiamento.rubrica_codigo IS 'Código da rubrica/conta.';
COMMENT ON COLUMN core.fato_financiamento.rubrica_nome IS 'Nome da rubrica/conta.';
COMMENT ON COLUMN core.fato_financiamento.coluna IS 'Coluna do demonstrativo, ex.: Receitas Realizadas, Despesas Liquidadas.';
COMMENT ON COLUMN core.fato_financiamento.ordem IS 'Ordem da linha no demonstrativo (desempata rubricas repetidas).';
COMMENT ON COLUMN core.fato_financiamento.valor IS 'Valor em R$ correntes.';
COMMENT ON COLUMN core.fato_financiamento.id_versao IS 'Versão de carga.';
COMMENT ON COLUMN core.fato_financiamento.data_coleta IS 'Data da coleta.';
CREATE INDEX IF NOT EXISTS ix_fato_financiamento_versao ON core.fato_financiamento (id_versao);

CREATE TABLE IF NOT EXISTS core.fato_populacao (
  id               BIGSERIAL PRIMARY KEY,
  ano              SMALLINT NOT NULL REFERENCES core.dim_tempo (ano),
  cod_territorio   TEXT NOT NULL REFERENCES core.dim_territorio (cod_territorio),
  sexo             TEXT NOT NULL CHECK (sexo IN ('M', 'F', 'T')),
  idade            SMALLINT NOT NULL,
  populacao        INTEGER,
  origem           TEXT NOT NULL,
  edicao           TEXT NOT NULL,
  status_valor     TEXT NOT NULL CHECK (status_valor IN ('observado', 'estimado', 'sem_dado')),
  id_fonte         INTEGER NOT NULL REFERENCES core.dim_fonte (id_fonte),
  id_versao        INTEGER NOT NULL REFERENCES etl.versao_dados (id_versao),
  data_coleta      DATE NOT NULL,
  UNIQUE (ano, cod_territorio, sexo, idade, origem, edicao, id_versao)
);
COMMENT ON TABLE core.fato_populacao IS 'População por idade simples e sexo. Estimativas (RIPSA) têm status estimado; o Censo 2022, observado. A edição da estimativa fica em "edicao".';
COMMENT ON COLUMN core.fato_populacao.id IS 'Chave técnica.';
COMMENT ON COLUMN core.fato_populacao.ano IS 'Ano de referência.';
COMMENT ON COLUMN core.fato_populacao.cod_territorio IS 'Município.';
COMMENT ON COLUMN core.fato_populacao.sexo IS 'M, F ou T (total).';
COMMENT ON COLUMN core.fato_populacao.idade IS 'Idade em anos completos (80 = 80 anos ou mais na RIPSA; 100 = 100 ou mais no Censo).';
COMMENT ON COLUMN core.fato_populacao.populacao IS 'Pessoas.';
COMMENT ON COLUMN core.fato_populacao.origem IS 'ripsa_ftp, ripsa_tabnet ou ibge_censo2022.';
COMMENT ON COLUMN core.fato_populacao.edicao IS 'Edição/versão da estimativa (ex.: RIPSA 2000-2025, consulta de 2026-09-29).';
COMMENT ON COLUMN core.fato_populacao.status_valor IS 'estimado (projeção) ou observado (censo).';
COMMENT ON COLUMN core.fato_populacao.id_fonte IS 'Fonte.';
COMMENT ON COLUMN core.fato_populacao.id_versao IS 'Versão de carga.';
COMMENT ON COLUMN core.fato_populacao.data_coleta IS 'Data da coleta.';
CREATE INDEX IF NOT EXISTS ix_fato_populacao_versao ON core.fato_populacao (id_versao);

CREATE TABLE IF NOT EXISTS core.fato_indicador (
  id                 BIGSERIAL PRIMARY KEY,
  cod_indicador      TEXT NOT NULL REFERENCES core.dim_indicador (cod_indicador),
  cod_territorio     TEXT NOT NULL REFERENCES core.dim_territorio (cod_territorio),
  co_entidade        CHAR(8),
  ano                SMALLINT NOT NULL REFERENCES core.dim_tempo (ano),
  cod_etapa          TEXT NOT NULL DEFAULT 'total' REFERENCES core.dim_etapa (cod_etapa),
  cod_recorte        TEXT NOT NULL DEFAULT 'total' REFERENCES core.dim_recorte (cod_recorte),
  valor              NUMERIC(20, 4),
  numerador          NUMERIC(20, 4),
  denominador        NUMERIC(20, 4),
  status_valor       TEXT NOT NULL CHECK (status_valor IN
                       ('observado', 'estimado', 'proxy_estadual', 'sem_dado', 'nao_se_aplica')),
  eh_calculo_proprio BOOLEAN NOT NULL,
  id_fonte           INTEGER NOT NULL REFERENCES core.dim_fonte (id_fonte),
  data_coleta        DATE NOT NULL,
  id_versao          INTEGER NOT NULL REFERENCES etl.versao_dados (id_versao),
  referencia         TEXT,
  nota               TEXT,
  UNIQUE NULLS NOT DISTINCT (cod_indicador, cod_territorio, co_entidade, ano, cod_etapa, cod_recorte, id_versao),
  CHECK (status_valor <> 'sem_dado' OR valor IS NULL),
  CHECK (status_valor <> 'nao_se_aplica' OR valor IS NULL)
);
COMMENT ON TABLE core.fato_indicador IS 'Tabela central de indicadores em formato longo: indicador x território (ou escola) x ano x etapa x recorte x versão. Todo valor tem fonte, data de coleta, versão e status; numerador e denominador quando aplicável.';
COMMENT ON COLUMN core.fato_indicador.id IS 'Chave técnica.';
COMMENT ON COLUMN core.fato_indicador.cod_indicador IS 'Indicador (core.dim_indicador).';
COMMENT ON COLUMN core.fato_indicador.cod_territorio IS 'Território (município, UF ou Brasil).';
COMMENT ON COLUMN core.fato_indicador.co_entidade IS 'Código INEP da escola; nulo = agregado do território. A unicidade trata nulos como iguais (NULLS NOT DISTINCT).';
COMMENT ON COLUMN core.fato_indicador.ano IS 'Ano de referência.';
COMMENT ON COLUMN core.fato_indicador.cod_etapa IS 'Etapa/modalidade (total quando não se aplica).';
COMMENT ON COLUMN core.fato_indicador.cod_recorte IS 'Recorte (total = sem recorte).';
COMMENT ON COLUMN core.fato_indicador.valor IS 'Valor do indicador. Nulo quando status é sem_dado ou nao_se_aplica: lacuna nunca vira zero.';
COMMENT ON COLUMN core.fato_indicador.numerador IS 'Numerador usado no cálculo (quando aplicável).';
COMMENT ON COLUMN core.fato_indicador.denominador IS 'Denominador usado no cálculo (quando aplicável).';
COMMENT ON COLUMN core.fato_indicador.status_valor IS 'observado, estimado (usa estimativa populacional ou aproximação), proxy_estadual, sem_dado ou nao_se_aplica.';
COMMENT ON COLUMN core.fato_indicador.eh_calculo_proprio IS 'Verdadeiro quando o valor é cálculo do Observatório e não número oficial.';
COMMENT ON COLUMN core.fato_indicador.id_fonte IS 'Fonte principal do valor.';
COMMENT ON COLUMN core.fato_indicador.data_coleta IS 'Data da coleta mais recente entre as entradas do valor.';
COMMENT ON COLUMN core.fato_indicador.id_versao IS 'Versão do cálculo (etl.versao_dados da fonte calculo_observatorio): identifica as versões das fontes e do método usados.';
COMMENT ON COLUMN core.fato_indicador.referencia IS 'Procedência detalhada (ex.: edição da estimativa populacional, arquivo, coluna de origem).';
COMMENT ON COLUMN core.fato_indicador.nota IS 'Observação sobre o valor (ex.: aproximação usada, quebra de série).';
CREATE INDEX IF NOT EXISTS ix_fato_indicador_versao ON core.fato_indicador (id_versao);
CREATE INDEX IF NOT EXISTS ix_fato_indicador_consulta ON core.fato_indicador (cod_indicador, cod_territorio, ano);

CREATE TABLE IF NOT EXISTS core.fato_meta_pme (
  meta_pme              TEXT NOT NULL,
  indicador_pme         TEXT NOT NULL,
  ano                   SMALLINT NOT NULL REFERENCES core.dim_tempo (ano),
  cod_indicador         TEXT REFERENCES core.dim_indicador (cod_indicador),
  valor_publicado       NUMERIC(20, 4),
  valor_publicado_texto TEXT,
  valor_meta            TEXT,
  situacao_declarada    TEXT,
  fonte_declarada       TEXT,
  documento             TEXT NOT NULL DEFAULT 'Documento de Avaliação Final do PME de Juazeiro-BA (2025)',
  observacao            TEXT,
  PRIMARY KEY (indicador_pme, ano)
);
COMMENT ON TABLE core.fato_meta_pme IS 'Série do PME 2015-2025 como foi publicada no relatório de avaliação (inclusive com erros), para comparar com o valor recalculado pelo Observatório. Preenchida manualmente em etapa futura.';
COMMENT ON COLUMN core.fato_meta_pme.meta_pme IS 'Número da meta do PME (1 a 20).';
COMMENT ON COLUMN core.fato_meta_pme.indicador_pme IS 'Indicador do PME (ex.: 1A, 3B).';
COMMENT ON COLUMN core.fato_meta_pme.ano IS 'Ano.';
COMMENT ON COLUMN core.fato_meta_pme.cod_indicador IS 'Indicador equivalente do Observatório (quando houver).';
COMMENT ON COLUMN core.fato_meta_pme.valor_publicado IS 'Valor numérico publicado no relatório.';
COMMENT ON COLUMN core.fato_meta_pme.valor_publicado_texto IS 'Valor como aparece no relatório (ex.: "Oscilante", "Sem dados").';
COMMENT ON COLUMN core.fato_meta_pme.valor_meta IS 'Meta do PME.';
COMMENT ON COLUMN core.fato_meta_pme.situacao_declarada IS 'Situação declarada no relatório (alcançada, não alcançada...).';
COMMENT ON COLUMN core.fato_meta_pme.fonte_declarada IS 'Fonte informada no relatório.';
COMMENT ON COLUMN core.fato_meta_pme.documento IS 'Documento de onde o valor foi transcrito.';
COMMENT ON COLUMN core.fato_meta_pme.observacao IS 'Observação (ex.: inconsistência entre quadros do relatório).';
