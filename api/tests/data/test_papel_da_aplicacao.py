"""Achados A-27 e A-20 — o que a APLICAÇÃO consegue fazer, com o papel dela.

`tests/data/test_imutabilidade_no_banco.py` prova que `estoque_app` não edita
movimento nem auditoria. Provava — e a aplicação conectava como **dono**, que
ignora `REVOKE`. Os testes descreviam um sistema que não era o que rodava:
`RN-M02` e `RN-D02` eram verdade na suíte e mentira em produção.

Este arquivo fecha a distância. Ele lê a URL da **configuração da aplicação**, a
mesma que o servidor usa, e afirma sobre ela. Se alguém apontar o `.env` de volta
para o dono, é aqui que quebra.

O segundo teste é o par do A-20: `saldo_lote` deixou de ser materializada, e a
prova é que ela acompanha uma escrita.

Pulam sem banco: `make db-local && make migrate`, e `make db-local` DE NOVO.
"""

import os
import secrets

import pytest
import sqlalchemy as sa
from sqlalchemy import Engine

from estoque.server.config import Config

DONO = os.environ.get(
    "DATABASE_URL_TESTE",
    "postgresql+psycopg://estoque:troque-isto@localhost:15432/estoque",
)


def _sincrona(url: str) -> str:
    """A configuração é async; aqui o driver é o síncrono, mesma credencial."""
    return url.replace("+asyncpg", "+psycopg")


def _motor(url: str) -> Engine | None:
    try:
        eng = sa.create_engine(url, future=True, connect_args={"connect_timeout": 2})
        with eng.connect():
            return eng
    except Exception:
        return None


@pytest.fixture(scope="module")
def app() -> Engine:
    """O motor com a credencial que o SERVIDOR usa — não uma escolhida no teste."""
    url = _sincrona(Config.do_ambiente().database_url)
    # Em CI e no container a URL aponta para `db:5432`; localmente, para a porta
    # publicada. O teste não deve falhar por causa do host.
    eng = _motor(url) or _motor(url.replace("@db:5432", "@localhost:15432"))
    if eng is None:
        pytest.skip("sem banco: rode `make db-local && make migrate && make db-local`")
    return eng


@pytest.fixture(scope="module")
def dono() -> Engine:
    eng = _motor(DONO)
    if eng is None:
        pytest.skip("sem banco")
    return eng


# ------------------------------------------------------- A-27 · o papel certo
def test_a27_a_aplicacao_nao_conecta_como_dono() -> None:
    """A configuração é a evidência, e ela é lida aqui — não descrita.

    O dono de uma tabela IGNORA `REVOKE`. Com ele na `DATABASE_URL`, os REVOKE da
    migração 0001 não protegem nada do que a aplicação faz, e a suíte inteira de
    imutabilidade passa a provar uma propriedade que o sistema não tem.
    """
    url = Config.do_ambiente().database_url
    assert "estoque_app" in url, (
        "a aplicação precisa conectar com o papel restrito; o dono ignora REVOKE"
    )
    assert "://estoque:" not in url


def test_a27_a_aplicacao_nao_apaga_movimento(app: Engine) -> None:
    """`RN-M02`: movimento não pode ser excluído **por ninguém**, em nenhum papel.

    Este teste existia para `estoque_app` e passava; o que faltava era a
    aplicação de fato usar esse papel. Agora a credencial vem da configuração.
    """
    with pytest.raises(sa.exc.ProgrammingError, match="permission denied"), app.begin() as c:
        c.execute(sa.text("DELETE FROM movimento WHERE tipo = 'saida'"))


def test_a27_a_aplicacao_nao_edita_movimento_efetivado(app: Engine) -> None:
    with pytest.raises(Exception, match=r"permission denied|definitivo"), app.begin() as c:
        c.execute(sa.text("UPDATE movimento SET quantidade = 1 WHERE status = 'efetivado'"))


def test_a27_a_aplicacao_nao_apaga_auditoria(app: Engine) -> None:
    """`RN-D02`: a trilha é append-only. Se a aplicação pudesse apagá-la, a
    própria evidência de que algo aconteceu seria removível por quem o fez."""
    with pytest.raises(sa.exc.ProgrammingError, match="permission denied"), app.begin() as c:
        c.execute(sa.text("DELETE FROM auditoria"))


def test_a27_a_aplicacao_nao_edita_auditoria(app: Engine) -> None:
    with pytest.raises(sa.exc.ProgrammingError, match="permission denied"), app.begin() as c:
        c.execute(sa.text("UPDATE auditoria SET acao = 'x'"))


