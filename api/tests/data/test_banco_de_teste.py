"""T-052 — os testes nunca gravam no banco de desenvolvimento. AC-3, AC-5, AC-6.

A guarda e' testada pelos dois lados, e o lado que vale e' o que PARA: uma suite
apontada para o dev tem de nao rodar. Os testes de processo filho rodam o pytest
de verdade, porque a guarda mora num hook de configuracao que so' existe la'.
"""

import os
import subprocess
import sys
from pathlib import Path

import banco
import pytest
from sqlalchemy.engine import make_url

from estoque.server.config import Config

API = Path(__file__).resolve().parents[2]
DEV = "postgresql+psycopg://estoque:troque-isto@localhost:15432/estoque"
# O `.env` traz o servico do compose; exportado no shell, e' o dev por outro nome.
DEV_PELO_ENV = "postgresql+asyncpg://estoque_app:app@db:5432/estoque"


def _pytest(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
    """Pytest num processo filho, sem nenhuma DATABASE_URL herdada alem das dadas."""
    herdado = {k: v for k, v in os.environ.items() if not k.startswith("DATABASE_URL")}
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *args],
        cwd=API,
        env={**herdado, **env},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    "url",
    [
        DEV,
        "postgresql+asyncpg://estoque_app:app@127.0.0.1:15432/estoque",
        DEV_PELO_ENV,
        "postgresql+psycopg://estoque:troque-isto@db/estoque",
    ],
)
def test_reconhece_o_banco_de_desenvolvimento(url: str) -> None:
    assert banco.e_desenvolvimento(url)


@pytest.mark.parametrize(
    "url",
    [
        banco.PADRAO_DONO,
        banco.PADRAO_APP_ASYNC,
        # o CI: mesmo nome de database, num Postgres efemero em outra porta
        "postgresql+psycopg://estoque:troque-isto@localhost:5432/estoque",
    ],
)
def test_nao_confunde_teste_nem_ci_com_desenvolvimento(url: str) -> None:
    assert not banco.e_desenvolvimento(url)


def test_os_padroes_sao_o_banco_de_teste() -> None:
    padroes = (banco.PADRAO_DONO, banco.PADRAO_APP, banco.PADRAO_APP_ASYNC)
    assert {make_url(p).database for p in padroes} == {"estoque_teste"}


def test_ac3_o_app_sob_teste_le_do_banco_em_que_a_fixture_grava() -> None:
    """Sem isto a fixture grava num banco e o servidor le de outro."""
    assert Config.do_ambiente().database_url == banco.URL_APP_ASYNC


def test_ac5_suite_apontada_para_o_dev_nao_roda() -> None:
    r = _pytest("--collect-only", "-q", "tests/domain", DATABASE_URL_TESTE=DEV)
    assert r.returncode != 0
    assert "make db-teste" in r.stdout + r.stderr


def test_ac5_database_url_exportada_do_env_tambem_para() -> None:
    r = _pytest("--collect-only", "-q", "tests/domain", DATABASE_URL=DEV_PELO_ENV)
    assert r.returncode != 0
    assert "make db-teste" in r.stdout + r.stderr


def test_ac5_par_positivo_sem_variavel_nenhuma_a_suite_roda() -> None:
    r = _pytest("--collect-only", "-q", "tests/domain")
    assert r.returncode == 0, r.stdout + r.stderr


def test_ac6_sem_postgres_os_testes_de_banco_pulam_e_dizem_por_que() -> None:
    """A guarda nao pode transformar "sem banco" em falha: isso e' o portao do CI."""
    fechado = "localhost:1/estoque_teste"
    r = _pytest(
        "-q",
        "-rs",
        "tests/data/test_imutabilidade_no_banco.py",
        DATABASE_URL_TESTE=f"postgresql+psycopg://estoque:x@{fechado}",
        DATABASE_URL_TESTE_APP=f"postgresql+psycopg://estoque_app:x@{fechado}",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sem banco" in r.stdout
