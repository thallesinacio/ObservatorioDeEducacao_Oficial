# Observatório da Educação de Juazeiro-BA — coleta de dados públicos

Projeto de extensão UNIVASF/SEDUC. Este repositório coleta automaticamente dados públicos de educação
de Juazeiro-BA (IBGE 2918407), com Petrolina-PE, Bahia e Brasil como comparação, e os organiza num
banco PostgreSQL pronto para o Power BI.

O que ele faz, ponta a ponta:

1. **Coleta** os arquivos e APIs oficiais (INEP, IBGE, DATASUS, FNDE, Tesouro), guardando cada arquivo
   em `data/raw/` e registrando URL, sha256, data e tamanho num manifesto (`etl.etl_arquivo`).
2. **Transforma** em camadas: `raw` (recorte dos municípios de interesse, como veio) → `staging`
   (tipado) → `core` (dimensões e fatos com versão de carga).
3. **Calcula** os indicadores do plano (eixos A a G) em `core.fato_indicador`, com fonte, data de coleta,
   versão, status (`observado`, `estimado`, `sem_dado`...) e, quando cabe, numerador e denominador.
4. **Testa** a qualidade do dado (`etl.dq_resultado`).
5. **Publica** o esquema `bi` (views em estrela) para o Power BI, lido por um usuário que só enxerga esse esquema.

Regras que valem em todo o projeto: **lacuna nunca vira zero**; **nenhum dado pessoal entra no banco**
(o menor grão é escola × ano); código de município/escola é sempre texto; rodar duas vezes não duplica nada.

---

## 1. O que instalar (uma vez)

No Windows (vale igual para Linux/macOS, trocando os comandos do terminal):

| Programa | Para quê | Onde baixar |
|---|---|---|
| Python 3.11 ou mais novo | rodar o projeto | https://www.python.org/downloads/ (marque "Add python.exe to PATH") |
| Docker Desktop **ou** PostgreSQL 16 | o banco de dados | https://www.docker.com/products/docker-desktop/ ou https://www.postgresql.org/download/windows/ |
| Git (opcional) | clonar o repositório | https://git-scm.com/download/win |
| Power BI Desktop | o painel | Microsoft Store |

## 2. Preparar o projeto