def test_a27_o_dono_consegue_o_que_a_aplicacao_nao_consegue(dono: Engine) -> None:
    """O par negativo, e o que dá sentido aos quatro testes acima.

    Se o banco recusasse `DELETE` para todo mundo, eles passariam sem provar nada
    sobre o papel. É a diferença entre os dois que é a garantia — e é exatamente
    essa diferença que estava anulada enquanto a aplicação usava o dono.

    A transação é revertida: o teste prova o privilégio, não exerce.
    """
    with dono.connect() as c:
        tx = c.begin()
        apagados = c.execute(sa.text("DELETE FROM auditoria")).rowcount
        tx.rollback()
    assert apagados >= 0, "o dono precisa conseguir — é ele quem migra"


def test_a27_a_aplicacao_continua_escrevendo_o_que_precisa(app: Engine) -> None:
    """O papel restrito não pode ser restrito DEMAIS: se `INSERT` em movimento
    ou auditoria falhasse, a correção teria trocado um erro por outro."""
    with app.begin() as c:
        c.execute(sa.text("SELECT 1 FROM movimento LIMIT 1"))
        c.execute(
            sa.text(
                "INSERT INTO auditoria (ator_id,acao,origem,criado_em) "
                "VALUES (null,'teste-a27','sistema',now())"
            )
        )


# ------------------------------------------------- A-20 · a view acompanha
def test_a20_saldo_lote_nao_e_materializada(dono: Engine) -> None:
    """View materializada só muda com `REFRESH`, e nenhum caminho da aplicação
    executava isso — nem poderia, com o papel restrito."""
    with dono.connect() as c:
        tipo = c.execute(
            sa.text(
                "SELECT c.relkind FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relname = 'saldo_lote' AND n.nspname = 'public'"
            )
        ).scalar_one()
    assert tipo == "v", f"esperava view comum ('v'), achei relkind={tipo!r}"


def test_a20_a_view_acompanha_uma_escrita(dono: Engine) -> None:
    """A prova que faltava, e que teria pegado o achado: escrever um movimento e
    conferir que o saldo lido mudou junto.

    Antes da migração 0005 este teste falhava por 7 unidades — o valor exato do
    movimento inserido, porque a view simplesmente não o via.
    """
    with dono.connect() as c:
        tx = c.begin()
        lote = c.execute(
            sa.text("SELECT lote_id FROM saldo_lote WHERE saldo > 100 LIMIT 1")
        ).scalar_one()
        antes = c.execute(
            sa.text("SELECT saldo FROM saldo_lote WHERE lote_id = :l"), {"l": lote}
        ).scalar_one()

        c.execute(
            sa.text(
                "INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,"
                "autor_id,status,criado_em) SELECT :i,:l,unidade_id,'saida',7,'avaria',"
                "autor_id,'efetivado',now() FROM movimento WHERE lote_id=:l LIMIT 1"
            ),
            {"i": f"probe-{secrets.token_hex(4)}", "l": lote},
        )
        depois = c.execute(
            sa.text("SELECT saldo FROM saldo_lote WHERE lote_id = :l"), {"l": lote}
        ).scalar_one()
        tx.rollback()

    assert depois == antes - 7, "a view não acompanhou a escrita"


def test_a20_pendente_de_autorizacao_nao_entra_no_saldo(dono: Engine) -> None:
    """RN-C01 na definição da view — e o par negativo do teste acima: ela conta
    o que foi efetivado, não tudo que foi escrito."""
    with dono.connect() as c:
        tx = c.begin()
        lote = c.execute(
            sa.text("SELECT lote_id FROM saldo_lote WHERE saldo > 100 LIMIT 1")
        ).scalar_one()
        antes = c.execute(
            sa.text("SELECT saldo FROM saldo_lote WHERE lote_id = :l"), {"l": lote}
        ).scalar_one()
        c.execute(
            sa.text(
                "INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,"
                "autor_id,status,criado_em) SELECT :i,:l,unidade_id,'saida',7,'avaria',"
                "autor_id,'aguardando_autorizacao',now() "
                "FROM movimento WHERE lote_id=:l LIMIT 1"
            ),
            {"i": f"probe-{secrets.token_hex(4)}", "l": lote},
        )
        depois = c.execute(
            sa.text("SELECT saldo FROM saldo_lote WHERE lote_id = :l"), {"l": lote}
        ).scalar_one()
        tx.rollback()

    assert depois == antes, "movimento pendente mexeu no saldo (RN-C01)"
