# PRD-001 — Controle de Estoque com Assistente · Ciclo 1

| | |
|---|---|
| **Documento** | PRD-001 |
| **Versão** | 1.0 |
| **Status** | Aprovado — pronto para implementação |
| **Release alvo** | Ciclo 1 |
| **Cliente** | Bertoni Distribuidora Farmacêutica (caso fictício) |
| **Fontes** | [Cliente](../01-o-cliente.md) · [Regras de negócio](../02-regras-de-negocio.md) · [Arquitetura](../03-arquitetura-v2.md) |
| **Decisões** | [ADR-0001 a ADR-0015](../adr/) |
| **Backlog** | [tasks/BOARD.md](../tasks/BOARD.md) |

> **Autoridade deste documento.** O PRD é normativo para **requisitos**. As regras
> de negócio (`RN-*`) permanecem normativas no [documento 02](../02-regras-de-negocio.md);
> este PRD as referencia, não as substitui. Decisões técnicas são normativas nos
> ADRs. Onde houver conflito: RN > ADR > PRD > tarefa.

---

## 1. Sumário executivo

A Bertoni opera três unidades de distribuição farmacêutica sobre um ERP de 2004 que
não conhece lote. A consequência medida: um recall de losartana levou **9 dias**
para ser rastreado, o inventário anual acusou **3,8%** de divergência, **R$ 183 mil**
venceram em prateleira e uma inspeção da ANVISA gerou auto de infração por
histórico de temperatura não comprovável.

O ciclo 1 entrega um sistema de estoque por lote com duas superfícies: **telas
tradicionais** para a operação de alta frequência e um **assistente que compõe a
interface** a partir de um catálogo de componentes registrados — sem gerar código
e sem nunca autorizar escrita.

**O ciclo 1 é considerado bem-sucedido se, e somente se,** os oito critérios de
aceite do cliente passarem como teste automatizado **e** os quatro números da
seção 9 forem medidos com um modelo real. Cobertura funcional do estoque inteiro
não é objetivo deste ciclo.

---

## 2. Problema

| Episódio | Custo | Causa raiz |
|---|---|---|
| Recall da losartana | 9 dias de rastreamento manual | O ERP não conhece lote; a rastreabilidade vive em planilha |
| Divergência de inventário | 3,8% do valor em estoque | Saldo é campo editável, sem movimento com autor e motivo |
| Vencimento em prateleira | R$ 183 mil | Não existe fila de vencimento; a checagem é manual e amostral |
| Auto de infração da ANVISA | Sanção regulatória | Histórico de temperatura não consultável por período |
| Vazamento de margem | Comercial exposto | Custo visível para papéis que não deveriam vê-lo |
| Blister de clonazepam | Risco regulatório e criminal | Movimentação de controlado concluída com uma identificação só |

Nenhum desses problemas é resolvido por relatório. Todos exigem que o **lote** seja
uma entidade de primeira classe e que o **saldo seja derivado de movimentos
imutáveis**.

---

## 3. Objetivos

| # | Objetivo | Como se mede |
|---|---|---|
| **O-1** | Rastreabilidade de lote ponta a ponta | CA-01 passa: lote → clientes em < 60 s |
| **O-2** | Saldo auditável por construção | CA-02 e CA-08 passam: saldo é soma de movimentos imutáveis |
| **O-3** | Perda por vencimento visível antes de acontecer | CA-03 passa: fila de 90 dias por unidade |
| **O-4** | Separação de funções aplicada pelo sistema | CA-04 passa: controlado exige duas identificações |
| **O-5** | Confidencialidade por papel e por unidade | CA-05 e CA-06 passam, inclusive pelo assistente |
| **O-6** | Conformidade de cadeia fria demonstrável | CA-07 passa: histórico por período, exportável |
| **O-7** | Validar a hipótese de UI generativa por schema com dado e permissão reais | Os quatro números da seção 9, com modelo real |

### 3.1 Não-objetivos

