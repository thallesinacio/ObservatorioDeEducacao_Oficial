"""Linha de comando do Observatório.

Uso (Windows, macOS ou Linux, com o ambiente virtual ativo):

    python -m observatorio db migrar
    python -m observatorio fontes listar
    python -m observatorio coletar --fonte censo_escolar --ano 2024
    python -m observatorio coletar --todas --de 2015
    python -m observatorio transformar --fonte censo_escolar
    python -m observatorio indicadores calcular
    python -m observatorio qualidade testar
    python -m observatorio pipeline --de 2015
    python -m observatorio relatorio cobertura
    python -m observatorio docs dicionario
    python -m observatorio importar --fonte sinopse_estatistica --arquivo C:/Downloads/x.zip --ano 2024 --url <url>
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from observatorio import config

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Observatório da Educação de Juazeiro-BA - ETL")
db_app = typer.Typer(no_args_is_help=True, help="Banco de dados")
fontes_app = typer.Typer(no_args_is_help=True, help="Fontes de dados")
ind_app = typer.Typer(no_args_is_help=True, help="Indicadores")
rel_app = typer.Typer(no_args_is_help=True, help="Relatórios")
qual_app = typer.Typer(no_args_is_help=True, help="Qualidade do dado")
docs_app = typer.Typer(no_args_is_help=True, help="Documentação gerada")
app.add_typer(db_app, name="db")
app.add_typer(fontes_app, name="fontes")
app.add_typer(ind_app, name="indicadores")
app.add_typer(rel_app, name="relatorio")
app.add_typer(qual_app, name="qualidade")
app.add_typer(docs_app, name="docs")


def _utf8() -> None:
    # Terminal do Windows: evita erro ao imprimir acentos.
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


@app.callback()
def principal() -> None:
    _utf8()
    from observatorio.log import configurar_log

    cfg = config.configuracoes()
    configurar_log(cfg.nivel_log, cfg.caminho_dados / "logs")


def _ids_fontes(fonte: list[str] | None, todas: bool) -> list[str] | None:
    if todas:
        return None
    if not fonte:
        raise typer.BadParameter("Informe --fonte <id> (pode repetir) ou --todas.")
    return fonte


def _encerrar(resumo) -> None:
    typer.echo(resumo.texto())
    raise typer.Exit(resumo.codigo_saida)


# ------------------------------------------------------------------ db
@db_app.command("migrar")
def db_migrar(offline: bool = typer.Option(False, help="Não consultar a API de localidades do IBGE (usa o cache).")):
    """Cria/atualiza esquemas, tabelas, papéis, dimensões de referência e as views do bi."""
    from observatorio.pipeline import migrar

    r = migrar(offline=offline)
    typer.echo(f"Migrations aplicadas agora: {', '.join(r['migrations_aplicadas']) or 'nenhuma (já estava atualizado)'}")
    typer.echo("Referências: " + ", ".join(f"{k}={v}" for k, v in r["referencias"].items()))
    typer.echo(f"Views do bi recriadas: {r['views_bi']} arquivo(s)")


# ------------------------------------------------------------------ fontes
@fontes_app.command("listar")
def fontes_listar():
    """Lista as fontes configuradas e se já têm coletor."""
    from observatorio.coleta import ORDEM_PIPELINE, registro

    reg = registro()
    for f in config.fontes():
        estado = "coletor" if f["id"] in reg else ("derivada" if f.get("tipo_acesso") == "derivado" else "pendente")
        ordem = f"#{ORDEM_PIPELINE.index(f['id']) + 1}" if f["id"] in ORDEM_PIPELINE else "  "
        typer.echo(f"{ordem:>3} {f['id']:<22} {f.get('prioridade', ''):<3} {estado:<9} {f['nome']}")


# ------------------------------------------------------------------ coleta e transformação
@app.command("coletar")
def coletar(
    fonte: list[str] | None = typer.Option(None, "--fonte", "-f", help="Id da fonte (repita para várias)."),
    todas: bool = typer.Option(False, "--todas", help="Todas as fontes com coletor."),
    ano: list[int] | None = typer.Option(None, "--ano", "-a", help="Ano(s) específico(s)."),
    de: int = typer.Option(None, "--de", help="Ano inicial (padrão: config/projeto.yaml)."),
    forcar: bool = typer.Option(False, "--forcar", help="Baixa de novo mesmo se o arquivo remoto não mudou."),
):
    """Baixa os arquivos (ou consulta as APIs) e registra no manifesto. Não transforma."""
    from observatorio.pipeline import executar_fontes

    _encerrar(executar_fontes(_ids_fontes(fonte, todas), ano, de or config.ano_inicial_padrao(), forcar,
                              coletar=True, transformar=False))


@app.command("transformar")
def transformar(
    fonte: list[str] | None = typer.Option(None, "--fonte", "-f"),
    todas: bool = typer.Option(False, "--todas"),
    forcar: bool = typer.Option(False, "--forcar", help="Reprocessa os arquivos vigentes mesmo sem mudança."),
):
    """Processa os arquivos coletados (raw -> staging -> core) numa nova versão, se a entrada mudou."""
    from observatorio.pipeline import executar_fontes

    _encerrar(executar_fontes(_ids_fontes(fonte, todas), None, config.ano_inicial_padrao(), forcar,
                              coletar=False, transformar=True))


@app.command("importar")
def importar(
    fonte: str = typer.Option(..., "--fonte", "-f"),
    arquivo: Path = typer.Option(..., "--arquivo", exists=True, dir_okay=False),
    url: str = typer.Option(..., "--url", help="URL oficial de onde o arquivo foi baixado."),
    ano: int | None = typer.Option(None, "--ano"),
    descricao: str | None = typer.Option(None, "--descricao", help="Metadados exigidos por algumas fontes."),
):
    """Registra um arquivo baixado manualmente (quando o site bloqueia a coleta automática)."""
    from observatorio.pipeline import importar_arquivo

    typer.echo(f"Arquivo registrado: id_arquivo={importar_arquivo(fonte, arquivo, ano, url, descricao)}. "
               f"Rode: python -m observatorio transformar --fonte {fonte}")


@app.command("pipeline")
def pipeline(
    de: int = typer.Option(None, "--de", help="Ano inicial (padrão: config/projeto.yaml)."),
    fonte: list[str] | None = typer.Option(None, "--fonte", "-f", help="Restringe a algumas fontes."),
    ano: list[int] | None = typer.Option(None, "--ano", "-a"),
    forcar: bool = typer.Option(False, "--forcar"),
    sem_migrar: bool = typer.Option(False, "--sem-migrar", help="Não roda db migrar antes."),
):
    """Tudo em sequência: migrar, coletar, transformar, indicadores e testes de qualidade."""
    from observatorio.pipeline import migrar
    from observatorio.pipeline import pipeline as executar

    if not sem_migrar:
        migrar()
    _encerrar(executar(fonte or None, ano, de or config.ano_inicial_padrao(), forcar))


# ------------------------------------------------------------------ indicadores, qualidade, relatórios
@ind_app.command("calcular")
def indicadores_calcular(forcar: bool = typer.Option(False, "--forcar")):
    """Calcula core.fato_indicador a partir das versões vigentes das fontes."""
    from observatorio.indicadores.calcular import calcular_indicadores

    r = calcular_indicadores(forcar=forcar)
    typer.echo(f"Versão {r['versao']} ({'nova' if r['nova'] else 'mantida'}): {r['linhas']} linha(s) gravada(s)")


@qual_app.command("testar")
def qualidade_testar():
    """Roda os testes de qualidade e grava em etl.dq_resultado."""
    from observatorio.qualidade.testes import executar_testes

    r = executar_testes()
    typer.echo(f"{r['testes']} teste(s): {r['erros']} com erro, {r['alertas']} com alerta (detalhes em bi.dq_resultado)")
    raise typer.Exit(1 if r["erros"] else 0)


@rel_app.command("cobertura")
def relatorio_cobertura(
    territorio: str | None = typer.Option(None, help="Código IBGE (padrão: município-alvo)."),
    saida: Path | None = typer.Option(None, help="Grava também em arquivo Markdown."),
):
    """Matriz de cobertura indicador x ano e situação das fontes."""
    from observatorio.relatorios import relatorio_cobertura as gerar

    texto = gerar(territorio)
    typer.echo(texto)
    if saida:
        saida.write_text(texto, encoding="utf-8")
        typer.echo(f"Gravado em {saida}")


@docs_app.command("dicionario")
def docs_dicionario():
    """Gera docs/dicionario_dados.md a partir dos COMMENT ON do banco."""
    from observatorio.relatorios import gerar_dicionario

    typer.echo(f"Gravado em {gerar_dicionario()}")


if __name__ == "__main__":
    app()
