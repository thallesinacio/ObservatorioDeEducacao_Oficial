# Fichas das fontes

Tudo abaixo foi verificado nas páginas e arquivos oficiais em **29/09/2026** (lendo os próprios arquivos,
por HTTP Range quando eram grandes). O catálogo usado pelo código fica em `config/fontes.yaml`; esta
página explica o que foi encontrado e como cada coletor trata a fonte.

Territórios: Juazeiro-BA **2918407** (alvo), Petrolina-PE **2611101** (comparação), Bahia **29** e Brasil **1**
(convenção do SIDRA). DATASUS e SIOPE usam o código de 6 dígitos (291840 / 261110).

---

## 1. Microdados do Censo Escolar (INEP) — `censo_escolar` — P1

- Página: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar
- Arquivos: `https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_{ano}.zip`; **2025 tem
  sublinhado final** (`microdados_censo_escolar_2025_.zip`), por isso os links são lidos da página.
- Tamanho: 26–34 MB (2015–2024); 537 MB em 2025 (ZIP sem compressão).
- CSV separado por `;`, codificação latin-1. Dicionário em `ANEXO I - Dicionário de Dados/dicionário_dados_educação_básica.xlsx`
  (cabeçalho na linha 7; categorias na coluna "Categoria", ex. `1 - Federal\n2 - Estadual...`).
- Layouts (config/layouts/censo_escolar.yaml):

  | Anos | Estrutura | Colunas |
  |---|---|---|
  | 2015–2021 | `microdados_ed_basica_AAAA.csv` (2020 com extensão `.CSV`) | 370 |
  | 2022 | idem, pasta interna "Microdados do Censo Escolar da Educação Básica 2022" | 385 |
  | 2023–2024 | idem (+ `suplemento_cursos_tecnicos`) | 408 / 426 |
  | 2025 | seis tabelas `Tabela_{Escola,Matricula,Docente,Turma,Gestor_Escolar,Curso_Tecnico}_2025_V2.csv` | — |

- Particularidades: `QT_MAT_BAS_0_3` … `QT_MAT_BAS_15_17` existem em todos os anos; `QT_MAT_FUND_AI_1..5`,
  EJA integrada (`QT_MAT_EJA_FUND_FIC`, `_MED_TEC`, `_MED_FIC`) e zona de residência (`QT_MAT_ZR_*`) só a
  partir de 2023; `QT_TUR_*_INT` a partir de 2023; 2025 traz docentes por escolaridade (`QT_DOC_BAS_ESCO_*`)
  e não publica endereço/bairro. Data de referência: última quarta-feira de maio. Tempo integral: jornada de 7 horas diárias ou mais (35 h semanais).
- Códigos: `TP_DEPENDENCIA` 1 Federal, 2 Estadual, 3 Municipal, 4 Privada; `TP_LOCALIZACAO` 1 Urbana, 2 Rural;
  `TP_SITUACAO_FUNCIONAMENTO` 1 Em atividade, 2 Paralisada, 3 Extinta (ano do Censo), 4 Extinta em anos
  anteriores; `TP_AEE` 0 Não oferece, 1 Não exclusivamente, 2 Exclusivamente.
- Grão: escola × ano (contagens). Não há dado de aluno ou docente individual nos microdados públicos.
- Valores de referência de Juazeiro calculados sobre os microdados reais (soma de `QT_MAT_BAS` / escolas em
  atividade / `QT_MAT_BAS_0_3` / `_4_5` / `_6_10` / `_11_14` / `_15_17` / matrículas da rede municipal):

  | Ano | Matrículas | Escolas | 0–3 | 4–5 | 6–10 | 11–14 | 15–17 | Rede municipal |
  |---|---|---|---|---|---|---|---|---|
  | 2015 | 60 692 | 184 | 3 223 | 5 572 | 16 873 | 15 183 | 10 711 | 32 861 |
  | 2016 | 63 575 | 189 | 3 605 | 6 232 | 17 423 | 15 596 | 11 304 | 32 584 |
  | 2017 | 63 716 | 189 | 3 740 | 6 504 | 17 779 | 15 433 | 11 266 | 33 404 |
  | 2018 | 65 222 | 196 | 4 336 | 6 723 | 17 964 | 15 437 | 11 381 | 34 284 |
  | 2019 | 65 078 | 196 | 4 567 | 7 127 | 18 492 | 15 365 | 11 203 | 33 935 |
  | 2020 | 69 010 | 191 | 4 502 | 7 499 | 18 421 | 15 113 | 11 385 | 35 612 |
  | 2021 | 68 576 | 189 | 3 305 | 6 649 | 18 137 | 14 858 | 11 577 | 36 136 |
  | 2022 | 68 520 | 228 | 4 449 | 7 312 | 19 374 | 14 912 | 11 336 | 36 712 |
  | 2023 | 68 332 | 194 | 4 884 | 7 693 | 19 583 | 15 163 | 11 111 | 36 709 |
  | 2024 | 67 679 | 188 | 4 830 | 7 816 | 19 626 | 15 068 | 10 881 | 37 114 |

  O total de 2024 bate com a Sinopse (tabela 1.1: 67 679). Em 2022, 53 escolas têm `QT_MAT_BAS` vazio.
  Use esta tabela para conferir a primeira carga completa.

