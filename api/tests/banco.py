"""O banco dos testes, num lugar so' — T-052, achado A-44.

Os testes de banco repetiam, em 13 arquivos, o endereco do banco de
DESENVOLVIMENTO como padrao, e o que gravavam ficava la': usuario, sessao,
auditoria, movimento. Os dois ultimos sao append-only, entao nao ha limpeza
seletiva — so' `make reset`. Em 2026-09-14 eram 262 usuarios de teste contra 8
reais, na tela do diretor.

O padrao agora e' o database `estoque_teste`, no mesmo Postgres. O CI continua
declarando as tres variaveis, contra o banco efemero dele.

`python tests/banco.py` cria, migra e semeia o `estoque_teste` — e' o `make db-teste`.
"""

import os
import subprocess
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

BANCO_TESTE = "estoque_teste"
_LOCAL = "localhost:15432"

PADRAO_DONO = f"postgresql+psycopg://estoque:troque-isto@{_LOCAL}/{BANCO_TESTE}"
PADRAO_APP = f"postgresql+psycopg://estoque_app:app@{_LOCAL}/{BANCO_TESTE}"
PADRAO_APP_ASYNC = f"postgresql+asyncpg://estoque_app:app@{_LOCAL}/{BANCO_TESTE}"

# O dono insere usuario e sessao, que `estoque_app` nao pode (A-27); os dois
# `APP` sao o papel da aplicacao, sincrono para sonda e assincrono para o pipeline.
URL_DONO = os.environ.get("DATABASE_URL_TESTE", PADRAO_DONO)
URL_APP = os.environ.get("DATABASE_URL_TESTE_APP", PADRAO_APP)
URL_APP_ASYNC = os.environ.get("DATABASE_URL_TESTE_APP_ASYNC", PADRAO_APP_ASYNC)

# O banco de desenvolvimento pelos dois enderecos em que ele aparece: a porta que
# o `make db-local` publica, e o servico do compose — que e' o que o `.env` traz,
# e que alguns testes convertem para localhost.
_DESENVOLVIMENTO = {("localhost", 15432), ("127.0.0.1", 15432), ("db", 5432)}


def e_desenvolvimento(url: str) -> bool:
    u = make_url(url)
    return u.database == "estoque" and (u.host, u.port or 5432) in _DESENVOLVIMENTO


def erro_de_endereco() -> str | None:
    """A mensagem de parada, se algum endereco dos testes cair no banco de dev.

    Parar, e nao pular: pular e' o que o CI reprova, e o que esconderia a volta do
    A-44 numa suite verde.
    """
    enderecos = {
        "DATABASE_URL_TESTE": URL_DONO,
        "DATABASE_URL_TESTE_APP": URL_APP,
        "DATABASE_URL_TESTE_APP_ASYNC": URL_APP_ASYNC,
        "DATABASE_URL": os.environ.get("DATABASE_URL", URL_APP_ASYNC),
    }
    ruins = sorted(nome for nome, url in enderecos.items() if e_desenvolvimento(url))
    if not ruins:
        return None
    return (
        f"{', '.join(ruins)} aponta para o banco de DESENVOLVIMENTO, e o que os testes "
        "gravam ali nao se apaga (achado A-44). Tire a variavel do ambiente — o padrao "
        f"e' `{BANCO_TESTE}` — e rode `make db-local && make db-teste`."
    )


def preparar() -> int:
    """Cria o database se faltar, migra e semeia. Idempotente, como migracao e seed."""
    alvo = make_url(URL_DONO)
    nome = alvo.database
    if not nome or e_desenvolvimento(URL_DONO):
        print(f"recusado: {alvo.render_as_string()} nao e' banco de teste", file=sys.stderr)
        return 1
    # CREATE DATABASE nao roda em transacao, nem de dentro do database que ainda
    # nao existe: conecta no `postgres`, com autocommit.
    manutencao = alvo.set(drivername="postgresql", database="postgres")
    try:
        with psycopg.connect(
            manutencao.render_as_string(hide_password=False), autocommit=True, connect_timeout=2
        ) as c:
            existe = c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (nome,))
            if existe.fetchone() is None:
                c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nome)))
                print(f"-> criado {nome}")
    except psycopg.OperationalError as e:
        print(
            f"sem banco em {alvo.host}:{alvo.port} — rode `make db-local` ({e})",
            file=sys.stderr,
        )
        return 1
    # Migracao e seed como DONO, o mesmo papel do `make migrate` e do `make seed`,
    # so' que apontados para o banco de teste.
    env = {**os.environ, "DATABASE_URL_ADMIN": URL_DONO}
    api = Path(__file__).resolve().parents[1]
    for passo in (["alembic", "upgrade", "head"], ["estoque.data.seed"]):
        subprocess.run([sys.executable, "-m", *passo], cwd=api, env=env, check=True)  # noqa: S603
    return 0


if __name__ == "__main__":
    raise SystemExit(preparar())
