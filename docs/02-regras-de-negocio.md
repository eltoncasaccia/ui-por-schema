# Regras de Negócio — Controle de Estoque

**Documento 2 — Derivado de [O Cliente](./01-o-cliente.md)**
Bertoni Distribuidora Farmacêutica · Ciclo 1

Cada regra tem um identificador estável. Regras marcadas com **[R]** existem por
exigência regulatória; **[S]** por separação de funções; **[C]** por decisão
comercial do cliente. As não marcadas são consequência operacional.

---

## 1. Escopo

### Dentro

Estoque físico: produto, lote, validade, saldo por unidade, endereçamento,
recebimento, quarentena, movimentação, transferência entre unidades, inventário,
ajuste, descarte, controle de temperatura, controle de acesso e trilha de auditoria.

### Fora

Nota fiscal, financeiro, contas a receber, faturamento, comissão, precificação de
venda, roteirização e entrega. Tudo isso permanece no ERP de 2004.

### Integração

| Direção | Conteúdo | Frequência |
|---|---|---|
| ERP → Sistema | Cadastro de produto, entrada de nota de compra, pedidos faturados | Diária |
| Sistema → ERP | Saldo consolidado por produto, ajustes de inventário | Diária |

A unidade de integração é o **produto**; o ERP não conhece lote. O lote existe
apenas aqui, e é isso que resolve o recall.

---

## 2. Glossário

| Termo | Significado |
|---|---|
| **SKU** | Item de catálogo. Não tem saldo por si — o saldo é do lote |
| **Lote** | Quantidade de um SKU, de uma fabricação, com validade única |
| **Unidade** | Depósito físico: CD Matriz, CD Refrigerado, Filial Uberlândia |
| **Quarentena** | Estado de mercadoria recebida e ainda não liberada para venda |
| **RT** | Farmacêutico Responsável Técnico. Responde legalmente pela operação |
| **Controlado** | Medicamento sujeito à Portaria SVS/MS 344/98 |
| **Termolábil** | Produto que exige cadeia fria contínua entre 2 °C e 8 °C |
| **FEFO** | *First Expired, First Out* — sai primeiro o que vence primeiro |
| **Estorno** | Movimento que anula outro, sem apagá-lo |

---

## 3. Entidades

| Entidade | Chave | Observação |
|---|---|---|
| **Produto** | código interno | EAN, fabricante, princípio ativo, classe, curva ABC, mín./máx. |
| **Classe do produto** | — | `comum`, `controlado`, `termolabil`, `antimicrobiano` |
| **Lote** | produto + número do lote + unidade | Validade, fabricação, quantidade, status, endereço |
| **Unidade** | código | Tipo: `seco` ou `refrigerado` |
| **Endereço** | rua · prédio · nível · apto | Posição física dentro da unidade |
| **Movimento** | sequencial imutável | Tipo, lote, quantidade, autor, motivo, data, referência |
| **Recebimento** | número | Fornecedor, nota, itens, temperatura de chegada, status |
| **Contagem** | número | Tipo (cíclica/geral), unidade, itens, contador, aprovador, status |
| **Transferência** | número | Origem, destino, itens, status |
| **Fornecedor** | CNPJ | — |
| **Pedido de compra** | número | Fornecedor, itens, status |
| **Usuário** | matrícula | Papel, unidades vinculadas, ativo |
| **Registro de auditoria** | sequencial imutável | Quem, o quê, quando, antes, depois, origem |

### Tipos de movimento

`entrada` · `saida` · `transferencia_saida` · `transferencia_entrada` ·
`ajuste_positivo` · `ajuste_negativo` · `descarte` · `devolucao` · `estorno`

---

## 4. Máquinas de estado

### 4.1 Lote

