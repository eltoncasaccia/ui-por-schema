"""Importa os modulos de comando, registrando-os. Ponto unico de entrada.

Este modulo e' GERADO por `make gerar-indice` varrendo `commands/*.py`.
Nao edite a mao — achado A-15: as cinco tarefas de escrita de W4 precisariam da
mesma linha aqui, e arquivo compartilhado por cinco tarefas e' o que o acordo
de trabalho §4 manda gerar.

Quem importa este modulo e' a borda HTTP. `assistant` nunca o alcanca, e o
contrato 3 do import-linter e' o que garante isso — nao a disciplina.
"""

from estoque.application.commands import (
    autorizacao,
    lote,
    saida,
)

__all__ = [
    "autorizacao",
    "lote",
    "saida",
]
