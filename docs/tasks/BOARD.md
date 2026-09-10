# Board — Ciclo 1

**39 tarefas · 6 ondas · 5 trilhas · 2 linguagens.**
Regras: [Acordo de Trabalho](./README.md) · Interfaces: [CONTRATOS](./CONTRATOS.md)
Ondas, trilhas e grafo: [PLANO](./PLANO.md) · Achados: [ACHADOS](./ACHADOS.md)

Legenda: `⬜ disponível` · `🔵 em andamento` · `🔴 bloqueada` · `🟡 em revisão` · `✅ concluída`

> **Assumir tarefa = editar a linha dela nesta tabela.** Esse commit é o lock.
>
> **Concluir = marcar os ACs verificados no arquivo da tarefa E mudar o status
> aqui, no MESMO commit.** Este board já foi ficção uma vez: dizia que nada
> tinha sido feito enquanto 19 tarefas estavam prontas
> ([A-002](../relatorios/A-002-auditoria-de-execucao.md)). O detalhe por tarefa
> está em [PROGRESSO](./PROGRESSO.md).

---

## 1. Tarefas

### W0 — Ambiente e contratos · serial

| Id | Tarefa | Trilha | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-035](./T-035-docker-compose.md) | **Docker Compose, Makefile, README** | E | M | — | ✅ |
| [T-001](./T-001-bootstrap.md) | Bootstrap `api/` e `web/`, CI | E | M | T-035 | ✅ |
| [T-002](./T-002-dominio-tipos-erros.md) | Domínio: 7 tipos, erros, identidade | A | M | T-001 | ✅ |
| [T-003](./T-003-contrato-registry.md) | Contrato do registry (sem `render`) | C | M | T-002 | ✅ |
| [T-004](./T-004-contratos-de-borda.md) | Schema, `viewKey`/`viewId`, envelope | C | M | T-002, T-003 | ✅ |
| [T-039](./T-039-codegen-e-bijecao.md) | **Codegen OpenAPI→TS + bijeção** · congela | C | M | T-003, T-004 | ✅ |
| [T-005](./T-005-arch-check.md) | Verificadores: `import-linter` + `arch:check` | E | M | T-002 | ✅ |

### W1 — Núcleo · até 13 sessões

| Id | Tarefa | Trilha | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-036](./T-036-schema-postgres.md) | **Schema Postgres, migrações, restrições** | A | G | T-002, T-035 | ✅ |
| [T-006](./T-006-fixtures.md) | Dados da Bertoni (seed determinístico) | A | M | T-036 | ✅ |
| [T-007](./T-007-repositorios.md) | Porta de dados e repositórios SQLAlchemy | A | M | T-036 | ✅ |
| [T-008](./T-008-regras-puras.md) | FEFO, validade, **status efetivo**, saldo | A | M | T-002 | ✅ |
| [T-009](./T-009-motor-de-permissao.md) | Motor de permissão e escopo | B | M | T-004 | ✅ |
| [T-010](./T-010-auditoria.md) | Trilha de auditoria append-only | B | M | T-004 | ✅ |
| [T-037](./T-037-autenticacao.md) | **Autenticação, sessão, CSRF** | B | G | T-004, T-036 | ✅ |
| [T-011](./T-011-servidor.md) | Servidor FastAPI, autorização por registro | B | G | T-009, T-010, T-037 | 🟡 |
| [T-012](./T-012-catalogo.md) | Registry runtime e catálogo por ator | C | M | T-004, T-009 | ✅ |
| [T-013](./T-013-validador-schema.md) | Validador de schema e revalidação | C | M | T-012 | ✅ |
| [T-014](./T-014-adapter-modelo.md) | Adapter Claude e Execution Trace | C | M | T-004 | ✅ |
| [T-015](./T-015-motor-de-render.md) | Motor de render e política de layout | D | M | T-039 | ✅ |
| [T-016](./T-016-query-e-viewkey.md) | TanStack Query, `viewId`, rotas | D | M | T-013, T-015 | 🟡 |

### W2 — Furo de risco · 1 sessão

| Id | Tarefa | Trilha | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-017](./T-017-spike-medicao.md) | **SPIKE: medição com modelo real** | C | M | T-011, T-014, T-016 | ✅ |

