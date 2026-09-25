# E2E Navigation Test Cases — Role: rt

> Auto-gerado pela skill `e2e-nav-test`
> Framework: React 18 + TypeScript (Vite) · FastAPI (Python)
> Gerado: 2026-09-25
> Papel: rt — responsável técnico (persona-exemplo: Helena Prado)

Testes de aceite de ponta a ponta. Ordenados por dependência — se um falhar,
os que dependem dele ficam **BLOQUEADOS**.

## Prerequisites

- **Subir o app**: `make up`
- **Base URL**: `http://localhost:5173`
- **Login**: botão de demonstração **"Helena Prado"** (senha `demo`)
- **Screenshots on failure**: `screenshots/` ao lado deste documento
- **Browser mode**: headless (execução real foi **headed**, a pedido)

## Detected Stack

Igual ao documento do diretor — ver `diretor.md` §Detected Stack.
Resumo: React 18 + TypeScript, Vite, `react-router-dom`; FastAPI; sessão em
cookie + CSRF; `MODO_DEMO` para login por persona.

## Role Matrix

| Rota / recurso | diretor | rt | gerente | conferente | comprador | auditoria |
|---|---|---|---|---|---|---|
| `/lotes` (lote_lista) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `/vencimento` (fila_vencimento) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `/quarentena` (fila + liberar) | – | ✓ | – | – | – | – |
| `/controlados` (controlado_autorizar) | – | ✓ | – | – | – | – |
| `/saida` (movimento_saida) | – | – | ✓ | ✓ | – | – |
| `/recebimento/novo` (recebimento_registrar) | – | – | ✓ | ✓ | – | – |
| `/usuarios` (fora do catálogo) | ✓ | – | – | – | – | – |
| Ver custo (`custo.ler`) | ✓ | – | – | – | ✓ | ✓ |
| Trilha de auditoria (`auditoria.ler`) | ✓ | ✓ | – | – | – | ✓ |
| Movimentos, recebimentos, temperatura (leitura) | ✓ | ✓ | ✓ | ✓ | – | ✓ |
| Descarte / estorno de movimento | ✓ | ✓ | ✓ | – | – | – |
| Bloquear/desbloquear lote (`lote.status`) | – | ✓ | – | – | – | – |

**Helena é o único papel com `lote.liberar` e `controlado.autorizar`** — as
duas ações mais sensíveis do domínio (RN-R02: liberação de quarentena
privativa do RT; RN-C01: dupla identificação de controlado).

---

## Dependency Tree

```
T01 Landing
 └─ T02 Login como Helena (rt)
     └─ T03 Workspace (/)
         ├─ T04 /lotes
         ├─ T05 /vencimento
         ├─ T06 /quarentena — fila de liberação
         │   └─ T07 /quarentena/:loteId — liberar um lote
         │       ├─ T08 Liberar com sucesso
         │       └─ T09 (negativo) Reprovar sem justificativa suficiente
         ├─ T10 /controlados — autorizar controlado
         │   └─ T11 Autorizar com dupla identificação
         ├─ T12 Trilha de auditoria
         ├─ T13 Descartar um movimento
         ├─ T14 Estornar um movimento
         └─ T15 Sair
     └─ T16 Acesso negado por URL — /saida (portão de formulário)
     └─ T17 Acesso negado por URL — /recebimento/novo
     └─ T18 Acesso negado por URL — /usuarios
```

T07 é o único nó com dois filhos de comportamento oposto (T08 positivo, T09
negativo) — ambos partem do MESMO lote carregado em T07, então rodam em
sequência, não em paralelo, dentro do mesmo teste ou com lotes distintos.

---

## Test Flows

### T01–T03: idênticos ao fluxo do diretor, com a persona "Helena Prado"

- [x] Login como Helena
- [x] No workspace, abrir "Navegação" e verificar **exatamente** 4 itens:
      "Lotes", "Vencimento", "Liberar quarentena", "Controlados"
- [x] Verificar que "Saída" e "Registrar recebimento" **não aparecem**

---

### T04: `/lotes` — T05: `/vencimento`

- [x] Mesmos passos do documento do diretor (T04/T06), com a persona Helena

---

### T06: `/quarentena` — fila de liberação

**Dependencies**: T03
**Blocks**: T07

- [x] Clicar em "Liberar quarentena" no menu
- [x] Verificar URL `/quarentena` e o título "Fila de quarentena"
- [x] Verificar contagem total e, se houver, o destaque de "venceram na fila"
- [x] Verificar ao menos uma linha, com produto, lote, unidade e validade

