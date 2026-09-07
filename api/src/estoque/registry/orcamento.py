"""Orcamento de tokens do catalogo. ADR-0011, RNF-08.

Numero medido na v1: ~164 tokens por componente registrado, em TODA pergunta.
A conta e' linear e implacavel — 25 componentes ~= 4k tokens de prompt sempre.
"""

from estoque.domain.identidade import Ator
from estoque.registry.registry import TETO_CATALOGO, catalogo_de, todos

# Aproximacao suficiente para orcamento: ~4 caracteres por token em pt-BR.
_CHARS_POR_TOKEN = 4
ALERTA_TOKENS = 4000


def tokens_do_catalogo(ator: Ator) -> int:
    chars = 0
    for e in catalogo_de(ator):
        chars += len(e["id"]) + len(e["label"]) + len(e["description"])
        chars += sum(len(x) for x in e["examples"])
        chars += len(str(e["params"]))
    return chars // _CHARS_POR_TOKEN


def verificar_teto() -> None:
    """RNF-08: falha a inicializacao acima do teto.

    Deliberadamente uma excecao na importacao, e nao um aviso: a discussao ao
    passar de 25 componentes e' de escopo, nao de codigo.
    """
    n = len(todos())
    if n > TETO_CATALOGO:
        msg = (
            f"catalogo com {n} componentes, teto e' {TETO_CATALOGO} (ADR-0011). "
            "Passar daqui exige recuperacao de catalogo, que e' outro sistema, "
            "com falhas proprias e silenciosas."
        )
        raise RuntimeError(msg)
