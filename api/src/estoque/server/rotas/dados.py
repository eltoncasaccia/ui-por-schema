"""`/api/componentes/{id}/dados` — o TERCEIRO momento de autorizacao, o unico
que garante (ADR-0004). E' o endpoint que um cliente forjando schema atinge
direto, sem passar pelo modelo.
"""

from typing import Any

from fastapi import APIRouter, Cookie
from pydantic import BaseModel, Field

from estoque.application.registry.definir import Pagina
from estoque.auditoria import registro as aud
from estoque.server.deps import ator_ou_falhar, ler_componente, motor, ok

rotas = APIRouter()


class PaginaPedido(BaseModel):
    limite: int = Field(default=20, ge=1, le=200)
    cursor: str | None = None


class PedidoDados(BaseModel):
    params: dict[str, Any] = {}
    # FORA de `params`: paginacao e' transporte, e o modelo nunca a escolhe.
    pagina: PaginaPedido = PaginaPedido()


@rotas.post("/api/componentes/{componente_id}/dados")
async def dados(
    componente_id: str, corpo: PedidoDados, sessao: str | None = Cookie(default=None)
) -> dict[str, Any]:
    """O TERCEIRO momento de autorizacao — o unico que garante (ADR-0004).

    Mesmo que a composicao ja' tenha sido validada, aqui a permissao e'
    reconferida por registro, com a identidade real. E' este endpoint que um
    cliente forjando schema atingiria direto, sem passar pelo modelo.
    """
    async with motor.connect() as c:
        ator = await ator_ou_falhar(c, sessao)
        pagina = Pagina(limite=corpo.pagina.limite, cursor=corpo.pagina.cursor)
        _, vm, etag = await ler_componente(c, ator, componente_id, corpo.params, pagina)

    async with motor.begin() as c2:
        await aud.registrar(
            c2,
            ator_id=ator.id,
            acao="ler",
            origem="assistente",
            entidade=componente_id,
            valor_novo={"params": corpo.params},
        )
    return ok(vm.model_dump(mode="json"), etag=etag)
