# R-001 — Medição com modelo real (spike T-017)

| | |
|---|---|
| **Data** | 2026-09-09 |
| **Produzido por** | [T-017](../tasks/T-017-spike-medicao.md) — SPIKE de furo de risco (onda W2) |
| **Pergunta** | Um modelo real emite schema válido com que frequência? ([PRD §9](../prd/PRD-001-ciclo-1.md), risco R-1) |
| **Método** | Suíte `estoque.eval` (17 casos, 7 personas), dois modelos, dois modos, via OpenRouter |
| **Resultado** | **Schema válido: 100% nas quatro combinações.** Composição correta: 100%, exceto Haiku 4.5 em modo restrito (94,1% — 1 falha, transcrita em §5) |
| **Recomendação** | **SEGUIR.** W3 está liberada. Ajuste recomendado, não bloqueante: modo `livre` como padrão — ver §7 |

> **Regra dos relatórios:** o que não se sustentou aparece com o mesmo destaque
> do que se sustentou. As lacunas do próprio spike estão em §8, não em rodapé.

---

## 1. A pergunta que este spike existe para responder

A POC v1 publicou quatro números vindos de um parser simulado sem ninguém
perceber ([documento 00](../00-achados-v1.md)). O ciclo 2 não pode repetir isso:
antes de escrever 15 componentes de leitura (W3) e 7 de escrita (W4), é preciso
saber se a hipótese central se sustenta —

> **um modelo de linguagem real, dado o catálogo filtrado por ator, devolve um
> schema que passa na validação do servidor?** E com que frequência?

A [regra de liberação da T-017](../tasks/T-017-spike-medicao.md): se a taxa de
schema válido ficar **abaixo de 80%**, a W3 não abre — abre-se antes uma tarefa
de ajuste de prompt e de descrições, e o spike é reexecutado.

---

## 2. O que foi medido — e o que este spike **não** fez

Este relatório é honesto sobre a distância entre o que a T-017 desenhou e o que
foi executado. A medição aconteceu; o spike, na forma prevista, não.

| A T-017 previa | O que aconteceu |
|---|---|
| 6 componentes **mínimos** em `api/src/estoque/spike/`, descartáveis | Medição feita contra o **registry real** (13 componentes registrados, filtrados por ator). Mais fiel à produção; `api/src/estoque/spike/` nunca existiu, e o AC-6 (removê-lo) é vacuamente verdadeiro |
| **30 perguntas**, escritas e commitadas **antes** da primeira execução (AC-1) | **17 casos** da suíte `estoque.eval` ([`casos.py`](../../api/src/estoque/eval/casos.py)), escritos ao longo do desenvolvimento da T-032. **Não há prova no histórico do git de que não foram ajustados aos resultados** — é a proteção que o AC-1 daria, e que continua ausente (achado [A-08b](../tasks/ACHADOS.md)) |
| Execução com `ANTHROPIC_API_KEY` presente, adapter nativo (AC-2) | Via **OpenRouter** (`anthropic/claude-sonnet-5`, `anthropic/claude-haiku-4.5`). O [ADR-0025](../adr/0025-agnosticismo-de-provedor.md) e [CONTRATOS 2.1](../tasks/CONTRATOS.md) tornaram o provedor **configuração**; o ambiente só tem `OPENROUTER_API_KEY`. O texto do AC-2 precede o ADR-0025 e está superado por ele (hierarquia `RN > ADR > tarefa`) |
| Relatório `R-001` com os quatro números do PRD §9, por modelo (AC-3) | Este documento, §4 |
| As falhas transcritas, com a razão (AC-4) | §5 — uma falha, transcrita |
| Recomendação: seguir / ajustar / rever (AC-5) | §7 — **seguir**, com o número que sustenta |

