"""ADR-0023, ADR-0024 — e o critério que mais importa em T-014: AC-3.

O erro central da POC v1 foi medir um parser simulado e publicar os números como
se fossem reais. Estes testes existem para que isso não possa se repetir.
"""

from typing import Any

import pytest

from estoque.assistant.adapter import (
    AdaptadorMock,
    AdaptadorOpenRouter,
    ErroDeModelo,
    extrair_json,
    json_schema_do_catalogo,
)
from estoque.domain.identidade import Ator
from estoque.registry.registry import catalogo_de


def test_sem_chave_falha_e_nao_cai_para_o_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-014 AC-3 — o critério mais importante desta tarefa."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ErroDeModelo, match="OPENROUTER_API_KEY"):
        AdaptadorOpenRouter()


async def test_mock_e_sempre_identificado_como_mock() -> None:
    """Nenhum número do mock pode ser confundido com número real."""
    r = await AdaptadorMock().compor("qualquer", [{"id": "fila_vencimento"}])
    assert r.trace.origem == "mock"
    assert r.trace.modelo == "mock"


# --- ADR-0024: o enum de `tipo` é o catálogo do ator ------------------------
def test_schema_restrito_so_permite_ids_do_catalogo_do_ator(
    personas: dict[str, Ator],
) -> None:
    cat = catalogo_de(personas["cleide"])
    schema = json_schema_do_catalogo(cat)
    enum = schema["properties"]["blocos"]["items"]["properties"]["tipo"]["enum"]
    assert enum == [c["id"] for c in cat]
    assert enum, "catálogo vazio tornaria o schema inútil"


def test_schema_restrito_e_o_catalogo_nao_divergem(personas: dict[str, Ator]) -> None:
    """ADR-0024 — o catálogo é serializado DUAS vezes: como texto no prompt e
    como JSON Schema. Divergência entre as duas é um modo de falha novo, e este
    teste é o que impede que ele passe."""
    from estoque.registry.registry import ids_permitidos

    for nome, ator in personas.items():
        cat = catalogo_de(ator)
        enum = json_schema_do_catalogo(cat)["properties"]["blocos"]["items"]["properties"][
            "tipo"
        ]["enum"]
        assert set(enum) == set(ids_permitidos(ator)), nome


def test_schema_restrito_nao_aceita_campo_extra() -> None:
    schema = json_schema_do_catalogo([{"id": "x"}])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["blocos"]["items"]["additionalProperties"] is False


def test_schema_restrito_nao_tem_campo_de_markup_nem_estilo() -> None:
    """ADR-0001: o schema não tem onde carregar código. Vale também para a
    versão que vai ao modelo como restrição de decodificação."""
    texto = str(json_schema_do_catalogo([{"id": "x"}]))
    for proibido in ("html", "style", "css", "script", "layout", "valor"):
        assert proibido not in texto.lower()


# --- modo livre: a extração que a medição precisa ---------------------------
@pytest.mark.parametrize(
    "bruto",
    [
        '{"versao":1,"blocos":[]}',
        '```json\n{"versao":1,"blocos":[]}\n```',
        'Claro! Aqui está:\n{"versao":1,"blocos":[]}\nEspero ter ajudado.',
    ],
)
def test_extrai_json_de_resposta_livre(bruto: str) -> None:
    assert extrair_json(bruto) == {"versao": 1, "blocos": []}


def test_resposta_sem_json_levanta() -> None:
    with pytest.raises(ValueError, match="sem objeto JSON"):
        extrair_json("desculpe, não consigo ajudar com isso")


async def test_trace_registra_modo_e_origem() -> None:
    """Nenhum número entra em relatório sem procedência (ADR-0023)."""
    r = await AdaptadorMock().compor("x", [{"id": "fila_vencimento"}], modo="livre")
    resumo: dict[str, Any] = r.trace.resumo()
    assert resumo["origem"] == "mock"
    assert resumo["modo"] == "livre"
