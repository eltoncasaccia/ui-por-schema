"""T-032 AC-5 — auditoria de enums (risco R-5 do PRD).

Um recorte sem valor nomeado deixa o modelo INVENTAR o filtro — "clientes
grandes" em vez de `unidade_id: cd-matriz` — e a resposta alarga em silêncio,
sem erro em lugar nenhum. O que vale aqui é o negativo: um componente com
campo de texto livre TEM que reprovar a auditoria, senão ela não audita nada.
"""

from typing import Any

from pydantic import BaseModel

from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import campos_sem_enum, todos


async def _load_nunca_chamado(params: Any, ctx: LoadContext) -> None:
    raise AssertionError("nunca deveria ser chamado — este componente não roda")


def test_catalogo_real_nao_tem_recorte_sem_enum() -> None:
    """Todo campo de `params`, hoje, é enum, identificador ou fronteira de
    intervalo (`de`/`ate`). Achado aqui é ausência de decisão, não estilo."""
    achados = campos_sem_enum(todos())
    assert achados == {}, achados


def test_auditoria_pega_campo_de_texto_livre() -> None:
    """(negativo) Um componente fictício com um recorte de texto livre —
    `cliente_porte: str` — precisa aparecer no achado. Sem este teste, a
    função acima poderia estar sempre devolvendo vazio por engano."""

    class ParamsFalsos(BaseModel):
        unidade_id: str | None = None  # identificador — não deve ser flagrado
        cliente_porte: str | None = None  # recorte de texto livre — DEVE ser

    falso = ComponentDef(
        id="componente_falso_teste",
        label="Falso",
        description="Componente que existe só pra provar que a auditoria pega texto livre.",
        examples=("exemplo",),
        params=ParamsFalsos,
        requires="produto.ler",
        tamanho="linha",
        load=_load_nunca_chamado,
        select=lambda d: d,  # nunca chamado
    )

    achados = campos_sem_enum({"componente_falso_teste": falso})

    assert achados == {"componente_falso_teste": ("cliente_porte",)}
