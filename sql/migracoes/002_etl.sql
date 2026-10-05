-- 002 - Tabelas operacionais (esquema etl)

CREATE TABLE IF NOT EXISTS etl.etl_execucao (
  id_execucao      BIGSERIAL PRIMARY KEY,
  job              TEXT NOT NULL,
  id_fonte         TEXT,
  parametros       TEXT,
  inicio           TIMESTAMPTZ NOT NULL DEFAULT now(),
  fim              TIMESTAMPTZ,
  status           TEXT NOT NULL DEFAULT 'em_andamento'
                   CHECK (status IN ('em_andamento', 'sucesso', 'sucesso_com_alertas', 'falha', 'ignorado')),
  linhas_lidas     BIGINT NOT NULL DEFAULT 0,
  linhas_gravadas  BIGINT NOT NULL DEFAULT 0,
  mensagem_erro    TEXT
);
COMMENT ON TABLE etl.etl_execucao IS 'Uma linha por execução de job (coleta, transformação, cálculo de indicadores, testes).';
COMMENT ON COLUMN etl.etl_execucao.job IS 'Nome do job, ex.: coletar, transformar, indicadores, qualidade, pipeline.';
COMMENT ON COLUMN etl.etl_execucao.id_fonte IS 'Fonte processada (id de config/fontes.yaml), quando o job é por fonte.';
COMMENT ON COLUMN etl.etl_execucao.parametros IS 'Parâmetros usados (anos, opções), em texto.';
COMMENT ON COLUMN etl.etl_execucao.status IS 'em_andamento, sucesso, sucesso_com_alertas, falha ou ignorado (nada novo a processar).';
COMMENT ON COLUMN etl.etl_execucao.linhas_lidas IS 'Linhas lidas das fontes nesta execução.';
COMMENT ON COLUMN etl.etl_execucao.linhas_gravadas IS 'Linhas gravadas no banco nesta execução.';
COMMENT ON COLUMN etl.etl_execucao.mensagem_erro IS 'Mensagem do erro, quando status = falha.';
CREATE INDEX IF NOT EXISTS ix_etl_execucao_fonte ON etl.etl_execucao (id_fonte, inicio DESC);

CREATE TABLE IF NOT EXISTS etl.etl_arquivo (
  id_arquivo       BIGSERIAL PRIMARY KEY,
  id_fonte         TEXT NOT NULL,
  ano_referencia   SMALLINT,
  url              TEXT NOT NULL,
  sha256           CHAR(64) NOT NULL,
  data_coleta      TIMESTAMPTZ NOT NULL,
  caminho_local    TEXT NOT NULL,
  tamanho_bytes    BIGINT NOT NULL,
  status_http      INTEGER,
  http_last_modified TEXT,
  http_etag        TEXT,
  versao_layout    TEXT,
  descricao        TEXT,
  id_execucao      BIGINT REFERENCES etl.etl_execucao (id_execucao),
  processado_em    TIMESTAMPTZ,
  arquivo_removido BOOLEAN NOT NULL DEFAULT false,
  UNIQUE NULLS NOT DISTINCT (id_fonte, ano_referencia, sha256, url)
);
COMMENT ON TABLE etl.etl_arquivo IS 'Manifesto dos arquivos brutos coletados: de onde veio, quando, hash sha256 e onde está no disco. Permite rebaixar e conferir.';
COMMENT ON COLUMN etl.etl_arquivo.id_fonte IS 'Fonte do arquivo (id de config/fontes.yaml).';
COMMENT ON COLUMN etl.etl_arquivo.ano_referencia IS 'Ano de referência dos dados do arquivo (para o Ideb, o ano da edição).';
COMMENT ON COLUMN etl.etl_arquivo.url IS 'Endereço de onde o arquivo foi baixado (ou a consulta da API).';
COMMENT ON COLUMN etl.etl_arquivo.sha256 IS 'Hash sha256 do conteúdo; o mesmo hash não é reprocessado, salvo com --forcar.';
COMMENT ON COLUMN etl.etl_arquivo.data_coleta IS 'Momento do download.';
COMMENT ON COLUMN etl.etl_arquivo.caminho_local IS 'Caminho do arquivo em data/raw/<fonte>/<ano>/ (relativo à pasta de dados).';
COMMENT ON COLUMN etl.etl_arquivo.tamanho_bytes IS 'Tamanho do arquivo em bytes.';
COMMENT ON COLUMN etl.etl_arquivo.status_http IS 'Código HTTP da resposta (ou 226 para FTP).';
COMMENT ON COLUMN etl.etl_arquivo.http_last_modified IS 'Cabeçalho Last-Modified da resposta; usado para não baixar de novo um arquivo grande que não mudou.';
COMMENT ON COLUMN etl.etl_arquivo.http_etag IS 'Cabeçalho ETag da resposta (quando o servidor informa).';
COMMENT ON COLUMN etl.etl_arquivo.versao_layout IS 'Layout identificado (ex.: censo_escolar L2015 ou L2025), para rastrear mudanças de formato.';
COMMENT ON COLUMN etl.etl_arquivo.processado_em IS 'Quando o arquivo foi carregado com sucesso no raw/staging.';
COMMENT ON COLUMN etl.etl_arquivo.arquivo_removido IS 'Verdadeiro quando o arquivo foi apagado do disco depois de processado (opção manter_zip_bruto = false).';

