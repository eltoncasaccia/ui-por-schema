#!/bin/sh
# `docker compose up` tem que bastar. Migracao e seed sao idempotentes, entao
# rodar a cada boot e' seguro e mantem a promessa de um comando so'.
set -e
echo "→ aplicando migrações"
alembic upgrade head
if [ "${SEED_NO_BOOT:-true}" = "true" ]; then
  echo "→ populando dados da Bertoni (idempotente)"
  python -m estoque.data.seed
fi
echo "→ subindo a API"
exec uvicorn estoque.server.app:app --host 0.0.0.0 --port 8000
