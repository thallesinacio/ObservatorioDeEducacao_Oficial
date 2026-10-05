# Dicionário de dados

Gerado automaticamente a partir dos comentários do banco (`COMMENT ON`) pelo comando `python -m observatorio docs dicionario`. Não edite à mão: altere o comentário na migration ou na view e gere de novo.

Gerado em 29/09/2026 20:16.

## Esquema `bi`

Camada de consumo do Power BI: views em esquema estrela, só com a versão vigente dos dados.

### `bi.cobertura_indicador_ano` (view)

Matriz de cobertura: para cada indicador, município (alvo e comparação) e ano, se há valor, lacuna registrada ou nada.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_indicador` | text | sim | Indicador. |
| `cod_territorio` | text | sim | Município. |
| `ano` | smallint | sim | Ano. |
| `linhas` | bigint | sim | Linhas no fato (todas as etapas e recortes). |
| `com_valor` | bigint | sim | Linhas com valor. |
| `situacao` | text | sim | com valor, com valor (estimado), lacuna registrada, fonte pendente, coleta manual ou não carregado. |

### `bi.dim_escola` (view)

Escolas (atributos da versão mais recente). Chave: co_entidade. O histórico de atributos fica em core.dim_escola.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `co_entidade` | character(8) | sim | Chave. Código INEP da escola (8 dígitos, texto). |
| `no_entidade` | text | sim | Nome da escola. |
| `cod_territorio` | text | sim | Município da escola. |
| `rede` | text | sim | Dependência administrativa. |
| `localizacao` | text | sim | Urbana ou Rural. |
| `situacao_funcionamento` | text | sim | Situação de funcionamento no último Censo (rótulo do dicionário do INEP). |
| `no_bairro` | text | sim | Bairro (não publicado em 2025). |
| `primeiro_ano_atributos` | smallint | sim | Primeiro ano com os atributos atuais. |
| `ultimo_ano_censo` | smallint | sim | Último ano em que a escola aparece no Censo carregado. |

### `bi.dim_etapa` (view)

Etapas e modalidades de ensino. Chave: cod_etapa ("total" = não se aplica).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_etapa` | text | sim | Chave. Código da etapa. |
| `nome` | text | sim | Nome da etapa. |
| `faixa_etaria_referencia` | text | sim | Faixa etária de referência. |
| `agrupamento` | text | sim | Etapa-mãe (para hierarquia no Power BI). |
| `ordem` | smallint | sim | Ordem de exibição (use "Classificar por coluna"). |

### `bi.dim_fonte` (view)

Fontes de dados. Chave: cod_fonte.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_fonte` | text | sim | Chave. Identificador da fonte. |
| `nome` | text | sim | Nome da fonte. |
| `orgao` | text | sim | Órgão produtor. |
| `prioridade` | text | sim | P1, P2 ou P3. |
| `url` | text | sim | Página oficial. |
| `tipo_acesso` | text | sim | download, api, derivado ou manual. |
| `formato` | text | sim | Formato do arquivo/resposta. |
| `periodicidade` | text | sim | Periodicidade de publicação. |
| `anos_disponiveis` | text | sim | Anos disponíveis na fonte. |
| `licenca` | text | sim | Licença/condições de uso. |
| `latencia_tipica` | text | sim | Defasagem típica de publicação. |
| `observacoes` | text | sim | Observações. |

### `bi.dim_indicador` (view)

Catálogo de indicadores com fórmula e nota metodológica. Chave: cod_indicador.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_indicador` | text | sim | Chave. Código do indicador (ex.: A1, B1.aprovacao). |
| `grupo` | text | sim | Código do plano ao qual o indicador pertence (ex.: B1). |
| `eixo` | text | sim | Eixo temático. |
| `nome` | text | sim | Nome do indicador. |
| `definicao` | text | sim | Definição. |
| `formula` | text | sim | Fórmula ou origem do número. |
| `unidade` | text | sim | Unidade de medida. |
| `polaridade` | text | sim | maior_melhor, menor_melhor ou neutro. |
| `meta_pme` | text | sim | Meta/estratégia do PME relacionada. |
| `meta_valor` | text | sim | Valor da meta do PME, quando houver. |
| `nivel_agregacao` | text | sim | Menor nível em que o indicador existe. |
| `cod_fonte` | text | sim | Fonte principal. |
| `nome_fonte` | text | sim | Nome da fonte principal. |
| `eh_calculo_proprio` | boolean | sim | Cálculo do Observatório (não é número oficial). |
| `cobertura` | text | sim | automatica, pendente ou manual_futura. |
| `nota_metodologica` | text | sim | Nota metodológica (limitações e cuidados de leitura). |
| `ordem` | integer | sim | Ordem de exibição. |

### `bi.dim_recorte` (view)

Recortes (rede, localização e um terceiro eixo). Chave: cod_recorte ("total" = sem recorte).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_recorte` | text | sim | Chave. Ex.: total, rede:municipal, rede:publica/localizacao:rural, raca_cor:parda. |
| `rotulo` | text | sim | Rótulo legível do recorte. |
| `rede` | text | sim | Rede do recorte ("todas" quando não há recorte de rede). |
| `localizacao` | text | sim | Localização do recorte ("todas" quando não há). |
| `tipo_outro` | text | sim | Terceiro eixo (sexo, raca_cor, porte, subfuncao, escolaridade, faixa_populacao...). |
| `valor_outro` | text | sim | Valor do terceiro eixo. |
| `ordem` | integer | sim | Ordem de exibição. |

### `bi.dim_status` (view)

Status possíveis de um valor. Chave: status_valor.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `status_valor` | text | sim | Chave. Código do status. |
| `rotulo` | text | sim | Rótulo. |
| `descricao` | text | sim | O que o status significa. |
| `eh_lacuna` | boolean | sim | Verdadeiro para sem_dado e nao_se_aplica. |
| `ordem` | integer | sim | Ordem de exibição. |

### `bi.dim_tempo` (view)

Anos. Chave: ano.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `ano` | smallint | sim | Chave. Ano de referência. |
| `rotulo` | text | sim | Rótulo do ano. |
| `data_referencia_censo` | date | sim | Data de referência do Censo Escolar no ano. |
| `eh_ano_pme` | boolean | sim | Ano da vigência do PME 2015-2025. |

### `bi.dim_territorio` (view)

Territórios: município-alvo, municípios de comparação, UF e Brasil. Chave: cod_territorio.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_territorio` | text | sim | Chave. Código IBGE em texto (7 dígitos município, 2 UF, "1" Brasil). |
| `nome` | text | sim | Nome do território. |
| `nivel` | text | sim | municipio, uf ou brasil. |
| `sg_uf` | character(2) | sim | Sigla da UF. |
| `cod_uf` | character(2) | sim | Código IBGE da UF. |
| `cod_municipio_6` | character(6) | sim | Código do município com 6 dígitos (DATASUS/SIOPE). |
| `eh_alvo` | boolean | sim | Município-alvo do Observatório. |
| `eh_comparacao` | boolean | sim | Território de comparação. |
| `nome_exibicao` | text | sim | Nome com a UF, para rótulos de gráfico. |
| `ordem` | integer | sim | Ordem sugerida de exibição (alvo primeiro). |

