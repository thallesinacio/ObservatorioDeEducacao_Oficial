"""Acesso à internet: sessão HTTP com retry, pausa entre chamadas e download em streaming.

* ``User-Agent`` identifica o projeto (config/projeto.yaml).
* Timeout e pausa vêm do .env (OBS_TIMEOUT_HTTP, OBS_PAUSA_ENTRE_CHAMADAS).
* Retry com backoff exponencial em erros de rede e respostas 429/5xx.
* Download grava em arquivo temporário, calcula o sha256 durante a gravação e só então
  move para o destino final: um download interrompido nunca deixa arquivo pela metade.
"""

from __future__ import annotations

import ftplib
import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

try:
    # Usa o repositório de certificados do sistema operacional (no Windows, o mesmo do navegador).
    # Necessário porque download.inep.gov.br não envia a cadeia intermediária do certificado: o
    # navegador completa a cadeia sozinho, mas o pacote de certificados padrão do Python não, e a
    # conexão falhava com SSLError. A verificação do certificado continua ligada.
    import truststore

    truststore.inject_into_ssl()
except ImportError:  # pragma: no cover
    pass

import requests
from requests.adapters import HTTPAdapter
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from observatorio.config import configuracoes, user_agent
from observatorio.log import obter_logger

log = obter_logger(__name__)

_ultima_chamada: dict[str, float] = {}


class ErroHttp(RuntimeError):
    def __init__(self, mensagem: str, status: int | None = None):
        super().__init__(mensagem)
        self.status = status


def _deve_repetir(exc: BaseException) -> bool:
    if isinstance(exc, (requests.ConnectionError, requests.Timeout, ftplib.error_temp, EOFError, ConnectionError)):
        return True
    if isinstance(exc, ErroHttp) and exc.status is not None:
        return exc.status == 429 or exc.status >= 500
    return False


_politica_retry = dict(
    retry=retry_if_exception(_deve_repetir),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)


def sessao() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = user_agent()
    s.headers["Accept-Language"] = "pt-BR,pt;q=0.9"
    adaptador = HTTPAdapter(pool_connections=4, pool_maxsize=4)
    s.mount("https://", adaptador)
    s.mount("http://", adaptador)
    return s


_SESSAO: requests.Session | None = None


def _sessao_global() -> requests.Session:
    global _SESSAO
    if _SESSAO is None:
        _SESSAO = sessao()
    return _SESSAO


def _pausar(host: str) -> None:
    pausa = configuracoes().pausa_entre_chamadas
    antes = _ultima_chamada.get(host)
    if antes is not None:
        falta = pausa - (time.monotonic() - antes)
        if falta > 0:
            time.sleep(falta)
    _ultima_chamada[host] = time.monotonic()


@retry(**_politica_retry)
def obter(url: str, params: dict | None = None, *, metodo: str = "GET", dados=None,
          cabecalhos: dict | None = None, timeout: int | None = None) -> requests.Response:
    """Requisição com pausa por host, timeout e retry. Levanta ErroHttp se status >= 400."""
    _pausar(urlparse(url).netloc)
    resp = _sessao_global().request(
        metodo, url, params=params, data=dados, headers=cabecalhos,
        timeout=timeout or configuracoes().timeout_http,
    )
    if resp.status_code >= 400:
        raise ErroHttp(f"HTTP {resp.status_code} em {resp.url}", resp.status_code)
    return resp


def obter_json(url: str, params: dict | None = None, **kw):
    return obter(url, params=params, **kw).json()


def obter_texto(url: str, params: dict | None = None, encoding: str | None = None, **kw) -> str:
    resp = obter(url, params=params, **kw)
    if encoding:
        resp.encoding = encoding
    return resp.text


@dataclass
class ArquivoBaixado:
    url: str
    caminho: Path
    sha256: str
    tamanho: int
    status: int
    last_modified: str | None = None
    etag: str | None = None
    reaproveitado: bool = False


def _sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


