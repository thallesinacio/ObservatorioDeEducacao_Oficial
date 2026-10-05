"""Acesso ao PostgreSQL: conexão, migrations versionadas e utilitários de carga.

As migrations ficam em ``sql/migracoes/NNN_nome.sql`` e são aplicadas em ordem, uma vez
cada, dentro de transação. O hash de cada arquivo aplicado fica em ``etl.migracao``: se um
arquivo já aplicado for alterado, o comando falha (crie uma migration nova em vez de editar).

As views da camada ``bi`` ficam em ``sql/bi/*.sql`` e são recriadas a cada ``db migrar``
(são "reexecutáveis": não guardam dado, só consulta).
"""

from __future__ import annotations

import hashlib
import io
import re
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql

from observatorio.config import DIR_SQL, configuracoes
from observatorio.log import obter_logger

log = obter_logger(__name__)

_PADRAO_MIGRACAO = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")


class ErroMigracao(RuntimeError):
    pass


def conectar(autocommit: bool = False) -> psycopg.Connection:
    cfg = configuracoes()
    return psycopg.connect(cfg.conninfo(), autocommit=autocommit)


@contextmanager
def transacao():
    """Abre conexão, faz commit no fim ou rollback em caso de erro."""
    conn = conectar()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _sha256_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def listar_migracoes(dir_migracoes: Path | None = None) -> list[tuple[str, Path]]:
    pasta = dir_migracoes or (DIR_SQL / "migracoes")
    itens = []
    for arq in sorted(pasta.glob("*.sql")):
        m = _PADRAO_MIGRACAO.match(arq.name)
        if not m:
            raise ErroMigracao(f"Nome de migration fora do padrão NNN_nome.sql: {arq.name}")
        itens.append((m.group(1), arq))
    return itens


def aplicar_migracoes(conn: psycopg.Connection) -> list[str]:
    """Aplica as migrations pendentes. Retorna as versões aplicadas nesta chamada."""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS etl")
        cur.execute(
            """CREATE TABLE IF NOT EXISTS etl.migracao (
                 versao TEXT PRIMARY KEY, arquivo TEXT NOT NULL,
                 sha256 CHAR(64) NOT NULL, aplicada_em TIMESTAMPTZ NOT NULL DEFAULT now())"""
        )
        conn.commit()
        cur.execute("SELECT versao, arquivo, sha256 FROM etl.migracao")
        ja = {v: (a, h) for v, a, h in cur.fetchall()}

    aplicadas: list[str] = []
    for versao, arq in listar_migracoes():
        texto = arq.read_text(encoding="utf-8")
        h = _sha256_texto(texto)
        if versao in ja:
            if ja[versao][1] != h:
                raise ErroMigracao(
                    f"A migration {arq.name} já foi aplicada e o arquivo mudou depois disso. "
                    "Não edite migrations aplicadas: crie uma nova (próximo número)."
                )
            continue
        log.info("Aplicando migration", arquivo=arq.name)
        try:
            with conn.cursor() as cur:
                cur.execute(texto)
                cur.execute(
                    "INSERT INTO etl.migracao (versao, arquivo, sha256) VALUES (%s, %s, %s)",
                    (versao, arq.name, h),
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise ErroMigracao(f"Falha ao aplicar {arq.name}: {e}") from e
        aplicadas.append(versao)
    return aplicadas


def recriar_views_bi(conn: psycopg.Connection) -> int:
    """Recria as views da camada bi (sql/bi/*.sql, em ordem alfabética)."""
    arquivos = sorted((DIR_SQL / "bi").glob("*.sql"))
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS bi CASCADE")
        cur.execute("CREATE SCHEMA bi")
        cur.execute(
            "COMMENT ON SCHEMA bi IS 'Camada de consumo do Power BI: views em esquema estrela, "
            "só com a versão vigente dos dados.'"
        )
        for arq in arquivos:
            cur.execute(arq.read_text(encoding="utf-8"))
        cur.execute("GRANT USAGE ON SCHEMA bi TO powerbi_leitor")
        cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA bi TO powerbi_leitor")
    conn.commit()
    return len(arquivos)


def configurar_papel_leitor(conn: psycopg.Connection, senha: str) -> None:
    """Dá LOGIN e senha ao papel powerbi_leitor (criado sem login pela migration 001)."""
    with conn.cursor() as cur:
        if senha:
            cur.execute(
                sql.SQL("ALTER ROLE powerbi_leitor WITH LOGIN PASSWORD {}").format(sql.Literal(senha))
            )
        else:
            log.warning("OBS_POWERBI_SENHA vazia: powerbi_leitor fica sem login")
            cur.execute("ALTER ROLE powerbi_leitor WITH NOLOGIN")
        # Garante que o leitor não enxerga nada fora do bi, mesmo se alguém der GRANT por engano.
        cur.execute("REVOKE ALL ON ALL TABLES IN SCHEMA raw, staging, core, etl FROM powerbi_leitor")
        cur.execute("REVOKE ALL ON SCHEMA raw, staging, core, etl FROM powerbi_leitor")
        cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO powerbi_leitor").format(
            sql.Identifier(configuracoes().db_nome)))
    conn.commit()


def executar_arquivo_sql(conn: psycopg.Connection, caminho: Path, params: dict[str, Any] | None = None) -> None:
    texto = caminho.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(texto, params or {})


# ------------------------------------------------------------------ carga em massa

def _formatar_copy(valor: Any) -> str:
    if valor is None:
        return "\\N"
    if isinstance(valor, bool):
        return "t" if valor else "f"
    s = str(valor)
    return (
        s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
    )


def copiar_linhas(
    conn: psycopg.Connection,
    tabela: str,
    colunas: Sequence[str],
    linhas: Iterable[Sequence[Any]],
    tamanho_lote: int = 50_000,
) -> int:
    """Carga em massa com COPY (formato texto). Retorna o número de linhas copiadas."""
    esquema, nome = tabela.split(".")
    comando = sql.SQL("COPY {}.{} ({}) FROM STDIN").format(
        sql.Identifier(esquema), sql.Identifier(nome), sql.SQL(", ").join(map(sql.Identifier, colunas))
    )
    total = 0
    with conn.cursor() as cur, cur.copy(comando) as cp:
        buf = io.StringIO()
        n = 0
        for linha in linhas:
            buf.write("\t".join(_formatar_copy(v) for v in linha))
            buf.write("\n")
            n += 1
            if n >= tamanho_lote:
                cp.write(buf.getvalue())
                total += n
                buf = io.StringIO()
                n = 0
        if n:
            cp.write(buf.getvalue())
            total += n
    return total


def banco_disponivel() -> bool:
    try:
        with conectar(autocommit=True) as c, c.cursor() as cur:
            cur.execute("SELECT 1")
        return True
    except Exception:
        return False
