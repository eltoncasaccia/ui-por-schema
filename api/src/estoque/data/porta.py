"""Unica porta para dados. CONTRATOS secao 4, ADR-0007.

Duas responsabilidades que NAO sao do chamador:

1. Escopo de unidade (RN-A01). A porta intersecta com as unidades do ator.
   Um criterio malicioso pedindo outra unidade e' ignorado — a intersecao
   sempre vence.
2. Campo restrito (RN-A02). `custo_unitario_centavos` chega AUSENTE para quem
   nao tem `custo.ler`. Ausente, nao `None`: `None` vazaria a existencia do
   campo e apareceria na serializacao.

Os tipos aqui sao Protocol de proposito: `domain` e `registry` nunca importam
SQLAlchemy (verificado por import-linter).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from estoque.domain.identidade import Ator, UnidadeId
from estoque.domain.tipos import (
    Lote,
    Movimento,
    Produto,
    Recebimento,
    RegistroTemperatura,
    StatusLoteRegistrado,
)


class Transacao(Protocol):
    """Transacao real (ADR-0018). Existe desde o inicio para que trocar o
    backend nao vire redesenho — e porque comando falho nao pode deixar efeito
    parcial (T-025 AC-7), o que armazenamento em memoria esconderia."""

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ContextoDados:
    ator: Ator
    unidades_permitidas: frozenset[UnidadeId]
    tx: Transacao


class RepoLote(Protocol):
    async def por_id(self, lote_id: str, ctx: ContextoDados) -> Lote | None: ...
    async def listar(
        self,
        ctx: ContextoDados,
        *,
        produto_id: str | None = None,
        unidade_id: UnidadeId | None = None,
        status: StatusLoteRegistrado | None = None,
        validade_ate: date | None = None,
    ) -> Sequence[Lote]: ...
    async def saldos(self, lote_ids: Sequence[str], ctx: ContextoDados) -> dict[str, int]: ...


class RepoProduto(Protocol):
    async def por_id(self, produto_id: str, ctx: ContextoDados) -> Produto | None: ...
    async def por_ids(self, ids: Sequence[str], ctx: ContextoDados) -> dict[str, Produto]: ...


class RepoMovimento(Protocol):
    async def do_lote(self, lote_id: str, ctx: ContextoDados) -> Sequence[Movimento]: ...
    async def listar(
        self,
        ctx: ContextoDados,
        *,
        unidade_id: UnidadeId | None = None,
        tipo: str | None = None,
        status: str | None = None,
        de: datetime | None = None,
        ate: datetime | None = None,
    ) -> Sequence[Movimento]: ...
    async def por_cliente(
        self, cliente_id: str, de: date, ate: date, ctx: ContextoDados
    ) -> Sequence[Movimento]: ...


class RepoRecebimento(Protocol):
    async def por_id(self, rid: str, ctx: ContextoDados) -> Recebimento | None: ...
    async def listar(self, ctx: ContextoDados) -> Sequence[Recebimento]: ...


class RepoTemperatura(Protocol):
    async def serie(
        self, unidade_id: UnidadeId, de: datetime, ate: datetime, ctx: ContextoDados
    ) -> Sequence[RegistroTemperatura]: ...


@dataclass(frozen=True, slots=True)
class Repositorios:
    """Injetado no `LoadContext` pelo servidor. Nenhum `load` constroi o seu."""

    lote: RepoLote
    produto: RepoProduto
    movimento: RepoMovimento
    recebimento: RepoRecebimento
    temperatura: RepoTemperatura
