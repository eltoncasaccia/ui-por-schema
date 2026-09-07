"""Saldo derivado. RN-M06.

Este modulo existe para que nao exista um campo `saldo`. O saldo de um lote e'
sempre a soma dos seus movimentos — nunca um numero guardado que alguem edita.
"""

from collections.abc import Iterable

from estoque.domain.tipos import Movimento

# Sinal por tipo de movimento. `quantidade` e' sempre positiva (RN-M04).
_SINAL: dict[str, int] = {
    "entrada": +1,
    "saida": -1,
    "descarte": -1,
    "estorno": +1,  # o estorno carrega o sinal invertido do original no seu tipo
}


def calcular_saldo(movimentos: Iterable[Movimento]) -> int:
    """Soma dos movimentos EFETIVADOS de um lote.

    Movimento `aguardando_autorizacao` NAO conta (RN-C01): enquanto a segunda
    identificacao nao vem, a mercadoria nao saiu do estoque. Se contasse, a dupla
    identificacao viraria teatro — o saldo ja teria mudado com uma assinatura so'.

    Movimento `recusado` tambem nao conta, e permanece registrado (RN-M02).
    """
    total = 0
    for m in movimentos:
        if m.status != "efetivado":
            continue
        total += _SINAL[m.tipo] * m.quantidade
    return total
