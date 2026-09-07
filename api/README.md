# api — Python 3.13 / FastAPI

Domínio, registry, autorização e assistente. **O cliente nunca fala com o banco**
([ADR-0018](../docs/adr/0018-postgres-em-container.md)).

```bash
uv sync
uv run pytest              # testes
uv run mypy --strict src   # tipos
uv run lint-imports        # contratos de arquitetura (ADR-0002, 0007, 0012)
```

## Camadas

| | |
|---|---|
| `domain/` | tipos e regras puras. Sem I/O, sem SQLAlchemy, sem FastAPI |
| `data/` | única porta para dados. `porta.py` é só `Protocol` |
| `registry/` | `ComponentDef` + catálogo derivado por ator |
| `schema/` | o contrato que o modelo produz + validação |
| `assistant/` | prompt, adapter, trace. **Não alcança `commands/`** |
| `commands/` | plano de escrita. Só humano dispara |
| `server/` | borda HTTP, autorização por registro, auditoria |

`uv run lint-imports` falha o build se essas fronteiras forem cruzadas — e
`tests/arquitetura/` prova que ele falha, introduzindo as violações de propósito.
