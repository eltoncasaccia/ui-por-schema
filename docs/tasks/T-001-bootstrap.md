# T-001 — Bootstrap `api/` e `web/`, CI

| | |
|---|---|
| **Onda** | W0 — Contratos · **serial** |
| **Trilha** | E |
| **Tamanho** | M |
| **Depende de** | T-035 |
| **Bloqueia** | T-002, T-005 |
| **ADRs** | [0016](../adr/0016-api-python-cliente-typescript.md), [0007](../adr/0007-camadas-e-arch-check.md) |

## Objetivo

Os dois projetos compilando, testando e em CI — **vazios**. Nada de domínio, nada
de UI.

## Arquivos de propriedade exclusiva

```
api/pyproject.toml   api/Dockerfile   api/src/estoque/**/__init__.py
api/.python-version  api/pytest.ini
web/package.json     web/Dockerfile   web/tsconfig.json
web/vite.config.ts   web/vitest.config.ts   web/eslint.config.js
```

## Escopo

### Faz — `api/`
- Python 3.13, gerenciado por **`uv`**.
- FastAPI · Pydantic v2 · SQLAlchemy 2.0 (async) · Alembic · `anthropic` · argon2.
- **`mypy --strict`** e **`ruff`** (lint + format).
- `pytest` + `pytest-asyncio`.
- **`import-linter`** com os contratos de camada (regras em T-005).
- Estrutura: `domain/ data/ registry/ schema/ assistant/ autorizacao/ auditoria/ auth/ commands/ server/`

### Faz — `web/`
- Vite + React 18 + TypeScript **estrito máximo**: `strict`,
  `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`.
- TanStack Query + TanStack Router. `openapi-fetch`. CSS Modules.
- Vitest + Testing Library. ESLint.
- Estrutura: `views/ render/ ui/ shell/ query/ estado/ generated/`
  *(corrigido: a tarefa dizia `components/ app/ state/`; os nomes adotados na
  implementação são `ui/ shell/ estado/` — ver [ADR-0031](../adr/0031-ports-and-adapters.md))*

### Faz — CI
`lint` · `typecheck` · `test` · `arch` **nos dois lados**, em todo push.

### Não faz
Regras de arquitetura de verdade (T-005) — aqui só o esqueleto e os comandos.

## Critérios de aceite

- [ ] **AC-1** `make typecheck` passa nos dois projetos vazios, em modo estrito.
- [ ] **AC-2** `make test` executa e reporta zero testes sem falhar, nos dois.
- [ ] **AC-3** CI verde num commit vazio.
- [ ] **AC-4** `mypy --strict` recusa uma função sem anotação de tipo.
      *(negativo)*
- [ ] **AC-5** `tsc` recusa `any` implícito. *(negativo)*
- [ ] **AC-6** As nove pastas da API e as sete do cliente existem.
- [ ] **AC-7** `docker compose up` continua funcionando com os dois `Dockerfile`
      reais, em build multi-stage.
- [ ] **AC-8** `web/package.json` **não** contém dependência de banco de dados.
      *(negativo — [ADR-0018](../adr/0018-postgres-em-container.md))*

## Armadilhas

Afrouxar `--strict` ou `strict` para destravar depois é o começo do fim. Se um tipo
incomodar, o problema é o tipo, não a flag.
