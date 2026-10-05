"""Relatórios de texto: cobertura (indicador x ano, fonte x ano) e dicionário de dados.

* ``relatorio_cobertura`` lê a camada vigente e monta a matriz de cobertura em Markdown
  (impressa no terminal e, se pedido, gravada em arquivo).
* ``gerar_dicionario`` lê os COMMENT ON do banco (esquemas core, bi e etl) e escreve
  docs/dicionario_dados.md — o dicionário é gerado do banco, nunca escrito à mão.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

import psycopg

from observatorio import config
from observatorio.db import conectar


def _consulta(conn: psycopg.Connection, sql: str, params: tuple | None = None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _tabela_md(cabecalho: list[str], linhas: list[list]) -> str:
    saida = ["| " + " | ".join(cabecalho) + " |", "|" + "|".join("---" for _ in cabecalho) + "|"]
    for l in linhas:
        saida.append("| " + " | ".join("" if v is None else str(v) for v in l) + " |")
    return "\n".join(saida)


def relatorio_cobertura(territorio: str | None = None) -> str:
    territorio = territorio or config.territorios_alvo()[0]
    with conectar() as conn:
        nome = _consulta(conn, "SELECT nome FROM core.dim_territorio WHERE cod_territorio = %s", (territorio,))
        nome = nome[0][0] if nome else territorio
        anos = [r[0] for r in _consulta(conn, "SELECT ano FROM core.dim_tempo WHERE ano BETWEEN %s AND %s ORDER BY ano",
                                        (config.ano_inicial_padrao(), datetime.now().year))]
        indicadores = _consulta(conn, "SELECT cod_indicador, nome, cobertura FROM core.dim_indicador ORDER BY ordem")
        fatos = _consulta(conn, """
            SELECT cod_indicador, ano, count(*) FILTER (WHERE valor IS NOT NULL) AS com_valor, count(*) AS total,
                   bool_or(status_valor = 'estimado') AS estimado
            FROM core.v_fato_indicador WHERE cod_territorio = %s AND co_entidade IS NULL
            GROUP BY cod_indicador, ano""", (territorio,))
        mapa = {(c, a): (v, t, e) for c, a, v, t, e in fatos}
        linhas = []
        for cod, nome_ind, cobertura in indicadores:
            celulas = []
            for a in anos:
                v, t, e = mapa.get((cod, a), (0, 0, False))
                celulas.append(("E" if e else "V") if v else ("L" if t else "·"))
            if cobertura != "automatica" and not any(c in "VE" for c in celulas):
                celulas = ["M" if cobertura == "manual_futura" else "P"] * len(anos)
            linhas.append([cod, nome_ind[:60], *celulas])
        fontes = _consulta(conn, """
            SELECT a.id_fonte, string_agg(DISTINCT a.ano_referencia::text, ', ' ORDER BY a.ano_referencia::text),
                   count(*), max(a.data_coleta)::date, sum(a.tamanho_bytes)
            FROM etl.etl_arquivo a WHERE a.processado_em IS NOT NULL AND NOT a.arquivo_removido
            GROUP BY a.id_fonte ORDER BY a.id_fonte""")
        execucoes = _consulta(conn, """
            SELECT DISTINCT ON (id_fonte) id_fonte, job, status, inicio::timestamp(0), linhas_gravadas
            FROM etl.etl_execucao WHERE id_fonte IS NOT NULL ORDER BY id_fonte, inicio DESC""")
    partes = [
        f"# Cobertura dos dados - {nome} ({territorio})",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M}.",
        "",
        "Legenda: V = valor observado/publicado; E = valor com estimativa (ex.: denominador populacional); "
        "L = registrado como lacuna (sem_dado / não se aplica); · = nada carregado para o ano; "
        "P = fonte pendente; M = coleta manual (etapa futura).",
        "",
        _tabela_md(["Indicador", "Nome", *[str(a) for a in anos]], linhas),
        "",
        "## Arquivos processados por fonte",
        "",
        _tabela_md(["Fonte", "Anos", "Arquivos", "Última coleta", "Bytes"], [list(f) for f in fontes]),
        "",
        "## Última execução por fonte",
        "",
        _tabela_md(["Fonte", "Tarefa", "Status", "Início", "Linhas gravadas"], [list(e) for e in execucoes]),
    ]
    return "\n".join(partes) + "\n"


def gerar_dicionario(destino: Path | None = None) -> Path:
    destino = destino or (config.DIR_DOCS / "dicionario_dados.md")
    with conectar() as conn:
        objetos = _consulta(conn, """
            SELECT n.nspname, c.relname, CASE c.relkind WHEN 'r' THEN 'tabela' WHEN 'v' THEN 'view'
                   WHEN 'm' THEN 'view materializada' ELSE c.relkind::text END,
                   obj_description(c.oid, 'pg_class')
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname IN ('bi', 'core', 'etl', 'staging', 'raw') AND c.relkind IN ('r', 'v', 'm')
            ORDER BY array_position(ARRAY['bi', 'core', 'etl', 'staging', 'raw'], n.nspname::text), c.relname""")
        colunas = _consulta(conn, """
            SELECT n.nspname, c.relname, a.attname, format_type(a.atttypid, a.atttypmod), NOT a.attnotnull,
                   col_description(c.oid, a.attnum)
            FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname IN ('bi', 'core', 'etl', 'staging', 'raw') AND c.relkind IN ('r', 'v', 'm')
              AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY n.nspname, c.relname, a.attnum""")
        esquemas = dict(_consulta(conn, """SELECT nspname, obj_description(oid, 'pg_namespace') FROM pg_namespace
                                            WHERE nspname IN ('bi', 'core', 'etl', 'staging', 'raw')"""))
    por_obj = defaultdict(list)
    for esq, rel, col, tipo, nulo, desc in colunas:
        por_obj[(esq, rel)].append((col, tipo, "sim" if nulo else "não", desc or ""))
    linhas = [
        "# Dicionário de dados",
        "",
        "Gerado automaticamente a partir dos comentários do banco (`COMMENT ON`) pelo comando "
        "`python -m observatorio docs dicionario`. Não edite à mão: altere o comentário na migration ou na "
        "view e gere de novo.",
        "",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M}.",
        "",
    ]
    esquema_atual = None
    for esq, rel, tipo, desc in objetos:
        if esq != esquema_atual:
            esquema_atual = esq
            linhas += [f"## Esquema `{esq}`", "", esquemas.get(esq) or "", ""]
        linhas += [f"### `{esq}.{rel}` ({tipo})", "", desc or "*(sem descrição)*", ""]
        cols = por_obj.get((esq, rel), [])
        if esq in ("staging", "raw") and not any(c[3] for c in cols):
            linhas += ["Colunas: " + ", ".join(f"`{c[0]}`" for c in cols), ""]
            continue
        linhas += [_tabela_md(["Coluna", "Tipo", "Aceita nulo", "Descrição"],
                              [[f"`{c}`", t, n, d.replace("|", "/")] for c, t, n, d in cols]), ""]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas), encoding="utf-8")
    return destino
