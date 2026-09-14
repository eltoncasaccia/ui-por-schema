"""T-046 — minimo e maximo por produto E por unidade (`RN-P06`).

Mesma forma da T-048: a bateria roda contra o fake e contra o repositorio real,
cada lado com o SEU dado e o esperado lido da MESMA fonte que o alimentou —
`fakes.FAIXAS` de um lado, `dados.faixas_de_estoque()` (arbitradas, via seed)
do outro. Constante copiada entre os dois lados faria a bateria comparar coisas
diferentes e passar.

Pula sem banco: `make db-local && make migrate && make seed`, e `make db-local`
DE NOVO (o `migrate` recria o container sem a porta).
"""

import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from estoque.application.registry.componentes.produto_saldo_por_unidade import (
    VM,
    Params,
    carregar,
    projetar,
)
from estoque.data.porta import ContextoDados
from estoque.data.repositorios import RepoProdutoSQL
from estoque.data.seed import dados as seed
from estoque.domain.identidade import Ator, UnidadeId
from estoque.domain.tipos import FaixaEstoque
from estoque.server.config import Config

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "registry"))
import fakes

TODAS = frozenset({"cd-matriz", "cd-refrigerado", "filial-uberlandia"})
URL_DONO = os.environ.get(
    "DATABASE_URL_TESTE", "postgresql+psycopg://estoque:troque-isto@localhost:15432/estoque"
)
PRODUTO_SECO = next(str(p[0]) for p in seed.PRODUTOS if p[5] != "termolabil")


class _TxNula:
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class PortaFaixas(Protocol):
    async def faixas(
        self, produto_id: str, ctx: ContextoDados
    ) -> dict[UnidadeId, FaixaEstoque]: ...


def _ctx(unidades: frozenset[str]) -> ContextoDados:
    ator = Ator(
        id="u-teste-046",
        nome="Teste 046",
        papel="diretor",
        unidades=unidades,  # type: ignore[arg-type]
        permissoes=frozenset({"produto.ler", "lote.ler"}),
        ativo=True,
    )
    return ContextoDados(ator=ator, unidades_permitidas=unidades, tx=_TxNula())  # type: ignore[arg-type]


async def _bateria(
    repo: PortaFaixas, produto_id: str, esperado: dict[str, tuple[int, int]]
) -> None:
    todas = await repo.faixas(produto_id, _ctx(TODAS))
    assert {u: (f.minimo, f.maximo) for u, f in todas.items()} == esperado

    # AC-1 · o mesmo produto, faixas diferentes por unidade
    assert esperado["cd-matriz"] != esperado["filial-uberlandia"]

    # AC-2 · escopo antes do criterio: a unidade de fora nao aparece
    ribeirao = await repo.faixas(produto_id, _ctx(frozenset({"cd-matriz", "cd-refrigerado"})))
    assert "filial-uberlandia" not in ribeirao
    uber = await repo.faixas(produto_id, _ctx(frozenset({"filial-uberlandia"})))
    assert set(uber) == {"filial-uberlandia"}

    assert await repo.faixas("p-inexistente-046", _ctx(TODAS)) == {}


# ------------------------------------------------------------ AC-3 · o fake
async def test_ac3_bateria_contra_o_fake() -> None:
    esperado: dict[str, tuple[int, int]] = {
        f.unidade_id: (f.minimo, f.maximo) for f in fakes.FAIXAS if f.produto_id == "p-amox"
    }
    await _bateria(fakes.FakeRepoProduto(), "p-amox", esperado)


# ------------------------------------------------- AC-3 · o repositorio real
def _url() -> str:
    return Config.do_ambiente().database_url.replace("@db:5432", "@localhost:15432")


@pytest.fixture
async def conexao() -> AsyncIterator[AsyncConnection]:
    try:
        eng = create_async_engine(_url(), future=True)
        async with eng.connect() as c:
            yield c
        await eng.dispose()
    except Exception:
        pytest.skip("sem banco: rode `make db-local && make migrate && make seed`")


