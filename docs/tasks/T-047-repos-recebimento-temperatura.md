# T-047 — Repositórios de recebimento e temperatura (escopo deferido da T-007)

| | |
|---|---|
| **Trilha** | A · dados |
| **Tamanho** | G |
| **Depende de** | T-036 (schema), T-007 (padrão dos repos) |
| **Bloqueia** | **T-022**, **T-023** |
| **Origem** | achado [A-32](./ACHADOS.md), execução da T-022 (2026-09-09) |
| **Regras** | RN-A01 · RN-R01 · RN-R04 · RN-R05 · RN-F01 |

## Por que existe

A T-007 listava "repositórios ... recebimento" no escopo e foi marcada ✅, mas
entregou isto:

```python
# server/deps.py
recebimento=None,  # type: ignore  # ciclo 1: T-022
temperatura=None,  # type: ignore  # ciclo 1: T-023
```

Não há `RepoRecebimentoSQL` nem `RepoTemperaturaSQL` em `data/repositorios.py`,
não há fake (é `_NaoUsado()` em `fakes.py`), e **não há um único recebimento no
seed**. As duas tarefas de componente que dependem disso — T-022 e T-023 — não
têm como rodar, e nenhuma delas é dona de `repositorios.py`, `deps.py`, `seed/`
ou `fakes.py`. Esta tarefa termina o que a T-007 deixou pela metade.

## Arquivos de propriedade exclusiva

```
api/tests/data/test_repos_recebimento_temperatura.py
```

## Toca, com registro (escopo deferido da T-007 / infra compartilhada)

```
api/src/estoque/data/repositorios.py     RepoRecebimentoSQL, RepoTemperaturaSQL, tradutores
api/src/estoque/server/deps.py           troca os dois `None` pelos repos reais
api/tests/registry/fakes.py              FakeRepoRecebimento, FakeRepoTemperatura + fixture mínima
api/src/estoque/data/seed/dados.py       recebimentos() — os casos da Bertoni
api/src/estoque/data/seed/__main__.py    bloco de upsert de recebimento
```

> Todos são escopo original da T-007/T-006. O registro fica aqui e no commit.

## Escopo

### Faz

- **`RepoRecebimentoSQL`** — `por_id(rid, ctx)` e `listar(ctx)`, ambos com
  `_escopo(unidade_id, ctx)` (RN-A01). `listar` ordena por `recebido_em` desc.
  Tradutor `_para_recebimento`.
- **`RepoTemperaturaSQL`** — `serie(unidade_id, de, ate, ctx)` com `_escopo` +
  `unidade_id` + `medido_em BETWEEN de AND ate`, ordenado por `medido_em`.
  Tradutor `_para_temperatura`.
- **Fiação** em `deps.py`.
- **Fakes** que **intersectam escopo do mesmo jeito que a porta manda** (RN-A01),
  como `FakeRepoLote` já faz — pedido fora do escopo devolve vazio / `None`.
- **Fixture mínima** em `fakes.py`: recebimentos cobrindo os casos que T-022
  precisa exercitar — normal, com `divergencia=True` (RN-R04), de controlado com
  `rt_id` preenchido (RN-R05), de termolábil com `temperatura_chegada_c` (RN-F01),
  e um em cada unidade (para o teste de escopo do T-022). Série de temperatura
  para T-023 (a de `seed/dados.py::temperaturas()` já tem a forma).
- **Seed** — `recebimentos()` em `dados.py` com os mesmos casos, e o upsert em
  `__main__.py`.

### Não faz

- **`lote.recebimento_id`** (link recebimento → "lotes gerados"). É mudança de
  schema + campo em `Lote` (CONTRATOS §3). Fica para uma tarefa de contrato
  própria; `recebimento_detalhe` (T-022) trata "lotes gerados" como item
  descopado, com achado, se precisar.
- Os componentes em si (T-022, T-023).
- Registrar recebimento (T-026) — este é só leitura.

## Critérios de aceite

- [ ] **AC-1** `RepoRecebimentoSQL.listar` e `.por_id` **nunca** devolvem
      recebimento de unidade fora do escopo do ator — provado no banco, com um
      ator restrito pedindo (inclusive por `unidade_id` no critério, se houver).
      *(negativo — RN-A01)*
- [ ] **AC-2** `RepoTemperaturaSQL.serie` idem: unidade fora do escopo devolve
      série vazia, não erro. *(negativo — RN-A01)*
- [ ] **AC-3** `por_id` de recebimento inexistente **e** de recebimento fora do
      escopo devolvem `None` pelo mesmo caminho. *(negativo — ADR-0014)*
- [ ] **AC-4** O fake e o repositório real concordam na interseção de escopo —
      a mesma asserção roda contra os dois (bateria da T-042 se já existir, ou o
      par de testes aqui).
- [ ] **AC-5** `make seed` popula recebimentos e é idempotente (rodar duas vezes
      não duplica). O seed cobre divergência, controlado e termolábil.
- [ ] **AC-6** `deps.py` não tem mais `recebimento=None` nem `temperatura=None`;
      `mypy --strict` passa sem o `type: ignore` daquelas linhas.

## Armadilhas

**Fake permissivo.** Um fake que não intersecta escopo faz toda a suíte de
registry de T-022/T-023 passar sobre um buraco (é o achado A-11). A interseção é
invariante da porta, não passo do `load`.

**Ordenar no Python.** `listar` e `serie` ordenam no SQL (`ORDER BY`), como os
outros repos — ordenação estável é o que a paginação por cursor assume.
