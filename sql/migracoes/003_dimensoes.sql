-- 003 - Dimensões (esquema core)

CREATE TABLE IF NOT EXISTS core.dim_territorio (
  cod_territorio   TEXT PRIMARY KEY,
  nome             TEXT NOT NULL,
  nivel            TEXT NOT NULL CHECK (nivel IN ('municipio', 'uf', 'brasil')),
  sg_uf            CHAR(2),
  cod_uf           CHAR(2),
  cod_municipio_6  CHAR(6),
  eh_alvo          BOOLEAN NOT NULL DEFAULT false,
  eh_comparacao    BOOLEAN NOT NULL DEFAULT false
);
COMMENT ON TABLE core.dim_territorio IS 'Territórios: municípios (código IBGE de 7 dígitos), UFs (2 dígitos) e Brasil (código 1, convenção do SIDRA). Generaliza a dim_municipio do plano técnico para acomodar os comparadores.';
COMMENT ON COLUMN core.dim_territorio.cod_territorio IS 'Código IBGE como texto: 7 dígitos para município, 2 para UF, "1" para Brasil.';
COMMENT ON COLUMN core.dim_territorio.nome IS 'Nome do território.';
COMMENT ON COLUMN core.dim_territorio.nivel IS 'municipio, uf ou brasil.';
COMMENT ON COLUMN core.dim_territorio.sg_uf IS 'Sigla da UF (vazio para Brasil).';
COMMENT ON COLUMN core.dim_territorio.cod_uf IS 'Código IBGE da UF (2 dígitos).';
COMMENT ON COLUMN core.dim_territorio.cod_municipio_6 IS 'Código do município com 6 dígitos (sem dígito verificador), usado por DATASUS e SIOPE.';
COMMENT ON COLUMN core.dim_territorio.eh_alvo IS 'Município-alvo do Observatório (config/projeto.yaml).';
COMMENT ON COLUMN core.dim_territorio.eh_comparacao IS 'Território carregado só para comparação.';

CREATE TABLE IF NOT EXISTS core.dim_tempo (
  ano                     SMALLINT PRIMARY KEY,
  data_referencia_censo   DATE NOT NULL,
  rotulo                  TEXT NOT NULL,
  eh_ano_pme              BOOLEAN NOT NULL
);
COMMENT ON TABLE core.dim_tempo IS 'Anos de referência.';
COMMENT ON COLUMN core.dim_tempo.ano IS 'Ano de referência dos dados.';
COMMENT ON COLUMN core.dim_tempo.data_referencia_censo IS 'Data de referência do Censo Escolar: última quarta-feira de maio (nota do dicionário de dados do INEP).';
COMMENT ON COLUMN core.dim_tempo.rotulo IS 'Rótulo de exibição do ano.';
COMMENT ON COLUMN core.dim_tempo.eh_ano_pme IS 'Verdadeiro para os anos de vigência do PME 2015-2025.';

CREATE TABLE IF NOT EXISTS core.dim_etapa (
  cod_etapa        TEXT PRIMARY KEY,
  nome             TEXT NOT NULL,
  faixa_etaria_referencia TEXT,
  agrupamento      TEXT NOT NULL,
  ordem            SMALLINT NOT NULL
);
COMMENT ON TABLE core.dim_etapa IS 'Etapas e modalidades de ensino (carregada de config/etapas.yaml).';
COMMENT ON COLUMN core.dim_etapa.cod_etapa IS 'Código da etapa, ex.: fund_ai (anos iniciais), med_serie_1 (1ª série do ensino médio), total (não se aplica).';
COMMENT ON COLUMN core.dim_etapa.nome IS 'Nome da etapa.';
COMMENT ON COLUMN core.dim_etapa.faixa_etaria_referencia IS 'Faixa etária adequada à etapa, quando houver.';
COMMENT ON COLUMN core.dim_etapa.agrupamento IS 'Etapa de nível superior (ex.: fund_ai pertence a Ensino Fundamental).';
COMMENT ON COLUMN core.dim_etapa.ordem IS 'Ordem de exibição.';

