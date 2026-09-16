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

- [ ] **AC-1** `make e2e` sobe a API (8001) e o Vite (5174) próprios contra
      `estoque_teste` e roda a suíte. Com o `make up` rodando ao mesmo tempo, não há
      conflito de porta, e as contagens de `usuario`, `sessao` e `auditoria` do banco
      `estoque` **não mudam**. *(negativo — verificação executada)*
- [ ] **AC-2** Cada uma das 7 personas entra pela tela de demonstração e vê o próprio
      nome e papel no rodapé da navegação.
- [ ] **AC-3** Menu por ator: Helena vê "Liberar quarentena", e **Cleide não vê**,
      embora tenha `lote.ler` (AC-4 da T-031). *(negativo)*
- [ ] **AC-4** Cleide, digitando `/quarentena/<id de um lote em quarentena do seed>`,
      recebe negativa, e a tela não oferece botão de liberar. O lote continua em
      quarentena. *(negativo — a prova é o servidor, não o menu)*
- [ ] **AC-5** Sem sessão, abrir `/lotes` mostra a tela de entrada, e nenhuma linha de
      lote aparece. *(negativo)*
- [ ] **AC-6** Cada item de rota do menu de Marco leva ao path da tabela
      `ROTAS_OPERACAO` e ao título correspondente.
- [ ] **AC-7** A navegação do A-45 continua certa no navegador de verdade: a partir
      de `/lotes`, clicar num indicador abre o workspace em `/`, e o item selecionado
      é sempre o da tela aberta, inclusive depois do "voltar" do navegador. *(O A-45
      foi corrigido em 2026-09-14, antes desta tarefa; o `test.fail()` previsto
      virou teste comum.)*
- [ ] **AC-8** Sabotagem: sem o filtro de catálogo (`PainelNavegacao.tsx:45`), o AC-3
      fica vermelho. Registrado no fechamento, não commitado.
- [ ] **AC-9** Nenhum `waitForTimeout` em `web/e2e/`, e o servidor de e2e sobe sem
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
