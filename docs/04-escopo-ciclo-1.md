# Escopo do Ciclo 1

**Documento 4 — o que se constrói primeiro, e o que fica de fora.**

> **Histórico.** Este documento foi a análise que produziu o corte de escopo do
> ciclo 1. Seu conteúdo normativo migrou para o [PRD-001](./prd/PRD-001-ciclo-1.md)
> (requisitos), para o [ADR-0010](./adr/0010-corte-de-escopo-ciclo-1.md) (o corte) e
> para os [ADRs 0008 a 0015](./adr/) (as decisões técnicas). **Em caso de
> divergência, valem o PRD e os ADRs.** Este texto permanece porque registra o
> raciocínio — a conferência critério a critério que levou ao corte.

---

## 1. O que o ciclo 1 tem que provar

Três coisas, nesta ordem de risco:

1. **Um modelo real emite schema válido com que frequência?** A pergunta da seção
   13 do documento 03, que a v1 nunca respondeu porque nunca rodou com API key.
   Enquanto estiver aberta, todo o resto é encanamento.
2. **Permissão de verdade sobrevive à composição dinâmica?** Catálogo filtrado por
   usuário, revalidação no servidor, autorização em cada `load` e cada `command`.
3. **CRUD funciona sem o modelo chegar perto da escrita?** O plano de render e o
   plano de escrita separados, na prática, com dado real e papel real.

O que o ciclo 1 **não** precisa provar: que o sistema cobre o estoque da Bertoni
inteiro. Não cobre, de propósito.

---

## 2. A decisão de corte

> **Contagem, ajuste e transferência ficam fora do ciclo 1.**

O que decidiu foi a conferência dos critérios de aceite, um a um:

| Critério | Depende de contagem, ajuste ou transferência? |
|---|---|
| CA-01 — recall em menos de 60 s | Não. É rastreabilidade de movimento |
| CA-02 — nenhum saldo muda sem movimento com autor e motivo | Não. É `RN-M06`: saldo é a soma dos movimentos |
| CA-03 — fila de vencimento por unidade | Não |
| CA-04 — controlado não se conclui com uma identificação só | Não. É `RN-C01`, na movimentação |
| CA-05 — custo invisível, inclusive na resposta do assistente | Não |
| CA-06 — Odair não obtém Ribeirão Preto por nenhum caminho | Não |
| CA-07 — histórico de temperatura consultável | Não |
| CA-08 — excluir movimento é recusado para todos | Não |

**Os oito continuam dentro do ciclo 1.** O corte remove três fluxos grandes sem
derrubar um critério sequer.

### Por que esses três, e não outros

Contagem é o pior primeiro fluxo possível para este desenho, por acumular
exatamente as quatro dificuldades que o documento 03 manda evitar no início:

1. É multi-etapa com validação cruzada — o documento 03 §11.1 manda registrar
   inteiro como L1, então **ensina pouco** sobre a hipótese de composição.
2. Exige off-line (`RNF-03`), que colide com catálogo servido pelo servidor —
   item 4 das decisões técnicas em aberto, sem resposta.
3. Traz conflito distribuído de verdade: dois usuários contando o mesmo endereço
   sem conexão. Isso é merge, não CRUD.
4. Depende de duas decisões do cliente ainda não tomadas (itens 4 e 5 da seção
   "Em aberto" do documento 02).

Ajuste cai junto por consequência de regra, não por escolha: `RN-I05` diz que
nenhum ajuste ocorre sem contagem aprovada por trás. Sem contagem, não existe
ajuste avulso para construir.

Transferência cai por ser dois movimentos ligados em duas unidades com estado
intermediário — mesma família de problema, menos valor imediato.

> **Consequência que precisa ficar registrada:** o componente de exemplo do
> documento 03 §4, `lote_ajuste_form`, **não faz parte do ciclo 1.** Ele continua
> sendo o exemplo certo do contrato; só não é o primeiro a ser escrito.

### As cinco pendências deixam de travar

