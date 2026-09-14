# Progresso — checklist de execução

**A regra:** o status muda **no mesmo commit da entrega**, nunca depois. Um
critério de aceite não conferido **fica em branco** — marcar por otimismo é pior
que deixar vazio, porque cria evidência falsa.

Estado apurado pela [auditoria A-002](../relatorios/A-002-auditoria-de-execucao.md),
atualizado a cada entrega.

**39 concluídas · 2 parciais · 7 não iniciadas** · 23 de 24 componentes previstos.
**W0, W1, W2, W3 e W4 fechadas.** As duas parciais que restam são de W5 (T-032, T-033).

> Contagem apurada das tabelas abaixo, não da memória: o cabeçalho já divergia
> delas (dizia "2 parciais" com três linhas 🟡 na tabela). Para reconferir:
> `awk -F'|' '/^\| T-0[0-9][0-9] \|/ {print $4}' PROGRESSO.md | sort | uniq -c`.

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
| T-035 | Docker Compose, Makefile, README | ✅ | — |
| T-001 | Bootstrap `api/` e `web/` | ✅ | — |
| T-002 | Domínio: 7 tipos, erros, identidade | ✅ | — |
| T-003 | Contrato do registry | ✅ | — |
| T-004 | Schema, `viewKey`/`viewId`, envelope | ✅ | — |
| T-039 | Codegen do registry → TS + bijeção | ✅ | 6 ACs verificados negativamente |
| T-005 | Verificadores de arquitetura | ✅ | 12 regras nos dois lados, cada uma com violação de propósito |

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
| T-011 | Servidor FastAPI | ✅ | **8 ACs verificados por HTTP** contra o app real (`tests/server/`, 4 arquivos novos, 40 testes). AC-3/AC-4 vinham da T-025. **AC-6 exigiu implementar `CS-06`**, que não existia ([A-34](./ACHADOS.md)): teto por ator no endpoint do assistente, antes da chamada ao modelo. AC-8 no recorte "leitura de dado de domínio" ([A-35](./ACHADOS.md)). Cada proteção sabotada de propósito para provar que o teste quebra |
| T-012 | Registry runtime e catálogo por ator | ✅ | — |
| T-013 | Validador de schema | ✅ | — |
| T-014 | Adapter de modelo e trace | ✅ | ampliado pelo ADR-0025 |
| T-015 | Motor de render e layout | ✅ | — |
| T-016 | TanStack Query, `viewId`, rotas | ✅ | **7 ACs verificados.** Rota `/v/:viewId` em `web/src/app/rotas.tsx`, sem biblioteca de rota (única rota com parâmetro do ciclo 1; revisar na T-031). AC-2/AC-3 por comportamento — 4 blocos = 1 requisição, resposta atrasada não sobrescreve. AC-5/AC-6 no servidor ([A-36](./ACHADOS.md)): abrir view não devolve dado, e bloco fora do catálogo de quem abre some. Três sabotagens verificadas |

## W2 — Furo de risco

| | Tarefa | Estado | O que falta |
|---|---|---|---|
| T-017 | SPIKE: medição com modelo real | ✅ | R-001 entregue (2026-09-09): Sonnet 5 e Haiku 4.5, dois modos, 100% de schema válido; recomendação **seguir**. **AC-1 não recuperável** — as perguntas não foram pré-commitadas (17 casos da T-032); registrado em R-001 §8 e A-08b. Medição via OpenRouter, não Anthropic nativo (ADR-0025) |

## W3 — Leitura · 15 de 15 componentes

| | Tarefa | Estado | Componentes |
|---|---|---|---|
| T-020 | Vencimento, indicador e curva | ✅ | `fila_vencimento` `estoque_indicador` `vencimento_grafico` |
| T-018 | Lote | ✅ | `lote_lista` `lote_detalhe` `lote_movimentos` `quarentena_fila` |
| T-019 | Produto e custo restrito | ✅ | `produto_ficha` `produto_saldo_por_unidade` (AC-7 em branco — `RN-P06` sem armazenamento: [A-30](./ACHADOS.md), [T-046](./T-046-minimo-maximo-por-unidade.md)) |
| T-021 | Rastreabilidade `CA-01` | ✅ | `rastreabilidade` — AC-1..AC-7 testados. Recorte de período no `load` (porta ignora `de`/`ate`: [A-31](./ACHADOS.md)). `RNF-01` real fica para T-034 |
| T-022 | Recebimento — leitura | ✅ | `recebimento_lista` `recebimento_detalhe` — AC-2..AC-7 testados. **AC-1 em branco**: "gerou lote em quarentena" precisa de `lote.recebimento_id`, que não tem schema. **AC-6** vira `periodo` enum (a tarefa pedia `de`/`ate` soltos — risco R-5). RN-R03 sem armazenamento para integridade/validade: [A-33](./ACHADOS.md) |
| T-023 | Cadeia fria `CA-07` | ✅ | `temperatura_historico` `temperatura_excursoes` — AC-1..AC-6 testados. Agregação automática acima de 480 pontos; excursão detectada por corrida contígua fora de 2–8 °C; lote vinculado se entrou até o fim da excursão (AC-4, com par negativo). **Exportação (AC-2) é `csv` no viewmodel** — sem endpoint ([A-23](./ACHADOS.md)). `RNF-04` real fica para T-034 |
| T-024 | Movimento e trilha | ✅ | 2 |

