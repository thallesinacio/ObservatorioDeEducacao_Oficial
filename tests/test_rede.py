"""Testes que acessam os sites oficiais (fora da execução padrão). Rode com:  pytest -m rede

Servem para detectar cedo mudanças de página, nome de arquivo ou formato das APIs.
"""

from __future__ import annotations

import pytest

from observatorio import config

pytestmark = pytest.mark.rede


def test_pagina_do_censo_lista_os_zips():
    from observatorio.coleta.censo_escolar import CensoEscolar

    links = CensoEscolar().descobrir_links()
    assert 2015 in links and 2024 in links


def test_indicadores_educacionais_tem_abas_por_ano():
    from observatorio.coleta.inep_indicadores import descobrir_links_por_ano

    links = descobrir_links_por_ano(config.fonte("inep_distorcao")["pagina_oficial"])
    assert links.get(2024, {}).get("municipio")


def test_pagina_do_ideb_e_da_sinopse():
    from observatorio.coleta import ideb, sinopse
    from observatorio.http import obter_texto

    assert ideb.descobrir_links(obter_texto(config.fonte("ideb")["pagina_oficial"]))
    assert 2024 in sinopse.descobrir_links(obter_texto(config.fonte("sinopse_estatistica")["pagina_oficial"]))


def test_apis_respondem():
    from observatorio.coleta import sidra, siope
    from observatorio.http import obter_json

    assert len(obter_json(sidra.montar_url("6579", ["2918407"], "v/9324/p/last"))) >= 2
    assert obter_json(siope.montar_url("Indicadores_Siope", 2023, "BA", ["291840"]))["value"]