| # | Pendência do documento 02 | Situação no ciclo 1 |
|---|---|---|
| 1 | Contagem cíclica por endereço ou curva ABC | Fora de escopo. Decidir na entrada do ciclo 2 |
| 2 | Substituto do RT é papel fixo ou por período | Fora. Ciclo 1 tem RT único, sem substituto |
| 3 | Devolução de cliente vai para quarentena ou bloqueio | Fora. Não há devolução no ciclo 1 |
| 4 | Limite de R$ 5.000 por item ou por contagem | Fora. Sem contagem, sem alçada |
| 5 | Uberlândia off-line, dois contadores no mesmo endereço | Fora. Ver seção 7 |

**Nenhuma das cinco bloqueia o ciclo 1.** As cinco viram critério de entrada do
ciclo 2, e aí precisam de resposta do cliente antes da primeira linha.

---

## 3. Dentro do ciclo 1

### Entidades

Produto, Lote, Unidade, Movimento, Recebimento, Registro de temperatura, Usuário,
Trilha de auditoria.

**Fora:** Contagem, Ajuste, Transferência, Pedido de compra, Cliente como cadastro
próprio (existe só como destinatário nos movimentos de saída, para o recall).

### Regras vigentes

Todas as famílias `RN-P`, `RN-L`, `RN-R`, `RN-M`, `RN-C`, `RN-F`, `RN-A` e `RN-D`
do documento 02. Ficam de fora `RN-I` (inventário) e `RN-T` (transferência)
inteiras, e `RN-A05` (substituto do RT).

### Papéis

Os seis, com os escopos de unidade da seção 6 do documento 02. Nenhum é cortado —
o conjunto de papéis **é** o teste de permissão, e cortar um enfraquece o ciclo.

### Duas superfícies, não uma

O documento 03 §11.5 é explícito: o assistente não é o app. O ciclo 1 entrega as
duas superfícies.

| Superfície | Para quê |
|---|---|
| **Telas com rota e URL** | Operação do dia a dia: recebimento, saída, quarentena. Abertas 200 vezes por dia, sem modelo no caminho |
| **Assistente** | Pergunta pontual, panorama, comparação, rastreabilidade. Uma pergunta, 1–3 s aceitáveis |

O ganho do desenho aparece aqui: **um componente registrado serve às duas.** O
`quarentena_liberar` é a rota `/quarentena/:id` e é também o que o modelo escolhe
quando Helena pede "liberar o lote L-8842". Uma declaração, dois caminhos.

---

## 4. O catálogo do ciclo 1 — 23 componentes

O teto é 25 (documento 03 §10: 25 componentes ≈ 4k tokens de prompt em toda
pergunta). Ficamos em **23 ≈ 3,8k tokens**, com folga de 2.

### Leitura — o modelo compõe à vontade (L2)

| # | Componente | Params principais | `requires` |
|---|---|---|---|
| 1 | `lote_lista` | produto, unidade, status, faixa de validade | `lote.ler` |
| 2 | `lote_detalhe` | loteId | `lote.ler` |
| 3 | `lote_movimentos` | loteId, período | `movimento.ler` |
| 4 | `produto_ficha` | produtoId | `produto.ler` |
| 5 | `produto_saldo_por_unidade` | produtoId | `lote.ler` |
| 6 | `fila_vencimento` | unidade, janela (30/60/90 d) | `lote.ler` |
| 7 | `rastreabilidade` | direção: `lote_para_clientes` \| `cliente_para_lotes` | `auditoria.rastrear` |
| 8 | `recebimento_lista` | unidade, status, período | `recebimento.ler` |
| 9 | `recebimento_detalhe` | recebimentoId | `recebimento.ler` |
| 10 | `quarentena_fila` | unidade | `lote.ler` |
| 11 | `temperatura_historico` | unidade, período | `temperatura.ler` |
| 12 | `temperatura_excursoes` | unidade, período | `temperatura.ler` |
| 13 | `movimento_lista` | unidade, tipo, período, status | `movimento.ler` |
| 14 | `estoque_indicador` | métrica (enum fechado), unidade | varia por métrica |
| 15 | `auditoria_trilha` | usuário, entidade, período | `auditoria.ler` |

### Escrita — unidades inteiras, escolhidas mas nunca executadas pelo modelo (L1)

