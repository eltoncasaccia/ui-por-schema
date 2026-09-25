# T-053 — Testes de ponta a ponta com Playwright

| | |
|---|---|
| **Trilha** | E · ambiente e qualidade / D · interface |
| **Tamanho** | M |
| **Depende de** | [T-052](./T-052-banco-de-teste-isolado.md) |
| **ADRs** | [0033](../adr/0033-e2e-playwright-banco-proprio.md), [0003](../adr/0003-catalogo-por-ator.md), [0019](../adr/0019-autenticacao-e-cadastro.md) |
| **Origem** | pedido do cliente em 2026-09-14; achado [A-45](./ACHADOS.md) |
| **Escrita em** | 2026-09-14 |

## Por que existe

Nenhum teste abre um navegador. O bug do menu [A-45](./ACHADOS.md) passou por toda a
suíte e só apareceu quando alguém clicou. O ADR-0033 decide a ferramenta, o banco e o
recorte. Esta tarefa entrega a primeira bateria.

## O que já foi conferido

- **Dependência:** o `@playwright/test` não está instalado. O `web/node_modules` da
  árvore principal é uma instalação real, então `npm install -D` é seguro nela. Numa
  worktree com `node_modules` por symlink, não rode.
- **Vite:** `web/vite.config.ts` fixa a porta 5173 e manda `/api` para
  `VITE_API_URL ?? http://localhost:8000`. O e2e sobe com `--port 5174 --strictPort`.
- **API:** sobe com `uvicorn estoque.server.app:app` (`api/entrypoint.sh:12`) e lê do
  ambiente, em `server/config.py`, as variáveis `DATABASE_URL` (papel restrito,
  asyncpg), `SESSAO_SECRET`, `MODO_DEMO` e `CORS_ORIGIN`. Confira se ela sobe sem chave
  de provedor: o e2e não chama modelo.
- **Tela de entrada:** com `MODO_DEMO`, há um botão por persona, com o nome
  ("Marco Bertoni · Diretor →"). A senha é `demo`, do seed.
- **Menu:** o botão "Navegação" da barra (`aria-pressed`) abre `aside.lateral`. Os
  itens são os três fixos (`MENU` em `web/src/shell/PainelNavegacao.tsx:24`) mais as
  rotas sem parâmetro (`NAV_ROTAS` em `web/src/app/layout/rotasOperacao.tsx`),
  filtradas pelo catálogo em `PainelNavegacao.tsx:45`. Prefira `getByRole` a classes
  CSS.
- **O bug, reproduzido em 2026-09-14:** o menu de Marco tem
  `Vencimento | Quarentena | Bloqueados | Lotes | Vencimento`. Em `/lotes`, clicar no
  **primeiro** "Vencimento" deixa a URL em `/lotes` e o título em "Lotes", e marca
  "Vencimento" como item atual.

## Arquivos de propriedade exclusiva

```
web/playwright.config.ts
web/e2e/**
```

## Toca, com registro

```
web/package.json · web/package-lock.json   devDependency @playwright/test, script e2e
Makefile                                   alvo e2e, que depende de db-teste
.github/workflows/ci.yml                   job e2e, separado de verificar
.gitignore                                 test-results/, playwright-report/
web/eslint.config.js · web/tsconfig*.json  só se e2e/ precisar entrar em lint e tipos
CLAUDE.md                                  §4: make e2e na tabela
web/CLAUDE.md                              seção Testes
```

## Critérios de aceite

- [x] **AC-1** `make e2e` sobe a API (8001) e o Vite (5174) próprios contra
      `estoque_teste` e roda a suíte. Com o `make up` rodando ao mesmo tempo, não há
      conflito de porta, e as contagens de `usuario`, `sessao` e `auditoria` do banco
      `estoque` **não mudam**. *(negativo — verificação executada)*
- [x] **AC-2** Cada uma das 7 personas entra pela tela de demonstração e vê o próprio
      nome e papel no rodapé da navegação.
- [x] **AC-3** Menu por ator: Helena vê "Liberar quarentena", e **Cleide não vê**,
      embora tenha `lote.ler` (AC-4 da T-031). *(negativo)*
- [x] **AC-4** Cleide, digitando `/quarentena/<id de um lote em quarentena do seed>`,
      recebe negativa, e a tela não oferece botão de liberar. O lote continua em
      quarentena. *(negativo — a prova é o servidor, não o menu)*
- [x] **AC-5** Sem sessão, abrir `/lotes` mostra a tela de entrada, e nenhuma linha de
      lote aparece. *(negativo)*
- [x] **AC-6** Cada item de rota do menu de Marco leva ao path da tabela
      `ROTAS_OPERACAO` e ao título correspondente.
