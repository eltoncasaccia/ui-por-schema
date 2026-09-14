"""A bateria unica da porta de dados — T-042.

Derivada de `data/porta.py` e das regras, NAO do fake: o fake e' candidato a
estar errado (achado A-11). Os dois lados rodam as mesmas funcoes sobre os
MESMOS dados: o fake os tem em memoria, e o teste do repositorio real grava
exatamente `LOTES_SEMENTE`/`MOVIMENTOS_SEMENTE` numa transacao desfeita no fim.
"""

import inspect
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from estoque.data import porta
from estoque.data.porta import (
    ContextoDados,
    RepoAuditoria,
    RepoLote,
    RepoMovimento,
    RepoProduto,
)
from estoque.data.repositorios import LIMITE_MOVIMENTOS
from estoque.domain.identidade import Ator
from estoque.domain.tipos import Lote, Movimento

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "registry"))
import fakes as fakes  # reexportado: o teste nao consegue importar antes do path

TODAS = frozenset({"cd-matriz", "cd-refrigerado", "filial-uberlandia"})
IVO = frozenset({"cd-matriz", "cd-refrigerado"})
AGORA = fakes.AGORA
FUTURO = datetime(2090, 1, 1, tzinfo=UTC)
CLIENTE = "c-contrato-042"

# AC-4: todo metodo de todo Protocol `Repo*` tem de ter linha aqui.
COBERTURA: dict[str, dict[str, str]] = {
    "RepoLote": {"por_id": "bateria_lote", "listar": "bateria_lote", "saldos": "bateria_lote"},
    "RepoProduto": {
        "por_id": "bateria_produto",
        "por_ids": "bateria_produto",
        "por_ean": "tests/data/test_produto_por_ean.py (T-048)",
        "faixas": "tests/data/test_minimo_maximo.py (T-046)",
    },
    "RepoMovimento": {
        "do_lote": "bateria_movimento",
        "listar": "bateria_movimento",
        "por_cliente": "bateria_movimento",
    },
    "RepoRecebimento": {
        "por_id": "tests/data/test_repos_recebimento_temperatura.py (T-047)",
        "listar": "tests/data/test_repos_recebimento_temperatura.py (T-047)",
    },
    "RepoTemperatura": {"serie": "tests/data/test_repos_recebimento_temperatura.py (T-047)"},
    "RepoAuditoria": {"listar": "bateria_auditoria"},
}


def metodos_da_porta() -> dict[str, set[str]]:
    return {
        nome: {m for m, v in vars(cls).items() if inspect.iscoroutinefunction(v)}
        for nome, cls in vars(porta).items()
        if inspect.isclass(cls)
        and nome.startswith("Repo")
        and getattr(cls, "_is_protocol", False)
    }


class _TxNula:
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


def ctx(unidades: frozenset[str], *, custo: bool = False) -> ContextoDados:
    permissoes = {"lote.ler", "produto.ler", "movimento.ler", "auditoria.ler"}
    if custo:
        permissoes.add("custo.ler")
    ator = Ator(
        id="u-contrato-042",
        nome="Contrato 042",
        papel="diretor",
        unidades=unidades,  # type: ignore[arg-type]
        permissoes=frozenset(permissoes),  # type: ignore[arg-type]
        ativo=True,
    )
    return ContextoDados(ator=ator, unidades_permitidas=unidades, tx=_TxNula())  # type: ignore[arg-type]


# --- os dados que os dois lados enxergam --------------------------------------

LOTE_EXCESSO = Lote(
    id="l-contrato-042",
    produto_id="p-amox",
    numero="CTR042",
    unidade_id="cd-matriz",
    fabricacao=fakes.HOJE - timedelta(days=10),
    validade=fakes.HOJE + timedelta(days=700),
    status="liberado",
    endereco=None,
)


def _mov(mid: str, lote: Lote, criado_em: datetime, cliente: str | None = None) -> Movimento:
    return replace(
        fakes.MOVIMENTOS[0],
        id=mid,
        lote_id=lote.id,
        unidade_id=lote.unidade_id,
        tipo="saida",
        quantidade=1,
        motivo="venda",
        criado_em=criado_em,
        cliente_id=cliente,
    )


_UBER = next(lote for lote in fakes.LOTES if lote.id == "l-amox-uber")

EXTRAS: list[Movimento] = [
    _mov("m-ctr-cli-dentro", LOTE_EXCESSO, AGORA - timedelta(days=2), CLIENTE),
    _mov("m-ctr-cli-antes", LOTE_EXCESSO, AGORA - timedelta(days=30), CLIENTE),
    _mov("m-ctr-cli-uber", _UBER, AGORA - timedelta(days=2), CLIENTE),
    *(
        _mov(f"m-ctr-exc-{i:03d}", LOTE_EXCESSO, FUTURO + timedelta(minutes=i))
        for i in range(LIMITE_MOVIMENTOS + 1)
    ),
]

