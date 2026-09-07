# Arquitetura v2

**Documento 3 — decisões técnicas.**
Escrito para ser lido sem contexto anterior. Se você está começando agora, leia
o [documento 00](./00-achados-v1.md) depois deste, para saber o que já foi medido.

---

## 1. De onde isto vem

A **v1** foi uma POC que testou uma hipótese: dá para ter uma IA compondo a
interface em tempo real — como o Claude faz no chat — **sem** deixá-la escrever
código?

O Claude gera React arbitrário e roda num iframe isolado. Nem a Anthropic confia
nesse código: ele fica numa origem separada, sem acesso a dados. Para software
com dados reais e permissão, isso não serve.

A v1 provou que o caminho alternativo funciona: o modelo emite **~60 tokens de
JSON** dizendo *quais componentes registrados compor*, o sistema valida contra um
allow-list e renderiza com os componentes da casa.

> O modelo escolhe a composição. Nunca o código, nunca os dados, nunca a
> autorização.

A v1 era **100% leitura** e **sem autenticação nenhuma**. A v2 existe para
responder o que ficou de fora: **escrita (CRUD) e permissão de verdade.**

---

## 2. A regra central

> **A saída do modelo autoriza renderizar. Nunca autoriza escrever.**

Dois planos, separados:

```
PLANO DE RENDER     modelo → schema (nomes + params) → valida → desenha
PLANO DE ESCRITA    humano → submit → endpoint autenticado → domínio → banco
```

O modelo vive inteiro no primeiro. Ele pode pedir *"mostre o formulário de ajuste
do lote L-8842"* — isso é render. Quem grava é a pessoa clicando em salvar,
passando pelo mesmo endpoint autenticado que a tela tradicional usa.

**Renderizar um formulário não é escrever.** É essa distinção que torna CRUD
viável sem entregar o banco ao modelo.

---

## 3. Os três níveis, e qual usar quando

| Nível | O modelo produz | Uso |
|---|---|---|
| **L1 — Roteamento** | uma view registrada + parâmetros | ~70% dos casos. Instantâneo, trivialmente seguro |
| **L2 — Composição** | schema compondo vários componentes registrados | panoramas sob demanda, comparações, respostas que misturam entidades |
| **L3 — Código** | JSX/HTML arbitrário em sandbox | só quando o artefato **é** o entregável. Fora deste projeto |

### A regra prática

> **L2 para leitura. L1 para escrita.**

Consultar, comparar, montar panorama → o modelo compõe à vontade.

Fluxo com várias etapas, validação cruzada, wizard → registre como **uma unidade
inteira**. O modelo escolhe qual formulário abrir; ele não monta formulário
peça por peça. Compor formulário complexo por schema é onde isto quebra, e não
vale a briga.

---

## 4. O contrato de componente

Fonte única de verdade. Registrar um componente produz, de uma declaração só: o
validador, a descrição que o modelo recebe, a carga de dados, a projeção pura, o
componente React e as operações de escrita.

```ts
defineComponent({
  id: 'lote_ajuste_form',
  label: 'Ajuste de lote',
  description:
    'Formulário de ajuste de saldo de um lote. Use quando o usuário quiser ' +
    'corrigir quantidade. Exige contagem aprovada — ver RN-I05.',
  examples: ['ajustar o lote L-8842', 'corrigir saldo da amoxicilina'],
  params: z.object({ loteId: z.string(), contagemId: z.string() }),

  // ---- plano de render ----
  load,                      // busca — autorizada no servidor
  select,                    // projeção pura, roda no render
  render: LoteAjusteForm,

  // ---- plano de escrita ----
  // O modelo NÃO passa por aqui. Só o humano dispara, e o servidor reconfere.
  commands: {
    aplicar: {
      endpoint: 'POST /lotes/:id/ajustes',
      schema: AjusteInput,          // validação de domínio, não de UI
      requires: 'ajuste.aplicar',
      confirm: true,
      idempotent: true,
    },
  },
})
```

