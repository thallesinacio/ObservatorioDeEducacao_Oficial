"""Estrutura comum dos coletores.

Cada fonte implementa:

* ``coletar(ctx)``: descobre e baixa os arquivos (ou consulta a API), grava em
  ``data/raw/<fonte>/<ano>/`` e registra no manifesto (etl.etl_arquivo);
* ``processar(conn, arquivo, ctx)``: lê um arquivo e grava o recorte em raw.linha e os dados
  tipados no staging (substituindo o que houver do mesmo ano/arquivo: idempotente);
* ``carregar_core(conn, id_versao, ctx)``: do staging para os fatos do core, com a versão.

O orquestrador (observatorio.pipeline) cuida de execução, transação, versão e vigência.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg

from observatorio import config
from observatorio.db import copiar_linhas
from observatorio.execucao import ArquivoRegistrado, Execucao, caminho_absoluto, registrar_arquivo
from observatorio.http import ArquivoBaixado, baixar, consultar_cabecalhos
from observatorio.log import obter_logger

log = obter_logger(__name__)


@dataclass
class Contexto:
    execucao: Execucao
    anos: list[int] | None = None          # None = todos os disponíveis a partir do ano inicial
    ano_inicial: int = field(default_factory=config.ano_inicial_padrao)
    forcar: bool = False

    @property
    def id_execucao(self) -> int | None:
        return self.execucao.id_execucao

    def ano_desejado(self, ano: int) -> bool:
        if self.anos:
            return ano in self.anos
        return ano >= self.ano_inicial

    def alertar(self, msg: str) -> None:
        self.execucao.alertar(msg)


class Fonte(ABC):
    id_fonte: str = ""
    # Fatos do core escritos por esta fonte (a carga apaga as linhas da versão antes de reinserir).
    tabelas_core: Sequence[str] = ()
    # Versão do código de transformação desta fonte: mudar força nova versão de dados.
    versao_transformacao: str = "1"

    @property
    def pasta_raw(self) -> Path:
        return config.configuracoes().caminho_raw / self.id_fonte

    def pasta_ano(self, ano: int | None) -> Path:
        return self.pasta_raw / (str(ano) if ano is not None else "sem_ano")

    @abstractmethod
    def coletar(self, conn: psycopg.Connection, ctx: Contexto) -> list[ArquivoRegistrado]:
        ...

    @abstractmethod
    def processar(self, conn: psycopg.Connection, arquivo: ArquivoRegistrado, ctx: Contexto) -> int:
        ...

    @abstractmethod
    def carregar_core(self, conn: psycopg.Connection, id_versao: int, ctx: Contexto) -> int:
        ...

    # -------------------------------------------------------------- utilitários

    def baixar_registrar(
        self, conn: psycopg.Connection, ctx: Contexto, url: str, ano: int | None, nome_arquivo: str,
        *, versao_layout: str | None = None, descricao: str | None = None, verificar_cabecalho: bool = True,
    ) -> ArquivoRegistrado:
        """Baixa (ou reaproveita, se o arquivo remoto não mudou) e registra no manifesto."""
        destino = self.pasta_ano(ano) / nome_arquivo
        baixado = None
        if verificar_cabecalho and not ctx.forcar:
            baixado = self._reaproveitar(conn, url, ano, destino)
        if baixado is None:
            baixado = baixar(url, destino)
        return registrar_arquivo(conn, self.id_fonte, ano, baixado, id_execucao=ctx.id_execucao,
                                 versao_layout=versao_layout, descricao=descricao)

    def _reaproveitar(self, conn: psycopg.Connection, url: str, ano: int | None, destino: Path) -> ArquivoBaixado | None:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT sha256, caminho_local, tamanho_bytes, status_http, http_last_modified, http_etag
                   FROM etl.etl_arquivo WHERE id_fonte = %s AND url = %s AND ano_referencia IS NOT DISTINCT FROM %s
                     AND NOT arquivo_removido
                   ORDER BY data_coleta DESC LIMIT 1""",
                (self.id_fonte, url, ano),
            )
            linha = cur.fetchone()
        if not linha:
            return None
        sha, caminho, tamanho, status, lm, etag = linha
        local = caminho_absoluto(caminho)
        if not local.exists() or local.stat().st_size != tamanho:
            return None
        try:
            cab = {k.lower(): v for k, v in consultar_cabecalhos(url).items()}
        except Exception:
            return None
        mesmo_tamanho = cab.get("content-length") in (None, str(tamanho))
        mesmo_lm = lm is not None and cab.get("last-modified") == lm
        mesmo_etag = etag is not None and cab.get("etag") == etag
        if mesmo_tamanho and (mesmo_lm or mesmo_etag):
            log.info("Arquivo remoto não mudou; usando cópia local", url=url)
            return ArquivoBaixado(url, local, sha, tamanho, status or 200, lm, etag, reaproveitado=True)
        return None


# ------------------------------------------------------------------ raw

def gravar_raw(conn: psycopg.Connection, id_arquivo: int, tabela_origem: str,
               linhas: Iterable[tuple[int, dict[str, Any]]]) -> int:
    """Grava o recorte bruto (todas as colunas em texto) em raw.linha, substituindo o anterior."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM raw.linha WHERE id_arquivo = %s AND tabela_origem = %s", (id_arquivo, tabela_origem))
    return copiar_linhas(
        conn, "raw.linha", ["id_arquivo", "tabela_origem", "num_linha", "dados"],
        ((id_arquivo, tabela_origem, n, json.dumps({k: (None if v is None else str(v)) for k, v in d.items()},
                                                   ensure_ascii=False)) for n, d in linhas),
    )


def nome_seguro(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", texto).strip("_")
