# Decisões tomadas

Onde a tarefa ou os documentos de referência deixavam algo em aberto, a decisão foi tomada e registrada
aqui. Cada item diz o que foi decidido e por quê.

## Modelagem (divergências em relação ao modelo de referência)

1. **`dim_territorio` no lugar de `co_municipio`.** Município (7 dígitos), UF (2) e Brasil ("1", convenção
   do SIDRA) na mesma dimensão, com `eh_alvo` e `eh_comparacao`. Os comparadores ficam em `config/projeto.yaml`.
2. **`fato_indicador`** ganhou `cod_etapa` (os indicadores do INEP são por etapa), `referencia` e `nota`
   (procedência e cuidados de leitura), `eh_calculo_proprio` e o status `nao_se_aplica` (o INEP distingue "--",
   recorte sem a etapa, de dado ausente). Unicidade com `UNIQUE NULLS NOT DISTINCT` (PostgreSQL 15+),
   para o agregado territorial (`co_entidade` nulo) não duplicar. CHECK garante que `sem_dado` e
   `nao_se_aplica` não têm valor. `numerador`, `denominador` e `valor` em `NUMERIC(20,4)`, porque despesas em
   R$ passam do limite de `NUMERIC(14,2)`.
3. **`co_entidade` como `CHAR(8)`** (texto), coerente com a regra de chaves naturais.
4. **Recorte com código canônico** (`rede:municipal|localizacao:rural|raca_cor:parda`) em `dim_recorte`, com
   as colunas decompostas (rede, localização, terceiro eixo). Permite cruzar rede × localização × um terceiro
   eixo sem multiplicar dimensões no Power BI.
5. **`fato_rendimento` em formato longo** (uma linha por medida: aprovação, reprovação, abandono, distorção),
   porque as quatro vêm de arquivos e anos de publicação diferentes.
6. **`fato_avaliacao` guarda a edição** da divulgação do Ideb de onde cada valor foi lido (o INEP revisa
   números antigos); a camada bi marca a edição mais recente.
7. **`fato_docente` aceita escola ou município**: o número por escola (Censo) conta duas vezes quem dá aula
   em duas escolas; o municipal da Sinopse conta o docente uma vez. Os dois convivem, identificados pela fonte.
8. **`fato_populacao`** (não estava na referência): população por idade simples, origem (RIPSA via FTP ou
   TabNet, Censo 2022) e edição da estimativa. É o denominador das taxas de atendimento.
9. **`dim_escola` como SCD tipo 2** reconstruída a cada carga a partir do staging (ilhas de atributos iguais
   por ano), com `valid_from`/`valid_to`/`eh_vigente`. Latitude/longitude ficam reservadas (não são
   publicadas nos microdados).
10. **Camada raw genérica**: `raw.linha` guarda, por arquivo, só as linhas dos territórios de interesse
    com todas as colunas em texto (jsonb). O arquivo inteiro fica em `data/raw/` e o manifesto (URL + sha256)
    permite baixar e conferir de novo. Guardar microdados do Brasil inteiro no banco não traria ganho.
11. **Versionamento por assinatura**: `etl.versao_dados` identifica a versão pelo sha256 do conjunto
    (ano, URL, sha256 dos arquivos) + versão do código de transformação. Mesma entrada = mesma versão:
    reexecutar não cria versão nem duplica linha. Só uma versão vigente por fonte; o bi mostra a vigente e o
    core guarda o histórico. Os indicadores são uma "fonte" derivada (`calculo_observatorio`), cuja
    assinatura inclui as versões vigentes de todas as fontes, a versão do método e o hash dos SQL de cálculo.
12. **Indicadores em SQL legível** (`sql/indicadores/`), gravando numa tabela temporária; um passo único
    completa fonte, flag de cálculo próprio e versão e aplica a regra "valor nulo ⇒ sem_dado". Duplicata numa
    definição faz o cálculo falhar em vez de gravar algo ambíguo.
13. **Views de apoio no core** (`core.v_fato_*` só com a versão vigente, `core.v_escola_ano`,
    `core.v_escola_recorte`, `core.v_contagem_escola`) para o cálculo e os testes.
14. **Camada bi recriada a cada `db migrar`** (DROP/CREATE do esquema bi + GRANT), para as views nunca
    ficarem fora de sincronia com o core. O papel `powerbi_leitor` recebe só USAGE/SELECT no bi e tem
    revogado tudo nos outros esquemas; o nome do papel é fixo (só a senha vem do `.env`).