| De | Evento | Para | Quem |
|---|---|---|---|
| — | recebimento registrado | **Quarentena** | Conferente |
| Quarentena | liberação | **Liberado** | RT |
| Quarentena | reprovação | **Bloqueado** | RT |
| Liberado | bloqueio (suspeita, recall, avaria) | **Bloqueado** | RT |
| Bloqueado | desbloqueio | **Liberado** | RT |
| Liberado | validade atingida | **Vencido** | Sistema, automático |
| Vencido · Bloqueado | descarte registrado | **Descartado** | Gerente + RT |
| Liberado | saldo chega a zero | **Esgotado** | Sistema, automático |

Apenas **Liberado** permite saída para venda.

### 4.2 Contagem

| De | Evento | Para | Quem |
|---|---|---|---|
| — | abertura | **Rascunho** | Conferente ou Gerente |
| Rascunho | submissão | **Contada** | Contador |
| Contada | sem divergência | **Aprovada** | Sistema |
| Contada | com divergência | **Em divergência** | Sistema |
| Em divergência | aprovação | **Aprovada** | Gerente ou Diretor, conforme valor |
| Em divergência | recontagem | **Rascunho** | Aprovador |
| Aprovada | ajuste gerado | **Aplicada** | Sistema |

### 4.3 Transferência entre unidades

| De | Evento | Para |
|---|---|---|
| — | solicitação | **Solicitada** |
| Solicitada | expedição na origem | **Em trânsito** |
| Em trânsito | recebimento no destino, conforme | **Concluída** |
| Em trânsito | recebimento com diferença | **Em divergência** |
| Em divergência | tratamento | **Concluída** |

Mercadoria em trânsito não pertence a nenhuma das duas unidades para efeito de
venda, mas continua no patrimônio da empresa.

---

## 5. Regras

### 5.1 Produto — `RN-P`

| ID | Regra |
|---|---|
| **RN-P01** | Produto não tem saldo. Saldo é sempre do lote, dentro de uma unidade. |
| **RN-P02** | Produto de classe `termolabil` só pode ter lote em unidade do tipo `refrigerado`. |
| **RN-P03** | Produto de classe `controlado` só pode ter lote na unidade que possua sala-cofre. **[R]** |
| **RN-P04** | Produto com qualquer movimento no histórico **não pode ser excluído**, apenas inativado. |
| **RN-P05** | Produto inativo não aceita entrada, mas continua com saldo visível até esgotar. |
| **RN-P06** | Estoque mínimo e máximo são por produto **e** por unidade — Uberlândia não gira igual a Ribeirão. |

### 5.2 Lote e validade — `RN-L`

| ID | Regra |
|---|---|
| **RN-L01** | Todo lote tem número, data de fabricação e data de validade. Nenhum dos três é opcional. **[R]** |
| **RN-L02** | Saída obedece **FEFO**. O sistema propõe o lote liberado de menor validade. |
| **RN-L03** | Separar um lote diferente do proposto pelo FEFO exige justificativa registrada. |
| **RN-L04** | Lote com validade ≤ **90 dias** entra em alerta e aparece na fila de vencimento. |
| **RN-L05** | Lote com validade ≤ **30 dias** é **bloqueado automaticamente** para venda. Só o RT libera, com justificativa. |
| **RN-L06** | Lote vencido não sai por nenhum motivo, exceto movimento de `descarte`. |
| **RN-L07** | Recebimento com validade inferior a **6 meses** é recusado, salvo autorização expressa do RT. |
| **RN-L08** | Dois lotes de mesmo número, mesmo produto e unidades diferentes são registros distintos com saldos independentes. |

### 5.3 Recebimento e quarentena — `RN-R`

| ID | Regra |
|---|---|
| **RN-R01** | Todo recebimento entra em **Quarentena**. Não existe entrada direta em estoque liberado. **[R]** |
| **RN-R02** | A liberação da quarentena é privativa do **RT**. Nenhum outro papel, em nenhuma circunstância. **[R]** |
| **RN-R03** | A liberação exige conferência registrada de: integridade da embalagem, validade mínima (RN-L07), nota fiscal e — se termolábil — temperatura de chegada. |
| **RN-R04** | Divergência entre nota e físico não impede o recebimento; gera pendência vinculada ao recebimento. |
| **RN-R05** | Recebimento de controlado exige dupla identificação: conferente **e** RT. **[R][S]** |

