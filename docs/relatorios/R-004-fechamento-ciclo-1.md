# R-004 — Fechamento do ciclo 1 (T-034)

| | |
|---|---|
| **Data** | 2026-09-28 |
| **Produzido por** | [T-034](../tasks/T-034-fechamento.md) — relatório de fechamento (onda W5, última tarefa do ciclo) |
| **Pergunta central** | Um modelo real emite schema válido com que frequência, e o ciclo está pronto pra alguém confiar nele? |
| **Resposta** | Schema válido: 83,7%–95,3% conforme o modelo. Nenhuma combinação vazou dado nem compôs escrita. O ciclo está funcionalmente pronto — 6/8 critérios de aceite do cliente completos (2 parciais), 6/6 requisitos de segurança — mas **não bate as quatro metas do PRD §9 simultaneamente com nenhum dos dois modelos** |
| **Recomendação** | **Fechar o ciclo 1 como está, com `haiku-4.5` em produção** (bate schema válido nos dois modos; `sonnet-5` não bate em nenhum). Ciclo 2 entra com 5 perguntas pendentes do cliente como critério de **entrada**, não de saída |

> **Regra deste relatório, herdada do [documento 00](../00-achados-v1.md):** o
> que não se sustentou aparece com o mesmo destaque do que se sustentou. Se a
> seção 4 estivesse vazia, este documento não teria sido escrito com
> honestidade.

---

## 1. Checklist de release do PRD §11

| Item | Estado | Evidência |
|---|---|---|
| CA-01 a CA-08 passam como teste automatizado | 🟡 **6/8 completos, 2 parciais** | [PROGRESSO §"Critérios de aceite do cliente"](../tasks/PROGRESSO.md); CA-01 fechado nesta tarefa (§2); CA-06 ainda só provado em 5 das telas |
| CS-01 a CS-06 passam, ou CS-04 tem achado documentado | ✅ **6/6**, incluindo CS-04 | [R-003](./R-003-seguranca-ciclo-1.md) — CS-04 passou com `qwen2.5:7b` real; achado A-42 (`titulo` sem teto) é sobre um efeito colateral, não sobre CS-04 em si |
| RF-01 a RF-20 implementados e rastreados | ✅ pelas famílias de regra que os sustentam | [RASTREABILIDADE §2](../RASTREABILIDADE.md) mapeia cada família `RN-*` (não RF-* diretamente) à tarefa que implementa. As famílias fora do ciclo — `RN-I` (inventário) e `RN-T` (transferência), inteiras, por [ADR-0010](../adr/0010-corte-de-escopo-ciclo-1.md); `RN-C02`/`RN-C04` e `RN-A05`, mesmo motivo — não correspondem a nenhum RF-01–20: nenhum dos vinte descreve inventário ou transferência. Não conferido RF a RF nesta tarefa, um a um |
| As quatro métricas da seção 9 medidas com os dois modelos | ✅ | [R-002](./R-002-avaliacao-ciclo-1.md) — ver §3 abaixo |
| `make arch` verde, com as regras testadas negativamente | ✅ | `make check` — 7 contratos de import-linter, 6 regras de `arch-check.ts`, ambos com teste negativo (sabotagem) |
| Catálogo com 23 componentes; teste de orçamento verde | 🟡 **24, não 23** | Cresceu um desde o PRD (`vencimento_grafico` foi acrescentado depois). Continua dentro do teto de 25 ([ADR-0011](../adr/0011-teto-de-catalogo.md)), testado (`RNF-08`). O número do PRD ficou desatualizado, não o sistema |
| Suíte de avaliação executando em CI a cada mudança de catálogo/prompt | ❌ **não implementado** | Ver §4 — é o item que menos se sustentou |
| Relatório de fechamento (T-034) escrito, incluindo o que não se sustentou | ✅ | Este documento |

**5 de 8 verdes, 2 parciais, 1 vermelho.** O ciclo não fecha "todos verdes" como
o PRD pedia — fecha com os dois itens não-verdes registrados, não escondidos.

---

## 2. RNF-01 e RNF-04: os números reais que faltavam

Dois números tinham prova só de **forma** (testes contra fakes, lineares, sem
medir tempo de verdade) e ficaram para esta tarefa de propósito — ver
`test_rastreabilidade.py`: *"RNF-01 real ... é medido no relatório de
fechamento, T-034."*

### RNF-01 — recall < 60 s

