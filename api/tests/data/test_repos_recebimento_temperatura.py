"""T-047 — `RepoRecebimentoSQL` e `RepoTemperaturaSQL`, e o escopo que a porta manda.

O que estes repos nunca fizeram: existir. `deps.py` passava `None`, o fake era
`_NaoUsado()`, o seed não tinha recebimento (achado A-32).

A mesma bateria de escopo (RN-A01) roda contra o **fake** (sempre) e contra o
**repositório real** ligado ao Postgres (pula sem banco). Um fake permissivo
faria a suíte de T-022/T-023 passar sobre um buraco — é o achado A-11.

Pula sem banco: `make db-local && make migrate && make seed`, e `make db-local`
DE NOVO.
"""

import sys
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from estoque.data.porta import ContextoDados
from estoque.data.repositorios import RepoRecebimentoSQL, RepoTemperaturaSQL
from estoque.domain.identidade import Ator
from estoque.server.config import Config

# `fakes` mora em tests/registry/ e é importado por nome lá; daqui, garante o path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "registry"))
import fakes

TODAS = frozenset({"cd-matriz", "cd-refrigerado", "filial-uberlandia"})


class _TxNula:
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


def _ator(unidades: frozenset[str]) -> Ator:
    return Ator(
        id="u-teste-047",
        nome="Teste 047",
        papel="auditoria",
        unidades=unidades,  # type: ignore[arg-type]
        permissoes=frozenset({"recebimento.ler", "temperatura.ler"}),
        ativo=True,
    )


def _ctx(unidades: frozenset[str]) -> ContextoDados:
    return ContextoDados(
        ator=_ator(unidades),
        unidades_permitidas=unidades,  # type: ignore[arg-type]
        tx=_TxNula(),
    )


# ---------------------------------------------------------------------------
# A bateria: recebe os dois repos e afirma sobre o escopo. Igual para fake e real.
# ---------------------------------------------------------------------------
async def _bateria_escopo(
    repo_receb: Any,
    repo_temp: Any,
    *,
    rid_matriz: str,
    rid_uberlandia: str,
) -> None:
    amplo = _ctx(TODAS)
    so_uberlandia = _ctx(frozenset({"filial-uberlandia"}))
    janela = (datetime(2000, 1, 1, tzinfo=UTC), datetime(2100, 1, 1, tzinfo=UTC))

    # --- recebimento ---
    todos = await repo_receb.listar(amplo)
    assert {r.id for r in todos} >= {rid_matriz, rid_uberlandia}

    restrito = await repo_receb.listar(so_uberlandia)
    unidades_vistas = {r.unidade_id for r in restrito}
    assert unidades_vistas == {"filial-uberlandia"}, unidades_vistas

    # por_id fora do escopo === inexistente: os dois devolvem None (ADR-0014)
    assert await repo_receb.por_id(rid_matriz, so_uberlandia) is None
    assert await repo_receb.por_id("r-nunca-existiu", so_uberlandia) is None
    # e dentro do escopo, aparece
    assert (await repo_receb.por_id(rid_uberlandia, so_uberlandia)) is not None

    # --- temperatura ---
    de, ate = janela
    dentro = await repo_temp.serie("cd-refrigerado", de, ate, amplo)
    assert len(dentro) > 0
    # CD Refrigerado não é do ator restrito a Uberlândia: série vazia, não erro
    fora = await repo_temp.serie("cd-refrigerado", de, ate, so_uberlandia)
    assert fora == []


# ---------------------------------------------------------------------------
# Fake — roda sempre
# ---------------------------------------------------------------------------
async def test_bateria_contra_o_fake() -> None:
    await _bateria_escopo(
        fakes.FakeRepoRecebimento(),
        fakes.FakeRepoTemperatura(),
        rid_matriz="r-normal-mtz",
        rid_uberlandia="r-uber",
    )


async def test_fake_serie_ordenada_por_medido_em() -> None:
    serie = await fakes.FakeRepoTemperatura().serie(
        "cd-refrigerado",
        datetime(2000, 1, 1, tzinfo=UTC),
        datetime(2100, 1, 1, tzinfo=UTC),
        _ctx(TODAS),
    )
    assert [t.medido_em for t in serie] == sorted(t.medido_em for t in serie)


# ---------------------------------------------------------------------------
# Repositório real — pula sem Postgres + seed
# ---------------------------------------------------------------------------
def _url() -> str:
    u = Config.do_ambiente().database_url
    return u.replace("@db:5432", "@localhost:15432")


@pytest.fixture
async def conexao() -> AsyncIterator[AsyncConnection]:
    try:
        eng = create_async_engine(_url(), future=True)
        async with eng.connect() as c:
            n = (
                await c.execute(sa.select(sa.func.count()).select_from(sa.text("recebimento")))
            ).scalar_one()
            if not n:
                pytest.skip("sem recebimento no banco: rode `make seed`")
            yield c
        await eng.dispose()
    except pytest.skip.Exception:
        raise
    except Exception:
        pytest.skip("sem banco: rode `make db-local && make migrate && make seed`")


async def test_bateria_contra_o_repositorio_real(conexao: AsyncConnection) -> None:
    await _bateria_escopo(
        RepoRecebimentoSQL(conexao),
        RepoTemperaturaSQL(conexao),
        rid_matriz="r-0001",
        rid_uberlandia="r-0006",
    )


async def test_real_listar_ordena_por_recebido_em_desc(conexao: AsyncConnection) -> None:
    todos = await RepoRecebimentoSQL(conexao).listar(_ctx(TODAS))
    datas = [r.recebido_em for r in todos]
    assert datas == sorted(datas, reverse=True)


async def test_real_serie_recorta_a_janela(conexao: AsyncConnection) -> None:
    repo = RepoTemperaturaSQL(conexao)
    ampla = await repo.serie(
        "cd-refrigerado",
        datetime(2000, 1, 1, tzinfo=UTC),
        datetime(2100, 1, 1, tzinfo=UTC),
        _ctx(TODAS),
    )
    estreita = await repo.serie(
        "cd-refrigerado",
        datetime.now(UTC) - timedelta(days=3650),
        datetime.now(UTC) - timedelta(days=3000),
        _ctx(TODAS),
    )
    assert len(ampla) > 0
    assert estreita == []
