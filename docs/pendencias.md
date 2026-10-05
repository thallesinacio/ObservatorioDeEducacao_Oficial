# Pendências

O que não foi feito, ou não pôde ser verificado, e por quê. Cada item diz o que falta para resolver.

## Execução

| # | Pendência | Motivo | Como resolver |
|---|---|---|---|
| 1 | **Primeira carga completa (2015–2025) não foi executada** | O ambiente onde o código foi escrito não acessa os sites do governo. Os coletores foram escritos sobre formatos verificados nos arquivos reais e o pipeline foi testado de ponta a ponta com recortes reais (fixtures) num PostgreSQL 16, mas o download real precisa rodar no computador do Observatório. | Seguir o README: `db migrar` e `pipeline --de 2015`. Conferir os totais de matrícula de Juazeiro com a tabela em `docs/fontes.md` e o `relatorio cobertura`. |
| 2 | FTP do DATASUS (`POPSBR<aa>.zip`) não verificado | Não foi possível listar o FTP. Nomes e colunas do DBF vêm de documentação de terceiros. | O coletor tenta o FTP e, se o formato não bater, usa o TabNet (verificado). Se o FTP funcionar, conferir em `bi.fato_populacao` que o total de Juazeiro 2024 é 254 481. |
| 3 | Página do TabNet fixa na edição "popsvs2024br" | É a edição vigente em 29/09/2026 (2000–2025). Quando o Ministério publicar outra, o endereço muda. | Atualizar `pagina_oficial` de `populacao_datasus` em `config/fontes.yaml`. A nova edição gera nova versão dos dados. |
| 4 | Layout de 2025 do Censo testado só na configuração | A fixture de 2025 (tabelas separadas, ZIP de 537 MB) não foi montada; os nomes de tabelas e colunas foram conferidos no arquivo real. | Após a primeira carga, conferir `bi.fato_matricula` de 2025 contra a Sinopse 2025 (o teste `conferencia_censo_sinopse` faz isso). |
| 5 | Planilhas do Ideb de UF/Brasil e por escola sem fixture | Só o arquivo de municípios do ensino médio foi recortado. O leitor usa a linha de códigos `VL_*`, igual nos três níveis. | Rodar `pytest -m rede` e conferir `bi.fato_avaliacao` depois da carga. |

## Indicadores sem valor nesta etapa

| Indicador | Situação | Motivo |
|---|---|---|
| A5 – taxa líquida no ensino médio | pendente | Os microdados públicos trazem matrículas por faixa etária (todas as etapas) ou por etapa (todas as idades), não o cruzamento idade × etapa. Sem microdado de aluno não há numerador. Alternativa futura: dado da SEDUC ou do IBGE (PNAD não tem recorte municipal). |
| B3 – conclusão do fundamental aos 16 anos | manual (etapa futura) | IBGE sem recorte municipal anual. |
| B4 – abandono e infrequência por escola | manual (etapa futura) | Depende do SIEJ / Busca Ativa (SEDUC). |
| C3 – % em nível adequado no Saeb | pendente (P2) | Níveis de proficiência exigem os resultados/microdados do Saeb (fonte P2, não implementada). As médias do Saeb já entram pelo Ideb (C2). |
| C4 – Indicador Criança Alfabetizada | pendente (P2) | Fonte P2 (ICA/INEP) não implementada nesta etapa. |
| C5 – avaliações diagnósticas | manual (etapa futura) | Dado da SEDUC. |
| E4 – formação continuada | manual (etapa futura) | Registros da SEDUC. |
| E6 – remuneração frente ao piso | manual (etapa futura) | A folha é dado pessoal; o SIOPE traz remuneração por profissional (com nome), que não é coletada. Precisa vir agregada pela SEDUC. |
| F5 – instrumentos de gestão | manual (etapa futura) | Legislação municipal (SAPL). |
| G4 – ensino superior na região | pendente (P2) | Censo da Educação Superior e CAPES não implementados. |

Estes indicadores já estão cadastrados em `core.dim_indicador` (com a cobertura marcada) e aparecem na
matriz de cobertura como "P" (pendente) ou "M" (manual), nunca como zero.

## Limitações conhecidas dos valores

- **E3** é limite superior (categorias de pós-graduação não exclusivas na Sinopse).
- **F4** só tem valor nos anos com códigos de rubrica do Fundeb verificados (2017–2024); anos novos ficam
  sem dado até alguém conferir os códigos e acrescentar em `config/siope.yaml`.
- **SIOPE 2015 e 2016**: o serviço OData não devolve dados; F1, F2, F2.siope e F4 começam em 2017.
- **RREO Anexo 08** não consta no SICONFI para Juazeiro; a conferência de F1 usa a DCA (despesa liquidada
  em educação), não o percentual de MDE.
- **A1–A4** usam população estimada e matrícula no município da escola; acima de 100% gera alerta.
- **G3 per capita** fica sem dado em 2022 e 2023 (o IBGE não publicou estimativa nesses anos).
- **E5.alunos_por_docente** soma docentes por escola (subestima a razão). O ATU oficial (E5.alunos_por_turma) é a referência.

## Fontes P2/P3 não implementadas

ICA, Saeb (níveis), Censo da Educação Superior, CAPES, portais de transparência / Tesouro Transparente e
dados internos da SEDUC (planilha padronizada). Estão no catálogo (`config/fontes.yaml`) para a próxima etapa.