| # | Componente | Command | `requires` |
|---|---|---|---|
| 16 | `recebimento_registrar` | `POST /recebimentos` | `recebimento.criar` |
| 17 | `quarentena_liberar` | `POST /lotes/:id/liberacao` | `lote.liberar` |
| 18 | `lote_status_acao` | `POST /lotes/:id/status` — enum: bloquear, desbloquear, liberar vencimento ≤30 d | `lote.status` |
| 19 | `movimento_saida` | `POST /movimentos/saida` | `movimento.criar` |
| 20 | `movimento_estorno` | `POST /movimentos/:id/estorno` | `movimento.estornar` |
| 21 | `movimento_descarte` | `POST /movimentos/descarte` | `movimento.descartar` |
| 22 | `controlado_autorizar` | `POST /movimentos/:id/autorizacao` | `controlado.autorizar` |

### Utilitário

| # | Componente | Uso |
|---|---|---|
| 23 | `confirm_action` | confirmação de comando irreversível — estorno, descarte, reprovação |

### Fusões deliberadas

- **`rastreabilidade`** cobre `RN-D03` e `RN-D04` num componente com enum de
  direção. São a mesma pergunta, dois sentidos.
- **`lote_status_acao`** cobre bloquear, desbloquear e liberar vencimento — três
  transições do mesmo formulário, todas privativas do RT.

Ambas respeitam o documento 03 §11.6: o recorte continua existindo no catálogo
como **valor nomeado no enum**. Filtro que falta alarga a resposta em silêncio;
enum que falta é rejeitado e aparece no trace.

### Onde não há componente

`sem_acesso` **não entra no catálogo.** Negativa é decisão do servidor, nunca
composição do modelo — e `RN-A07` exige que a mensagem não revele existência nem
conteúdo do registro negado. O modelo não escolhe negar; ele nem sabe que existe.

---

## 5. Dupla identificação de controlado — `CA-04`

Único fluxo de duas pessoas no ciclo 1, e está dentro de propósito: é o teste mais
afiado da regra central. Nenhuma saída de modelo conclui a operação.

```
Cleide submete saída de controlado
  → servidor grava movimento em `aguardando_autorizacao`
  → saldo NÃO muda (RN-M06: só movimento efetivado soma)
  → Helena vê em movimento_lista(status: aguardando_autorizacao)
  → Helena autoriza em controlado_autorizar
  → servidor efetiva. Duas identidades no registro
```

Não exige componente novo para a fila: `movimento_lista` já tem o `status` no
enum. Foi assim que o catálogo coube em 23.

---

## 6. Critérios de saída

O ciclo 1 está pronto quando os oito critérios do documento 02 passam **como
teste automatizado**, mais cinco de segurança que a composição dinâmica cria e
que o documento 02 não tinha como prever.

| ID | Critério de segurança | Testa |
|---|---|---|
| **CS-01** | Schema forjado enviado direto ao servidor, sem passar pelo modelo, é rejeitado igual | Documento 03 §6 — schema é payload não-confiável |
| **CS-02** | Cleide pede custo e o catálogo dela não tem componente que o exponha — nem em exportação | `CA-05` pelo caminho do assistente |
| **CS-03** | Odair pede Ribeirão e recebe negado, não vazio, e a mensagem não revela existência | `CA-06` + `RN-A07` |
| **CS-04** | Nome de produto ou motivo vindo do banco contendo instrução para o modelo não altera composição | Injeção via dado — em aberto desde a v1 |
| **CS-05** | Toda resposta do assistente gera registro de auditoria: quem perguntou, o que foi mostrado, quando | `RN-D05` |

**CS-04 é o que menos se sabe fazer.** Não havia nada disso na v1. Se ele não
passar, o resultado é um achado, não um bug — e vira decisão de arquitetura.

### Os números que o ciclo 1 tem que produzir

Sem eles o ciclo não fecha, porque são a resposta da seção 13 do documento 03:

| Medida | Como |
|---|---|
| Taxa de schema válido | Suíte de avaliação, modelo real, catálogo real de 23 |
| Taxa de componente correto dado schema válido | Idem — schema válido e resposta errada é pior que rejeição |
| Tempo até o primeiro componente | p50 e p95, modelo real |
| Custo por pergunta | Tokens de entrada com catálogo de 23 |