**Cobertura das personas:** os 17 casos exercitam as 7 — Marco (diretor), Helena
(RT), Ivo e Odair (gerentes de escopos distintos), Cleide (conferente), Rafael
(comprador), Sandra (auditoria) — nos eixos leitura direta, gráfico-vs-número e
negativos (o certo é **não** compor). Dos 6 componentes que a T-017 nomeava, 5 já
existem no registry; `produto_ficha` ainda não ([T-019](../tasks/T-019-componentes-produto.md) não iniciada).

---

## 3. Método

- **Arnês:** `docker compose run --rm api python -m estoque.eval --modo restrito --modo livre`
- **Adapter:** `AdaptadorOpenRouter` real. A suíte **recusa rodar com o mock**
  (`estoque.eval` aborta se `type(adaptador).__name__ == "AdaptadorMock"`) — a
  trava que a v1 não tinha.
- **Configuração da execução** (sobrescrita do `.env`, que aponta para um Ollama
  local `qwen2.5:7b`):
  `PROVEDOR=openrouter`, `LLM_BASE_URL=https://openrouter.ai/api/v1/chat/completions`,
  `MODELO_ASSISTENTE=anthropic/claude-sonnet-5` / `anthropic/claude-haiku-4.5`.
- **Parâmetros:** `temperature=0`, `max_tokens=1024`, sem streaming.
- **Modo `restrito`:** `response_format: json_schema` estrito, derivado do
  catálogo do ator ([ADR-0024](../adr/0024-decodificacao-restrita.md)). Fallback
  `restrito → ferramenta → livre` se o provedor recusar o envelope — não houve
  fallback nesta execução.
- **Modo `livre`:** sem `response_format`; o modelo devolve texto e a extração
  do JSON é tolerante a cerca de código. É a pergunta original da v1.
- **Schema válido** = o objeto devolvido passa em `validar_schema` contra o
  catálogo do ator. Composição vazia conta como válida — é a resposta certa para
  pergunta fora do catálogo.
- **Composição correta** = o conjunto de `tipo` compostos é **igual** ao
  esperado do caso. Para caso negativo, correto é o conjunto vazio.
- **Métricas de tempo:** sem streaming no ciclo 1, `ms_até_primeiro_token` é
  igual ao `ms_total`. O número medido é **tempo de resposta completo**, não
  time-to-first-token — ver a ressalva em §6.
- **Telemetria:** o LangFuse retornou `401 Unauthorized` nas duas execuções
  (achado [A-10](../tasks/ACHADOS.md), tarefa T-043 no [BOARD](../tasks/BOARD.md)).
  As métricas abaixo vêm do JSON local (`EVAL_SAIDA`), não do painel.

---

## 4. Resultados, por modelo

**17 casos por célula. Os quatro números do PRD §9.**

### Claude Sonnet 5 (`anthropic/claude-sonnet-5`)

| | schema válido | composição correta | p50 | p95 | tokens de entrada (médio) | custo (17 casos) |
|---|---|---|---|---|---|---|
| **restrito** | **100%** | **100%** | 4,1 s | 8,1 s | 5 421 | US$ 0,196 |
| **livre** | **100%** | **100%** | 2,9 s | 7,2 s | 2 694 | US$ 0,102 |

### Claude Haiku 4.5 (`anthropic/claude-haiku-4.5`)

| | schema válido | composição correta | p50 | p95 | tokens de entrada (médio) | custo (17 casos) |
|---|---|---|---|---|---|---|
| **restrito** | **100%** | **94,1%** (16/17) | 1,8 s | 4,7–6,1 s | 4 414 | US$ 0,079 |
| **livre** | **100%** | **100%** | 1,5 s | 2,0 s | 2 006 | US$ 0,038 |

> p95 do Haiku restrito variou entre duas execuções (4,7 s e 6,1 s); o p50
> (~1,8 s) e o custo (idêntico ao centavo, `temperature=0`) não variaram. A
> latência é ruidosa; o ponto não.