### 5.4 Movimentação e saldo — `RN-M`

| ID | Regra |
|---|---|
| **RN-M01** | Saldo **nunca** fica negativo. Movimento que resultaria em negativo é rejeitado. |
| **RN-M02** | Movimento é **imutável**. Não pode ser editado nem excluído por ninguém, em nenhum papel. |
| **RN-M03** | Correção se faz por movimento de **estorno**, que referencia o original e exige motivo. |
| **RN-M04** | Todo movimento grava: autor, data/hora do servidor, unidade, lote, quantidade, tipo e motivo. |
| **RN-M05** | Motivo vem de lista fechada por tipo de movimento; texto livre é complemento, nunca substituto. |
| **RN-M06** | O saldo de um lote é sempre a soma dos seus movimentos. Não existe campo de saldo editável. |

### 5.5 Controlados — `RN-C`

| ID | Regra |
|---|---|
| **RN-C01** | Toda movimentação de controlado exige **duas identificações**: o operador e o RT. **[R][S]** |
| **RN-C02** | Ajuste de saldo de controlado exige, além das duas identificações, motivo e documento anexo. **[R]** |
| **RN-C03** | Controlado não entra em contagem cíclica comum: tem contagem própria, com periodicidade e registro separados. **[R]** |
| **RN-C04** | Divergência em controlado, de qualquer valor, escala direto para RT **e** Diretor. Não há alçada de gerente. **[R]** |
| **RN-C05** | O sistema mantém livro de registro eletrônico de controlados, exportável e imutável. **[R]** |

### 5.6 Cadeia fria — `RN-F`

| ID | Regra |
|---|---|
| **RN-F01** | Recebimento de termolábil exige registro da temperatura de chegada da carga. **[R]** |
| **RN-F02** | Temperatura fora da faixa 2–8 °C mantém o lote em quarentena com bloqueio; só o RT decide o destino. **[R]** |
| **RN-F03** | A unidade refrigerada registra temperatura em intervalo fixo, e o histórico é consultável por período. **[R]** |
| **RN-F04** | Excursão de temperatura registrada gera ocorrência vinculada aos lotes presentes na unidade no período. **[R]** |

### 5.7 Inventário e ajuste — `RN-I`

| ID | Regra |
|---|---|
| **RN-I01** | **Quem conta não aprova.** O aprovador tem de ser pessoa diferente do contador. **[S]** |
| **RN-I02** | Divergência de até **R$ 5.000** em valor absoluto: aprova o gerente da unidade. **[C]** |
| **RN-I03** | Divergência acima de **R$ 5.000**: aprova o Diretor. **[C]** |
| **RN-I04** | Divergência em controlado: RN-C04 prevalece sobre RN-I02 e RN-I03. **[R]** |
| **RN-I05** | Nenhum ajuste ocorre sem contagem aprovada por trás. Não existe ajuste avulso. |
| **RN-I06** | Todo ajuste exige motivo de lista fechada: `avaria`, `furto`, `erro de separação`, `erro de recebimento`, `vencimento`, `erro de contagem anterior`. |
| **RN-I07** | Contagem cíclica é por endereço ou por curva ABC. Curva A conta mensalmente; B, trimestralmente; C, semestralmente. |
| **RN-I08** | Contagem em rascunho pode ser descartada pelo autor. A partir de **Contada**, não pode mais. |

### 5.8 Transferência — `RN-T`

| ID | Regra |
|---|---|
| **RN-T01** | Transferência é sempre **dois movimentos ligados**: saída na origem e entrada no destino. |
| **RN-T02** | Entre a saída e a entrada, a mercadoria fica **Em trânsito** e não é vendável em nenhuma unidade. |
| **RN-T03** | O lote mantém sua identidade na transferência: número, validade e fabricação não mudam. |
| **RN-T04** | Divergência no recebimento da transferência gera pendência para os gerentes das **duas** unidades. |
| **RN-T05** | Transferência de controlado exige autorização do RT na origem e no destino. **[R]** |