`requires` faz **duas** coisas, e as duas importam:

1. Filtra o catálogo na geração — quem não pode ajustar nunca vê esse componente
   no vocabulário do modelo.
2. É reconferido no servidor a cada chamada.

Permissão nunca depende do modelo.

---

## 5. Catálogo servido por usuário

Na v1 o catálogo era uma constante no cliente. Na v2 ele é **gerado no servidor,
por requisição, filtrado pelas permissões e pelas unidades do usuário**.

Consequências, usando os papéis do [documento 02](./02-regras-de-negocio.md):

- Cleide (conferente) não tem `custo.ler` → nenhum componente que exponha custo
  entra no catálogo dela → o modelo não consegue nem propor.
- Odair (gerente, Uberlândia) tem escopo de unidade → componentes vêm com o
  escopo já aplicado; pedir Ribeirão não retorna vazio, retorna negado.
- Helena (RT) é a única com `lote.liberar` → só o catálogo dela contém o
  componente de liberação de quarentena.

Isso resolve o problema que a v1 tinha e não sabia: **o modelo oferecendo o que a
pessoa não pode ter.**

---

## 6. Permissão em três momentos

| Quando | O quê | Protege contra |
|---|---|---|
| **Antes do modelo** | monta o catálogo filtrado pelo usuário | o modelo propor o impossível |
| **Depois do modelo** | revalida o schema no servidor contra o mesmo catálogo | alucinação e requisição forjada |
| **Em cada `load` e cada `command`** | autoriza por registro, com a identidade real | **acesso indevido de fato** |

Os dois primeiros são higiene: controlam o que é *oferecido*. **O terceiro é o
único que protege**, porque controla o que é *acessível*.

### O detalhe que decide

**O cliente pode montar um schema à mão e enviar direto**, sem passar pelo modelo.
Então o servidor trata schema como payload não-confiável, igual a qualquer outro
body de API. Validar só no momento em que o assistente responde é proteger o
caminho errado.

### Inegociáveis

1. Autorização no servidor a cada carga e a cada comando — nunca só na tela.
2. O modelo nunca escolhe dado. Ele escolhe *qual pergunta fazer*.
3. Nenhum número de autoria do modelo na tela. Componente que aceitasse valor
   literal renderizaria alucinação com a mesma cara de verdade.
4. Catálogo filtrado por usuário.
5. Log de auditoria de tudo que o assistente mostrou, para quem, quando —
   `RN-D05` exige que a própria consulta seja auditada.
6. Rate limit por usuário. Cada pergunta custa tokens.
7. Erro de permissão não revela existência nem conteúdo do registro negado
   (`RN-A07`).

> **Correção herdada da v1:** o `NotFoundError` da v1 listava os ids disponíveis
> para o modelo se recuperar sozinho. Isso vaza existência de registro. Erro bom
> para o modelo e erro seguro conflitam aqui — decidir caso a caso, com
> consciência de acesso.

---

## 7. CRUD, operação por operação

| | Quem decide mostrar | Quem executa | Autorização |
|---|---|---|---|
| **Read** | modelo (compõe) | `load` do componente | servidor, por registro e por unidade |
| **Create** | modelo (mostra form `mode=create`) | humano no submit | servidor, no command |
| **Update** | modelo (mostra form `mode=edit`, id) | humano no submit | servidor + versão/etag |
| **Delete** | modelo (mostra `confirm_action`) | humano confirma | servidor + idempotency key |

O modelo nunca chega perto de um `INSERT`.

### Choque com as regras do domínio

O [documento 02](./02-regras-de-negocio.md) restringe delete quase totalmente:
movimento é imutável (`RN-M02`, corrige-se por estorno), produto com histórico só
inativa (`RN-P04`), usuário só desativa (`RN-A06`), auditoria nunca (`RN-D02`).