## 2. Sinopse Estatística da Educação Básica (INEP) — `sinopse_estatistica` — P1

- Página: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/sinopses-estatisticas/educacao-basica
- 2020–2025 em `download.inep.gov.br/dados_abertos/sinopses_estatisticas/` (ex.:
  `sinopse_estatistica_censo_escolar_2024.zip`; 2020–2022 `sinopses_estatisticas_censo_escolar_AAAA.zip`);
  2015–2019 em `.../informacoes_estatisticas/sinopses_estatisticas/sinopses_educacao_basica/`.
- XLSX de 88 a 199 MB, uma aba por tabela. A numeração muda (2025), então as tabelas são achadas pelo
  título (`config/sinopse.yaml`): "1.1 – Número de Matrículas da Educação Básica, por Etapa de Ensino..." e
  "2.4 – Número de Docentes da Educação Básica, por Nível de Escolaridade e Formação Acadêmica...".
- Linhas: Brasil, regiões, UFs (colunas "Região Geográfica | Unidade da Federação | Município | Código do Município").
- Docentes contados **uma vez por município** (nota da própria tabela). As colunas de pós-graduação não
  são exclusivas.
- Juazeiro 2024, tabela 2.4: total 2 765; fundamental 3; médio 221; graduação 2 541 (licenciatura 2 359,
  sem licenciatura 182); especialização 1 638; mestrado 174; doutorado 31. Petrolina: 4 497; 2; 438; 4 057;
  3 946; 111; 2 125; 206; 48.

## 3. Indicadores Educacionais (INEP) — P1

| id | Página (`.../dados-abertos/indicadores-educacionais/`) |
|---|---|
| `inep_rendimento` | `taxas-de-rendimento-escolar` |
| `inep_distorcao` | `taxas-de-distorcao-idade-serie` |
| `inep_afd` | `adequacao-da-formacao-docente` |
| `inep_atu` | `media-de-alunos-por-turma` |
| `inep_dsu` | `percentual-de-docentes-com-curso-superior` |

- Cada página tem uma aba por ano (`a[data-id]`; a de 2021 aparece como "2021."), com sub-página `<pagina>/<ano>`.
- Nomes de arquivo variam (ex.: `tx_rendimento_municipios_2015.zip`, `TAXA_REND_2016_MUNICIPIOS.zip`,
  `TX_REND_MUNICIPIOS_2018.zip`, `tx_rend_municipios_2019.zip`; em 2015 há subpastas como
  `2015/distorcao_idade_serie/tdi_municipios_2015.zip`) — os links são lidos da página, nunca montados.
- Três arquivos por ano: Brasil/regiões/UFs, municípios e escolas (rendimento e distorção por escola são carregados).
- ZIP com XLSX e ODS; usamos o XLSX. Cabeçalho em várias linhas com células mescladas; em parte dos anos
  há uma linha de códigos (`NU_ANO_CENSO`, `FUN_CAT_0`, `1_CAT_FUN_AI`, `TDI_F14`, `AFD_INF1`...); o
  rendimento de 2015 não tem. O parser usa o texto do cabeçalho e, quando há, o código (que prevalece).
- Marcadores: `--` = recorte sem a etapa (não se aplica); `-`, `*`, `ND`, `...`, `x` = sem dado.
  `Particular` e `Privada` = rede privada. Números às vezes com vírgula (ODS) ou artefato binário (`40.799999999999997`).
- Divergência conhecida: no DSU 2024 a coluna de código `EDU_BAS_CAT_0` tem rótulo "Educação Especial"
  (vale o código: educação básica; registrado como alerta de qualidade).

## 4. Ideb — resultados (INEP) — `ideb` — P1

- Página: https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb/resultados
- Arquivos: `https://download.inep.gov.br/ideb/resultados/divulgacao_{anos_iniciais|anos_finais|ensino_medio}_{municipios|escolas}_2025.zip`,
  `divulgacao_regioes_ufs_ideb_2025.zip`, `divulgacao_brasil_ideb_2025.zip`.
- Formato largo com linha de códigos: `SG_UF | CO_MUNICIPIO | NO_MUNICIPIO | REDE | VL_APROVACAO_2017_SI_4 |
  VL_APROVACAO_2017_1 ... | VL_INDICADOR_REND_2017 | VL_NOTA_MATEMATICA_2017 | VL_NOTA_PORTUGUES_2017 |
  VL_NOTA_MEDIA_2017 | VL_OBSERVADO_2017 | VL_PROJECAO_2019`. Marcadores `-` e `ND`. Rede "Privada (1)".
- A edição mais recente traz a série; cada edição baixada é guardada (o INEP revisa números).