### 5.9 Acesso — `RN-A`

| ID | Regra |
|---|---|
| **RN-A01** | Todo usuário é vinculado a uma ou mais **unidades**. Só enxerga saldo, movimento, contagem e recebimento das unidades às quais está vinculado. |
| **RN-A02** | **Custo e margem** são campos restritos. Visíveis apenas para Diretor, Comprador e Auditoria. **[C]** |
| **RN-A03** | Permissão é verificada **no servidor, a cada operação**. A interface esconde o que o usuário não pode fazer, mas esconder não é controlar. |
| **RN-A04** | Nenhum papel acumula contar e aprovar a própria contagem, nem em situação de falta de pessoal. **[S]** |
| **RN-A05** | O RT pode designar um **substituto** por período determinado, registrado e auditado. Fora desse período, o substituto não tem os poderes do RT. **[R]** |
| **RN-A06** | Usuário não é excluído, é **desativado** — a trilha de auditoria precisa continuar resolvendo o nome. |
| **RN-A07** | Mensagem de erro por falta de permissão não revela a existência nem o conteúdo do registro negado. |

### 5.10 Auditoria e rastreabilidade — `RN-D`

| ID | Regra |
|---|---|
| **RN-D01** | Toda operação de escrita gera registro de auditoria: quem, o quê, quando, valor anterior, valor novo, origem. |
| **RN-D02** | O registro de auditoria é **imutável e não excluível**, inclusive para o Diretor. |
| **RN-D03** | Dado um número de lote, o sistema lista todos os clientes que o receberam, com nota e data. **[R]** |
| **RN-D04** | Dado um cliente e um período, o sistema lista todos os lotes que ele recebeu. **[R]** |
| **RN-D05** | Consulta de auditoria é ela própria auditada — ver quem consultou o quê importa. |

---

## 6. Matriz de permissões

`C` criar · `L` ler · `E` editar · `X` excluir · `A` ação especial · `—` sem acesso

| | Diretor | RT | Gerente | Conferente | Comprador | Auditoria |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Produto** | C L E | L | L | L | C L E | L |
| **Produto — inativar** | A | — | — | — | A | — |
| **Custo e margem** | L | — | — | — | L | L |
| **Lote** | L | L | L | L | L | L |
| **Lote — liberar quarentena** | — | **A** | — | — | — | — |
| **Lote — bloquear/desbloquear** | — | **A** | — | — | — | — |
| **Lote — liberar vencimento ≤30d** | — | **A** | — | — | — | — |
| **Recebimento** | L | L A | C L | C L | L | L |
| **Movimento — saída** | L | L | C L | C L | — | L |
| **Movimento — descarte** | L A | A | C L | — | — | L |
| **Movimento — estorno** | A | A | A | — | — | L |
| **Controlado — movimentar** | — | **A** | — | C* | — | L |
| **Controlado — autorizar** | — | **A** | — | — | — | L |
| **Contagem** | L | L | C L | C L | — | L |
| **Contagem — aprovar ≤ R$5.000** | A | — | A | — | — | — |
| **Contagem — aprovar > R$5.000** | **A** | — | — | — | — | — |
| **Transferência** | L | L A** | C L A | C L | — | L |
| **Pedido de compra** | L A | — | L | — | C L E | L |
| **Usuário e permissão** | C L E | — | — | — | — | L |
| **Trilha de auditoria** | L | L | — | — | — | **L** |

\* Conferente inicia a movimentação de controlado, que só se efetiva com autorização do RT (RN-C01).
\*\* RT autoriza transferência de controlado (RN-T05).

### Escopo por unidade

