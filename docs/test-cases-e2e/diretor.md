# E2E Navigation Test Cases — Role: diretor

> Auto-gerado pela skill `e2e-nav-test`
> Framework: React 18 + TypeScript (Vite) · FastAPI (Python)
> Gerado: 2026-09-25
> Papel: diretor (persona-exemplo: Marco Bertoni)

Testes de aceite de ponta a ponta para o sistema de estoque da Bertoni
Distribuidora Farmacêutica. Os testes seguem ordem de dependência — se um
falhar, todos os que dependem dele ficam **BLOQUEADOS**.

## Prerequisites

- **Subir o app**: `make up` (raiz do repo) — sobe API (FastAPI), Vite e Postgres
- **Base URL**: `http://localhost:5173`
- **Login**: tela de entrada, botão de demonstração **"Marco Bertoni"** (senha
  `demo`, atalho só existe com `MODO_DEMO=true`)
- **Screenshots on failure**: `screenshots/` ao lado deste documento
- **Browser mode**: headless

## Detected Stack

- **Framework**: React 18 + TypeScript, Vite, `react-router-dom` (`BrowserRouter`)
  para 8 rotas de operação; um roteador próprio via `pushState` para `/v/:viewId`
- **Auth**: sessão em cookie `httpOnly` + CSRF de dupla submissão; login por
  persona quando `MODO_DEMO=true`
- **UI**: sistema de tokens próprio (`estilo.css`), sem framework de CSS
- **Papéis detectados**: diretor, rt, gerente, conferente, comprador, auditoria
- **Rotas descobertas**: 8 de operação + `/usuarios` (fora do catálogo) + `/v/:viewId`

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

---

## Dependency Tree

```
T01 Landing (tela de entrada)
 └─ T02 Login como Marco (diretor)
     └─ T03 Workspace (/)
         ├─ T04 /lotes
         │   └─ T05 /lotes/:id (detalhe de um lote)
         ├─ T06 /vencimento
         ├─ T07 Indicadores do painel (estoque_indicador)
         ├─ T08 /usuarios — gestão de usuário
         │   └─ T09 Alterar papel de um usuário sem papel
         ├─ T10 Ver custo num indicador (custo.ler)
         ├─ T11 Trilha de auditoria
         └─ T12 Sair
     └─ T13 Acesso negado por URL — /quarentena/:loteId (sem lote.liberar)
     └─ T14 Acesso negado por URL — /saida (portão de formulário)
     └─ T15 Acesso negado por URL — /controlados
     └─ T16 Acesso negado por URL — /recebimento/novo
```

Se T02 falhar, T03 em diante ficam **BLOQUEADOS**. T13–T16 são independentes
entre si e de T04–T12 — todos dependem só de T03 (sessão ativa).

---

## Test Flows

### T01: Landing page

**Dependencies**: None
**Blocks**: T02

- [x] Navegar para `/`
- [x] Verificar o heading "Estoque Bertoni" visível
- [x] Verificar o botão "Marco Bertoni" (e os outros 6, um por persona) visível
- [x] Verificar que nenhuma tabela ou dado de estoque aparece na tela

---

### T02: Login como Marco (diretor)

**Dependencies**: T01
**Blocks**: T03, T13, T14, T15, T16

- [x] Clicar no botão "Marco Bertoni"
- [x] Verificar redirecionamento para o workspace (`/`)
- [x] Verificar o botão "Navegação" (barra de ícones) visível
- [x] Abrir a navegação lateral e verificar o rodapé: nome "Marco Bertoni" e
      papel "diretor"

---

### T03: Workspace (`/`)

**Dependencies**: T02
**Blocks**: T04, T06, T07, T08, T10, T11, T12

- [x] Verificar a barra de ícones (Navegação, Fixadas, Recebidas, Assistente,
      Execution Trace, tema, Sair)
- [x] Abrir o painel "Navegação"
- [x] Verificar que o menu mostra **exatamente** "Lotes" e "Vencimento" —
      nenhuma outra rota do catálogo de 6
- [x] Verificar que "Liberar quarentena", "Controlados", "Saída" e "Registrar
      recebimento" **não aparecem** no menu

---

### T04: `/lotes`

**Dependencies**: T03
**Blocks**: T05

