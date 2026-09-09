# Plano — Ciclo 1

As ondas, as trilhas e o grafo de dependências. **Isto quase não muda durante
a execução** — por isso saiu do [BOARD](./BOARD.md), que é editado a cada
tarefa assumida e a cada tarefa concluída.

Procurando o estado de uma tarefa? → [BOARD](./BOARD.md) · [PROGRESSO](./PROGRESSO.md)

---

## 1. Ondas

Uma onda não é prazo, é **barreira de dependência**. Tarefas da mesma onda são
paralelizáveis; a seguinte abre quando as dependências declaradas fecham.

| Onda | O que é | Paralelismo | Abre com |
|---|---|---|---|
| **W0** | Ambiente e contratos congelados | **Serial** | — |
| **W1** | Núcleo: banco, dados, permissão, auth, registry, render | até 13 sessões | T-039 ✅ |
| **W2** | Furo de risco: medição com modelo real | 1 sessão | W1 ✅ |
| **W3** | 15 componentes de leitura | até 7 sessões | T-017 revisado |
| **W4** | 7 componentes de escrita | até 5 sessões | T-025 ✅ — **aberta** |
| **W5** | Garantias e fechamento | até 4 sessões | W4 ✅ |

**W0 é serial de propósito.** Sete tarefas em sequência compram treze simultâneas.

---

## 2. Trilhas

| Trilha | Domínio | Onde |
|---|---|---|
| **A** | Domínio e dados | `api/src/estoque/{domain,data}` · `api/migrations` |
| **B** | Servidor, permissão, auth, auditoria | `api/src/estoque/{server,autorizacao,auditoria,auth,commands}` |
| **C** | Registry e assistente | `api/src/estoque/{registry,schema,assistant}` |
| **D** | Render e interface | `web/src/**` |
| **E** | Ambiente e qualidade | raiz · `web/scripts` · `api/tests` · `eval/` |

**Tarefas de W3 e W4 atravessam A/C e D** — registro em Python, view em TypeScript
([ADR-0017](../adr/0017-registry-servidor-views-cliente.md)). O teste de bijeção
recusa meia entrega.

---

## 3. Grafo de dependências

```mermaid
graph TD
  T035[T-035 Docker Compose] --> T001[T-001 Bootstrap api+web]
  T001 --> T002[T-002 Domínio]
  T002 --> T003[T-003 Contrato registry]
  T003 --> T004[T-004 Borda: schema, viewId]
  T004 --> T039[T-039 Codegen + bijeção]
  T002 --> T005[T-005 Verificadores]

  T039 --> W1{{W1 · núcleo}}
  T002 --> T036[T-036 Schema Postgres]
  T036 --> T006[T-006 Dados Bertoni]
  T036 --> T007[T-007 Repositórios]
  T002 --> T008[T-008 Regras puras]
  T004 --> T009[T-009 Permissão]
  T004 --> T010[T-010 Auditoria]
  T036 --> T037[T-037 Auth + CSRF]
  T009 --> T011[T-011 Servidor]
  T010 --> T011
  T037 --> T011
  T009 --> T012[T-012 Catálogo]
  T012 --> T013[T-013 Validador]
  T004 --> T014[T-014 Adapter Claude]
  T039 --> T015[T-015 Motor de render]
  T013 --> T016[T-016 Query + viewId]
  T015 --> T016

  T011 --> T017[T-017 SPIKE medição]
  T014 --> T017
  T016 --> T017

  T017 --> W3{{W3 · 15 componentes de leitura}}
  W3 --> T018[T-018 Lote]
  W3 --> T019[T-019 Produto]
  W3 --> T020[T-020 Vencimento]
  W3 --> T021[T-021 Rastreabilidade]
  W3 --> T022[T-022 Recebimento]
  W3 --> T023[T-023 Temperatura]
  W3 --> T024[T-024 Movimento]

  T011 --> T025[T-025 Pipeline de comando]
  T015 --> T025
  T025 --> T026[T-026 Receber]
  T025 --> T027[T-027 Quarentena]
  T025 --> T028[T-028 Saída FEFO]
  T025 --> T029[T-029 Estorno]
  T028 --> T030[T-030 Controlado]

  T026 --> T031[T-031 Telas com rota]
  T027 --> T031
  T028 --> T031
  T031 --> T038[T-038 Gestão de usuários]
  T017 --> T032[T-032 Avaliação]
  T030 --> T033[T-033 Segurança]
  T031 --> T034[T-034 Fechamento]
  T032 --> T034
  T033 --> T034
```

**Caminho crítico** (12 tarefas):
`T-035 → T-001 → T-002 → T-003 → T-004 → T-039 → T-012 → T-015 → T-016 → T-017 → T-018 → T-027 → T-031 → T-034`

---
