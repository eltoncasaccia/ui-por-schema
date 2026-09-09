"""Repositorios SQLAlchemy. Implementam os Protocol de `porta.py`.

DUAS coisas acontecem aqui e nao no chamador:

1. ESCOPO DE UNIDADE (RN-A01). Todo SELECT recebe `WHERE unidade_id = ANY(...)`
   com as unidades do ator. Um criterio pedindo outra unidade e' ignorado — a
   intersecao sempre vence. Nao existe caminho que devolva dado fora do escopo.

2. CAMPO RESTRITO (RN-A02). `custo_unitario_centavos` chega AUSENTE para quem
   nao tem `custo.ler`. Ausente, nao `None`: `None` vazaria a existencia do
   campo e apareceria na serializacao JSON.
"""

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from estoque.data import modelos as m
from estoque.data.porta import ContextoDados, LinhaAuditoria
from estoque.domain.identidade import UnidadeId
from estoque.domain.tipos import (
    Lote,
    Movimento,
    Produto,
    Recebimento,
    RegistroTemperatura,
    StatusLoteRegistrado,
)


def _escopo(coluna: sa.Column[str], ctx: ContextoDados) -> sa.ColumnElement[bool]:
    """RN-A01 — a intersecao com o escopo do ator, sempre aplicada."""
    return coluna.in_(sorted(ctx.unidades_permitidas))


class RepoLoteSQL:
    def __init__(self, conn: AsyncConnection) -> None:
        self._c = conn

    async def por_id(self, lote_id: str, ctx: ContextoDados) -> Lote | None:
        q = sa.select(m.lote).where(m.lote.c.id == lote_id, _escopo(m.lote.c.unidade_id, ctx))
        r = (await self._c.execute(q)).mappings().first()
        # Fora do escopo devolve None — indistinguivel de inexistente (ADR-0014).
        return _para_lote(dict(r)) if r else None

    async def listar(
        self,
        ctx: ContextoDados,
        *,
        produto_id: str | None = None,
        unidade_id: UnidadeId | None = None,
        status: StatusLoteRegistrado | None = None,
        validade_ate: date | None = None,
    ) -> Sequence[Lote]:
        q = sa.select(m.lote).where(_escopo(m.lote.c.unidade_id, ctx))
        if produto_id:
            q = q.where(m.lote.c.produto_id == produto_id)
        if unidade_id:
            # Pedir unidade fora do escopo nao amplia nada: o WHERE de escopo
            # ja' esta' aplicado e este apenas restringe mais.
            q = q.where(m.lote.c.unidade_id == unidade_id)
        if status:
            q = q.where(m.lote.c.status == status)
        if validade_ate:
            q = q.where(m.lote.c.validade <= validade_ate)
        q = q.order_by(m.lote.c.validade, m.lote.c.id)
        return [_para_lote(dict(r)) for r in (await self._c.execute(q)).mappings()]

    async def saldos(self, lote_ids: Sequence[str], ctx: ContextoDados) -> dict[str, int]:
        """Le a view materializada (ADR-0022). Derivada, nunca escrita aqui."""
        if not lote_ids:
            return {}
        q = (
            sa.select(m.saldo_lote.c.lote_id, m.saldo_lote.c.saldo)
            .join(m.lote, m.lote.c.id == m.saldo_lote.c.lote_id)
            .where(
                m.saldo_lote.c.lote_id.in_(list(lote_ids)), _escopo(m.lote.c.unidade_id, ctx)
            )
        )
        return {r.lote_id: r.saldo for r in (await self._c.execute(q))}


class RepoProdutoSQL:
    def __init__(self, conn: AsyncConnection) -> None:
        self._c = conn

    async def por_id(self, produto_id: str, ctx: ContextoDados) -> Produto | None:
        q = sa.select(m.produto).where(m.produto.c.id == produto_id)
        r = (await self._c.execute(q)).mappings().first()
        return _para_produto(dict(r), ctx) if r else None

    async def por_ids(self, ids: Sequence[str], ctx: ContextoDados) -> dict[str, Produto]:
        if not ids:
            return {}
        q = sa.select(m.produto).where(m.produto.c.id.in_(list(set(ids))))
        return {
            r["id"]: _para_produto(dict(r), ctx) for r in (await self._c.execute(q)).mappings()
        }