## W4 — Escrita · fechada, sete comandos

| | Tarefa | Estado |
|---|---|---|
| T-025 | Pipeline de comando | ✅ |
| T-026 | Registrar recebimento | ✅ |
| T-027 | Quarentena e status | ✅ |
| T-028 | Saída com FEFO | ✅ |
| T-029 | Estorno e descarte | ✅ |
| T-030 | Dupla identificação `CA-04` | ✅ |

> **O ADR-0002 deixou de ser promessa.** Até a T-025, *"a saída do modelo
> autoriza renderizar, nunca autoriza escrever"* não era falsificável: não havia
> escrita para o modelo deixar de autorizar. Agora há um caminho de escrita, e a
> barreira é verificada por três testes independentes — grafo de imports,
> ausência de callable em `CommandDef`, e bijeção declarado ↔ executável
> (`api/tests/commands/test_ac1_barreira.py`). Cada um foi confirmado vermelho
> com a violação introduzida de propósito.
>
> **A W4 fechou com a T-029.** São sete comandos: liberar quarentena, mudar
> status, dar saída, autorizar controlado, registrar recebimento, **estornar** e
> **descartar**. Os oito ACs da T-029 verificados — AC-1 e AC-2 pela varredura do
> `openapi()` do app real e por HTTP com sessão de Diretor, AC-3 comparando a
> linha inteira do original antes e depois. Seis proteções sabotadas de
> propósito, seis testes vermelhos.
>
> **Limite conhecido, [A-38](./ACHADOS.md):** só **saída** se estorna. O sinal de
> `estorno` é fixo e positivo na view `saldo_lote` (migração 0001, congelada), e
> um estorno de entrada somaria de novo o que se queria desfazer — entrada errada
> não tem correção no ciclo 1.

## W5 — Garantias

| | Tarefa | Estado | O que falta |
|---|---|---|---|
| T-032 | Suíte de avaliação | 🟡 | 17 casos dos ~40; roda os dois modos; sem série histórica |
| T-033 | Segurança CS-01 a CS-06 | 🟡 | CS-01/02/03/05/06 cobertos — CS-01, CS-03 e CS-06 ganharam teste **de borda HTTP** na T-011; **CS-04 continua nunca testado** (o de menor confiança do release); falta `R-003` |
| T-031 | Telas com rota | ✅ | **6 ACs verificados, AC-3 em branco (medição é da T-034).** `react-router-dom` adotado — `app/layout/Roteador.tsx` autocontido (próprio `BrowserRouter`), 8 rotas em `app/layout/rotasOperacao.tsx` (tabela única: alimenta o roteador e a navegação lateral). AC-1 provado por igualdade de HTML entre a rota e `Composicao` direta. AC-4 verificado com catálogo mockado e contra o servidor real (Cleide sem `quarentena_liberar`, Helena com). AC-5 idem, incl. `curl` autenticado contra o container. `/saida` sem `:id` na URL mas `movimento_saida.produto_id` é obrigatório — sem componente de busca de produto no catálogo; resolvido com identificador digitado/colado + `?produto_id=`, ver nota no arquivo da tarefa. Tocou `App.tsx` e `PainelNavegacao.tsx` fora da lista original (justificado no arquivo da tarefa) |
| T-038 | Gestão de usuários | ⬜ | — |
| T-034 | Relatório de fechamento | ⬜ | — |

## Tarefas abertas pela auditoria

