"""Estimativas populacionais por município, idade simples e sexo (RIPSA / Ministério da Saúde).

Denominador das taxas de atendimento (A1 a A4). Dois caminhos, nesta ordem:

1. FTP do DATASUS (``ftp://ftp.datasus.gov.br/dissemin/publicos/IBGE/POPSVS/``): um ZIP com DBF
   por ano (POPSBR<aa>.zip). O diretório é listado antes de baixar e o DBF é validado pelos nomes
   das colunas; se algo não bater (ou o FTP estiver fora do ar), cai no caminho 2.
2. TabNet (``tabcgi.exe?ibge/cnv/popsvs2024br.def``): a mesma base, consultada pelo formulário
   público com Linha = Idade simples, Coluna = Ano e filtro por município. A resposta é uma tabela
   em texto separada por ";" dentro de <PRE>. Verificado em 29/09/2026.

Só a população TOTAL (os dois sexos) por idade simples é gravada: é o que os indicadores usam e
evita depender da codificação de sexo do DBF, que não pôde ser verificada. 80 = 80 anos ou mais.
Todo valor é estimativa (status "estimado" nos indicadores); a edição fica gravada.
"""

from __future__ import annotations

import html as html_lib
import re
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode, urljoin

import psycopg
from bs4 import BeautifulSoup

from observatorio import config
from observatorio.carga.dimensoes import id_fonte_numerico
from observatorio.coleta.base import Contexto, Fonte, gravar_raw
from observatorio.db import copiar_linhas
from observatorio.execucao import ArquivoRegistrado, registrar_arquivo
from observatorio.http import listar_ftp, obter, obter_texto, salvar_bytes
from observatorio.log import obter_logger
from observatorio.transformacao.leitores import ErroLeitura
from observatorio.transformacao.normalizacao import codigo_municipio_6, normalizar_rotulo

log = obter_logger(__name__)

DIR_FTP = "ftp://ftp.datasus.gov.br/dissemin/publicos/IBGE/POPSVS/"
_RX_ZIP_FTP = re.compile(r"^POPSBR(\d{2})\.zip$", re.IGNORECASE)


# ------------------------------------------------------------------ TabNet

def interpretar_tabnet(texto: str) -> tuple[str, dict[int, dict[int, int | None]], dict[int, int]]:
    """Lê a resposta do TabNet (Linha = idade simples, Coluna = ano).

    Devolve (titulo, {ano: {idade: pop}}, {ano: total publicado}).
    """
    sopa = BeautifulSoup(texto, "html.parser")
    titulo = sopa.find(["h1", "H1"])
    titulo_txt = html_lib.unescape(titulo.get_text(" ", strip=True)) if titulo else ""
    pre = sopa.find("pre")
    if pre is None:
        raise ErroLeitura("Resposta do TabNet sem bloco <PRE> (a consulta pode ter falhado)")
    linhas = [l.strip() for l in pre.get_text().splitlines() if l.strip() and l.strip() != "&"]
    cab = [c.strip().strip('"') for c in linhas[0].split(";")]
    anos = [int(c) for c in cab[1:]]
    por_ano: dict[int, dict[int, int | None]] = {a: {} for a in anos}
    totais: dict[int, int] = {}
    for l in linhas[1:]:
        cels = [c.strip().strip('"') for c in l.split(";")]
        rotulo = normalizar_rotulo(cels[0])
        valores = []
        for c in cels[1:]:
            c = c.replace(".", "")
            valores.append(0 if c == "-" else (int(c) if c.isdigit() else None))
        if rotulo == "total":
            totais = {a: v for a, v in zip(anos, valores) if v is not None}
            continue
        idade = idade_tabnet(rotulo)
        if idade is None:
            raise ErroLeitura(f"Linha de idade não reconhecida no TabNet: {cels[0]!r}")
        for a, v in zip(anos, valores):
            por_ano[a][idade] = v
    return titulo_txt, por_ano, totais


def idade_tabnet(rotulo: str) -> int | None:
    t = normalizar_rotulo(rotulo)
    if t.startswith("menos que 1 ano") or t.startswith("menos de 1 ano"):
        return 0
    m = re.fullmatch(r"(\d+)\s+anos?( e mais| ou mais)?", t)
    return int(m.group(1)) if m else None