> **A tarefa que pode matar o projeto**, e por isso está aqui e não no fim.
> **Nenhuma tarefa de W3 começa antes de o relatório R-001 ser lido.**
> R-001 entregue em 2026-09-09 ([relatório](../relatorios/R-001-medicao-modelo-real.md)):
> 100% de schema válido nos dois modelos e nos dois modos — **seguir**. Lacunas
> do spike (AC-1, 17 casos em vez de 30) em R-001 §8 e achado A-08b.

### W3 — Leitura · até 7 sessões · 15 componentes

| Id | Tarefa | Componentes | Tam. | Status |
|---|---|---|---|---|
| [T-018](./T-018-componentes-lote.md) | Lote | `lote_lista` `lote_detalhe` `lote_movimentos` `quarentena_fila` | G | ✅ |
| [T-019](./T-019-componentes-produto.md) | Produto e custo restrito | `produto_ficha` `produto_saldo_por_unidade` | M | ✅ |
| [T-020](./T-020-vencimento-indicador.md) | Vencimento, indicador e curva | `fila_vencimento` `estoque_indicador` `vencimento_grafico` | G | ✅ |
| [T-021](./T-021-rastreabilidade.md) | Rastreabilidade `CA-01` | `rastreabilidade` | M | ✅ |

> **T-019 fechou com AC-7 em branco:** `RN-P06` (mín/máx por unidade) não tem
> armazenamento no sistema. Achado [A-30](./ACHADOS.md), tarefa
> [T-046](./T-046-minimo-maximo-por-unidade.md).
>
> **T-021 fechou:** o recorte de período do `RN-D04` foi feito no `load` porque
> `RepoMovimento.por_cliente` ignora `de`/`ate` (achado [A-31](./ACHADOS.md),
> conserto em T-007/T-042). `RNF-01` medido de verdade fica para T-034.
| [T-022](./T-022-recebimento-leitura.md) | Recebimento | `recebimento_lista` `recebimento_detalhe` | M | ✅ |
| [T-023](./T-023-temperatura.md) | Cadeia fria `CA-07` | `temperatura_historico` `temperatura_excursoes` | M | ✅ |
| [T-024](./T-024-movimento-auditoria.md) | Movimento e trilha | `movimento_lista` `auditoria_trilha` | M | ✅ |
| [T-047](./T-047-repos-recebimento-temperatura.md) | **Repos de recebimento e temperatura** — escopo deferido da T-007 ([A-32](./ACHADOS.md)) | G | ✅ |

> **T-047 fechou:** `RepoRecebimentoSQL` / `RepoTemperaturaSQL` existem, `deps.py`
> não passa mais `None`, o seed tem 6 recebimentos (divergência, controlado,
> termolábil), e a bateria de escopo roda contra fake **e** banco. **T-022 e
> T-023 desbloqueadas.** "Lotes gerados" (`lote.recebimento_id`) segue sem
> schema — item descopado da T-022.
>
> **T-022 fechou:** `recebimento_lista` (params `unidade_id?` `status?`
> `periodo` — `de`/`ate` viraram enum, risco R-5) e `recebimento_detalhe`
> registrados, com escopo negativo por Odair, `status` enum fechado e custo
> invisível provados. **AC-1 em branco** — "gerou lote em quarentena" depende de
> `lote.recebimento_id`, que não existe. **RN-R03 sem armazenamento** para
> integridade/validade como conferências registradas: achado
> [A-33](./ACHADOS.md).
>
> **T-023 fechou:** `temperatura_historico` (série com faixa 2–8 °C, agregação
> automática acima de 480 pontos, `csv` no viewmodel) e `temperatura_excursoes`
> (ocorrências fora da faixa + lotes presentes até o fim da janela, `RN-F04`).
> AC-1..AC-6 verificados. **Exportação (AC-2) é client-side a partir do
> viewmodel** — não há endpoint de export no ciclo 1 ([A-23](./ACHADOS.md)); os
> mesmos dados da tela, por construção.

### W4 — Escrita · até 5 sessões · 7 componentes

| Id | Tarefa | Componentes | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-025](./T-025-pipeline-de-comando.md) | Pipeline de comando e confirmação | *(nenhum — ver nota)* | G | T-011, T-015 | ✅ |
| [T-026](./T-026-recebimento-registrar.md) | Registrar recebimento | `recebimento_registrar` | G | T-025, T-022 | ⬜ |
| [T-027](./T-027-quarentena-e-status.md) | Quarentena e status | `quarentena_liberar` `lote_status_acao` | G | T-025, T-018 | ✅ |
| [T-028](./T-028-saida-fefo.md) | Saída com FEFO | `movimento_saida` | G | T-025, T-008 | ✅ |
| [T-029](./T-029-estorno-descarte.md) | Estorno e descarte | `movimento_estorno` `movimento_descarte` | M | T-025, T-024 | ⬜ |
| [T-030](./T-030-controlado-autorizar.md) | Dupla identificação `CA-04` | `controlado_autorizar` | G | T-028, T-024 | ✅ |