### `bi.dq_resultado` (view)

Resultado da última rodada dos testes de qualidade.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `teste` | text | sim | Nome do teste. |
| `tabela` | text | sim | Tabela testada. |
| `coluna` | text | sim | Coluna ou indicador testado. |
| `severidade` | text | sim | info, alerta ou erro. |
| `resultado` | text | sim | ok ou falha. |
| `ocorrencias` | integer | sim | Linhas que violaram a regra. |
| `detalhe` | text | sim | Explicação e exemplos. |
| `executado_em` | timestamp with time zone | sim | Momento do teste. |

### `bi.fato_avaliacao` (view)

Ideb, metas, notas do Saeb e taxas de aprovação usadas no Ideb, com todas as edições carregadas. Filtre eh_edicao_mais_recente para ter um valor por chave.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `ano` | smallint | sim | Ano de aplicação. |
| `cod_territorio` | text | sim | Território. |
| `co_entidade` | character(8) | sim | Escola (vazio = território). |
| `cod_etapa` | text | sim | Etapa avaliada. |
| `cod_recorte` | text | sim | Rede. |
| `componente` | text | sim | ideb, meta_ideb, matematica, lingua_portuguesa, nota_padronizada, indicador_rendimento, aprovacao. |
| `instrumento` | text | sim | Instrumento de medida. |
| `edicao` | smallint | sim | Edição da divulgação de onde o valor foi lido. |
| `valor` | numeric(12,4) | sim | Valor publicado. |
| `status_valor` | text | sim | observado ou sem_dado. |
| `data_coleta` | date | sim | Data da coleta. |
| `eh_edicao_mais_recente` | boolean | sim | Verdadeiro para o valor da edição mais recente. |

### `bi.fato_docente` (view)

Docentes por escola (Censo, soma conta duplicado quem atua em mais de uma escola) ou por município (Sinopse, docente único), versão vigente.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `ano` | smallint | sim | Ano do Censo. |
| `cod_territorio` | text | sim | Território. |
| `co_entidade` | character(8) | sim | Escola (vazio para número municipal da Sinopse). |
| `cod_etapa` | text | sim | Etapa. |
| `cod_recorte` | text | sim | Recorte (ex.: escolaridade:mestrado). |
| `qt_docentes` | integer | sim | Número de docentes. |
| `status_valor` | text | sim | observado ou sem_dado. |
| `cod_fonte` | text | sim | censo_escolar ou sinopse_estatistica. |
| `variavel_origem` | text | sim | Variável/coluna de origem. |
| `data_coleta` | date | sim | Data da coleta. |

### `bi.fato_financiamento` (view)

Receitas e despesas declaradas ao SIOPE e à DCA (SICONFI), versão vigente, em R$ correntes.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `ano` | smallint | sim | Exercício. |
| `cod_territorio` | text | sim | Município. |
| `cod_fonte` | text | sim | siope ou siconfi. |
| `demonstrativo` | text | sim | Demonstrativo de origem. |
| `rubrica_codigo` | text | sim | Código da rubrica/conta. |
| `rubrica_nome` | text | sim | Nome da rubrica/conta. |
| `coluna` | text | sim | Coluna do demonstrativo (ex.: Receitas Realizadas, Despesas Liquidadas). |
| `ordem` | text | sim | Ordem/identificação da linha no demonstrativo. |
| `valor` | numeric(20,2) | sim | Valor em R$ correntes. |
| `data_coleta` | date | sim | Data da coleta. |

### `bi.fato_indicador` (view)

Fato central: um valor por indicador x território (ou escola) x ano x etapa x recorte, versão vigente. Lacuna tem valor vazio e status sem_dado/nao_se_aplica (nunca zero).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_indicador` | text | sim | Indicador (bi.dim_indicador). |
| `cod_territorio` | text | sim | Território (bi.dim_territorio). |
| `co_entidade` | character(8) | sim | Escola (bi.dim_escola); vazio = agregado do território. |
| `ano` | smallint | sim | Ano (bi.dim_tempo). |
| `cod_etapa` | text | sim | Etapa (bi.dim_etapa). |
| `cod_recorte` | text | sim | Recorte (bi.dim_recorte). |
| `valor` | numeric(20,4) | sim | Valor do indicador. Vazio quando é lacuna. |
| `numerador` | numeric(20,4) | sim | Numerador usado (quando aplicável). |
| `denominador` | numeric(20,4) | sim | Denominador usado (quando aplicável). |
| `status_valor` | text | sim | Status do valor (bi.dim_status). |
| `eh_lacuna` | boolean | sim | Verdadeiro para sem_dado e nao_se_aplica. |
| `eh_estimado` | boolean | sim | Verdadeiro quando o valor usa estimativa (ex.: população projetada). |
| `eh_proxy_estadual` | boolean | sim | Verdadeiro quando o valor é da UF usado no lugar do municipal. |
| `eh_calculo_proprio` | boolean | sim | Verdadeiro quando é cálculo do Observatório (não é número oficial). |
| `cod_fonte` | text | sim | Fonte do valor (bi.dim_fonte). |
| `data_coleta` | date | sim | Data da coleta mais recente das entradas. |
| `id_versao` | integer | sim | Versão do cálculo (etl.versao_dados). |
| `referencia` | text | sim | Procedência detalhada (arquivo, coluna, edição da estimativa). |
| `nota` | text | sim | Observação sobre o valor. |
| `nivel` | text | sim | territorio ou escola. |

### `bi.fato_matricula` (view)

Matrículas por escola, ano, etapa e recorte (microdados do Censo Escolar), versão vigente.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `ano` | smallint | sim | Ano do Censo. |
| `co_entidade` | character(8) | sim | Escola. |
| `cod_territorio` | text | sim | Município. |
| `cod_etapa` | text | sim | Etapa. |
| `cod_recorte` | text | sim | Recorte (sexo, cor/raça, faixa etária, turno...). |
| `qt_matriculas` | integer | sim | Matrículas; vazio = célula vazia na origem. |
| `status_valor` | text | sim | observado ou sem_dado. |
| `variavel_origem` | text | sim | Variável do Censo. |
| `data_coleta` | date | sim | Data da coleta. |

### `bi.fato_populacao` (view)

População por idade simples (RIPSA estimada; Censo 2022 observada), versão vigente.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `ano` | smallint | sim | Ano. |
| `cod_territorio` | text | sim | Município. |
| `sexo` | text | sim | T = total. |
| `idade` | smallint | sim | Idade em anos (80 = 80 ou mais na RIPSA; 100 = 100 ou mais no Censo). |
| `populacao` | integer | sim | Pessoas. |
| `origem` | text | sim | ripsa_ftp, ripsa_tabnet ou ibge_censo2022. |
| `edicao` | text | sim | Edição da estimativa. |
| `status_valor` | text | sim | estimado ou observado. |
| `data_coleta` | date | sim | Data da coleta. |

### `bi.fato_rendimento` (view)

Taxas de rendimento e distorção idade-série do INEP (formato longo), versão vigente.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `ano` | smallint | sim | Ano. |
| `cod_territorio` | text | sim | Território. |
| `co_entidade` | character(8) | sim | Escola (vazio = território). |
| `cod_etapa` | text | sim | Etapa / ano / série. |
| `cod_recorte` | text | sim | Rede x localização. |
| `medida` | text | sim | aprovacao, reprovacao, abandono ou distorcao_idade_serie. |
| `valor` | numeric(9,4) | sim | Taxa em %. |
| `status_valor` | text | sim | observado, sem_dado ou nao_se_aplica. |
| `cod_fonte` | text | sim | Fonte. |
| `data_coleta` | date | sim | Data da coleta. |

### `bi.fonte_situacao` (view)

Situação de cada fonte: última coleta, anos disponíveis, última execução e versão vigente.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_fonte` | text | sim | Fonte. |
| `nome` | text | sim | Nome da fonte. |
| `prioridade` | text | sim | Prioridade (P1, P2, P3). |
| `ultima_coleta` | timestamp with time zone | sim | Momento da coleta mais recente. |
| `arquivos` | bigint | sim | Arquivos/consultas processados. |
| `primeiro_ano` | smallint | sim | Primeiro ano coletado. |
| `ultimo_ano` | smallint | sim | Último ano coletado. |
| `ultima_tarefa` | text | sim | Última tarefa executada (coletar, transformar...). |
| `ultimo_status` | text | sim | Status da última tarefa. |
| `ultima_execucao` | timestamp with time zone | sim | Fim da última tarefa. |
| `ultima_mensagem` | text | sim | Alertas ou erro da última tarefa (resumo). |
| `versao_vigente` | integer | sim | Versão de dados exibida. |
| `versao_criada_em` | timestamp with time zone | sim | Quando a versão vigente foi criada. |