- [x] Clicar em "Lotes" no menu
- [x] Verificar URL `/lotes` e título da tela "Lotes"
- [x] Verificar a tabela (ou lista de cartões, em tela estreita) com ao menos
      uma linha — **confirmado em tela estreita de verdade**: com o painel de
      navegação e o dock do assistente abertos, mesmo em viewport 1680px o
      workspace sobra em ~560px e `Tabela` vira lista de cartões
      (20 `.linha-cartao`, nenhum `<table>`)
- [x] Verificar que a coluna de custo **não aparece** (diretor não vê custo
      aqui — `lote_lista` não carrega `custo.ler` no viewmodel)
- [x] ~~Clicar numa linha da tabela~~ **passo corrigido na execução**: o
      clique **não navega**. `ui/Tabela.tsx` é puramente apresentacional —
      sem prop de navegação, sem `onClick` de linha, confirmado no código.
      Ver Observations.

---

### T05: `/lotes/:id` — detalhe de um lote

**Dependencies**: T04

- [x] Navegar direto para `/lotes/<id>` (não por clique — ver correção acima)
- [x] Verificar dados do lote: produto, número, validade, saldo, status
- [x] Verificar que **nenhum campo de custo** aparece
- [x] Voltar (`goBack`) e verificar retorno a `/lotes`

---

### T06: `/vencimento`

**Dependencies**: T03

- [x] Clicar em "Vencimento" no menu
- [x] Verificar URL `/vencimento` e título "Vencimento"
- [x] Verificar a fila de lotes por proximidade de validade
- [x] Verificar o item "Vencimento" marcado como atual no menu
      (`aria-current="page"`)

---

### T07: Indicadores do painel (`estoque_indicador`) — `[BLOCKED]`

**Dependencies**: T03

- [BLOCKED] No workspace (`/`), verificar ao menos um indicador visível — o
  passo pressupõe algo já composto no workspace, mas `/` abre **vazio** sem
  uma composição prévia. Indicadores só existem depois do assistente montar
  uma composição, ou de uma view fixada (`PainelFixadas`) ser reaberta —
  nenhuma das duas existe nesta corrida sem chamar o modelo (ADR-0013)

---

### T08: `/usuarios` — gestão de usuário

**Dependencies**: T03
**Blocks**: T09

- [x] Navegar para `/usuarios` (fora do catálogo — só por URL; **este é o
      único papel que alcança esta tela**)
- [x] Verificar a lista de usuários, com papel e unidades de cada um
- [BLOCKED] Verificar um usuário com `papel: null` ("sem papel") — as 7
  personas do seed de desenvolvimento já têm papel atribuído; não há
  recém-cadastrado disponível nesta corrida

---

### T09: Alterar papel de um usuário sem papel — `[BLOCKED]`

**Dependencies**: T08

- [BLOCKED] Bloqueado por T08 (nenhum usuário sem papel disponível). Mesmo se
  houvesse, ficou fora do escopo combinado para esta corrida: é escrita real
  em `usuario` no banco de desenvolvimento

---

### T10: Ver custo num indicador (`custo.ler`) — `[BLOCKED]`

**Dependencies**: T03

- [BLOCKED] Compor um `estoque_indicador` com `metrica=valor_em_estoque`
  exige o assistente (chamada ao modelo) — fora do escopo desta corrida
  (ADR-0013, custa token a cada execução)

---

### T11: Trilha de auditoria — `[BLOCKED]`

**Dependencies**: T03

- [BLOCKED] `auditoria_trilha` **não tem rota própria** — não está em
  `ROTAS_OPERACAO`, só alcançável compondo pelo assistente. **Achado da
  execução**: o passo do documento ("se houver entrada de menu") assumia uma
  alternativa que não existe — o diretor não tem nenhum caminho de navegação
  direta até a trilha, apesar de ter `auditoria.ler`

---

### T12: Sair

**Dependencies**: T03

- [x] Clicar no botão "Sair" (barra de ícones)
- [x] Verificar retorno à tela de entrada
- [x] Navegar para `/lotes` e verificar que mostra a tela de entrada, não dados
- [ ] *(negativo, servidor)* Requisitar `/api/auth/eu` com o cookie de sessão
      antigo — **não executado nesta corrida** (só a UI foi conferida, não a
      requisição forjada com o cookie capturado antes do "Sair"; já coberto
      pelo `entrada.spec.ts` da suíte automatizada — T-057 AC-6)

---

### Access Denial Tests

### T13: Acesso negado por URL — `/quarentena/:loteId`

**Dependencies**: T02

- [x] Obter um `lote_id` em quarentena (via banco, não a UI — diretor não vê a
      fila)
