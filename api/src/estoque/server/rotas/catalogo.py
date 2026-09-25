"""`/api/catalogo` — o vocabulario DESTE ator (ADR-0003)."""

from typing import Any

from fastapi import APIRouter, Cookie

from estoque.application.exportacao.tabelas import TABULADORES
from estoque.application.registry.registry import buscar, catalogo_de
from estoque.server.deps import ator_ou_falhar, motor, ok

rotas = APIRouter()


def _comandos(componente_id: str) -> dict[str, Any] | None:
    """O mesmo formato que `deps.py:bloco_resposta` já anexa a um `Bloco`
    composto pelo assistente ou por uma view salva (T-049, CONTRATOS §6/§8) —
    aqui para quem monta o `Bloco` de uma ROTA tradicional (`TelaOperacao`,
    `TelaSaida`), que não passa por nenhum dos dois. Sem isto, o clique num
    componente de escrita aberto por `/quarentena/:loteId` ou `/saida` nunca
    chega a `POST /api/comandos/{nome}`: o evento sobe, mas `BlocoRender`
    descarta porque `bloco.comandos` está ausente — achado da T-057, a
    primeira tarefa a exercitar essa escrita com um clique de verdade.

    `None`, não dict vazio, para os componentes de leitura — a mesma
    distinção que `bloco_resposta` já preserva.
    """
    comp = buscar(componente_id)
    if comp is None or not comp.commands:
        return None
    return {
        nome: {"endpoint": cmd.endpoint, "confirm": cmd.confirm, "idempotent": cmd.idempotent}
        for nome, cmd in comp.commands.items()
    }


@rotas.get("/api/catalogo")
async def catalogo(sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    """O vocabulario DESTE ator (ADR-0003). Exposto para a interface poder
    mostrar o que o assistente e' capaz de fazer para quem esta logado."""
    async with motor.connect() as c:
        ator = await ator_ou_falhar(c, sessao)
    saida = []
    for e in catalogo_de(ator):
        # `exportavel` e `comandos` sao da borda, nao do catalogo: vao para a
        # interface decidir o que mostrar, e nunca para o prompt — o modelo
        # nao exporta (ADR-0035) nem grava (ADR-0002).
        entrada: dict[str, Any] = {**e, "exportavel": e["id"] in TABULADORES}
        comandos = _comandos(e["id"])
        if comandos:
            entrada["comandos"] = comandos
        saida.append(entrada)
    return ok(saida)
