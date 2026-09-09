"""A borda HTTP de `/api/comandos/{nome}` — T-025, e T-011 AC-3 e AC-4.

Os testes de `test_t025_ac.py` provam o pipeline. Estes provam a FIACAO: que os
cabecalhos `Idempotency-Key` e `If-Match` chegam nele, e que a rota nova nao
escapou do middleware de CSRF.

A rota nova que esquece a protecao transversal e' o modo de falha mais comum de
uma borda HTTP — e o motivo de o CSRF deste projeto ser middleware e nao
dependencia por rota. O teste que prova isso e' o negativo, aqui embaixo.

Pulam sem banco: `make db-local && make migrate`, e `make db-local` DE NOVO.
"""

import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from estoque.application.commands import pipeline
from estoque.application.commands.tipos import Comando, ContextoComando, Efeito
from estoque.data import modelos as m

URL_DONO = os.environ.get(
    "DATABASE_URL_TESTE",
    "postgresql+psycopg://estoque:troque-isto@localhost:15432/estoque",
)

USUARIO = "t025-http-ivo"
LOTE = "t025-http-lote"
PRODUTO = "t025-http-prod"


class EntradaHttp(BaseModel):
    lote_id: str
    quantidade: int


async def _aplicar(entrada: Any, ctx: ContextoComando) -> Efeito:
    mid = f"t025-http-{secrets.token_hex(6)}"
    await ctx.conn.execute(
        sa.insert(m.movimento).values(
            id=mid,
            lote_id=entrada.lote_id,
            unidade_id="cd-matriz",
            tipo="saida",
            quantidade=entrada.quantidade,
            motivo="venda",
            autor_id=ctx.ator.id,
            status="efetivado",
            criado_em=ctx.agora,
        )
    )
    return Efeito(
        entidade="movimento",
        entidade_id=mid,
        valor_anterior=None,
        valor_novo={"quantidade": entrada.quantidade},
        dados={"movimento_id": mid},
    )


async def _etag_do_lote(entrada: Any, ctx: ContextoComando) -> str | None:
    linha = (
        (await ctx.conn.execute(sa.select(m.lote).where(m.lote.c.id == entrada.lote_id)))
        .mappings()
        .first()
    )
    return None if linha is None else pipeline.etag_de_valores(dict(linha))


async def _aplicar_com_etag(entrada: Any, ctx: ContextoComando) -> Efeito:
    await ctx.conn.execute(
        sa.update(m.lote).where(m.lote.c.id == entrada.lote_id).values(status="bloqueado")
    )
    return Efeito(
        entidade="lote",
        entidade_id=entrada.lote_id,
        valor_anterior={"status": "quarentena"},
        valor_novo={"status": "bloqueado"},
        dados={"lote_id": entrada.lote_id},
    )


pipeline.registrar(
    Comando(
        nome="t025_http_saida",
        requires=("movimento.criar",),
        schema=EntradaHttp,
        aplicar=_aplicar,
        idempotent=False,
    )
)
pipeline.registrar(
    Comando(
        nome="t025_http_status",
        requires=("movimento.criar",),
        schema=EntradaHttp,
        aplicar=_aplicar_com_etag,
        idempotent=True,
        etag_de=_etag_do_lote,
    )
)


# -------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def dono() -> sa.Engine:
    try:
        eng = sa.create_engine(URL_DONO, future=True, connect_args={"connect_timeout": 2})
        with eng.connect():
            pass
    except Exception:
        pytest.skip("sem banco: rode `make db-local && make migrate && make db-local`")
    return eng


