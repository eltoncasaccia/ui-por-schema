"""O nucleo que toda rota usa: a conexao, a identidade, o envelope.

Fica FORA de `app.py` para que os routers nao importem a aplicacao — se
importassem, `app.py` teria que importa-los de volta para registra-los, e o
ciclo so' se resolveria com import tardio dentro de funcao.

`motor`, `CFG` e `OBS` sao criados na importacao deste modulo, e `app.py` os
reexporta: `estoque.server.app.CFG` e `_engine` continuam existindo, apontando
para o MESMO objeto.
"""

from typing import Any

from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from estoque.application.registry.registry import buscar
from estoque.assistant.langfuse_obs import criar as criar_observador
from estoque.assistant.observador import Observador, ObservadorNulo
from estoque.data.porta import Repositorios
from estoque.data.repositorios import (
    RepoAuditoriaSQL,
    RepoLoteSQL,
    RepoMovimentoSQL,
    RepoProdutoSQL,
    RepoRecebimentoSQL,
    RepoTemperaturaSQL,
)
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator
from estoque.server import sessao as ses
from estoque.server.config import Config

CFG = Config.do_ambiente()
# Nulo quando nao ha chave do LangFuse: telemetria e' opcional por construcao.
OBS: Observador = criar_observador() or ObservadorNulo()
PH = PasswordHasher()
motor = create_async_engine(CFG.database_url, future=True, pool_pre_ping=True)


def ok(dados: Any, **meta: Any) -> dict[str, Any]:
    return {"ok": True, "dados": dados, "meta": meta}


async def ator_ou_falhar(conn: AsyncConnection, sid: str | None) -> Ator:
    if not sid:
        raise ErroDominio("nao_autenticado", "Sessao ausente.")
    ator = await ses.ator_da_sessao(conn, sid)
    if ator is None:
        raise ErroDominio("nao_autenticado", "Sessao invalida ou expirada.")
    return ator


def repos(conn: AsyncConnection) -> Repositorios:
    return Repositorios(
        lote=RepoLoteSQL(conn),
        produto=RepoProdutoSQL(conn),
        movimento=RepoMovimentoSQL(conn),
        auditoria=RepoAuditoriaSQL(conn),
        recebimento=RepoRecebimentoSQL(conn),
        temperatura=RepoTemperaturaSQL(conn),
    )


class Tx:
    def __init__(self, c: AsyncConnection) -> None:
        self._c = c

    async def commit(self) -> None:
        await self._c.commit()

    async def rollback(self) -> None:
        await self._c.rollback()


def tamanho(tipo: str) -> str:
    c = buscar(tipo)
    return c.tamanho if c else "inteira"