| Usuário | Unidades |
|---|---|
| Marco (Diretor) | Todas |
| Helena (RT) | Todas |
| Ivo (Gerente) | CD Matriz, CD Refrigerado |
| Odair (Gerente) | Filial Uberlândia |
| Cleide (Conferente) | CD Matriz, CD Refrigerado |
| Rafael (Comprador) | Todas — somente leitura de saldo |
| Sandra (Auditoria) | Todas — somente leitura |

---

## 7. Regras de CRUD por entidade

O que pode e o que não pode ser apagado é, aqui, uma regra de negócio — não uma
decisão técnica.

| Entidade | Criar | Ler | Atualizar | Excluir |
|---|---|---|---|---|
| **Produto** | Sim | Sim | Sim | **Não** se houver movimento — inativa (RN-P04) |
| **Lote** | Só por recebimento | Sim | Só status e endereço | **Nunca** |
| **Movimento** | Sim | Sim | **Nunca** (RN-M02) | **Nunca** — usa estorno (RN-M03) |
| **Recebimento** | Sim | Sim | Até a liberação | Só em rascunho |
| **Contagem** | Sim | Sim | Até `Contada` | Só em `Rascunho` (RN-I08) |
| **Transferência** | Sim | Sim | Até `Em trânsito` | Só em `Solicitada` |
| **Pedido de compra** | Sim | Sim | Até o envio | Só em rascunho |
| **Usuário** | Sim | Sim | Sim | **Não** — desativa (RN-A06) |
| **Auditoria** | Automático | Sim | **Nunca** | **Nunca** (RN-D02) |

---

## 8. Requisitos não funcionais

| ID | Requisito |
|---|---|
| **RNF-01** | Rastreamento de recall (RN-D03) responde em **menos de 60 segundos**. |
| **RNF-02** | Operação de conferência funciona com leitor de código de barras e uma mão — sem digitação obrigatória. |
| **RNF-03** | A filial de Uberlândia perde conexão. Conferência e contagem precisam tolerar queda e sincronizar depois. |
| **RNF-04** | Nenhuma tela de operação exige mais de 2 segundos para responder em uso normal. |
| **RNF-05** | Implantação sem parar a operação. Sem inventário geral de três dias. |
| **RNF-06** | Registro de temperatura mantido por **5 anos**, consultável por período. **[R]** |

---

## 9. Critérios de aceite

Cada critério existe por causa de um episódio concreto do documento 1.

| ID | Critério | Origem |
|---|---|---|
| **CA-01** | Dado um número de lote, obter a lista de clientes que o receberam em menos de 60 s | Recall da losartana, 9 dias |
| **CA-02** | Nenhum saldo muda sem movimento com autor e motivo recuperáveis | Divergência de 3,8% |
| **CA-03** | Fila de vencimento mostra tudo que vence em 90 dias, por unidade, sem planilha | R$ 183 mil vencidos |
| **CA-04** | Nenhuma movimentação de controlado se conclui com uma identificação só | Blister de clonazepam |
| **CA-05** | Custo é invisível para RT, Gerente e Conferente — inclusive em exportação e na resposta do assistente | Vazamento de margem |
| **CA-06** | Odair não obtém saldo, contagem ou movimento de Ribeirão Preto por nenhum caminho | Pedido do cliente |
| **CA-07** | Histórico de temperatura da câmara fria é consultável por período e exportável | Auto de infração da ANVISA |
| **CA-08** | Tentativa de excluir movimento é recusada para todos os papéis, incluindo Diretor | RN-M02 |

---

## 10. Em aberto

Decisões que dependem do cliente e ainda não foram tomadas:

1. Contagem cíclica por endereço ou por curva ABC — RN-I07 propõe ABC, falta confirmar.
2. O substituto do RT (RN-A05) é papel fixo ou designação por período? Assumido: por período.
3. Devolução de cliente volta para quarentena ou para bloqueio direto? Assumido: quarentena.
4. Limite de R$ 5.000 (RN-I02) é por item ou por contagem inteira? Assumido: por contagem.
5. Uberlândia off-line (RNF-03) — qual o comportamento se dois usuários contarem o mesmo endereço sem conexão?
