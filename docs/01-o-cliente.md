# Bertoni Distribuidora Farmacêutica

**Documento 1 — O cliente**
Empresa fictícia, criada para servir de caso real a esta POC. Nenhum dado
corresponde a pessoa ou organização existente.

---

## Ficha

| | |
|---|---|
| Razão social | Bertoni Distribuidora Farmacêutica Ltda. |
| CNPJ | 04.812.663/0001-27 *(fictício)* |
| Sede | Ribeirão Preto — SP |
| Fundação | Março de 1998 |
| Porte | Médio — R$ 96 milhões de faturamento anual |
| Funcionários | 87 |
| AFE / ANVISA | 3.04.812-6 *(fictícia)* |
| Autorização Especial | Sim — medicamentos sujeitos à Portaria 344/98 |
| SKUs ativos | ≈ 4.200 |
| Clientes | 610 farmácias independentes, 44 clínicas, 7 hospitais de pequeno porte |
| Região | Interior de São Paulo e Triângulo Mineiro |

### Unidades

| Unidade | O que guarda |
|---|---|
| **CD Matriz — Ribeirão Preto/SP** | Estoque seco. Inclui sala-cofre para controlados |
| **CD Refrigerado — Ribeirão Preto/SP** | Termolábeis entre 2 °C e 8 °C: vacinas, insulinas, biológicos |
| **Filial Uberlândia/MG** | Estoque seco. Atende o Triângulo Mineiro |

---

## A história

Aparecido Bertoni era farmacêutico de balcão em Ribeirão Preto. Em 1998, cansado
de esperar três dias por uma caixa de antibiótico que vinha de São Paulo, comprou
uma Kombi e começou a entregar para os colegas da região. A tese era simples:
farmácia independente não consegue comprar direto da indústria, e o distribuidor
grande não liga para quem compra pouco.

Deu certo. Em 2006 a Kombi virou seis caminhões e um galpão alugado na via Anhanguera.
Em 2011 veio a sala-cofre e a autorização para trabalhar com controlados — o que
dobrou o ticket médio, porque farmácia que compra controlado compra o resto junto.
Em 2016, a câmara fria, para entrar em vacinas.

Aparecido morreu em 2019. Os dois filhos assumiram: **Marco**, que cuidava do
comercial desde 2009, e **Helena**, farmacêutica, que voltou de São Paulo para
assumir a responsabilidade técnica.

Herdaram um negócio saudável e um controle que nunca foi refeito desde 2004.

---

## Como a empresa opera hoje

O ERP — instalado em 2004, mantido por um analista que atende remoto — cuida de
nota fiscal, financeiro, faturamento e comissão. Funciona. Ninguém quer mexer.

O que ele **não** faz é controlar estoque de verdade. Ele tem um campo de saldo
por produto, e só. Não conhece lote, não conhece validade, não conhece endereço
no depósito, não conhece unidade.

O resto vive fora dele:

- **Validade** — uma planilha que a Cleide atualiza às sextas. Foi criada em 2013.
- **Endereçamento** — etiquetas nas prateleiras e a memória do Ivo.
- **Controlados** — livro de registro físico, escrito à mão, guardado na sala da Helena.
- **Temperatura da câmara fria** — datalogger que imprime um rolo térmico, arquivado numa caixa.
- **Transferência entre unidades** — WhatsApp entre o Ivo e o Odair, com foto do romaneio.
- **Contagem** — inventário geral uma vez por ano, três dias com a operação parada.

> "A gente sabe o que tem. O problema é que a gente sabe de cabeça, e cabeça não
> passa em auditoria."
> — **Ivo Salgado**, gerente do CD Matriz

---

## O que quebrou

Quatro episódios, em ordem cronológica. São eles que estão pagando pelo projeto.

### 1. R$ 183 mil vencidos — dezembro de 2024

O fechamento do ano encontrou R$ 183 mil em produto vencido na prateleira. O maior
item: 900 frascos de amoxicilina suspensão que passaram da validade dentro do CD,
enquanto a empresa comprava mais do mesmo item.

A planilha de validade existia. Estava desatualizada em cinco semanas.

### 2. Inventário com 3,8% de divergência — janeiro de 2025

O inventário geral fechou com 3,8% de divergência em valor — cerca de R$ 340 mil
entre sobras e faltas. A contabilidade pediu explicação item a item.

Não havia explicação. Os ajustes eram digitados direto no ERP, sem motivo, sem
autor, sem data confiável. A empresa descobriu que qualquer um dos quatro usuários
com acesso ao módulo de estoque podia zerar um saldo e ninguém saberia.

### 3. Recall de losartana — março de 2025

O fabricante recolheu um lote de losartana 50 mg. A Bertoni precisava dizer para
quais farmácias vendeu aquele lote.

Levou **nove dias**. Duas pessoas cruzando notas fiscais em PDF com o romaneio de
separação, para reconstruir uma informação que o sistema nunca guardou — porque o
sistema nunca soube qual lote saiu em qual venda.

