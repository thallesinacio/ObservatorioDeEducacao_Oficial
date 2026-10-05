"""Configuração comum dos testes.

* Testes marcados ``rede`` acessam os sites oficiais e ficam fora da execução padrão
  (``pytest`` roda com ``-m "not rede"``; use ``pytest -m rede`` para rodá-los).
* Testes marcados ``banco`` precisam de um PostgreSQL. Eles usam um banco próprio, criado e
  apagado a cada sessão (nome em OBS_DB_NOME_TESTE, padrão "observatorio_teste"), com o mesmo
  host/usuário/senha do .env. Se não houver PostgreSQL acessível, são pulados.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import psycopg
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures() -> Path:
    return FIXTURES


def _conninfo(dbname: str) -> str:
    from observatorio import config

    cfg = config.configuracoes()
    partes = {"host": cfg.db_host, "port": str(cfg.db_porta), "dbname": dbname, "user": cfg.db_usuario,
              "password": cfg.db_senha}
    return " ".join(f"{k}='{v}'" for k, v in partes.items() if v)


@pytest.fixture(scope="session")
def banco_teste(tmp_path_factory):
    """Banco vazio + pasta de dados temporária; devolve o nome do banco."""
    from observatorio import config

    nome = os.environ.get("OBS_DB_NOME_TESTE", "observatorio_teste")
    try:
        with psycopg.connect(_conninfo("postgres"), autocommit=True, connect_timeout=3) as adm:
            adm.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')
            adm.execute(f'CREATE DATABASE "{nome}"')
    except Exception as e:  # sem PostgreSQL ou sem permissão para criar banco
        pytest.skip(f"PostgreSQL indisponível para os testes de banco: {e}")

    dados = tmp_path_factory.mktemp("dados")
    antigos = {k: os.environ.get(k) for k in ("OBS_DB_NOME", "OBS_DIR_DADOS", "OBS_POWERBI_SENHA",
                                             "OBS_PAUSA_ENTRE_CHAMADAS")}
    os.environ.update({"OBS_DB_NOME": nome, "OBS_DIR_DADOS": str(dados), "OBS_POWERBI_SENHA": "senha-de-teste",
                       "OBS_PAUSA_ENTRE_CHAMADAS": "0"})
    config.configuracoes.cache_clear()
    # Cache da API de localidades do IBGE (resposta real guardada nas fixtures): migrar roda offline.
    cache = dados / "raw" / "ibge_localidades"
    cache.mkdir(parents=True)
    shutil.copyfile(FIXTURES / "api" / "ibge_localidades_municipios.json", cache / "municipios.json")
    shutil.copyfile(FIXTURES / "api" / "ibge_localidades_estados.json", cache / "estados.json")
    yield nome
    for k, v in antigos.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    config.configuracoes.cache_clear()
    try:
        with psycopg.connect(_conninfo("postgres"), autocommit=True, connect_timeout=3) as adm:
            adm.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')
    except Exception:
        pass