Medidos com **os dois modelos**: `claude-haiku-4-5-20251001` e `claude-sonnet-5`.

---

## 7. Decisões técnicas — as seis em aberto do documento 03, fechadas

| # | Questão | Decisão | Porquê |
|---|---|---|---|
| 1 | TanStack Query ou store próprio | **TanStack Query** para estado de servidor; store observável mínimo só para sessão do assistente | A v1 escreveu o store à mão e concluiu que não valeu. Invalidação de pedido superado e coalescing vêm de graça. `useQuery` não é `useEffect` — o `arch:check` continua válido |
| 2 | Como o schema vira URL | **Id gerado no servidor** | `RN-D05` obriga auditar a consulta de qualquer forma. Se o registro tem que existir, ele já é o endereço. Ganha revogação junto |
| 3 | Recuperação de catálogo | **Não no ciclo 1** | 23 componentes. Vira obrigatória se o ciclo 2 passar de 25 |
| 4 | Off-line em Uberlândia | **Assistente exige conexão.** Nada mais no ciclo 1 é off-line | Sem contagem no escopo, o único consumidor real de off-line saiu junto. Volta como problema de ciclo 2, no lugar certo |
| 5 | Modelo e latência | **Medir os dois.** Padrão inicial: haiku | Ver seção 6. Decisão de produção sai do número, não da intuição |
| 6 | Suíte de avaliação | **Desde a primeira semana**, ~40 perguntas com composição esperada | UI não-determinística não tem regressão comum. Rodar a cada mudança de catálogo ou de prompt |

### Herdado da v1 e mantido

- `npm run arch:check` recriado, e **testado negativamente** — introduzir as
  violações de propósito e confirmar que o build quebra. Regra que nunca falhou
  não é evidência de nada.
- Identidade de view (`viewKey` derivada do schema) desde o início. Documento 03
  §11.3: composição sem endereço quebra favorito, histórico, auditoria e voltar
  no navegador.
- **Compartilhamento de view fica para o ciclo 2.** A identidade é fundação e é
  barata; o compartilhamento é feature e tem regra própria de não-escalação.

---

## 8. Ordem de construção

O risco maior vem primeiro. Medir cedo é o único jeito de o achado ainda ser
barato.

| # | Marco | Entrega | Fecha |
|---|---|---|---|
| **M0** | Fundação | `domain/`, `data/` com fixtures das 3 unidades, `registry/`, `arch:check` | Nada de assistente ainda |
| **M1** | **Furo de risco** | 6 componentes de leitura + modelo real + trace | **A pergunta da seção 13.** Se a taxa for ruim, é aqui que se descobre |
| **M2** | Leitura completa | os 15 de leitura, catálogo filtrado por usuário, autorização no `load` | CA-01, CA-03, CA-05, CA-06, CA-07 · CS-02, CS-03 |
| **M3** | Escrita | os 7 commands, `confirm_action`, estorno, autorização no servidor | CA-02, CA-08 · CS-01 |
| **M4** | Controlados e auditoria | dupla identificação, trilha, adversarial | CA-04 · CS-04, CS-05 |
| **M5** | Avaliação | suíte de ~40 perguntas, os dois modelos, números publicados | Seção 6 inteira |

**M1 é o marco que pode matar o projeto**, e é por isso que está em segundo lugar
e não em último. Se um modelo real emite schema válido raramente demais com o
catálogo da Bertoni, o desenho muda antes de existirem 23 componentes escritos.

---

## 9. O que fica registrado para o ciclo 2

Em ordem provável de valor:

1. Contagem e inventário — com os itens 1, 4 e 5 do documento 02 respondidos pelo
   cliente **antes** da primeira linha.
2. Off-line em Uberlândia, junto com a contagem, que é quem precisa dele.
3. Ajuste de saldo, que só existe depois da contagem (`RN-I05`).
4. Transferência entre unidades.
5. Compartilhamento de view pelo sistema — documento 03 §8.
6. Substituto do RT (`RN-A05`).
7. Recuperação de catálogo, se e quando passar de 25 componentes.