| | Tarefa | Estado | Origem |
|---|---|---|---|
| T-040 | CSRF e rate limit | ✅ | A-02, A-03 — **fechados** |
| T-041 | CI no GitHub Actions | ✅ | A-07 — com Postgres, e portão que reprova teste pulado |
| T-042 | Contract test fake ↔ repositório real | ⬜ | A-11 |
| T-043 | Instrumentação ao vivo do LangFuse | ⬜ | A-10 |
| T-044 | `relatorio_movimentacao` | ⬜ | ADR-0029 |
| T-045 | Borda HTTP por router | ✅ | ADR-0032 — `app.py` de 817 → 134 linhas; contrato 5 do import-linter, com teste negativo; 467 testes, mesma contagem |
| T-046 | Mín/máx por produto e unidade (`RN-P06`) | ⬜ | A-30 — sem armazenamento; é também tarefa de contrato (CONTRATOS §4) |
| T-048 | `RepoProduto.por_ean` (tarefa de contrato) | ✅ | A-37 — a `US-02` pede o leitor de código de barras e não havia busca por EAN em lugar nenhum. Porta + adaptador + fake + `UNIQUE (produto.ean)` na migração `0006`. Bateria única fake↔banco. **Destrava a T-026 (AC-8)**. CONTRATOS rev. 2.3 |
| T-047 | Repos de recebimento e temperatura | ✅ | A-32 — `RepoRecebimentoSQL`/`RepoTemperaturaSQL`, `deps.py` sem `None`, seed com 6 recebimentos, bateria de escopo fake↔real. Desbloqueou T-022 e T-023 |
| T-049 | Dispatcher de comando no cliente | ✅ | A-40 — `Bloco` ganha `comandos` (CONTRATOS §6/§8), view despacha `CustomEvent`, `render/motor.tsx` executa. Testado com mock (4 testes) e depois contra o servidor real por HTTP. `recebimento_registrar` grava de ponta a ponta; os outros 6 recusam por `If-Match` — ver T-050. AC-1 em branco na metade que depende do etag |
| T-050 | Etag na leitura | ✅ | A-41 (fatia simples) — `application/etag.py` (módulo neutro, contrato 2 intacto), `ComponentDef.etag`, `meta.etag` em `/dados`. `quarentena_liberar` e `lote_status_acao` completam de ponta a ponta contra o servidor real (Docker reconstruído, não só pytest); etag desatualizado devolve `conflito` e nada é aplicado. `movimento_saida` (etag por candidato) e `controlado_autorizar`/`movimento_estorno` (porta faltando) cortados para T-051 no levantamento |
| T-051 | Etag por linha | ✅ | A-41 (resto) — `controlado_autorizar` (bloc-level) e etag POR LINHA em `movimento_saida`/`movimento_descarte`/`movimento_estorno` (a pessoa escolhe o candidato depois de ler). Levantamento original errava: nenhum método novo de `RepoMovimento` foi preciso — o domínio `Movimento` já carrega tudo que o etag usa. Verificado por `curl` contra o container real (autorizar + saída) e pytest contra Postgres real (descarte + estorno), sempre com o par positivo/negativo. **T-031 destravada** |

---

## Critérios de aceite do cliente

Um dos oito está completo. Os outros dependem de componentes ou de escrita que
ainda não existem — mas a escrita deixou de ser zero: T-025, T-027 e T-028 já
movem estoque, com auditoria e recusa negativa testadas.

| | Depende de | Estado |
|---|---|---|
| CA-01 recall < 60 s | T-021 | 🟡 `rastreabilidade` entregue, duas direções, consulta auditada, escopo não atravessa. Prova de forma (`load` linear); o número real de `RNF-01` contra Postgres é do T-034 |
| CA-02 saldo auditável | T-025, T-028, T-029 | ✅ **completo**: razão imutável, saída, liberação e agora estorno — o saldo depois da correção é a soma dos dois movimentos, sem edição de campo (AC-4), e a trilha registra saldo anterior e posterior |
| CA-03 fila de vencimento | T-020 | ✅ **único completo** |
| CA-04 dupla identificação | T-030 | ✅ **completo**: submissão não muda saldo, autorização grava as duas identidades distintas, e a mesma pessoa é recusada em três camadas — permissão, domínio e CHECK do banco |
| CA-05 custo invisível | T-019 | ✅ `produto_ficha` entregue: chave de custo ausente para os 4 papéis sem `custo.ler` (não `null`), presente e só sob pedido para os 3 que podem, schema forjado recusado no servidor, exportação herda a omissão |
| CA-06 escopo de unidade | T-018 | 🟡 provado na fila e nos quatro de lote; falta cobrir os demais |
| CA-07 cadeia fria | T-023 | ✅ histórico consultável por período com faixa 2–8 °C e agregação no período longo; excursões com os lotes expostos (`RN-F04`, corte de presença testado nas duas direções); exportação `csv` no viewmodel. `RNF-04` (2 s) e `RNF-06` (5 anos no banco real) ficam para T-034 |
| CA-08 excluir recusado | T-029 + banco | ✅ **completo**: o banco recusa `UPDATE`/`DELETE` (T-036), **nenhuma rota responde a verbo que apague ou substitua** — varredura do `openapi()`, com uma rota `DELETE` acrescentada de propósito para provar que a varredura enxerga —, e o Diretor recebe a mesma recusa que qualquer papel, byte a byte. Corrigir se faz por estorno, que é `INSERT` |

## Requisitos de segurança

| | Estado |
|---|---|
| CS-01 schema forjado rejeitado | ✅ testado **pelo endpoint** (T-011 AC-2): componente fora do catálogo, valor de enum filtrado e unidade fora do escopo, cada um com o contraponto de quem pode |
| CS-02 catálogo filtrado | ✅ testado |
| CS-03 negativa não revela existência | ✅ testado **byte a byte na resposta HTTP** (T-011 AC-7), em `lote_detalhe` e `recebimento_detalhe`. Limite conhecido: canal lateral de **tempo** não é medido |
| CS-04 injeção via dado do banco | ⬜ **nunca testado** — é o de menor confiança |
| CS-05 resposta do assistente auditada | ✅ |
| CS-06 rate limit por ator | ✅ **o endpoint do assistente passou a ter teto** (T-011, achado [A-34](./ACHADOS.md)): 30 por ator e 120 por IP em 5 min, conferidos antes da chamada ao modelo, recusa auditada. O login já tinha o dele (T-040) — são duas proteções, e só uma existia |