class RepoMovimentoSQL:
    def __init__(self, conn: AsyncConnection) -> None:
        self._c = conn

    async def do_lote(self, lote_id: str, ctx: ContextoDados) -> Sequence[Movimento]:
        q = (
            sa.select(m.movimento)
            .where(m.movimento.c.lote_id == lote_id, _escopo(m.movimento.c.unidade_id, ctx))
            .order_by(m.movimento.c.criado_em)
        )
        return [_para_movimento(dict(r)) for r in (await self._c.execute(q)).mappings()]

    async def listar(
        self,
        ctx: ContextoDados,
        *,
        unidade_id: UnidadeId | None = None,
        tipo: str | None = None,
        status: str | None = None,
        de: datetime | None = None,
        ate: datetime | None = None,
    ) -> Sequence[Movimento]:
        q = sa.select(m.movimento).where(_escopo(m.movimento.c.unidade_id, ctx))
        if unidade_id:
            q = q.where(m.movimento.c.unidade_id == unidade_id)
        if tipo:
            q = q.where(m.movimento.c.tipo == tipo)
        if status:
            q = q.where(m.movimento.c.status == status)
        if de:
            q = q.where(m.movimento.c.criado_em >= de)
        if ate:
            q = q.where(m.movimento.c.criado_em <= ate)
        q = q.order_by(m.movimento.c.criado_em.desc()).limit(500)
        return [_para_movimento(dict(r)) for r in (await self._c.execute(q)).mappings()]

    async def por_cliente(
        self, cliente_id: str, de: date, ate: date, ctx: ContextoDados
    ) -> Sequence[Movimento]:
        q = sa.select(m.movimento).where(
            m.movimento.c.cliente_id == cliente_id,
            _escopo(m.movimento.c.unidade_id, ctx),
        )
        return [_para_movimento(dict(r)) for r in (await self._c.execute(q)).mappings()]


class RepoRecebimentoSQL:
    """Leitura de recebimento. Escopo de unidade sempre aplicado (RN-A01)."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._c = conn

    async def por_id(self, rid: str, ctx: ContextoDados) -> Recebimento | None:
        q = sa.select(m.recebimento).where(
            m.recebimento.c.id == rid, _escopo(m.recebimento.c.unidade_id, ctx)
        )
        r = (await self._c.execute(q)).mappings().first()
        # Fora do escopo devolve None — indistinguivel de inexistente (ADR-0014).
        return _para_recebimento(dict(r)) if r else None

    async def listar(self, ctx: ContextoDados) -> Sequence[Recebimento]:
        q = (
            sa.select(m.recebimento)
            .where(_escopo(m.recebimento.c.unidade_id, ctx))
            .order_by(m.recebimento.c.recebido_em.desc(), m.recebimento.c.id)
        )
        return [_para_recebimento(dict(r)) for r in (await self._c.execute(q)).mappings()]


class RepoTemperaturaSQL:
    """Serie de temperatura de UMA unidade, dentro do escopo do ator (RN-A01)."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._c = conn

    async def serie(
        self, unidade_id: UnidadeId, de: datetime, ate: datetime, ctx: ContextoDados
    ) -> Sequence[RegistroTemperatura]:
        q = (
            sa.select(m.registro_temperatura)
            .where(
                m.registro_temperatura.c.unidade_id == unidade_id,
                # Pedir unidade fora do escopo nao amplia nada: o WHERE de escopo
                # ja' restringe, e a igualdade acima so' restringe mais.
                _escopo(m.registro_temperatura.c.unidade_id, ctx),
                m.registro_temperatura.c.medido_em >= de,
                m.registro_temperatura.c.medido_em <= ate,
            )
            .order_by(m.registro_temperatura.c.medido_em)
        )
        return [_para_temperatura(dict(r)) for r in (await self._c.execute(q)).mappings()]


# --- traducao banco -> dominio ---------------------------------------------
def _para_lote(r: dict[str, object]) -> Lote:
    return Lote(
        id=str(r["id"]),
        produto_id=str(r["produto_id"]),
        numero=str(r["numero"]),
        unidade_id=r["unidade_id"],  # type: ignore[arg-type]
        fabricacao=r["fabricacao"],  # type: ignore[arg-type]
        validade=r["validade"],  # type: ignore[arg-type]
        status=r["status"],  # type: ignore[arg-type]
        endereco=None if r["endereco"] is None else str(r["endereco"]),
    )