CREATE TABLE IF NOT EXISTS etl.versao_dados (
  id_versao        SERIAL PRIMARY KEY,
  id_fonte         TEXT NOT NULL,
  assinatura       CHAR(64) NOT NULL,
  descricao        TEXT,
  criado_em        TIMESTAMPTZ NOT NULL DEFAULT now(),
  id_execucao      BIGINT REFERENCES etl.etl_execucao (id_execucao),
  vigente          BOOLEAN NOT NULL DEFAULT false,
  UNIQUE (id_fonte, assinatura)
);
COMMENT ON TABLE etl.versao_dados IS 'Versões de carga. A assinatura é o hash dos arquivos de entrada (e, para indicadores, das versões das fontes e da versão do método). Mesma entrada = mesma versão: reexecutar não duplica dados. Só uma versão por fonte fica vigente.';
COMMENT ON COLUMN etl.versao_dados.assinatura IS 'sha256 que identifica o conjunto de entradas desta versão.';
COMMENT ON COLUMN etl.versao_dados.vigente IS 'Verdadeiro para a versão exibida na camada bi.';
CREATE UNIQUE INDEX IF NOT EXISTS ux_versao_vigente ON etl.versao_dados (id_fonte) WHERE vigente;

CREATE TABLE IF NOT EXISTS etl.dq_resultado (
  id_resultado     BIGSERIAL PRIMARY KEY,
  id_execucao      BIGINT REFERENCES etl.etl_execucao (id_execucao),
  teste            TEXT NOT NULL,
  tabela           TEXT NOT NULL,
  coluna           TEXT,
  severidade       TEXT NOT NULL CHECK (severidade IN ('info', 'alerta', 'erro')),
  resultado        TEXT NOT NULL CHECK (resultado IN ('ok', 'falha')),
  ocorrencias      INTEGER NOT NULL DEFAULT 0,
  detalhe          TEXT,
  executado_em     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.dq_resultado IS 'Resultado dos testes de qualidade do dado (unicidade, faixas válidas, soma das partes, variação anual, conferência cruzada).';
COMMENT ON COLUMN etl.dq_resultado.severidade IS 'info, alerta (não interrompe) ou erro.';
COMMENT ON COLUMN etl.dq_resultado.resultado IS 'ok ou falha.';
COMMENT ON COLUMN etl.dq_resultado.ocorrencias IS 'Quantidade de linhas que violaram a regra.';
COMMENT ON COLUMN etl.dq_resultado.detalhe IS 'Exemplos das violações ou explicação do teste.';

CREATE TABLE IF NOT EXISTS etl.de_para (
  dominio          TEXT NOT NULL,
  valor_origem     TEXT NOT NULL,
  valor_canonico   TEXT NOT NULL,
  fonte            TEXT,
  observacao       TEXT,
  atualizado_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (dominio, valor_origem)
);
COMMENT ON TABLE etl.de_para IS 'Conciliação de valores entre fontes (ex.: nomes de rede "Particular" x "Privada"; nomes de escola SIEJ x INEP).';
COMMENT ON COLUMN etl.de_para.dominio IS 'Domínio do valor, ex.: dependencia, localizacao, escola_nome.';

CREATE TABLE IF NOT EXISTS etl.regra_ausencia (
  id_fonte         TEXT NOT NULL,
  marcador         TEXT NOT NULL,
  status_valor     TEXT NOT NULL,
  descricao        TEXT,
  PRIMARY KEY (id_fonte, marcador)
);
COMMENT ON TABLE etl.regra_ausencia IS 'Como cada marcador de ausência de cada fonte vira status (carregada de config/regras_ausencia.yaml). Nenhum marcador vira zero.';

CREATE TABLE IF NOT EXISTS etl.migracao (
  versao           TEXT PRIMARY KEY,
  arquivo          TEXT NOT NULL,
  sha256           CHAR(64) NOT NULL,
  aplicada_em      TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.migracao IS 'Migrations de esquema já aplicadas (sql/migracoes).';