Medido contra o Postgres do ambiente de desenvolvimento (`make up`), autenticado
como Marco (diretor), pelo endpoint real (`POST /api/componentes/rastreabilidade/dados`),
não por chamada direta à função:

| Lote | Saídas | Unidades | Clientes atingidos | Tempo (5 medições) |
|---|---|---|---|---|
| `l-los-a1-mat` (Losartana — o mesmo produto do recall que originou o CA-01) | 60 | 449 | 60 | 10–20 ms |

**10–20 ms contra um alvo de 60 s** — três ordens de grandeza de folga. O banco
de desenvolvimento tem 269 movimentos no total; não é o volume de produção,
mas é volume real, não fixture. Combinado com a prova de forma já existente
(`load` é `O(n)` no número de movimentos do lote, testado com fixture maior),
a folga é grande o bastante para não depender de otimização futura.

### RNF-04 — tela de operação ≤ 2 s

Medido nos mesmos moldes, servidor real, 5 das 8 telas de rota — as que têm
leitura simples (`GET` de dados). As outras 3 (`recebimento_registrar`,
`quarentena_liberar`, `movimento_saida`) são formulário de escrita, com outro
padrão de carga, e ficaram de fora desta rodada:

| Componente | Rota | Tempo (3 medições) |
|---|---|---|
| `lote_lista` | `/lotes` | 10–30 ms |
| `fila_vencimento` | `/vencimento` | 10–20 ms |
| `quarentena_fila` | `/quarentena` | 10–20 ms |
| `controlado_autorizar` | `/controlados` | 10–50 ms |
| `lote_detalhe` | `/lotes/:id` | 10–20 ms |

**Escopo desta medição: resposta do servidor, não pintura completa no
navegador.** Não inclui o tempo de React montando a tela nem o round trip de
rede de um cliente real fora do `localhost` — isso soma algumas dezenas de ms
num ambiente normal, não segundos. Não é o número final de produção; é prova
suficiente de que a folga é grande.

### RNF-06 — temperatura retida 5 anos

**Não medido com volume real de 5 anos** — geraria dados sintéticos só para
este relatório, sem valor de produto. Verificado por **ausência**: não existe
job de expurgo ou `DELETE` programado em lugar nenhum do código
(`grep` por `retencao`/`purge`/`expurg` no backend inteiro devolve só o
comentário que *menciona* a política, em `temperatura_excursoes.py`) — o dado
persiste indefinidamente por padrão do Postgres, não por garantia ativa do
sistema. **Isto é uma lacuna, registrada, não uma medição.**

---

## 3. As quatro métricas do PRD §9

Publicadas por [R-002](./R-002-avaliacao-ciclo-1.md), 43 casos, dois modelos,
dois modos, execução real (nunca o mock):

| Modelo | Modo | Schema válido | Composição correta | p95 | Tokens de entrada |
|---|---|---|---|---|---|
| `claude-sonnet-5` | restrito | 83,7% | 76,7% | 7 682 ms | 10 262 |
| `claude-sonnet-5` | livre | 88,4% | 83,7% | 15 931 ms | 5 756 |
| `claude-haiku-4.5` | restrito | **95,3%** | 81,4% | 7 522 ms | 7 730 |
| `claude-haiku-4.5` | livre | **95,3%** | 79,1% | 3 091 ms | 4 221 |

Alvos: schema válido ≥ 95% · composição correta ≥ 85% · p95 ≤ 3 s · tokens —
alerta em 4k.

**Recomendação de modelo: `haiku-4.5`.** É o único que bate a meta de schema
válido, nos dois modos, e é 2,6× mais barato que `sonnet-5` em modo restrito.
Nenhum dos dois bate composição correta nem p95 — ver §4.

O catálogo cresceu de 7 casos/7 componentes (R-001, spike da T-017) para 43
casos/24 componentes (R-002, esta tarefa). A queda nas taxas **é esperada com
catálogo maior**, não é regressão do modelo — mais opção é mais chance de
confundir componentes semanticamente próximos.

---

## 4. O que não se sustentou

Seção obrigatória — o AC-3 desta tarefa existe pra forçar que ela não fique
vazia.

- **Nenhuma das quatro metas do PRD §9 é batida pelos dois modelos ao mesmo
  tempo.** `haiku-4.5` bate schema válido; nenhum bate composição correta
  (76,7%–83,7% contra alvo de 85%) nem p95 (todos acima de 3s, o melhor caso
  é 3 091 ms). O PRD tratava estes quatro números como binários — "o ciclo
  não fecha sem eles" — e a leitura correta, com os números em mãos, é mais
  fina: os números existem e são bons o bastante pra decidir, mas não são o
  "sim" que o documento original esperava.
