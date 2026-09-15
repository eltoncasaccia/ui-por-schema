# ADR-0033 — Testes de ponta a ponta com Playwright, contra um banco próprio

**Status:** Aceito · **Data:** 2026-09-14 · **Escopo:** Ferramental

A dependência foi perguntada antes, como exige o [ADR-0028](./0028-processo-de-decisao.md),
e o cliente respondeu em 2026-09-14: *"vamos implementar testes com playwright"*.

## Contexto

A suíte tem três camadas, e nenhuma abre um navegador:

| Camada | O que prova | O que não alcança |
|---|---|---|
| `pytest` | domínio, registry com fakes, borda HTTP contra Postgres real | a interface |
| `vitest` + jsdom | views, motor de render, invariantes visuais | roteador real, cookie, proxy |
| verificadores | camadas, bijeção, arquivos gerados | comportamento |

Algumas coisas só existem no navegador:
- o `BrowserRouter` da T-031, convivendo com o `useRotaView` da T-016 por meio de um
  `popstate` sintético (`web/src/app/layout/Roteador.tsx`);
- o cookie de sessão `SameSite=Lax` e o par CSRF, atravessando o proxy do Vite;
- o menu filtrado pelo catálogo do ator.

**A evidência de que isso importa é concreta.** Em 2026-09-14, com o `playwright-cli`,
o seguinte caminho foi reproduzido: em `/lotes`, clicar em "Vencimento" monta a fila
no workspace, mas a tela continua mostrando Lotes, com "Vencimento" destacado no
menu. O bug passou por toda a suíte ([A-45](../tasks/ACHADOS.md)).

**Um e2e ingênuo agravaria um segundo problema.** Os testes de banco já escrevem no
banco de desenvolvimento, e o que escrevem não pode ser apagado, porque `movimento`
e `auditoria` são append-only ([A-44](../tasks/ACHADOS.md)). Um e2e que fizesse login
contra o `make up` somaria sessões e auditoria ao mesmo banco.

## Decisão

1. **`@playwright/test` como devDependency de `web/`**, com as specs em `web/e2e/`.
   Só Chromium no ciclo 1.
2. **O e2e sobe os próprios servidores** pelo `webServer` do Playwright: a API por
   `uv run uvicorn` na porta 8001, o Vite na 5174 com `VITE_API_URL` apontando para
   ela, e os dois contra o database `estoque_teste` ([T-052](../tasks/T-052-banco-de-teste-isolado.md)).
   Reusar o stack do `make up` é exatamente como o A-44 volta.
3. **O servidor de e2e é configurado para passar pelas próprias proteções:**
   `CORS_ORIGIN` é a origem do Vite de e2e, porque o CSRF compara `Origin` com ela.
   `MODO_DEMO=true` dá entrada por persona, com a senha `demo` do seed.
4. **O e2e cobre só o que as outras camadas não provam:** navegação e roteamento,
   sessão real e catálogo por ator refletido na interface. Regra de negócio continua
   no `pytest`, e desenho de view no `vitest`. Um e2e que repete teste de outra camada
   é custo sem evidência nova.
5. **Teste negativo é obrigatório também aqui:** a persona que não pode, tentando
   pela interface **e** pela URL digitada.
6. **Bug conhecido entra como `test.fail()`.** O teste reprova sozinho quando o bug é
   corrigido, o mesmo arranjo do `xfail(strict=True)` do A-42.
7. **Nenhuma chamada a modelo de linguagem.** O servidor de e2e sobe sem chave de
   provedor, porque chamar o modelo custa token ([ADR-0013](./0013-suite-de-avaliacao.md)).
8. **`make e2e` fica fora do `make check` local**, porque exige navegador e dois
   servidores. No CI é um job próprio, que publica relatório e trace quando falha.
9. **Esperas fixas são proibidas.** `waitForTimeout` não entra em `web/e2e/`: as
   asserções esperam pelo estado da página. Espera fixa é a causa mais comum de teste
   intermitente.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Cypress** | Um segundo runner, com modelo de execução próprio. O Playwright roda em Node com o mesmo TypeScript |
| **Só `vitest` + jsdom** | Não há roteador de verdade nem cookie. O bug do A-45 passaria de novo |
| **Reusar o stack do `make up`** | Escreve no banco de desenvolvimento (A-44) |
| **Container Postgres só para teste** | Container novo sem ganho sobre um database a mais no mesmo container |
| **Limpar os dados no teardown** | Bate na imutabilidade de `movimento` e `auditoria`, que é a regra que o sistema defende |
| **`playwright-cli` ou MCP como suíte** | São ferramentas de exploração do agente, não uma rede de regressão versionada. O `playwright-cli` instalado global continua servindo para investigar |

## Consequências

**Positivas**
- A navegação ganha rede. A correção do menu terá um teste que prova, em vez de um
  print.
- O banco de desenvolvimento para de receber escrita de teste, tanto do `pytest`
  quanto do e2e.

**Negativas**
- Uma dependência nova, e o download do Chromium no CI.
- O CI fica mais lento, embora em job paralelo.
- Teste de ponta a ponta é a camada mais cara e a mais sujeita a intermitência. Por
  isso a lista é curta (item 4) e a espera fixa é proibida (item 9).

**O que continua não verificado**
- Firefox e WebKit.
- O layout estreito, em que a `Tabela` vira cartões. É candidato a um projeto
  `mobile` do Playwright depois.