Isso é uma **vantagem** para este desenho: quanto menos delete existe, menor a
superfície onde uma composição errada causa dano irreversível. `confirm_action`
vai ser usado mais para *estorno* e *descarte* do que para exclusão real.

---

## 8. Identidade de view e compartilhamento

### O problema descoberto na v1

Favoritar duplicava, e a estrela voltava apagada ao reabrir a tela. Causa
conceitual: o favorito estava chaveado no id da **composição**, criado a cada
renderização. Reabrir a mesma tela gerava id novo.

**Uma view é a mesma view quando o schema é o mesmo.** A chave passou a ser
derivada do schema (`viewKey`), não da execução.

Armadilha geral: quando a UI é composta dinamicamente, "a mesma tela" perde o id
óbvio. Tudo que precise lembrar de uma tela — favoritos, histórico, permissões,
telemetria, auditoria — precisa de identidade explícita de view. Apps por rota
ganham isso de graça na URL.

### Compartilhamento

**Compartilha-se o schema, não o prompt.** Prompt é não-determinístico: a outra
pessoa clica e o modelo pode compor diferente.

Mecânica escolhida — **pelo sistema, não por link**:

1. Usuário clica em compartilhar.
2. Aparece lista de destinatários, filtrada por quem ele pode contatar.
3. O sistema entrega o item na caixa do destinatário.

Ganhos sobre link: auditoria (quem compartilhou o quê), revogação, e nenhum
segredo em trânsito — link é encaminhado, colado em grupo, fica em histórico.

**A regra que não pode quebrar:**

> **Compartilhar aponta para uma view. Não concede acesso.**

O destinatário abre sob a permissão dele. Ao abrir, o schema é revalidado contra
**o catálogo dele**, e os dados carregam sob a autenticação dele. Se ele não pode
ver o lote, ele vê "sem acesso" — não os dados de quem compartilhou. Sem isso,
compartilhamento vira canal de escalação de privilégio.

Conceder acesso junto, se for necessário, é **uma segunda ação, explícita e
auditada**, disponível só para quem tem autoridade de conceder. Nunca implícita.

Fica gravado: `{ schema, quem compartilhou, com quem, quando, mensagem, status }`.
O schema, não os dados — assim o item continua correto meses depois.

---

## 9. Camadas

Mantidas da v1 porque se pagaram:

| Camada | Responsabilidade |
|---|---|
| `domain/` | tipos + regras puras. Sem React, sem I/O. As regras do documento 02 moram aqui |
| `data/` | única porta para dados. Trocar mock por API real é mudança local |
| `application/` | queries, commands, pipeline, actions — toda a orquestração |
| `state/` | store observável fora do React; persistent / session / ui separados |
| `registry/` | `defineComponent` + registry + catálogo derivado |
| `schema/` | o contrato que o modelo produz + validação |
| `render/` | schema → React |
| `viewmodels/` | projeções puras |
| `components/` | apresentação. Não busca dado, não decide regra, não lê store |

**Cortadas na v1 e que continuam cortadas:** Context Engine (duplicava session
state), Task Engine (indireção que só renomeava chamadas), Layout Engine como
camada (é um `switch` de 60 linhas).

### Mecanismos que precisam existir de novo

Sem `useEffect` para orquestrar, duas coisas viram responsabilidade sua:

1. **Invalidação de pedido superado** — abrir A e logo B não pode deixar a
   resposta de A sobrescrever B. Na v1: token de slot, checado depois de todo
   `await`.
2. **Coalescing de requisições** — quatro componentes da mesma entidade disparam
   quatro consultas idênticas. Na v1: compartilhamento de promessas em voo.

Ambos são de graça em TanStack Query. **Avaliar usar TanStack Query na v2** em vez
de reescrever — a v1 concluiu que o store fora do React não é a parte valiosa.

### Verificação automática

A v1 tinha `npm run arch:check`, que falhava o build se um componente importasse
a camada de dados, usasse `useEffect` ou lesse store direto. As regras foram
testadas negativamente. **Vale recriar** — é o que transforma a disciplina em
propriedade verificável.