- **Suíte de avaliação não roda em CI.** O PRD §11 pedia "a cada mudança de
  catálogo ou prompt"; o que existe é `make eval` manual, fora do CI de
  propósito ([ADR-0013](../adr/0013-suite-de-avaliacao.md): gasta token a cada
  execução). Nenhum gatilho automático (`paths:` do GitHub Actions,
  por exemplo) foi implementado. Isto é dívida real, não decisão registrada.
- **Pelo menos 5 dos 43 casos da suíte de avaliação têm composição esperada
  questionável** ([A-50](../tasks/ACHADOS.md)) — escritos olhando o
  componente mais específico, quando o modelo escolheu um substituto que a
  permissão do ator também alcança. Isto **infla artificialmente a taxa de
  falha** medida em §3: o número real de composição correta é provavelmente
  mais alto que o publicado, mas o relatório publica o número medido, não o
  número corrigido — corrigir os casos é trabalho futuro, não deste
  relatório.
- **`temperatura-marco`, um sexto caso, falhou nas quatro combinações sem
  explicação defensável** — o modelo nunca compôs, mesmo com o componente
  disponível e a permissão presente. Diferente dos outros 5, isto é sinal
  real, possivelmente de uma `description` ambígua entre
  `temperatura_historico` e `temperatura_excursoes` — não investigado a
  fundo aqui.
- **RNF-06 não tem número real** (§2) — verificado por ausência de expurgo,
  não por medição de volume.
- **CA-06 (escopo de unidade) continua parcial** — provado na fila de
  vencimento e em quatro componentes de lote; o resto do catálogo não tem
  teste dedicado, mesmo que a autorização por baixo (T-009, motor de
  permissão) seja a mesma para todos.
- **Catálogo tem 24 componentes, não 23** — o PRD nunca foi atualizado
  quando `vencimento_grafico` foi acrescentado. Dentro do teto (25), mas o
  número documentado divergiu do sistema por um ciclo inteiro sem ninguém
  notar — o mesmo tipo de deriva silenciosa que o R-5 (risco de filtro sem
  enum) descreve para outro tipo de recorte.
- **A série histórica no LangFuse nunca foi ligada** — telemetria com `401`
  nas execuções tentadas (achado A-10/T-043, ainda sem dono). Os números
  deste relatório vêm de JSON local, não de um painel que alguém possa abrir
  amanhã e comparar.

---

## 5. Achados consolidados

Ver [`docs/05-achados-ciclo-1.md`](../05-achados-ciclo-1.md) para a narrativa
completa. Resumo por destino:

| Destino | Quantidade | Exemplos |
|---|---|---|
| Fechados durante o ciclo | 31 | A-27 (variável de ambiente confirmava o destino errado), A-44 (testes gravando no banco de desenvolvimento), A-49 (escrita por rota nunca chegava ao servidor) |
| Esperando decisão do cliente | 4 | A-19 (listas de motivo por tipo), A-23 (livro de controlados exportável), A-33 (integridade do recebimento), A-35 (auditar navegação é exigência regulatória?) |
| Anotados como limite conhecido, decisão consciente de não fazer agora | 11 | A-38 (estorno de entrada sem representação), A-42 (`titulo` sem teto — CS-04 passou, mas o texto hostil chega ao título), A-43 (checagem morta em `validar.py`) |
| Aberto, sem tarefa própria | 1 | A-50 (casos de avaliação com `esperado` questionável — §4) |

**Nenhum achado fechado por decreto.** Todo "✅ resolvido" em
`achados-resolvidos.md` tem o teste que prova, não só a afirmação.

---

## 6. Custo real medido

Com o catálogo de 24 componentes (não os 7 do R-001):

| | `sonnet-5` | `haiku-4.5` |
|---|---|---|
| Custo por pergunta (restrito) | ~US$ 0,0219 | ~US$ 0,0083 |
| Custo por pergunta (livre) | ~US$ 0,0134 | ~US$ 0,0045 |
| Custo mensal estimado (1 ator, 20 perguntas/dia, restrito) | ~US$ 13,15 | ~US$ 4,98 |

