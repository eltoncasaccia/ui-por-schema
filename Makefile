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

env:  ## compara o .env com o .env.example
	@python3 scripts/env.py

env-completar:  ## acrescenta ao .env as variáveis novas do exemplo
	@python3 scripts/env.py --completar

modelo:  ## mostra qual modelo e provedor estão em uso
	@docker compose exec -T api sh -c 'echo "provedor : $$PROVEDOR"; echo "modelo   : $$MODELO_ASSISTENTE"; echo "modo     : $$MODO_DECODIFICACAO"; echo "base     : $${LLM_BASE_URL:-(padrão do provedor)}"'

gerar-indice:  ## regenera registry/indice.py e views/indice.ts varrendo os diretórios
	@python3 scripts/gerar_indice.py

types: gerar-indice  ## gera os tipos do cliente a partir do registry da API
	cd api && uv run python -m estoque.application.registry.exportar > ../web/src/generated/contrato.json
	cd web && npx tsx scripts/gerar-tipos.ts

test:  ## testes dos dois lados
	cd api && uv run pytest -q
	cd web && npx vitest run

typecheck:  ## mypy --strict + tsc
	# `src` E `tests`: o achado A-09 nasceu de `tests` ficar de fora, e dez erros
	# de tipo viverem lá, invisíveis ao DoD e ao CI, visíveis a quem abre o arquivo.
	cd api && uv run mypy --strict src tests
	cd web && npx tsc --noEmit

lint:  ## ruff + eslint
	cd api && uv run ruff check src tests && uv run ruff format --check src tests
	cd web && npx eslint src scripts

arch:  ## verificadores de arquitetura dos dois lados
	@python3 scripts/gerar_indice.py --conferir
	cd api && uv run lint-imports
	cd web && npx tsx scripts/arch-check.ts

eval:  ## suíte de avaliação: mede os dois modos e publica no LangFuse
	docker compose run --rm api python -m estoque.eval

eval-livre:  ## só o modo livre — a pergunta original da v1
	docker compose run --rm api python -m estoque.eval --modo livre

check: lint typecheck test arch  ## tudo que o CI roda

.PHONY: help up down reset logs db-local env env-completar modelo eval-livre migrate seed gerar-indice types test typecheck lint arch eval check