---

## 10. Números medidos que restringem o desenho

Da v1, dados reais:

| | |
|---|---|
| Schema de tela com 3 componentes | **~60 tokens** |
| Componente React equivalente, gerado | ~800–2000 tokens |
| Custo do catálogo no prompt | **~164 tokens por componente registrado** |
| Tempo até o 1º componente (só latência simulada, sem modelo) | 600–1000 ms |

**A consequência mais importante:** 25 componentes ≈ 4k tokens de prompt em toda
pergunta; 60 componentes ≈ 10k. **Não escala por adição.** Passando de ~25
componentes é obrigatório recuperar catálogo — buscar só os relevantes à
pergunta — que é outro sistema, com falhas próprias.

Para o estoque da Bertoni, isso significa: manter o catálogo do ciclo 1 **abaixo
de 25 componentes**, e tratar recuperação de catálogo como item de roadmap, não
de arquitetura inicial.

---

## 11. O que NÃO fazer

Inviabilidades conhecidas, em ordem de quão rápido mordem:

1. **Não componha formulários complexos por schema.** Multi-etapa, validação
   cruzada, wizard → registre inteiro (L1).
2. **Não deixe o assistente ser o app.** Ele é *uma* superfície. Telas normais
   continuam telas normais, com rota e URL.
3. **Não deixe composição sem endereço.** Favorito, compartilhar, voltar no
   navegador e auditoria dependem de identidade de view.
4. **Não deixe o modelo decidir layout.** Na v1, `grid` espremia tabela em tile de
   200px. Cada componente declara seu próprio tamanho; o layout obedece ao
   componente, não ao modelo. *O modelo escolhe o que mostrar; o front-end decide
   como aquilo se parece.*
5. **Não use o assistente para a tela do dia a dia.** Modelo real soma 1–3 s. Ok
   para uma pergunta; inaceitável para a tela aberta 200 vezes ao dia.
6. **Não confie no filtro que falta.** Achado mais perigoso da v1: um componente
   não registrado é rejeitado e aparece no trace; um **filtro** que falta apenas
   alarga a resposta em silêncio. Pedir "viagens programadas" devolvia tudo
   porque o catálogo não tinha esse valor. Todo recorte que o usuário sabe pedir
   precisa existir no catálogo como valor nomeado — auditoria contínua.

---

## 12. Decisões técnicas em aberto

1. **TanStack Query ou store próprio?** A v1 escreveu o store à mão e concluiu
   que não valeu. Decidir antes de escrever a primeira linha.
2. **Como o schema vira URL?** Serializado no cliente ou id gerado no servidor? O
   servidor dá auditoria e revogação; o cliente é mais simples.
3. **Recuperação de catálogo** — necessária se o ciclo 1 passar de 25
   componentes. Contar os componentes no documento de escopo.
4. **Off-line em Uberlândia** (`RNF-03`) interage mal com catálogo servido pelo
   servidor. Como o assistente se comporta sem conexão? Provável resposta:
   assistente exige conexão; conferência e contagem funcionam sem.
5. **Modelo e latência** — `claude-haiku-4-5-20251001` para melhor caso,
   `claude-sonnet-5` para melhor qualidade. Medir os dois com o catálogo real.
6. **Suíte de avaliação.** UI não-determinística não tem teste de regressão
   comum. Planejar desde o início: um conjunto de perguntas com composição
   esperada, rodado a cada mudança de catálogo ou de prompt.

---

## 13. A pergunta que continua aberta

A v1 nunca rodou com uma API key. Todo número acima veio do parser mockado —
que acerta porque foi escrito para acertar.

> **Com que frequência um modelo real emite schema válido?**

Isso não é detalhe de implementação: é o que decide se a experiência se sustenta.
Medir cedo na v2, com o catálogo real da Bertoni, e registrar taxa de schema
válido e tempo até o primeiro componente antes de comprometer o projeto.