15. **SQLAlchemy não foi usado**: psycopg 3 com SQL explícito e `COPY` para carga em lote é mais simples de
    ler e mais rápido para este volume.

## Tratamento dos dados

16. **Identificação de colunas das planilhas do INEP pelo texto do cabeçalho**, com o código de variável
    prevalecendo quando existe e segue o padrão conhecido. Divergência rótulo × código vira alerta de
    qualidade (caso real: DSU 2024, `EDU_BAS_CAT_0` rotulada "Educação Especial").
17. **Marcadores** (config/regras_ausencia.yaml): no INEP, `--` = não se aplica; `-`, `*`, `ND`, `...`, `x` =
    sem dado. No IBGE, `-` é zero absoluto **por definição do IBGE** (vira 0 observado; é o único caso de zero
    vindo de marcador). Célula vazia = sem dado. Nada disso está no código: muda-se no YAML.
18. **Censo 2022 com `QT_MAT_BAS` vazio em 53 escolas**: vazio fica nulo (sem_dado) na escola; as somas
    municipais ignoram as células vazias (a soma é das escolas que informaram).
19. **Somas municipais só com escolas em atividade** (TP_SITUACAO_FUNCIONAMENTO = 1) para D1–D7 e E5; A6
    soma todas as escolas presentes no arquivo (paralisadas e extintas não têm matrícula).
20. **Taxas de atendimento (A1–A4)**: numerador = `QT_MAT_BAS_<faixa>` (todas as redes, escolas do
    município, idade na data de referência do Censo); denominador = população RIPSA/DATASUS por idade simples
    (estimativa oficial do Ministério da Saúde, com idade simples, que o IBGE não publica por município fora
    do Censo). Status `estimado`; a edição da estimativa vai em `referencia`. Não se limita a 100%: acima disso
    há alerta (fluxo diário Juazeiro–Petrolina; o Censo conta a matrícula no município da escola). A soma só
    existe se todas as variáveis e idades da faixa existem no ano.
21. **População só total por idade (sexo T)**: o coletor soma os dois sexos, porque a codificação de sexo do
    DBF do FTP não pôde ser verificada e nenhum indicador desta etapa usa sexo.
22. **FTP do DATASUS com fallback no TabNet**: o FTP é tentado primeiro (arquivos anuais), validando as
    colunas do DBF; se falhar, o formulário público do TabNet é consultado (verificado). O formulário é
    lido da própria página para montar o POST.
23. **E3 (docentes com pós-graduação)** vem da Sinopse (docente único). Como as categorias de pós não são
    exclusivas, o valor é a soma limitada ao total de graduados: um **limite superior**, com status `estimado`
    e nota explicativa. Em 2025, os microdados trazem `QT_DOC_BAS_ESCO_SUP_POS_NENHUM` por escola, mas somar
    escolas conta docente repetido, por isso não foi usado para E3.
24. **F1 conferido pela DCA, não pelo RREO**: o RREO Anexo 08 não consta no SICONFI para Juazeiro; a
    conferência cruzada compara a despesa liquidada em educação do SIOPE com a função 12 da DCA Anexo I-E.
25. **F2 (cálculo próprio)**: despesa liquidada em educação declarada ao SIOPE (Dados Gerais) ÷ matrículas
    da rede municipal (Censo do mesmo ano). Mantido ao lado do indicador oficial 4.8 do SIOPE (F2.siope).
26. **F4 (Fundeb)**: soma de rubricas por lista de códigos verificada por período (`config/siope.yaml`);
    ano sem códigos verificados fica `sem_dado`, em vez de adivinhar a rubrica.
27. **F3**: DCA Anexo I-E, coluna "Despesas Liquidadas", função 12 (recorte total) e subfunções 12.xxx
    (recorte `subfuncao:12.xxx`, rotulado com o nome da conta).
28. **D3 (infraestrutura)**: média de cinco itens binários (internet; biblioteca ou sala de leitura;
    laboratório de ciências ou informática; quadra; alguma acessibilidade), 0 a 100 por escola; escola sem
    algum item informado fica sem valor; município = média das escolas com valor.
29. **D1/D2/D5.sala de recursos** só para redes públicas (recortes `rede:publica` e cada rede pública).
30. **Sinopse**: tabelas localizadas pelo título, não pelo número (a numeração muda em 2025). Das matrículas
    por etapa, só o total de cada etapa vira medida principal; subitens (ex.: "Ensino Médio Normal") ficam
    como detalhe no staging.