| # | Fora | Porquê |
|---|---|---|
| **NO-1** | Contagem, inventário e ajuste de saldo | [ADR-0010](../adr/0010-corte-de-escopo-ciclo-1.md) |
| **NO-2** | Transferência entre unidades | ADR-0010 |
| **NO-3** | Operação off-line | [ADR-0015](../adr/0015-assistente-exige-conexao.md) |
| **NO-4** | Nota fiscal, financeiro, faturamento, precificação, roteirização | Permanecem no ERP — [documento 02 §1](../02-regras-de-negocio.md) |
| **NO-5** | Substituto do RT (`RN-A05`) | Depende de decisão do cliente; sem contagem, não é caminho crítico |
| ~~**NO-6**~~ | ~~Compartilhamento de view entre usuários~~ | **Entrou no escopo** a pedido, e foi entregue — ver §5.4 |
| **NO-7** | Recuperação de catálogo (RAG sobre componentes) | Desnecessária em 23 componentes — [ADR-0011](../adr/0011-teto-de-catalogo.md) |
| **NO-8** | Geração de código pelo modelo (L3) | [ADR-0001](../adr/0001-ui-por-schema.md) |

---

## 4. Personas

Os seis papéis são todos implementados. **O conjunto de papéis é o teste de
permissão** — remover um enfraquece o release.

| Persona | Papel | Unidades | O que precisa | O que não pode ver |
|---|---|---|---|---|
| **Cleide** | Conferente | Matriz, Refrigerado | Receber com leitor, uma mão livre | Custo, margem |
| **Helena** | RT (farmacêutica) | Todas | Liberar quarentena, autorizar controlado | Custo, margem |
| **Ivo** | Gerente | Matriz, Refrigerado | Saída, descarte, panorama das suas unidades | Custo · Uberlândia |
| **Odair** | Gerente | Uberlândia | O mesmo, na filial | Custo · Matriz e Refrigerado |
| **Marco** | Diretor | Todas | Panorama consolidado, valor em estoque | — |
| **Rafael** | Comprador | Todas (leitura) | Saldo, curva, custo para negociar | Escrita de estoque |
| **Sandra** | Auditoria | Todas (leitura) | Trilha completa, exportação | Escrita |

---

## 5. Escopo funcional

### 5.1 Entidades

**Dentro:** Produto, Lote, Unidade, Movimento, Recebimento, Registro de temperatura,
Usuário, Trilha de auditoria.

**Fora:** Contagem, Ajuste, Transferência, Pedido de compra. Cliente existe apenas
como destinatário em movimentos de saída, para servir ao recall — não é cadastro.

### 5.2 Requisitos funcionais

Cada `RF` deriva de regras do documento 02 e é implementado por tarefas rastreadas
em [RASTREABILIDADE.md](../RASTREABILIDADE.md).

| RF | Requisito | Regras |
|---|---|---|
| **RF-01** | Saldo de lote é a soma dos seus movimentos; não existe campo de saldo editável | RN-M06, RN-P01 |
| **RF-02** | Movimento é imutável: não editável e não excluível por nenhum papel | RN-M02, RN-D02 |
| **RF-03** | Correção de movimento se faz por estorno referenciando o original, com motivo de lista fechada | RN-M03, RN-M05 |
| **RF-04** | Todo recebimento entra em quarentena; não existe entrada direta em estoque liberado | RN-R01 |
| **RF-05** | A liberação de quarentena é privativa do RT e exige checklist registrado | RN-R02, RN-R03 |
| **RF-06** | Lote com validade ≤ 90 dias entra na fila de vencimento; ≤ 30 dias é bloqueado automaticamente | RN-L04, RN-L05 |
| **RF-07** | Saída propõe o lote de menor validade (FEFO); divergir exige justificativa registrada | RN-L02, RN-L03 |
| **RF-08** | Saldo nunca fica negativo; movimento que resultaria em negativo é rejeitado | RN-M01 |
| **RF-09** | Movimentação de controlado só se efetiva com duas identificações distintas | RN-C01, RN-C02 |
| **RF-10** | Dado um lote, o sistema lista clientes, notas e datas; dado um cliente e período, lista lotes | RN-D03, RN-D04 |
| **RF-11** | Temperatura é registrada em intervalo fixo, consultável por período e exportável | RN-F03, RNF-06 |
| **RF-12** | Excursão de temperatura gera ocorrência vinculada aos lotes presentes no período | RN-F04 |
| **RF-13** | Usuário só enxerga dados das unidades às quais está vinculado | RN-A01 |
| **RF-14** | Custo e margem são visíveis apenas para Diretor, Comprador e Auditoria — em tela, exportação e assistente | RN-A02 |
| **RF-15** | Toda escrita gera registro de auditoria imutável com valor anterior e novo | RN-D01, RN-D02 |
| **RF-16** | Consulta de auditoria é ela própria auditada | RN-D05 |
| **RF-17** | Produto com movimento no histórico é inativado, nunca excluído; usuário é desativado, nunca excluído | RN-P04, RN-A06 |
| **RF-18** | O assistente compõe a resposta a partir de um catálogo filtrado pelas permissões e unidades do ator | RN-A03 · ADR-0003 |
| **RF-19** | Toda composição tem identidade estável derivada do schema, endereçável por URL | ADR-0009 |
| **RF-20** | Termolábil só existe em unidade refrigerada; controlado só em unidade com sala-cofre | RN-P02, RN-P03 |

