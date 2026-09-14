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
    FaixaEstoque,
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
    async def por_ean(self, ean: str, ctx: ContextoDados) -> Produto | None:
        """Busca pelo identificador EXTERNO — o que o leitor de codigo de barras
        devolve (T-048, `US-02`, `RNF-02`).

        E' a primeira busca do sistema por um identificador que vem do mundo
        fisico, e por isso a unica que NAO intersecta escopo de unidade: produto
        nao pertence a unidade (`RN-P01`), e filtrar aqui esconderia do
        conferente um produto legitimo que ele tem na mao.

        O que continua valendo e' a omissao de custo (`RN-A02`), que e' por
        ATOR e nao por unidade. Bem definido porque `produto.ean` e' UNIQUE
        desde a migracao 0006.
        """
        ...

    async def faixas(
        self, produto_id: str, ctx: ContextoDados
    ) -> dict[UnidadeId, FaixaEstoque]:
        """Estoque minimo e maximo de um produto POR UNIDADE (T-046, `RN-P06`).

        A faixa e' do par (produto, unidade): o mesmo produto tem faixas
        diferentes na Matriz e na filial. Intersecta o escopo do ator como o
        resto da porta (`RN-A01`) — unidade de fora nao aparece, nem pedindo.
        """
        ...


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


@dataclass(frozen=True, slots=True)
class LinhaAuditoria:
    """Uma linha da trilha.

    Mora aqui, e nao em `domain/tipos.py`, por dois motivos. CONTRATOS §3 congela
    SETE entidades de dominio, e trilha nao e' uma delas — e' registro de que algo
    aconteceu com as outras. E `valor_anterior`/`valor_novo` sao JSON livre: nao
    ha tipo de dominio a dar a eles, porque a forma depende de qual comando
    escreveu.
    """

    id: int
    ator_id: str | None
    acao: str
    entidade: str | None
    entidade_id: str | None
    valor_anterior: dict[str, object] | None
    valor_novo: dict[str, object] | None
    origem: str
    criado_em: datetime


class RepoAuditoria(Protocol):
    """A trilha, so' de leitura.

    NAO existe `inserir` aqui de proposito: quem escreve na trilha e'
    `auditoria/registro.py`, chamado pelo servidor e pelo pipeline. Um caminho de
    escrita exposto pela porta de dados seria um segundo lugar por onde gravar
    auditoria, e o segundo lugar e' o que esquece um campo.

    **Sem escopo de unidade**, e a razao e' que a tabela nao tem `unidade_id`: a
    trilha registra acao, nao mercadoria. Quem le e' governado por
    `auditoria.ler`, que hoje so' o Diretor e a Auditoria tem — e os dois
    alcancam todas as unidades. Se um dia um papel de escopo restrito ganhar essa
    permissao, este comentario vira um problema a resolver.
    """

    async def listar(
        self,
        ctx: ContextoDados,
        *,
        ator_id: str | None = None,
        entidade: str | None = None,
        de: datetime | None = None,
        ate: datetime | None = None,
        limite: int = 50,
    ) -> Sequence[LinhaAuditoria]: ...


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
    auditoria: RepoAuditoria
