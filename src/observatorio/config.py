"""Configuração do projeto.

Duas camadas:

* ``Configuracoes`` (pydantic-settings): segredos e ajustes de ambiente, lidos do arquivo
  ``.env`` na raiz do projeto ou de variáveis de ambiente com prefixo ``OBS_``.
* Arquivos YAML em ``config/``: territórios, fontes, indicadores e layouts. Ficam versionados
  no Git porque descrevem o método, não o ambiente.
"""

from __future__ import annotations

import os
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


def _descobrir_raiz() -> Path:
    """Raiz do projeto: a pasta que contém ``config/`` e ``sql/``."""
    if os.environ.get("OBS_RAIZ"):
        return Path(os.environ["OBS_RAIZ"]).resolve()
    aqui = Path(__file__).resolve()
    for candidato in [aqui.parents[2], Path.cwd(), *Path.cwd().parents]:
        if (candidato / "config" / "projeto.yaml").exists() and (candidato / "sql").exists():
            return candidato
    return aqui.parents[2]


RAIZ = _descobrir_raiz()
DIR_CONFIG = RAIZ / "config"
DIR_SQL = RAIZ / "sql"
DIR_DOCS = RAIZ / "docs"


class Configuracoes(BaseSettings):
    """Ajustes de ambiente (arquivo .env)."""

    model_config = SettingsConfigDict(
        env_prefix="OBS_",
        env_file=str(RAIZ / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_host: str = "localhost"
    db_porta: int = 5432
    db_nome: str = "observatorio"
    db_usuario: str = "observatorio_etl"
    db_senha: str = ""

    powerbi_senha: str = ""

    dir_dados: str = "data"
    manter_zip_bruto: bool = True
    pausa_entre_chamadas: float = 1.0
    timeout_http: int = 120
    nivel_log: str = "INFO"

    @property
    def caminho_dados(self) -> Path:
        p = Path(self.dir_dados)
        return p if p.is_absolute() else (RAIZ / p)

    @property
    def caminho_raw(self) -> Path:
        return self.caminho_dados / "raw"

    def conninfo(self) -> str:
        """String de conexão no formato aceito pelo psycopg 3."""
        partes = {
            "host": self.db_host,
            "port": str(self.db_porta),
            "dbname": self.db_nome,
            "user": self.db_usuario,
            "password": self.db_senha,
            "application_name": "observatorio_etl",
        }
        return " ".join(f"{k}='{_escapar(v)}'" for k, v in partes.items() if v != "")


def _escapar(valor: str) -> str:
    return valor.replace("\\", "\\\\").replace("'", "\\'")


@lru_cache(maxsize=1)
def configuracoes() -> Configuracoes:
    return Configuracoes()


@cache
def carregar_yaml(nome: str) -> dict[str, Any]:
    """Lê um arquivo YAML de ``config/`` (ex.: ``carregar_yaml("fontes.yaml")``)."""
    caminho = DIR_CONFIG / nome
    with caminho.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def projeto() -> dict[str, Any]:
    return carregar_yaml("projeto.yaml")


def territorios_alvo() -> list[str]:
    return [str(c) for c in projeto()["territorios"]["municipios_alvo"]]


def territorios_comparacao() -> list[str]:
    return [str(c) for c in projeto()["territorios"].get("municipios_comparacao", [])]


def municipios_de_interesse() -> list[str]:
    """Municípios alvo + comparação, sem repetição, na ordem da configuração."""
    vistos: list[str] = []
    for c in territorios_alvo() + territorios_comparacao():
        if c not in vistos:
            vistos.append(c)
    return vistos


def ufs_comparacao() -> list[str]:
    return [str(c) for c in projeto()["territorios"].get("ufs_comparacao", [])]


def incluir_brasil() -> bool:
    return bool(projeto()["territorios"].get("incluir_brasil", True))


def ano_inicial_padrao() -> int:
    return int(projeto()["periodo"]["ano_inicial_padrao"])


def versao_calculo_indicadores() -> str:
    return str(projeto()["metodologia"]["versao_calculo_indicadores"])


def opcao_coleta(nome: str, padrao: Any = None) -> Any:
    return projeto().get("coleta", {}).get(nome, padrao)


def opcao_qualidade(nome: str, padrao: Any = None) -> Any:
    return projeto().get("qualidade", {}).get(nome, padrao)


def fontes() -> list[dict[str, Any]]:
    return list(carregar_yaml("fontes.yaml")["fontes"])


def fonte(id_fonte: str) -> dict[str, Any]:
    for f in fontes():
        if f["id"] == id_fonte:
            return f
    raise KeyError(f"Fonte '{id_fonte}' não está em config/fontes.yaml")


def indicadores() -> list[dict[str, Any]]:
    return list(carregar_yaml("indicadores.yaml")["indicadores"])


def user_agent() -> str:
    return str(projeto()["projeto"]["user_agent"])