**Comparação com a primeira medição (PRD §9 — Haiku 4.5 via OpenRouter, 17
casos):** aquela tabela dava 100%/100% nos dois modos, com 2 078 / 962 tokens de
entrada. Os tokens subiram (4 414 / 2 006) porque o catálogo cresceu de 3 para 13
componentes desde então — cada componente adiciona `description` + `examples` ao
prompt. **Esta tabela substitui a provisória do PRD §9.**

---

## 5. A falha (AC-4)

Uma única falha em 68 execuções (17 casos × 2 modos × 2 modelos). **Schema
válido; composição errada.** Nenhum schema foi rejeitado.

| Caso | `neg-escrita` |
|---|---|
| **Persona** | Cleide (conferente) |
| **Pergunta** | *"libere o lote L-8842 da quarentena"* |
| **Esperado** | **não compor** — [ADR-0002](../adr/0002-plano-render-plano-escrita.md): o modelo nunca autoriza escrita |
| **Sonnet 5** | correto nos dois modos (não compôs) |
| **Haiku 4.5 · livre** | correto (não compôs) |
| **Haiku 4.5 · restrito** | **compôs `lote_detalhe`** |

**Leitura.** Pedido de escrita ("libere o lote"), o Haiku em modo restrito não
reconheceu como fora do escopo de composição e respondeu com o componente de
leitura mais próximo. O schema estrito permite `blocos: []`, mas a decodificação
restrita parece enviesar o modelo fraco a **preencher** o array. Em modo livre o
mesmo modelo recusou.

**Isto não é brecha de segurança.** `lote_detalhe` é leitura; nenhuma escrita
acontece. A barreira do [ADR-0002](../adr/0002-plano-render-plano-escrita.md) é a
autorização no servidor a cada `load`, não a composição do modelo — e ela não foi
tocada. É uma **degradação de comportamento** no exato caso que trata da
fronteira leitura/escrita, e é o tipo de regressão silenciosa que a suíte de
avaliação existe para pegar.

---

## 6. Leitura dos números

1. **A pergunta central está respondida: 100% de schema válido, nas quatro
   combinações.** Zero rejeição de schema em 68 execuções. O risco R-1 do PRD
   ("modelo emite schema válido com frequência baixa demais") **não se
   materializou**, com folga sobre o gatilho de 80% e sobre o alvo ≥ 95% do PRD.

2. **Decodificação restrita mais que dobra os tokens de entrada.** Sonnet
   2 694 → 5 421; Haiku 2 006 → 4 414. O JSON Schema do catálogo viaja em toda
   pergunta. Confirma o achado do PRD §9, agora com catálogo de 13.

3. **Restrito custa mais, demora mais e — no modelo fraco — erra mais.** É o
   único cenário com falha de composição (§5), tem o p95 mais alto do Haiku, e
   dobra o custo. Não comprou precisão que o modo livre já não tivesse.

4. **Modo restrito estoura o teto de alerta de tokens de entrada do PRD §9
   (4 000).** Sonnet 5 421, Haiku 4 414. Modo livre fica abaixo nos dois
   (2 694 / 2 006).

5. **Latência: o alvo p95 ≤ 3 s do PRD ainda não é comparável.** O PRD mede
   "tempo até o primeiro componente", que pressupõe streaming; o ciclo 1 não tem
   streaming, então o número aqui é tempo de resposta **completo**. Só Haiku
   livre (p95 2,0 s) passaria mesmo assim. Medir o alvo de verdade depende de
   streaming — fora do escopo do ciclo 1.

6. **Custo é baixo em termos absolutos.** A pior célula (Sonnet restrito) é
   US$ 0,196 por 17 perguntas ≈ US$ 0,012/pergunta. A suíte inteira desta
   medição (4 células + diagnóstico) custou cerca de US$ 0,45.

---

## 7. Recomendação (AC-5)

**SEGUIR. A W3 está liberada.**

O número que sustenta: **100% de schema válido em 68 execuções, com zero
rejeição**, nos dois modelos e nos dois modos. A hipótese sobre a qual os 22
componentes seriam escritos se sustenta.

**Ajuste recomendado, não bloqueante — `livre` como modo padrão:**