---

### 5.4 Escopo acrescentado durante a execução

Três coisas entraram depois do PRD original. Registradas aqui porque um PRD que
não acompanha a execução vira ficção — foi o achado A-06 da
[auditoria A-002](../relatorios/A-002-auditoria-de-execucao.md).

| Entregue | Era | Por que entrou |
|---|---|---|
| **Compartilhamento de view** | `NO-6`, não-objetivo | Pedido explicitamente. Entregue com destinatários filtrados por quem consegue abrir a composição, e a regra "aponta para uma view, não concede acesso" verificada |
| **`vencimento_grafico`** | não previsto | O indicador responde *quantos*; a curva responde *quando*. Catálogo passa de 22 para 23, folga de 2 |
| **Cadastro de usuário** | não era RF | Pedido. Cria usuário sem papel e sem permissão ([ADR-0019](../adr/0019-autenticacao-e-cadastro.md)) |

**RF-21** — Uma view pode ser compartilhada com quem consegue abri-la; o
destinatário carrega sob a própria permissão, com o schema revalidado contra o
catálogo dele.

## 6. Histórias de usuário

Formato: **Dado / Quando / Então**. Cada `AC` é verificável por teste automatizado
e está amarrado a uma tarefa em [RASTREABILIDADE.md](../RASTREABILIDADE.md).

### US-01 — Rastrear um recall · *Sandra, Marco* · `CA-01`

> Como auditora, preciso descobrir quem recebeu um lote suspeito em menos de um
> minuto, para que o recall não dependa de nove dias de planilha.

- **AC-01.1** Dado um número de lote com saídas registradas, quando consulto a
  rastreabilidade, então recebo cliente, nota e data de cada saída, **em menos de
  60 segundos** (`RNF-01`).
- **AC-01.2** Dado um cliente e um período, quando consulto no sentido inverso,
  então recebo todos os lotes que ele recebeu.
- **AC-01.3** Dado que a consulta foi executada, então existe registro de auditoria
  de quem consultou o quê e quando (`RN-D05`).

### US-02 — Receber mercadoria em quarentena · *Cleide* · `CA-02`

> Como conferente, preciso registrar o recebimento com o leitor e uma mão livre.

- **AC-02.1** Dado um recebimento registrado, então o lote nasce em **Quarentena**;
  não existe caminho para entrada direta em liberado.
- **AC-02.2** Dado um lote com validade inferior a 6 meses, quando registro o
  recebimento, então é recusado, salvo autorização expressa do RT (`RN-L07`).
- **AC-02.3** Dado um produto termolábil, quando registro o recebimento, então a
  temperatura de chegada é obrigatória (`RN-F01`).
- **AC-02.4** Dada divergência entre nota e físico, então o recebimento se conclui
  e gera pendência vinculada (`RN-R04`).
- **AC-02.5** Dado o fluxo completo, então nenhum campo exige digitação quando há
  código de barras disponível (`RNF-02`).

### US-03 — Liberar quarentena · *Helena* · `CA-02`

> Como RT, respondo legalmente pela liberação; ninguém mais pode fazê-la.