---

### T07: `/quarentena/:loteId` — liberar um lote

**Dependencies**: T06
**Blocks**: T08, T09

- [x] Pegar o `lote_id` da primeira linha da fila
- [x] Navegar para `/quarentena/<lote_id>` (identificador digitado/colado —
      não há link clicável na tabela, por desenho — confirmado: mesmo
      achado do `/lotes` do diretor)
- [x] Verificar o título "Liberação · lote <número>"
- [x] Verificar o checklist de conferência (integridade, validade, nota
      fiscal, e temperatura só se o produto for termolábil)
- [x] Verificar os botões "Liberar" e "Reprovar", ambos desabilitados até a
      conferência e a justificativa estarem completas

---

### T08: Liberar com sucesso

**Dependencies**: T07

- [x] Marcar todos os itens obrigatórios da conferência
- [x] Preencher a justificativa (mínimo 10 caracteres)
- [x] Clicar "Liberar" — verificar o diálogo "Confirmar esta ação?"
- [x] Clicar "Confirmar"
- [x] Verificar que o lote sai da fila de `/quarentena`
- [x] **Verificado direto no banco** (não pela trilha — ver T12 BLOCKED):
      `lote.status = 'liberado'` para `l-ins-quar`, e a linha de auditoria
      `lote_liberar_quarentena` gravada com `ator_id = 'u-helena'`. **Escrita
      real no banco de desenvolvimento**, combinada com o usuário para esta
      corrida de avaliação da skill.

---

### T09: *(negativo)* Reprovar sem justificativa suficiente

**Dependencies**: T07 (com um SEGUNDO lote, distinto do usado em T08 —
usei `l-amx-ube-quar`)

- [x] Em `/quarentena/<outro_lote_id>`, deixar a justificativa vazia ou com
      menos de 10 caracteres
- [x] Verificar que os botões "Liberar" e "Reprovar" continuam desabilitados
- [x] Verificar o texto de ajuda indicando o que falta ("Falta conferir: ...")
- [x] Preencher a justificativa curta e NÃO marcar a conferência obrigatória
- [x] Verificar que "Liberar" continua desabilitado — **nenhuma escrita
      ocorreu neste teste**, por desenho

---

### T10: `/controlados` — autorizar controlado

**Dependencies**: T03
**Blocks**: T11

- [x] Clicar em "Controlados" no menu
- [x] Verificar URL `/controlados` e o título "Controlados aguardando
      autorização"
- [x] Verificar ao menos um movimento pendente, com produto e quantidade
      (1 pendência: Clonazepam 2mg · 30, lote `l-clo-1`, submetido por
      `u-cleide`)

---

### T11: Autorizar com dupla identificação

**Dependencies**: T10

- [x] Selecionar um movimento controlado pendente — **passo corrigido na
      execução**: não existe seleção por clique. `/controlados` sem
      `movimento_id` no param **só mostra a fila**; o formulário de decisão
      (`vm.alvo`) exige um `movimento_id` que nenhuma rota de
      `ROTAS_OPERACAO` fornece — confirmado no próprio docstring do
      componente: *"quando T-024 [descoberta pelo `movimento_lista`] chegar,
      esta lista vira o atalho do RT em vez do único caminho"*. Hoje, o
      único caminho é o assistente compor `controlado_autorizar` com o
      `movimento_id` certo.
- [x] ~~Preencher a decisão e a segunda identificação exigida por `RN-C01`~~
      **passo corrigido**: não existe um campo de "segunda identificação".
      `RN-C01` é satisfeita pela IDENTIDADE de quem está logado (Helena ≠
      `u-cleide`, que submeteu) — o formulário só tem um campo "Motivo"
- [BLOCKED] Autorizar de verdade fica **bloqueado nesta corrida**: exige
  chegar ao formulário pelo assistente, fora do escopo (ADR-0013). Testei
  também `/controlados?movimento_id=m-00269` (o id do movimento pendente,
  obtido via banco) — **sem efeito**: `TelaOperacao.tsx` constrói os params
  do componente só a partir dos params de ROTA (`rota.params(urlParams)`),
  nunca da query string, e `/controlados` não declara `:movimentoId` como
  `/quarentena/:loteId` declara. O movimento continua
  `aguardando_autorizacao` no banco — nenhuma escrita aconteceu para este
  teste especificamente

---

### T12: Trilha de auditoria — `[BLOCKED]`

**Dependencies**: T03