@pytest.fixture
def sessao(dono: sa.Engine) -> str:
    """Sessao real no banco. O app resolve o ator a cada requisicao, do banco
    (RN-A06), entao nao ha como injetar um ator falso pela borda — e essa e' a
    propriedade que se quer, nao um obstaculo a contornar."""
    sid = secrets.token_urlsafe(32)
    agora = datetime.now(UTC)
    with dono.begin() as c:
        c.execute(
            sa.text(
                "INSERT INTO unidade VALUES ('cd-matriz','Matriz','seco',true) "
                "ON CONFLICT DO NOTHING"
            )
        )
        c.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "(:p,'7891','Dipirona','F','dip','comum','A',true,900) ON CONFLICT DO NOTHING"
            ),
            {"p": PRODUTO},
        )
        c.execute(
            sa.text(
                "INSERT INTO lote VALUES "
                "(:l,:p,'L-HTTP','cd-matriz','2025-01-01','2027-01-01','quarentena',null) "
                "ON CONFLICT DO NOTHING"
            ),
            {"l": LOTE, "p": PRODUTO},
        )
        c.execute(sa.text("UPDATE lote SET status='quarentena' WHERE id=:l"), {"l": LOTE})
        c.execute(
            sa.text(
                "INSERT INTO usuario VALUES (:u,'Ivo HTTP','ivo.http@bertoni.test','x',"
                "'gerente',true) ON CONFLICT DO NOTHING"
            ),
            {"u": USUARIO},
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
async def _pool_limpo() -> Any:
    """Descarta o pool do app entre testes.

    `server.app` cria o engine no import, e o pool guarda conexoes asyncpg
    presas ao event loop que as abriu. Cada teste roda no seu proprio loop, e a
    conexao reaproveitada falha com "attached to a different loop" — um sintoma
    do arranjo de teste, nao do servidor, que vive num loop so'.
    """
    from estoque.server.app import _engine

    yield
    await _engine.dispose()


def _cliente(sid: str | None, *, com_csrf: bool = True) -> AsyncClient:
    from estoque.server.app import CFG, app

    tok = secrets.token_urlsafe(24)
    cookies: dict[str, str] = {"csrf": tok}
    if sid:
        cookies["sessao"] = sid
    headers = {"Origin": CFG.cors_origin}
    if com_csrf:
        headers["X-CSRF-Token"] = tok
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://teste",
        cookies=cookies,
        headers=headers,
    )


def _movimentos(dono: sa.Engine) -> int:
    with dono.connect() as c:
        total = c.execute(
            sa.text("SELECT count(*) FROM movimento WHERE lote_id = :l"), {"l": LOTE}
        ).scalar_one()
    return int(total)


# ------------------------------------------------------- T-011 AC-3 · idempotencia
async def test_mesma_chave_no_cabecalho_produz_um_efeito(dono: sa.Engine, sessao: str) -> None:
    antes = _movimentos(dono)
    chave = secrets.token_hex(8)
    corpo = {"lote_id": LOTE, "quantidade": 2}
    async with _cliente(sessao) as cli:
        um = await cli.post(
            "/api/comandos/t025_http_saida", json=corpo, headers={"Idempotency-Key": chave}
        )
        dois = await cli.post(
            "/api/comandos/t025_http_saida", json=corpo, headers={"Idempotency-Key": chave}
        )
    assert um.status_code == 200, um.text
    assert dois.status_code == 200, dois.text
    assert dois.json()["dados"] == um.json()["dados"]
    assert dois.json()["meta"]["repetido"] is True
    assert _movimentos(dono) == antes + 1


async def test_sem_idempotency_key_a_borda_recusa(dono: sa.Engine, sessao: str) -> None:
    """CONTRATOS §8. Se o cabecalho nao chegasse ao pipeline, esta requisicao
    passaria — e o teste acima poderia estar verde por outro motivo."""
    antes = _movimentos(dono)
    async with _cliente(sessao) as cli:
        r = await cli.post(
            "/api/comandos/t025_http_saida", json={"lote_id": LOTE, "quantidade": 2}
        )
    assert r.status_code == 422
    assert r.json()["erro"]["codigo"] == "invalido"
    assert _movimentos(dono) == antes


# ---------------------------------------------------------- T-011 AC-4 · If-Match
async def test_if_match_antigo_devolve_conflito(sessao: str) -> None:
    corpo = {"lote_id": LOTE, "quantidade": 1}
    async with _cliente(sessao) as cli:
        primeira = await cli.post(
            "/api/comandos/t025_http_status", json=corpo, headers={"If-Match": "etag-velho"}
        )
        assert primeira.status_code == 409
        assert primeira.json()["erro"]["codigo"] == "conflito"


