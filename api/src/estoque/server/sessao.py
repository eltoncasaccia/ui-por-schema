"""Sessao em cookie com estado no servidor. ADR-0019.

Nao usamos JWT sem estado: `RN-A06` exige que desativar um usuario tenha efeito
IMEDIATO, e token sem estado continua valido ate expirar. Sessao no banco pode
ser revogada.
"""

import secrets
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from estoque.data import modelos as m
from estoque.domain.identidade import PERMISSOES_POR_PAPEL, Ator, PapelId, UnidadeId

COOKIE = "sessao"
COOKIE_CSRF = "csrf"
DURACAO = timedelta(hours=12)


async def criar(conn: AsyncConnection, usuario_id: str) -> str:
    sid = secrets.token_urlsafe(32)
    agora = datetime.now(UTC)
    await conn.execute(
        sa.insert(m.sessao).values(
            id=sid, usuario_id=usuario_id, criada_em=agora, expira_em=agora + DURACAO
        )
    )
    return sid


async def encerrar(conn: AsyncConnection, sid: str) -> None:
    await conn.execute(sa.delete(m.sessao).where(m.sessao.c.id == sid))


async def ator_da_sessao(conn: AsyncConnection, sid: str) -> Ator | None:
    """Resolve o ator a cada requisicao, do banco.

    Le `ativo` e `papel` do banco toda vez de proposito: e' o que faz desativar
    um usuario ter efeito imediato (RN-A06) em vez de esperar a sessao expirar.
    """
    q = (
        sa.select(m.usuario, m.sessao.c.expira_em)
        .join(m.sessao, m.sessao.c.usuario_id == m.usuario.c.id)
        .where(m.sessao.c.id == sid)
    )
    r = (await conn.execute(q)).mappings().first()
    if r is None or r["expira_em"] < datetime.now(UTC):
        return None
    if not r["ativo"]:
        return None

    unis = [
        row.unidade_id
        for row in await conn.execute(
            sa.select(m.usuario_unidade.c.unidade_id).where(
                m.usuario_unidade.c.usuario_id == r["id"]
            )
        )
    ]
    papel: PapelId | None = r["papel"]
    return Ator(
        id=r["id"],
        nome=r["nome"],
        papel=papel,
        unidades=frozenset(unis),
        # ADR-0019: sem papel, sem permissao. Catalogo vazio, nada visivel.
        permissoes=PERMISSOES_POR_PAPEL[papel] if papel else frozenset(),
        ativo=True,
    )


def novo_token_csrf() -> str:
    return secrets.token_urlsafe(24)


def unidades_validas(ator: Ator) -> frozenset[UnidadeId]:
    return ator.unidades
