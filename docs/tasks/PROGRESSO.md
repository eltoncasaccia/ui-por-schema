# Progresso — checklist de execução

**A regra:** o status muda **no mesmo commit da entrega**, nunca depois. Um
critério de aceite não conferido **fica em branco** — marcar por otimismo é pior
que deixar vazio, porque cria evidência falsa.

Estado apurado pela [auditoria A-002](../relatorios/A-002-auditoria-de-execucao.md),
atualizado a cada entrega.

**25 concluídas · 4 parciais · 13 não iniciadas** · 10 de 24 componentes previstos.

`✅ concluída` · `🟡 parcial` · `⬜ não iniciada` · `🔴 bloqueada`

---

## Como usar

Ao terminar uma tarefa, **três coisas no mesmo commit**:

1. marcar os `- [ ]` do arquivo da tarefa que foram **de fato verificados**
2. mudar a linha aqui e no [BOARD](./BOARD.md)
3. se mudou escopo, revisar o [PRD](../prd/PRD-001-ciclo-1.md)

Antes de marcar concluída, a pergunta é sempre a mesma: **cada AC tem um teste
ou uma verificação que eu executei?** Se a resposta for "deve funcionar", não
está pronto.

---

## W0 — Ambiente e contratos

| | Tarefa | Estado | O que falta |
|---|---|---|---|
| T-035 | Docker Compose, Makefile, README | ✅ | AC-5 (CI) pendente — ver A-07 |
| T-001 | Bootstrap `api/` e `web/` | ✅ | AC-3 (CI verde) pendente — ver A-07 |
| T-002 | Domínio: 7 tipos, erros, identidade | ✅ | — |
| T-003 | Contrato do registry | ✅ | — |
| T-004 | Schema, `viewKey`/`viewId`, envelope | ✅ | — |
| T-039 | Codegen do registry → TS + bijeção | ✅ | 6 ACs verificados negativamente |
| T-005 | Verificadores de arquitetura | 🟡 | 4 de 6 regras Python; **as 6 do TS não existem** |

## W1 — Núcleo

| | Tarefa | Estado | O que falta |
|---|---|---|---|
| T-036 | Schema Postgres, migrações, restrições | ✅ | — |
| T-006 | Dados da Bertoni (seed) | ✅ | — |
| T-007 | Porta de dados e repositórios | ✅ | — |
| T-008 | FEFO, validade, status efetivo, saldo | ✅ | — |
| T-009 | Motor de permissão e escopo | ✅ | — |
| T-010 | Trilha de auditoria | ✅ | — |
| T-037 | Autenticação, sessão, CSRF | ✅ | CSRF e rate limit entregues em T-040 |
| T-011 | Servidor FastAPI | 🟡 | `Idempotency-Key` e `If-Match` **implementados na T-025** (rota `/api/comandos/{nome}`, com teste de borda). AC-3 e AC-4 da T-011 passam a valer; os demais ACs dela não foram reconferidos nesta sessão |
| T-012 | Registry runtime e catálogo por ator | ✅ | — |
| T-013 | Validador de schema | ✅ | — |
| T-014 | Adapter de modelo e trace | ✅ | ampliado pelo ADR-0025 |
| T-015 | Motor de render e layout | ✅ | — |
| T-016 | TanStack Query, `viewId`, rotas | 🟡 | não há rota `/v/:viewId` no cliente |

## W2 — Furo de risco

| | Tarefa | Estado | O que falta |
|---|---|---|---|
| T-017 | SPIKE: medição com modelo real | 🟡 | medição feita e publicada no PRD §9; **falta o relatório R-001** e o commit das perguntas ANTES da execução — A-08 |

## W3 — Leitura · 7 de 15 componentes

| | Tarefa | Estado | Componentes |
|---|---|---|---|
| T-020 | Vencimento, indicador e curva | ✅ | `fila_vencimento` `estoque_indicador` `vencimento_grafico` |
| T-018 | Lote | ✅ | `lote_lista` `lote_detalhe` `lote_movimentos` `quarentena_fila` |
| T-019 | Produto e custo restrito | ⬜ | 2 |
| T-021 | Rastreabilidade `CA-01` | ⬜ | 1 |
| T-022 | Recebimento — leitura | ⬜ | 2 |
| T-023 | Cadeia fria `CA-07` | ⬜ | 2 |
| T-024 | Movimento e trilha | ⬜ | 2 |

