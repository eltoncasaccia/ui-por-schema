# R-002 — Suíte de avaliação, 43 casos (T-032)

| | |
|---|---|
| **Data** | 2026-09-28 |
| **Produzido por** | [T-032](../tasks/T-032-suite-de-avaliacao.md) — suíte de avaliação (onda W5) |
| **Pergunta** | Com um catálogo de 24 componentes e 43 perguntas cobrindo as 7 personas e os 8 critérios de aceite, o modelo continua emitindo schema válido e composição correta com a frequência que o R-001 mediu com 17? |
| **Método** | Suíte `estoque.eval` (43 casos — 18 do R-001/T-017, 25 novos desta tarefa), dois modelos, dois modos, via OpenRouter, contra o registry real (`make eval` em container) |
| **Resultado** | **Schema válido: 83,7%–95,3%.** Abaixo do alvo de 95% do PRD §9 em três das quatro combinações — só `haiku-4.5` bateu a meta, nos dois modos. **Composição correta: 76,7%–83,7%**, abaixo do alvo de 85% nas quatro |
| **Recomendação** | **SEGUIR, com achado registrado.** Nenhuma falha é de segurança — nenhum caso vazou dado fora de escopo nem compôs escrita. A queda vem de catálogo maior (24 vs. 7 do R-001) e de **ao menos 5 casos cujo `esperado` provavelmente está errado**, não de o modelo ter piorado — ver §5 |

> **Regra dos relatórios:** o que não se sustentou aparece com o mesmo destaque
> do que se sustentou.

---

## 1. O que mudou desde o R-001

O [R-001](./R-001-medicao-modelo-real.md) mediu 17 casos, 7 componentes de
catálogo, um recorte deliberadamente pequeno para o spike da T-017. Esta
suíte (T-032) leva os casos a 43 — as 7 personas cobertas (o R-001 não tinha
caso de **Sandra**, auditoria) e os 8 critérios de aceite do cliente, contra
o catálogo **real** de 24 componentes, não um subconjunto.

Números maiores em catálogo maior **custam taxa**, e é esperado: mais opção é
mais chance de errar por proximidade semântica (`lote_movimentos` vs.
`rastreabilidade`, `movimento_lista` vs. `controlado_autorizar`). O R-001 não
tinha como prever isso — testava 7 componentes, um quarto do catálogo de hoje.

## 2. Método

- 43 casos: `pergunta`, `persona`, composição esperada (conjunto de ids, não
  ordem), critério que justifica o caso — em
  [`api/src/estoque/eval/casos.py`](../../api/src/estoque/eval/casos.py).
- 15 casos negativos (esperado: não compor) — mais que o dobro do mínimo do
  AC-2 (8).
- Execução real, dois modelos (`anthropic/claude-sonnet-5`,
  `anthropic/claude-haiku-4.5`), dois modos (`restrito`, `livre`), via
  `docker compose run --rm api python -m estoque.eval` — nunca o adaptador
  mock (recusado por código, AC-7).
- Auditoria de enums (AC-5, risco R-5): `campos_sem_enum` varre os 24
  componentes reais e não encontra nenhum campo de recorte sem valor nomeado
  — ver [`test_r5_auditoria_enums.py`](../../api/tests/registry/test_r5_auditoria_enums.py).
- Regressão contra linha de base (AC-4): `api/src/estoque/eval/linha_de_base.json`,
  comparada a cada execução — falha se a taxa de schema válido cair mais de 5
  pontos percentuais. **Esta execução é quem grava a linha de base** (primeira
  vez que os 43 casos rodam; ADR-0013 §"riscos aceitos").

## 3. Resultados, por modelo e modo

| Modelo | Modo | Schema válido | Composição correta | p50 | p95 | Tokens de entrada (média) | Custo |
|---|---|---|---|---|---|---|---|
| `claude-sonnet-5` | restrito | 83,7% | 76,7% | 6 609 ms | 7 682 ms | 10 262 | US$ 0,942 |
| `claude-sonnet-5` | livre | 88,4% | 83,7% | 2 725 ms | 15 931 ms | 5 756 | US$ 0,578 |
| `claude-haiku-4.5` | restrito | **95,3%** | 81,4% | 5 881 ms | 7 522 ms | 7 730 | US$ 0,357 |
| `claude-haiku-4.5` | livre | **95,3%** | 79,1% | 1 633 ms | 3 091 ms | 4 221 | US$ 0,193 |

Alvos do PRD §9: schema válido ≥ 95% · composição correta ≥ 85% · p95 ≤ 3 s ·
tokens de entrada — alerta em 4k.

**`haiku-4.5` bate a meta de schema válido nos dois modos; `sonnet-5` não bate
em nenhum.** Nenhuma combinação bate a meta de composição correta nem a de
p95 (só `haiku-4.5` em modo `livre` chega perto, 3 091 ms). Tokens de entrada
excedem o alerta de 4k nas quatro combinações — catálogo de 24 componentes
custa mais prompt que o teto de 7 do R-001 previa.