### `bi.meta_pme` (view)

Série do PME como publicada no relatório de avaliação (preenchimento manual em etapa futura).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `meta_pme` | text | sim | Meta do PME. |
| `indicador_pme` | text | sim | Indicador do PME. |
| `ano` | smallint | sim | Ano. |
| `cod_indicador` | text | sim | Indicador equivalente do Observatório. |
| `valor_publicado` | numeric(20,4) | sim | Valor publicado. |
| `valor_publicado_texto` | text | sim | Valor como aparece no relatório. |
| `valor_meta` | text | sim | Meta. |
| `situacao_declarada` | text | sim | Situação declarada. |
| `fonte_declarada` | text | sim | Fonte informada no relatório. |
| `documento` | text | sim | Documento de origem. |
| `observacao` | text | sim | Observação. |

### `bi.qualidade_status` (view)

Percentual de linhas por status (observado, estimado, sem_dado...) em cada indicador e território.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_indicador` | text | sim | Indicador. |
| `cod_territorio` | text | sim | Território. |
| `status_valor` | text | sim | Status. |
| `linhas` | bigint | sim | Quantidade de linhas. |
| `percentual` | numeric | sim | Percentual das linhas do indicador no território. |

## Esquema `core`

Camada central: dimensões, fatos e indicadores, com histórico de versões.

### `core.dim_codigo_inep` (tabela)

Tabela auxiliar de decodificação dos códigos do INEP (dependência, localização, situação de funcionamento...), extraída do dicionário de dados que vem no ZIP do Censo Escolar. Vale o dicionário mais recente carregado.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `variavel` | text | não | Nome da variável no Censo, ex.: TP_DEPENDENCIA. |
| `codigo` | text | não | Código da categoria. |
| `rotulo` | text | não | Rótulo da categoria, como no dicionário do INEP. |
| `ano_dicionario` | smallint | não | Ano do dicionário de onde o rótulo foi lido. |

### `core.dim_escola` (tabela)

Escolas como dimensão de mudança lenta (tipo 2): uma linha por período em que os atributos ficaram iguais. Reconstruída a partir de staging.censo_escola a cada carga.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `co_entidade` | character(8) | não | Código INEP da escola, 8 dígitos, texto. |
| `valid_from` | smallint | não | Primeiro ano do Censo com estes atributos. |
| `valid_to` | smallint | sim | Último ano do Censo com estes atributos (vazio se ainda vale no último Censo carregado). |
| `eh_vigente` | boolean | não | Verdadeiro para a versão mais recente da escola. |
| `no_entidade` | text | sim | Nome da escola no Censo. |
| `cod_territorio` | text | sim | Município da escola (código IBGE de 7 dígitos). |
| `tp_dependencia` | smallint | sim | Dependência administrativa (código INEP; rótulo em core.dim_codigo_inep). |
| `tp_categoria_escola_privada` | smallint | sim | Categoria da escola privada (código INEP). |
| `tp_localizacao` | smallint | sim | Localização (código INEP: 1 urbana, 2 rural). |
| `tp_localizacao_diferenciada` | smallint | sim | Localização diferenciada (código INEP). |
| `tp_situacao_funcionamento` | smallint | sim | Situação de funcionamento (código INEP). |
| `no_bairro` | text | sim | Bairro (não publicado nos microdados de 2025). |
| `co_distrito` | text | sim | Código do distrito (IBGE). |
| `latitude` | numeric(10,7) | sim | Latitude (não publicada nos microdados públicos; reservada para a etapa com a SEDUC). |
| `longitude` | numeric(10,7) | sim | Longitude (idem). |
| `ultimo_ano_censo` | smallint | não | Último ano em que a escola aparece no Censo carregado. |
| `hash_atributos` | character(32) | não | Hash dos atributos, usado para detectar mudança. |

### `core.dim_etapa` (tabela)

Etapas e modalidades de ensino (carregada de config/etapas.yaml).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_etapa` | text | não | Código da etapa, ex.: fund_ai (anos iniciais), med_serie_1 (1ª série do ensino médio), total (não se aplica). |
| `nome` | text | não | Nome da etapa. |
| `faixa_etaria_referencia` | text | sim | Faixa etária adequada à etapa, quando houver. |
| `agrupamento` | text | não | Etapa de nível superior (ex.: fund_ai pertence a Ensino Fundamental). |
| `ordem` | smallint | não | Ordem de exibição. |

### `core.dim_fonte` (tabela)

