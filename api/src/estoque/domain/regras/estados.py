"""Maquina de estados do lote e imutabilidade de movimento.

Documento 02, secao 4.1. RN-M02, RN-M03.
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from typing import Literal

from estoque.domain.identidade import PapelId
from estoque.domain.tipos import (
    ClasseProduto,
    Lote,
    MotivoMovimento,
    Movimento,
    StatusLoteRegistrado,
    TipoUnidade,
)

EventoLote = Literal["liberacao", "reprovacao", "bloqueio", "desbloqueio", "descarte"]

# (de, evento) -> (para, papeis que podem)
# Fonte: documento 02 secao 4.1. Toda transicao fora desta tabela e' recusada,
# INCLUSIVE para o Diretor: papel nao e' nivel, e' conjunto.
_TRANSICOES: dict[
    tuple[StatusLoteRegistrado, EventoLote],
    tuple[StatusLoteRegistrado, frozenset[PapelId]],
] = {
    ("quarentena", "liberacao"): ("liberado", frozenset({"rt"})),
    ("quarentena", "reprovacao"): ("bloqueado", frozenset({"rt"})),
    ("liberado", "bloqueio"): ("bloqueado", frozenset({"rt"})),
    ("bloqueado", "desbloqueio"): ("liberado", frozenset({"rt"})),
    ("bloqueado", "descarte"): ("descartado", frozenset({"gerente", "rt"})),
}


def transicao_valida(
    de: StatusLoteRegistrado, evento: EventoLote, papel: PapelId | None
) -> bool:
    """Recusa toda transicao fora da tabela 4.1, para qualquer papel.

    `papel is None` (recem-cadastrado) nunca passa.
    """
    if papel is None:
        return False
    destino = _TRANSICOES.get((de, evento))
    if destino is None:
        return False
    return papel in destino[1]


def aplicar_transicao(lote: Lote, evento: EventoLote, papel: PapelId | None) -> Lote:
    if not transicao_valida(lote.status, evento, papel):
        msg = f"transicao invalida: {lote.status} + {evento}"
        raise ValueError(msg)
    novo = _TRANSICOES[(lote.status, evento)][0]
    return replace(lote, status=novo)


def valida_alocacao(classe: ClasseProduto, tipo: TipoUnidade, sala_cofre: bool) -> bool:
    """RN-P02: termolabil so' em unidade refrigerada.
    RN-P03: controlado so' em unidade com sala-cofre."""
    if classe == "termolabil" and tipo != "refrigerado":
        return False
    return not (classe == "controlado" and not sala_cofre)


def resulta_negativo(saldo_atual: int, quantidade_saida: int) -> bool:
    """RN-M01: saldo nunca fica negativo."""
    return saldo_atual - quantidade_saida < 0


def montar_estorno(
    original: Movimento,
    motivo: MotivoMovimento,
    autor_id: str,
    novo_id: str,
    agora: datetime,
) -> Movimento:
    """RN-M03: correcao se faz por estorno que REFERENCIA o original.

    O original nao e' tocado — `Movimento` e' frozen, e esta funcao devolve um
    registro novo. RN-M02 nao e' uma checagem em runtime aqui; e' a ausencia de
    qualquer caminho que modifique o original.
    """
    if original.status != "efetivado":
        msg = "so' movimento efetivado pode ser estornado"
        raise ValueError(msg)
    if original.tipo == "estorno":
        msg = "estorno de estorno nao e' permitido"
        raise ValueError(msg)
    return Movimento(
        id=novo_id,
        lote_id=original.lote_id,
        unidade_id=original.unidade_id,
        tipo="estorno",
        # O sinal do estorno anula o do original: saida (-) vira entrada (+).
        quantidade=original.quantidade,
        motivo=motivo,
        complemento=None,
        autor_id=autor_id,
        autorizador_id=None,
        status="efetivado",
        criado_em=agora,
        estorna_movimento_id=original.id,
        cliente_id=None,
        nota_fiscal=None,
    )


def ja_estornado(original: Movimento, todos: Sequence[Movimento]) -> bool:
    return any(m.estorna_movimento_id == original.id for m in todos)