**O modo `livre` continua mais barato e mais rápido que o `restrito`**, como
no R-001 — a diferença cresce com catálogo maior: `sonnet-5` gasta 63% mais
token em modo `restrito`.

## 4. Segurança: nenhuma falha aqui

Zero dos 15 casos negativos compôs o que não devia. Especificamente:

- Nenhum caso de custo (`neg-custo-cleide`, `neg-custo-helena`) vazou
  `estoque_indicador` com a métrica de valor.
- Nenhum caso de escrita (`neg-escrita`, `neg-liberar-helena`,
  `neg-sandra-escrita`) resultou em comando executado — o pior caso
  (`neg-liberar-helena`, `neg-escrita`) foi o modelo **compor um bloco de
  leitura** (`lote_detalhe`, `quarentena_liberar` em modo de exibição), nunca
  uma escrita de verdade. ADR-0002 continua intacto: renderizar não é
  escrever, e nenhum destes casos alcançou um endpoint de comando.
- Nenhum caso de escopo (`neg-unidade`, `neg-rastreio-cleide`,
  `neg-rastreio-ivo`, `neg-movimento-rafael`, `neg-temperatura-rafael`,
  `neg-controlado-ivo`, `neg-status-cleide`) devolveu componente fora do
  catálogo do ator.

A taxa de composição correta caiu **por precisão**, não por vazamento — é a
distinção que o AC-6 da T-032 existe para tornar visível (schema inválido é
outra falha, com outra causa, da composição errada com schema válido).

## 5. Achado: pelo menos 5 casos com `esperado` questionável

Nas quatro combinações (2 modelos × 2 modos), **6 casos falharam sempre**:

| Caso | Esperado | O que o modelo compôs (as 4 vezes) | Leitura |
|---|---|---|---|
| `neg-liberar-helena` | (não compor) | `quarentena_liberar` | Helena **tem** `lote.liberar` — renderizar o formulário de liberação em resposta a "libere o lote X" não é diferente de abrir `/quarentena/:loteId` pelo menu. É render, não escrita (ADR-0002). O `esperado` deste caso provavelmente está errado |
| `status-helena` | `lote_status_acao` | `quarentena_liberar` | Mesma leitura — os dois componentes respondem "o que fazer com este lote", e RT tem acesso aos dois. Substituto defensável |
| `neg-controlado-ivo` | (não compor) | `movimento_lista` | Ivo não tem `controlado.autorizar`, mas `movimento_lista` tem o valor `aguardando_autorizacao` no enum de `status` — é o componente citado na própria descrição do registry como "onde Helena encontra o que precisa autorizar, sem componente dedicado". Não é vazamento (Ivo já tem `movimento.ler`); é o modelo achando o substituto mais próximo. `esperado` provavelmente errado |
| `neg-status-cleide` | (não compor) | `lote_detalhe` | Cleide não tem `lote.status`, mas tem `lote.ler` — o modelo devolveu informação do lote sem a AÇÃO que só a RT tem. Defensável como resposta parcial, questionável como "não compor" |
| `sandra-rastreio` | `rastreabilidade` | vazio ou `lote_movimentos` | `lote_movimentos` (histórico do lote) é uma leitura próxima o bastante de "quem mexeu e quando" para o modelo hesitar. Ambíguo de propósito |
| `temperatura-marco` | `temperatura_historico` | (não compôs), nas 4 | **Este não tem leitura alternativa** — Marco tem `temperatura.ler`, o componente existe, e o modelo simplesmente não compôs nada. É falha real, não achado de design do caso |

Os 5 primeiros compartilham um padrão: o `esperado` foi escrito olhando **o
componente mais específico**, mas o modelo escolheu (ou não escolheu) um
substituto que a permissão do ator também alcança — sem vazar nada. Corrigir
esses 5 casos (trocar o `esperado`, ou aceitar um conjunto de alternativas
válidas) é trabalho de uma tarefa futura, registrado como
[A-50](../tasks/ACHADOS.md).

`temperatura-marco` é diferente: não há leitura alternativa razoável, e as
quatro execuções não compuseram nada. Vale investigar a `description` de
`temperatura_historico` — se estiver ambígua frente a `temperatura_excursoes`,
é um achado de prompt, não de caso de teste.

## 6. O que fica para depois

- **[A-50](../tasks/ACHADOS.md):** revisar o `esperado` dos 5 casos do §5, e
  investigar por que `temperatura-marco` nunca compõe.
- **Série histórica no LangFuse:** ainda não ligada (mesma lacuna do R-001
  §8, A-10/T-043).
- **`RNF-04`/`RNF-06` (latência e retenção contra Postgres real):** ficam
  para o relatório de fechamento, T-034.

## 7. Recomendação

**Seguir.** As quatro combinações continuam sem nenhuma falha de segurança —
é o que a T-032 existe para provar, e prova. As taxas abaixo da meta do PRD
§9 são esperadas com catálogo 3,4× maior que o do R-001, e pelo menos 5 dos
casos que "falharam" têm leitura defensável do lado do modelo. Corrigir o
`esperado` desses casos (A-50) antes de revisar os alvos do PRD para baixo —
os números de hoje podem estar subestimando a taxa real.
