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
from datetime import UTC, date, datetime, timedelta

from estoque.application.registry.definir import LoadContext, Pagina
from estoque.data.porta import ContextoDados, LinhaAuditoria, Repositorios
from estoque.domain.identidade import Ator, UnidadeId
from estoque.domain.tipos import (
    Lote,
    Movimento,
    Produto,
    Recebimento,
    RegistroTemperatura,
    StatusLoteRegistrado,
)

HOJE = date.today()
# COM fuso, porque a coluna real e' `timestamptz` e CONTRATOS §10 manda
# "datetime com timezone, sempre do servidor".
#
# ACHADO (familia do A-11): estava ingenuo. `lote_movimentos` nao percebia
# porque compara `.date()`, mas `movimento_lista` passa o corte como `datetime`
# ao repositorio — e ai o falso quebra onde o real funciona. Fake que diverge do
# adaptador e' o achado A-11 outra vez, agora no tipo do dado e nao no escopo.
AGORA = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)


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
    # T-023 AC-4: um lote do CD Refrigerado que so' entra DEPOIS da excursao de
    # calor da serie TEMPERATURAS (ver `m-13`). E' o par negativo do vinculo do
    # RN-F04 — nao estava na camara quando a temperatura subiu.
    _lote("l-vac-ref-tardio", "p-vac", "VAC2410", "cd-refrigerado", "quarentena", 300),
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
    status: str = "efetivado",
    estorna: str | None = None,
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
        status=status,  # type: ignore[arg-type]
        criado_em=AGORA - timedelta(days=dias_atras),
        estorna_movimento_id=estorna,
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
    # --- os dois casos que T-024 precisa, e que faltavam ---------------------
    # Saida de CONTROLADO esperando a segunda identificacao (RN-C01). E' o que
    # `movimento_lista(status=aguardando_autorizacao)` encontra, e a base do
    # CA-04: nao mexe no saldo enquanto pendente.
    _mov(
        "m-11",
        _POR_ID["l-rital-bloq"],
        "saida",
        5,
        "venda",
        dias_atras=4,
        status="aguardando_autorizacao",
    ),
    # Par estorno/original (RN-M03): os DOIS ficam visiveis. `m-02` foi uma saida
    # de 120 que `m-12` corrige — e a lista tem de mostrar o erro E a correcao,
    # nao um estado limpo que finge que o erro nunca existiu.
    _mov(
        "m-12",
        _POR_ID["l-amox-mtz"],
        "estorno",
        120,
        "estorno",
        dias_atras=9,
        estorna="m-02",
    ),
    # T-023 AC-4: entrada de `l-vac-ref-tardio` HOJE (AGORA) — depois da excursao
    # da serie TEMPERATURAS (i=5,6, ~AGORA-42h a -36h). O `temperatura_excursoes`
    # nao deve vincular este lote: ele nao estava na camara quando subiu.
    _mov("m-13", _POR_ID["l-vac-ref-tardio"], "entrada", 100, "recebimento", dias_atras=0),
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


# Trilha de auditoria montada para o caso dificil do AC-5: uma linha COM custo.
#
# Se a trilha do fixture nao tivesse custo, o teste de vazamento passaria por
# ausencia de dado — o mesmo motivo de `PRODUTOS` ter custo de proposito.
TRILHA: list[LinhaAuditoria] = [
    LinhaAuditoria(
        id=3,
        ator_id="u-helena",
        acao="lote_liberar_quarentena",
        entidade="lote",
        entidade_id="l-vac-quar",
        valor_anterior={"status": "quarentena"},
        valor_novo={"status": "liberado", "justificativa": "conferencia completa"},
        origem="tela",
        criado_em=AGORA,
    ),
    LinhaAuditoria(
        id=2,
        ator_id="u-ivo",
        acao="movimento_saida",
        entidade="movimento",
        entidade_id="m-99",
        valor_anterior={"lote_id": "l-amox-mtz", "saldo": 500},
        # O custo NAO deveria estar aqui, e por isso esta': o AC-5 e' sobre a
        # trilha continuar segura mesmo quando um comando futuro escrever demais.
        valor_novo={
            "quantidade": 10,
            "custo_unitario_centavos": 1250,
            "total_centavos": 12500,
        },
        origem="assistente",
        criado_em=AGORA,
    ),
    LinhaAuditoria(
        id=1,
        ator_id="u-sandra",
        acao="ler",
        entidade="auditoria_trilha",
        entidade_id=None,
        valor_anterior=None,
        valor_novo={"params": {}},
        origem="assistente",
        criado_em=AGORA,
    ),
]


class FakeRepoAuditoria:
    """Sem escopo de unidade — a tabela real nao tem `unidade_id`. Ver `porta.py`."""

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
        linhas = list(TRILHA)
        if ator_id:
            linhas = [x for x in linhas if x.ator_id == ator_id]
        if entidade:
            linhas = [x for x in linhas if x.entidade == entidade]
        if de:
            linhas = [x for x in linhas if x.criado_em >= de]
        if ate:
            linhas = [x for x in linhas if x.criado_em <= ate]
        return sorted(linhas, key=lambda x: (x.criado_em, x.id), reverse=True)[:limite]


