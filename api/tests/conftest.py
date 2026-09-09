"""As sete personas do documento 02, como atores reais.

O conjunto de papeis E' o teste de permissao — remover um enfraquece a suite.
"""

import pytest

from estoque.domain.identidade import (
    PERMISSOES_POR_PAPEL,
    Ator,
    PapelId,
)


def ator(nome: str, papel: PapelId, unidades: set[str]) -> Ator:
    return Ator(
        id=f"u-{nome.lower()}",
        nome=nome,
        papel=papel,
        unidades=frozenset(unidades),  # type: ignore[arg-type]
        permissoes=PERMISSOES_POR_PAPEL[papel],
        ativo=True,
    )


TODAS: set[str] = {"cd-matriz", "cd-refrigerado", "filial-uberlandia"}

PERSONAS: dict[str, Ator] = {
    "marco": ator("Marco", "diretor", TODAS),
    "helena": ator("Helena", "rt", TODAS),
    "ivo": ator("Ivo", "gerente", {"cd-matriz", "cd-refrigerado"}),
    "odair": ator("Odair", "gerente", {"filial-uberlandia"}),
    "cleide": ator("Cleide", "conferente", {"cd-matriz", "cd-refrigerado"}),
    "rafael": ator("Rafael", "comprador", TODAS),
    "sandra": ator("Sandra", "auditoria", TODAS),
}


@pytest.fixture
def personas() -> dict[str, Ator]:
    return PERSONAS


@pytest.fixture(autouse=True)
def _registro_carregado() -> None:
    import estoque.application.registry.indice  # noqa: F401


@pytest.fixture
def recem_cadastrado() -> Ator:
    """ADR-0019: cadastro nao concede papel. Zero permissoes, nao ve nada."""
    return Ator(
        id="u-novo",
        nome="Novo",
        papel=None,
        unidades=frozenset(),
        permissoes=frozenset(),
        ativo=True,
    )