- **AC-03.1** Dado qualquer papel que não seja RT, quando tenta liberar, então é
  recusado no servidor — mesmo com requisição forjada (`RN-R02`).
- **AC-03.2** Dado que sou RT, quando libero, então o checklist de integridade,
  validade, nota e — se termolábil — temperatura é obrigatório (`RN-R03`).
- **AC-03.3** Dado um lote reprovado, então ele vai para **Bloqueado**, nunca para
  liberado.
- **AC-03.4** Dado que não sou RT, então nenhum componente de liberação aparece no
  meu catálogo do assistente (`ADR-0003`).

### US-04 — Ver o que vai vencer · *Ivo, Odair* · `CA-03`

- **AC-04.1** Dada a fila de vencimento, então lista todo lote com validade ≤ 90
  dias, apenas das minhas unidades, sem planilha.
- **AC-04.2** Dado um lote que atinge 30 dias de validade, então é bloqueado
  automaticamente para venda (`RN-L05`).
- **AC-04.3** Dado um lote bloqueado por validade, então apenas o RT o libera, com
  justificativa registrada.

### US-05 — Dar saída obedecendo FEFO · *Ivo, Odair, Cleide* · `CA-02`

- **AC-05.1** Dada uma saída, então o sistema propõe o lote **liberado** de menor
  validade (`RN-L02`).
- **AC-05.2** Dado que escolho outro lote, então justificativa é obrigatória e fica
  registrada no movimento (`RN-L03`).
- **AC-05.3** Dado um lote vencido ou bloqueado, então nenhuma saída é possível,
  exceto movimento de descarte (`RN-L06`).
- **AC-05.4** Dada uma saída que deixaria o saldo negativo, então é rejeitada
  (`RN-M01`).

### US-06 — Movimentar controlado com dupla identificação · *Cleide + Helena* · `CA-04`

- **AC-06.1** Dado que a conferente submete a movimentação, então o movimento fica
  em `aguardando_autorizacao` e **o saldo não muda**.
- **AC-06.2** Dado que o RT autoriza, então o movimento se efetiva com **as duas
  identidades** gravadas.
- **AC-06.3** Dado que a mesma pessoa tenta submeter e autorizar, então é recusado
  (`RN-A04`, `RN-C01`).
- **AC-06.4** Dado ajuste de controlado, então motivo e documento anexo são
  obrigatórios (`RN-C02`).

### US-07 — Corrigir um erro sem apagar história · *Ivo, Helena, Marco* · `CA-08`

- **AC-07.1** Dado qualquer papel, incluindo Diretor, quando tenta excluir um
  movimento, então é recusado (`RN-M02`).
- **AC-07.2** Dado um estorno, então ele referencia o movimento original, exige
  motivo de lista fechada e ambos permanecem visíveis (`RN-M03`).
- **AC-07.3** Dado o estorno aplicado, então o saldo reflete a soma dos dois
  movimentos, sem edição de campo.

### US-08 — Não ver o que não me cabe · *Cleide, Helena, Ivo* · `CA-05`

- **AC-08.1** Dado um papel sem `custo.ler`, então custo e margem não aparecem em
  tela, em exportação nem na resposta do assistente.
- **AC-08.2** Dado esse papel, então **nenhum componente que exponha custo entra no
  catálogo** enviado ao modelo.
- **AC-08.3** Dado que ele pergunta explicitamente pelo custo, então a resposta não
  contém o valor por nenhum caminho, incluindo agregados derivados.

### US-09 — Escopo de unidade · *Odair* · `CA-06`

- **AC-09.1** Dado que Odair pede dados de Ribeirão Preto, então não obtém saldo,
  movimento nem recebimento por nenhum caminho.
- **AC-09.2** Dado um id de registro de outra unidade, então a resposta é
  indistinguível de registro inexistente (`RN-A07`, [ADR-0014](../adr/0014-erros-que-nao-vazam.md)).
- **AC-09.3** Dado um pedido pela unidade inteira, então a negativa é explícita —
  a existência da unidade não é segredo (ADR-0014).

### US-10 — Comprovar cadeia fria · *Helena, Sandra* · `CA-07`

