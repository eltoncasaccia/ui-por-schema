"""Paginação é transporte, não vocabulário do modelo."""

import estoque.application.registry.indice  # noqa: F401
from estoque.application.registry.definir import Pagina
from estoque.application.registry.registry import todos


def test_pagina_nao_e_param_de_nenhum_componente() -> None:
    """Se `limite` ou `cursor` virassem params, o modelo passaria a escolher
    quantas linhas mostrar e por onde continuar — que não é decisão dele."""
    for comp in todos().values():
        campos = set(comp.params.model_fields)
        assert not (campos & {"limite", "cursor", "pagina", "offset"}), comp.id


def test_pagina_tem_padrao_seguro() -> None:
    p = Pagina()
    assert p.limite > 0 and p.cursor is None


async def test_limite_da_pagina_e_respeitado() -> None:
    """A página chega pelo LoadContext, não pelos params. Já foi ignorada uma
    vez: o servidor construía o contexto sem passá-la, e a fila voltava inteira."""
    import inspect

    from estoque.server import app

    fonte = inspect.getsource(app.dados)
    assert "pagina=Pagina(" in fonte, "o servidor precisa repassar a página ao load"
