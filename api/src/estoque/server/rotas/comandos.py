"""`/api/comandos/{nome}` — a borda do PLANO DE ESCRITA. T-025, T-011 AC-3/AC-4.

Nao e' alcancavel a partir da saida do modelo, e nao por disciplina:
`assistant` nao importa `commands` (import-linter, contrato 3).
"""

from typing import Any

from fastapi import APIRouter, Cookie, Request, Response

from estoque.application.commands import pipeline
from estoque.server.deps import ator_ou_falhar, motor, ok

rotas = APIRouter()


@rotas.post("/api/comandos/{nome}")
async def comando(
    nome: str,
    corpo: dict[str, Any],
    req: Request,
    resposta: Response,
    sessao: str | None = Cookie(default=None),
) -> dict[str, Any]:
    """A borda do PLANO DE ESCRITA. T-025, T-011 AC-3 e AC-4.

    Esta rota nao e' alcancavel a partir da saida do modelo, e nao e' por
    disciplina: `assistant` nao importa `commands` (import-linter, contrato 3), e
    o `CommandDef` que o catalogo publica nao carrega funcao nenhuma. O modelo
    pode fazer o formulario aparecer; quem dispara e' a pessoa que clica em
    salvar — pela mesma rota que a tela tradicional usa (ADR-0002).

    CSRF e `Origin` ja' foram conferidos no middleware, que roda em TODA escrita.
    """
    async with motor.connect() as c:
        ator = await ator_ou_falhar(c, sessao)

    r = await pipeline.executar(
        nome,
        corpo,
        ator=ator,
        motor=motor,
        origem="tela",
        idempotency_key=req.headers.get("Idempotency-Key"),
        if_match=req.headers.get("If-Match"),
    )
    if r.etag:
        resposta.headers["ETag"] = r.etag
    return ok(r.dados, etag=r.etag, repetido=r.repetido)