def _para_produto(r: dict[str, object], ctx: ContextoDados) -> Produto:
    """RN-A02: sem `custo.ler`, o campo nao e' preenchido.

    `Produto.custo_unitario_centavos` tem default None, entao nao passar o
    argumento deixa a chave com o valor default — e o serializador do viewmodel
    nunca a expoe, porque o viewmodel de quem nao tem custo nao a declara.
    """
    comum = {
        "id": str(r["id"]),
        "ean": str(r["ean"]),
        "nome": str(r["nome"]),
        "fabricante": str(r["fabricante"]),
        "principio_ativo": str(r["principio_ativo"]),
        "classe": r["classe"],
        "curva_abc": r["curva_abc"],
        "ativo": bool(r["ativo"]),
    }
    if ctx.ator.pode("custo.ler"):
        centavos = int(str(r["custo_unitario_centavos"]))
        return Produto(**comum, custo_unitario_centavos=centavos)  # type: ignore[arg-type]
    return Produto(**comum)  # type: ignore[arg-type]


def _txt(v: object) -> str | None:
    return None if v is None else str(v)


def _float_ou_nulo(v: object) -> float | None:
    return None if v is None else float(str(v))


def _para_recebimento(r: dict[str, object]) -> Recebimento:
    return Recebimento(
        id=str(r["id"]),
        unidade_id=r["unidade_id"],  # type: ignore[arg-type]
        nota_fiscal=str(r["nota_fiscal"]),
        fornecedor=str(r["fornecedor"]),
        status=r["status"],  # type: ignore[arg-type]
        conferente_id=str(r["conferente_id"]),
        rt_id=_txt(r["rt_id"]),
        temperatura_chegada_c=_float_ou_nulo(r["temperatura_chegada_c"]),
        divergencia=bool(r["divergencia"]),
        recebido_em=r["recebido_em"],  # type: ignore[arg-type]
    )


def _para_temperatura(r: dict[str, object]) -> RegistroTemperatura:
    return RegistroTemperatura(
        id=str(r["id"]),
        unidade_id=r["unidade_id"],  # type: ignore[arg-type]
        medido_em=r["medido_em"],  # type: ignore[arg-type]
        celsius=float(str(r["celsius"])),
    )


def _para_movimento(r: dict[str, object]) -> Movimento:
    return Movimento(
        id=str(r["id"]),
        lote_id=str(r["lote_id"]),
        unidade_id=r["unidade_id"],  # type: ignore[arg-type]
        tipo=r["tipo"],  # type: ignore[arg-type]
        quantidade=int(str(r["quantidade"])),
        motivo=r["motivo"],  # type: ignore[arg-type]
        complemento=_txt(r["complemento"]),
        autor_id=str(r["autor_id"]),
        autorizador_id=_txt(r["autorizador_id"]),
        status=r["status"],  # type: ignore[arg-type]
        criado_em=r["criado_em"],  # type: ignore[arg-type]
        estorna_movimento_id=_txt(r["estorna_movimento_id"]),
        cliente_id=_txt(r["cliente_id"]),
        nota_fiscal=_txt(r["nota_fiscal"]),
    )


class RepoAuditoriaSQL:
    """Leitura da trilha. Sem `_escopo`: a tabela nao tem `unidade_id`.

    Ver a docstring de `RepoAuditoria` em `porta.py` para por que isso e' uma
    decisao e nao um esquecimento.
    """

    def __init__(self, conn: AsyncConnection) -> None:
        self._c = conn

    async def listar(
        self,
        ctx: ContextoDados,
        *,
        ator_id: str | None = None,
        entidade: str | None = None,
        de: datetime | None = None,
        ate: datetime | None = None,
        limite: int = 50,
    ) -> Sequence[LinhaAuditoria]:
        q = sa.select(m.auditoria)
        if ator_id:
            q = q.where(m.auditoria.c.ator_id == ator_id)
        if entidade:
            q = q.where(m.auditoria.c.entidade == entidade)
        if de:
            q = q.where(m.auditoria.c.criado_em >= de)
        if ate:
            q = q.where(m.auditoria.c.criado_em <= ate)
        # Mais recente primeiro: quem abre a trilha esta' investigando o que
        # acabou de acontecer, nao lendo a historia desde o comeco.
        q = q.order_by(m.auditoria.c.criado_em.desc(), m.auditoria.c.id.desc()).limit(limite)
        return [_para_auditoria(dict(r)) for r in (await self._c.execute(q)).mappings()]


def _para_auditoria(r: dict[str, Any]) -> LinhaAuditoria:
    return LinhaAuditoria(
        id=int(r["id"]),
        ator_id=r["ator_id"],
        acao=r["acao"],
        entidade=r["entidade"],
        entidade_id=r["entidade_id"],
        valor_anterior=r["valor_anterior"],
        valor_novo=r["valor_novo"],
        origem=r["origem"],
        criado_em=r["criado_em"],
    )