@retry(**_politica_retry)
def baixar(url: str, destino: Path, *, params: dict | None = None, metodo: str = "GET",
           dados=None, cabecalhos: dict | None = None) -> ArquivoBaixado:
    """Baixa ``url`` em streaming para ``destino`` (http, https ou ftp)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(destino.suffix + ".parcial")
    if url.startswith("ftp://"):
        return _baixar_ftp(url, destino, temporario)
    _pausar(urlparse(url).netloc)
    h = hashlib.sha256()
    tamanho = 0
    with _sessao_global().request(metodo, url, params=params, data=dados, headers=cabecalhos,
                                  stream=True, timeout=configuracoes().timeout_http) as resp:
        if resp.status_code >= 400:
            raise ErroHttp(f"HTTP {resp.status_code} em {url}", resp.status_code)
        with temporario.open("wb") as f:
            for bloco in resp.iter_content(chunk_size=1 << 20):
                if bloco:
                    f.write(bloco)
                    h.update(bloco)
                    tamanho += len(bloco)
        status = resp.status_code
        last_modified = resp.headers.get("Last-Modified")
        etag = resp.headers.get("ETag")
    esperado = resp.headers.get("Content-Length")
    if esperado and resp.headers.get("Content-Encoding") in (None, "", "identity") and int(esperado) != tamanho:
        temporario.unlink(missing_ok=True)
        raise ErroHttp(f"Download incompleto de {url}: {tamanho} de {esperado} bytes", 599)
    os.replace(temporario, destino)
    log.info("Arquivo baixado", url=url, bytes=tamanho)
    return ArquivoBaixado(url, destino, h.hexdigest(), tamanho, status, last_modified, etag)


def _baixar_ftp(url: str, destino: Path, temporario: Path) -> ArquivoBaixado:
    u = urlparse(url)
    h = hashlib.sha256()
    tamanho = 0
    with ftplib.FTP(u.hostname, timeout=configuracoes().timeout_http) as ftp:
        ftp.login()
        with temporario.open("wb") as f:
            def escrever(bloco: bytes) -> None:
                nonlocal tamanho
                f.write(bloco)
                h.update(bloco)
                tamanho += len(bloco)
            resposta = ftp.retrbinary(f"RETR {u.path}", escrever, blocksize=1 << 16)
    os.replace(temporario, destino)
    log.info("Arquivo baixado (FTP)", url=url, bytes=tamanho)
    return ArquivoBaixado(url, destino, h.hexdigest(), tamanho, int(resposta[:3]) if resposta[:3].isdigit() else 226)


@retry(**_politica_retry)
def consultar_cabecalhos(url: str) -> dict[str, str]:
    """HEAD no arquivo remoto: tamanho, Last-Modified e ETag, para decidir se precisa baixar de novo."""
    _pausar(urlparse(url).netloc)
    resp = _sessao_global().head(url, allow_redirects=True, timeout=configuracoes().timeout_http)
    if resp.status_code >= 400:
        raise ErroHttp(f"HTTP {resp.status_code} em {url}", resp.status_code)
    return {k: v for k, v in resp.headers.items()}


@retry(**_politica_retry)
def listar_ftp(url_diretorio: str) -> list[str]:
    """Lista os nomes de arquivo de um diretório FTP público."""
    u = urlparse(url_diretorio)
    with ftplib.FTP(u.hostname, timeout=configuracoes().timeout_http) as ftp:
        ftp.login()
        ftp.cwd(u.path)
        return ftp.nlst()


def registrar_arquivo_local(url: str, caminho: Path, status: int = 200) -> ArquivoBaixado:
    """Monta um ArquivoBaixado para um arquivo que já está no disco (ex.: resposta de API salva)."""
    return ArquivoBaixado(url, caminho, _sha256_arquivo(caminho), caminho.stat().st_size, status)


def salvar_bytes(url: str, conteudo: bytes, destino: Path, status: int = 200) -> ArquivoBaixado:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(destino.suffix + ".parcial")
    temporario.write_bytes(conteudo)
    os.replace(temporario, destino)
    return ArquivoBaixado(url, destino, hashlib.sha256(conteudo).hexdigest(), len(conteudo), status)
