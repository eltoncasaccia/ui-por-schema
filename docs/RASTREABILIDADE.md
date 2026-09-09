# Matriz de Rastreabilidade — Ciclo 1

De onde cada exigência vem e onde ela é cumprida. Serve a três perguntas:

- *"Onde está implementado o `RN-C01`?"* → tabela 2
- *"Se eu mudar esta tarefa, o que quebra?"* → tabelas 1 e 3
- *"O que prova que `CA-04` funciona?"* → tabela 1, coluna de teste

---

## 1. Critérios de aceite do cliente

Os oito critérios do [documento 02 §9](./02-regras-de-negocio.md). **Todos dentro
do ciclo 1** — nenhum caiu com o corte do [ADR-0010](./adr/0010-corte-de-escopo-ciclo-1.md).

| CA | Origem no cliente | História | Tarefas | Teste que prova |
|---|---|---|---|---|
| **CA-01** | Recall da losartana, 9 dias | US-01 | [T-021](./tasks/T-021-rastreabilidade.md) · [T-006](./tasks/T-006-fixtures.md) · [T-010](./tasks/T-010-auditoria.md) | `T-021 AC-1` (< 60 s, com volume real) |
| **CA-02** | Divergência de 3,8% | US-02, US-05, US-07 | [T-002](./tasks/T-002-dominio-tipos-erros.md) · [T-007](./tasks/T-007-repositorios.md) · [T-025](./tasks/T-025-pipeline-de-comando.md) · [T-028](./tasks/T-028-saida-fefo.md) | `T-002 AC-1` (sem campo saldo) · `T-025 AC-5` |
| **CA-03** | R$ 183 mil vencidos | US-04 | [T-020](./tasks/T-020-vencimento-indicador.md) | `T-020 AC-1`, `AC-2` (fronteiras 89/90/91) |
| **CA-04** ✅ | Blister de clonazepam | US-06 | [T-028](./tasks/T-028-saida-fefo.md) · [T-030](./tasks/T-030-controlado-autorizar.md) · [T-024](./tasks/T-024-movimento-auditoria.md) | `T-030 AC-3` (mesma pessoa é recusada, em três camadas) |
| **CA-05** | Vazamento de margem | US-08 | [T-007](./tasks/T-007-repositorios.md) · [T-012](./tasks/T-012-catalogo.md) · [T-019](./tasks/T-019-componentes-produto.md) · [T-020](./tasks/T-020-vencimento-indicador.md) · [T-024](./tasks/T-024-movimento-auditoria.md) | `T-019 AC-4` (agregado derivado) · `T-024 AC-5` (trilha) |
| **CA-06** | Pedido do cliente | US-09 | [T-007](./tasks/T-007-repositorios.md) · [T-009](./tasks/T-009-motor-de-permissao.md) · [T-018](./tasks/T-018-componentes-lote.md) · [T-023](./tasks/T-023-temperatura.md) | `T-011 AC-7` (resposta byte a byte idêntica) |
| **CA-07** | Auto de infração da ANVISA | US-10 | [T-023](./tasks/T-023-temperatura.md) | `T-023 AC-3`, `AC-4` (vínculo por janela) |
| **CA-08** | `RN-M02` | US-07 | [T-029](./tasks/T-029-estorno-descarte.md) · [T-024](./tasks/T-024-movimento-auditoria.md) | `T-029 AC-1`, `AC-2` (Diretor recusado) |

---

## 2. Regras de negócio → tarefa

| Família | Regras | Onde é implementada |
|---|---|---|
| `RN-P` Produto | P01–P06 | [T-002](./tasks/T-002-dominio-tipos-erros.md) · [T-008](./tasks/T-008-regras-puras.md) · [T-019](./tasks/T-019-componentes-produto.md) · [T-026](./tasks/T-026-recebimento-registrar.md) |
| `RN-L` Lote e validade | L01–L08 | [T-008](./tasks/T-008-regras-puras.md) · [T-018](./tasks/T-018-componentes-lote.md) · [T-020](./tasks/T-020-vencimento-indicador.md) · [T-026](./tasks/T-026-recebimento-registrar.md) · [T-027](./tasks/T-027-quarentena-e-status.md) · [T-028](./tasks/T-028-saida-fefo.md) |
| `RN-R` Recebimento | R01–R05 | [T-022](./tasks/T-022-recebimento-leitura.md) · [T-026](./tasks/T-026-recebimento-registrar.md) · [T-027](./tasks/T-027-quarentena-e-status.md) **R02, R03 ✅** |
| `RN-M` Movimentação | M01–M06 | [T-002](./tasks/T-002-dominio-tipos-erros.md) · [T-007](./tasks/T-007-repositorios.md) · [T-008](./tasks/T-008-regras-puras.md) · [T-025](./tasks/T-025-pipeline-de-comando.md) **M04** · [T-028](./tasks/T-028-saida-fefo.md) · [T-029](./tasks/T-029-estorno-descarte.md) |
| `RN-C` Controlados | C01–C05 | [T-026](./tasks/T-026-recebimento-registrar.md) · [T-028](./tasks/T-028-saida-fefo.md) · [T-030](./tasks/T-030-controlado-autorizar.md) **C01 ✅, C05 imutável ✅** — **C02 e C04 fora** (dependem de ajuste e contagem, ADR-0010) |
| `RN-F` Cadeia fria | F01–F04 | [T-023](./tasks/T-023-temperatura.md) · [T-026](./tasks/T-026-recebimento-registrar.md) · [T-027](./tasks/T-027-quarentena-e-status.md) |
| `RN-I` Inventário | I01–I08 | **Fora do ciclo 1** — [ADR-0010](./adr/0010-corte-de-escopo-ciclo-1.md) |
| `RN-T` Transferência | T01–T05 | **Fora do ciclo 1** — ADR-0010 |
| `RN-A` Acesso | A01–A07 | [T-007](./tasks/T-007-repositorios.md) · [T-009](./tasks/T-009-motor-de-permissao.md) · [T-011](./tasks/T-011-servidor.md) · [T-012](./tasks/T-012-catalogo.md) · [T-025](./tasks/T-025-pipeline-de-comando.md) **A03 na escrita** — **A05 fora** (substituto do RT) |
| `RN-D` Auditoria | D01–D05 | [T-010](./tasks/T-010-auditoria.md) · [T-021](./tasks/T-021-rastreabilidade.md) · [T-024](./tasks/T-024-movimento-auditoria.md) · [T-025](./tasks/T-025-pipeline-de-comando.md) **D01, inclusive da tentativa recusada** |