## 5. População por idade simples (RIPSA/Ministério da Saúde) — `populacao_datasus` — P1

- TabNet (verificado): http://tabnet.datasus.gov.br/cgi/deftohtm.exe?ibge/cnv/popsvs2024br.def — "Estudo de
  Estimativas Populacionais por Município, Idade e Sexo 2000-2025". Consulta por POST em
  `tabcgi.exe?ibge/cnv/popsvs2024br.def` com Linha = Idade simples, Coluna = Ano, filtro de município
  (valores do formulário, codificação latin-1). Resposta em `<PRE>`: `"Idade simples";"2023";"2024";"2025"`,
  idades "Menos que 1 ano de idade", "1  ano", ..., "80 anos e mais", "Total".
- Juazeiro, total 2024 = 254 481 (igual à estimativa do IBGE, SIDRA 6579).
- FTP `ftp://ftp.datasus.gov.br/dissemin/publicos/IBGE/POPSVS/POPSBR{aa}.zip` (DBF): **não verificável** do
  ambiente de desenvolvimento; o coletor tenta o FTP primeiro, valida as colunas do DBF e cai no TabNet se algo falhar.

## 6. IBGE SIDRA — `sidra_ibge` e `sidra_alfabetizacao` — P1/P2

API `https://apisidra.ibge.gov.br/values/t/{tabela}/n6/{municípios}/...` (consultas em `config/sidra.yaml`):

| Tabela | Uso | Observação |
|---|---|---|
| 6579, v9324 | população estimada (G1.ibge_total, G3 per capita) | 2001–2026, sem 2007, 2010, 2022 e 2023 |
| 9514, v93 | Censo 2022 por idade (G1.censo2022) | c2 6794 = Total, c287 = idade, c286 113635 = Total |
| 5938, v37 | PIB (mil R$) | 2002–2023; Juazeiro 2023 = 6 159 604 |
| 9542, v950 | alfabetização 15+ (G2) | c59 93024 Total / 1023 Alfabetizadas; Juazeiro: 163 658 de 181 185 = 90,3% |

Marcador `-` do IBGE = zero absoluto (vira 0 observado); `..` não se aplica; `...` e `X` sem dado.

## 7. SIOPE (FNDE) — `siope` — P1

- OData: `https://www.fnde.gov.br/olinda-ide/servico/DADOS_ABERTOS_SIOPE/versao/v1/odata/{Recurso}(Ano_Consulta=@Ano_Consulta,Num_Peri=@Num_Peri,Sig_UF=@Sig_UF)?@Ano_Consulta=2023&@Num_Peri=6&@Sig_UF='BA'&$format=json&$filter=COD_MUNI eq 291840`
- Dados de 2017 em diante (2015 e 2016 voltam vazios).
- Recursos usados: `Indicadores_Siope` (COD_INDI 24 = 1.1 % em MDE → F1; 56 = 4.8 investimento por aluno →
  F2.siope), `Receita_Siope` (F4), `Despesas_Funcao_Educacao_Siope`, `Dados_Gerais_Siope` (`$select` só de valores).
- **Não coletados** (dado pessoal): `Remuneracao_Siope` (nome de cada profissional) e os dados do responsável pela declaração.
- Fundeb (F4, coluna "Receitas Realizadas"): 2017–2020 `4,17,24,01,00,00` + `4,17,24,02,00,00`; 2021–2022
  `17580100` + `17180900` (cada um aparece repetido em sub-níveis com o mesmo valor — só o nível de cima entra);
  2023–2024 `17510000` + `17150000`. Juazeiro 2023: 167 200 041,80 + 117 558 344,15.
- Juazeiro 2023: F1 = 25,57%; investimento por aluno = R$ 9 601,27; despesa liquidada em educação = R$ 352 481 793,69.

## 8. SICONFI (Tesouro Nacional) — `siconfi` — P1

- API `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/` (paginada: `items`, `hasMore`, `offset`).
- DCA Anexo I-E: `dca?an_exercicio=2023&no_anexo=DCA-Anexo I-E&id_ente=2918407`; itens com `rotulo`
  "Total Geral da Despesa por Função", `coluna` (Empenhadas/Liquidadas/Pagas...), `conta` ("12 - Educação",
  "12.361 - Ensino Fundamental"...). Juazeiro 2023, 12 - Educação liquidada = 352 481 793,69 (= SIOPE).
- RREO Anexo 08 (MDE): **não consta** para Juazeiro (2016, 2019, 2023, 2024) nem Petrolina (2023) — o
  coletor consulta e registra alerta quando vem vazio.

## 9. IBGE — API de localidades

`https://servicodados.ibge.gov.br/api/v1/localidades/municipios/2918407|2611101` e `/estados/29|26`: nomes
oficiais dos territórios (com cache em `data/raw/ibge_localidades/`).

## Fontes P2/P3 ainda não coletadas

Ver `docs/pendencias.md`: ICA, Saeb (níveis de proficiência), Censo da Educação Superior, CAPES e dados da SEDUC.