A ANVISA espera esse rastreamento em 72 horas.

### 4. O blister de clonazepam — abril de 2025

Uma contagem de controlados acusou uma cartela a menos de clonazepam. Erro de
contagem ou desvio, não há como saber: a movimentação de controlado era registrada
à mão, no fim do dia, por uma pessoa só.

Helena teve que notificar. O processo ainda corre.

> "Meu CRF está no papel. Se sumir um comprimido de controlado eu não posso dizer
> 'acho que foi erro de contagem'. Eu preciso provar. Hoje eu não consigo provar nada."
> — **Dra. Helena Bertoni**, farmacêutica responsável

### E ainda: o vazamento de margem — 2023

Um vendedor com acesso à tela de custo do ERP levou a tabela de margem para um
concorrente ao sair. Desde então, Marco desconfia de qualquer tela que mostre preço
de compra.

---

## A inspeção

Em **maio de 2025**, a ANVISA inspecionou a unidade de Ribeirão Preto. O auto de
infração apontou dois itens:

1. Ausência de registro sistemático e recuperável do controle de temperatura da
   câmara fria — o rolo térmico na caixa não foi aceito como registro.
2. Inconsistência entre o livro de registro de controlados e o saldo físico.

Há prazo para adequação. É isso que transformou "um dia a gente arruma o estoque"
em um projeto com orçamento aprovado.

---

## Quem é quem

Sete pessoas usam o sistema. Elas não têm os mesmos direitos, e as diferenças não
são preferência de gestão — são separação de funções, exigência regulatória e
proteção de informação comercial.

### Marco Bertoni — Diretor
Sócio-administrador. Vê tudo, inclusive custo e margem. Aprova ajustes de inventário
acima de R$ 5.000. Não opera estoque, e não quer operar.

> "Eu não quero aprender onde fica cada relatório. Quero perguntar 'quanto tem de
> losartana vencendo em 60 dias' e ver a resposta. Se pra isso eu tiver que abrir
> dez telas, eu não vou abrir."

### Dra. Helena Bertoni — Farmacêutica Responsável (RT)
CRF-SP 41.882 *(fictício)*. É ela, legalmente, quem responde pelo que sai daqui.
Única pessoa que libera lote da quarentena e que autoriza movimentação de controlado.
**Não tem acesso a custo nem margem** — decisão dela própria, para que a avaliação
técnica nunca tenha um número comercial do lado.

### Ivo Salgado — Gerente do CD Matriz
23 anos de casa. Opera o dia a dia de Ribeirão Preto, seco e refrigerado. Aprova
divergência de contagem até R$ 5.000. Não vê custo. Vê quantidade, lote, validade
e endereço.

### Odair Pimentel — Gerente da Filial Uberlândia
Mesmas atribuições do Ivo, **restrito à unidade de Uberlândia**. Não deve enxergar
saldo, contagem ou movimentação de Ribeirão Preto.

### Cleide Moura — Conferente
Recebe carga, confere, endereça, separa e conta. É quem mais usa o sistema.
Registra contagem, **mas não aprova a própria contagem**. Não vê custo.

### Rafael Tanaka — Comprador
Vê custo, histórico de compra e curva de consumo. Cria pedido de compra.
**Não movimenta estoque** — não recebe, não ajusta, não transfere.

### Sandra Lopes — Auditoria e Contabilidade
Enxerga tudo, inclusive custo e a trilha de auditoria completa. **Não altera nada.**
Leitura pura, por definição do cargo.

---

## O que eles pediram

Nas palavras deles, na reunião de abertura:

1. "Saber o que eu tenho, de qual lote, vencendo quando, em qual unidade."
2. "Que ninguém mexa em saldo sem deixar rastro e sem dizer por quê."
3. "Que a Helena seja a única a liberar o que precisa da assinatura dela."
4. "Que o Odair não veja o estoque de Ribeirão, e vice-versa."
5. "Que custo só apareça pra quem precisa de custo."
6. "Se der recall de novo, eu quero a lista de clientes no mesmo dia."
7. "E eu quero poder perguntar, não caçar relatório."

## O que não está em jogo

O ERP fica. Nota fiscal, financeiro, faturamento, contas a receber e comissão
continuam lá. O sistema novo cuida do estoque físico e conversa com o ERP por
importação e exportação de arquivo.

Trocar o ERP é uma discussão de 2027, e não é esta.

## Restrições

- Orçamento aprovado para o primeiro ciclo: **R$ 240 mil**.
- Prazo para atender à adequação da ANVISA: **fim do primeiro semestre**.
- O CD trabalha das 6h às 20h. Implantação não pode parar a operação — o
  inventário geral de três dias parados não se repete.
- Cleide e a equipe de conferência usam coletor de código de barras. Boa parte da
  operação é feita em pé, com uma mão.
- A internet da filial de Uberlândia cai. Não é uma hipótese, é uma terça-feira.