async def test_ac3_bateria_contra_o_repositorio_real(conexao: AsyncConnection) -> None:
    esperado = {u: (mn, mx) for p, u, mn, mx in seed.faixas_de_estoque() if p == PRODUTO_SECO}
    await _bateria(RepoProdutoSQL(conexao), PRODUTO_SECO, esperado)


async def test_a_aplicacao_so_le_faixa(conexao: AsyncConnection) -> None:
    """Sem escrita de faixa no ciclo 1, o papel da aplicacao nao pode inserir."""
    with pytest.raises(Exception) as recusa:
        await conexao.execute(
            sa.text("INSERT INTO produto_unidade VALUES (:p, 'cd-refrigerado', 1, 2)"),
            {"p": PRODUTO_SECO},
        )
    assert "permission" in str(recusa.value).lower()
    await conexao.rollback()


# ------------------------------------------------------ AC-6 · CHECK no banco
def _dono() -> sa.Engine:
    try:
        eng = sa.create_engine(URL_DONO, connect_args={"connect_timeout": 2})
        with eng.connect():
            pass
    except Exception:
        pytest.skip("sem banco: rode `make db-local && make migrate && make seed`")
    return eng


@pytest.mark.parametrize(("minimo", "maximo"), [(100, 99), (-1, 10)])
def test_ac6_o_banco_recusa_faixa_invalida(minimo: int, maximo: int) -> None:
    with _dono().connect() as c:
        with pytest.raises(sa.exc.IntegrityError):
            c.execute(
                sa.text("INSERT INTO produto_unidade VALUES (:p, 'cd-refrigerado', :mn, :mx)"),
                {"p": PRODUTO_SECO, "mn": minimo, "mx": maximo},
            )
        c.rollback()


def test_ac6_contraponto_faixa_valida_entra() -> None:
    """Sem ele, uma tabela que recusasse tudo passaria no teste acima."""
    with _dono().connect() as c:
        c.execute(
            sa.text("INSERT INTO produto_unidade VALUES (:p, 'cd-refrigerado', 10, 10)"),
            {"p": PRODUTO_SECO},
        )
        n = c.execute(
            sa.text(
                "SELECT count(*) FROM produto_unidade "
                "WHERE produto_id=:p AND unidade_id='cd-refrigerado'"
            ),
            {"p": PRODUTO_SECO},
        ).scalar_one()
        assert n == 1
        c.rollback()


# ------------------------------------- AC-4 · a faixa na tela, com a marcacao
async def _vm(ator: Ator, produto_id: str) -> VM:
    return projetar(await carregar(Params(produto_id=produto_id), fakes.contexto(ator)))


async def test_ac4_abaixo_do_minimo_e_marcado(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["marco"], "p-vac")
    ref = next(x for x in vm.linhas if x.unidade_id == "cd-refrigerado")
    assert (ref.saldo, ref.minimo, ref.maximo, ref.abaixo_do_minimo) == (550, 600, 1200, True)


async def test_ac4_dentro_da_faixa_nao_e_marcado(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["marco"], "p-amox")
    por = {x.unidade_id: x for x in vm.linhas}
    assert (por["cd-matriz"].minimo, por["cd-matriz"].maximo) == (200, 800)
    assert (por["filial-uberlandia"].minimo, por["filial-uberlandia"].maximo) == (50, 300)
    assert not any(x.abaixo_do_minimo for x in vm.linhas)


async def test_ac4_unidade_sem_faixa_nao_e_marcada(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["marco"], "p-vac")
    uber = next(x for x in vm.linhas if x.unidade_id == "filial-uberlandia")
    assert uber.minimo is None
    assert not uber.abaixo_do_minimo


async def test_ac2_odair_so_ve_a_faixa_de_uberlandia(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["odair"], "p-amox")
    assert [(x.unidade_id, x.minimo, x.maximo) for x in vm.linhas] == [
        ("filial-uberlandia", 50, 300)
    ]
