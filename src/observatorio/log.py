"""Logging estruturado.

Cada linha de log sai como ``chave=valor`` legível no terminal e também em JSON no arquivo
``data/logs/observatorio.log`` (uma linha por evento), para auditoria posterior.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

_CONFIGURADO = False


class _FormatoTerminal(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extras = getattr(record, "dados", None) or {}
        sufixo = " ".join(f"{k}={v}" for k, v in extras.items())
        hora = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        base = f"{hora} {record.levelname:<7} {record.name.replace('observatorio.', '')}: {record.getMessage()}"
        return f"{base}  {sufixo}" if sufixo else base


class _FormatoJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        doc = {
            "momento": datetime.fromtimestamp(record.created).isoformat(timespec="seconds"),
            "nivel": record.levelname,
            "modulo": record.name,
            "mensagem": record.getMessage(),
        }
        doc.update(getattr(record, "dados", None) or {})
        if record.exc_info:
            doc["excecao"] = self.formatException(record.exc_info)
        return json.dumps(doc, ensure_ascii=False, default=str)


def configurar_log(nivel: str = "INFO", dir_logs: Path | None = None) -> None:
    global _CONFIGURADO
    if _CONFIGURADO:
        return
    raiz = logging.getLogger("observatorio")
    raiz.setLevel(getattr(logging, nivel.upper(), logging.INFO))
    terminal = logging.StreamHandler(sys.stderr)
    terminal.setFormatter(_FormatoTerminal())
    raiz.addHandler(terminal)
    if dir_logs is not None:
        try:
            dir_logs.mkdir(parents=True, exist_ok=True)
            arquivo = logging.FileHandler(dir_logs / "observatorio.log", encoding="utf-8")
            arquivo.setFormatter(_FormatoJson())
            raiz.addHandler(arquivo)
        except OSError:
            pass
    raiz.propagate = False
    _CONFIGURADO = True


class LoggerEstruturado(logging.LoggerAdapter):
    """Permite ``log.info("mensagem", fonte="x", ano=2024)``."""

    def process(self, msg, kwargs):
        dados = {k: kwargs.pop(k) for k in list(kwargs) if k not in ("exc_info", "stack_info", "stacklevel", "extra")}
        kwargs["extra"] = {"dados": dados}
        return msg, kwargs


def obter_logger(nome: str) -> LoggerEstruturado:
    return LoggerEstruturado(logging.getLogger(nome), {})