---

## 3. Requisitos de segurança

Nascem da composição dinâmica; não existiam no documento 02.

| CS | Requisito | ADR | Implementado em | Verificado em |
|---|---|---|---|---|
| **CS-01** | Schema forjado rejeitado igual | [0004](./adr/0004-autorizacao-em-tres-momentos.md) | [T-011](./tasks/T-011-servidor.md) · [T-013](./tasks/T-013-validador-schema.md) | [T-033](./tasks/T-033-testes-de-seguranca.md) |
| **CS-02** | Catálogo filtrado antes do modelo | [0003](./adr/0003-catalogo-por-ator.md) | [T-012](./tasks/T-012-catalogo.md) · [T-019](./tasks/T-019-componentes-produto.md) | T-033 |
| **CS-03** | Negativa não revela existência | [0014](./adr/0014-erros-que-nao-vazam.md) | [T-009](./tasks/T-009-motor-de-permissao.md) · [T-011](./tasks/T-011-servidor.md) | T-033 |
| **CS-04** | Dado do banco não altera composição | [0012](./adr/0012-injecao-de-prompt-via-dado.md) | [T-014](./tasks/T-014-adapter-modelo.md) · [T-005](./tasks/T-005-arch-check.md) regra 6 | T-033 — **menor confiança** |
| **CS-05** | Resposta do assistente é auditada | — | [T-010](./tasks/T-010-auditoria.md) | T-033 |
| **CS-06** | Rate limit por ator | [0011](./adr/0011-teto-de-catalogo.md) | [T-011](./tasks/T-011-servidor.md) | T-033 |

---

## 4. Catálogo — 22 componentes

Teto de 25 por [ADR-0011](./adr/0011-teto-de-catalogo.md), verificado por `RNF-08`.

| # | Componente | `requires` | Tarefa |
|---|---|---|---|
| 1 | `lote_lista` | `lote.ler` | [T-018](./tasks/T-018-componentes-lote.md) |
| 2 | `lote_detalhe` | `lote.ler` | T-018 |
| 3 | `lote_movimentos` | `movimento.ler` | T-018 |
| 4 | `quarentena_fila` | `lote.ler` | T-018 |
| 5 | `produto_ficha` | `produto.ler` | [T-019](./tasks/T-019-componentes-produto.md) |
| 6 | `produto_saldo_por_unidade` | `lote.ler` | T-019 |
| 7 | `fila_vencimento` | `lote.ler` | [T-020](./tasks/T-020-vencimento-indicador.md) |
| 8 | `estoque_indicador` | varia por métrica | T-020 |
| 8b | `vencimento_grafico` | `lote.ler` | T-020 |
| 9 | `rastreabilidade` | `auditoria.rastrear` | [T-021](./tasks/T-021-rastreabilidade.md) |
| 10 | `recebimento_lista` | `recebimento.ler` | [T-022](./tasks/T-022-recebimento-leitura.md) |
| 11 | `recebimento_detalhe` | `recebimento.ler` | T-022 |
| 12 | `temperatura_historico` | `temperatura.ler` | [T-023](./tasks/T-023-temperatura.md) |
| 13 | `temperatura_excursoes` | `temperatura.ler` | T-023 |
| 14 | `movimento_lista` ✅ | `movimento.ler` | [T-024](./tasks/T-024-movimento-auditoria.md) |
| 15 | `auditoria_trilha` ✅ | `auditoria.ler` | T-024 |
| 17 | `recebimento_registrar` | `recebimento.criar` | [T-026](./tasks/T-026-recebimento-registrar.md) |
| 18 | `quarentena_liberar` ✅ | `lote.liberar` | [T-027](./tasks/T-027-quarentena-e-status.md) |
| 19 | `lote_status_acao` ✅ | `lote.status` | T-027 |
| 20 | `movimento_saida` ✅ | `movimento.criar` | [T-028](./tasks/T-028-saida-fefo.md) |
| 21 | `movimento_estorno` | `movimento.estornar` | [T-029](./tasks/T-029-estorno-descarte.md) |
| 22 | `movimento_descarte` | `movimento.descartar` | T-029 |
| 23 | `controlado_autorizar` ✅ | `controlado.autorizar` | [T-030](./tasks/T-030-controlado-autorizar.md) |