CREATE TABLE IF NOT EXISTS core.dim_recorte (
  cod_recorte      TEXT PRIMARY KEY,
  rotulo           TEXT NOT NULL,
  rede             TEXT,
  localizacao      TEXT,
  tipo_outro       TEXT,
  valor_outro      TEXT,
  ordem            INTEGER NOT NULL DEFAULT 999
);
COMMENT ON TABLE core.dim_recorte IS 'Recortes analíticos. Um recorte combina até três eixos: rede, localização e um terceiro (sexo, cor/raça, faixa etária, porte, grupo AFD, subfunção...). O código "total" significa sem recorte.';
COMMENT ON COLUMN core.dim_recorte.cod_recorte IS 'Código canônico, ex.: total; rede:municipal; rede:municipal|localizacao:rural; raca_cor:parda.';
COMMENT ON COLUMN core.dim_recorte.rotulo IS 'Rótulo legível.';
COMMENT ON COLUMN core.dim_recorte.rede IS 'Rede (dependência administrativa): federal, estadual, municipal, privada, publica ou vazio (todas).';
COMMENT ON COLUMN core.dim_recorte.localizacao IS 'urbana, rural ou vazio (todas).';
COMMENT ON COLUMN core.dim_recorte.tipo_outro IS 'Tipo do terceiro eixo, ex.: raca_cor, sexo, faixa_etaria, porte, afd_grupo, subfuncao.';
COMMENT ON COLUMN core.dim_recorte.valor_outro IS 'Valor do terceiro eixo.';
COMMENT ON COLUMN core.dim_recorte.ordem IS 'Ordem de exibição.';

CREATE TABLE IF NOT EXISTS core.dim_fonte (
  id_fonte         SERIAL PRIMARY KEY,
  cod_fonte        TEXT NOT NULL UNIQUE,
  nome             TEXT NOT NULL,
  orgao            TEXT,
  prioridade       TEXT,
  url              TEXT,
  tipo_acesso      TEXT,
  formato          TEXT,
  periodicidade    TEXT,
  anos_disponiveis TEXT,
  licenca          TEXT,
  latencia_tipica  TEXT,
  observacoes      TEXT
);
COMMENT ON TABLE core.dim_fonte IS 'Fontes de dados (carregada de config/fontes.yaml).';
COMMENT ON COLUMN core.dim_fonte.id_fonte IS 'Chave numérica da fonte.';
COMMENT ON COLUMN core.dim_fonte.cod_fonte IS 'Identificador textual da fonte, igual ao de config/fontes.yaml.';
COMMENT ON COLUMN core.dim_fonte.nome IS 'Nome da fonte.';
COMMENT ON COLUMN core.dim_fonte.orgao IS 'Órgão produtor.';
COMMENT ON COLUMN core.dim_fonte.prioridade IS 'P1, P2 ou P3 nesta etapa.';
COMMENT ON COLUMN core.dim_fonte.url IS 'Página oficial.';
COMMENT ON COLUMN core.dim_fonte.tipo_acesso IS 'api, download, scraping, manual ou derivado.';
COMMENT ON COLUMN core.dim_fonte.formato IS 'Formato dos arquivos.';
COMMENT ON COLUMN core.dim_fonte.periodicidade IS 'Periodicidade de publicação.';
COMMENT ON COLUMN core.dim_fonte.anos_disponiveis IS 'Anos disponíveis na fonte.';
COMMENT ON COLUMN core.dim_fonte.licenca IS 'Licença / condição de uso.';
COMMENT ON COLUMN core.dim_fonte.latencia_tipica IS 'Defasagem típica entre a referência e a publicação.';
COMMENT ON COLUMN core.dim_fonte.observacoes IS 'Observações sobre a fonte.';

