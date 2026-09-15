"""T-024 AC-6 — consultar a trilha gera evento de auditoria. `RN-D05`.

A regra é contraintuitiva de propósito: **a consulta de auditoria é auditada.**
Quem consultou o quê importa tanto quanto quem alterou — uma trilha que registra
só escrita descreve um sistema onde ninguém nunca olhou nada.

Este teste é de BORDA, e não do componente: quem grava o evento de leitura é o
endpoint (`server/app.py`), num lugar só, para toda leitura. Testar no componente
provaria que o componente não faz — que é verdade e não é o AC.

Pula sem banco: `make db-local && make db-teste`.
"""

import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import banco
import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine

DONO = banco.URL_DONO

USUARIO = "t024-sandra"


@pytest.fixture(scope="module")
def dono() -> Engine:
    try:
        eng = sa.create_engine(DONO, future=True, connect_args={"connect_timeout": 2})
        with eng.connect():
            pass
    except Exception:
        pytest.skip("sem banco: rode `make db-local && make db-teste`")
    return eng


@pytest.fixture
def sessao(dono: Engine) -> str:
    """Sandra, papel `auditoria` — é quem tem `auditoria.ler`."""
    sid = secrets.token_urlsafe(32)
    agora = datetime.now(UTC)
    with dono.begin() as c:
        c.execute(
            sa.text(
                "INSERT INTO usuario VALUES (:u,'Sandra CI','sandra.ci@bertoni.test','x',"
                "'auditoria',true) ON CONFLICT DO NOTHING"
            ),
            {"u": USUARIO},
        )
        c.execute(
            sa.text(
                "INSERT INTO unidade VALUES ('cd-matriz','Matriz','seco',true) "
                "ON CONFLICT DO NOTHING"
            )
        )
        c.execute(
            sa.text(
                "INSERT INTO usuario_unidade VALUES (:u,'cd-matriz') ON CONFLICT DO NOTHING"
            ),
            {"u": USUARIO},
        )
        c.execute(
            sa.text("INSERT INTO sessao VALUES (:s,:u,:a,:e)"),
            {"s": sid, "u": USUARIO, "a": agora, "e": agora + timedelta(hours=12)},
        )
    return sid


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    from estoque.server.app import _engine

    yield
    await _engine.dispose()


def eventos_de_leitura(dono: Engine, componente: str) -> int:
    with dono.connect() as c:
        return int(
            c.execute(
                sa.text(
                    "SELECT count(*) FROM auditoria WHERE acao='ler' "
                    "AND entidade=:e AND ator_id=:u"
                ),
                {"e": componente, "u": USUARIO},
            ).scalar_one()
        )


async def _ler(sid: str, componente: str) -> int:
    from estoque.server.app import CFG, app

    tok = secrets.token_urlsafe(24)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://teste",
        cookies={"sessao": sid, "csrf": tok},
        headers={"Origin": CFG.cors_origin, "X-CSRF-Token": tok},
    ) as cli:
        r = await cli.post(f"/api/componentes/{componente}/dados", json={"params": {}})
    return r.status_code


async def test_ac6_consultar_a_trilha_gera_evento_de_auditoria(
    dono: Engine, sessao: str
) -> None:
    antes = eventos_de_leitura(dono, "auditoria_trilha")
    assert await _ler(sessao, "auditoria_trilha") == 200
    assert eventos_de_leitura(dono, "auditoria_trilha") == antes + 1


async def test_ac6_a_leitura_registra_quem_consultou(dono: Engine, sessao: str) -> None:
    """ "Gerou evento" não basta: o evento sem ator não responde a pergunta que
    `RN-D05` faz, que é quem olhou."""
    assert await _ler(sessao, "auditoria_trilha") == 200
    with dono.connect() as c:
        linha = (
            c.execute(
                sa.text(
                    "SELECT ator_id, entidade, origem FROM auditoria "
                    "WHERE acao='ler' AND entidade='auditoria_trilha' "
                    "ORDER BY id DESC LIMIT 1"
                )
            )
            .mappings()
            .one()
        )
    assert linha["ator_id"] == USUARIO
    assert linha["entidade"] == "auditoria_trilha"
    assert linha["origem"] in ("assistente", "tela")


async def test_ac6_a_recusa_nao_gera_evento_de_leitura(dono: Engine, sessao: str) -> None:
    """O par negativo, e ele diz uma coisa sobre o desenho.

    Sandra não tem `movimento.criar`. Pedir um componente que ela não pode ver é
    recusado ANTES do `load`, e portanto antes do registro de leitura — não se
    registra ter lido o que não foi lido.
    """
    antes = eventos_de_leitura(dono, "movimento_saida")
    assert await _ler(sessao, "movimento_saida") == 403
    assert eventos_de_leitura(dono, "movimento_saida") == antes


async def test_ac6_vale_para_movimento_lista_tambem(dono: Engine, sessao: str) -> None:
    """`RN-D05` diz "toda leitura", não "a leitura da trilha"."""
    antes = eventos_de_leitura(dono, "movimento_lista")
    assert await _ler(sessao, "movimento_lista") == 200
    assert eventos_de_leitura(dono, "movimento_lista") == antes + 1