Fontes de dados (carregada de config/fontes.yaml).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id_fonte` | integer | não | Chave numérica da fonte. |
| `cod_fonte` | text | não | Identificador textual da fonte, igual ao de config/fontes.yaml. |
| `nome` | text | não | Nome da fonte. |
| `orgao` | text | sim | Órgão produtor. |
| `prioridade` | text | sim | P1, P2 ou P3 nesta etapa. |
| `url` | text | sim | Página oficial. |
| `tipo_acesso` | text | sim | api, download, scraping, manual ou derivado. |
| `formato` | text | sim | Formato dos arquivos. |
| `periodicidade` | text | sim | Periodicidade de publicação. |
| `anos_disponiveis` | text | sim | Anos disponíveis na fonte. |
| `licenca` | text | sim | Licença / condição de uso. |
| `latencia_tipica` | text | sim | Defasagem típica entre a referência e a publicação. |
| `observacoes` | text | sim | Observações sobre a fonte. |

### `core.dim_indicador` (tabela)

Catálogo de indicadores (carregado de config/indicadores.yaml). Indicador novo = linha nova, sem mudar o esquema.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_indicador` | text | não | Código do indicador, ex.: A1, B1.aprovacao, F2.siope. |
| `grupo` | text | não | Código do plano técnico ao qual o indicador pertence (A1 a G4). |
| `eixo` | text | não | Eixo temático (A a G). |
| `nome` | text | não | Nome do indicador. |
| `definicao` | text | não | O que o indicador mede. |
| `formula` | text | não | Fórmula ou origem do valor. |
| `unidade` | text | não | Unidade de medida. |
| `polaridade` | text | não | maior_melhor, menor_melhor ou neutro. |
| `meta_pme` | text | sim | Meta(s) do PME 2015-2025 relacionada(s). |
| `meta_valor` | text | sim | Valor da meta do PME, em texto. |
| `nivel_agregacao` | text | não | municipio, escola ou municipio_e_escola. |
| `cod_fonte` | text | não | Fonte principal (calculo_observatorio quando é cálculo próprio). |
| `eh_calculo_proprio` | boolean | não | Verdadeiro quando o valor é calculado pelo Observatório (não é número oficial). |
| `cobertura` | text | não | automatica (calculado nesta etapa), pendente (fonte ainda não viável) ou manual_futura (depende da SEDUC). |
| `nota_metodologica` | text | sim | Nota metodológica a exibir junto do número. |
| `ordem` | integer | não | Ordem de exibição. |

### `core.dim_recorte` (tabela)

