"""T-036 AC-1, AC-2, AC-3 — RN-M02, RN-D02 e RN-C01 aplicados pelo BANCO.

Estes testes sao o que separa este projeto de um CRUD com um comentario dizendo
"nao editar". Movimento imutavel e auditoria inalteravel tem peso regulatorio:
deixa-los apenas no codigo significa que um bug de ORM, um script de correcao
ou um UPDATE manual os violam em silencio.

A aplicacao conecta como `estoque_app`, um papel SEM privilegio de UPDATE/DELETE
nessas tabelas. A migracao roda como dono — e' a separacao que faz o REVOKE
valer, porque o dono de uma tabela ignora privilegios negados.

Pulam quando nao ha banco: `make db-local` para rodar.
"""

import os

import pytest
import sqlalchemy as sa
from sqlalchemy import Engine

URL_APP = os.environ.get(
    "DATABASE_URL_TESTE_APP",
    "postgresql+psycopg://estoque_app:app@localhost:15432/estoque",
)
URL_DONO = os.environ.get(
    "DATABASE_URL_TESTE",
    "postgresql+psycopg://estoque:troque-isto@localhost:15432/estoque",
)


def _motor(url: str) -> Engine | None:
    try:
        eng = sa.create_engine(url, future=True, connect_args={"connect_timeout": 2})
        with eng.connect():
            return eng
    except Exception:
        return None


@pytest.fixture(scope="module")
def app() -> Engine:
    eng = _motor(URL_APP)
    if eng is None:
        pytest.skip("sem banco: rode `make db-local && make migrate`")
    return eng


@pytest.fixture(scope="module")
def dono() -> Engine:
    eng = _motor(URL_DONO)
    if eng is None:
        pytest.skip("sem banco")
    return eng


@pytest.fixture(scope="module", autouse=True)
def _dados(dono: Engine) -> None:
    with dono.begin() as c:
        c.execute(
            sa.text("""
            INSERT INTO unidade VALUES ('t-un','T','seco',true) ON CONFLICT DO NOTHING;
            INSERT INTO produto VALUES
                ('t-p','1','P','F','pa','comum','A',true,100) ON CONFLICT DO NOTHING;
            INSERT INTO usuario VALUES
                ('t-u','U','t@x','h','conferente',true) ON CONFLICT DO NOTHING;
            INSERT INTO usuario VALUES
                ('t-rt','RT','rt@x','h','rt',true) ON CONFLICT DO NOTHING;
            INSERT INTO lote VALUES
                ('t-l','t-p','N1','t-un','2025-01-01','2027-01-01','liberado',null)
                ON CONFLICT DO NOTHING;
            INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,autor_id,status)
                VALUES ('t-m','t-l','t-un','entrada',100,'recebimento','t-u','efetivado')
                ON CONFLICT DO NOTHING;
        """)
        )


# --- RN-M02 / CA-08: nem o Diretor apaga movimento --------------------------
def test_update_em_movimento_e_recusado_pelo_banco(app: Engine) -> None:
    with pytest.raises(sa.exc.ProgrammingError, match="permission denied"), app.begin() as c:
        c.execute(sa.text("UPDATE movimento SET quantidade = 999 WHERE id = 't-m'"))


def test_delete_em_movimento_e_recusado_pelo_banco(app: Engine) -> None:
    with pytest.raises(sa.exc.ProgrammingError, match="permission denied"), app.begin() as c:
        c.execute(sa.text("DELETE FROM movimento WHERE id = 't-m'"))


# --- RN-D02: auditoria nunca, inclusive para o Diretor ----------------------
def test_delete_em_auditoria_e_recusado_pelo_banco(app: Engine) -> None:
    with pytest.raises(sa.exc.ProgrammingError, match="permission denied"), app.begin() as c:
        c.execute(sa.text("DELETE FROM auditoria"))


def test_update_em_auditoria_e_recusado_pelo_banco(app: Engine) -> None:
    with pytest.raises(sa.exc.ProgrammingError, match="permission denied"), app.begin() as c:
        c.execute(sa.text("UPDATE auditoria SET acao = 'x'"))


# --- RN-M03: correcao por estorno, que e' INSERT ----------------------------
def test_insert_continua_permitido(app: Engine) -> None:
    """A imutabilidade nao trava o sistema: corrigir se faz por estorno."""
    with app.begin() as c:
        c.execute(
            sa.text("""
            INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,
                                   autor_id,status,estorna_movimento_id)
            VALUES ('t-m-est','t-l','t-un','estorno',10,'estorno','t-u','efetivado','t-m')
            ON CONFLICT DO NOTHING
        """)
        )


# --- RN-A04 / RN-C01: separacao de funcoes no banco -------------------------
def test_autor_nao_pode_ser_o_proprio_autorizador(app: Engine) -> None:
    """CA-04. Separacao de funcoes com peso regulatorio nao pode depender de um
    `if` no servidor — um caminho novo esqueceria a checagem."""
    with pytest.raises(sa.exc.IntegrityError, match="movimento_check"), app.begin() as c:
        c.execute(
            sa.text("""
            INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,
                                   autor_id,autorizador_id,status)
            VALUES ('t-m-x','t-l','t-un','saida',5,'venda','t-u','t-u','efetivado')
        """)
        )


def test_autorizador_diferente_e_aceito(app: Engine) -> None:
    with app.begin() as c:
        c.execute(
            sa.text("""
            INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,
                                   autor_id,autorizador_id,status)
            VALUES ('t-m-ok','t-l','t-un','saida',5,'venda','t-u','t-rt','efetivado')
            ON CONFLICT DO NOTHING
        """)
        )


# --- ADR-0022 / RN-M06: nenhuma coluna derivada ----------------------------
def test_lote_nao_tem_coluna_saldo_nem_status_derivado(dono: Engine) -> None:
    with dono.connect() as c:
        cols = {
            r[0]
            for r in c.execute(
                sa.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'lote'"
                )
            )
        }
    assert "saldo" not in cols, "RN-M06: saldo e' derivado, nunca coluna"
    with dono.connect() as c:
        check = c.execute(
            sa.text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'lote_status_check'"
            )
        ).scalar_one()
    for derivado in ("vencido", "esgotado"):
        assert derivado not in check, f"ADR-0022: {derivado} e' derivado, nao armazenado"


def test_saldo_bate_com_a_soma_dos_movimentos(dono: Engine) -> None:
    """A view e' derivada. Se divergir, a fonte e' o movimento.

    Nao ha mais `REFRESH`: `saldo_lote` deixou de ser materializada na migracao
    0005 (achado A-20). Materializada, ela so' mudava por comando manual que
    nenhum caminho da aplicacao executava — e todo saldo LIDO ficava para tras
    depois da primeira escrita. Agora e' calculada, e concordar com a soma
    deixou de ser algo a verificar depois de atualizar: e' verdade por
    construcao. O teste continua, porque a definicao da view pode mudar.
    """
    with dono.begin() as c:
        da_view = c.execute(
            sa.text("SELECT saldo FROM saldo_lote WHERE lote_id = 't-l'")
        ).scalar_one()
        somado = c.execute(
            sa.text("""
            SELECT COALESCE(SUM(CASE tipo
                WHEN 'entrada' THEN quantidade WHEN 'estorno' THEN quantidade
                ELSE -quantidade END), 0)
            FROM movimento WHERE lote_id = 't-l' AND status = 'efetivado'
        """)
        ).scalar_one()
    assert da_view == somado