LOTES_SEMENTE: list[Lote] = [*fakes.LOTES, LOTE_EXCESSO]
MOVIMENTOS_SEMENTE: list[Movimento] = [*fakes.MOVIMENTOS, *EXTRAS]
IDS_FORA_DE_IVO = {lote.id for lote in LOTES_SEMENTE if lote.unidade_id not in IVO}


# --- as baterias --------------------------------------------------------------


async def bateria_lote(repo: RepoLote) -> None:
    ivo = ctx(IVO)
    esperados = {lote.id for lote in LOTES_SEMENTE if lote.unidade_id in IVO}
    semente = {lote.id for lote in LOTES_SEMENTE}

    # RN-A01: o escopo vem antes do criterio
    assert {x.id for x in await repo.listar(ivo)} & semente == esperados
    assert not {x.id for x in await repo.listar(ivo, status="quarentena")} & IDS_FORA_DE_IVO
    # ADR-0014: unidade fora do escopo e' vazio, nunca erro
    assert list(await repo.listar(ivo, unidade_id="filial-uberlandia")) == []
    assert await repo.por_id("l-amox-uber", ivo) is None
    assert await repo.por_id("l-amox-mtz", ivo) is not None

    # cursor depende de ordem estavel
    todos = list(await repo.listar(ctx(TODAS)))
    assert [(x.validade, x.id) for x in todos] == sorted((x.validade, x.id) for x in todos)

    # RN-M06: so' efetivado conta (m-11 pendente fica fora); RN-A01: fora do
    # escopo nem aparece no dicionario
    saldos = await repo.saldos(
        ["l-amox-mtz", "l-rital-bloq", "l-amox-zero", "l-amox-uber"], ivo
    )
    assert saldos == {"l-amox-mtz": 500, "l-rital-bloq": 40, "l-amox-zero": 0}


async def bateria_produto(repo: RepoProduto) -> None:
    com, sem = ctx(TODAS, custo=True), ctx(TODAS)
    p = await repo.por_id("p-amox", com)
    assert p is not None
    assert p.custo_unitario_centavos == 1250
    # RN-A02: ausente para quem nao pode — e o resto do produto continua chegando
    q = await repo.por_id("p-amox", sem)
    assert q is not None
    assert q.custo_unitario_centavos is None
    assert q.nome == p.nome

    varios = await repo.por_ids(["p-amox", "p-vac", "p-amox"], sem)
    assert set(varios) == {"p-amox", "p-vac"}
    assert all(x.custo_unitario_centavos is None for x in varios.values())
    assert (await repo.por_ids(["p-vac"], com))["p-vac"].custo_unitario_centavos == 4800
    assert await repo.por_id("p-inexistente", com) is None


async def bateria_movimento(repo: RepoMovimento) -> None:
    ivo = ctx(IVO)
    assert list(await repo.do_lote("l-amox-uber", ivo)) == []
    assert [x.id for x in await repo.do_lote("l-amox-mtz", ivo)] == ["m-01", "m-02", "m-12"]
    assert list(await repo.listar(ivo, unidade_id="filial-uberlandia")) == []
    refrigerado = {
        x.id
        for x in await repo.listar(
            ivo, unidade_id="cd-refrigerado", de=AGORA - timedelta(days=100), ate=AGORA
        )
    }
    assert {"m-07", "m-08", "m-13"} <= refrigerado

    # A-31: periodo E escopo
    janela = await repo.por_cliente(
        CLIENTE, (AGORA - timedelta(days=5)).date(), AGORA.date(), ivo
    )
    assert {x.id for x in janela} == {"m-ctr-cli-dentro"}
    larga = await repo.por_cliente(
        CLIENTE, (AGORA - timedelta(days=60)).date(), AGORA.date(), ctx(TODAS)
    )
    assert {x.id for x in larga} == {"m-ctr-cli-dentro", "m-ctr-cli-antes", "m-ctr-cli-uber"}

    # A-39: teto, e o que sobra sao os MAIS RECENTES, em ordem decrescente
    ultimos = list(await repo.listar(ivo, de=FUTURO))
    assert len(ultimos) == LIMITE_MOVIMENTOS
    assert ultimos[0].id == f"m-ctr-exc-{LIMITE_MOVIMENTOS:03d}"
    assert "m-ctr-exc-000" not in {x.id for x in ultimos}


async def bateria_auditoria(repo: RepoAuditoria, *, ator_id: str | None, total: int) -> None:
    """Sem escopo de unidade, de proposito: a tabela nao tem `unidade_id`."""
    todas = [x.id for x in await repo.listar(ctx(TODAS), ator_id=ator_id)]
    uma = [
        x.id for x in await repo.listar(ctx(frozenset({"filial-uberlandia"})), ator_id=ator_id)
    ]
    assert len(todas) == total
    assert uma == todas
    assert todas == sorted(todas, reverse=True)
    assert len(await repo.listar(ctx(TODAS), ator_id=ator_id, limite=total - 1)) == total - 1
