"""Regras de tratamento comuns a todas as fontes.

* Códigos: município com 7 dígitos, escola com 8, sempre texto com zeros à esquerda.
* Texto: trim e espaços repetidos colapsados (o original fica no raw).
* Números: vírgula decimal, separador de milhar, floats de planilha (40.799999999999997).
* Ausência: cada marcador vira um status (config/regras_ausencia.yaml); nunca zero.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import cache
from typing import Any

from observatorio.config import carregar_yaml

_ESPACOS = re.compile(r"\s+")
_NUMERO_BR = re.compile(r"^[+-]?\d{1,3}(\.\d{3})+(,\d+)?$")   # 1.234.567,89
_NUMERO_VIRGULA = re.compile(r"^[+-]?\d+,\d+$")                  # 13,9
_NUMERO_PONTO = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")  # 13.9 / 1e-3


def texto_limpo(valor: Any) -> str | None:
    if valor is None:
        return None
    s = _ESPACOS.sub(" ", str(valor).replace("\xa0", " ")).strip()
    return s or None


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalizar_rotulo(s: Any) -> str:
    """Minúsculas, sem acento e com espaços simples; usado para comparar cabeçalhos."""
    t = texto_limpo(s) or ""
    t = sem_acento(t).lower()
    t = t.replace("°", "º").replace("ª", "a").replace("º", "o")
    return _ESPACOS.sub(" ", t).strip()


def _somente_digitos(valor: Any) -> str | None:
    if valor is None:
        return None
    s = str(valor).strip()
    if not s:
        return None
    if re.fullmatch(r"\d+\.0+", s):  # 2918407.0 vindo de planilha
        s = s.split(".")[0]
    s = re.sub(r"\D", "", s)
    return s or None


def codigo_municipio(valor: Any) -> str | None:
    """Código IBGE do município com 7 dígitos (texto)."""
    s = _somente_digitos(valor)
    if s is None:
        return None
    if len(s) > 7:
        raise ValueError(f"Código de município com mais de 7 dígitos: {valor!r}")
    return s.zfill(7)


def codigo_municipio_6(cod7: str) -> str:
    """Código de 6 dígitos (sem o verificador), usado por DATASUS e SIOPE."""
    return cod7[:6]


def codigo_escola(valor: Any) -> str | None:
    """Código INEP da escola com 8 dígitos (texto)."""
    s = _somente_digitos(valor)
    if s is None:
        return None
    if len(s) > 8:
        raise ValueError(f"Código de escola com mais de 8 dígitos: {valor!r}")
    return s.zfill(8)


def inteiro(valor: Any) -> int | None:
    if valor is None:
        return None
    s = str(valor).strip()
    if s == "":
        return None
    try:
        return int(Decimal(s.replace(",", ".")))
    except (InvalidOperation, ValueError):
        return None


# ------------------------------------------------------------------ regras de ausência

@dataclass(frozen=True)
class Regra:
    status: str
    valor: Decimal | None
    descricao: str


@cache
def regras_ausencia(id_fonte: str) -> dict[str, Regra]:
    cfg = carregar_yaml("regras_ausencia.yaml")
    regras: dict[str, Regra] = {}
    for marcador, r in (cfg.get("fontes", {}).get(id_fonte) or {}).items():
        regras[str(marcador).strip()] = Regra(
            r["status"], Decimal(str(r["valor"])) if "valor" in r else None, r.get("descricao", "")
        )
    return regras


@dataclass(frozen=True)
class ValorTratado:
    valor: Decimal | None
    status: str
    texto: str | None


def converter_numero(valor: Any, id_fonte: str, casas: int = 6) -> ValorTratado:
    """Converte uma célula em número + status, aplicando as regras de ausência da fonte.

    >>> converter_numero("13,9", "inep_distorcao").valor
    Decimal('13.9')
    >>> converter_numero("--", "inep_distorcao").status
    'nao_se_aplica'
    """
    if valor is None:
        return ValorTratado(None, "sem_dado", None)
    if isinstance(valor, bool):
        valor = int(valor)
    if isinstance(valor, (int, float, Decimal)):
        texto = repr(valor) if isinstance(valor, float) else str(valor)
        d = Decimal(str(valor)) if not isinstance(valor, float) else Decimal(repr(valor))
        return ValorTratado(_arredondar(d, casas), "observado", texto)
    texto = str(valor).strip()
    if texto == "":
        return ValorTratado(None, "sem_dado", None)
    regra = regras_ausencia(id_fonte).get(texto)
    if regra is not None:
        return ValorTratado(regra.valor, regra.status, texto)
    s = texto.replace("\xa0", "").replace(" ", "")
    try:
        if _NUMERO_BR.match(s):
            d = Decimal(s.replace(".", "").replace(",", "."))
        elif _NUMERO_VIRGULA.match(s):
            d = Decimal(s.replace(",", "."))
        elif _NUMERO_PONTO.match(s):
            d = Decimal(s)
        else:
            return ValorTratado(None, "sem_dado", texto)
    except InvalidOperation:
        return ValorTratado(None, "sem_dado", texto)
    return ValorTratado(_arredondar(d, casas), "observado", texto)


def _arredondar(d: Decimal, casas: int) -> Decimal:
    q = Decimal(1).scaleb(-casas)
    r = d.quantize(q, rounding=ROUND_HALF_UP)
    return r.normalize() if r != 0 else Decimal(0)


# ------------------------------------------------------------------ rede e localização

_REDES = {
    "federal": "federal",
    "estadual": "estadual",
    "municipal": "municipal",
    "privada": "privada",
    "particular": "privada",
    "publica": "publica",
    "total": None,
}


def normalizar_rede(valor: Any) -> str | None:
    """'Particular' e 'Privada (1)' viram 'privada'; 'Total' vira None (todas as redes)."""
    t = normalizar_rotulo(valor)
    t = re.sub(r"\(\d+\)|\d+$", "", t).strip()
    if t in _REDES:
        return _REDES[t]
    raise ValueError(f"Rede não reconhecida: {valor!r}")


def normalizar_localizacao(valor: Any) -> str | None:
    t = normalizar_rotulo(valor)
    t = re.sub(r"\(\d+\)|\d+$", "", t).strip()
    if t in ("urbana", "urbano"):
        return "urbana"
    if t in ("rural",):
        return "rural"
    if t in ("total", ""):
        return None
    raise ValueError(f"Localização não reconhecida: {valor!r}")


_REDE_POR_TP_DEPENDENCIA = {1: "federal", 2: "estadual", 3: "municipal", 4: "privada"}
_LOCALIZACAO_POR_TP = {1: "urbana", 2: "rural"}


def rede_por_tp_dependencia(tp: int | None) -> str | None:
    return _REDE_POR_TP_DEPENDENCIA.get(tp) if tp is not None else None


def localizacao_por_tp(tp: int | None) -> str | None:
    return _LOCALIZACAO_POR_TP.get(tp) if tp is not None else None
