"""FEFO — First Expired, First Out. RN-L02 e RN-L03."""

from collections.abc import Sequence
from datetime import date

from estoque.domain.regras.validade import status_efetivo
from estoque.domain.tipos import Lote


def propor_fefo(lotes: Sequence[Lote], saldos: dict[str, int], hoje: date) -> Lote | None:
    """RN-L02: o sistema propoe o lote LIBERADO de menor validade.

    Lotes em quarentena, bloqueados, vencidos ou esgotados nao entram — propor
    um lote que nao pode sair seria propor um erro.

    Desempate deterministico e documentado (T-008 AC-3): mesma validade decide
    pelo id do lote, em ordem crescente. Sem isso, a mesma pergunta daria
    respostas diferentes entre execucoes.
    """
    elegiveis = [
        lote
        for lote in lotes
        if status_efetivo(lote, saldos.get(lote.id, 0), hoje) == "liberado"
    ]
    if not elegiveis:
        return None
    return min(elegiveis, key=lambda lote: (lote.validade, lote.id))


def exige_justificativa_fefo(escolhido: Lote, proposto: Lote | None) -> bool:
    """RN-L03: separar lote diferente do proposto pelo FEFO exige justificativa."""
    if proposto is None:
        return True
    return escolhido.id != proposto.id