Abra o **PowerShell** na pasta do projeto (ex.: `C:\Users\<você>\ObservatorioDeEducacao`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # se o Windows bloquear: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install --upgrade pip
pip install -e ".[dev]"
copy .env.example .env
notepad .env                          # troque as duas senhas
```

## 3. Subir o banco

**Opção A — Docker (recomendada):**

```powershell
docker compose up -d
docker compose ps                     # espere o status "healthy"
```

O banco, o usuário e a senha saem do `.env` (`OBS_DB_NOME`, `OBS_DB_USUARIO`, `OBS_DB_SENHA`).

**Opção B — PostgreSQL instalado no Windows:** crie um usuário e um banco com os mesmos nomes do `.env`
(no pgAdmin, ou no `psql` como `postgres`):

```sql
CREATE ROLE observatorio_etl LOGIN PASSWORD 'a-senha-do-.env' CREATEROLE;
CREATE DATABASE observatorio OWNER observatorio_etl;
```

(`CREATEROLE` é necessário porque a primeira migration cria o papel somente leitura `powerbi_leitor`.)

## 4. Rodar

```powershell
python -m observatorio db migrar              # cria esquemas, tabelas, papéis, dimensões e as views do bi
python -m observatorio pipeline --de 2015     # coleta, transforma, calcula indicadores e testa (demora na 1ª vez)
python -m observatorio relatorio cobertura    # matriz indicador × ano × status
```

A primeira execução baixa perto de 3 GB (microdados do Censo 2015–2025, Sinopses, planilhas por escola).
Para ir por partes:

```powershell
python -m observatorio fontes listar
python -m observatorio coletar --fonte censo_escolar --ano 2024
python -m observatorio coletar --todas --de 2015
python -m observatorio transformar --fonte censo_escolar
python -m observatorio transformar --todas
python -m observatorio indicadores calcular
python -m observatorio qualidade testar
python -m observatorio docs dicionario        # regenera docs/dicionario_dados.md a partir do banco
```

Opções úteis: `--forcar` (baixa/reprocessa mesmo sem mudança), `--ano` (repita para vários anos).
O pipeline termina com um resumo por fonte; se alguma fonte falhar, as outras seguem e o código de saída é 1.
Detalhes de cada execução ficam em `etl.etl_execucao` e em `data/logs/observatorio.log` (JSON por linha).

**Rodar de novo é seguro:** arquivo remoto sem mudança não é baixado de novo (confere tamanho e
Last-Modified/ETag); arquivo com o mesmo sha256 não é reprocessado; mesma entrada gera a mesma versão.
Quando uma fonte publica revisão, uma **nova versão** é gravada e passa a ser a vigente; a anterior fica
no histórico (`etl.versao_dados`).

**Site bloqueou a coleta?** Baixe o arquivo no navegador e registre-o:

```powershell
python -m observatorio importar --fonte sinopse_estatistica --ano 2024 --arquivo C:\Downloads\sinopse.zip --url https://download.inep.gov.br/dados_abertos/sinopses_estatisticas/sinopse_estatistica_censo_escolar_2024.zip
python -m observatorio transformar --fonte sinopse_estatistica
```

**Atualizar todo ano:** basta rodar `python -m observatorio pipeline` de novo (ex.: pelo Agendador de Tarefas do Windows).

## 5. Conectar no Power BI

1. No Power BI Desktop: **Obter dados → Banco de dados PostgreSQL**.
2. Servidor: `localhost:5432` (ou o host/porta do `.env`); Banco de dados: `observatorio`.
   Modo: **Importar**.
3. Credenciais: aba **Banco de dados**, usuário `powerbi_leitor`, senha = `OBS_POWERBI_SENHA` do `.env`.
   (Se aparecer aviso de criptografia, aceite a conexão sem criptografia para o banco local.)
4. Marque as views do esquema **bi**:
   - dimensões: `bi.dim_territorio`, `bi.dim_tempo`, `bi.dim_etapa`, `bi.dim_recorte`, `bi.dim_indicador`,
     `bi.dim_fonte`, `bi.dim_escola`, `bi.dim_status`;
   - fatos: `bi.fato_indicador` (principal), e se quiser `bi.fato_matricula`, `bi.fato_rendimento`,
     `bi.fato_avaliacao`, `bi.fato_docente`, `bi.fato_financiamento`, `bi.fato_populacao`, `bi.meta_pme`;
   - qualidade: `bi.cobertura_indicador_ano`, `bi.qualidade_status`, `bi.fonte_situacao`, `bi.dq_resultado`.
5. Em **Modelo**, crie as relações (um-para-muitos, filtro em direção única), todas de chave de texto
   única da dimensão para o fato:

   | Dimensão (1) | Fato (*) |
   |---|---|
   | `dim_indicador[cod_indicador]` | `fato_indicador[cod_indicador]` |
   | `dim_territorio[cod_territorio]` | `fato_indicador[cod_territorio]` |
   | `dim_tempo[ano]` | `fato_indicador[ano]` |
   | `dim_etapa[cod_etapa]` | `fato_indicador[cod_etapa]` |
   | `dim_recorte[cod_recorte]` | `fato_indicador[cod_recorte]` |
   | `dim_status[status_valor]` | `fato_indicador[status_valor]` |
   | `dim_fonte[cod_fonte]` | `fato_indicador[cod_fonte]` |
   | `dim_escola[co_entidade]` | `fato_indicador[co_entidade]` |

   As outras tabelas de fato se ligam às mesmas dimensões pelas colunas de mesmo nome.
6. Boas práticas no painel:
   - para o valor do município, filtre `fato_indicador[nivel] = "territorio"` e `cod_recorte = "total"`
     (ou use o recorte desejado);
   - use `Classificar por coluna` com a coluna `ordem` nas dimensões de etapa, recorte e indicador;
   - valor vazio é **lacuna** (veja `status_valor`), não zero: não troque por 0 em medidas DAX;
   - destaque `eh_calculo_proprio` e `eh_estimado` (ex.: "cálculo do Observatório", "usa população estimada")
     e mostre `dim_indicador[formula]` e `[nota_metodologica]` na dica de ferramenta.
7. Para atualizar o painel depois de rodar o pipeline: **Página Inicial → Atualizar**.

## 6. Testes

```powershell
pytest              # sem internet: parsers com recortes reais das fontes + pipeline completo num banco de teste
pytest -m rede      # confere se as páginas e APIs oficiais continuam no mesmo formato
ruff check src tests
```

Os testes de banco criam e apagam o banco `observatorio_teste` (mesmo host/usuário do `.env`; o usuário
precisa poder criar banco). Sem PostgreSQL, eles são pulados.

## 7. Onde está cada coisa

```
config/        fontes.yaml, indicadores.yaml, projeto.yaml (territórios, período, limiares), etapas,
               recortes, regras de ausência, layouts do Censo, sinopse.yaml, sidra.yaml, siope.yaml
sql/migracoes/ esquemas e tabelas (numeradas, aplicadas uma vez; conferidas por sha256)
sql/indicadores/ cálculo dos indicadores (SQL legível)
sql/bi/        views do Power BI (recriadas a cada "db migrar")
src/observatorio/
  coleta/      um módulo por fonte        transformacao/  leitores e cabeçalhos das planilhas
  carga/       dimensões                  indicadores/    orquestra o cálculo versionado
  qualidade/   testes de qualidade        pipeline.py, cli.py, relatorios.py
tests/         testes + fixtures (recortes reais dos arquivos oficiais)
docs/          fontes.md, decisoes.md, pendencias.md, dicionario_dados.md
data/          raw/ (arquivos baixados), interim/, processed/, logs/ — fora do Git
```

Para trocar ou incluir municípios de comparação, edite `config/projeto.yaml` e rode `db migrar` e o pipeline.
Para mudar uma fórmula, edite `sql/indicadores/` e suba `metodologia.versao_calculo_indicadores` em
`config/projeto.yaml`: o próximo cálculo gera uma versão nova em vez de sobrescrever a anterior.
