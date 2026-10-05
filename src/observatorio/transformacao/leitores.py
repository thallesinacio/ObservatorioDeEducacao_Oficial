"""Leitores de arquivos grandes, com memória baixa.

* ``ler_xlsx``: lê uma aba de XLSX em streaming (lxml.iterparse), linha a linha, devolvendo os
  valores como texto exatamente como estão no arquivo. Planilhas do INEP chegam a 1 GB de XML;
  openpyxl ou pandas carregariam tudo em memória.
* ``ler_csv_em_blocos``: CSV nacional do Censo Escolar lido em blocos, filtrando municípios já
  na leitura, com separador e encoding detectados.
* ``membro_zip``: localiza um arquivo dentro de um ZIP por expressão regular (nomes mudam entre
  anos e às vezes vêm com encoding quebrado).
"""

from __future__ import annotations

import csv
import io
import re
import shutil
import zipfile
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

import pandas as pd
from lxml import etree

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_COL = re.compile(r"^([A-Z]+)")


class ErroLeitura(RuntimeError):
    pass


# ------------------------------------------------------------------ ZIP

def _nome_legivel(info: zipfile.ZipInfo) -> str:
    """Nomes de ZIP do INEP às vezes vêm em cp437 sem a flag UTF-8; tenta reparar."""
    nome = info.filename
    if not (info.flag_bits & 0x800):
        try:
            nome = nome.encode("cp437").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                nome = nome.encode("cp437").decode("cp850")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
    return nome


def listar_membros(caminho_zip: Path) -> list[tuple[str, zipfile.ZipInfo]]:
    with zipfile.ZipFile(caminho_zip) as z:
        return [(_nome_legivel(i), i) for i in z.infolist() if not i.is_dir()]


def membro_zip(caminho_zip: Path, padrao: str, obrigatorio: bool = True) -> zipfile.ZipInfo | None:
    """Primeiro membro cujo nome (sem pasta) casa com ``padrao`` (regex, sem diferenciar maiúsculas).

    Ignora arquivos temporários do Office (~$...).
    """
    rx = re.compile(padrao, re.IGNORECASE)
    candidatos = [
        info for nome, info in listar_membros(caminho_zip)
        if rx.search(PurePosixPath(nome).name) and not PurePosixPath(nome).name.startswith("~$")
    ]
    if not candidatos:
        if obrigatorio:
            nomes = ", ".join(n for n, _ in listar_membros(caminho_zip))
            raise ErroLeitura(f"Nenhum arquivo casa com /{padrao}/ em {caminho_zip.name}. Conteúdo: {nomes}")
        return None
    return candidatos[0]