Recortes analíticos. Um recorte combina até três eixos: rede, localização e um terceiro (sexo, cor/raça, faixa etária, porte, grupo AFD, subfunção...). O código "total" significa sem recorte.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_recorte` | text | não | Código canônico, ex.: total; rede:municipal; rede:municipal/localizacao:rural; raca_cor:parda. |
| `rotulo` | text | não | Rótulo legível. |
| `rede` | text | sim | Rede (dependência administrativa): federal, estadual, municipal, privada, publica ou vazio (todas). |
| `localizacao` | text | sim | urbana, rural ou vazio (todas). |
| `tipo_outro` | text | sim | Tipo do terceiro eixo, ex.: raca_cor, sexo, faixa_etaria, porte, afd_grupo, subfuncao. |
| `valor_outro` | text | sim | Valor do terceiro eixo. |
| `ordem` | integer | não | Ordem de exibição. |

### `core.dim_tempo` (tabela)

Anos de referência.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `ano` | smallint | não | Ano de referência dos dados. |
| `data_referencia_censo` | date | não | Data de referência do Censo Escolar: última quarta-feira de maio (nota do dicionário de dados do INEP). |
| `rotulo` | text | não | Rótulo de exibição do ano. |
| `eh_ano_pme` | boolean | não | Verdadeiro para os anos de vigência do PME 2015-2025. |

### `core.dim_territorio` (tabela)

Territórios: municípios (código IBGE de 7 dígitos), UFs (2 dígitos) e Brasil (código 1, convenção do SIDRA). Generaliza a dim_municipio do plano técnico para acomodar os comparadores.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `cod_territorio` | text | não | Código IBGE como texto: 7 dígitos para município, 2 para UF, "1" para Brasil. |
| `nome` | text | não | Nome do território. |
| `nivel` | text | não | municipio, uf ou brasil. |
| `sg_uf` | character(2) | sim | Sigla da UF (vazio para Brasil). |
| `cod_uf` | character(2) | sim | Código IBGE da UF (2 dígitos). |
| `cod_municipio_6` | character(6) | sim | Código do município com 6 dígitos (sem dígito verificador), usado por DATASUS e SIOPE. |
| `eh_alvo` | boolean | não | Município-alvo do Observatório (config/projeto.yaml). |
| `eh_comparacao` | boolean | não | Território carregado só para comparação. |

### `core.fato_avaliacao` (tabela)

Resultados de avaliação (Ideb, notas do Saeb, indicador de rendimento, metas). O instrumento aplicado fica gravado para marcar quebra de série (ex.: ANA -> Saeb 2º ano -> ICA).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | não | Chave técnica. |
| `ano` | smallint | não | Ano de aplicação/referência. |
| `cod_territorio` | text | não | Território. |
| `co_entidade` | character(8) | sim | Escola; nulo para agregado do território. |
| `cod_etapa` | text | não | Etapa avaliada (fund_ai = 5º ano, fund_af = 9º ano, med = ensino médio). |
| `cod_recorte` | text | não | Rede. |
| `componente` | text | não | ideb, meta_ideb, matematica, lingua_portuguesa, nota_padronizada, indicador_rendimento ou aprovacao. |
| `instrumento` | text | não | Instrumento de medida (ex.: Saeb/Ideb). |
| `edicao` | smallint | não | Edição da publicação de onde o valor foi lido (o INEP revisa valores já publicados). |
| `valor` | numeric(12,4) | sim | Valor publicado. |
| `status_valor` | text | não | observado, sem_dado ou nao_se_aplica. |
| `id_fonte` | integer | não | Fonte. |
| `id_versao` | integer | não | Versão de carga. |
| `data_coleta` | date | não | Data da coleta do arquivo. |

### `core.fato_docente` (tabela)

Docentes por escola (Censo Escolar, QT_DOC_*) ou por município (Sinopse Estatística, docentes únicos), por etapa e recorte (ex.: escolaridade).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | não | Chave técnica. |
| `ano` | smallint | não | Ano do Censo Escolar. |
| `cod_territorio` | text | não | Município. |
| `co_entidade` | character(8) | sim | Código INEP da escola; nulo quando o número é municipal (Sinopse). |
| `cod_etapa` | text | não | Etapa em que o docente atua. |
| `cod_recorte` | text | não | Recorte, ex.: escolaridade:pos_graduacao, rede:municipal. |
| `qt_docentes` | integer | sim | Número de docentes. Somar escolas conta duas vezes o docente que atua em mais de uma. |
| `variavel_origem` | text | não | Variável ou coluna de origem. |
| `id_fonte` | integer | não | Fonte (Censo Escolar ou Sinopse). |
| `status_valor` | text | não | observado ou sem_dado. |
| `id_versao` | integer | não | Versão de carga. |
| `data_coleta` | date | não | Data da coleta do arquivo. |

### `core.fato_financiamento` (tabela)

Valores financeiros por ano, território, fonte e rubrica (SIOPE: receitas, despesas por subfunção, totais; SICONFI: DCA Anexo I-E, função 12 - Educação).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | não | Chave técnica. |
| `ano` | smallint | não | Exercício. |
| `cod_territorio` | text | não | Município. |
| `id_fonte` | integer | não | Fonte (SIOPE ou SICONFI). |
| `demonstrativo` | text | não | Demonstrativo de origem, ex.: SIOPE-Receita, SIOPE-Despesa-Funcao, SIOPE-Dados-Gerais, DCA-Anexo I-E. |
| `rubrica_codigo` | text | não | Código da rubrica/conta. |
| `rubrica_nome` | text | não | Nome da rubrica/conta. |
| `coluna` | text | não | Coluna do demonstrativo, ex.: Receitas Realizadas, Despesas Liquidadas. |
| `ordem` | text | não | Ordem da linha no demonstrativo (desempata rubricas repetidas). |
| `valor` | numeric(20,2) | sim | Valor em R$ correntes. |
| `id_versao` | integer | não | Versão de carga. |
| `data_coleta` | date | não | Data da coleta. |

### `core.fato_indicador` (tabela)

Tabela central de indicadores em formato longo: indicador x território (ou escola) x ano x etapa x recorte x versão. Todo valor tem fonte, data de coleta, versão e status; numerador e denominador quando aplicável.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | não | Chave técnica. |
| `cod_indicador` | text | não | Indicador (core.dim_indicador). |
| `cod_territorio` | text | não | Território (município, UF ou Brasil). |
| `co_entidade` | character(8) | sim | Código INEP da escola; nulo = agregado do território. A unicidade trata nulos como iguais (NULLS NOT DISTINCT). |
| `ano` | smallint | não | Ano de referência. |
| `cod_etapa` | text | não | Etapa/modalidade (total quando não se aplica). |
| `cod_recorte` | text | não | Recorte (total = sem recorte). |
| `valor` | numeric(20,4) | sim | Valor do indicador. Nulo quando status é sem_dado ou nao_se_aplica: lacuna nunca vira zero. |
| `numerador` | numeric(20,4) | sim | Numerador usado no cálculo (quando aplicável). |
| `denominador` | numeric(20,4) | sim | Denominador usado no cálculo (quando aplicável). |
| `status_valor` | text | não | observado, estimado (usa estimativa populacional ou aproximação), proxy_estadual, sem_dado ou nao_se_aplica. |
| `eh_calculo_proprio` | boolean | não | Verdadeiro quando o valor é cálculo do Observatório e não número oficial. |
| `id_fonte` | integer | não | Fonte principal do valor. |
| `data_coleta` | date | não | Data da coleta mais recente entre as entradas do valor. |
| `id_versao` | integer | não | Versão do cálculo (etl.versao_dados da fonte calculo_observatorio): identifica as versões das fontes e do método usados. |
| `referencia` | text | sim | Procedência detalhada (ex.: edição da estimativa populacional, arquivo, coluna de origem). |
| `nota` | text | sim | Observação sobre o valor (ex.: aproximação usada, quebra de série). |

### `core.fato_matricula` (tabela)

Matrículas por escola, ano, etapa e recorte (sexo, cor/raça, faixa etária, turno, localização de residência), a partir das contagens QT_MAT_* do Censo Escolar.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | não | Chave técnica. |
| `ano` | smallint | não | Ano do Censo Escolar. |
| `co_entidade` | character(8) | não | Código INEP da escola (8 dígitos). |
| `cod_territorio` | text | não | Município da escola. |
| `cod_etapa` | text | não | Etapa/modalidade (core.dim_etapa). |
| `cod_recorte` | text | não | Recorte (core.dim_recorte); total = sem recorte. |
| `qt_matriculas` | integer | sim | Número de matrículas; nulo quando a célula veio vazia (nunca zero por ausência). |
| `variavel_origem` | text | não | Variável do Censo de onde veio o número (ex.: QT_MAT_FUND_AI). |
| `status_valor` | text | não | observado ou sem_dado. |
| `id_versao` | integer | não | Versão de carga (etl.versao_dados). |
| `data_coleta` | date | não | Data em que o arquivo de origem foi baixado. |

### `core.fato_meta_pme` (tabela)

Série do PME 2015-2025 como foi publicada no relatório de avaliação (inclusive com erros), para comparar com o valor recalculado pelo Observatório. Preenchida manualmente em etapa futura.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `meta_pme` | text | não | Número da meta do PME (1 a 20). |
| `indicador_pme` | text | não | Indicador do PME (ex.: 1A, 3B). |
| `ano` | smallint | não | Ano. |
| `cod_indicador` | text | sim | Indicador equivalente do Observatório (quando houver). |
| `valor_publicado` | numeric(20,4) | sim | Valor numérico publicado no relatório. |
| `valor_publicado_texto` | text | sim | Valor como aparece no relatório (ex.: "Oscilante", "Sem dados"). |
| `valor_meta` | text | sim | Meta do PME. |
| `situacao_declarada` | text | sim | Situação declarada no relatório (alcançada, não alcançada...). |
| `fonte_declarada` | text | sim | Fonte informada no relatório. |
| `documento` | text | não | Documento de onde o valor foi transcrito. |
| `observacao` | text | sim | Observação (ex.: inconsistência entre quadros do relatório). |

### `core.fato_populacao` (tabela)

População por idade simples e sexo. Estimativas (RIPSA) têm status estimado; o Censo 2022, observado. A edição da estimativa fica em "edicao".

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | não | Chave técnica. |
| `ano` | smallint | não | Ano de referência. |
| `cod_territorio` | text | não | Município. |
| `sexo` | text | não | M, F ou T (total). |
| `idade` | smallint | não | Idade em anos completos (80 = 80 anos ou mais na RIPSA; 100 = 100 ou mais no Censo). |
| `populacao` | integer | sim | Pessoas. |
| `origem` | text | não | ripsa_ftp, ripsa_tabnet ou ibge_censo2022. |
| `edicao` | text | não | Edição/versão da estimativa (ex.: RIPSA 2000-2025, consulta de 2026-09-29). |
| `status_valor` | text | não | estimado (projeção) ou observado (censo). |
| `id_fonte` | integer | não | Fonte. |
| `id_versao` | integer | não | Versão de carga. |
| `data_coleta` | date | não | Data da coleta. |

### `core.fato_rendimento` (tabela)

Taxas de rendimento (aprovação, reprovação, abandono) e de distorção idade-série publicadas pelo INEP, por território ou escola, etapa e recorte (rede x localização). Formato longo: uma linha por medida.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | não | Chave técnica. |
| `ano` | smallint | não | Ano de referência. |
| `cod_territorio` | text | não | Território. |
| `co_entidade` | character(8) | sim | Escola; nulo quando é agregado do território. |
| `cod_etapa` | text | não | Etapa (inclui ano/série). |
| `cod_recorte` | text | não | Recorte rede x localização. |
| `medida` | text | não | aprovacao, reprovacao, abandono ou distorcao_idade_serie. |
| `valor` | numeric(9,4) | sim | Taxa em %. |
| `status_valor` | text | não | observado, sem_dado ou nao_se_aplica (marcador do INEP para recorte sem matrícula). |
| `id_fonte` | integer | não | Fonte. |
| `id_versao` | integer | não | Versão de carga. |
| `data_coleta` | date | não | Data da coleta do arquivo. |

### `core.fato_turma` (tabela)

Turmas por escola, ano, etapa e recorte (contagens QT_TUR_* do Censo Escolar).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | não | Chave técnica. |
| `ano` | smallint | não | Ano do Censo Escolar. |
| `co_entidade` | character(8) | não | Código INEP da escola. |
| `cod_territorio` | text | não | Município da escola. |
| `cod_etapa` | text | não | Etapa/modalidade. |
| `cod_recorte` | text | não | Recorte (turno, tempo integral). |
| `qt_turmas` | integer | sim | Número de turmas. |
| `variavel_origem` | text | não | Variável do Censo de origem. |
| `status_valor` | text | não | observado ou sem_dado. |
| `id_versao` | integer | não | Versão de carga. |
| `data_coleta` | date | não | Data da coleta do arquivo. |

### `core.v_contagem_escola` (view)

Contagens do Censo Escolar (matrículas, docentes e turmas) por escola e variável de origem, versão vigente. Valor nulo = célula vazia na origem.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `ano` | smallint | sim |  |
| `co_entidade` | character(8) | sim |  |
| `cod_territorio` | text | sim |  |
| `variavel` | text | sim |  |
| `valor` | integer | sim |  |
| `data_coleta` | date | sim |  |

### `core.v_escola_ano` (view)

Cadastro da escola em cada ano do Censo Escolar (rede, localização, situação e itens de infraestrutura já combinados). Indicadores IN_* ausentes no layout do ano ficam nulos.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `ano` | smallint | sim |  |
| `co_entidade` | character(8) | sim |  |
| `cod_territorio` | character(7) | sim |  |
| `no_entidade` | text | sim |  |
| `tp_dependencia` | smallint | sim |  |
| `rede` | text | sim |  |
| `eh_publica` | boolean | sim |  |
| `localizacao` | text | sim |  |
| `tp_situacao_funcionamento` | smallint | sim |  |
| `em_atividade` | boolean | sim |  |
| `in_internet` | smallint | sim |  |
| `tem_biblioteca_ou_sala_leitura` | integer | sim |  |
| `tem_laboratorio` | integer | sim |  |
| `in_quadra_esportes` | smallint | sim |  |
| `tem_acessibilidade` | integer | sim |  |
| `in_sala_atendimento_especial` | smallint | sim |  |
| `tp_aee` | smallint | sim |  |
| `versao_layout` | text | sim |  |
| `data_coleta` | date | sim |  |

### `core.v_escola_recorte` (view)

Para cada escola e ano, os recortes de rede x localização aos quais ela pertence (total, rede:municipal, rede:publica, localizacao:rural, rede:municipal|localizacao:rural...). Base para somar escolas por recorte.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `ano` | smallint | sim |  |
| `co_entidade` | character(8) | sim |  |
| `cod_territorio` | character(7) | sim |  |
| `cod_recorte` | text | sim |  |

### `core.v_fato_avaliacao` (view)

core.fato_avaliacao, só a versão vigente (todas as edições do Ideb carregadas).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | sim |  |
| `ano` | smallint | sim |  |
| `cod_territorio` | text | sim |  |
| `co_entidade` | character(8) | sim |  |
| `cod_etapa` | text | sim |  |
| `cod_recorte` | text | sim |  |
| `componente` | text | sim |  |
| `instrumento` | text | sim |  |
| `edicao` | smallint | sim |  |
| `valor` | numeric(12,4) | sim |  |
| `status_valor` | text | sim |  |
| `id_fonte` | integer | sim |  |
| `id_versao` | integer | sim |  |
| `data_coleta` | date | sim |  |

### `core.v_fato_docente` (view)

core.fato_docente, só a versão vigente.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | sim |  |
| `ano` | smallint | sim |  |
| `cod_territorio` | text | sim |  |
| `co_entidade` | character(8) | sim |  |
| `cod_etapa` | text | sim |  |
| `cod_recorte` | text | sim |  |
| `qt_docentes` | integer | sim |  |
| `variavel_origem` | text | sim |  |
| `id_fonte` | integer | sim |  |
| `status_valor` | text | sim |  |
| `id_versao` | integer | sim |  |
| `data_coleta` | date | sim |  |

### `core.v_fato_financiamento` (view)

core.fato_financiamento, só a versão vigente de cada fonte.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | sim |  |
| `ano` | smallint | sim |  |
| `cod_territorio` | text | sim |  |
| `id_fonte` | integer | sim |  |
| `demonstrativo` | text | sim |  |
| `rubrica_codigo` | text | sim |  |
| `rubrica_nome` | text | sim |  |
| `coluna` | text | sim |  |
| `ordem` | text | sim |  |
| `valor` | numeric(20,2) | sim |  |
| `id_versao` | integer | sim |  |
| `data_coleta` | date | sim |  |

### `core.v_fato_indicador` (view)

core.fato_indicador, só a versão vigente do cálculo.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | sim |  |
| `cod_indicador` | text | sim |  |
| `cod_territorio` | text | sim |  |
| `co_entidade` | character(8) | sim |  |
| `ano` | smallint | sim |  |
| `cod_etapa` | text | sim |  |
| `cod_recorte` | text | sim |  |
| `valor` | numeric(20,4) | sim |  |
| `numerador` | numeric(20,4) | sim |  |
| `denominador` | numeric(20,4) | sim |  |
| `status_valor` | text | sim |  |
| `eh_calculo_proprio` | boolean | sim |  |
| `id_fonte` | integer | sim |  |
| `data_coleta` | date | sim |  |
| `id_versao` | integer | sim |  |
| `referencia` | text | sim |  |
| `nota` | text | sim |  |

### `core.v_fato_matricula` (view)

core.fato_matricula, só a versão vigente.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | sim |  |
| `ano` | smallint | sim |  |
| `co_entidade` | character(8) | sim |  |
| `cod_territorio` | text | sim |  |
| `cod_etapa` | text | sim |  |
| `cod_recorte` | text | sim |  |
| `qt_matriculas` | integer | sim |  |
| `variavel_origem` | text | sim |  |
| `status_valor` | text | sim |  |
| `id_versao` | integer | sim |  |
| `data_coleta` | date | sim |  |

### `core.v_fato_populacao` (view)

core.fato_populacao, só a versão vigente de cada fonte.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | sim |  |
| `ano` | smallint | sim |  |
| `cod_territorio` | text | sim |  |
| `sexo` | text | sim |  |
| `idade` | smallint | sim |  |
| `populacao` | integer | sim |  |
| `origem` | text | sim |  |
| `edicao` | text | sim |  |
| `status_valor` | text | sim |  |
| `id_fonte` | integer | sim |  |
| `id_versao` | integer | sim |  |
| `data_coleta` | date | sim |  |

### `core.v_fato_rendimento` (view)

core.fato_rendimento, só a versão vigente.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | sim |  |
| `ano` | smallint | sim |  |
| `cod_territorio` | text | sim |  |
| `co_entidade` | character(8) | sim |  |
| `cod_etapa` | text | sim |  |
| `cod_recorte` | text | sim |  |
| `medida` | text | sim |  |
| `valor` | numeric(9,4) | sim |  |
| `status_valor` | text | sim |  |
| `id_fonte` | integer | sim |  |
| `id_versao` | integer | sim |  |
| `data_coleta` | date | sim |  |

### `core.v_fato_turma` (view)

core.fato_turma, só a versão vigente.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id` | bigint | sim |  |
| `ano` | smallint | sim |  |
| `co_entidade` | character(8) | sim |  |
| `cod_territorio` | text | sim |  |
| `cod_etapa` | text | sim |  |
| `cod_recorte` | text | sim |  |
| `qt_turmas` | integer | sim |  |
| `variavel_origem` | text | sim |  |
| `status_valor` | text | sim |  |
| `id_versao` | integer | sim |  |
| `data_coleta` | date | sim |  |

