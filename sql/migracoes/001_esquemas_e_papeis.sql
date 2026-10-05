-- 001 - Esquemas e papéis
-- Camadas: raw (como veio), staging (tipado e limpo), core (dimensões, fatos, indicadores),
-- bi (views para o Power BI) e etl (tabelas operacionais).

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS bi;
CREATE SCHEMA IF NOT EXISTS etl;

COMMENT ON SCHEMA raw IS 'Camada bruta: recorte dos arquivos das fontes exatamente como vieram (valores em texto), com vínculo ao arquivo de origem em etl.etl_arquivo.';
COMMENT ON SCHEMA staging IS 'Camada de tratamento: dados tipados, com códigos normalizados e marcadores de ausência convertidos em status.';
COMMENT ON SCHEMA core IS 'Camada central: dimensões, fatos e indicadores, com histórico de versões.';
COMMENT ON SCHEMA bi IS 'Camada de consumo do Power BI: views em esquema estrela, só com a versão vigente dos dados.';
COMMENT ON SCHEMA etl IS 'Tabelas operacionais: execuções, arquivos coletados, versões, testes de qualidade e conciliação de códigos.';

-- Papel de leitura do Power BI. A senha e o LOGIN são definidos pelo comando
-- "python -m observatorio db migrar", a partir do arquivo .env (nunca ficam no SQL).
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'powerbi_leitor') THEN
    CREATE ROLE powerbi_leitor NOLOGIN;
  END IF;
END
$$;

-- Nenhum acesso padrão às camadas internas.
REVOKE ALL ON SCHEMA raw, staging, core, etl FROM PUBLIC;
REVOKE ALL ON SCHEMA bi FROM PUBLIC;

-- O leitor do Power BI enxerga apenas o esquema bi.
GRANT USAGE ON SCHEMA bi TO powerbi_leitor;
ALTER DEFAULT PRIVILEGES IN SCHEMA bi GRANT SELECT ON TABLES TO powerbi_leitor;