def extrair_membro(caminho_zip: Path, info: zipfile.ZipInfo, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(caminho_zip) as z, z.open(info) as origem, destino.open("wb") as f:
        shutil.copyfileobj(origem, f, length=1 << 20)
    return destino


# ------------------------------------------------------------------ XLSX

def _indice_coluna(ref: str) -> int:
    letras = _COL.match(ref).group(1)
    n = 0
    for ch in letras:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def abas_xlsx(caminho: Path) -> dict[str, str]:
    """Mapa nome da aba -> caminho interno do XML da aba."""
    with zipfile.ZipFile(caminho) as z:
        wb = etree.fromstring(z.read("xl/workbook.xml"))
        rels = etree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    alvo = {r.get("Id"): r.get("Target") for r in rels}
    abas = {}
    for s in wb.iter(f"{_NS}sheet"):
        rid = s.get(f"{_NS_REL}id")
        t = alvo.get(rid, "")
        t = t.lstrip("/")
        if not t.startswith("xl/"):
            t = "xl/" + t
        abas[s.get("name")] = t
    return abas


def _strings_compartilhadas(z: zipfile.ZipFile) -> list[str]:
    try:
        f = z.open("xl/sharedStrings.xml")
    except KeyError:
        return []
    valores: list[str] = []
    with f:
        for _, el in etree.iterparse(f, events=("end",), tag=f"{_NS}si"):
            valores.append("".join(t.text or "" for t in el.iter(f"{_NS}t")))
            el.clear()
    return valores


def ler_xlsx(caminho: Path, aba: str | None = None) -> Iterator[list[str | None]]:
    """Gera as linhas de uma aba (primeira aba se ``aba`` for None).

    Cada linha é uma lista de textos (None para célula vazia), já alinhada pelas referências
    de coluna (A, B, ...). Números saem como estão no XML (ex.: '40.799999999999997').
    Linhas totalmente vazias intermediárias são devolvidas como listas vazias, para preservar
    a posição do cabeçalho.
    """
    abas = abas_xlsx(caminho)
    if aba is None:
        interno = next(iter(abas.values()))
    elif aba in abas:
        interno = abas[aba]
    else:
        raise ErroLeitura(f"Aba '{aba}' não existe em {caminho.name}. Abas: {list(abas)}")
    with zipfile.ZipFile(caminho) as z:
        ss = _strings_compartilhadas(z)
        with z.open(interno) as f:
            ultima = 0
            for _, row in etree.iterparse(f, events=("end",), tag=f"{_NS}row"):
                r = int(row.get("r") or (ultima + 1))
                while ultima + 1 < r:
                    ultima += 1
                    yield []
                ultima = r
                celulas: dict[int, str | None] = {}
                for c in row.iter(f"{_NS}c"):
                    ref = c.get("r")
                    tipo = c.get("t")
                    if tipo == "inlineStr":
                        val = "".join(t.text or "" for t in c.iter(f"{_NS}t"))
                    else:
                        v = c.find(f"{_NS}v")
                        val = v.text if v is not None else None
                        if val is not None and tipo == "s":
                            val = ss[int(val)]
                    if ref is None:
                        idx = len(celulas)
                    else:
                        idx = _indice_coluna(ref)
                    celulas[idx] = val
                row.clear()
                while row.getprevious() is not None:
                    del row.getparent()[0]
                if not celulas:
                    yield []
                    continue
                linha = [None] * (max(celulas) + 1)
                for i, v in celulas.items():
                    linha[i] = v
                yield linha


# ------------------------------------------------------------------ CSV

def detectar_formato_csv(amostra: bytes) -> tuple[str, str]:
    """Detecta (encoding, separador) a partir dos primeiros bytes."""
    encoding = "utf-8"
    try:
        amostra.decode("utf-8")
    except UnicodeDecodeError:
        encoding = "latin-1"
    if amostra.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
    texto = amostra.decode(encoding, errors="replace")
    primeira = texto.splitlines()[0] if texto else ""
    contagem = {sep: primeira.count(sep) for sep in (";", ",", "|", "\t")}
    separador = max(contagem, key=contagem.get)
    if contagem[separador] == 0:
        raise ErroLeitura("Não foi possível detectar o separador do CSV")
    return encoding, separador


def cabecalho_csv(caminho_zip: Path, info: zipfile.ZipInfo) -> tuple[list[str], str, str]:
    with zipfile.ZipFile(caminho_zip) as z, z.open(info) as f:
        amostra = f.read(256 * 1024)
    encoding, sep = detectar_formato_csv(amostra)
    primeira = amostra.decode(encoding, errors="replace").splitlines()[0]
    colunas = next(csv.reader([primeira], delimiter=sep))
    return [c.strip() for c in colunas], encoding, sep


def ler_csv_em_blocos(
    caminho_zip: Path,
    info: zipfile.ZipInfo,
    coluna_filtro: str,
    valores_filtro: set[str],
    tamanho_bloco: int = 50_000,
) -> Iterator[pd.DataFrame]:
    """Lê um CSV dentro do ZIP em blocos, devolvendo só as linhas cujo ``coluna_filtro`` está em
    ``valores_filtro``. Todas as colunas como texto (dtype=str), vazio vira None."""
    colunas, encoding, sep = cabecalho_csv(caminho_zip, info)
    if coluna_filtro not in colunas:
        raise ErroLeitura(f"Coluna {coluna_filtro} não existe em {info.filename}")
    with zipfile.ZipFile(caminho_zip) as z, z.open(info) as bruto:
        texto = io.TextIOWrapper(bruto, encoding=encoding, newline="")
        leitor = pd.read_csv(
            texto, sep=sep, dtype=str, chunksize=tamanho_bloco, keep_default_na=False,
            na_values=[], quoting=csv.QUOTE_MINIMAL, engine="c", low_memory=True,
        )
        numero_linha = 0
        for bloco in leitor:
            bloco.columns = [c.strip() for c in bloco.columns]
            bloco.insert(0, "__linha__", range(numero_linha + 1, numero_linha + 1 + len(bloco)))
            numero_linha += len(bloco)
            filtrado = bloco[bloco[coluna_filtro].str.strip().isin(valores_filtro)]
            if len(filtrado):
                yield filtrado.replace({"": None})