## Esquema `etl`

Tabelas operacionais: execuções, arquivos coletados, versões, testes de qualidade e conciliação de códigos.

### `etl.de_para` (tabela)

Conciliação de valores entre fontes (ex.: nomes de rede "Particular" x "Privada"; nomes de escola SIEJ x INEP).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `dominio` | text | não | Domínio do valor, ex.: dependencia, localizacao, escola_nome. |
| `valor_origem` | text | não |  |
| `valor_canonico` | text | não |  |
| `fonte` | text | sim |  |
| `observacao` | text | sim |  |
| `atualizado_em` | timestamp with time zone | não |  |

### `etl.dq_resultado` (tabela)

Resultado dos testes de qualidade do dado (unicidade, faixas válidas, soma das partes, variação anual, conferência cruzada).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id_resultado` | bigint | não |  |
| `id_execucao` | bigint | sim |  |
| `teste` | text | não |  |
| `tabela` | text | não |  |
| `coluna` | text | sim |  |
| `severidade` | text | não | info, alerta (não interrompe) ou erro. |
| `resultado` | text | não | ok ou falha. |
| `ocorrencias` | integer | não | Quantidade de linhas que violaram a regra. |
| `detalhe` | text | sim | Exemplos das violações ou explicação do teste. |
| `executado_em` | timestamp with time zone | não |  |

### `etl.etl_arquivo` (tabela)

Manifesto dos arquivos brutos coletados: de onde veio, quando, hash sha256 e onde está no disco. Permite rebaixar e conferir.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id_arquivo` | bigint | não |  |
| `id_fonte` | text | não | Fonte do arquivo (id de config/fontes.yaml). |
| `ano_referencia` | smallint | sim | Ano de referência dos dados do arquivo (para o Ideb, o ano da edição). |
| `url` | text | não | Endereço de onde o arquivo foi baixado (ou a consulta da API). |
| `sha256` | character(64) | não | Hash sha256 do conteúdo; o mesmo hash não é reprocessado, salvo com --forcar. |
| `data_coleta` | timestamp with time zone | não | Momento do download. |
| `caminho_local` | text | não | Caminho do arquivo em data/raw/<fonte>/<ano>/ (relativo à pasta de dados). |
| `tamanho_bytes` | bigint | não | Tamanho do arquivo em bytes. |
| `status_http` | integer | sim | Código HTTP da resposta (ou 226 para FTP). |
| `http_last_modified` | text | sim | Cabeçalho Last-Modified da resposta; usado para não baixar de novo um arquivo grande que não mudou. |
| `http_etag` | text | sim | Cabeçalho ETag da resposta (quando o servidor informa). |
| `versao_layout` | text | sim | Layout identificado (ex.: censo_escolar L2015 ou L2025), para rastrear mudanças de formato. |
| `descricao` | text | sim |  |
| `id_execucao` | bigint | sim |  |
| `processado_em` | timestamp with time zone | sim | Quando o arquivo foi carregado com sucesso no raw/staging. |
| `arquivo_removido` | boolean | não | Verdadeiro quando o arquivo foi apagado do disco depois de processado (opção manter_zip_bruto = false). |

