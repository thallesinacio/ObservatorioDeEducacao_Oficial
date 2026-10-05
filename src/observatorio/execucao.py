"""Registro operacional: execuções, manifesto de arquivos e versões de dados.

* ``Execucao``: context manager que grava uma linha em etl.etl_execucao (com conexão própria em
  autocommit, para o registro sobreviver mesmo se a transação dos dados falhar).
* ``registrar_arquivo``: manifesto em etl.etl_arquivo (URL, sha256, tamanho, status HTTP...).
* ``obter_versao``: versão de carga identificada pelo hash das entradas. Mesma entrada = mesma
  versão, o que torna a carga idempotente (reexecutar não cria versão nova nem duplica linhas).
"""

from __future__ import annotations

import hashlib
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import psycopg

from observatorio.config import configuracoes
from observatorio.db import conectar
from observatorio.http import ArquivoBaixado
from observatorio.log import obter_logger

log = obter_logger(__name__)


class Execucao:
    """Uso:

    with Execucao("coletar", "censo_escolar", "anos=2015-2025") as ex:
        ...
        ex.linhas_lidas += n
    """

    def __init__(self, job: str, id_fonte: str | None = None, parametros: str | None = None):
        self.job = job
        self.id_fonte = id_fonte
        self.parametros = parametros
        self.id_execucao: int | None = None
        self.linhas_lidas = 0
        self.linhas_gravadas = 0
        self.alertas: list[str] = []
        self.status_final: str | None = None
        self._conn: psycopg.Connection | None = None

    def __enter__(self) -> Execucao:
        self._conn = conectar(autocommit=True)
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO etl.etl_execucao (job, id_fonte, parametros) VALUES (%s, %s, %s) RETURNING id_execucao",
                (self.job, self.id_fonte, self.parametros),
            )
            self.id_execucao = cur.fetchone()[0]
        log.info("Início", job=self.job, fonte=self.id_fonte, execucao=self.id_execucao)
        return self

    def ignorar(self, motivo: str) -> None:
        self.status_final = "ignorado"
        self.alertas.append(motivo)

    def alertar(self, mensagem: str) -> None:
        self.alertas.append(mensagem)
        log.warning(mensagem, job=self.job, fonte=self.id_fonte)

    def __exit__(self, tipo, exc, tb) -> bool:
        if exc is not None:
            status = "falha"
            mensagem = f"{tipo.__name__}: {exc}\n" + "".join(traceback.format_tb(tb)[-3:])
        else:
            status = self.status_final or ("sucesso_com_alertas" if self.alertas else "sucesso")
            mensagem = "\n".join(self.alertas) if self.alertas else None
        assert self._conn is not None
        with self._conn.cursor() as cur:
            cur.execute(
                """UPDATE etl.etl_execucao SET fim = now(), status = %s, linhas_lidas = %s,
                   linhas_gravadas = %s, mensagem_erro = %s WHERE id_execucao = %s""",
                (status, self.linhas_lidas, self.linhas_gravadas, mensagem, self.id_execucao),
            )
        self._conn.close()
        nivel = log.error if status == "falha" else log.info
        nivel("Fim", job=self.job, fonte=self.id_fonte, status=status,
              lidas=self.linhas_lidas, gravadas=self.linhas_gravadas)
        return False  # a exceção segue para o chamador


@dataclass
class ArquivoRegistrado:
    id_arquivo: int
    id_fonte: str
    ano: int | None
    url: str
    caminho: Path
    sha256: str
    data_coleta: datetime
    ja_processado: bool
    versao_layout: str | None = None
    descricao: str | None = None
    extras: dict = field(default_factory=dict)


def caminho_relativo(caminho: Path) -> str:
    base = configuracoes().caminho_dados
    try:
        return caminho.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return caminho.as_posix()


def caminho_absoluto(relativo: str) -> Path:
    p = Path(relativo)
    return p if p.is_absolute() else configuracoes().caminho_dados / p