Calculado a partir do custo total dividido pelos 43 casos de cada execução do
[R-002](./R-002-avaliacao-ciclo-1.md). Acima da estimativa de ~US\$ 2,50/mês
que o README publicava com o catálogo de 7 do R-001 — o catálogo maior custa
mais prompt, como o R-002 §3 já registrava para tokens de entrada.

---

## 7. Pendências para o ciclo 2

**As cinco perguntas do [documento 02 §10](../02-regras-de-negocio.md) são
critério de ENTRADA do ciclo 2, não de saída dele** — o roadmap (PRD §12) já
diz isto para o item 1 (contagem e inventário), e vale para os outros
igualmente:

1. Contagem cíclica por endereço ou por curva ABC?
2. O substituto do RT é papel fixo ou designação por período? (assumido: por
   período)
3. Devolução de cliente volta para quarentena ou bloqueio direto? (assumido:
   quarentena)
4. Limite de R$ 5.000 é por item ou por contagem inteira? (assumido: por
   contagem)
5. Uberlândia off-line — comportamento com dois usuários contando o mesmo
   endereço sem conexão?

Mais os quatro achados esperando decisão do cliente (§5, tabela) — são a
mesma categoria de pendência, não itens separados.

**Trabalho técnico que o ciclo 2 herda, não pendência do cliente:**

- Ligar a suíte de avaliação ao CI (o item vermelho do §1).
- Corrigir os 5 casos de avaliação com `esperado` questionável (A-50).
- Investigar `temperatura-marco` (§4).
- Cobrir CA-06 no resto do catálogo.
- Ligar a série histórica no LangFuse.

---

## 8. O que faríamos diferente

- **Medir o número real de performance na tarefa que cria o componente, não
  numa tarefa de fechamento no fim.** RNF-01 e RNF-04 ficaram sete semanas
  sem número real porque a tarefa que os "provava" (T-021, T-031) provava só
  a forma. O padrão "prova de forma agora, número real depois" é razoável
  para não bloquear o paralelismo — mas só se alguém voltar. Quase não
  voltou: só voltou porque o T-034 existe e tem AC específico pra isso.
- **Contar componentes do catálogo automaticamente em documentação, não à
  mão.** O PRD disse "23" a tarefa inteira enquanto o sistema tinha 24 — o
  mesmo tipo de deriva que R-5 descreve para filtro, só que na própria
  contagem que o PRD usa para decidir se o ciclo fecha.
- **Rodar a suíte de avaliação nova ANTES de escrever os casos novos, com um
  subconjunto pequeno, pra validar o formato do `esperado` contra o modelo
  real cedo** — em vez de escrever 25 casos de uma vez e descobrir, só na
  execução final, que pelo menos 5 tinham leitura alternativa defensável. Um
  piloto de 3–4 casos teria custado centavos e pego o padrão
  ("`esperado` = componente mais específico, modelo escolhe substituto
  válido") antes de escalar.
- **Decidir "CI roda a suíte a cada mudança de catálogo" como uma tarefa
  própria, não como uma linha do PRD que ninguém pegou.** Ficou sem dono do
  início ao fim do ciclo — é o único item vermelho do checklist de release,
  e é vermelho porque nunca teve uma tarefa, não porque alguém tentou e
  falhou.
- **O padrão de propriedade exclusiva de arquivo funcionou bem para código.
  Para documentos como `ACHADOS.md`, `BOARD.md` e `PROGRESSO.md` — que
  praticamente toda tarefa toca — ele não se aplica, e não devia fingir que
  se aplica.** Duas tarefas fechadas na mesma sessão (T-032 e T-055, por
  exemplo) editam os três de forma intercalada; a saída prática foi um
  commit reconhecer isso explicitamente em vez de forçar uma separação
  artificial.

---

## 9. Veredito

**O ciclo 1 fecha.** A tese central — modelo compõe por schema, nunca
escreve, autorização em três momentos — está implementada, testada nos dois
sentidos (positivo e negativo) em toda superfície que foi auditada, e
nenhuma das 15 sondas negativas da suíte de avaliação vazou dado ou compôs
escrita. Os dois números que faltavam desde o R-001 (RNF-01, RNF-04) agora
têm medição real, e os dois batem a meta por larga margem.

O que fica registrado, não escondido: as quatro métricas do PRD §9 não são
batidas pelos dois modelos ao mesmo tempo, a suíte de avaliação não está em
CI, e uma fração real dos casos de avaliação precisa de revisão antes que o
número de "composição correta" seja confiável no dígito. Nada disso é
motivo para não fechar — é o que o ciclo 2 herda, com nome e dono.