31. **SIOPE Receita**: a mesma rubrica aparece mais de uma vez com o mesmo `NUM_ORDE`, por isso a chave do
    staging é a posição da linha na resposta.
32. **Arquivos grandes**: o ZIP do Censo pode ser apagado após o processamento (`OBS_MANTER_ZIP_BRUTO=false`);
    o manifesto guarda URL e sha256 para baixar e conferir depois. Padrão: manter.
33. **Coleta que a automação não alcança**: comando `importar`, que registra no manifesto um arquivo baixado
    à mão (mesmo tratamento, mesma rastreabilidade).
34. **Arquivo de API**: respostas JSON são gravadas como vieram (SICONFI: páginas juntadas num JSON com as
    chaves ordenadas), para que o sha256 identifique mudança de conteúdo.

## Processo

35. **Desenvolvimento sem acesso direto às fontes**: o ambiente de desenvolvimento não alcança os sites do
    governo (bloqueio de rede do ambiente). Os formatos foram verificados abrindo os arquivos e APIs reais pelo
    navegador do computador do bolsista, e as fixtures de teste são recortes reais desses arquivos
    (`tests/fixtures/gerar_fixtures.py` documenta a origem). O pipeline completo contra a internet precisa ser
    rodado no computador do Observatório (ver README e `docs/pendencias.md`).
36. **Certificados HTTPS pelo sistema operacional (`truststore`)**: `download.inep.gov.br` não envia o
    certificado intermediário da cadeia. O navegador completa a cadeia sozinho; o pacote de certificados
    padrão do Python não, e o download falhava com `SSLError` no Windows. O projeto usa o repositório de
    certificados do sistema (o mesmo do navegador). A verificação continua ligada: desligá-la não é opção.
37. **Só Juazeiro (29/09/2026, pedido do bolsista)**: Petrolina saiu da comparação
    (`municipios_comparacao: []` em `config/projeto.yaml`). Escolas e indicadores municipais são só de
    Juazeiro; Bahia e Brasil continuam como referência quando a própria fonte já traz esses totais
    (ex.: Indicadores Educacionais, Ideb, Sinopse). Para voltar a comparar, basta recolocar o código do
    município na lista e rodar o pipeline.
38. **Ajustes após a primeira carga real (29/09/2026)**, conferidos nos arquivos baixados:
    - planilhas do INEP com colunas vazias formatadas à direita (2019+) não geram mais colunas-fantasma;
    - ZIPs de Brasil/UFs de 2015–2016 com três planilhas (Brasil, regiões, UFs): todas são lidas; a
      coluna "Abrangência" e a UF por extenso ("Bahia") são reconhecidas;
    - códigos de variável trocados pelo INEP em 2016–2017 (ex.: `NO_MUNICIPIO` sob "Código do Município",
      `TIPOLOCA` sob "Dependência Administrativa"): o texto do cabeçalho passou a valer mais que o código
      para as colunas de identificação;
    - Ideb: os arquivos ficam numa aba carregada à parte (`resultados/2005-2025`), lida pelo coletor;
    - Sinopse: o "Sumário" lista os títulos de todas as tabelas; só vale a aba que tem a tabela;
    - Sinopse 2025 traz o total de docentes com pós-graduação (docente único): E3 passa a ser observado
      nesse ano; até 2024 continua limite superior (estimado);
    - Windows: arquivos temporários só são apagados depois de fechados.
    Conferência: Sinopse 1.1 de Juazeiro = soma dos microdados em 2015 (60 692) e 2020 (69 010).
39. **Ideb: série da taxa de aprovação pelo rótulo, não pelo código.** Na edição 2025, os códigos das
    colunas de aprovação estão deslocados nos anos iniciais (`VL_APROVACAO_2005_SI` = "1º",
    `VL_APROVACAO_2005_1` = "2º"...) e nos anos finais `_1.._4` significam 6º a 9º ano. O coletor usa o
    rótulo do cabeçalho ("1º ao 5º ano", "3º", "2ª série"). O arquivo de UFs não tem código nas colunas
    de território e rede: elas são reconhecidas pelo rótulo. Um código repetido na linha de códigos
    (`VL_INDICADOR_REND_2023` duas vezes no arquivo de UFs) fica só com a primeira ocorrência.
