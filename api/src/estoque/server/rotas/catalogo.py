"""`/api/catalogo` — o vocabulario DESTE ator (ADR-0003)."""

from typing import Any

from fastapi import APIRouter, Cookie

from estoque.application.exportacao.tabelas import TABULADORES
from estoque.application.registry.registry import catalogo_de
from estoque.server.deps import ator_ou_falhar, motor, ok

rotas = APIRouter()


@rotas.get("/api/catalogo")
async def catalogo(sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    """O vocabulario DESTE ator (ADR-0003). Exposto para a interface poder
    mostrar o que o assistente e' capaz de fazer para quem esta logado."""
    async with motor.connect() as c:
        ator = await ator_ou_falhar(c, sessao)
    # `exportavel` e' da borda, nao do catalogo: vai para a interface decidir se
    # mostra o botao, e nunca para o prompt — o modelo nao exporta (ADR-0035).
    return ok([{**e, "exportavel": e["id"] in TABULADORES} for e in catalogo_de(ator)])