def edicao_do_titulo(titulo: str) -> str:
    m = re.search(r"(\d{4})\s*-\s*(\d{4})", titulo)
    return f"RIPSA {m.group(1)}-{m.group(2)}" if m else "RIPSA"


def montar_consulta_tabnet(html_def: str, url_def: str, cod6: str, anos: list[int]) -> tuple[str, bytes]:
    """Monta o POST do formulário do TabNet a partir da própria página (nomes e valores lidos dela)."""
    sopa = BeautifulSoup(html_def, "html.parser")
    form = sopa.find("form")
    if form is None:
        raise ErroLeitura("Página do TabNet sem formulário")
    acao = urljoin(url_def, form.get("action", ""))

    def opcoes(nome_rx: str):
        sel = sopa.find("select", attrs={"name": re.compile(nome_rx)})
        if sel is None:
            raise ErroLeitura(f"Campo {nome_rx} não encontrado no formulário do TabNet")
        return sel["name"], [(o.get("value"), o.get_text(" ", strip=True), o.has_attr("selected")) for o in sel.find_all("option")]

    _, linha = opcoes("^Linha$")
    _, coluna = opcoes("^Coluna$")
    _, incremento = opcoes("^Incremento$")
    _, arquivos = opcoes("^Arquivos$")
    nome_mun, municipios = opcoes("^SMunic")
    v_linha = next((v for v, t, _ in linha if normalizar_rotulo(t) == "idade simples"), None)
    v_coluna = next((v for v, t, _ in coluna if normalizar_rotulo(t) == "ano"), None)
    v_incr = next((v for v, t, s in incremento if s), incremento[0][0] if incremento else None)
    v_mun = next((v for v, t, _ in municipios if t.startswith(cod6)), None)
    if not all([v_linha, v_coluna, v_incr]):
        raise ErroLeitura("Formulário do TabNet mudou: Linha 'Idade simples' ou Coluna 'Ano' não encontradas")
    if v_mun is None:
        raise ErroLeitura(f"Município {cod6} não está na lista do TabNet")
    arqs = [v for v, t, _ in arquivos if t.isdigit() and int(t) in anos]
    if not arqs:
        raise ErroLeitura(f"Nenhum dos anos {anos} está disponível no TabNet")
    campos = [("Linha", v_linha), ("Coluna", v_coluna), ("Incremento", v_incr)]
    campos += [("Arquivos", a) for a in arqs]
    campos.append((nome_mun, v_mun))
    for sel in sopa.find_all("select"):
        n = sel.get("name", "")
        if n.startswith("S") and n != nome_mun:
            campos.append((n, "TODAS_AS_CATEGORIAS__"))
    campos += [("formato", "prn"), ("mostre", "Mostra")]
    return acao, urlencode(campos, encoding="latin-1").encode("ascii")


# ------------------------------------------------------------------ DBF do FTP

def detectar_colunas_dbf(campos: list[str], amostra: list[dict]) -> dict[str, str] | None:
    """Identifica município, ano, idade e população pelo nome e pelo conteúdo. None se não der."""
    achados: dict[str, str] = {}
    for c in campos:
        cu = c.upper()
        valores = [str(r.get(c) or "").strip() for r in amostra]
        if "MUN" in cu and all(re.fullmatch(r"\d{6,7}", v) for v in valores if v):
            achados.setdefault("municipio", c)
        elif cu == "ANO" and all(re.fullmatch(r"\d{4}", v) for v in valores if v):
            achados.setdefault("ano", c)
        elif "IDADE" in cu or cu in ("FXETARIA", "FAIXA_ETA"):
            achados.setdefault("idade", c)
        elif cu.startswith("POP"):
            achados.setdefault("populacao", c)
    return achados if {"municipio", "ano", "idade", "populacao"} <= set(achados) else None