- [x] **AC-7** A navegação do A-45 continua certa no navegador de verdade: a partir
      de `/lotes`, clicar num indicador abre o workspace em `/`, e o item selecionado
      é sempre o da tela aberta, inclusive depois do "voltar" do navegador. *(O A-45
      foi corrigido em 2026-09-14, antes desta tarefa; o `test.fail()` previsto
      virou teste comum.)*
- [x] **AC-8** Sabotagem: sem o filtro de catálogo (`PainelNavegacao.tsx:45`), o AC-3
      fica vermelho. Registrado no fechamento, não commitado.
- [x] **AC-9** Nenhum `waitForTimeout` em `web/e2e/`, e o servidor de e2e sobe sem
      chave de provedor de modelo.
- [ ] **AC-10** CI: job `e2e` separado, que instala só o Chromium e publica
      `playwright-report` e o trace como artefato quando falha.

## Não faz

- **Corrigir o menu (A-45):** já foi corrigido em 2026-09-14. Esta tarefa só prova
  a correção no navegador.
- **Linhas clicáveis e cadastro de usuário:** esperam decisão do cliente.
- **Testar o assistente com modelo real:** custa token (ADR-0013).
- **Firefox, WebKit e layout estreito:** ficam registrados no ADR-0033 como não
  verificados.

## Como foi verificado (2026-09-25)

`make e2e` · **14 testes, 6,0 s**, Chromium, contra `estoque_teste`.

| AC | A prova |
|---|---|
| AC-1 | Stack de desenvolvimento **no ar** (8000/5173) durante a corrida do e2e (8001/5174). Banco `estoque` **idêntico** antes e depois — `usuario=7`, `sessao=0`, `auditoria=0`, `movimento=269`. O controle de que a suíte escreveu em algum lugar: `estoque_teste` foi de `sessao=77`/`auditoria=107` para `90`/`126` |
| AC-2 | As 7 personas, uma por teste, com nome e papel lidos do rodapé |
| AC-3 | Helena vê "Liberar quarentena"; Cleide não vê, **e vê "Lotes"** — o controle que separa filtro de tela vazia |
| AC-4 | O id do lote sai da fila da própria RT (`lerComponente`), não de constante. Cleide digita `/quarentena/<id>`, recebe **"Sem acesso a este componente."** palavra por palavra, não há botão de liberar no workspace, o número do lote não aparece, e a fila de Helena continua com o mesmo total e o mesmo lote |
| AC-5 | Tela: `/lotes` sem sessão mostra a entrada, sem tabela. Servidor: POST recusado em **403 pelo CSRF** — que é middleware e não deixa a requisição chegar à autenticação — e GET `/api/auth/eu` em **401** |
| AC-6 | A lista esperada é `ROTAS_OPERACAO` **cruzada com o catálogo do ator**, buscado em `/api/catalogo` no próprio teste. Cada item leva ao path, ao título e ao `aria-current`; e as rotas fora do catálogo têm `toHaveCount(0)` |
| AC-7 | De `/lotes`, o indicador abre em `/`, a marca migra, e o **voltar do navegador** devolve URL, título e marca |
| AC-8 | **Sabotagem executada:** `PainelNavegacao.tsx:45` sem o filtro → AC-3 (Cleide) e AC-6 ficaram **vermelhos**; AC-4 **continuou verde**, que é o certo: o menu é conveniência, quem protege é o servidor. Restaurado, não commitado |
| AC-9 | `grep waitForTimeout` em `web/e2e/` e no config: nada. Nenhuma chave de provedor no `env` do `webServer` — a API subiu assim |

**AC-10 fica em branco:** o job existe, o YAML foi validado (dois jobs, 9 passos
no `e2e`), mas **nenhuma execução de CI aconteceu** — isso só se confere num
push. Marcar agora seria evidência falsa.

### Achado do próprio teste

A sabotagem reprovou o AC-4 por um motivo errado: a busca por botão "liberar"
casava com o **item do menu**, não com a tela. Corrigido para procurar dentro de
`main.workspace`. Um teste que passa pelo motivo errado é pior que um teste que
falha — e foi a sabotagem, não a suíte verde, que mostrou isso.

### Tocado além da lista declarada

- **`web/vitest.config.ts`** — o `vitest` coleta por nome e capturava as três
  specs de `e2e/`, reprovando-as com "0 test" porque o `test()` delas é do outro
  runner. Uma linha de `exclude`, que é a forma de o ADR-0033 §8 valer na
  prática ("`make e2e` fica fora do `make check`").
- **`Makefile`, alvo `help`** — o `grep -E '^[a-z-]+:'` não aceita dígito, e
  `e2e` nunca apareceria na lista de comandos. Virou `^[a-z0-9-]+:`.
- **`Makefile`, alvo `lint-web`** — passou a lintar `e2e` junto com `src` e
  `scripts`; sem isso as specs ficariam fora do `eslint`.