- **AC-10.1** Dado um período, então o histórico de temperatura da unidade
  refrigerada é consultável e exportável.
- **AC-10.2** Dada uma excursão fora de 2–8 °C, então existe ocorrência vinculada
  aos lotes presentes na unidade naquele período (`RN-F04`).
- **AC-10.3** Dado o requisito regulatório, então o registro é retido por 5 anos
  (`RNF-06`).

### US-11 — Perguntar em linguagem natural · *todos* · `O-7`

- **AC-11.1** Dada uma pergunta de consulta, então o assistente responde compondo
  componentes registrados, sem gerar código.
- **AC-11.2** Dado um schema com componente não registrado ou valor fora de enum,
  então é rejeitado e aparece no Execution Trace.
- **AC-11.3** Dado um schema forjado enviado direto ao endpoint, sem passar pelo
  modelo, então é rejeitado com o mesmo rigor (`CS-01`).
- **AC-11.4** Dada a mesma pergunta em duas sessões, então composições iguais
  produzem a mesma `viewKey` (`RF-19`).

---

## 7. Requisitos não funcionais

| ID | Requisito | Verificação |
|---|---|---|
| **RNF-01** | Rastreamento de recall responde em < 60 s | Teste de performance com fixture de volume |
| **RNF-02** | Conferência opera com leitor e uma mão, sem digitação obrigatória | Revisão de fluxo + teste de teclado |
| **RNF-04** | Nenhuma tela de operação passa de 2 s em uso normal | p95 medido nas telas com rota |
| **RNF-06** | Temperatura retida por 5 anos, consultável por período | Teste com fixture de série longa |
| **RNF-07** | Assistente: p95 até o primeiro componente ≤ 3 s | Suíte de avaliação, modelo real |
| **RNF-08** | Catálogo ≤ 25 componentes; ciclo 1 fecha em 23 | Teste que falha o build ao ultrapassar |

`RNF-03` (off-line) e `RNF-05` (implantação sem parar a operação) ficam fora deste
ciclo — ver NO-3 e ADR-0015.

---

## 8. Requisitos de segurança

Estes nascem da composição dinâmica e **não existiam no documento 02**, porque o
documento 02 descreve o negócio, não esta arquitetura.

| ID | Requisito | ADR |
|---|---|---|
| **CS-01** | Schema enviado direto ao servidor, sem passar pelo modelo, é validado com o mesmo rigor | ADR-0004 |
| **CS-02** | Catálogo é filtrado por ator antes de ir ao modelo; o modelo não conhece o que o ator não pode | ADR-0003 |
| **CS-03** | Negativa por escopo não revela existência de registro individual | ADR-0014 |
| **CS-04** | Conteúdo vindo do banco (nome de produto, motivo, observação) não altera a composição | ADR-0012 |
| **CS-05** | Toda resposta do assistente gera registro de auditoria | RN-D05 |
| **CS-06** | Rate limit por ator no endpoint do assistente | ADR-0011 |

> **CS-04 é o requisito de menor confiança do release.** Não há solução conhecida
> completa para injeção de prompt via dado. A mitigação está no ADR-0012, e o
> resultado do teste é um **achado a registrar**, não necessariamente um defeito a
> corrigir dentro do ciclo.

---

## 9. Métricas de sucesso

Sem estes quatro números o ciclo **não fecha**, independentemente de funcionalidade
entregue. Eles respondem a pergunta que a POC v1 deixou aberta.

| Métrica | Alvo do ciclo 1 | Como |
|---|---|---|
| **Taxa de schema válido** | Medir e publicar; alvo ≥ 95% | Suíte de ~40 perguntas, modelo real, catálogo de 23 |
| **Taxa de composição correta** dado schema válido | Medir e publicar; alvo ≥ 85% | Comparação com composição esperada |
| **Tempo até o primeiro componente** | p50 e p95; p95 ≤ 3 s | Instrumentação no Execution Trace |
| **Custo por pergunta** | Medir; teto de alerta em 4k tokens de entrada | Contagem de tokens com catálogo real |

Medidos com **os dois modelos**, com o mesmo conjunto de perguntas. A escolha de
produção sai do número, não da intuição.