### `etl.etl_execucao` (tabela)

Uma linha por execução de job (coleta, transformação, cálculo de indicadores, testes).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id_execucao` | bigint | não |  |
| `job` | text | não | Nome do job, ex.: coletar, transformar, indicadores, qualidade, pipeline. |
| `id_fonte` | text | sim | Fonte processada (id de config/fontes.yaml), quando o job é por fonte. |
| `parametros` | text | sim | Parâmetros usados (anos, opções), em texto. |
| `inicio` | timestamp with time zone | não |  |
| `fim` | timestamp with time zone | sim |  |
| `status` | text | não | em_andamento, sucesso, sucesso_com_alertas, falha ou ignorado (nada novo a processar). |
| `linhas_lidas` | bigint | não | Linhas lidas das fontes nesta execução. |
| `linhas_gravadas` | bigint | não | Linhas gravadas no banco nesta execução. |
| `mensagem_erro` | text | sim | Mensagem do erro, quando status = falha. |

### `etl.migracao` (tabela)

Migrations de esquema já aplicadas (sql/migracoes).

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `versao` | text | não |  |
| `arquivo` | text | não |  |
| `sha256` | character(64) | não |  |
| `aplicada_em` | timestamp with time zone | não |  |

### `etl.regra_ausencia` (tabela)

Como cada marcador de ausência de cada fonte vira status (carregada de config/regras_ausencia.yaml). Nenhum marcador vira zero.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id_fonte` | text | não |  |
| `marcador` | text | não |  |
| `status_valor` | text | não |  |
| `descricao` | text | sim |  |

### `etl.versao_dados` (tabela)