- [x] Navegar direto para `/quarentena/<lote_id>`
- [x] Verificar a mensagem "Sem acesso a este componente."
- [x] Verificar que nenhum dado do lote aparece na tela

### T14: Acesso negado por URL — `/saida` (portão de formulário)

**Dependencies**: T02

- [x] Navegar para `/saida`
- [x] Verificar o texto "Informe o id do produto para começar a separação." —
      **antes** de qualquer busca, sem recusa ainda
- [x] Preencher um id de produto válido e clicar "Continuar"
- [x] Verificar a mensagem "Sem acesso a este componente." — a recusa só chega
      ao submeter, porque só aí existe um `Bloco` de verdade

### T15: Acesso negado por URL — `/controlados`

**Dependencies**: T02

- [x] Navegar para `/controlados`
- [x] Verificar a mensagem "Sem acesso a este componente."
- [x] Verificar que nenhum campo do formulário de autorização aparece

### T16: Acesso negado por URL — `/recebimento/novo`

**Dependencies**: T02

- [x] Navegar para `/recebimento/novo`
- [x] Verificar a mensagem "Sem acesso a este componente."
- [x] Verificar que o campo "Código de barras do produto" **não** aparece

---

## Não faz

- **Assistente com modelo real** — chamar o modelo custa token a cada execução
  (ADR-0013). O painel pode ser aberto e a composição de leitura verificada
  visualmente, mas nenhum teste automatizado envia prompt.
- **Exportação (CSV/XLSX/PDF) e paginação** — candidatos, fora do recorte de
  navegação/catálogo.
- **Firefox, WebKit, layout estreito** — não verificados, por decisão do
  projeto (ADR-0033).

---

## Observations

Executado em 2026-09-25, `@playwright/test` (chromium, **headed**,
`viewport: 1680×900`), contra `make up` (dev, `localhost:5173`/`:8000`,
banco `estoque`). Roteiro em `web/run_diretor.mjs` (script único, fora da
suíte oficial da T-057 — apagado depois da corrida).

### Achados sobre o DOCUMENTO gerado pela skill (não sobre o app)

- **T04/T05 — "clicar numa linha da tabela" não existe.** `ui/Tabela.tsx` é
  puramente apresentacional: sem `onClick` de linha, sem prop de navegação.
  `/lotes/:id` funciona perfeitamente, mas só por URL direta — o mesmo
  padrão que `TelaSaida.tsx` já documenta para `/saida` ("identificador
  digitado ou colado, não buscado"). A skill assumiu clique-para-detalhe
  sem confirmar contra o componente real.
- **T07/T10/T11 — três passos pressupõem alcançar um componente sem rota
  própria.** `estoque_indicador` (com métrica de custo) e `auditoria_trilha`
  só existem no catálogo do assistente — não há item de menu nem URL direta
  para nenhum dos dois. A skill não distinguiu "está no catálogo do ator"
  de "tem rota alcançável sem o modelo", e isso inflou o plano com passos
  não executáveis num teste automatizado (que corretamente exclui o
  assistente, por ADR-0013).
- **T09 pressupôs um usuário "sem papel" no seed** — existe no seed de
  `estoque_teste` (o do `pytest`/e2e automatizado), mas não necessariamente
  no banco de desenvolvimento neste momento.

### Achado sobre o APP (viewport)

Com o painel de navegação e o dock do assistente abertos, o workspace sobra
em **~560px mesmo num viewport de 1680px** — `Tabela` vira lista de cartões.
Um roteiro escrito assumindo `<table>`/`<tr>` (papel `row`) falha em
qualquer corrida real com os dois painéis abertos, que é o estado padrão da
aplicação ao entrar. Vale registrar isso na skill como um lembrete geral:
**não assumir a role semântica de uma tabela sem checar o layout responsivo
primeiro.**

### Blocked Tests

| Test | Motivo |
|---|---|
| T07 | Indicador só existe via assistente (modelo real) ou view fixada — nenhum disponível |
| T09 | Sem usuário "sem papel" no banco de dev; e seria escrita real fora do escopo |
| T10 | Exige o assistente (ADR-0013) |
| T11 | `auditoria_trilha` sem rota própria — só alcançável pelo assistente |

### Summary

- Total: 16
- Passou: 12 (T01, T02, T03, T04, T05, T06, T08, T12, T13, T14, T15, T16 —
  T05 com o passo de clique corrigido na execução)
- Falhou: 0
- Bloqueado: 4 (T07, T09, T10, T11)
