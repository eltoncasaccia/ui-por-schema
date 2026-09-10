"""Ferramentas dos testes de borda HTTP — T-011.

Modulo comum, e nao `conftest.py`, por dois motivos concretos: `mypy --strict`
recusa dois modulos chamados `conftest` na mesma arvore, e importar fixture de
um conftest aninhado faz o `ruff` acusar F811 em cada parametro de teste. Aqui
sao funcoes normais, importadas por nome — mesmo arranjo do `tests/registry/fakes.py`.

Os testes de borda precisam de **sessao real no banco**: o app resolve o ator a
cada requisicao, do banco (`RN-A06`), entao nao ha como injetar um ator falso
pela borda. Essa e' a propriedade que se quer, nao um obstaculo a contornar — e
por isso estes testes pulam sem Postgres em vez de fingir com um duble.

Pulam sem banco: `make db-local && make migrate && make seed`, e `make db-local`
DE NOVO (o `migrate` recria o container sem a porta).
"""

import os
import secrets
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine

# O papel DONO: os testes precisam inserir usuario e sessao, e `estoque_app` nao
# pode (achado A-27). A aplicacao sob teste continua conectando como `estoque_app`,
# que e' o ponto do A-27 — o teste nao pode emprestar privilegio a ela.
URL_DONO = os.environ.get(
    "DATABASE_URL_TESTE",
    "postgresql+psycopg://estoque:troque-isto@localhost:15432/estoque",
)

UNIDADES: dict[str, tuple[str, str]] = {
    "cd-matriz": ("Matriz", "seco"),
    "cd-refrigerado": ("Refrigerado", "refrigerado"),
    "filial-uberlandia": ("Uberlandia", "seco"),
}

_motor: Engine | None = None


def motor_dono() -> Engine:
    """Engine do papel dono, memorizado. **Pula o teste** se nao houver banco."""
    global _motor
    if _motor is None:
        try:
            eng = sa.create_engine(URL_DONO, future=True, connect_args={"connect_timeout": 2})
            with eng.connect():
                pass
        except Exception:
            pytest.skip("sem banco: rode `make db-local && make migrate && make db-local`")
        _motor = eng
    return _motor


def criar_sessao(
    *,
    usuario_id: str,
    papel: str,
    unidades: Iterable[str] = ("cd-matriz",),
    ativo: bool = True,
) -> str:
    """Cria usuario + unidades + sessao e devolve o `sid`.

    O papel entra por parametro porque metade dos testes de borda e' sobre QUEM
    esta' pedindo: Odair nao alcanca a Matriz, Cleide nao tem custo.
    """
    dono = motor_dono()
    sid = secrets.token_urlsafe(32)
    agora = datetime.now(UTC)
    with dono.begin() as c:
        for uid in unidades:
            nome, tipo = UNIDADES[uid]
            c.execute(
                sa.text("INSERT INTO unidade VALUES (:i,:n,:t,false) ON CONFLICT DO NOTHING"),
                {"i": uid, "n": nome, "t": tipo},
            )
        c.execute(
            sa.text(
                "INSERT INTO usuario VALUES (:u,:n,:e,'x',:p,:a) "
                "ON CONFLICT (id) DO UPDATE SET papel = EXCLUDED.papel, "
                "ativo = EXCLUDED.ativo"
            ),
            {
                "u": usuario_id,
                "n": usuario_id,
                "e": f"{usuario_id}@bertoni.test",
                "p": papel,
                "a": ativo,
            },
        )
        for uid in unidades:
            c.execute(
                sa.text("INSERT INTO usuario_unidade VALUES (:u,:i) ON CONFLICT DO NOTHING"),
                {"u": usuario_id, "i": uid},
            )
        c.execute(
            sa.text("INSERT INTO sessao VALUES (:s,:u,:a,:e)"),
            {"s": sid, "u": usuario_id, "a": agora, "e": agora + timedelta(hours=12)},
        )
    return sid


def cliente(
    sid: str | None = None, *, com_csrf: bool = True, origem: str | None = None
) -> AsyncClient:
    """Cliente HTTP contra o app real, com cookie de sessao e par CSRF."""
    from estoque.server.app import CFG, app

    tok = secrets.token_urlsafe(24)
    cookies: dict[str, str] = {"csrf": tok}
    if sid:
        cookies["sessao"] = sid
    headers = {"Origin": origem or CFG.cors_origin}
    if com_csrf:
        headers["X-CSRF-Token"] = tok
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://teste",
        cookies=cookies,
        headers=headers,
    )


async def descartar_pool() -> None:
    """Descarta o pool do app entre testes.

    `server.app` cria o engine no import, e o pool guarda conexoes asyncpg presas
    ao loop que as abriu. Cada teste roda no proprio loop, e a conexao
    reaproveitada falha com "attached to a different loop" — sintoma do arranjo
    de teste, nao do servidor, que vive num loop so'.
    """
    from estoque.server.app import _engine

    await _engine.dispose()