Versões de carga. A assinatura é o hash dos arquivos de entrada (e, para indicadores, das versões das fontes e da versão do método). Mesma entrada = mesma versão: reexecutar não duplica dados. Só uma versão por fonte fica vigente.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id_versao` | integer | não |  |
| `id_fonte` | text | não |  |
| `assinatura` | character(64) | não | sha256 que identifica o conjunto de entradas desta versão. |
| `descricao` | text | sim |  |
| `criado_em` | timestamp with time zone | não |  |
| `id_execucao` | bigint | sim |  |
| `vigente` | boolean | não | Verdadeiro para a versão exibida na camada bi. |

## Esquema `staging`

Camada de tratamento: dados tipados, com códigos normalizados e marcadores de ausência convertidos em status.

### `staging.censo_contagem` (tabela)

Todas as contagens QT_* do Censo Escolar por escola e ano, em formato longo (variável, valor). Célula vazia na origem fica nula, nunca zero.

Colunas: `ano`, `co_entidade`, `variavel`, `valor`, `id_arquivo`

### `staging.censo_dicionario` (tabela)

Dicionário de dados do INEP (ANEXO I do ZIP do Censo Escolar), por ano.

Colunas: `ano`, `variavel`, `descricao`, `tipo`, `categorias`, `id_arquivo`

### `staging.censo_escola` (tabela)

Cadastro e infraestrutura das escolas dos municípios de interesse, por ano do Censo Escolar (tipado). Coluna ausente no layout do ano fica nula.

Colunas: `ano`, `co_entidade`, `co_municipio`, `no_entidade`, `tp_dependencia`, `tp_categoria_escola_privada`, `tp_localizacao`, `tp_localizacao_diferenciada`, `tp_situacao_funcionamento`, `no_bairro`, `co_distrito`, `in_internet`, `in_banda_larga`, `in_biblioteca`, `in_biblioteca_sala_leitura`, `in_sala_leitura`, `in_laboratorio_ciencias`, `in_laboratorio_informatica`, `in_quadra_esportes`, `in_acessibilidade_inexistente`, `in_banheiro_pne`, `in_agua_potavel`, `in_energia_rede_publica`, `in_esgoto_rede_publica`, `in_sala_atendimento_especial`, `in_alimentacao`, `tp_aee`, `versao_layout`, `id_arquivo`

### `staging.censo_layout` (tabela)

Variáveis presentes no arquivo de cada ano: permite distinguir "variável não existe no layout" (sem_dado por quebra de série) de "valor vazio".

Colunas: `ano`, `versao_layout`, `variavel`, `tabela_origem`, `id_arquivo`

### `staging.ideb` (tabela)

Planilhas do Ideb convertidas de formato largo (anos em colunas) para longo, guardando a edição de onde cada valor veio.

Colunas: `edicao`, `nivel`, `cod_territorio`, `co_entidade`, `rede`, `cod_etapa`, `ano`, `medida`, `coluna_origem`, `valor`, `valor_texto`, `status_valor`, `id_arquivo`

### `staging.inep_indicador` (tabela)

Planilhas dos Indicadores Educacionais do INEP (rendimento, distorção, AFD, ATU, DSU) e tabelas da Sinopse, em formato longo. A etapa e a medida são identificadas pelo texto do cabeçalho.

Colunas: `id_fonte`, `ano`, `nivel`, `cod_territorio`, `co_entidade`, `localizacao`, `rede`, `coluna_origem`, `rotulo_origem`, `medida`, `cod_etapa`, `valor`, `valor_texto`, `status_valor`, `id_arquivo`

### `staging.populacao` (tabela)

População por idade simples e sexo. origem: ripsa_ftp, ripsa_tabnet ou ibge_censo2022. idade 80 = 80 anos ou mais (RIPSA). sexo: M, F ou T (total).

Colunas: `origem`, `edicao`, `ano`, `cod_territorio`, `sexo`, `idade`, `populacao`, `id_arquivo`

### `staging.siconfi` (tabela)

Itens das declarações fiscais do SICONFI (DCA e RREO) dos municípios de interesse.

Colunas: `demonstrativo`, `ano`, `periodo`, `cod_territorio`, `anexo`, `rotulo`, `coluna`, `cod_conta`, `conta`, `valor`, `id_arquivo`

### `staging.sidra` (tabela)

Valores das tabelas do SIDRA/IBGE. classificacao guarda as categorias da consulta (ex.: c287=6558 para a idade de 1 ano).

Colunas: `tabela`, `variavel`, `cod_territorio`, `ano`, `classificacao`, `valor`, `valor_texto`, `unidade`, `status_valor`, `id_arquivo`

### `staging.siope_dados_gerais` (tabela)

Totais declarados ao SIOPE (sem dados do responsável pela declaração).

Colunas: `ano`, `cod_territorio`, `populacao_declarada`, `desp_educacao_orcada`, `desp_educacao_empenhada`, `desp_educacao_liquidada`, `desp_educacao_paga`, `desp_total_liquidada`, `receita_realizada`, `data_declaracao`, `id_arquivo`

### `staging.siope_despesa_funcao` (tabela)

Despesas da função Educação por subfunção declaradas ao SIOPE.

Colunas: `ano`, `cod_territorio`, `num_orde`, `subfuncao`, `empenhada`, `liquidada`, `paga`, `id_arquivo`

### `staging.siope_indicador` (tabela)

Indicadores legais e de gasto declarados ao SIOPE (6º bimestre).

Colunas: `ano`, `cod_territorio`, `tipo`, `cod_indi`, `cod_exib`, `nom_indi`, `nom_grupo`, `valor`, `valor_texto`, `id_arquivo`

### `staging.siope_receita` (tabela)

Receitas declaradas ao SIOPE (rubrica, coluna e valor). A mesma rubrica pode aparecer mais de uma vez com NUM_ORDE igual, por isso a chave é a posição da linha na resposta da API (linha).

Colunas: `ano`, `cod_territorio`, `cod_rubrica`, `nom_item`, `idn_clas`, `coluna`, `num_nive`, `num_orde`, `linha`, `valor`, `id_arquivo`

## Esquema `raw`

Camada bruta: recorte dos arquivos das fontes exatamente como vieram (valores em texto), com vínculo ao arquivo de origem em etl.etl_arquivo.

### `raw.linha` (tabela)

Camada bruta: recorte (territórios de interesse) de cada arquivo, uma linha por registro de origem, todas as colunas em texto exatamente como vieram. O arquivo inteiro fica em disco em data/raw/<fonte>/<ano>/.

| Coluna | Tipo | Aceita nulo | Descrição |
|---|---|---|---|
| `id_arquivo` | bigint | não |  |
| `tabela_origem` | text | não | Tabela ou planilha de origem dentro do arquivo (ex.: microdados_ed_basica, Tabela_Matricula, municipios). |
| `num_linha` | integer | não | Número da linha no arquivo de origem (1 = primeira linha de dados). |
| `dados` | jsonb | não | Objeto {coluna: valor em texto} com a linha original. |
