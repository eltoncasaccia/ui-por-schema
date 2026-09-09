# T-045 — A borda HTTP quebrada por área

| | |
|---|---|
| **Onda** | W5 |
| **Trilha** | E |
| **Tamanho** | M |
| **Depende de** | — (refactor puro; nenhum comportamento muda) |
| **Bloqueia** | nada — mas destrava a propriedade exclusiva de toda tarefa que toca rota |
| **ADRs** | [ADR-0032](../adr/0032-borda-http-por-router.md) · [ADR-0031](../adr/0031-ports-and-adapters.md) |
| **Regras** | — |

## Objetivo

`server/app.py` tinha **817 linhas e 20 endpoints**. O ADR-0031 descreve
`server/` como adapter primário — a casca fina que traduz HTTP para caso de uso —
e uma casca de 817 linhas não é fina.

O custo era concreto: T-011, T-025, T-037 e T-040 declararam `server/app.py`
como propriedade exclusiva e escreveram **todas** nele, então a regra que torna o
trabalho paralelo seguro não podia ser cumprida. E mexer numa rota de 33 linhas
obrigava a carregar as outras 784.

## Arquivos de propriedade exclusiva

```
api/src/estoque/server/app.py            (reescrito: raiz de composição)
api/src/estoque/server/deps.py           (novo)
api/src/estoque/server/rotas/__init__.py (novo)
api/src/estoque/server/rotas/saude.py            auth.py
api/src/estoque/server/rotas/catalogo.py         assistente.py
api/src/estoque/server/rotas/views.py            compartilhamento.py
api/src/estoque/server/rotas/dados.py            comandos.py
api/.importlinter                        (contrato 5)
api/tests/arquitetura/violacoes/rotas/   rotas.cfg   (fixture da violação)
docs/adr/0032-borda-http-por-router.md   (novo)
```

Toca também, só nos **ponteiros** (nenhuma asserção enfraquecida):
`api/tests/arquitetura/test_verificador_falha_quando_violado.py`,
`tests/assistant/test_agnosticismo.py`, `tests/auth/test_limite.py`,
`tests/server/test_destinatarios.py`, `test_erros_da_borda.py`,
`test_forma_do_ator.py`, e a tabela "onde cada coisa mora" do `api/CLAUDE.md`.

## Critérios de aceite

- [x] **AC-1** — `app.py` fica abaixo de 150 linhas e não contém nenhuma rota de
      negócio: só montagem, middleware de CSRF, os três handlers de erro e o
      ciclo de vida. *(139 linhas)*
- [x] **AC-2** — cada área tem um arquivo em `server/rotas/`, e nenhum passa de
      205 linhas. *(maior: `auth.py`, 202)*
- [x] **AC-3** — `estoque.server.app.CFG` e `estoque.server.app._engine`
      continuam importáveis e são o **mesmo objeto** de `deps`.
- [x] **AC-4** — os **467 testes anteriores continuam passando**, e o total vai
      a 468 com o negativo do AC-6. Nenhuma asserção foi removida ou enfraquecida.
- [x] **AC-5** — `api/.importlinter` ganha o contrato 5, `independence` entre os
      oito routers, e `lint-imports` reporta `5 kept, 0 broken`.
- [x] **AC-6 — o teste negativo.** Um fixture introduz
      `rotas.auth -> rotas.comandos` de propósito e o teste afirma que o
      `lint-imports` sai diferente de zero, com o caminho da violação na saída.
      *Sem ele, verde não prova nada — pode estar verde por não estar
      verificando.*
- [x] **AC-7** — `make check` verde nos dois lados.

## O que NÃO foi feito, e por quê

**Os routers não usam `Depends()` do FastAPI.** Foi tentador e é mais idiomático,
mas o CSRF **precisa** ser middleware — dependência esquecida numa rota nova é um
buraco silencioso, e rota nova é o que se acrescenta com pressa. Ter metade do
transversal em middleware e metade em `Depends` seria pior de explicar que a
assimetria atual. Registrado no ADR-0032.

**`deps.py` mantém estado de módulo na importação** (`motor`, `CFG`, `OBS`),
igual ao que `app.py` fazia. Não é bom para teste. Mudar isso é outra decisão, e
esta já é grande o bastante.

**Três linhas de asserção mudaram**, e nenhuma enfraqueceu:
`"Contracts: 4 kept"` → `5 kept` (o contrato novo), `count("return _ok(")` →
`count("return ok(")` (o helper virou público ao sair para `deps.py`), e duas
linhas mortas caíram em `test_agnosticismo.py` — liam o fonte e faziam `del` na
linha seguinte.