- [BLOCKED] `auditoria_trilha` **não tem rota própria** — mesmo achado do
  diretor (T11 de `diretor.md`). Helena tem `auditoria.ler`, mas não há
  caminho de navegação direta até a trilha; só o assistente

---

### T13: Descartar um movimento — `[BLOCKED]`

**Dependencies**: T03

- [BLOCKED] `movimento_descarte` **não tem rota própria** em
  `ROTAS_OPERACAO` — só alcançável pelo assistente. O documento gerado
  assumiu "abrir `lote_movimentos` ou `movimento_lista`" como caminho, mas
  nenhum dos dois tem uma ação de descarte embutida na tela; descartar é
  um componente à parte, sem rota

### T14: Estornar um movimento — `[BLOCKED]`

**Dependencies**: T03

- [BLOCKED] Mesmo motivo do T13, para `movimento_estorno`

---

### T15: Sair

**Dependencies**: T03

- [x] Mesmos passos do documento do diretor (T12)

---

### Access Denial Tests

### T16: Acesso negado por URL — `/saida` (portão de formulário)

**Dependencies**: T02

- [x] Navegar para `/saida`, ver o portão, preencher um produto, "Continuar"
- [x] Verificar "Sem acesso a este componente." (Helena não tem
      `movimento.criar`)

### T17: Acesso negado por URL — `/recebimento/novo`

**Dependencies**: T02

- [x] Navegar direto; verificar "Sem acesso a este componente."

### T18: Acesso negado por URL — `/usuarios`

**Dependencies**: T02

- [x] Navegar para `/usuarios`; verificar recusa — a tela de gestão de
      usuário não aparece (conteúdo da página não contém dado de nenhum
      usuário), consistente com `usuario.gerenciar` sendo exclusivo do
      diretor

---

## Não faz

Mesmo recorte do documento do diretor — sem assistente com modelo real, sem
exportação/paginação, sem Firefox/WebKit/layout estreito.

---

## Observations

Executado em 2026-09-25, `@playwright/test` (chromium, **headed**,
`viewport: 1680×900`), contra `make up` (dev, `localhost:5173`/`:8000`,
banco `estoque`). Roteiro em `web/run_rt.mjs` (script único, fora da suíte
oficial da T-057 — apagado depois da corrida).

**Uma escrita real aconteceu no banco de desenvolvimento nesta corrida**,
combinada com o usuário: T08 (liberação do lote `l-ins-quar`). O movimento
controlado do T11 continua `aguardando_autorizacao` — a tentativa de
autorizá-lo não teve efeito (ver nota do T11), então nada foi escrito para
ele. Nenhuma das duas toca `estoque_teste`, que é o banco da suíte
automatizada da T-057.

### Achados sobre o DOCUMENTO gerado pela skill (não sobre o app)

- **T11 é o achado mais importante desta corrida.** A skill assumiu que
  `/controlados` leva a um formulário de decisão clicável — mas o
  componente, por desenho **documentado no próprio código-fonte**, só
  mostra a fila sem um `movimento_id`, e nenhuma rota do projeto fornece
  esse id. O caminho real para autorizar hoje é só o assistente. Isto não é
  falha da skill sozinha: é o tipo de detalhe que só aparece lendo o
  componente linha a linha, não a rota — e a skill leu a ROTA
  (`ROTAS_OPERACAO`), não o componente por trás dela.
- **T11 também inventou um campo que não existe** ("segunda identificação")
  — `RN-C01` é satisfeita pela identidade de quem está logado, não por um
  campo extra do formulário.
- **T13/T14 pressupõem ações dentro de telas de leitura** (`lote_movimentos`,
  `movimento_lista`) que não têm formulário de escrita embutido —
  descarte/estorno são componentes à parte, sem rota própria, mesma classe
  de achado do T11/T12.
- **T07 confirma o mesmo achado do `diretor.md`**: navegação por
  identificador direto, nunca por clique numa linha.

### Blocked Tests

| Test | Motivo |
|---|---|
| T11 | Formulário de decisão exige `movimento_id`, que nenhuma rota fornece — só o assistente alcança |
| T12 | `auditoria_trilha` sem rota própria |
| T13 | `movimento_descarte` sem rota própria |
| T14 | `movimento_estorno` sem rota própria |

### Summary

- Total: 18
- Passou: 14 (T01–T10, T15–T18 — com T07 e o primeiro passo do T11 corrigidos
  na execução)
- Falhou: 0
- Bloqueado: 4 (T11 quanto ao passo de autorizar de fato, T12, T13, T14)
