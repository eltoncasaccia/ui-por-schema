"""`/api/usuarios` — papel, unidades e ativacao de quem se cadastrou (T-038, ADR-0019).

Tela com rota, FORA do catalogo: administrar usuario e' raro, sensivel e nao
ganha nada com composicao. Nenhum componente, nenhum caminho do assistente.

**POST, nao PATCH.** A varredura do CA-08 (T-029) recusa verbo que substitui ou
apaga em toda a borda; mudar acesso e' escrita como qualquer comando.

**Ninguem altera o proprio acesso (AC-4).** Hoje so' o Diretor tem
`usuario.gerenciar`, e ja' e' Diretor. A regra existe antes de surgir um papel
intermediario que pudesse se promover.

Desativar derruba a sessao sem apagar nada: `ator_da_sessao` le `ativo` do banco
a cada requisicao (RN-A06).
"""

from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Cookie
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncConnection

from estoque.auditoria import registro as aud
from estoque.autorizacao.motor import autorizar_ou_falhar
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import PapelId, UnidadeId
from estoque.server.deps import ator_ou_falhar, motor, ok

rotas = APIRouter()


class Mudanca(BaseModel):
    """Parcial: so' o que veio no corpo muda. `papel: null` e' "sem papel" (ADR-0019)."""

    model_config = ConfigDict(extra="forbid")

    papel: PapelId | None = None
    unidades: list[UnidadeId] | None = None
    ativo: bool | None = None


async def _estado(c: AsyncConnection, uid: str) -> dict[str, Any] | None:
    u = (
        (
            await c.execute(
                sa.select(m.usuario.c.papel, m.usuario.c.ativo).where(m.usuario.c.id == uid)
            )
        )
        .mappings()
        .first()
    )
    if u is None:
        return None
    unidades = await c.execute(
        sa.select(m.usuario_unidade.c.unidade_id).where(m.usuario_unidade.c.usuario_id == uid)
    )
    return {
        "papel": u["papel"],
        "ativo": u["ativo"],
        "unidades": sorted(r.unidade_id for r in unidades),
    }


@rotas.get("/api/usuarios")
async def listar(sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    async with motor.begin() as c:
        ator = await ator_ou_falhar(c, sessao)
        autorizar_ou_falhar(ator, ("usuario.gerenciar",), "gestao de usuarios")
        usuarios = (
            (
                await c.execute(
                    sa.select(
                        m.usuario.c.id,
                        m.usuario.c.nome,
                        m.usuario.c.email,
                        m.usuario.c.papel,
                        m.usuario.c.ativo,
                    ).order_by(m.usuario.c.nome)
                )
            )
            .mappings()
            .all()
        )
        unidades: dict[str, list[str]] = {}
        for v in await c.execute(sa.select(m.usuario_unidade)):
            unidades.setdefault(v.usuario_id, []).append(v.unidade_id)
        await aud.registrar(c, ator_id=ator.id, acao="ler", origem="tela", entidade="usuario")
    return ok([{**u, "unidades": sorted(unidades.get(u["id"], []))} for u in usuarios])


@rotas.post("/api/usuarios/{usuario_id}")
async def alterar(
    usuario_id: str, corpo: Mudanca, sessao: str | None = Cookie(default=None)
) -> dict[str, Any]:
    async with motor.begin() as c:
        ator = await ator_ou_falhar(c, sessao)
        autorizar_ou_falhar(ator, ("usuario.gerenciar",), "gestao de usuarios")
        if usuario_id == ator.id:
            raise ErroDominio("nao_autorizado", "Ninguem altera o proprio acesso.")

        anterior = await _estado(c, usuario_id)
        if anterior is None:
            raise ErroDominio("nao_encontrado", "Usuario nao encontrado.")

        campos = corpo.model_fields_set
        if not campos:
            raise ErroDominio("invalido", "Nada a alterar.")
        if "ativo" in campos and corpo.ativo is None:
            raise ErroDominio("invalido", "`ativo` precisa ser verdadeiro ou falso.")
        # RN-A01: vinculado a UMA OU MAIS unidades.
        if "unidades" in campos and not corpo.unidades:
            raise ErroDominio("invalido", "Informe ao menos uma unidade.")

        valores = {k: getattr(corpo, k) for k in ("papel", "ativo") if k in campos}
        if valores:
            await c.execute(
                sa.update(m.usuario).where(m.usuario.c.id == usuario_id).values(**valores)
            )
        if corpo.unidades:
            await c.execute(
                sa.delete(m.usuario_unidade).where(m.usuario_unidade.c.usuario_id == usuario_id)
            )
            await c.execute(
                sa.insert(m.usuario_unidade),
                [
                    {"usuario_id": usuario_id, "unidade_id": u}
                    for u in sorted(set(corpo.unidades))
                ],
            )

        novo = await _estado(c, usuario_id)
        # RN-D01: valor anterior e novo, na mesma transacao da mudanca.
        await aud.registrar(
            c,
            ator_id=ator.id,
            acao="usuario_alterar",
            origem="tela",
            entidade="usuario",
            entidade_id=usuario_id,
            valor_anterior=anterior,
            valor_novo=novo,
        )
    return ok(novo)
