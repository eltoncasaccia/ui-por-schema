"""T-042 — a mesma bateria contra o fake e contra o repositorio real (AC-1).

Pula sem banco — e o CI reprova esse pulo (AC-5, portao da T-041).
"""

from collections.abc import AsyncIterator
from typing import Protocol

import pytest
import sqlalchemy as sa
from porta_contrato import (
    COBERTURA,
    LOTES_SEMENTE,
    MOVIMENTOS_SEMENTE,
    bateria_auditoria,
    bateria_lote,
    bateria_movimento,
    bateria_produto,
    fakes,
    metodos_da_porta,
)
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from estoque.data import porta
from estoque.data.repositorios import (
    RepoAuditoriaSQL,
    RepoLoteSQL,
    RepoMovimentoSQL,
    RepoProdutoSQL,
)
from estoque.server.config import Config

ATOR_TRILHA = "u-contrato-042-trilha"


# ------------------------------------------------------------------ o fake
async def test_ac1_bateria_contra_o_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fakes, "LOTES", LOTES_SEMENTE)
    monkeypatch.setattr(fakes, "MOVIMENTOS", MOVIMENTOS_SEMENTE)
    await bateria_lote(fakes.FakeRepoLote())
    await bateria_produto(fakes.FakeRepoProduto())
    await bateria_movimento(fakes.FakeRepoMovimento())
    await bateria_auditoria(fakes.FakeRepoAuditoria(), ator_id=None, total=len(fakes.TRILHA))


# ------------------------------------------------------ o repositorio real
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


async def _semear(c: AsyncConnection) -> None:
    await c.execute(
        sa.text(
            "INSERT INTO produto (id, ean, nome, fabricante, principio_ativo, classe, "
            "curva_abc, ativo, custo_unitario_centavos) VALUES (:id, :ean, :nome, "
            ":fabricante, :principio_ativo, :classe, :curva_abc, :ativo, "
            ":custo_unitario_centavos)"
        ),
        [vars_de(p) for p in fakes.PRODUTOS.values()],
    )
    await c.execute(
        sa.text(
            "INSERT INTO lote (id, produto_id, numero, unidade_id, fabricacao, validade, "
            "status, endereco) VALUES (:id, :produto_id, :numero, :unidade_id, "
            ":fabricacao, :validade, :status, :endereco)"
        ),
        [vars_de(x) for x in LOTES_SEMENTE],
    )
    await c.execute(
        sa.text(
            "INSERT INTO movimento (id, lote_id, unidade_id, tipo, quantidade, motivo, "
            "complemento, autor_id, autorizador_id, status, criado_em, estorna_movimento_id, "
            "cliente_id, nota_fiscal) VALUES (:id, :lote_id, :unidade_id, :tipo, :quantidade, "
            ":motivo, :complemento, :autor_id, :autorizador_id, :status, :criado_em, "
            ":estorna_movimento_id, :cliente_id, :nota_fiscal)"
        ),
        [vars_de(x) for x in MOVIMENTOS_SEMENTE],
    )
    await c.execute(
        sa.text(
            "INSERT INTO auditoria (ator_id, acao, origem, criado_em) "
            "VALUES (:a, 'ler', 'tela', :t)"
        ),
        [{"a": ATOR_TRILHA, "t": fakes.AGORA}] * 3,
    )


def vars_de(obj: object) -> dict[str, object]:
    return {nome: getattr(obj, nome) for nome in obj.__slots__}  # type: ignore[attr-defined]


async def test_ac1_bateria_contra_o_repositorio_real(conexao: AsyncConnection) -> None:
    await _semear(conexao)
    try:
        await bateria_lote(RepoLoteSQL(conexao))
        await bateria_produto(RepoProdutoSQL(conexao))
        await bateria_movimento(RepoMovimentoSQL(conexao))
        await bateria_auditoria(RepoAuditoriaSQL(conexao), ator_id=ATOR_TRILHA, total=3)
    finally:
        await conexao.rollback()


# --------------------------------------------------------------- AC-4
def test_ac4_todo_metodo_da_porta_tem_cobertura() -> None:
    assert metodos_da_porta() == {k: set(v) for k, v in COBERTURA.items()}


def test_ac4_metodo_novo_sem_cobertura_e_detectado(monkeypatch: pytest.MonkeyPatch) -> None:
    class RepoNovo(Protocol):
        async def buscar(self) -> None: ...

    monkeypatch.setattr(porta, "RepoNovo", RepoNovo, raising=False)
    assert metodos_da_porta() != {k: set(v) for k, v in COBERTURA.items()}