## W4 — Escrita · pipeline pronto, comandos por fazer

| | Tarefa | Estado |
|---|---|---|
| T-025 | Pipeline de comando | ✅ |
| T-026 | Registrar recebimento | ⬜ |
| T-027 | Quarentena e status | ✅ |
| T-028 | Saída com FEFO | ✅ |
| T-029 | Estorno e descarte | ⬜ |
| T-030 | Dupla identificação `CA-04` | ⬜ |

> **O ADR-0002 deixou de ser promessa.** Até a T-025, *"a saída do modelo
> autoriza renderizar, nunca autoriza escrever"* não era falsificável: não havia
> escrita para o modelo deixar de autorizar. Agora há um caminho de escrita, e a
> barreira é verificada por três testes independentes — grafo de imports,
> ausência de callable em `CommandDef`, e bijeção declarado ↔ executável
> (`api/tests/commands/test_ac1_barreira.py`). Cada um foi confirmado vermelho
> com a violação introduzida de propósito.
>
> O que ainda falta da metade: os 7 comandos concretos, T-026 a T-030.

## W5 — Garantias

| | Tarefa | Estado | O que falta |
|---|---|---|---|
| T-032 | Suíte de avaliação | 🟡 | 17 casos dos ~40; roda os dois modos; sem série histórica |
| T-033 | Segurança CS-01 a CS-06 | 🟡 | CS-01/02/03 cobertos; **CS-04 e CS-06 não**; falta `R-003` |
| T-031 | Telas com rota | ⬜ | não há roteador no cliente |
| T-038 | Gestão de usuários | ⬜ | — |
| T-034 | Relatório de fechamento | ⬜ | — |

## Tarefas abertas pela auditoria

| | Tarefa | Estado | Origem |
|---|---|---|---|
| T-040 | CSRF e rate limit | ✅ | A-02, A-03 — **fechados** |
| T-041 | CI no GitHub Actions | ⬜ | A-07 |
| T-042 | Contract test fake ↔ repositório real | ⬜ | A-11 |
| T-043 | Instrumentação ao vivo do LangFuse | ⬜ | A-10 |
| T-044 | `relatorio_movimentacao` | ⬜ | ADR-0029 |

---

## Critérios de aceite do cliente

Um dos oito está completo. Os outros dependem de componentes ou de escrita que
ainda não existem — mas a escrita deixou de ser zero: T-025, T-027 e T-028 já
movem estoque, com auditoria e recusa negativa testadas.

| | Depende de | Estado |
|---|---|---|
| CA-01 recall < 60 s | T-021 | ⬜ |
| CA-02 saldo auditável | T-025, T-028, T-029 | 🟡 razão imutável, saída e liberação prontas, com trilha de valor anterior e novo; falta estorno (T-029) |
| CA-03 fila de vencimento | T-020 | ✅ **único completo** |
| CA-04 dupla identificação | T-030 | 🟡 **a metade que importa está pronta**: saída de controlado nasce `aguardando_autorizacao` e NÃO muda o saldo (T-028 AC-6). Falta o ato de autorizar |
| CA-05 custo invisível | T-019 | 🟡 provado no indicador e no catálogo; falta `produto_ficha` |
| CA-06 escopo de unidade | T-018 | 🟡 provado na fila e nos quatro de lote; falta cobrir os demais |
| CA-07 cadeia fria | T-023 | ⬜ |
| CA-08 excluir recusado | T-029 + banco | 🟡 banco recusa, e agora há movimento criado pela aplicação para provar contra (T-028 AC-7); falta o caminho de estorno |

## Requisitos de segurança

| | Estado |
|---|---|
| CS-01 schema forjado rejeitado | ✅ testado |
| CS-02 catálogo filtrado | ✅ testado |
| CS-03 negativa não revela existência | ✅ testado |
| CS-04 injeção via dado do banco | ⬜ **nunca testado** — é o de menor confiança |
| CS-05 resposta do assistente auditada | ✅ |
| CS-06 rate limit por ator | 🟡 login coberto (T-040); falta o endpoint do assistente |