def ler_dbf_zip(caminho: Path, municipios6: set[str]) -> tuple[dict[tuple[str, int], dict[int, int]], list[dict]]:
    """Soma a população por (município, ano, idade) — os dois sexos juntos."""
    from dbfread import DBF

    with zipfile.ZipFile(caminho) as z, tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        nomes = [n for n in z.namelist() if n.lower().endswith(".dbf")]
        if not nomes:
            raise ErroLeitura(f"{caminho.name}: nenhum .dbf no ZIP")
        dbf_path = Path(z.extract(nomes[0], tmp))
        tabela = DBF(str(dbf_path), encoding="latin-1", load=False)
        campos = tabela.field_names
        amostra = []
        for r in tabela:
            amostra.append(dict(r))
            if len(amostra) >= 50:
                break
        col = detectar_colunas_dbf(campos, amostra)
        if col is None:
            raise ErroLeitura(f"{caminho.name}: colunas do DBF não reconhecidas: {campos}")
        soma: dict[tuple[str, int], dict[int, int]] = defaultdict(lambda: defaultdict(int))
        brutas = []
        for r in tabela:
            mun = str(r[col["municipio"]]).strip()[:6]
            if mun not in municipios6:
                continue
            idade_txt = re.sub(r"\D", "", str(r[col["idade"]]))
            if not idade_txt:
                continue
            ano, idade = int(r[col["ano"]]), int(idade_txt)
            soma[(mun, ano)][idade] += int(r[col["populacao"]] or 0)
            brutas.append({k: r[k] for k in campos})
    return soma, brutas


