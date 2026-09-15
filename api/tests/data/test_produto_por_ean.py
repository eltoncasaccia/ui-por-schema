"""T-048 — `RepoProduto.por_ean`, o caminho que o leitor de código de barras usa.

**A mesma bateria roda contra o fake E contra o repositório real** (AC-4). É o
achado A-11 aplicado desde o primeiro dia deste método: um fake mais permissivo
que o adaptador faria a suíte de T-026 passar sobre um buraco, e o buraco aqui
seria custo vazando para quem não tem `custo.ler`.

Pula sem banco: `make db-local && make db-teste`.
"""

import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Protocol

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from estoque.data.porta import ContextoDados
from estoque.data.repositorios import RepoProdutoSQL
from estoque.domain.identidade import Ator
from estoque.domain.tipos import Produto
from estoque.server.config import Config

# `fakes` mora em tests/registry/ e é importado por nome lá; daqui, garante o path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "registry"))
import fakes

TODAS = frozenset({"cd-matriz", "cd-refrigerado", "filial-uberlandia"})


class _TxNula:
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class PortaProduto(Protocol):
    async def por_ean(self, ean: str, ctx: ContextoDados) -> Produto | None: ...


def _ctx(*, custo: bool) -> ContextoDados:
    """`custo.ler` é o eixo do AC-2: o mesmo EAN, dois atores, dois resultados."""
    permissoes = {"produto.ler", "custo.ler"} if custo else {"produto.ler"}
    ator = Ator(
        id="u-teste-048",
        nome="Teste 048",
        papel="comprador" if custo else "conferente",
        unidades=TODAS,  # type: ignore[arg-type]
        permissoes=frozenset(permissoes),  # type: ignore[arg-type]
        ativo=True,
    )
    return ContextoDados(
        ator=ator,
        unidades_permitidas=TODAS,  # type: ignore[arg-type]
        tx=_TxNula(),
    )


async def _bateria(
    repo: PortaProduto, *, ean: str, produto_id: str, custo_esperado: int
) -> None:
    """A bateria que os dois lados têm de passar igual."""
    # AC-1 · acha pelo EAN
    achado = await repo.por_ean(ean, _ctx(custo=True))
    assert achado is not None, f"EAN {ean} não encontrado"
    assert achado.id == produto_id
    assert achado.ean == ean

    # AC-1 (negativo) · EAN que não existe
    assert await repo.por_ean("0000000000000", _ctx(custo=True)) is None

    # AC-1 (negativo) · o casamento é por IGUALDADE, não por prefixo.
    #
    # Este par nasceu de uma sabotagem que a suíte NÃO pegou: trocar o `==` por
    # `LIKE '<ean>%'` no repositório real passava em tudo, porque o EAN
    # inexistente acima não é prefixo de nada. Um leitor que lesse mal o último
    # dígito devolveria o produto errado — e produto errado num recebimento é
    # lote errado, com validade e classe erradas.
    assert await repo.por_ean(ean[:-1], _ctx(custo=True)) is None
    assert await repo.por_ean(ean + "0", _ctx(custo=True)) is None

    # AC-2 · custo presente para quem pode...
    assert achado.custo_unitario_centavos == custo_esperado
    # ...e AUSENTE para quem não pode. É o RN-A02, e o par negativo é o que vale.
    sem = await repo.por_ean(ean, _ctx(custo=False))
    assert sem is not None
    assert sem.custo_unitario_centavos is None
    # O resto do produto continua chegando: a omissão é do CUSTO, não do
    # produto. Sem isto, um `return None` faria o AC-2 passar sem servir a nada.
    assert sem.id == achado.id
    assert sem.nome == achado.nome


# --------------------------------------------------------------- o fake
async def test_ac4_bateria_contra_o_fake() -> None:
    vac = fakes.PRODUTOS["p-vac"]
    await _bateria(
        fakes.FakeRepoProduto(), ean=vac.ean, produto_id="p-vac", custo_esperado=4800
    )


