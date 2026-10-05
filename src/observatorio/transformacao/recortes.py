"""Códigos de recorte (core.dim_recorte).

Formato canônico: partes "eixo:valor" separadas por "|", na ordem rede, localizacao e um terceiro
eixo opcional. Sem partes = "total". Exemplos: ``rede:municipal``, ``rede:publica|localizacao:rural``,
``raca_cor:parda``.
"""

from __future__ import annotations

from functools import lru_cache

from observatorio.config import carregar_yaml

TOTAL = "total"


def montar(rede: str | None = None, localizacao: str | None = None, outro: str | None = None) -> str:
    """``outro`` no formato "tipo:valor" (ex.: "sexo:feminino") ou None."""
    partes = []
    if rede:
        partes.append(f"rede:{rede}")
    if localizacao:
        partes.append(f"localizacao:{localizacao}")
    if outro and outro != TOTAL:
        if ":" not in outro:
            raise ValueError(f"Recorte inválido (esperado tipo:valor): {outro}")
        partes.append(outro)
    return "|".join(partes) if partes else TOTAL


def decompor(codigo: str) -> dict[str, str | None]:
    d: dict[str, str | None] = {"rede": None, "localizacao": None, "tipo_outro": None, "valor_outro": None}
    if codigo == TOTAL:
        return d
    for parte in codigo.split("|"):
        tipo, _, valor = parte.partition(":")
        if tipo in ("rede", "localizacao"):
            d[tipo] = valor
        else:
            d["tipo_outro"], d["valor_outro"] = tipo, valor
    return d


@lru_cache(maxsize=1)
def _eixos() -> dict:
    return carregar_yaml("recortes.yaml")["eixos"]


def rotulo(codigo: str) -> str:
    if codigo == TOTAL:
        return "Total"
    eixos = _eixos()
    partes = []
    for parte in codigo.split("|"):
        tipo, _, valor = parte.partition(":")
        eixo = eixos.get(tipo, {})
        nome_valor = (eixo.get("valores") or {}).get(valor, valor.replace("_", " "))
        partes.append(f"{eixo.get('rotulo', tipo)}: {nome_valor}")
    return " | ".join(partes)


def ordem(codigo: str) -> int:
    if codigo == TOTAL:
        return 0
    eixos = list(_eixos())
    d = decompor(codigo)
    n = 0
    for i, chave in enumerate(("rede", "localizacao")):
        if d[chave]:
            valores = list(_eixos()[chave].get("valores") or {})
            n += (i + 1) * 100 + (valores.index(d[chave]) if d[chave] in valores else 50)
    if d["tipo_outro"]:
        t = d["tipo_outro"]
        valores = list(_eixos().get(t, {}).get("valores") or {})
        n += 1000 * (eixos.index(t) + 1 if t in eixos else 50) + (valores.index(d["valor_outro"]) if d["valor_outro"] in valores else 99)
    return n
