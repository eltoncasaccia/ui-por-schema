.DEFAULT_GOAL := help
SHELL := /bin/bash

help:  ## mostra os comandos
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n",$$1,$$2}'

.env:
	@cp -n .env.example .env && echo "criado .env a partir de .env.example — revise os segredos"

up: .env  ## sobe tudo (db + api + web)
	docker compose up --build

down:  ## derruba os serviços
	docker compose down

reset:  ## derruba e APAGA os dados
	docker compose down -v

logs:  ## acompanha os logs
	docker compose logs -f

db-local:  ## publica o Postgres em localhost:15432 (só dev, exige -f explícito)
	docker compose -f docker-compose.yml -f compose.local.yml up -d db

migrate:  ## aplica as migrações
	docker compose run --rm api alembic upgrade head

seed:  ## popula o banco com os dados da Bertoni (idempotente)
	docker compose run --rm api python -m estoque.data.seed

types:  ## gera os tipos do cliente a partir do OpenAPI
	cd web && npm run gerar-tipos

test:  ## testes dos dois lados
	cd api && uv run pytest -q
	cd web && npx vitest run

typecheck:  ## mypy --strict + tsc
	cd api && uv run mypy --strict src
	cd web && npx tsc --noEmit

lint:  ## ruff + eslint
	cd api && uv run ruff check src tests && uv run ruff format --check src tests
	cd web && npx eslint src

arch:  ## verificadores de arquitetura dos dois lados
	cd api && uv run lint-imports
	cd web && npx tsx scripts/arch-check.ts

eval:  ## suíte de avaliação do assistente
	cd api && uv run python -m eval.executar

check: lint typecheck test arch  ## tudo que o CI roda

.PHONY: help up down reset logs db-local migrate seed types test typecheck lint arch eval check