async def test_if_match_correto_aplica_e_devolve_etag_novo(sessao: str) -> None:
    # O etag corrente e' o que a ultima resposta de escrita devolveu. Aqui ele e'
    # lido direto do banco, que e' a mesma fonte que o comando consulta.
    from estoque.server.app import _engine

    async with _engine.connect() as c:
        linha = (await c.execute(sa.select(m.lote).where(m.lote.c.id == LOTE))).mappings().one()
    etag = pipeline.etag_de_valores(dict(linha))

    async with _cliente(sessao) as cli:
        r = await cli.post(
            "/api/comandos/t025_http_status",
            json={"lote_id": LOTE, "quantidade": 1},
            headers={"If-Match": etag},
        )
    assert r.status_code == 200, r.text
    assert r.headers["ETag"] != etag, "o etag precisa mudar quando a entidade muda"


# ------------------------------------------------------------------- negativos
async def test_sem_sessao_a_rota_recusa(dono: sa.Engine) -> None:
    antes = _movimentos(dono)
    async with _cliente(None) as cli:
        r = await cli.post(
            "/api/comandos/t025_http_saida",
            json={"lote_id": LOTE, "quantidade": 2},
            headers={"Idempotency-Key": secrets.token_hex(8)},
        )
    assert r.status_code == 401
    assert _movimentos(dono) == antes


async def test_sem_token_csrf_a_rota_recusa(dono: sa.Engine, sessao: str) -> None:
    """O teste que justifica o CSRF ser middleware.

    Uma rota de escrita nova e' exatamente o que esquece a protecao transversal
    quando ela e' dependencia declarada rota a rota. Se este teste passar a
    devolver 200, a rota escapou do middleware."""
    antes = _movimentos(dono)
    async with _cliente(sessao, com_csrf=False) as cli:
        r = await cli.post(
            "/api/comandos/t025_http_saida",
            json={"lote_id": LOTE, "quantidade": 2},
            headers={"Idempotency-Key": secrets.token_hex(8)},
        )
    assert r.status_code == 403
    assert _movimentos(dono) == antes


async def test_origem_de_terceiro_e_recusada(dono: sa.Engine, sessao: str) -> None:
    antes = _movimentos(dono)
    async with _cliente(sessao) as cli:
        r = await cli.post(
            "/api/comandos/t025_http_saida",
            json={"lote_id": LOTE, "quantidade": 2},
            headers={
                "Origin": "https://sitedeterceiro.example",
                "Idempotency-Key": secrets.token_hex(8),
            },
        )
    assert r.status_code == 403
    assert _movimentos(dono) == antes


async def test_comando_inexistente_devolve_nao_encontrado(sessao: str) -> None:
    async with _cliente(sessao) as cli:
        r = await cli.post(
            "/api/comandos/nao_existe",
            json={},
            headers={"Idempotency-Key": secrets.token_hex(8)},
        )
    assert r.status_code == 404
    assert r.json()["erro"]["mensagem"] == "Registro nao encontrado."


async def test_papel_sem_a_permissao_e_recusado_na_rota(dono: sa.Engine, sessao: str) -> None:
    """RN-A03 pela borda: Ivo e' gerente e nao tem `lote.liberar`. Mesmo com
    sessao valida, CSRF valido e corpo valido, a rota recusa."""
    pipeline.registrar(
        Comando(
            nome="t025_http_proibido",
            requires=("lote.liberar",),
            schema=EntradaHttp,
            aplicar=_aplicar,
            idempotent=False,
        )
    )
    antes = _movimentos(dono)
    async with _cliente(sessao) as cli:
        r = await cli.post(
            "/api/comandos/t025_http_proibido",
            json={"lote_id": LOTE, "quantidade": 2},
            headers={"Idempotency-Key": secrets.token_hex(8)},
        )
    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "nao_autorizado"
    assert _movimentos(dono) == antes
