"""Importa os modulos de comando para que eles se registrem.

Espelha `registry/indice.py`, e pela mesma razao: registro por efeito colateral
de import so' acontece se alguem importar. A diferenca e' que este arquivo e'
escrito a mao — sao poucos comandos, e cada um e' uma decisao, nao uma entrada
de catalogo gerada.

Quem importa este modulo e' a borda HTTP. `assistant` nunca o alcanca, e o
contrato 3 do import-linter e' o que garante isso.
"""

from estoque.commands import lote as _lote  # noqa: F401  — registra os comandos do lote
