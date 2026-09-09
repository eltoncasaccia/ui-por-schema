"""`/api/views`: um schema persistido e seu endereco publico. ADR-0021."""

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Cookie
from pydantic import BaseModel, ConfigDict, Field

from estoque.application.schema.validar import revalidar_ou_falhar
from estoque.application.schema.viewkey import novo_view_id, view_key
from estoque.auditoria import registro as aud
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio
from estoque.server.deps import ator_ou_falhar, motor, ok, tamanho

rotas = APIRouter()


class NovaView(BaseModel):
    # `schema` colide com um metodo do BaseModel; o nome no JSON continua sendo
    # `schema`, que e' o que o contrato publico diz.
    model_config = ConfigDict(populate_by_name=True)

    titulo: str
    esquema: dict[str, Any] = Field(alias="schema")


@rotas.post("/api/views")
async def criar_view(
    corpo: NovaView, sessao: str | None = Cookie(default=None)
) -> dict[str, Any]:
    """Persiste um schema e devolve seu endereco publico.

    Dois identificadores, com papeis distintos (ADR-0021):
      view_key  hash do schema, INTERNO — "esta tela e' a mesma de antes?"
      view_id   opaco, PUBLICO, revogavel — o endereco em /v/:viewId
    """
    async with motor.begin() as c:
        ator = await ator_ou_falhar(c, sessao)
        schema = revalidar_ou_falhar(corpo.esquema, ator)
        vid, vkey = novo_view_id(), view_key(schema)
        await c.execute(
            sa.insert(m.view_registro).values(
                view_id=vid,
                view_key=vkey,
                schema=schema.model_dump(),
                criado_por=ator.id,
                criado_em=datetime.now(UTC),
            )
        )
        await aud.registrar(
            c,
            ator_id=ator.id,
            acao="criar_view",
            origem="tela",
            entidade="view",
            entidade_id=vid,
            valor_novo={"view_key": vkey},
        )
    return ok({"view_id": vid, "view_key": vkey})


@rotas.get("/api/views/{view_id}")
async def abrir_view(view_id: str, sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    """A regra que nao pode quebrar: o schema e' revalidado contra o catalogo
    DO REQUISITANTE, e os dados carregam sob a autenticacao DELE.

    Quem abre uma view compartilhada e nao pode ver o lote ve "sem acesso" — nao
    os dados de quem compartilhou.
    """
    async with motor.begin() as c:
        ator = await ator_ou_falhar(c, sessao)
        r = (
            (
                await c.execute(
                    sa.select(m.view_registro).where(m.view_registro.c.view_id == view_id)
                )
            )
            .mappings()
            .first()
        )
        # Revogado responde como inexistente — ADR-0014.
        if r is None or r["revogado_em"] is not None:
            raise ErroDominio("nao_encontrado", "Registro nao encontrado.")
        schema = revalidar_ou_falhar(r["schema"], ator)
        await aud.registrar(
            c,
            ator_id=ator.id,
            acao="abrir_view",
            origem="tela",
            entidade="view",
            entidade_id=view_id,
        )
    return ok(
        {
            "view_id": view_id,
            "schema": schema.model_dump(),
            "blocos": [
                {"tipo": b.tipo, "params": b.params, "tamanho": tamanho(b.tipo)}
                for b in schema.blocos
            ],
        }
    )