def registrar_arquivo(
    conn: psycopg.Connection,
    id_fonte: str,
    ano: int | None,
    baixado: ArquivoBaixado,
    *,
    id_execucao: int | None,
    versao_layout: str | None = None,
    descricao: str | None = None,
) -> ArquivoRegistrado:
    """Grava (ou reaproveita) a linha do manifesto. Mesmo (fonte, ano, sha256, url) = mesmo arquivo."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO etl.etl_arquivo
                 (id_fonte, ano_referencia, url, sha256, data_coleta, caminho_local, tamanho_bytes,
                  status_http, http_last_modified, http_etag, versao_layout, descricao, id_execucao)
               VALUES (%s, %s, %s, %s, now(), %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id_fonte, ano_referencia, sha256, url) DO UPDATE
                 SET caminho_local = EXCLUDED.caminho_local, arquivo_removido = false,
                     http_last_modified = COALESCE(EXCLUDED.http_last_modified, etl.etl_arquivo.http_last_modified),
                     http_etag = COALESCE(EXCLUDED.http_etag, etl.etl_arquivo.http_etag)
               RETURNING id_arquivo, data_coleta, processado_em""",
            (id_fonte, ano, baixado.url, baixado.sha256, caminho_relativo(baixado.caminho), baixado.tamanho,
             baixado.status, baixado.last_modified, baixado.etag, versao_layout, descricao, id_execucao),
        )
        id_arquivo, data_coleta, processado_em = cur.fetchone()
    conn.commit()
    return ArquivoRegistrado(id_arquivo, id_fonte, ano, baixado.url, baixado.caminho, baixado.sha256,
                             data_coleta, processado_em is not None, versao_layout, descricao)


def marcar_processado(conn: psycopg.Connection, id_arquivo: int, versao_layout: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE etl.etl_arquivo SET processado_em = now(), versao_layout = COALESCE(%s, versao_layout) WHERE id_arquivo = %s",
            (versao_layout, id_arquivo),
        )


def marcar_removido(conn: psycopg.Connection, id_arquivo: int) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE etl.etl_arquivo SET arquivo_removido = true WHERE id_arquivo = %s", (id_arquivo,))


def arquivos_vigentes(conn: psycopg.Connection, id_fonte: str) -> list[tuple[int, int | None, str, str, date]]:
    """Arquivo mais recente já processado para cada (ano, url) da fonte.

    Retorna (id_arquivo, ano, sha256, url, data_coleta).
    """
    with conn.cursor() as cur:
        cur.execute(
            """SELECT DISTINCT ON (ano_referencia, url) id_arquivo, ano_referencia, sha256, url, data_coleta::date
               FROM etl.etl_arquivo
               WHERE id_fonte = %s AND processado_em IS NOT NULL
               ORDER BY ano_referencia, url, processado_em DESC, id_arquivo DESC""",
            (id_fonte,),
        )
        return cur.fetchall()


def assinatura(partes: list[str]) -> str:
    h = hashlib.sha256()
    for p in sorted(partes):
        h.update(p.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def obter_versao(
    conn: psycopg.Connection, id_fonte: str, partes: list[str], descricao: str, id_execucao: int | None
) -> tuple[int, bool]:
    """Devolve (id_versao, nova). Não torna vigente: chame ``tornar_vigente`` após carregar."""
    ass = assinatura(partes)
    with conn.cursor() as cur:
        cur.execute("SELECT id_versao FROM etl.versao_dados WHERE id_fonte = %s AND assinatura = %s", (id_fonte, ass))
        linha = cur.fetchone()
        if linha:
            return linha[0], False
        cur.execute(
            """INSERT INTO etl.versao_dados (id_fonte, assinatura, descricao, id_execucao)
               VALUES (%s, %s, %s, %s) RETURNING id_versao""",
            (id_fonte, ass, descricao, id_execucao),
        )
        return cur.fetchone()[0], True


def tornar_vigente(conn: psycopg.Connection, id_fonte: str, id_versao: int) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE etl.versao_dados SET vigente = false WHERE id_fonte = %s AND id_versao <> %s AND vigente",
                    (id_fonte, id_versao))
        cur.execute("UPDATE etl.versao_dados SET vigente = true WHERE id_versao = %s", (id_versao,))


def versao_vigente(conn: psycopg.Connection, id_fonte: str) -> int | None:
    with conn.cursor() as cur:
        cur.execute("SELECT id_versao FROM etl.versao_dados WHERE id_fonte = %s AND vigente", (id_fonte,))
        r = cur.fetchone()
        return r[0] if r else None