# --- recebimento e temperatura (T-047) -----------------------------------
#
# Antes eram `_NaoUsado()`: explodia em qualquer acesso, porque nenhum
# componente os tocava. T-022 e T-023 mudam isso. Os fakes abaixo intersectam
# escopo do MESMO jeito que a porta manda (RN-A01) — fake permissivo faz a
# suite passar sobre um buraco (achado A-11).

RECEBIMENTOS: list[Recebimento] = [
    # normal: nota conferida, sem divergencia, nao controlado, nao termolabil
    Recebimento(
        id="r-normal-mtz",
        unidade_id="cd-matriz",
        nota_fiscal="NF-70001",
        fornecedor="Distribuidora Alfa",
        status="conferido",
        conferente_id="u-cleide",
        rt_id=None,
        temperatura_chegada_c=None,
        divergencia=False,
        recebido_em=AGORA - timedelta(days=10),
    ),
    # RN-R04: divergencia entre nota e fisico, pendencia aberta, nao impede
    Recebimento(
        id="r-diverg-mtz",
        unidade_id="cd-matriz",
        nota_fiscal="NF-70002",
        fornecedor="Distribuidora Beta",
        status="conferido",
        conferente_id="u-cleide",
        rt_id=None,
        temperatura_chegada_c=None,
        divergencia=True,
        recebido_em=AGORA - timedelta(days=7),
    ),
    # RN-R05: controlado exige dupla identificacao (conferente E RT)
    Recebimento(
        id="r-controlado-mtz",
        unidade_id="cd-matriz",
        nota_fiscal="NF-70003",
        fornecedor="Cristalia",
        status="liberado",
        conferente_id="u-cleide",
        rt_id="u-helena",
        temperatura_chegada_c=None,
        divergencia=False,
        recebido_em=AGORA - timedelta(days=5),
    ),
    # RN-F01: termolabil exige temperatura de chegada
    Recebimento(
        id="r-termo-ref",
        unidade_id="cd-refrigerado",
        nota_fiscal="NF-70004",
        fornecedor="Butantan",
        status="conferido",
        conferente_id="u-cleide",
        rt_id=None,
        temperatura_chegada_c=5.4,
        divergencia=False,
        recebido_em=AGORA - timedelta(days=3),
    ),
    # so' em Uberlandia — para o teste de escopo (Odair ve so' este)
    Recebimento(
        id="r-uber",
        unidade_id="filial-uberlandia",
        nota_fiscal="NF-70005",
        fornecedor="Distribuidora Gama",
        status="rascunho",
        conferente_id="u-odair",
        rt_id=None,
        temperatura_chegada_c=None,
        divergencia=False,
        recebido_em=AGORA - timedelta(days=1),
    ),
]

# Serie curta de temperatura em CD Refrigerado, com UMA excursao de calor.
TEMPERATURAS: list[RegistroTemperatura] = [
    RegistroTemperatura(
        id=f"t-{i:03d}",
        unidade_id="cd-refrigerado",
        medido_em=AGORA - timedelta(hours=6 * (12 - i)),
        celsius=5.0 if i not in (5, 6) else 9.8,  # i=5,6: excursao acima de 8
    )
    for i in range(13)
]


class FakeRepoRecebimento:
    """Intersecta escopo antes de qualquer criterio (RN-A01)."""

    def _visiveis(self, ctx: ContextoDados) -> list[Recebimento]:
        return [r for r in RECEBIMENTOS if r.unidade_id in ctx.unidades_permitidas]

    async def por_id(self, rid: str, ctx: ContextoDados) -> Recebimento | None:
        return next((r for r in self._visiveis(ctx) if r.id == rid), None)

    async def listar(self, ctx: ContextoDados) -> Sequence[Recebimento]:
        # Mesma ordem do repositorio real: `recebido_em` desc, `id` asc no empate.
        por_id_asc = sorted(self._visiveis(ctx), key=lambda r: r.id)
        return sorted(por_id_asc, key=lambda r: r.recebido_em, reverse=True)


class FakeRepoTemperatura:
    async def serie(
        self, unidade_id: str, de: datetime, ate: datetime, ctx: ContextoDados
    ) -> Sequence[RegistroTemperatura]:
        if unidade_id not in ctx.unidades_permitidas:
            return []
        sel = [
            t for t in TEMPERATURAS if t.unidade_id == unidade_id and de <= t.medido_em <= ate
        ]
        return sorted(sel, key=lambda t: t.medido_em)


def contexto(ator: Ator, *, limite: int = 20, cursor: str | None = None) -> LoadContext:
    dados = ContextoDados(ator=ator, unidades_permitidas=ator.unidades, tx=FakeTx())
    return LoadContext(
        ator=ator,
        unidades_permitidas=ator.unidades,
        repos=Repositorios(
            lote=FakeRepoLote(),
            produto=FakeRepoProduto(),
            movimento=FakeRepoMovimento(),
            auditoria=FakeRepoAuditoria(),
            recebimento=FakeRepoRecebimento(),
            temperatura=FakeRepoTemperatura(),
        ),
        dados=dados,
        pagina=Pagina(limite=limite, cursor=cursor),
    )
