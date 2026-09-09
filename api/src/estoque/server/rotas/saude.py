"""`/api/saude`. Sem sessao, sem banco — e' o que o compose usa como healthcheck."""

from fastapi import APIRouter

rotas = APIRouter()


@rotas.get("/api/saude")
async def saude() -> dict[str, str]:
    return {"status": "ok"}
