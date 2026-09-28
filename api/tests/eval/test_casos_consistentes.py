"""T-032 — os 43 casos precisam ser consistentes com o catálogo real ANTES de
gastar token rodando modelo. Um caso cujo `esperado` nem está no catálogo da
persona é errado por construção: falharia sempre, e o motivo não teria nada a
ver com o modelo.
"""

import estoque.application.registry.indice  # noqa: F401
from estoque.application.registry.registry import ids_permitidos
from estoque.eval.__main__ import PERSONAS, ator_de
from estoque.eval.casos import CASOS


def test_toda_persona_de_caso_existe() -> None:
    for c in CASOS:
        assert c.persona in PERSONAS, f"{c.id}: persona {c.persona!r} não existe"


def test_esperado_esta_dentro_do_catalogo_da_persona() -> None:
    for c in CASOS:
        permitidos = ids_permitidos(ator_de(c.persona))
        faltando = c.esperado - permitidos
        assert not faltando, f"{c.id} ({c.persona}): {faltando} fora do catálogo dela"


def test_cobre_as_sete_personas() -> None:
    assert {c.persona for c in CASOS} == set(PERSONAS)


def test_pelo_menos_oito_negativos() -> None:
    """AC-2. Negativo é metade do valor da suíte (ADR-0013) — menos de 8 é
    pouco pra cobrir 7 personas e 8 critérios de aceite pelo lado do "não"."""
    negativos = [c for c in CASOS if not c.esperado]
    assert len(negativos) >= 8, len(negativos)


def test_pelo_menos_quarenta_casos() -> None:
    """AC-1."""
    assert len(CASOS) >= 40, len(CASOS)


def test_nenhum_id_duplicado() -> None:
    ids = [c.id for c in CASOS]
    assert len(ids) == len(set(ids))
