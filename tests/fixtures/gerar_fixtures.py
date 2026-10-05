"""Gera as fixtures de planilhas do INEP (Indicadores Educacionais e Ideb) usadas nos testes.

As linhas de cabeçalho e de dados abaixo são RECORTES REAIS das planilhas publicadas pelo INEP,
lidas em 29/09/2026 diretamente dos arquivos oficiais (download.inep.gov.br), com as mesmas
células mescladas (texto só na primeira célula do grupo), a mesma linha de códigos e os mesmos
marcadores ("--", "-", "ND"). Só o número de linhas foi reduzido.

As planilhas são gravadas dentro de um ZIP com a mesma estrutura de pastas do INEP.
Rode este arquivo para regenerar as fixtures:  python tests/fixtures/gerar_fixtures.py
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from openpyxl import Workbook

AQUI = Path(__file__).parent

MEC = ["", "Ministério da Educação"]
INEP = ["", "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira"]


def _num(v: str):
    """Números vêm como número na planilha; marcadores ficam como texto."""
    if v in ("--", "-", "ND", ""):
        return v if v else None
    return float(v.replace(",", "."))


def _gravar_zip(destino: Path, pasta: str, nome_xlsx: str, linhas: list[list], numerico=True):
    wb = Workbook()
    ws = wb.active
    for linha in linhas:
        ws.append(linha)
    buf = io.BytesIO()
    wb.save(buf)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{pasta}/{nome_xlsx}", buf.getvalue())
        z.writestr(f"{pasta}/md5_{nome_xlsx}.txt", "fixture de teste\n")


def _dados(texto: str, n_id: int) -> list[list]:
    linhas = []
    for l in texto.strip().splitlines():
        partes = l.split(";")
        linhas.append(partes[:n_id] + [_num(p) for p in partes[n_id:]])
    return linhas


# ----------------------------------------------------------------- TDI 2024 (municípios)
TDI24_DADOS = """
2024;Nordeste;BA;2918407;Juazeiro;Total;Total;13,9;9,3;20,0;2,9;6,0;12,5;12,9;12,1;17,4;22,1;21,3;18,9;24,8;23,7;20,7;29,9;--
2024;Nordeste;BA;2918407;Juazeiro;Urbana;Total;14,8;10,4;20,5;3,4;6,8;14,3;14,3;12,8;17,8;22,5;21,4;20,5;21,4;20,0;16,2;27,7;--
2024;Nordeste;BA;2918407;Juazeiro;Rural;Total;11,2;5,9;18,2;1,6;3,5;6,7;8,7;9,5;16,5;21,1;21,2;14,1;42,7;41,6;43,6;43,0;--
2024;Nordeste;BA;2918407;Juazeiro;Total;Federal;--;--;--;--;--;--;--;--;--;--;--;--;20,9;11,3;13,6;44,8;--
2024;Nordeste;BA;2918407;Juazeiro;Total;Estadual;19,9;--;19,9;--;--;--;--;--;14,7;20,9;21,1;22,3;26,9;25,9;22,6;31,6;--
2024;Nordeste;BA;2918407;Juazeiro;Total;Municipal;14,4;10,1;23,1;3,4;7,0;13,4;13,2;13,2;21,0;26,0;25,2;20,2;--;--;--;--;--
2024;Nordeste;BA;2918407;Juazeiro;Rural;Municipal;11,3;5,9;18,2;1,7;3,5;6,4;8,6;9,6;16,5;21,1;21,2;14,1;--;--;--;--;--
2024;Nordeste;BA;2918407;Juazeiro;Total;Privada;6,4;5,9;7,5;0,8;1,9;8,4;11,4;6,8;7,5;9,5;7,2;5,3;4,5;4,0;5,6;3,8;--
2024;Nordeste;BA;2918407;Juazeiro;Total;Pública;15,4;10,1;21,9;3,4;7,0;13,4;13,2;13,2;18,9;24,1;23,5;21,1;26,6;25,4;22,1;32,1;--
"""
TDI24 = [
    MEC, INEP, [],
    ["Taxa de Distorção Idade-Série por Município - 2024"],
    ["Taxa de Distorção Idade-Série, por Dependência Administrativa e Localização, nos Níveis de Ensino Fundamental e Médio - Municípios - 2024"],
    ["Ano", "Região", "Sigla da UF", "Código do Município", "Nome do Município", "Localização", "Dependência Administrativa",
     "Ensino Fundamental"] + [None] * 11 + ["Ensino Médio"],
    [None] * 7 + ["Total", "Anos Iniciais", "Anos Finais", "1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano", "6º Ano",
                  "7º Ano", "8º Ano", "9º Ano", "Total", "1ª Série", "2ª Série", "3ª Série", "4ª Série"],
    [],
    ["NU_ANO_CENSO", "NO_REGIAO", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "NO_CATEGORIA", "NO_DEPENDENCIA", "FUN_CAT_0",
     "FUN_AI_CAT_0", "FUN_AF_CAT_0", "FUN_01_CAT_0", "FUN_02_CAT_0", "FUN_03_CAT_0", "FUN_04_CAT_0", "FUN_05_CAT_0",
     "FUN_06_CAT_0", "FUN_07_CAT_0", "FUN_08_CAT_0", "FUN_09_CAT_0", "MED_CAT_0", "MED_01_CAT_0", "MED_02_CAT_0",
     "MED_03_CAT_0", "MED_04_CAT_0"],
] + _dados(TDI24_DADOS, 7) + [[], ["Fonte: Censo da Educação Básica 2024/INEP."]]

# ----------------------------------------------------------------- TDI 2015 (municípios; layout antigo)
TDI15_DADOS = """
2015;Nordeste;29;BA;2918407;Juazeiro;Total;Total;27.6;21.7;35;5.4;17.2;25.5;30.6;27.7;38.9;37;33;29.2;40.799999999999997;43;39.700000000000003;39.5;24.7
2015;Nordeste;29;BA;2918407;Juazeiro;Total;Estadual;43;--;43;--;--;--;--;--;45.8;46.1;41.3;38.200000000000003;43.4;45.7;42.1;42.5;24.7
2015;Nordeste;29;BA;2918407;Juazeiro;Total;Municipal;27.9;25;34.799999999999997;6;19.5;29.6;34.700000000000003;32;40.700000000000003;37.200000000000003;31.4;24.5;--;--;--;--;--
2015;Nordeste;29;BA;2918407;Juazeiro;Rural;Privada;0;0;--;0;0;0;--;--;--;--;--;--;--;--;--;--;--
"""
TDI15 = [
    ["", "             Ministério da Educação"],
    ["", "                      Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira"],
    [],
    ["                                                                                                    Taxa de Distorção Idade-Série, por Município - 2015"],
    ["Taxa de Distorção Idade-Série, por Dependência Administrativa e Localização, nos Níveis de Ensino Fundamental de 8 e 9 anos e Médio, segundo a Região Geográfica, Unidades da Federação e seus respectivos Municípios em 2015. "],
    ["Ano", "Região", "Código da UF", "Sigla da UF", "Código do Município", " Município", "Localização", "Rede",
     "Ensino Fundamental de 8 e 9 anos"] + [None] * 11 + ["Ensino Médio"],
    [None] * 8 + ["Total", "Anos Iniciais", "Anos Finais", "1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano", "6º Ano",
                  "7º Ano", "8º Ano", "9º Ano", "Total", " 1ª Série", " 2ª Série", " 3ª Série", " 4ª Série"],
    [],
    ["NU_ANO_CENSO", "NO_REGIAO", "CO_UF", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "TIPOLOCA", "DEPENDAD", "TDI_FUN",
     "TDI_F14", "TDI_F58", "TDI_F00", "TDI_F01", "TDI_F02", "TDI_F03", "TDI_F04", "TDI_F05", "TDI_F06", "TDI_F07",
     "TDI_F08", "TDI_MED", "TDI_M01", "TDI_M02", "TDI_M03", "TDI_M04"],
] + [[p if i < 8 else _num(p) for i, p in enumerate(l.split(";"))] for l in TDI15_DADOS.strip().splitlines()]

# ----------------------------------------------------------------- Rendimento 2015 (sem linha de códigos)
REND15_DADOS = """
2015;Nordeste;BA;2918407;Juazeiro;Total;Total;84.8;89.8;78.7;98;86.4;85.5;88.1;92.8;74.8;76.400000000000006;82.4;83.1;78.8;71.2;80.599999999999994;87.2;92;--;13;9.4;17.399999999999999;1.1000000000000001;12.9;13.8;11.3;6.2;20.6;20.5;13.7;13.3;13.3;20;11.3;6.1;6.7;--;2.2000000000000002;0.8;3.9;0.9;0.7;0.7;0.6;1;4.5999999999999996;3.1;3.9;3.6;7.9;8.8000000000000007;8.1;6.7;1.3;--
2015;Nordeste;BA;2918407;Juazeiro;Total;Municipal;86.5;88.8;80.900000000000006;97.8;85.1;83.9;87.2;92.1;74.3;79;84.7;91.3;--;--;--;--;--;--;12.2;10.3;16.600000000000001;1.1000000000000001;14.2;15.3;12.1;6.7;22;19.8;12.5;7;--;--;--;--;--;--;1.3;0.9;2.5;1.1000000000000001;0.7;0.8;0.7;1.2;3.7;1.2;2.8;1.7;--;--;--;--;--;--
2015;Nordeste;BA;2918407;Juazeiro;Rural;Particular;100;100;--;100;100;100;--;--;--;--;--;--;--;--;--;--;--;--;0;0;--;0;0;0;--;--;--;--;--;--;--;--;--;--;--;--;0;0;--;0;0;0;--;--;--;--;--;--;--;--;--;--;--;--
"""
_R15 = ["Total {m} no Ens. Fundamental", "{M} - Anos Iniciais (1º ao 5º Ano)", "{M} - Anos Finais (6º ao 9º Ano)",
        "{M} no 1º Ano ", "{M} no 2º Ano", "{M} no 3º Ano", "{M} no 4º Ano", "{M} no 5º Ano", "{M} no 6º Ano",
        "{M} no 7º Ano", "{M} no 8º Ano", "{M} no 9º Ano", "Total {m} no Ens. Médio", "{M} na 1ª série",
        "{M} na 2ª série", "{M} na 3ª série", "{M} na 4ª série", "Total  {m} Médio Não-Seriado"]


def _rotulos_rend15():
    saida = []
    for m in ("Aprovação", "Reprovação", "Abandono"):
        for r in _R15:
            saida.append(r.format(m=m, M=m))
    return saida


REND15 = [
    ["", "", "Ministério da Educação"], ["", "", "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira"], [],
    ["                                                                                                     Taxas de Rendimento por município, em 2015"],
    ["Taxa de Aprovação - 2015"] + [None] * 24 + ["Taxa de Reprovação - 2015"] + [None] * 17 + ["Taxa de Abandono - 2015"],
    ["Taxa de Aprovação por Localização e a Dependência Administrativa, nos Níveis de Ensino Fundamental de 8 e 9 Anos e Médio, divididos por série, segundo as Unidades da Federação e seus respectivos municipios, em 2015. "],
    ["Ano", "Região", "UF", "Código do Município", "Nome do Município", "Localização", "Rede",
     "Taxa de Aprovação - Ensino Fundamental de 8 e 9 anos"] + [None] * 11 + ["Taxa de Aprovação - Ensino Médio"] + [None] * 5
    + ["Taxa de Reprovação - Ensino Fundamental de 8 e 9 anos"] + [None] * 11 + ["Taxa de Reprovação - Ensino Médio"] + [None] * 5
    + ["Taxa de Abandono - Ensino Fundamental de 8 e 9 anos"] + [None] * 11 + ["Taxa de Abandono - Ensino Médio"],
    [None] * 7 + _rotulos_rend15(),
    [], [],
] + [[p if i < 7 else _num(p) for i, p in enumerate(l.split(";"))] for l in REND15_DADOS.strip().splitlines()]

# ----------------------------------------------------------------- Rendimento 2024 (com códigos; Petrolina)
_ETAPAS24 = ["Total", "Anos Iniciais", "Anos Finais", "1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano", "6º Ano",
             "7º Ano", "8º Ano", "9º Ano", "Total", "1ª série", "2ª série", "3ª série", "4ª série", "Não-Seriado"]
_COD24 = ["FUN", "FUN_AI", "FUN_AF", "FUN_01", "FUN_02", "FUN_03", "FUN_04", "FUN_05", "FUN_06", "FUN_07", "FUN_08",
          "FUN_09", "MED", "MED_01", "MED_02", "MED_03", "MED_04", "MED_NS"]
REND24 = [
    MEC, INEP, [],
    ["Taxas de Rendimento Escolar por município - 2024"],
    ["Taxas de Rendimento Escolar (Aprovação, Reprovação e Abandono), segundo a Localização e a Dependência Administrativa, nos Níveis de Ensino Fundamental e Médio por série, segundo os municípios - 2024"],
    ["Ano", "Região", "UF", "Código do Município", "Nome do Município", "Localização", "Dependência Administrativa",
     "Taxa de Aprovação"] + [None] * 17 + ["Taxa de Reprovação"] + [None] * 17 + ["Taxa de Abandono"],
    [None] * 7 + (["Ensino Fundamental de 8 e 9 anos"] + [None] * 11 + ["Ensino Médio"] + [None] * 5) * 3,
    [None] * 7 + _ETAPAS24 * 3,
    ["NU_ANO_CENSO", "NO_REGIAO", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "NO_CATEGORIA", "NO_DEPENDENCIA"]
    + [f"{k}_CAT_{c}" for k in (1, 2, 3) for c in _COD24],
] + _dados("2024;Nordeste;PE;2611101;Petrolina;Total;Total;97,5;98,5;96,3;99,5;99,7;97,5;97,1;99,1;95,4;95,8;96,1;98,2;96,3;94,6;96,1;98,6;--;97,3;2,4;1,4;3,5;0,5;0,3;2,4;2,8;0,8;4,5;4,0;3,7;1,7;3,2;4,7;3,4;1,2;--;0,0;0,1;0,1;0,2;0,0;0,0;0,1;0,1;0,1;0,1;0,2;0,2;0,1;0,5;0,7;0,5;0,2;--;2,7", 7)

# ----------------------------------------------------------------- AFD 2015 (códigos antigos)
AFD15_DADOS = """
2015;Nordeste;BA;2918407;JUAZEIRO;Total;Total;36.5;1.6;8.9;5.6;47.4;40.799999999999997;2.1;24.2;5.4;27.5;40.9;3.6;16;1.3;38.200000000000003;40.6;0.4;33.9;10.1;15;26.1;0.1;29;15.5;29.3;29.4;0.6;45.2;12.4;12.4;35.5;0;38.9;18;7.6
2015;Nordeste;BA;2918407;JUAZEIRO;Total;Municipal;39.5;1.9;11;7.2;40.4;42;2.4;25;3.2;27.4;44.6;3.7;17;1.1000000000000001;33.6;37.6;0.3;38.700000000000003;6.7;16.7;--;--;--;--;--;30.1;0.5;48.4;10.1;10.9;--;--;--;--;--
"""
_G = ["Grupo 1", "Grupo 2", "Grupo 3", "Grupo 4", "Grupo 5"]
AFD15 = [
    ["", "                Ministério da Educação"], ["", "                     Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira"], [],
    ["                                                                   Percentual de docentes1,2 por grupo do indicador de adequação da formação do docente3 - Municípios - 2015"],
    ["Percentual de docentes1,2 na Educação Infantil (Creche e Pré-Escola), no Ensino Fundamental, no Ensino Médio e Educação de Jovens e Adultos por grupo4 de adequação da formação à disciplina que leciona, segundo localização e dependência administrativa - Municípios - 2015"],
    [],
    ["Ano", "Região", "Sigla", "Código do Município", "Nome do Município", "Localização", "Dependência Administrativa",
     "Percentual de docentes1,2 por grupo4 de adequação da formação à disciplina que leciona e etapa/modalidade de ensino"],
    [None] * 7 + ["Educação Infantil"] + [None] * 4 + ["Ensino Fundamental"] + [None] * 14 + ["Ensino Médio"] + [None] * 4 + ["EJA"],
    [None] * 12 + ["Total"] + [None] * 4 + ["Anos Iniciais"] + [None] * 4 + ["Anos Finais"] + [None] * 9 + ["Fundamental"] + [None] * 4 + ["Médio"],
    [None] * 7 + _G * 7,
    ["ano", "no_cod", "sigla", "pk_cod_municipio", "no_cod", "TIPOLOCA", "Dependad"]
    + [f"AFD_{e}{g}" for e in ("INF", "FUN", "F14", "F58", "MED", "EJAF", "EJAM") for g in range(1, 6)],
] + [[p if i < 7 else _num(p) for i, p in enumerate(l.split(";"))] for l in AFD15_DADOS.strip().splitlines()]

# ----------------------------------------------------------------- ATU e DSU 2024 (Petrolina)
ATU24 = [
    MEC, INEP, [],
    ["Média de Alunos por Turma - Municípios - 2024"],
    ["Média de Alunos por Turma da Educação Básica - (Creche, Pré-Escola), Ensino Fundamental e Ensino Médio, por Localização e Dependência Administrativa - Municípios - 2024."],
    ["Ano", "Região", "UF", "Código do Município", "Município", "Localização", "Dependência Administrativa", "Média de Alunos por Turma / Etapas de Ensino"],
    [None] * 7 + ["Educação Infantil", None, None, "Ensino Fundamental"] + [None] * 12 + ["Ensino Médio"],
    [None] * 7 + ["Total1", "Creche", "Pré-Escola", "Total", "Anos Iniciais", "Anos Finais", "1º Ano", "2° ano", "3° ano", "4° ano", "5° ano",
                  "6° ano", "7° ano", "8° ano", "9° ano", "Turmas Multietapa, Multi ou Correção de Fluxo2", "Total", "1ª série", "2ª série",
                  "3ª série", "4ª série", "Não-Seriado"],
    ["NU_ANO_CENSO", "NO_REGIAO", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "NO_CATEGORIA", "NO_DEPENDENCIA", "ED_INF_CAT_0", "CRE_CAT_0",
     "PRE_CAT_0", "FUN_CAT_0", "FUN_AI_CAT_0", "FUN_AF_CAT_0", "FUN_01_CAT_0", "FUN_02_CAT_0", "FUN_03_CAT_0", "FUN_04_CAT_0",
     "FUN_05_CAT_0", "FUN_06_CAT_0", "FUN_07_CAT_0", "FUN_08_CAT_0", "FUN_09_CAT_0", "MULT_ETA_CAT_0", "MED_CAT_0", "MED_01_CAT_0",
     "MED_02_CAT_0", "MED_03_CAT_0", "MED_04_CAT_0", "MED_NS_CAT_0"],
] + _dados("2024;Nordeste;PE;2611101;Petrolina;Total;Total;16,9;15,6;18,2;26,0;23,0;31,1;20,6;21,0;24,0;24,1;25,5;30,2;31,2;31,8;31,2;15,6;34,0;36,2;33,5;32,7;--;15,0", 7)

DSU24 = [
    MEC, INEP, [],
    ["Percentual de Funções Docentes com Curso Superior por município - 2024"],
    ["Percentual de Funções Docentes com Curso Superior na Educação Infantil (Creche e Pré-Escola), no Ensino Fundamental, no Ensino Médio, na Educação Profissional, na Educação de Jovens e Adultos, e na Educação Especial, por Localização e Dependência Administrativa - Municípios - 2024."],
    [],
    ["Ano", "Região", "UF", "Código do Município", "Nome do Município", "Localização", "Dependência Administrativa",
     "Percentual de Funções Docentes com curso superior por etapa/modalidade de ensino"],
    [None] * 7 + ["Educação Infantil", None, None, "Ensino Fundamental", None, None, "Ensino Médio", "Educação Profissional",
                  "Educação de Jovens e Adultos (EJA)", "Educação Especial"],
    [None] * 7 + ["Total", "Creche", "Pré-Escola", "Total", "Anos Iniciais", "Anos Finais"],
    ["NU_ANO_CENSO", "NO_REGIAO", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "NO_CATEGORIA", "NO_DEPENDENCIA", "ED_INF_CAT_0", "CRE_CAT_0",
     "PRE_CAT_0", "FUN_CAT_0", "FUN_AI_CAT_0", "FUN_AF_CAT_0", "MED_CAT_0", "PROF_CAT_0", "EJA_CAT_0", "EDU_BAS_CAT_0"],
] + _dados("2024;Nordeste;PE;2611101;Petrolina;Total;Total;83,2;82,7;83,4;92,3;88,1;95,3;97,6;74,5;99,2;90,5", 7)

# ----------------------------------------------------------------- Ideb 2025 - ensino médio (municípios)
# ordem real das colunas na planilha: aprovação e rendimento intercalados por ano
IDEB_EM_COD = (["SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "REDE"]
               + [c for a in (2017, 2019, 2021, 2023, 2025) for c in
                  [f"VL_APROVACAO_{a}_SI_4", f"VL_APROVACAO_{a}_1", f"VL_APROVACAO_{a}_2", f"VL_APROVACAO_{a}_3",
                   f"VL_APROVACAO_{a}_4", f"VL_INDICADOR_REND_{a}"]]
               + [c for a in (2017, 2019, 2021, 2023, 2025) for c in
                  [f"VL_NOTA_MATEMATICA_{a}", f"VL_NOTA_PORTUGUES_{a}", f"VL_NOTA_MEDIA_{a}"]]
               + [f"VL_OBSERVADO_{a}" for a in (2017, 2019, 2021, 2023, 2025)]
               + ["VL_PROJECAO_2019", "VL_PROJECAO_2021"])
IDEB_EM_DADOS = """
BA;2918407;Juazeiro;Estadual;81.3;73.3;82.3;89.8;90.8;0.83433599999999997;84.6;78.3;86.5;92.1;79.099999999999994;0.83625899999999997;91.9;93.2;92.9;92.5;84.4;0.90593999999999997;89.3;95;89.3;83.2;-;0.88905299999999998;94.5;94.6;95.4;94.5;-;0.94831600000000005;252.32;250.95;3.9900709999999999;258.48;260.64999999999998;4.2217969999999996;ND;ND;-;255.03;254.67;4.0838210000000004;257.86;258.07;4.1744669999999999;3.3;3.5;-;3.6;4;3.5;3.8
BA;2918407;Juazeiro;Federal;-;-;-;-;-;-;84.8;83.8;74.099999999999994;100;-;0.846777;-;-;-;-;-;-;-;-;-;-;-;-;93.1;90.6;96.6;91.9;-;0.92962999999999996;-;-;-;294.04000000000002;314.23;5.5233309999999998;-;-;-;-;-;-;ND;ND;-;-;4.7;-;-;-;-;4.9000000000000004
BA;2918407;Juazeiro;Pública;81.599999999999994;74.099999999999994;82.5;89.8;90.8;0.83742300000000003;84.6;78.400000000000006;86.2;92.3;79.099999999999994;0.836252;91.7;92.6;92.8;92.6;84.4;0.90451700000000002;89.3;94.6;89.2;83.5;-;0.88868800000000003;94.4;94.4;95.4;94.3;-;0.94697399999999998;252.32;250.95;3.9900709999999999;259.18;261.70999999999998;4.2474970000000001;ND;ND;-;255.03;254.67;4.0838210000000004;258.63;259.45;4.20594;3.3;3.6;-;3.6;4;3.6;3.8
"""


def _ideb_em():
    ser = ["Total", "1ª série", "2ª série", "3ª série", "4ª série", "Indicador de Rendimento (P)"]
    l7 = ["Sigla da UF", "Código do Município", "Nome do Município", "Rede"]
    for a in ("2017", "2019", "20211", "2023", "2025"):
        l7 += [f"Taxa de Aprovação - {a}"] + [None] * 5
    for a in ("2017", "2019", "20211", "2023", "2025"):
        l7 += [f"Nota SAEB - {a}", None, None]
    for a in ("2017", "2019", "20211", "2023", "2025"):
        l7 += [f"IDEB\n{a}\n(N x P)"]
    l7 += ["Metas do 1º ciclo do Ideb2,3"]
    l8 = [None] * 34 + ["Matemática", "Língua Portuguesa", "Nota Média Padronizada (N)"] * 5
    l9 = [None] * 4 + ser * 5 + [None] * 20 + ["2019", "2021"]
    dados = []
    for l in IDEB_EM_DADOS.strip().splitlines():
        p = l.split(";")
        dados.append(p[:4] + [_num(x) for x in p[4:]])
    return [MEC, INEP, [], ["Ensino Médio Regular"],
            ["Indicadores educacionais compostos por: Taxa de Aprovação, SAEB e IDEB nos anos de 2017, 2019, 20211, 2023 e 2025 e Metas do 1º ciclo do Ideb2,3. Os dados estão dimensionados por município e organizados por rede de ensino."],
            [], l7, l8, l9, IDEB_EM_COD] + dados


# ----------------------------------------------------------------- Censo Escolar: ZIP com o recorte real
# Dicionário: linhas reais do "dicionário_dados_educação_básica.xlsx" de 2024 (aba de escolas),
# só as variáveis decodificadas pelo pipeline.
DICIONARIO = [
    [None, "Alteração de nomenclatura ou metodologia de cálculo"], [None, "Variável nova"], [None, "Descontinuidade"],
    ["Dicionário de Variáveis - Tabela de Escolas"], [], [],
    ["N", "Nome da Variável", "Descrição da Variável", "Tipo", "Tam.(1)", "Categoria", 'Coleta por ano ("s"=sim;"n"=não ) '],
    [None] * 6 + ["07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24"],
    [],
    ["1", "NU_ANO_CENSO", "Ano do Censo", "Num", "4"],
    ["21", "TP_DEPENDENCIA", "Dependência Administrativa", "Num", "1", "1 - Federal\n2 - Estadual\n3 - Municipal\n4 - Privada"],
    ["23", "TP_LOCALIZACAO", "Localização", "Num", "1", "1 - Urbana\n2 - Rural"],
    ["32", "TP_SITUACAO_FUNCIONAMENTO", "Situação de funcionamento", "Num", "1",
     "1 - Em Atividade\n2 - Paralisada\n3 - Extinta (ano do Censo)\n4 - Extinta em Anos Anteriores"],
    ["326", "TP_AEE", "Atendimento Educacional Especializado (AEE)", "Num", "1", "0 - Não oferece\n1 - Não exclusivamente\n2 - Exclusivamente"],
    ["413", "QT_MAT_BAS_0_3", "Número de Matrículas da Educação Básica - Até 3 anos de idade", "Num", "8"],
]


def _dicionario_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "microdados_unidade_coleta"
    for linha in DICIONARIO:
        ws.append(linha)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def censo_zip(ano: int, destino: Path) -> Path:
    """Monta um ZIP no formato do INEP com o recorte real (tests/fixtures/censo_escolar/recorte_<ano>.csv)."""
    texto = (AQUI / "censo_escolar" / f"recorte_{ano}.csv").read_text(encoding="utf-8")
    pasta = f"microdados_censo_escolar_{ano}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{pasta}/dados/microdados_ed_basica_{ano}.csv", texto.encode("latin-1"))
        z.writestr(f"{pasta}/Anexos/ANEXO I - Dicionário de Dados/dicionário_dados_educação_básica.xlsx", _dicionario_xlsx())
        z.writestr(f"{pasta}/leia-me/Leia-me.pdf", b"%PDF-1.4 fixture")
    return destino


# ----------------------------------------------------------------- Sinopse Estatística 2024 (tabelas 1.1 e 2.4)
# Cabeçalhos e linhas reais de "Sinopse_Estatistica_da_Educação_Basica_2024.xlsx" (abas "Educação Básica 1.1"
# e "2.4"), lidos em 29/09/2026. Mantidas: Brasil, a região Norte, a UF Rondônia e os municípios de Juazeiro
# e Petrolina. As notas de rodapé foram encurtadas.


def _celulas(texto: str, largura: int) -> list:
    """'A=Brasil | E=47088922' -> lista posicional (A=0, B=1...). Números viram int."""
    linha = [None] * largura
    for parte in texto.split(" | "):
        col, _, valor = parte.partition("=")
        col = col.strip()
        idx = 0
        for ch in col:
            idx = idx * 26 + (ord(ch) - 64)
        valor = valor if valor.strip() else None
        if valor is not None and valor.strip().isdigit() and idx - 1 >= 4:
            valor = int(valor.strip())
        linha[idx - 1] = valor
    return linha


SIN11 = [
    "A=Voltar ao Sumário",
    "A=MATRÍCULAS",
    "A=Educação Básica ",
    "A=1.1 – Número de Matrículas da Educação Básica, por Etapa de Ensino, segundo a Região Geográfica, a Unidade da Federação e o Município - 2024",
    "A=",
    "A=Região Geográfica | B=Unidade da Federação | C=Município | D=Código do Município | E=                                         Número de Matrículas da Educação Básica",
    "E=Total1-4 | F=                                   Etapa de Ensino ",
    "F=Educação Infantil | I=Ensino Fundamental | L=Ensino Médio | P=Educação Profissional | X=Educação de Jovens e Adultos (EJA) | AA=Educação Especial",
    "P=Total10 | Q=Educação Profissional Técnica de Nível Médio | U=Educação Profissional - Formação Inicial Continuada (FIC)",
    "F=Total5 | G=Creche | H=Pré-Escola | I=Total6 | J=Anos Iniciais7 | K=Anos Finais8 | L=Total9 | M=Ensino Médio Propedêutico  | N=Ensino Médio Normal/Magistério | O=Curso Técnico Integrado (Ensino Médio Integrado) | Q=Total11 | R=Associada ao Ensino Médio12 | S=Curso Técnico Concomitante | T=Curso Técnico Subsequente | U=Total13 | V=Curso FIC Concomitante | W=Curso FIC Integrado na Modalidade EJA14 | X=Total15 | Y=Ensino Fundamental16 | Z=Ensino Médio17 | AA=Total18 | AB=Classes Comuns19 | AC=Classes Exclusivas20",
    "A=",
    "A=Brasil  | E=47088922 | F=9491894 | G=4187691 | H=5304203 | I=26002356 | J=14498233 | K=11504123 | L=7790396 | M=6767102 | N=37371 | O=985923 | P=2576293 | Q=2389454 | R=1082146 | S=313866 | T=993442 | U=186839 | V=105649 | W=81190 | X=2391319 | Y=1414929 | Z=976390 | AA=2076825 | AB=1923692 | AC=153133",
    "A=Norte  | E=4777569 | F=790488 | G=243882 | H=546606 | I=2822911 | J=1574107 | K=1248804 | L=788015 | M=742208 | N=408 | O=45399 | P=151587 | Q=145954 | R=48241 | S=22962 | T=74751 | U=5633 | V=3377 | W=2256 | X=275065 | Y=157698 | Z=117367 | AA=198915 | AB=192588 | AC=6327",
    "A=Norte  | B=Rondônia  | E=383849 | F=64262 | G=18023 | H=46239 | I=224303 | J=120307 | K=103996 | L=73187 | M=67613 | N=0 | O=5574 | P=11671 | Q=11583 | R=5869 | S=1281 | T=4433 | U=88 | V=88 | W=0 | X=16295 | Y=6967 | Z=9328 | AA=19021 | AB=18492 | AC=529",
    "A=Norte  | B=Rondônia  | C=Alta Floresta D'Oeste  | D=1100015 | E=5071 | F=884 | G=237 | H=647 | I=2980 | J=1548 | K=1432 | L=1005 | M=1005 | N=0 | O=0 | P=0 | Q=0 | R=0 | S=0 | T=0 | U=0 | V=0 | W=0 | X=202 | Y=85 | Z=117 | AA=190 | AB=190 | AC=0",
    "A=Nordeste  | B=Pernambuco  | C=Petrolina  | D=2611101 | E=106871 | F=23975 | G=11330 | H=12645 | I=60039 | J=32757 | K=27282 | L=16568 | M=14810 | N=0 | O=1758 | P=4350 | Q=4310 | R=1776 | S=1107 | T=1427 | U=40 | V=10 | W=30 | X=3745 | Y=1855 | Z=1890 | AA=4332 | AB=4125 | AC=207",
    "A=Nordeste  | B=Bahia  | C=Juazeiro  | D=2918407 | E=67679 | F=13365 | G=5462 | H=7903 | I=35799 | J=20263 | K=15536 | L=9602 | M=7961 | N=0 | O=1641 | P=6779 | Q=6779 | R=1647 | S=207 | T=4925 | U=0 | V=0 | W=0 | X=3781 | Y=1267 | Z=2514 | AA=2304 | AB=2103 | AC=201",
    "A=",
    "A=Fonte: INEP – Censo Escolar da Educação Básica 2024",
    "A=Notas:   1 - (notas de rodapé da tabela; texto encurtado na fixture)",
]

SIN24 = [
    "A=Voltar ao Sumário",
    "A=DOCENTES",
    "A=Educação Básica",
    "A=2.4 – Número de Docentes da Educação Básica, por Nível de Escolaridade e Formação Acadêmica, segundo a Região Geográfica, a Unidade da Federação e o Município - 2024",
    "A=",
    "A=Região Geográfica | B=Unidade da Federação | C=Município | D=Código do Município | E=Número de Docentes da Educação Básica",
    "E=Total1-8 | F=Nível de Escolaridade e Formação Acadêmica",
    "F=Ensino Fundamental  | G=Ensino Médio | H=Ensino Superior",
    "H=Graduação | K=Pós-Graduação",
    "H=Total9 | I=Com Licenciatura10 | J=Sem Licenciatura | K=Especialização | L=Mestrado | M=Doutorado",
    "A=",
    "A=Brasil  | E=2367777 | F=4731 | G=290580 | H=2072466 | I=2007378 | J=65088 | K=1045470 | L=92536 | M=26297",
    "A=Norte  | E=209520 | F=745 | G=26398 | H=182377 | I=177878 | J=4499 | K=78905 | L=6458 | M=1601",
    "A=Norte  | B=Rondônia  | E=15696 | F=17 | G=673 | H=15006 | I=14695 | J=311 | K=11372 | L=700 | M=141",
    "A=Norte  | B=Rondônia  | C=Alta Floresta D'Oeste  | D=1100015 | E=286 | F=0 | G=20 | H=266 | I=266 | J=0 | K=239 | L=11 | M=1",
    "A=Nordeste  | B=Pernambuco  | C=Petrolina  | D=2611101 | E=4497 | F=2 | G=438 | H=4057 | I=3946 | J=111 | K=2125 | L=206 | M=48",
    "A=Nordeste  | B=Bahia  | C=Juazeiro  | D=2918407 | E=2765 | F=3 | G=221 | H=2541 | I=2359 | J=182 | K=1638 | L=174 | M=31",
    "A=",
    "A=Fonte: INEP – Censo Escolar da Educação Básica 2024",
    "A=Notas:   1 - Docentes referem-se aos indivíduos que estavam em efetiva regência de classe na data de referência do Censo Escolar da Educação Básica.",
]


def sinopse_zip(destino: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sumário"
    ws.append(["Sinopse Estatística da Educação Básica 2024"])
    for nome, linhas, largura in (("Educação Básica 1.1", SIN11, 29), ("2.4", SIN24, 13)):
        aba = wb.create_sheet(nome)
        for l in linhas:
            celulas = _celulas(l, largura)
            while celulas and celulas[-1] is None:
                celulas.pop()
            aba.append(celulas)
    buf = io.BytesIO()
    wb.save(buf)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Sinopse_Estatistica_da_Educação_Basica_2024/Sinopse_Estatistica_da_Educação_Basica_2024.xlsx",
                   buf.getvalue())
    return destino


def main():
    base = AQUI / "inep_indicadores"
    _gravar_zip(base / "TDI_2024_MUNICIPIOS.zip", "TDI_2024_MUNICIPIOS", "TDI_MUNICIPIOS_2024.xlsx", TDI24)
    _gravar_zip(base / "tdi_municipios_2015.zip", "TDI_2015_MUNICIPIOS", "TDI_MUNICIPIOS_2015.xlsx", TDI15)
    _gravar_zip(base / "tx_rendimento_municipios_2015.zip", "TAXA_REND_2015_MUNICIPIOS", "TX_REND_MUN_2015.xlsx", REND15)
    _gravar_zip(base / "tx_rend_municipios_2024.zip", "tx_rend_municipios_2024", "tx_rend_municipios_2024.xlsx", REND24)
    _gravar_zip(base / "adequacao_formacao_docente_municipios_2015.zip", "AFD_2015_MUNICIPIOS", "AFD_MUNICIPIOS_2015.xlsx", AFD15)
    _gravar_zip(base / "ATU_2024_MUNICIPIOS.zip", "ATU_2024_MUNICIPIOS", "ATU_MUNICIPIOS_2024.xlsx", ATU24)
    _gravar_zip(base / "DSU_2024_MUNICIPIOS.zip", "DSU_2024_MUNICIPIOS", "DSU_MUNICIPIOS_2024.xlsx", DSU24)
    _gravar_zip(AQUI / "ideb" / "divulgacao_ensino_medio_municipios_2025.zip", "divulgacao_ensino_medio_municipios_2025",
                "divulgacao_ensino_medio_municipios_2025.xlsx", _ideb_em())
    sinopse_zip(AQUI / "sinopse" / "sinopse_estatistica_censo_escolar_2024.zip")
    for ano in (2019, 2022, 2024):
        censo_zip(ano, AQUI / "censo_escolar" / f"microdados_censo_escolar_{ano}.zip")
    print("Fixtures gravadas em", AQUI)


if __name__ == "__main__":
    main()
