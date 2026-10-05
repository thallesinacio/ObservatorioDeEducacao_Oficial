"""Interpretação dos cabeçalhos das planilhas do INEP.

As planilhas de Indicadores Educacionais, Sinopse e Ideb têm cabeçalho em várias linhas com
células mescladas (o texto aparece só na primeira célula do grupo) e, em parte dos anos, uma
linha extra com códigos de variável (NU_ANO_CENSO, FUN_CAT_0, 1_CAT_FUN_AI...). Os códigos mudam
de ano para ano (2015 não tem essa linha no arquivo de rendimento), então a identificação da
medida e da etapa usa o TEXTO do cabeçalho, que é estável. O código, quando existe, é guardado
como ``coluna_origem`` para rastreabilidade.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from observatorio.transformacao.normalizacao import normalizar_rotulo, texto_limpo

_CODIGO = re.compile(r"^[A-Za-z0-9]+(_[A-Za-z0-9]+)+$|^[A-Z]{2,}[A-Z0-9]*$")
_ANO = re.compile(r"^(19|20)\d{2}(\.0)?$")


@dataclass
class Coluna:
    indice: int
    rotulo: str          # texto hierárquico, ex.: "Taxa de Aprovação > Ensino Médio > 1ª série"
    codigo: str | None   # código da linha de variáveis, se houver
    partes: tuple[str, ...]

    @property
    def rotulo_norm(self) -> str:
        return normalizar_rotulo(self.rotulo)

    @property
    def nome_origem(self) -> str:
        return self.codigo or self.rotulo


def _eh_linha_de_codigos(linha: list) -> bool:
    valores = [str(v).strip() for v in linha if v not in (None, "")]
    if len(valores) < 3:
        return False
    codigos = [v for v in valores if _CODIGO.match(v)]
    return len(codigos) / len(valores) >= 0.8 and any("_" in v for v in codigos)


def eh_linha_de_dados(linha: list) -> bool:
    """Linha de dados começa com um ano (ou tem código de município/escola nas primeiras colunas)."""
    valores = [str(v).strip() for v in linha[:6] if v not in (None, "")]
    if not valores:
        return False
    if _ANO.match(valores[0]):
        return True
    # Sinopse Estatística: a primeira linha de dados é "Brasil" seguida de números.
    if normalizar_rotulo(valores[0]) == "brasil":
        numeros = [v for v in linha[1:] if v not in (None, "") and re.fullmatch(r"-?\d+([.,]\d+)?", str(v).strip())]
        return len(numeros) >= 2
    return any(re.fullmatch(r"\d{7}(\.0)?|\d{8}(\.0)?", v) for v in valores[:4])


_RX_INICIO_CABECALHO = re.compile(
    r"^(ano|sigla( da uf)?|uf|codigo do municipio|codigo da escola|brasil|regiao|regiao geografica|"
    r"unidade da federacao|unidade geografica|unidade geografica \(unidgeo\)|nu_ano_censo|sg_uf)$"
)


def localizar_cabecalho(linhas: list[list], max_busca: int = 40) -> tuple[int, int]:
    """Devolve (inicio, fim_exclusivo) do bloco de cabeçalho.

    Início: primeira linha cujo primeiro rótulo é de identificação (Ano, Sigla da UF, Código do
    Município, Brasil...). Fim: a linha seguinte à linha de códigos de variável, se houver; senão,
    a primeira linha de dados (começa com ano ou tem código de município/escola).
    """
    inicio = None
    for i, linha in enumerate(linhas[:max_busca]):
        primeiros = [normalizar_rotulo(v) for v in linha[:3] if v not in (None, "")]
        if inicio is None:
            if primeiros and _RX_INICIO_CABECALHO.match(primeiros[0]):
                inicio = i
            continue
        if _eh_linha_de_codigos(linha):
            return inicio, i + 1
        if eh_linha_de_dados(linha):
            return inicio, i
    raise ValueError("Cabeçalho não encontrado nas primeiras linhas da planilha")


def montar_colunas(bloco: list[list]) -> list[Coluna]:
    """Monta o rótulo hierárquico de cada coluna a partir das linhas do cabeçalho.

    Células mescladas deixam o texto só na primeira coluna do grupo. O texto é propagado para as
    colunas vazias seguintes, mas só enquanto o grupo da linha de cima for o mesmo (não atravessa
    para o grupo vizinho).
    """
    codigos: list | None = None
    niveis: list[list] = []
    for linha in bloco:
        if not any(v not in (None, "") for v in linha):
            continue
        if _eh_linha_de_codigos(linha):
            codigos = linha
            continue
        niveis.append(linha)
    largura = max([len(x) for x in niveis] + [len(codigos or [])] + [0])
    preenchidos: list[list[str]] = []
    for n, linha in enumerate(niveis):
        pai = preenchidos[n - 1] if n else None
        cheio: list[str] = []
        for i in range(largura):
            v = texto_limpo(linha[i]) if i < len(linha) else None
            if v:
                cheio.append(v)
                continue
            mesmo_grupo = i > 0 and (pai is None or pai[i] == pai[i - 1])
            if mesmo_grupo and cheio and cheio[i - 1] and (n > 0 or _grupo_de_valores(linha, i)):
                cheio.append(cheio[i - 1])
            else:
                cheio.append("")
        preenchidos.append(cheio)
    # Colunas vazias à direita da tabela (célula formatada, sem texto próprio em nenhuma linha do
    # cabeçalho nem código) não são dados: sem este corte, elas herdariam o rótulo do último grupo
    # ("... > Não-Seriado") e duplicariam a coluna verdadeira.
    ultima = -1
    for i in range(largura):
        tem_texto = any(i < len(linha) and texto_limpo(linha[i]) for linha in niveis)
        tem_codigo = bool(codigos and i < len(codigos) and texto_limpo(codigos[i]))
        if tem_texto or tem_codigo:
            ultima = i
    largura = ultima + 1
    colunas = []
    for i in range(largura):
        partes: list[str] = []
        for nivel in preenchidos:
            p = nivel[i]
            if p and (not partes or partes[-1] != p):
                partes.append(p)
        cod = texto_limpo(codigos[i]) if codigos and i < len(codigos) else None
        rotulo = " > ".join(partes) if partes else (cod or f"coluna_{i + 1}")
        colunas.append(Coluna(i, rotulo, cod, tuple(partes)))
    return colunas


def _grupo_de_valores(linha: list, i: int) -> bool:
    """Na primeira linha do cabeçalho, só propaga para a direita a partir do primeiro grupo que
    não é de identificação (evita que "Dependência Administrativa" vire rótulo de colunas de dado
    quando a planilha não tem título de grupo)."""
    anterior = None
    for j in range(i - 1, -1, -1):
        if j < len(linha) and linha[j] not in (None, ""):
            anterior = normalizar_rotulo(linha[j])
            break
    if anterior is None:
        return False
    return not any(rx.search(anterior) for _, rx in _ID)


# ------------------------------------------------------------------ identificação de colunas

_ID = [
    ("ano", re.compile(r"^(ano|nu_ano_censo)$")),
    ("cod_municipio", re.compile(r"(codigo do municipio|^co_municipio$|^pk_cod_municipio$)")),
    ("cod_escola", re.compile(r"(codigo da escola|codigo da entidade|^co_entidade$|^id_escola$|^co_escola$)")),
    ("sg_uf", re.compile(r"^(sigla( da uf)?|uf|sg_uf|sigla)$")),
    ("cod_uf", re.compile(r"^(codigo da uf|co_uf)$")),
    ("localizacao", re.compile(r"^(localizacao|tipoloca|no_categoria)$")),
    ("rede", re.compile(r"^(dependencia administrativa|rede|dependad|no_dependencia)$")),
    ("unidade", re.compile(r"^(brasil|unidade da federacao|unidade geografica|unidade geografica \(unidgeo\)|unidgeo|regiao|"
                            r"regiao geografica|no_regiao|brasil / regiao / uf|abrangencia)$")),
    ("nome_municipio", re.compile(r"^(nome do municipio|municipio|no_municipio|no_cod)$")),
    ("nome_escola", re.compile(r"^(nome da escola|no_entidade|escola)$")),
]


def papel_da_coluna(col: Coluna) -> str | None:
    """Identifica colunas de identificação pelo texto (ou código) do cabeçalho."""
    # O texto vale mais que o código: em 2016 o INEP trocou os códigos TIPOLOCA/Dependad entre as
    # colunas "Localização" e "Dependência Administrativa" do arquivo de UFs.
    candidatos = [normalizar_rotulo(col.partes[0]) if col.partes else "", normalizar_rotulo(col.codigo or "")]
    for c in candidatos:
        if not c:
            continue
        for papel, rx in _ID:
            if rx.search(c):
                return papel
    return None


# ------------------------------------------------------------------ etapa e medida

_ETAPAS = [
    ("fund_ai", re.compile(r"anos iniciais|1o ao 5o")),
    ("fund_af", re.compile(r"anos finais|6o ao 9o")),
    ("fund_ano_{n}", re.compile(r"\b([1-9])o ano\b|^([1-9])o$|> ([1-9])o$")),
    ("med_serie_{n}", re.compile(r"\b([1-4])a serie\b")),
    ("med_ns", re.compile(r"nao[ -]seriado")),
    ("fund_multi", re.compile(r"multietapa|multi ou correcao")),
    ("inf_cre", re.compile(r"\bcreche\b")),
    ("inf_pre", re.compile(r"pre-?escola")),
    ("eja_fund", re.compile(r"(eja|jovens e adultos).*fundamental")),
    ("eja_med", re.compile(r"(eja|jovens e adultos).*medio")),
    ("eja", re.compile(r"\beja\b|jovens e adultos")),
    ("prof", re.compile(r"educacao profissional")),
    ("esp", re.compile(r"educacao especial")),
    ("inf", re.compile(r"educacao infantil")),
    ("fund", re.compile(r"ens(ino|\.)\s*fundamental|\bfundamental\b")),
    ("med", re.compile(r"ens(ino|\.)\s*medio|\bmedio\b")),
    ("bas", re.compile(r"educacao basica")),
]


def classificar_etapa(rotulo: str) -> str | None:
    t = normalizar_rotulo(rotulo)
    for codigo, rx in _ETAPAS:
        m = rx.search(t)
        if m:
            if "{n}" in codigo:
                n = next(g for g in m.groups() if g)
                return codigo.format(n=n)
            return codigo
    return None


def classificar_medida_rendimento(rotulo: str) -> str | None:
    t = normalizar_rotulo(rotulo)
    if "reprova" in t:
        return "reprovacao"
    if "aprova" in t:
        return "aprovacao"
    if "abandono" in t:
        return "abandono"
    return None


def grupo_afd(rotulo: str) -> str | None:
    m = re.search(r"grupo\s*([1-5])", normalizar_rotulo(rotulo))
    return m.group(1) if m else None


# ------------------------------------------------------------------ etapa pelo código de variável
# Família de códigos usada pelo INEP desde ~2019 nas planilhas de Indicadores Educacionais:
# FUN_CAT_0, FUN_AI_CAT_0, FUN_01_CAT_0, MED_NS_CAT_0, 1_CAT_FUN_AI, ED_INF_CAT_3, EDU_BAS_CAT_0...
_RX_CODIGO_ETAPA = re.compile(
    r"^(?:\d_CAT_)?(ED_INF|CRE|PRE|EJA_FUN|EJA_MED|FUN|MED|PROF|EJA|EDU_BAS|MULT_ETA|ESP)"
    r"(?:_(AI|AF|0[1-9]|NS))?(?:_CAT_\d)?$"
)
_BASE_CODIGO = {
    "ED_INF": "inf", "CRE": "inf_cre", "PRE": "inf_pre", "FUN": "fund", "MED": "med", "PROF": "prof",
    "EJA": "eja", "EJA_FUN": "eja_fund", "EJA_MED": "eja_med", "EDU_BAS": "bas", "MULT_ETA": "fund_multi",
    "ESP": "esp",
}


def etapa_por_codigo(codigo: str | None) -> str | None:
    if not codigo:
        return None
    m = _RX_CODIGO_ETAPA.match(codigo.strip().upper())
    if not m:
        return None
    base, sufixo = m.group(1), m.group(2)
    etapa = _BASE_CODIGO[base]
    if sufixo is None:
        return etapa
    if sufixo in ("AI", "AF"):
        return f"fund_{sufixo.lower()}" if base == "FUN" else None
    if sufixo == "NS":
        return "med_ns" if base == "MED" else None
    n = int(sufixo)
    if base == "FUN":
        return f"fund_ano_{n}"
    if base == "MED":
        return f"med_serie_{n}"
    return None


@dataclass
class EtapaIdentificada:
    etapa: str | None
    pelo_rotulo: str | None
    pelo_codigo: str | None

    @property
    def divergente(self) -> bool:
        return bool(self.pelo_rotulo and self.pelo_codigo and self.pelo_rotulo != self.pelo_codigo)


def identificar_etapa(col: Coluna) -> EtapaIdentificada:
    """Etapa da coluna: vale o código de variável quando ele segue o padrão conhecido (é a
    especificação legível por máquina); senão, o texto do cabeçalho. Divergências entre os dois
    são devolvidas para virar alerta de qualidade (ex.: DSU 2024 rotula "Educação Especial" a
    coluna de código EDU_BAS_CAT_0)."""
    pelo_rotulo = classificar_etapa(col.rotulo)
    pelo_codigo = etapa_por_codigo(col.codigo)
    return EtapaIdentificada(pelo_codigo or pelo_rotulo, pelo_rotulo, pelo_codigo)


def grupo_afd_da_coluna(col: Coluna) -> str | None:
    """Grupo do AFD lido só do nível mais baixo do cabeçalho (o título tem notas como 'grupo4')."""
    return grupo_afd(col.partes[-1]) if col.partes else None
