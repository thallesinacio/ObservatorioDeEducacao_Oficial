"""Leitura das planilhas e respostas reais (recortes guardados em tests/fixtures), sem banco e sem rede."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from observatorio.coleta import ideb, populacao_datasus, siconfi, sidra, sinopse, siope
from observatorio.coleta.inep_indicadores import classificar_link, ler_planilha_inep
from observatorio.transformacao import cabecalho as cb
from observatorio.transformacao.leitores import extrair_membro, ler_xlsx, listar_membros, membro_zip

MUNIS = {"2918407", "2611101"}
UFS = {"brasil": "1", "bahia": "29", "ba": "29"}


def _xlsx(zip_path: Path, tmp_path: Path) -> Path:
    return extrair_membro(zip_path, membro_zip(zip_path, r"\.xlsx$"), tmp_path / "p.xlsx")


def _valores(fixtures, tmp_path, arquivo, medida_fn):
    cols, linhas = ler_planilha_inep(_xlsx(fixtures / "inep_indicadores" / arquivo, tmp_path), MUNIS, UFS)
    saida = {}
    for ln in linhas:
        for c, v in ln.valores:
            etapa = cb.identificar_etapa(c).etapa
            saida[(ln.cod_territorio, ln.rede, ln.localizacao, medida_fn(c), etapa)] = v
    return saida


def test_rendimento_2015_sem_linha_de_codigos(fixtures, tmp_path):
    v = _valores(fixtures, tmp_path, "tx_rendimento_municipios_2015.zip", lambda c: cb.classificar_medida_rendimento(c.rotulo))
    assert float(v[("2918407", "total", "total", "aprovacao", "fund")]) == pytest.approx(84.8)
    assert float(v[("2918407", "total", "total", "abandono", "med")]) == pytest.approx(7.9)
    assert float(v[("2918407", "total", "total", "reprovacao", "fund_ai")]) == pytest.approx(9.4)


def test_distorcao_2024_com_marcador(fixtures, tmp_path):
    v = _valores(fixtures, tmp_path, "TDI_2024_MUNICIPIOS.zip", lambda c: "tdi")
    assert float(v[("2918407", "total", "total", "tdi", "fund")]) == pytest.approx(13.9)
    assert float(v[("2918407", "total", "total", "tdi", "med")]) == pytest.approx(24.8)
    # Rede federal não tem ensino fundamental em Juazeiro: marcador "--", nunca zero.
    assert v[("2918407", "federal", "total", "tdi", "fund")] == "--"


def test_afd_grupo_pela_ultima_linha_do_cabecalho(fixtures, tmp_path):
    v = _valores(fixtures, tmp_path, "adequacao_formacao_docente_municipios_2015.zip", cb.grupo_afd_da_coluna)
    assert float(v[("2918407", "total", "total", "1", "fund")]) == pytest.approx(40.8)
    assert float(v[("2918407", "total", "total", "5", "med")]) == pytest.approx(29.3)


def test_dsu_2024_rotulo_divergente_do_codigo(fixtures, tmp_path):
    cols, _ = ler_planilha_inep(_xlsx(fixtures / "inep_indicadores" / "DSU_2024_MUNICIPIOS.zip", tmp_path), MUNIS, UFS)
    col = next(c for c in cols if c.codigo == "EDU_BAS_CAT_0")
    e = cb.identificar_etapa(col)
    assert e.divergente and e.etapa == "bas" and e.pelo_rotulo == "esp"


def test_classificar_links_do_inep():
    assert classificar_link("https://download.inep.gov.br/x/TAXA_REND_2016_MUNICIPIOS.zip") == "municipio"
    assert classificar_link("https://download.inep.gov.br/x/tx_rend_escolas_2019.zip") == "escola"
    assert classificar_link("https://download.inep.gov.br/x/tx_rend_brasil_regioes_ufs_2025.zip") == "uf"


def test_ideb_formato_largo_para_longo(fixtures, tmp_path):
    x = _xlsx(fixtures / "ideb" / "divulgacao_ensino_medio_municipios_2025.zip", tmp_path)
    brutas, valores, avisos = ideb.ler_planilha_ideb(ler_xlsx(x), "med", MUNIS, UFS, "teste")
    assert brutas and not avisos
    d = {(v.rede, v.medida, v.ano, v.cod_etapa): v.bruto for v in valores if v.cod_territorio == "2918407"}
    assert d[("estadual", "ideb", 2023, "med")] == "3.6"
    assert d[("estadual", "ideb", 2021, "med")] == "-"       # vira sem_dado, não zero
    assert d[("estadual", "meta_ideb", 2021, "med")] == "3.8"
    assert ("estadual", "aprovacao", 2017, "med_serie_1") in d


def test_ideb_links_da_pagina():
    html = ('<a href="https://download.inep.gov.br/ideb/resultados/divulgacao_anos_iniciais_municipios_2025.zip">x</a>'
            '<a href="https://download.inep.gov.br/ideb/resultados/divulgacao_brasil_ideb_2025.zip">y</a>')
    links = ideb.descobrir_links(html)
    assert links[0]["etapa"] == "fund_ai" and links[0]["nivel"] == "municipio"
    assert links[1]["nivel"] == "brasil" and links[1]["edicao"] == 2025


def test_sinopse_tabelas_pelo_titulo(fixtures, tmp_path):
    z = fixtures / "sinopse" / "sinopse_estatistica_censo_escolar_2024.zip"
    nome, info = listar_membros(z)[0]
    x = extrair_membro(z, info, tmp_path / "s.xlsx")
    tabelas = {t.chave: t for t in sinopse.localizar_tabelas(x)}
    assert tabelas["matriculas_etapa"].numero == "1.1" and tabelas["docentes_escolaridade"].numero == "2.4"
    cols, _, linhas = sinopse.ler_tabela(x, tabelas["docentes_escolaridade"], MUNIS, UFS)
    juazeiro = next(v for n, t, v in linhas if t == "2918407")
    por_esc = {sinopse.escolaridade_docente(c): valor for c, valor in juazeiro}
    assert por_esc["total"] == "2765" and por_esc["especializacao"] == "1638" and por_esc["doutorado"] == "31"
    cols, _, linhas = sinopse.ler_tabela(x, tabelas["matriculas_etapa"], MUNIS, UFS)
    juazeiro = next(v for n, t, v in linhas if t == "2918407")
    principais = {sinopse.etapa_matricula(c)[0]: valor for c, valor in juazeiro if sinopse.etapa_matricula(c)[1]}
    assert principais["bas"] == "67679" and principais["fund_ai"] == "20263" and principais["esp"] == "2304"
    assert {n for n, _, _ in linhas} == {"brasil", "municipio"}


def test_tabnet_resposta(fixtures):
    texto = (fixtures / "api" / "tabnet_popsvs_juazeiro_2023_2025.html").read_bytes().decode("latin-1")
    titulo, por_ano, totais = populacao_datasus.interpretar_tabnet(texto)
    assert populacao_datasus.edicao_do_titulo(titulo) == "RIPSA 2000-2025"
    assert por_ano[2024][0] == 3784 and por_ano[2024][80] == 3939
    assert totais[2024] == 254481


def test_tabnet_formulario(fixtures):
    html = (fixtures / "api" / "tabnet_popsvs_def.html").read_bytes().decode("latin-1")
    acao, corpo = populacao_datasus.montar_consulta_tabnet(
        html, "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?ibge/cnv/popsvs2024br.def", "291840", [2023, 2024])
    assert acao.endswith("tabcgi.exe?ibge/cnv/popsvs2024br.def")
    assert b"SMunic%EDpio=2061" in corpo and b"Arquivos=pop24.dbf" in corpo and b"Linha=Idade_simples" in corpo


def test_sidra_censo_por_idade(fixtures):
    dados = json.loads((fixtures / "api" / "sidra_9514_2918407.json").read_text(encoding="utf-8"))
    regs = sidra.interpretar_resposta(dados)
    assert {r["ano"] for r in regs} == {2022}
    idades = {sidra.idade_do_rotulo(r["classificacao"].split("Idade=")[1].split(";")[0].split(":", 1)[1]) for r in regs}
    assert {0, 1, 2} <= idades
    assert sidra.idade_do_rotulo("100 anos ou mais") == 100 and sidra.idade_do_rotulo("0 a 4 anos") is None


def test_siope_url_e_fundeb():
    url = siope.montar_url("Receita_Siope", 2023, "BA", ["291840"])
    assert "@Sig_UF='BA'" in url and "COD_MUNI%20eq%20291840" in url
    assert siope.fundeb_do_ano(2022)["codigos"] == ["17580100", "17180900"]
    assert siope.fundeb_do_ano(2016) is None


def test_siconfi_conta():
    assert siconfi.codigo_da_conta("12.361 - Ensino Fundamental") == "12.361"
    assert siconfi.codigo_da_conta("12 - Educação") == "12"


def test_decimal_siope():
    assert siope.decimal_ou_none("1133599092.86") == Decimal("1133599092.86")
    assert siope.decimal_ou_none("") is None


def test_ideb_serie_pelo_rotulo():
    # Nos anos iniciais o INEP desloca os códigos (VL_APROVACAO_2005_SI = "1º"); vale o rótulo.
    assert ideb.etapa_da_aprovacao("fund_ai", "1º ao 5º ano", "SI_4") == "fund_ai"
    assert ideb.etapa_da_aprovacao("fund_ai", "1º", "SI") == "fund_ano_1"
    assert ideb.etapa_da_aprovacao("fund_af", "6º", "1") == "fund_ano_6"
    assert ideb.etapa_da_aprovacao("med", "2ª série", "2") == "med_serie_2"
    assert ideb.etapa_da_aprovacao("med", "Indicador de Rendimento (P)", None) is None