O modelo e o provedor são configuração
([ADR-0025](../adr/0025-agnosticismo-de-provedor.md)): `PROVEDOR` e
`MODELO_ASSISTENTE` no `.env`, sem tocar em código. `make eval` roda a suíte;
`make modelo` diz o que está em uso.

### Primeira medição — 17 casos, Claude Haiku 4.5 via OpenRouter

| | restrito | livre |
|---|---|---|
| schema válido | 100% | 100% |
| composição correta | 100% | 100% |
| tokens de entrada (médio) | **2078** | **962** |
| custo (17 casos) | US$ 0,039 | US$ 0,020 |

> A decodificação restrita **mais que dobra os tokens de entrada** — o JSON
> Schema do catálogo viaja em toda pergunta. Com 23 componentes os dois modos
> acertam igual, o que torna o custo o único critério, e ele favorece o modo
> livre. Pode inverter com catálogo maior ou modelo mais fraco.

**Ainda não medido:** Sonnet, e a série histórica no LangFuse — cujo caminho de
código não foi exercitado ([ADR-0026](../adr/0026-observabilidade.md)).

---

## 10. Riscos

| # | Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|---|
| **R-1** | Modelo real emite schema válido com frequência baixa demais | Média | **Fatal para O-7** | T-017 mede com 6 componentes antes de existirem 23 |
| **R-2** | Injeção de prompt via dado do banco altera composição | Média | Alto | ADR-0012; teste CS-04; achado documentado |
| **R-3** | Catálogo cresce e estoura o orçamento de tokens | Baixa | Médio | RNF-08 falha o build acima de 25 |
| **R-4** | Latência do modelo inviabiliza a experiência | Média | Médio | Assistente nunca está no caminho da operação de alta frequência (ADR-0002) |
| **R-5** | Filtro ausente no catálogo alarga resposta em silêncio | **Alta** | Alto | Todo recorte é enum nomeado; auditoria de enums na suíte de avaliação |
| **R-6** | Paralelismo gera conflito de merge e retrabalho | Média | Médio | Contratos congelados + propriedade exclusiva de arquivo ([tasks/README](../tasks/README.md)) |

**R-5 é o achado mais perigoso herdado da v1:** componente não registrado é
rejeitado e aparece no trace; **filtro que falta apenas alarga a resposta, em
silêncio.** Não há erro para observar.

---

## 11. Critérios de release

> **Estado real:** apurado na [auditoria A-002](../relatorios/A-002-auditoria-de-execucao.md)
> e mantido em [PROGRESSO](../tasks/PROGRESSO.md). Hoje: **19 tarefas
> concluídas, 5 parciais, 15 não iniciadas · 3 de 23 componentes · nenhuma
> escrita.** Um único critério de aceite do cliente está completo (CA-03).

O ciclo 1 está pronto quando **todos** os itens abaixo estiverem verdes:

- [ ] CA-01 a CA-08 passam como teste automatizado
- [ ] CS-01 a CS-06 passam, ou CS-04 tem achado documentado com decisão registrada
- [ ] RF-01 a RF-20 implementados e rastreados
- [ ] As quatro métricas da seção 9 medidas com os dois modelos e publicadas
- [ ] `npm run arch:check` verde, com as regras testadas negativamente
- [ ] Catálogo com 23 componentes; teste de orçamento verde
- [ ] Suíte de avaliação executando em CI a cada mudança de catálogo ou de prompt
- [ ] Relatório de fechamento (T-034) escrito, incluindo o que **não** se sustentou

---

## 12. Roadmap posterior

Em ordem de valor, com o pré-requisito de cada um:

| # | Item | Pré-requisito |
|---|---|---|
| 1 | Contagem e inventário | Respostas do cliente às pendências 1, 4 e 5 do documento 02 |
| 2 | Operação off-line em Uberlândia | Item 1 — é quem precisa dele |
| 3 | Ajuste de saldo | Item 1 (`RN-I05`) |
| 4 | Transferência entre unidades | — |
| 5 | Compartilhamento de view | Identidade de view (entregue no ciclo 1) |
| 6 | Substituto do RT | Decisão do cliente sobre `RN-A05` |
| 7 | Recuperação de catálogo | Só se passar de 25 componentes |
