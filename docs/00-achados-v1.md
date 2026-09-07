# Achados da POC v1

**Documento 0 — histórico.** Resultado da primeira POC (UI generativa por schema,
domínio de logística), construída e descartada antes da v2. O código está em
`.archive/v1-ui-generativa-backup.tar.gz`; a demo continua no ar como artifact.

Escrito depois de construir. O objetivo era testar a hipótese, não confirmá-la —
então os itens que **não** se sustentaram estão aqui com o mesmo destaque dos que
se sustentaram.

---

## Antes de tudo: o que esta POC ainda NÃO respondeu

Este é o item mais importante do documento.

**O caminho do Claude real foi escrito, tipado e compilado, mas nunca executado.**
Não havia `ANTHROPIC_API_KEY` no ambiente. Tudo que foi medido abaixo passou pelo
parser mockado, que eu escrevi — ou seja, ele acerta porque eu ensinei ele a
acertar. Isso valida a arquitetura e **não diz absolutamente nada** sobre a
pergunta que mais importa para adotar isso em produção:

> Um modelo real emite schemas válidos com que frequência?

Enquanto essa pergunta estiver aberta, as demais conclusões são sobre encanamento,
não sobre viabilidade. Para fechá-la: `export ANTHROPIC_API_KEY=...`, `npm run dev`,
trocar o adaptador para "Claude (API real)" no painel do assistente, rodar as cinco
perguntas sugeridas e ler a aba Execution Trace. A linha `validation` mostra
aceitos vs. rejeitados; é esse número que decide.

Também continuam em aberto:

- **Latência real.** Os 749–1044 ms medidos são latência simulada do repositório
  (200–500 ms por chamada, duas rodadas sequenciais). Não há um modelo no caminho.
- **Escala do catálogo.** Testado com 7 componentes. Ver a conta abaixo.
- **Injeção de prompt.** Um nome de carga ou uma observação de viagem vinda do banco
  pode conter instruções para o modelo. Nada nesta POC testa isso.
- **Cobertura.** Se o L2 responde 60% ou 95% das perguntas reais de um operador é
  desconhecido — o mock só responde o que eu já sabia perguntar.

---

## O que se sustentou

### 1. Orquestração fora do React funciona, e dá para provar

`scripts/smoke.ts` roda o fluxo inteiro — intenção, task, query, repositório, view
model, schema, validação, estado resolvido — **em Node, sem DOM e sem renderizar
nada**. Não é um detalhe de teste: se a orquestração morasse nos componentes,
nada disso seria alcançável assim.

O mecanismo é um store observável comum (`src/state/store.ts`, 40 linhas) lido por
`useSyncExternalStore`. O fluxo nasce de um evento do usuário, não de um ciclo de
render.

### 2. Zero `useEffect`, e verificado

| | |
|---|---|
| `useEffect` no `src/` | **0** |
| `useState` | 3 — todos estado local de input/UI |
| `useCallback`/`useMemo` | 2 — ambos dentro de `useStore` |

`npm run arch:check` falha o build se um `useEffect` aparecer, se um componente
importar a camada de dados, ou se alguém importar os fixtures fora de `data/`.
As regras foram **testadas negativamente**: introduzi as três violações de
propósito e confirmei que o check quebra. Uma regra que nunca falhou não é
evidência de nada.

### 3. Uma entidade, uma cópia

Ao final do smoke há 19 referências a viagens espalhadas por 6 composições, e
**6 objetos de viagem** no store. Composições referenciam por id; promover uma
resposta do chat para o workspace aponta para o mesmo objeto, não copia.

### 4. O registry é uma fronteira de segurança real

Testado com entrada hostil:

| Entrada | Resultado |
|---|---|
| `{"type": "RandomReactComponent"}` | rejeitado, componente não registrado |
| `{"type": "<script>alert(1)</script>"}` | rejeitado |
| `metric_card` com `metric: "lucro_do_trimestre"` | rejeitado, fora do enum |
| `layout: "display:grid;grid-template-columns:1fr 1fr"` | rejeitado, fora do enum |

