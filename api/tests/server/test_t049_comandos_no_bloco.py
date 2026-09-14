"""T-049 AC-5 — o `Bloco` carrega `comandos` só quando o componente declara.

Abrir uma view não roda `load`/`select` (T-016 AC-5, `test_t016_ac.py`) — a
revalidação só confere catálogo e permissão. Por isso não há lote nem produto
para semear aqui: o que se testa é a FORMA do bloco de resposta, não o dado.

Achado [A-40](../../../docs/tasks/ACHADOS.md): nenhum botão de escrita chamava
o servidor porque o cliente nunca soube qual endpoint chamar. `comandos` é o
metadado que fecha essa lacuna — testado nas duas rotas que montam blocos
(`/api/views/{id}` e `/api/assistente/compor`), porque as duas usam
`deps.bloco_resposta` e as duas precisam concordar.
"""

from collections.abc import AsyncGenerator, Mapping, Sequence
from typing import Any

import pytest
from borda import cliente, criar_sessao, descartar_pool

from estoque.assistant.adapter import AdaptadorMock, Resposta
from estoque.assistant.trace import Modo
from estoque.server.rotas import assistente


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


def helena() -> str:
    """RT — a única com `lote.liberar`, requisito de `quarentena_liberar`."""
    return criar_sessao(usuario_id="t049-helena", papel="rt", unidades=("cd-matriz",))


async def _abrir(sid: str, blocos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    schema = {"versao": 1, "blocos": blocos}
    async with cliente(sid) as cli:
        r = await cli.post("/api/views", json={"titulo": "t049", "schema": schema})
    view_id = r.json()["dados"]["view_id"]
    async with cliente(sid) as cli:
        r = await cli.get(f"/api/views/{view_id}")
    return list(r.json()["dados"]["blocos"])


COMANDOS_ESPERADOS = {
    "lote_liberar_quarentena": {
        "endpoint": "/api/comandos/lote_liberar_quarentena",
        "confirm": True,
        "idempotent": False,
    }
}


async def test_ac5_componente_com_command_carrega_comandos_via_views() -> None:
    blocos = [{"tipo": "quarentena_liberar", "params": {"lote_id": "x"}}]
    [bloco] = await _abrir(helena(), blocos)
    assert bloco["comandos"] == COMANDOS_ESPERADOS


async def test_ac5_componente_de_leitura_nao_carrega_comandos_via_views() -> None:
    """Negativo — o par que impede `comandos: {}` de vazar para os 15 de leitura."""
    [bloco] = await _abrir(helena(), [{"tipo": "lote_lista", "params": {}}])
    assert "comandos" not in bloco


class _AdaptadorFixo:
    """Devolve sempre a mesma composição, sem chamar modelo nenhum (CS-06)."""

    def __init__(self, blocos: Sequence[dict[str, Any]]) -> None:
        self._mock = AdaptadorMock({"x": {"versao": 1, "blocos": list(blocos)}})

    async def compor(
        self, pergunta: str, catalogo: Sequence[Mapping[str, Any]], modo: Modo = "restrito"
    ) -> Resposta:
        return await self._mock.compor("x", catalogo, modo=modo)


async def test_ac5_componente_com_command_carrega_comandos_via_assistente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        assistente,
        "_adaptador",
        lambda: _AdaptadorFixo([{"tipo": "quarentena_liberar", "params": {"lote_id": "x"}}]),
    )
    async with cliente(helena()) as cli:
        r = await cli.post("/api/assistente/compor", json={"pergunta": "liberar"})
    [bloco] = r.json()["dados"]["blocos"]
    assert bloco["comandos"] == COMANDOS_ESPERADOS


async def test_ac5_componente_de_leitura_nao_carrega_comandos_via_assistente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        assistente,
        "_adaptador",
        lambda: _AdaptadorFixo([{"tipo": "lote_lista", "params": {}}]),
    )
    async with cliente(helena()) as cli:
        r = await cli.post("/api/assistente/compor", json={"pergunta": "liberar"})
    [bloco] = r.json()["dados"]["blocos"]
    assert "comandos" not in bloco
