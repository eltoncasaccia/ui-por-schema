"""Alembic roda SINCRONO e como DONO do banco.

Duas decisoes deliberadas:

1. Driver sincrono (`psycopg`), enquanto a aplicacao usa `asyncpg`. Migracao e'
   tarefa administrativa de uma passada — async nao compra nada aqui, e asyncpg
   nao executa multiplos comandos num mesmo prepared statement, o que tornaria
   cada migracao um picadinho de `op.execute`.

2. Conecta como DONO, nao como a aplicacao. E' essa separacao que faz o REVOKE
   da migracao 0001 ter efeito: o dono de uma tabela ignora privilegios negados,
   entao se a API conectasse como dono, RN-M02 continuaria sendo so' convencao.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

url = os.environ.get("DATABASE_URL_ADMIN") or os.environ["DATABASE_URL"]
# a aplicacao usa asyncpg; a migracao usa o driver sincrono
url_sync = url.replace("+asyncpg", "+psycopg")
target_metadata = None  # migracoes escritas a mao, sem autogenerate

if context.is_offline_mode():
    context.configure(url=url_sync, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url_sync, future=True)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