O schema não tem onde carregar código: não existe campo para markup, estilo ou
dado. Isso é uma propriedade da estrutura, não uma promessa do prompt.

### 5. Economia de tokens é real e grande

| | tokens |
|---|---|
| Schema de uma tela de 3 componentes | **~60** |
| Schema de um panorama de 6 componentes | ~123 |
| Um componente React equivalente, gerado | ~800–2000 |

É uma ordem de grandeza. É daqui que sai a diferença entre "a tela aparece" e
"a tela é digitada na sua frente".

### 6. O registry como fonte única funcionou melhor do que eu esperava

Registrar um componente produz, de uma declaração só: o validador, a descrição
enviada ao modelo, a carga de dados, a projeção pura e o componente React. Não
existe uma segunda lista para esquecer de atualizar — que é como esses sistemas
normalmente apodrecem.

### 7. React ficou fino de verdade

`src/components/` são **280 linhas em 8 arquivos** — 7,4% do código. Nenhum
componente busca dado, decide regra ou lê store.

Ressalva honesta: um app React comum com Zustand + TanStack Query também teria
componentes finos. Esse número impressiona menos do que parece.

---

## O que custou, e que ninguém menciona

### 1. Sem `useEffect`, o cleanup dele vira problema seu

Abrir a viagem A e imediatamente a B faz duas requisições concorrentes. O
`useEffect` cancelaria a primeira de graça. Aqui foi preciso escrever
invalidação por token de slot (`claimSlot`, em `src/state/store.ts`) e lembrar de
checá-la depois de **todo** `await`. Está testado no cenário 5 do smoke — e é
exatamente o tipo de coisa que alguém esquece na terceira feature.

### 2. Coalescing teve que ser escrito à mão

Quatro componentes da mesma viagem disparavam quatro consultas idênticas.
`src/application/inflight.ts` resolve compartilhando promessas em voo. É o que
TanStack Query dá de graça.

### 3. O schema custa type safety

No momento em que a composição vira JSON, o TypeScript para de checar props.
`src/schema/validate.ts` compra isso de volta em runtime com Zod — 130 linhas
que só existem por causa dessa fronteira.

### 4. O contrato `load` / `select` é incomum

Separar "carrega para o store" de "projeta puro na render" é o que mantém o React
fora do fetching. Também é uma convenção que ninguém conhece e que precisa ser
ensinada a todo desenvolvedor novo. Não é gratuito.

### 5. O modelo não pode decidir layout

Tentei deixar `grid` decidir a largura dos componentes. Uma tabela num tile de
200px fica ilegível. A solução foi cada componente **declarar seu próprio
tamanho** (`size: 'tile' | 'block'`), e o layout engine obedecer ao componente,
não ao modelo. Regra geral que sai daqui: *o modelo escolhe o que mostrar; o
front-end decide como aquilo se parece.* Quando essa linha é cruzada, quebra.

### 6. O catálogo é o teto do que pode ser perguntado

Encontrado em uso, não em teste. Pedir *"liste as viagens programadas"* devolvia
**a lista inteira**. A causa não era o dado mockado nem o parser: o
`entity_table` só aceitava `all | delayed | in_transit | available`. "Programada"
não existia no vocabulário, então o assistente caía no caso genérico e respondia
uma pergunta mais larga — silenciosamente, com cara de resposta certa.

Essa é a falha mais perigosa desta arquitetura, porque **não parece uma falha**.
Um componente não registrado é rejeitado no gate e aparece no trace. Um *filtro*
que falta simplesmente amplia a resposta. Ninguém percebe até um cliente
perguntar por que a contagem está errada.

Duas medidas saíram daí:

- Os filtros passaram a cobrir todos os status do domínio, declarados por
  entidade (`FILTERS_BY_ENTITY`).
- O gate ganhou validação cruzada: `drivers` + `maintenance` agora é **rejeitado**
  com mensagem, em vez de degradar para "todos". Combinação sem sentido vira erro
  visível.

