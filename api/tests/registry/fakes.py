"""Repositorios falsos e um estoque pequeno, para exercitar `load` e `select`.

Por que falso e nao o banco: `load` e `select` sao a fronteira que este projeto
precisa provar — escopo, campo restrito, status efetivo, pureza. Um teste contra
Postgres provaria as mesmas coisas mais devagar, e nao provaria nenhuma a mais.
Imutabilidade, essa sim, so' o banco prova, e esta' em `tests/data/`.

**O falso implementa a intersecao de escopo do jeito que a porta manda**
(`data/porta.py`, RN-A01): pedido para unidade fora do ator devolve vazio. Isso
prova que o COMPONENTE nao contorna a porta — nao prova que o adaptador real
intersecta, que e' responsabilidade da T-007.

O estoque foi montado para os casos dificeis, nao para parecer real:

  l-amox-mtz / l-amox-uber   mesmo numero, unidades diferentes (RN-L08)
  l-amox-venc                liberado no banco, VENCIDO de fato (ADR-0022)
  l-vac-quar                 quarentena em dia
  l-vac-quar-venc            venceu DENTRO da quarentena — o pior caso
  l-rital-bloq               bloqueado por decisao humana
  l-amox-zero                entrada e saida iguais: saldo zero, `esgotado`
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Any

from estoque.data.porta import ContextoDados, Repositorios
from estoque.domain.identidade import Ator, UnidadeId
from estoque.domain.tipos import (
    Lote,
    Movimento,
    Produto,
    StatusLoteRegistrado,
)
from estoque.registry.definir import LoadContext, Pagina

HOJE = date.today()
AGORA = datetime(2026, 9, 1, 10, 0, 0)


def _lote(
    lote_id: str,
    produto_id: str,
    numero: str,
    unidade: str,
    status: StatusLoteRegistrado,
    dias_ate_vencer: int,
) -> Lote:
    return Lote(
        id=lote_id,
        produto_id=produto_id,
        numero=numero,
        unidade_id=unidade,  # type: ignore[arg-type]
        fabricacao=HOJE - timedelta(days=120),
        validade=HOJE + timedelta(days=dias_ate_vencer),
        status=status,
        endereco=f"A-{lote_id[-2:]}",
    )


PRODUTOS: dict[str, Produto] = {
    "p-amox": Produto(
        id="p-amox",
        ean="7891234000018",
        nome="Amoxicilina 500mg",
        fabricante="Medquimica",
        principio_ativo="amoxicilina",
        classe="antimicrobiano",
        curva_abc="A",
        ativo=True,
        # Presente aqui de PROPOSITO: se um componente vazasse custo, o teste
        # AC-6 pegaria. Custo ausente no fixture faria o teste passar por
        # acidente, provando nada.
        custo_unitario_centavos=1250,
    ),
    "p-vac": Produto(
        id="p-vac",
        ean="7891234000025",
        nome="Vacina Influenza",
        fabricante="Butantan",
        principio_ativo="influenza",
        classe="termolabil",
        curva_abc="A",
        ativo=True,
        custo_unitario_centavos=4800,
    ),
    "p-rital": Produto(
        id="p-rital",
        ean="7891234000032",
        nome="Metilfenidato 10mg",
        fabricante="Novartis",
        principio_ativo="metilfenidato",
        classe="controlado",
        curva_abc="B",
        ativo=True,
        custo_unitario_centavos=3300,
    ),
}

LOTES: list[Lote] = [
    _lote("l-amox-mtz", "p-amox", "AMX2401", "cd-matriz", "liberado", 200),
    # Mesmo NUMERO do de cima, outra unidade: dois registros (RN-L08).
    _lote("l-amox-uber", "p-amox", "AMX2401", "filial-uberlandia", "liberado", 200),
    _lote("l-amox-venc", "p-amox", "AMX2312", "cd-matriz", "liberado", -10),
    _lote("l-amox-zero", "p-amox", "AMX2405", "cd-matriz", "liberado", 300),
    _lote("l-vac-quar", "p-vac", "VAC2402", "cd-refrigerado", "quarentena", 400),
    _lote("l-vac-quar-venc", "p-vac", "VAC2301", "cd-refrigerado", "quarentena", -3),
    _lote("l-rital-bloq", "p-rital", "RIT2401", "cd-matriz", "bloqueado", 500),
    _lote("l-vac-uber-quar", "p-vac", "VAC2403", "filial-uberlandia", "quarentena", 250),
]


def _mov(
    mid: str,
    lote: Lote,
    tipo: str,
    qtd: int,
    motivo: str,
    *,
    autorizador: str | None = None,
    dias_atras: int = 0,
) -> Movimento:
    return Movimento(
        id=mid,
        lote_id=lote.id,
        unidade_id=lote.unidade_id,
        tipo=tipo,  # type: ignore[arg-type]
        quantidade=qtd,
        motivo=motivo,  # type: ignore[arg-type]
        complemento=None,
        autor_id="u-cleide",
        autorizador_id=autorizador,
        status="efetivado",
        criado_em=AGORA - timedelta(days=dias_atras),
        estorna_movimento_id=None,
        cliente_id=None,
        nota_fiscal=None,
    )


_POR_ID = {lote.id: lote for lote in LOTES}

MOVIMENTOS: list[Movimento] = [
    _mov("m-01", _POR_ID["l-amox-mtz"], "entrada", 500, "recebimento", dias_atras=30),
    _mov("m-02", _POR_ID["l-amox-mtz"], "saida", 120, "venda", dias_atras=10),
    _mov("m-03", _POR_ID["l-amox-uber"], "entrada", 200, "recebimento", dias_atras=28),
    _mov("m-04", _POR_ID["l-amox-venc"], "entrada", 80, "recebimento", dias_atras=200),
    # Entra e sai tudo: saldo zero, status efetivo `esgotado` (ADR-0022).
    _mov("m-05", _POR_ID["l-amox-zero"], "entrada", 60, "recebimento", dias_atras=40),
    _mov("m-06", _POR_ID["l-amox-zero"], "saida", 60, "venda", dias_atras=5),
    _mov("m-07", _POR_ID["l-vac-quar"], "entrada", 300, "recebimento", dias_atras=12),
    _mov("m-08", _POR_ID["l-vac-quar-venc"], "entrada", 150, "recebimento", dias_atras=90),
    _mov(
        "m-09",
        _POR_ID["l-rital-bloq"],
        "entrada",
        40,
        "recebimento",
        autorizador="u-helena",
        dias_atras=20,
    ),
    _mov("m-10", _POR_ID["l-vac-uber-quar"], "entrada", 90, "recebimento", dias_atras=8),
]

SINAL = {"entrada": 1, "estorno": 1, "saida": -1, "descarte": -1}


class FakeTx:
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class FakeRepoLote:
    """Intersecta com as unidades do ator ANTES de qualquer criterio (RN-A01).

    A ordem importa: filtrar primeiro pelo `unidade_id` pedido e so' depois
    intersectar produziria o mesmo resultado aqui, mas ensinaria o padrao
    errado — a intersecao e' invariante da porta, nao passo do filtro.
    """

    def _visiveis(self, ctx: ContextoDados) -> list[Lote]:
        return [lote for lote in LOTES if lote.unidade_id in ctx.unidades_permitidas]

    async def por_id(self, lote_id: str, ctx: ContextoDados) -> Lote | None:
        return next((lote for lote in self._visiveis(ctx) if lote.id == lote_id), None)

    async def listar(
        self,
        ctx: ContextoDados,
        *,
        produto_id: str | None = None,
        unidade_id: UnidadeId | None = None,
        status: StatusLoteRegistrado | None = None,
        validade_ate: date | None = None,
    ) -> Sequence[Lote]:
        sel = self._visiveis(ctx)
        if produto_id is not None:
            sel = [lote for lote in sel if lote.produto_id == produto_id]
        if unidade_id is not None:
            sel = [lote for lote in sel if lote.unidade_id == unidade_id]
        if status is not None:
            sel = [lote for lote in sel if lote.status == status]
        if validade_ate is not None:
            sel = [lote for lote in sel if lote.validade <= validade_ate]
        return sorted(sel, key=lambda lote: (lote.validade, lote.id))

    async def saldos(self, lote_ids: Sequence[str], ctx: ContextoDados) -> dict[str, int]:
        """RN-M06: saldo e' soma de movimento. Nao existe coluna `saldo`, e o
        falso tambem nao tem uma — se tivesse, o AC-3 nao provaria nada."""
        visiveis = {lote.id for lote in self._visiveis(ctx)}
        saldo: dict[str, int] = {i: 0 for i in lote_ids if i in visiveis}
        for m in MOVIMENTOS:
            if m.lote_id in saldo and m.status == "efetivado":
                saldo[m.lote_id] += SINAL[m.tipo] * m.quantidade
        return saldo


class FakeRepoProduto:
    def _visivel(self, p: Produto, ctx: ContextoDados) -> Produto:
        """RN-A02: custo chega AUSENTE para quem nao tem `custo.ler`.

        O dataclass e' frozen, entao "ausente" aqui e' `None` — a porta real
        omite a chave na serializacao. O que este falso garante e' que o custo
        so' esta' disponivel a quem pode, e o AC-6 checa o outro lado: nenhum
        dos quatro componentes leva custo ao viewmodel, nem para quem pode.
        """
        if "custo.ler" in ctx.ator.permissoes:
            return p
        return replace(p, custo_unitario_centavos=None)

    async def por_id(self, produto_id: str, ctx: ContextoDados) -> Produto | None:
        p = PRODUTOS.get(produto_id)
        return self._visivel(p, ctx) if p else None

    async def por_ids(self, ids: Sequence[str], ctx: ContextoDados) -> dict[str, Produto]:
        return {i: self._visivel(PRODUTOS[i], ctx) for i in set(ids) if i in PRODUTOS}


class FakeRepoMovimento:
    def _visiveis(self, ctx: ContextoDados) -> list[Movimento]:
        return [m for m in MOVIMENTOS if m.unidade_id in ctx.unidades_permitidas]

    async def do_lote(self, lote_id: str, ctx: ContextoDados) -> Sequence[Movimento]:
        sel = [m for m in self._visiveis(ctx) if m.lote_id == lote_id]
        return sorted(sel, key=lambda m: (m.criado_em, m.id))

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
        sel = self._visiveis(ctx)
        if unidade_id is not None:
            sel = [m for m in sel if m.unidade_id == unidade_id]
        if tipo is not None:
            sel = [m for m in sel if m.tipo == tipo]
        if status is not None:
            sel = [m for m in sel if m.status == status]
        if de is not None:
            sel = [m for m in sel if m.criado_em >= de]
        if ate is not None:
            sel = [m for m in sel if m.criado_em <= ate]
        return sorted(sel, key=lambda m: (m.criado_em, m.id))

    async def por_cliente(
        self, cliente_id: str, de: date, ate: date, ctx: ContextoDados
    ) -> Sequence[Movimento]:
        return [m for m in self._visiveis(ctx) if m.cliente_id == cliente_id]


class _NaoUsado:
    """Recebimento e temperatura nao pertencem a nenhum componente de lote.

    Explode em vez de devolver vazio: um `load` que os chamasse sem querer
    passaria despercebido com lista vazia, e falharia so' em producao.
    """

    def __getattr__(self, nome: str) -> Any:
        msg = f"componente de lote nao deveria chamar {nome!r}"
        raise AssertionError(msg)


def contexto(ator: Ator, *, limite: int = 20, cursor: str | None = None) -> LoadContext:
    dados = ContextoDados(ator=ator, unidades_permitidas=ator.unidades, tx=FakeTx())
    return LoadContext(
        ator=ator,
        unidades_permitidas=ator.unidades,
        repos=Repositorios(
            lote=FakeRepoLote(),
            produto=FakeRepoProduto(),
            movimento=FakeRepoMovimento(),
            recebimento=_NaoUsado(),  # type: ignore[arg-type]
            temperatura=_NaoUsado(),  # type: ignore[arg-type]
        ),
        dados=dados,
        pagina=Pagina(limite=limite, cursor=cursor),
    )
