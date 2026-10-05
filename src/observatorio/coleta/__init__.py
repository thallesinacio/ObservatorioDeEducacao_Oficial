"""Registro dos coletores disponíveis."""

from __future__ import annotations

from observatorio.coleta.base import Fonte


def registro() -> dict[str, Fonte]:
    from observatorio.coleta.censo_escolar import CensoEscolar
    from observatorio.coleta.ideb import Ideb
    from observatorio.coleta.inep_indicadores import (
        AdequacaoFormacaoDocente,
        DistorcaoIdadeSerie,
        DocentesSuperior,
        MediaAlunosTurma,
        TaxasRendimento,
    )
    from observatorio.coleta.populacao_datasus import PopulacaoDatasus
    from observatorio.coleta.siconfi import Siconfi
    from observatorio.coleta.sidra import Sidra, SidraAlfabetizacao
    from observatorio.coleta.sinopse import SinopseEstatistica
    from observatorio.coleta.siope import Siope

    fontes = [
        CensoEscolar(), PopulacaoDatasus(), Sidra(), TaxasRendimento(), DistorcaoIdadeSerie(),
        AdequacaoFormacaoDocente(), MediaAlunosTurma(), DocentesSuperior(), SinopseEstatistica(), Ideb(),
        Siope(), Siconfi(), SidraAlfabetizacao(),
    ]
    return {f.id_fonte: f for f in fontes}


# Ordem de execução no pipeline (a população vem antes dos indicadores que dependem dela).
ORDEM_PIPELINE = [
    "censo_escolar", "populacao_datasus", "sidra_ibge", "inep_rendimento", "inep_distorcao", "inep_afd",
    "inep_atu", "inep_dsu", "sinopse_estatistica", "ideb", "siope", "siconfi", "sidra_alfabetizacao",
]
