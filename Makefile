.DEFAULT_GOAL := help
SHELL := /bin/bash

help:  ## mostra os comandos
	@grep -E '^[a-z0-9-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-15s\033[0m %s\n",$$1,$$2}'

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

# O banco dos testes, separado do de desenvolvimento (T-052, A-44): o que teste
# grava em movimento e auditoria nao se apaga. `uv` local, e nao `compose run`,
# que recriaria o container do banco sem a porta.
db-teste:  ## cria, migra e semeia o estoque_teste — o banco dos testes (idempotente)
	cd api && uv run python tests/banco.py

migrate:  ## aplica as migrações
	docker compose run --rm api alembic upgrade head

seed:  ## popula o banco com os dados da Bertoni (idempotente)
	docker compose run --rm api python -m estoque.data.seed

env:  ## compara o .env com o .env.example
	@python3 scripts/env.py

env-completar:  ## acrescenta ao .env as variáveis novas do exemplo
	@python3 scripts/env.py --completar

modelo:  ## mostra o modelo e o provedor EFETIVOS (não o que o .env diz)
# Pergunta à própria fábrica, não ao ambiente: `LLM_BASE_URL` só vale para o
# provedor `compativel`, e ecoar a variável crua dizia que o OpenRouter ia para
# o Ollama quando ele não ia. Diagnóstico que mente é pior que diagnóstico
# ausente — quem confia nele procura o defeito no lugar errado.
	@docker compose exec -T api python -c "\
import os; from estoque.assistant.fabrica import criar_adaptador; \
a = criar_adaptador(); \
print('provedor :', os.environ.get('PROVEDOR', 'openrouter')); \
print('modelo   :', a._modelo); \
print('modo     :', os.environ.get('MODO_DECODIFICACAO', 'restrito')); \
print('base     :', a._base); \
print('chave    :', a._nome_da_chave, '(preenchida)' if a._chave else '(VAZIA)')"


gerar-indice:  ## regenera registry/indice.py e views/indice.ts varrendo os diretórios
	@python3 scripts/gerar_indice.py

types: gerar-indice  ## gera os tipos do cliente a partir do registry da API
	cd api && uv run python -m estoque.application.registry.exportar > ../web/src/generated/contrato.json
	cd web && npx tsx scripts/gerar-tipos.ts

# Um alvo por lado, e os dois lados juntos. Motivo: quem escreve Python pagava
# `tsc`, `eslint` e `vitest` a CADA iteracao do laco de correcao — e a saida
# desses tres nao ajuda quem esta consertando um teste de pytest. Durante a
# implementacao rode so' o `check-` do seu lado; `make check` inteiro uma vez, no
# fim, antes do commit.
#
# A excecao e' `indice`: a bijecao registry <-> view e' cross-side por desenho
# (ADR-0017), entao nao se divide, e fica fora de `check-api` e `check-web`.

rn:  ## imprime só as regras citadas — `make rn RN-L05 RN-R02`
	@python3 scripts/rn.py $(filter-out rn,$(MAKECMDGOALS))

# Deixa `RN-L05` ser argumento de `make rn` sem virar alvo desconhecido. O padrao
# e' `RN-%` e nao `%` de proposito: um alvo digitado errado continua falhando
# alto, que e' o que se quer.
RN-%:
	@:

test-api:  ## pytest
	cd api && uv run pytest -q

test-web:  ## vitest — reporter `dot`: uma linha por arquivo, a falha inteira
	cd web && npx vitest run --reporter=dot

capturas:  ## regenera os prints do README a partir do sistema no ar (exige make up)
	cd web && npx tsx scripts/capturar-telas.ts

e2e: db-teste  ## Playwright: navegacao e catalogo por ator, em servidores proprios (8001/5174)
	cd web && npx playwright test

test: test-api test-web  ## testes dos dois lados

# `src` E `tests`: o achado A-09 nasceu de `tests` ficar de fora, e dez erros
# de tipo viverem lá, invisíveis ao DoD e ao CI, visíveis a quem abre o arquivo.
typecheck-api:  ## mypy --strict em src e tests
	cd api && uv run mypy --strict src tests

typecheck-web:  ## tsc --noEmit
	cd web && npx tsc --noEmit

typecheck: typecheck-api typecheck-web  ## mypy --strict + tsc

lint-api:  ## ruff check + ruff format --check
	cd api && uv run ruff check src tests && uv run ruff format --check src tests

lint-web:  ## eslint — o formatador padrão não imprime nada quando está limpo
	cd web && npx eslint src scripts e2e

lint: lint-api lint-web  ## ruff + eslint

indice:  ## confere a bijeção registry ↔ view (ADR-0017) — cross-side, não divide
	@python3 scripts/gerar_indice.py --conferir

arch-api:  ## os quatro contratos do import-linter
	cd api && uv run lint-imports

arch-web:  ## camadas do cliente
	cd web && npx tsx scripts/arch-check.ts

arch: indice arch-api arch-web  ## verificadores de arquitetura dos dois lados

check-api: lint-api typecheck-api test-api arch-api  ## só o backend — use durante a implementação
check-web: lint-web typecheck-web test-web arch-web  ## só o cliente — use durante a implementação

eval:  ## suíte de avaliação: mede os dois modos e publica no LangFuse
	docker compose run --rm api python -m estoque.eval

eval-livre:  ## só o modo livre — a pergunta original da v1
	docker compose run --rm api python -m estoque.eval --modo livre

check: lint typecheck test arch  ## tudo que o CI roda

.PHONY: help up down reset logs db-local db-teste env env-completar modelo eval-livre migrate seed \
	gerar-indice types indice rn \
	test test-api test-web typecheck typecheck-api typecheck-web \
	lint lint-api lint-web arch arch-api arch-web \
	check check-api check-web eval