async def test_ean_vazio_nao_acha_nada_no_fake() -> None:
    """Sem isto, um fake que fizesse `startswith` passaria na bateria."""
    assert await fakes.FakeRepoProduto().por_ean("", _ctx(custo=True)) is None


# ------------------------------------------------- o repositório real
def _url() -> str:
    return Config.do_ambiente().database_url.replace("@db:5432", "@localhost:15432")


@pytest.fixture
async def conexao() -> AsyncIterator[AsyncConnection]:
    try:
        eng = create_async_engine(_url(), future=True)
        async with eng.connect() as c:
            n = (
                await c.execute(sa.select(sa.func.count()).select_from(sa.text("produto")))
            ).scalar_one()
            if not n:
                pytest.skip("sem produto no banco: rode `make db-teste`")
            yield c
        await eng.dispose()
    except pytest.skip.Exception:
        raise
    except Exception:
        pytest.skip("sem banco: rode `make db-local && make db-teste`")


async def test_ac4_bateria_contra_o_repositorio_real(conexao: AsyncConnection) -> None:
    linha = (
        (
            await conexao.execute(
                sa.text(
                    "SELECT id, ean, custo_unitario_centavos FROM produto ORDER BY id LIMIT 1"
                )
            )
        )
        .mappings()
        .one()
    )
    await _bateria(
        RepoProdutoSQL(conexao),
        ean=str(linha["ean"]),
        produto_id=str(linha["id"]),
        custo_esperado=int(linha["custo_unitario_centavos"]),
    )


async def test_ac3_o_banco_recusa_ean_duplicado(conexao: AsyncConnection) -> None:
    """A restrição que torna `por_ean` bem definido.

    Sem ela a assinatura `Produto | None` seria mentira: a busca devolveria
    "algum" dos produtos, e qual dependeria do plano de execução.

    A transação é revertida — o teste prova a recusa, não suja o banco.
    """
    alvo = (
        (await conexao.execute(sa.text("SELECT ean FROM produto ORDER BY id LIMIT 1")))
        .mappings()
        .one()
    )

    with pytest.raises(Exception) as capturado:
        await conexao.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "('p-clone-048', :ean, 'Clone', 'F', 'x', 'comum', 'A', true, 100)"
            ),
            {"ean": alvo["ean"]},
        )
    assert "ean" in str(capturado.value).lower()
    await conexao.rollback()


async def test_ac3_ean_diferente_entra_normalmente(conexao: AsyncConnection) -> None:
    """O contraponto: a restrição recusa o DUPLICADO, não a inserção.

    Sem ele, uma coluna quebrada que recusasse tudo passaria no teste acima.
    """
    await conexao.execute(
        sa.text(
            "INSERT INTO produto VALUES "
            "('p-novo-048', '7890000000048', 'Novo', 'F', 'x', 'comum', 'A', true, 100)"
        )
    )
    achado = await RepoProdutoSQL(conexao).por_ean("7890000000048", _ctx(custo=True))
    assert achado is not None
    assert achado.id == "p-novo-048"
    await conexao.rollback()


async def test_por_ean_nao_filtra_por_unidade(conexao: AsyncConnection) -> None:
    """Produto não pertence a unidade (`RN-P01`).

    Um ator de UMA unidade acha o mesmo produto que um ator de todas — filtrar
    aqui esconderia do conferente um produto legítimo que ele tem na mão.
    """
    linha = (
        (await conexao.execute(sa.text("SELECT ean FROM produto ORDER BY id LIMIT 1")))
        .mappings()
        .one()
    )
    uma = ContextoDados(
        ator=Ator(
            id="u-uma-unidade",
            nome="Uma",
            papel="conferente",
            unidades=frozenset({"filial-uberlandia"}),
            permissoes=frozenset({"produto.ler"}),
            ativo=True,
        ),
        unidades_permitidas=frozenset({"filial-uberlandia"}),
        tx=_TxNula(),
    )
    achado: Any = await RepoProdutoSQL(conexao).por_ean(str(linha["ean"]), uma)
    assert achado is not None
