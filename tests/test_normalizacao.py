from decimal import Decimal

import pytest

from observatorio.transformacao import recortes as rc
from observatorio.transformacao.normalizacao import (
    codigo_escola,
    codigo_municipio,
    converter_numero,
    normalizar_localizacao,
    normalizar_rede,
)


@pytest.mark.parametrize("entrada,esperado", [
    ("13,9", Decimal("13.9")),
    ("40.799999999999997", Decimal("40.8")),
    (81.59999999999999, Decimal("81.6")),
    ("1.234,5", Decimal("1234.5")),
    ("0", Decimal("0")),
])
def test_converte_numeros(entrada, esperado):
    t = converter_numero(entrada, "inep_rendimento")
    assert t.status == "observado"
    assert t.valor == esperado


@pytest.mark.parametrize("fonte,marcador,status", [
    ("inep_rendimento", "--", "nao_se_aplica"),
    ("inep_rendimento", "-", "sem_dado"),
    ("ideb", "ND", "sem_dado"),
    ("ideb", "-", "sem_dado"),
    ("sidra_ibge", "...", "sem_dado"),
    ("sidra_ibge", "..", "nao_se_aplica"),
])
def test_marcadores_viram_status_e_nunca_zero(fonte, marcador, status):
    t = converter_numero(marcador, fonte)
    assert t.status == status
    assert t.valor is None


def test_traco_do_ibge_e_zero_absoluto():
    t = converter_numero("-", "sidra_ibge")
    assert (t.status, t.valor) == ("observado", Decimal(0))


def test_celula_vazia_e_lacuna():
    assert converter_numero("", "inep_afd").status == "sem_dado"
    assert converter_numero(None, "inep_afd").valor is None


def test_codigos_como_texto():
    assert codigo_municipio("2918407") == "2918407"
    assert codigo_municipio(2918407.0) == "2918407"
    assert codigo_escola("29024650") == "29024650"


@pytest.mark.parametrize("texto,rede", [("Particular", "privada"), ("Privada (1)", "privada"), ("Pública", "publica"),
                                        ("Municipal", "municipal"), ("Total", None)])
def test_rede(texto, rede):
    assert normalizar_rede(texto) == rede


def test_localizacao():
    assert normalizar_localizacao("Urbana") == "urbana"
    assert normalizar_localizacao("Total") is None
    with pytest.raises(ValueError):
        normalizar_localizacao("Marte")


def test_recortes_canonicos():
    assert rc.montar() == "total"
    assert rc.montar("municipal", "rural") == "rede:municipal|localizacao:rural"
    assert rc.montar("publica", outro="raca_cor:parda") == "rede:publica|raca_cor:parda"
    assert rc.decompor("rede:municipal|porte:ate_50") == {"rede": "municipal", "localizacao": None,
                                                         "tipo_outro": "porte", "valor_outro": "ate_50"}