class PopulacaoDatasus(Fonte):
    id_fonte = "populacao_datasus"
    tabelas_core = ("core.fato_populacao",)
    versao_transformacao = "2026.09.1"

    # -------------------------------------------------------------- coleta
    def coletar(self, conn: psycopg.Connection, ctx: Contexto) -> list[ArquivoRegistrado]:
        anos_def = config.fonte(self.id_fonte)
        try:
            return self._coletar_ftp(conn, ctx)
        except Exception as e:  # FTP fora do ar, sem os anos pedidos ou DBF em formato inesperado
            ctx.alertar(f"FTP do DATASUS indisponível ou em formato inesperado ({type(e).__name__}: {e}); usando o TabNet")
        return self._coletar_tabnet(conn, ctx, anos_def["pagina_oficial"])

    def _coletar_ftp(self, conn: psycopg.Connection, ctx: Contexto) -> list[ArquivoRegistrado]:
        nomes = listar_ftp(DIR_FTP)
        por_ano = {}
        for n in nomes:
            m = _RX_ZIP_FTP.match(n.rsplit("/", 1)[-1])
            if m:
                por_ano[2000 + int(m.group(1))] = n.rsplit("/", 1)[-1]
        anos = [a for a in sorted(por_ano) if ctx.ano_desejado(a)]
        if not anos:
            raise ErroLeitura(f"Nenhum POPSBR<aa>.zip para os anos pedidos em {DIR_FTP}")
        registrados = []
        for ano in anos:
            url = DIR_FTP + por_ano[ano]
            arq = self.baixar_registrar(conn, ctx, url, ano, por_ano[ano], verificar_cabecalho=False,
                                        descricao="origem=ripsa_ftp")
            ler_dbf_zip(arq.caminho, {codigo_municipio_6(m) for m in config.municipios_de_interesse()})  # valida
            registrados.append(arq)
        return registrados

    def _coletar_tabnet(self, conn: psycopg.Connection, ctx: Contexto, url_def: str) -> list[ArquivoRegistrado]:
        html_def = obter_texto(url_def, encoding="latin-1")
        disponiveis = [int(t) for t in re.findall(r">\s*(\d{4})\s*<", html_def)]
        anos = sorted({a for a in disponiveis if ctx.ano_desejado(a)})
        if not anos:
            raise ErroLeitura("Nenhum ano pedido disponível no TabNet")
        registrados = []
        for cod7 in config.municipios_de_interesse():
            cod6 = codigo_municipio_6(cod7)
            acao, corpo = montar_consulta_tabnet(html_def, url_def, cod6, anos)
            resp = obter(acao, metodo="POST", dados=corpo,
                         cabecalhos={"Content-Type": "application/x-www-form-urlencoded"})
            url_reg = f"{acao}#municipio={cod6}&anos={anos[0]}-{anos[-1]}"
            baixado = salvar_bytes(url_reg, resp.content,
                                   self.pasta_ano(None) / f"tabnet_popsvs_{cod6}_{anos[0]}_{anos[-1]}.html",
                                   resp.status_code)
            registrados.append(registrar_arquivo(conn, self.id_fonte, None, baixado, id_execucao=ctx.id_execucao,
                                                 descricao=f"origem=ripsa_tabnet;municipio={cod7}"))
        return registrados

    # -------------------------------------------------------------- processamento
    def processar(self, conn: psycopg.Connection, arquivo: ArquivoRegistrado, ctx: Contexto) -> int:
        municipios = config.municipios_de_interesse()
        por6 = {codigo_municipio_6(m): m for m in municipios}
        linhas = []
        if arquivo.caminho.suffix.lower() == ".zip":
            origem, edicao = "ripsa_ftp", "RIPSA (FTP DATASUS POPSVS)"
            soma, brutas = ler_dbf_zip(arquivo.caminho, set(por6))
            gravar_raw(conn, arquivo.id_arquivo, "dbf", ((i + 1, b) for i, b in enumerate(brutas)))
            for (mun6, ano), idades in soma.items():
                for idade, pop in idades.items():
                    linhas.append((origem, edicao, ano, por6[mun6], "T", idade, pop, arquivo.id_arquivo))
        else:
            origem = "ripsa_tabnet"
            texto = arquivo.caminho.read_bytes().decode("latin-1")
            titulo, por_ano, totais = interpretar_tabnet(texto)
            edicao = edicao_do_titulo(titulo) + " (TabNet)"
            m = re.search(r"municipio=(\d{7})", arquivo.descricao or "")
            if not m:
                raise ErroLeitura(f"Arquivo do TabNet sem município na descrição: {arquivo.descricao}")
            cod7 = m.group(1)
            brutas = []
            for ano, idades in por_ano.items():
                soma = sum(v for v in idades.values() if v is not None)
                if ano in totais and totais[ano] != soma:
                    ctx.alertar(f"TabNet {cod7} {ano}: soma das idades ({soma}) difere do total publicado ({totais[ano]})")
                for idade, pop in idades.items():
                    linhas.append((origem, edicao, ano, cod7, "T", idade, pop, arquivo.id_arquivo))
                    brutas.append({"municipio": cod7, "ano": ano, "idade": idade, "populacao": pop})
            gravar_raw(conn, arquivo.id_arquivo, "tabnet", ((i + 1, b) for i, b in enumerate(brutas)))
        chaves = {(l[0], l[1], l[2], l[3]) for l in linhas}
        with conn.cursor() as cur:
            for origem_, edicao_, ano, terr in chaves:
                cur.execute("""DELETE FROM staging.populacao WHERE origem = %s AND edicao = %s AND ano = %s
                               AND cod_territorio = %s""", (origem_, edicao_, ano, terr))
        n = copiar_linhas(conn, "staging.populacao",
                          ["origem", "edicao", "ano", "cod_territorio", "sexo", "idade", "populacao", "id_arquivo"], linhas)
        ctx.execucao.linhas_gravadas += n
        return n

    def carregar_core(self, conn: psycopg.Connection, id_versao: int, ctx: Contexto) -> int:
        id_num = id_fonte_numerico(conn, self.id_fonte)
        with conn.cursor() as cur:
            # Mesmo (município, ano) vindo do FTP e do TabNet: fica o do arquivo processado por último.
            cur.execute(
                """INSERT INTO core.fato_populacao (ano, cod_territorio, sexo, idade, populacao, origem, edicao,
                       status_valor, id_fonte, id_versao, data_coleta)
                   SELECT DISTINCT ON (s.ano, s.cod_territorio, s.sexo, s.idade)
                          s.ano, s.cod_territorio, s.sexo, s.idade, s.populacao, s.origem, s.edicao,
                          CASE WHEN s.populacao IS NULL THEN 'sem_dado' ELSE 'estimado' END, %s, %s, a.data_coleta::date
                   FROM staging.populacao s JOIN etl.etl_arquivo a USING (id_arquivo)
                   JOIN core.dim_tempo t ON t.ano = s.ano
                   WHERE s.origem IN ('ripsa_ftp', 'ripsa_tabnet')
                   ORDER BY s.ano, s.cod_territorio, s.sexo, s.idade, a.processado_em DESC NULLS LAST, s.id_arquivo DESC""",
                (id_num, id_versao),
            )
            return cur.rowcount
