"""T-050 AC-1, AC-2, AC-3, AC-4 — etag na leitura, contra Postgres real.

Achado A-41, na verificação da T-049 contra o servidor real: 6 dos 7 comandos
exigem `If-Match`, e nenhuma leitura devolvia etag. Escopo desta tarefa (o
corte foi registrado no arquivo dela): `quarentena_liberar` e
`lote_status_acao`, os dois cujo etag é só sobre o `Lote` — `movimento_saida`
soma `saldo` e fica para T-051.

Pulam sem banco: `make db-local && make migrate`, e `make db-local` DE NOVO.
"""

import secrets
from collections.abc import AsyncGenerator
from datetime import date, timedelta
from typing import Any, cast

import pytest
import sqlalchemy as sa
from borda import cliente, criar_sessao, descartar_pool, motor_dono

LOTE = "t050-lote"
PRODUTO = "t050-prod"


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


@pytest.fixture(autouse=True)
def _semear() -> None:
    hoje = date.today()
    with motor_dono().begin() as c:
        c.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "(:p,'9990000000501','T050 Produto','F','x','comum','A',true,100) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PRODUTO},
        )
        c.execute(
            sa.text(
                "INSERT INTO lote VALUES "
                "(:l,:p,'L-050','cd-matriz',:f,:v,'quarentena',null) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "l": LOTE,
                "p": PRODUTO,
                "f": hoje - timedelta(days=10),
                "v": hoje + timedelta(days=400),
            },
        )
        # Estado inicial conhecido mesmo depois de um teste ter mudado.
        c.execute(sa.text("UPDATE lote SET status='quarentena' WHERE id=:l"), {"l": LOTE})


def helena() -> str:
    return criar_sessao(usuario_id="t050-helena", papel="rt", unidades=("cd-matriz",))


async def _dados(sid: str, componente: str, params: dict[str, Any]) -> dict[str, Any]:
    async with cliente(sid) as cli:
        r = await cli.post(
            f"/api/componentes/{componente}/dados",
            json={"params": params, "pagina": {"limite": 20, "cursor": None}},
        )
    return cast(dict[str, Any], r.json())


async def _liberar(sid: str, etag: str, chave: str) -> Any:
    async with cliente(sid) as cli:
        r = await cli.post(
            "/api/comandos/lote_liberar_quarentena",
            headers={"If-Match": etag, "Idempotency-Key": chave},
            json={
                "lote_id": LOTE,
                "decisao": "liberar",
                "justificativa": "conferência completa, embalagem íntegra",
                "integridade_conferida": True,
                "validade_conferida": True,
                "nota_fiscal_conferida": True,
                "temperatura_conferida": False,
            },
        )
    return r


async def test_ac1_leitura_devolve_etag_para_os_dois_componentes() -> None:
    sid = helena()
    d1 = await _dados(sid, "quarentena_liberar", {"lote_id": LOTE})
    d2 = await _dados(sid, "lote_status_acao", {"lote_id": LOTE})
    assert isinstance(d1["meta"]["etag"], str) and len(d1["meta"]["etag"]) > 0
    assert isinstance(d2["meta"]["etag"], str) and len(d2["meta"]["etag"]) > 0


async def test_ac2_etag_estavel_sem_escrita_e_muda_depois_dela() -> None:
    sid = helena()
    d1 = await _dados(sid, "quarentena_liberar", {"lote_id": LOTE})
    d2 = await _dados(sid, "quarentena_liberar", {"lote_id": LOTE})
    assert d1["meta"]["etag"] == d2["meta"]["etag"]

    r = await _liberar(sid, d1["meta"]["etag"], secrets.token_hex(8))
    assert r.status_code == 200, r.text

    d3 = await _dados(sid, "quarentena_liberar", {"lote_id": LOTE})
    assert d3["meta"]["etag"] != d1["meta"]["etag"]


async def test_ac3_etag_desatualizado_e_recusado_e_nada_e_aplicado() -> None:
    """Negativo — o critério central: sem isto, `If-Match` seria decoração."""
    sid = helena()
    d1 = await _dados(sid, "quarentena_liberar", {"lote_id": LOTE})
    etag_velho = d1["meta"]["etag"]

    # Alguém libera o lote com o etag correto — o estado mudou por baixo.
    ok1 = await _liberar(sid, etag_velho, secrets.token_hex(8))
    assert ok1.status_code == 200, ok1.text

    # Uma segunda tentativa, com o etag LIDO ANTES dessa mudança.
    async with cliente(sid) as cli:
        r = await cli.post(
            "/api/comandos/lote_status",
            headers={"If-Match": etag_velho, "Idempotency-Key": secrets.token_hex(8)},
            json={
                "lote_id": LOTE,
                "acao": "bloquear",
                "justificativa": "tentativa com etag velho",
            },
        )
    assert r.json()["ok"] is False
    assert r.json()["erro"]["codigo"] == "conflito"

    with motor_dono().connect() as c:
        status = c.execute(
            sa.text("SELECT status FROM lote WHERE id=:l"), {"l": LOTE}
        ).scalar_one()
    # Continua liberado — a tentativa recusada não bloqueou o lote.
    assert status == "liberado"


async def test_ac4_escrever_com_o_etag_atual_completa_de_ponta_a_ponta() -> None:
    """O `curl` que a T-049 registrou como falha ("If-Match obrigatorio")
    agora completa — é o mesmo fluxo, com o etag que faltava."""
    sid = helena()
    d = await _dados(sid, "quarentena_liberar", {"lote_id": LOTE})
    r = await _liberar(sid, d["meta"]["etag"], secrets.token_hex(8))
    assert r.status_code == 200
    assert r.json()["ok"] is True