> **`confirm_action` saiu do catálogo** (achado A-05). Confirmação é decisão do
> motor de render diante de `CommandDef.confirm`, não composição que o modelo
> escolhe — mesmo tratamento de `sem_acesso`.

### Abertas pela auditoria A-002

| Id | Tarefa | Trilha | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-040](./T-040-csrf-e-rate-limit.md) | **CSRF e rate limit** — segurança prometida e ausente | B | M | T-037 | ✅ |
| [T-041](./T-041-ci.md) | CI no GitHub Actions | E | P | T-001 | ✅ |
| [T-042](./T-042-contract-test-repositorios.md) | **Contract test** fake ↔ repositório real — hoje o escopo do adaptador não é testado | A | M | T-007 | ⬜ |
| T-043 | Instrumentação ao vivo do pipeline do assistente (duração real de span) | C | M | T-011 | ⬜ |
| [T-044](./T-044-relatorio-movimentacao.md) | `relatorio_movimentacao` — relatório parametrizado ([ADR-0029](../adr/0029-relatorio-como-componente.md)) | C | M | T-024 | ⬜ |

| [T-045](./T-045-borda-http-por-router.md) | **Borda HTTP por router** — `app.py` tinha 817 linhas e 4 tarefas escreviam nele ([ADR-0032](../adr/0032-borda-http-por-router.md)) | E | M | — | ✅ |

| [T-046](./T-046-minimo-maximo-por-unidade.md) | **Mín/máx por produto e unidade** (`RN-P06`) — sem armazenamento no sistema; é também tarefa de contrato (CONTRATOS §4). Aberta pela T-019 ([A-30](./ACHADOS.md)) | A | M | T-002, T-007, T-036, T-006 | ⬜ |

### W5 — Garantias e fechamento · até 4 sessões

| Id | Tarefa | Trilha | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-031](./T-031-telas-com-rota.md) | Superfície tradicional: telas com rota | D | G | T-026, T-027, T-028 | ⬜ |
| [T-038](./T-038-gestao-de-usuarios.md) | **Gestão de usuários** (fora do catálogo) | D | M | T-037, T-031 | ⬜ |
| [T-032](./T-032-suite-de-avaliacao.md) | Suíte de avaliação, 40 perguntas | E | G | T-017, W3 | 🟡 |
| [T-033](./T-033-testes-de-seguranca.md) | Segurança CS-01 a CS-06 | E | G | W3, W4 | 🟡 |
| [T-034](./T-034-fechamento.md) | Relatório de fechamento | E | M | T-031, T-032, T-033 | ⬜ |

---

## 2. Contagem de catálogo

Teto de 25 ([ADR-0011](../adr/0011-teto-de-catalogo.md)), verificado por `RNF-08`.

| Onda | Componentes | Acumulado |
|---|---|---|
| W3 | 15 de leitura + `vencimento_grafico` | 16 |
| W4 | 7 de escrita | **23** |

> **T-044 acrescenta +1 ao catálogo: 24, folga 1.** Um segundo relatório estoura
> o teto de 25 e vira discussão de escopo (ADR-0011).

**Registrados hoje: 20** — `fila_vencimento` `estoque_indicador` `vencimento_grafico`
(T-020), `lote_lista` `lote_detalhe` `lote_movimentos` `quarentena_fila` (T-018),
`quarentena_liberar` `lote_status_acao` (T-027), `movimento_saida` (T-028),
`controlado_autorizar` (T-030), `movimento_lista` `auditoria_trilha` (T-024),
`produto_ficha` `produto_saldo_por_unidade` (T-019), `rastreabilidade` (T-021),
`recebimento_lista` `recebimento_detalhe` (T-022) e `temperatura_historico`
`temperatura_excursoes` (T-023).
**4 de escrita, teto 25.**

**23 ao final, folga de 2.** Toda tarefa que registra componente atualiza esta tabela no
mesmo commit. Acima de 25 o build quebra, e a discussão é de escopo.

---