**Não são componentes de catálogo**, e a razão é a mesma nos dois: são decisões
do motor de render diante do que o servidor devolveu, nunca composição que o
modelo escolhe.

| | Por quê |
|---|---|
| `sem_acesso` | negativa é decisão do render ([T-015](./tasks/T-015-motor-de-render.md), ADR-0014) |
| `confirm_action` | confirmação é decisão do render diante de `CommandDef.confirm` (achado A-05, [T-025](./tasks/T-025-pipeline-de-comando.md)). Era o único componente sem `requires` próprio, contra CONTRATOS §5 |

A numeração acima pula o 16, que era o `confirm_action`. Renumerar apagaria o
rastro de uma decisão — e é o rastro que este documento existe para guardar.

---

## 5. Requisitos não funcionais

| RNF | Requisito | Verificado em |
|---|---|---|
| **RNF-01** | Recall < 60 s | [T-021](./tasks/T-021-rastreabilidade.md) `AC-1` |
| **RNF-02** | Conferência com leitor, uma mão | [T-026](./tasks/T-026-recebimento-registrar.md) `AC-8` |
| **RNF-04** | Tela de operação ≤ 2 s | [T-031](./tasks/T-031-telas-com-rota.md) `AC-3` |
| **RNF-06** | Temperatura retida 5 anos | [T-023](./tasks/T-023-temperatura.md) `AC-1` |
| **RNF-07** | p95 do assistente ≤ 3 s | [T-032](./tasks/T-032-suite-de-avaliacao.md) `AC-3` |
| **RNF-08** | Catálogo ≤ 25 | [T-012](./tasks/T-012-catalogo.md) `AC-4` · [T-030](./tasks/T-030-controlado-autorizar.md) |
| ~~RNF-03~~ | Off-line | **Fora** — [ADR-0015](./adr/0015-assistente-exige-conexao.md) |
| ~~RNF-05~~ | Implantação sem parar | **Fora** do ciclo 1 |

---

## 6. Cobertura de ADR

Todo ADR tem pelo menos uma tarefa que o verifica. ADR sem verificação é texto.

| ADR | Verificado em |
|---|---|
| [0001](./adr/0001-ui-por-schema.md) UI por schema | T-004 `AC-1` · T-013 |
| [0002](./adr/0002-plano-render-plano-escrita.md) Render × escrita | **T-025 `AC-1`** · T-005 regra 5 |
| [0003](./adr/0003-catalogo-por-ator.md) Catálogo por ator | T-012 `AC-1` · T-027 `AC-2` |
| [0004](./adr/0004-autorizacao-em-tres-momentos.md) Três momentos | T-011 `AC-2` · T-013 `AC-5` |
| [0005](./adr/0005-l2-leitura-l1-escrita.md) L2/L1 | T-003 `AC-3` · **T-031 `AC-1`** |
| [0006](./adr/0006-contrato-unico-de-componente.md) Contrato único | T-003 · T-012 `AC-7` |
| [0007](./adr/0007-camadas-e-arch-check.md) Camadas | **T-005** — as 9 regras |
| [0008](./adr/0008-tanstack-query.md) TanStack Query | T-016 `AC-1`, `AC-2`, `AC-3` |
| [0009](./adr/0009-identidade-de-view.md) Identidade de view | T-004 `AC-2` · **T-016 `AC-5`** |
| [0010](./adr/0010-corte-de-escopo-ciclo-1.md) Corte de escopo | T-012 — teste de escopo |
| [0011](./adr/0011-teto-de-catalogo.md) Teto de catálogo | T-012 `AC-4` |
| [0012](./adr/0012-injecao-de-prompt-via-dado.md) Injeção via dado | T-014 `AC-1` · T-033 CS-04 |
| [0013](./adr/0013-suite-de-avaliacao.md) Suíte de avaliação | T-032 `AC-4` |
| [0014](./adr/0014-erros-que-nao-vazam.md) Erros que não vazam | **T-011 `AC-7`** · T-009 `AC-5` |
| [0015](./adr/0015-assistente-exige-conexao.md) Exige conexão | T-014 — sem caminho off-line |

**Em negrito, o teste que mais importa para cada decisão.** Se algum deles quebrar,
a decisão correspondente deixou de valer — e nenhum outro teste vai perceber.
