"""Trilha de auditoria append-only. RN-D01, RN-D02, RN-D05.

Este modulo NAO tem funcao de update nem de delete. Nao e' validacao em runtime:
a API simplesmente nao oferece o caminho, e o banco recusa o privilegio
(migracao 0001). Duas camadas, nenhuma delas confiando na outra.

`RN-D05`: a consulta tambem e' auditada. Ver quem consultou o que importa.
"""

from datetime import UTC, datetime
from typing import Any, Literal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from estoque.data import modelos as m

Origem = Literal["tela", "assistente", "sistema"]


async def registrar(
    conn: AsyncConnection,
    *,
    ator_id: str | None,
    acao: str,
    origem: Origem,
    entidade: str | None = None,
    entidade_id: str | None = None,
    valor_anterior: dict[str, Any] | None = None,
    valor_novo: dict[str, Any] | None = None,
) -> None:
    await conn.execute(
        sa.insert(m.auditoria).values(
            ator_id=ator_id,
            acao=acao,
            entidade=entidade,
            entidade_id=entidade_id,
            valor_anterior=valor_anterior,
            valor_novo=valor_novo,
            origem=origem,
            criado_em=datetime.now(UTC),  # RN-M04: do servidor, nunca do cliente
        )
    )