CREATE TABLE IF NOT EXISTS core.dim_indicador (
  cod_indicador      TEXT PRIMARY KEY,
  grupo              TEXT NOT NULL,
  eixo               TEXT NOT NULL,
  nome               TEXT NOT NULL,
  definicao          TEXT NOT NULL,
  formula            TEXT NOT NULL,
  unidade            TEXT NOT NULL,
  polaridade         TEXT NOT NULL CHECK (polaridade IN ('maior_melhor', 'menor_melhor', 'neutro')),
  meta_pme           TEXT,
  meta_valor         TEXT,
  nivel_agregacao    TEXT NOT NULL,
  cod_fonte          TEXT NOT NULL REFERENCES core.dim_fonte (cod_fonte),
  eh_calculo_proprio BOOLEAN NOT NULL,
  cobertura          TEXT NOT NULL CHECK (cobertura IN ('automatica', 'pendente', 'manual_futura')),
  nota_metodologica  TEXT,
  ordem              INTEGER NOT NULL
);
COMMENT ON TABLE core.dim_indicador IS 'Catálogo de indicadores (carregado de config/indicadores.yaml). Indicador novo = linha nova, sem mudar o esquema.';
COMMENT ON COLUMN core.dim_indicador.cod_indicador IS 'Código do indicador, ex.: A1, B1.aprovacao, F2.siope.';
COMMENT ON COLUMN core.dim_indicador.grupo IS 'Código do plano técnico ao qual o indicador pertence (A1 a G4).';
COMMENT ON COLUMN core.dim_indicador.eixo IS 'Eixo temático (A a G).';
COMMENT ON COLUMN core.dim_indicador.nome IS 'Nome do indicador.';
COMMENT ON COLUMN core.dim_indicador.definicao IS 'O que o indicador mede.';
COMMENT ON COLUMN core.dim_indicador.formula IS 'Fórmula ou origem do valor.';
COMMENT ON COLUMN core.dim_indicador.unidade IS 'Unidade de medida.';
COMMENT ON COLUMN core.dim_indicador.polaridade IS 'maior_melhor, menor_melhor ou neutro.';
COMMENT ON COLUMN core.dim_indicador.meta_pme IS 'Meta(s) do PME 2015-2025 relacionada(s).';
COMMENT ON COLUMN core.dim_indicador.meta_valor IS 'Valor da meta do PME, em texto.';
COMMENT ON COLUMN core.dim_indicador.nivel_agregacao IS 'municipio, escola ou municipio_e_escola.';
COMMENT ON COLUMN core.dim_indicador.cod_fonte IS 'Fonte principal (calculo_observatorio quando é cálculo próprio).';
COMMENT ON COLUMN core.dim_indicador.eh_calculo_proprio IS 'Verdadeiro quando o valor é calculado pelo Observatório (não é número oficial).';
COMMENT ON COLUMN core.dim_indicador.cobertura IS 'automatica (calculado nesta etapa), pendente (fonte ainda não viável) ou manual_futura (depende da SEDUC).';
COMMENT ON COLUMN core.dim_indicador.nota_metodologica IS 'Nota metodológica a exibir junto do número.';
COMMENT ON COLUMN core.dim_indicador.ordem IS 'Ordem de exibição.';

