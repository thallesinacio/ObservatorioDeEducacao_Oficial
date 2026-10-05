"""Registra as fixtures (recortes reais dos arquivos oficiais) no manifesto, como se tivessem sido
coletadas, para rodar a transformação e o cálculo sem acesso à internet.

Uso direto (banco configurado no .env):  python tests/carga_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

FIX = Path(__file__).parent / "fixtures"
INEP = "https://download.inep.gov.br"
IND = f"{INEP}/informacoes_estatisticas/indicadores_educacionais"
SIOPE = ("https://www.fnde.gov.br/olinda-ide/servico/DADOS_ABERTOS_SIOPE/versao/v1/odata/{r}(Ano_Consulta=@Ano_Consulta,"
         "Num_Peri=@Num_Peri,Sig_UF=@Sig_UF)?@Ano_Consulta=2023&@Num_Peri=6&@Sig_UF='BA'&$format=json&"
         "$filter=COD_MUNI%20eq%20291840")
SIDRA = "https://apisidra.ibge.gov.br/values/t/{t}/n6/2918407/{c}"

# (fonte, arquivo, ano, url oficial de origem, descrição exigida pelo coletor)
ARQUIVOS = [
    ("censo_escolar", "censo_escolar/microdados_censo_escolar_2019.zip", 2019,
     f"{INEP}/dados_abertos/microdados_censo_escolar_2019.zip", None),
    ("censo_escolar", "censo_escolar/microdados_censo_escolar_2022.zip", 2022,
     f"{INEP}/dados_abertos/microdados_censo_escolar_2022.zip", None),
    ("censo_escolar", "censo_escolar/microdados_censo_escolar_2024.zip", 2024,
     f"{INEP}/dados_abertos/microdados_censo_escolar_2024.zip", None),
    ("inep_rendimento", "inep_indicadores/tx_rendimento_municipios_2015.zip", 2015,
     f"{IND}/2015/tx_rendimento_municipios_2015.zip", "nivel=municipio"),
    ("inep_rendimento", "inep_indicadores/tx_rend_municipios_2024.zip", 2024,
     f"{IND}/2024/tx_rend_municipios_2024.zip", "nivel=municipio"),
    ("inep_distorcao", "inep_indicadores/tdi_municipios_2015.zip", 2015,
     f"{IND}/2015/distorcao_idade_serie/tdi_municipios_2015.zip", "nivel=municipio"),
    ("inep_distorcao", "inep_indicadores/TDI_2024_MUNICIPIOS.zip", 2024, f"{IND}/2024/TDI_2024_MUNICIPIOS.zip",
     "nivel=municipio"),
    ("inep_afd", "inep_indicadores/adequacao_formacao_docente_municipios_2015.zip", 2015,
     f"{IND}/2015/adequacao_formacao_docente_municipios_2015.zip", "nivel=municipio"),
    ("inep_atu", "inep_indicadores/ATU_2024_MUNICIPIOS.zip", 2024, f"{IND}/2024/ATU_2024_MUNICIPIOS.zip",
     "nivel=municipio"),
    ("inep_dsu", "inep_indicadores/DSU_2024_MUNICIPIOS.zip", 2024, f"{IND}/2024/DSU_2024_MUNICIPIOS.zip",
     "nivel=municipio"),
    ("sinopse_estatistica", "sinopse/sinopse_estatistica_censo_escolar_2024.zip", 2024,
     f"{INEP}/dados_abertos/sinopses_estatisticas/sinopse_estatistica_censo_escolar_2024.zip", None),
    ("ideb", "ideb/divulgacao_ensino_medio_municipios_2025.zip", 2025,
     f"{INEP}/ideb/resultados/divulgacao_ensino_medio_municipios_2025.zip", "etapa=med;nivel=municipio"),
    ("populacao_datasus", "api/tabnet_popsvs_juazeiro_2023_2025.html", None,
     "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?ibge/cnv/popsvs2024br.def#municipio=291840&anos=2023-2025",
     "origem=ripsa_tabnet;municipio=2918407"),
    ("sidra_ibge", "api/sidra_6579_2918407.json", None, SIDRA.format(t="6579", c="v/9324/p/all"), "populacao_estimada"),
    ("sidra_ibge", "api/sidra_9514_2918407.json", None,
     SIDRA.format(t="9514", c="v/93/p/all/c2/6794/c287/all/c286/113635"), "censo2022_idade"),
    ("sidra_ibge", "api/sidra_5938_2918407.json", None, SIDRA.format(t="5938", c="v/37/p/all"), "pib"),
    ("sidra_alfabetizacao", "api/sidra_9542_2918407.json", None,
     SIDRA.format(t="9542", c="v/950/p/all/c59/93024,1023/c2/6794/c86/95251/c287/100362"), "alfabetizacao_15_mais"),
    ("siope", "api/siope_indicadores_2023_BA.json", 2023, SIOPE.format(r="Indicadores_Siope"),
     "recurso=indicadores;uf=BA"),
    ("siope", "api/siope_receita_2023_BA.json", 2023, SIOPE.format(r="Receita_Siope"), "recurso=receita;uf=BA"),
    ("siope", "api/siope_despesa_funcao_2023_BA.json", 2023, SIOPE.format(r="Despesas_Funcao_Educacao_Siope"),
     "recurso=despesa_funcao;uf=BA"),
    ("siope", "api/siope_dados_gerais_2023_BA.json", 2023, SIOPE.format(r="Dados_Gerais_Siope"),
     "recurso=dados_gerais;uf=BA"),
    ("siconfi", "api/siconfi_dca_2023_2918407.json", 2023,
     "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca?an_exercicio=2023&no_anexo=DCA-Anexo I-E&id_ente=2918407",
     "consulta=dca_anexo_i_e;ente=2918407"),
]


def importar_todas() -> list[int]:
    from observatorio.pipeline import importar_arquivo

    return [importar_arquivo(fonte, FIX / arq, ano, url, desc) for fonte, arq, ano, url, desc in ARQUIVOS]


def carregar_tudo():
    """Importa as fixtures, transforma todas as fontes, calcula indicadores e roda os testes de qualidade."""
    from observatorio.indicadores.calcular import calcular_indicadores
    from observatorio.pipeline import executar_fontes
    from observatorio.qualidade.testes import executar_testes

    importar_todas()
    resumo = executar_fontes(None, None, 2015, False, coletar=False, transformar=True)
    ind = calcular_indicadores()
    dq = executar_testes()
    return resumo, ind, dq


if __name__ == "__main__":
    r, ind, dq = carregar_tudo()
    print(r.texto())
    print("indicadores:", ind)
    print("qualidade:", dq)