Regra que fica: **todo recorte que o usuário sabe pedir precisa existir no
catálogo como um valor nomeado.** Auditar isso é trabalho contínuo, não uma
tarefa de setup.

### 7. Identidade da view ≠ identidade da renderização

Outro bug de uso: favoritar duplicava, e a estrela voltava apagada ao reabrir a
tela. A causa é conceitual — o favorito estava chaveado no id da *composição*,
que é criado a cada renderização. Reabrir a mesma viagem gerava id novo: a
estrela lia "não favoritado" e favoritar de novo criava uma segunda entrada.

Favoritar é sobre a **view**, não sobre uma execução dela. A chave passou a ser
derivada do schema (`viewKey`), o que também deixou reabrir um favorito
recarregar os dados em vez de mostrar um retrato antigo.

Vale registrar porque é uma armadilha embutida no modelo: quando a UI é composta
dinamicamente, "a mesma tela" deixa de ter um id óbvio, e qualquer coisa que
precise lembrar de uma tela — favoritos, histórico, permissões, telemetria —
precisa de uma noção explícita de identidade de view. Sistemas baseados em rota
ganham isso de graça na URL.

### 8. O catálogo cresce no prompt, toda requisição

7 componentes = **1.147 tokens**, ou ~164 tokens por componente.

Extrapolando: 30 componentes ≈ 5k tokens; 60 componentes ≈ 10k tokens **em toda
pergunta**. Isso não escala por adição. Um sistema real precisará de recuperação
de catálogo (buscar só os componentes relevantes à pergunta) antes de passar de
~25 componentes. Não implementei — mas é o primeiro muro.

---

## O que foi cortado do desenho original, e por quê

| Cortado | Motivo |
|---|---|
| **Context Engine** | Era o Session State com outro nome. Mantê-lo criaria a duplicação de estado que a própria proposta proibia. Context virou projeção derivada. |
| **Task Engine** | Absorvido por `application/actions.ts`. Uma indireção que só renomeava chamadas de função. |
| **Layout Engine** | Virou `src/render/Layout.tsx`, 62 linhas. Continua útil; o nome é que era inflado. |
| **Escada de 10 camadas** | Sobraram 7 diretórios com responsabilidades distintas. As três removidas não deixaram buraco. |

---

## Veredito

**A parte que não vale a pena copiar:** o store fora do React. Funciona, mas
Zustand e TanStack Query entregam o mesmo com menos código seu e com o cleanup e
o coalescing já resolvidos. Se o objetivo fosse só "menos `useEffect`", esta POC
seria trabalho desnecessário.

**A parte que vale:** o eixo **Registry → catálogo → validação → composição**.
É aqui que está a coisa genuinamente diferente, e é a única parte que eu levaria
para um projeto real sem hesitar. O registry como fonte única de verdade e o gate
de validação são baratos de construir e resolvem problemas que não têm outra
solução pronta.

**Recomendação:**

1. Use isto na **superfície do assistente**, não no app inteiro. Telas normais
   continuam telas normais, chamando endpoints normais.
2. Comece por **L1 (roteamento)**: o modelo escolhe uma view pronta e seus
   parâmetros. Cobre a maior parte das perguntas, é instantâneo e trivialmente
   seguro.
3. Suba para **L2 (composição)** só onde L1 não bastar — comparações,
   panoramas sob demanda, respostas que misturam entidades.
4. Nunca deixe o modelo produzir dados. `metric_card` recebe *qual* indicador,
   não o número. Se um componente aceitar valores literais do modelo, um número
   alucinado renderiza tão convincente quanto um verdadeiro.
5. `text_block` é o único ponto onde texto do modelo chega à tela, e é o elo mais
   fraco desta POC. A descrição proíbe afirmar números, mas nada **impede**.
   Em produção, ou remova, ou valide contra os dados carregados.

**A pergunta que decide tudo** continua sendo a do topo deste documento. Rode com
a API key antes de comprometer um projeto real com essa arquitetura.