CREATE TABLE IF NOT EXISTS core.dim_escola (
  co_entidade                CHAR(8) NOT NULL,
  valid_from                 SMALLINT NOT NULL,
  valid_to                   SMALLINT,
  eh_vigente                 BOOLEAN NOT NULL,
  no_entidade                TEXT,
  cod_territorio             TEXT REFERENCES core.dim_territorio (cod_territorio),
  tp_dependencia             SMALLINT,
  tp_categoria_escola_privada SMALLINT,
  tp_localizacao             SMALLINT,
  tp_localizacao_diferenciada SMALLINT,
  tp_situacao_funcionamento  SMALLINT,
  no_bairro                  TEXT,
  co_distrito                TEXT,
  latitude                   NUMERIC(10, 7),
  longitude                  NUMERIC(10, 7),
  ultimo_ano_censo           SMALLINT NOT NULL,
  hash_atributos             CHAR(32) NOT NULL,
  PRIMARY KEY (co_entidade, valid_from)
);
COMMENT ON TABLE core.dim_escola IS 'Escolas como dimensão de mudança lenta (tipo 2): uma linha por período em que os atributos ficaram iguais. Reconstruída a partir de staging.censo_escola a cada carga.';
COMMENT ON COLUMN core.dim_escola.co_entidade IS 'Código INEP da escola, 8 dígitos, texto.';
COMMENT ON COLUMN core.dim_escola.valid_from IS 'Primeiro ano do Censo com estes atributos.';
COMMENT ON COLUMN core.dim_escola.valid_to IS 'Último ano do Censo com estes atributos (vazio se ainda vale no último Censo carregado).';
COMMENT ON COLUMN core.dim_escola.eh_vigente IS 'Verdadeiro para a versão mais recente da escola.';
COMMENT ON COLUMN core.dim_escola.no_entidade IS 'Nome da escola no Censo.';
COMMENT ON COLUMN core.dim_escola.cod_territorio IS 'Município da escola (código IBGE de 7 dígitos).';
COMMENT ON COLUMN core.dim_escola.tp_dependencia IS 'Dependência administrativa (código INEP; rótulo em core.dim_codigo_inep).';
COMMENT ON COLUMN core.dim_escola.tp_categoria_escola_privada IS 'Categoria da escola privada (código INEP).';
COMMENT ON COLUMN core.dim_escola.tp_localizacao IS 'Localização (código INEP: 1 urbana, 2 rural).';
COMMENT ON COLUMN core.dim_escola.tp_localizacao_diferenciada IS 'Localização diferenciada (código INEP).';
COMMENT ON COLUMN core.dim_escola.tp_situacao_funcionamento IS 'Situação de funcionamento (código INEP).';
COMMENT ON COLUMN core.dim_escola.no_bairro IS 'Bairro (não publicado nos microdados de 2025).';
COMMENT ON COLUMN core.dim_escola.co_distrito IS 'Código do distrito (IBGE).';
COMMENT ON COLUMN core.dim_escola.latitude IS 'Latitude (não publicada nos microdados públicos; reservada para a etapa com a SEDUC).';
COMMENT ON COLUMN core.dim_escola.longitude IS 'Longitude (idem).';
COMMENT ON COLUMN core.dim_escola.ultimo_ano_censo IS 'Último ano em que a escola aparece no Censo carregado.';
COMMENT ON COLUMN core.dim_escola.hash_atributos IS 'Hash dos atributos, usado para detectar mudança.';

CREATE TABLE IF NOT EXISTS core.dim_codigo_inep (
  variavel         TEXT NOT NULL,
  codigo           TEXT NOT NULL,
  rotulo           TEXT NOT NULL,
  ano_dicionario   SMALLINT NOT NULL,
  PRIMARY KEY (variavel, codigo)
);
COMMENT ON TABLE core.dim_codigo_inep IS 'Tabela auxiliar de decodificação dos códigos do INEP (dependência, localização, situação de funcionamento...), extraída do dicionário de dados que vem no ZIP do Censo Escolar. Vale o dicionário mais recente carregado.';
COMMENT ON COLUMN core.dim_codigo_inep.variavel IS 'Nome da variável no Censo, ex.: TP_DEPENDENCIA.';
COMMENT ON COLUMN core.dim_codigo_inep.codigo IS 'Código da categoria.';
COMMENT ON COLUMN core.dim_codigo_inep.rotulo IS 'Rótulo da categoria, como no dicionário do INEP.';
COMMENT ON COLUMN core.dim_codigo_inep.ano_dicionario IS 'Ano do dicionário de onde o rótulo foi lido.';