| | restrito | livre |
|---|---|---|
| schema válido | 100% | 100% |
| composição correta | 100% Sonnet / 94,1% Haiku | 100% ambos |
| tokens de entrada | dobro; estoura o teto de 4k | abaixo do teto |
| custo | ~2× | 1× |
| latência p95 | maior | menor |

Nesta medição, `restrito` só **custou** — mais tokens, mais latência, e a única
falha do estudo. O caso a favor dele (garantia estrutural contra schema inválido)
não apareceu, porque o `livre` também não produziu schema inválido nenhum. A
decisão final de modo e de modelo de produção é da [T-032](../tasks/T-032-suite-de-avaliacao.md),
com a suíte de 40 casos e a série histórica; este spike recomenda a direção.

---

## 8. O que este relatório **não** entrega

- **AC-1 não cumprido.** As perguntas não foram escritas nem commitadas antes da
  primeira execução. São os 17 casos da T-032, escritos junto com o
  desenvolvimento. O "100% bom demais" que a [auditoria A-002](A-002-auditoria-de-execucao.md)
  apontou segue **sem a proteção** que o AC-1 daria — só que agora com dois
  modelos e 68 execuções, o que reduz (não elimina) a suspeita de ajuste.
- **17 casos, não 30.** Menos da metade do volume previsto.
- **`api/src/estoque/spike/` nunca foi construído.** A medição usou o registry
  real. Mais fiel, mas fora da letra da T-017.
- **Sem Anthropic nativo.** Via OpenRouter (superado pelo ADR-0025, mas registrado).
- **Sem série histórica no LangFuse.** Telemetria com `401` nas duas execuções
  (A-10 / T-043). Números vindos do JSON local.
- **Latência do alvo do PRD não medida** — depende de streaming.

O caminho para fechar o que falta: a [T-032](../tasks/T-032-suite-de-avaliacao.md)
leva os casos a ~40 e liga a série histórica; a T-043 (no [BOARD](../tasks/BOARD.md))
conserta a telemetria. A disciplina do AC-1 (perguntas antes do resultado) só
pode ser recuperada para os casos **novos** que a T-032 acrescentar — commit
separado e anterior.

---

### Erratum (2026-09-28, [T-056](../tasks/T-056-erratum-r-001.md))

As duas frases acima — *"as perguntas não foram escritas nem commitadas antes
da primeira execução"* e *"`spike/` nunca foi construído"* — **descrevem a
rodada publicada, não a única rodada que existiu.** Ficam como estão, porque
relatório é registro: o erratum corrige o que se pode **afirmar**, não apaga o
que foi dito.

Existiu uma segunda rodada, anterior e abandonada sem publicação, fora da
`main`: commit `e753200` (branch `tarefa/T-017`, autor e committer em
**2026-09-08 12:15:48 -03**, sem sinal de reescrita — confira com
`git show -s --format='%ci %ci' e753200`). Recuperada em 2026-09-25
([A-47](../tasks/ACHADOS.md)) para `docs/relatorios/R-001-perguntas.json` (30
perguntas) e `R-001-dados-brutos.json` (120 execuções). **Não é a rodada dos
números do §4**: usou `sonnet-4.6` + `haiku-4.5`, dois modos, 30 perguntas e
120 execuções — 100% de schema válido, 96,7% de composição correta. A
publicada usou `sonnet-5` + `haiku-4.5`, 17 casos e 68 execuções.

**O [A-08b](../tasks/ACHADOS.md) não fecha.** A rodada recuperada cumpriu a
disciplina do AC-1; a rodada **publicada** — a que sustenta o "seguir" do §7 e
o número que o PRD §9 cita — não. Fechar o achado transferiria para os
resultados publicados uma garantia que eles não têm. O texto correto não é
"não recuperável": é "recuperável, mas não vale para a rodada publicada".

Com a data verificável pelo comando acima, `tarefa/T-017` deixou de ser a
única prova e pode ser apagada sem perder evidência.
