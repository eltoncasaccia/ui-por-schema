# T-052 — Banco de teste isolado do banco de desenvolvimento

| | |
|---|---|
| **Trilha** | E · ambiente e qualidade |
| **Tamanho** | M |
| **Depende de** | — |
| **ADRs** | [0033](../adr/0033-e2e-playwright-banco-proprio.md), [0018](../adr/0018-postgres-em-container.md), [0028](../adr/0028-processo-de-decisao.md) |
| **Origem** | achado [A-44](./ACHADOS.md); primeiro sinal em [R-003 §4](../relatorios/R-003-seguranca-ciclo-1.md) ("Resíduo no banco de desenvolvimento") |
| **Escrita em** | 2026-09-14 |

## Por que existe

Os testes de banco não têm banco próprio. Sem variável de ambiente, todos caem
em `localhost:15432/estoque`, que é o mesmo banco do `make up`. Cada execução
deixa usuários, sessões, auditoria e movimentos que **não podem ser apagados**:
`movimento` e `auditoria` são append-only, e apagar o usuário exigiria apagar
linhas delas.

Medido em 2026-09-14, antes de um `make reset` manual: **262 usuários de teste
contra 8 reais**, 3.262 linhas de auditoria, 4.181 sessões, 417 movimentos e 27
lotes. Os usuários apareciam na tela `/usuarios` do diretor. O CI não via o
problema porque usa banco efêmero.

Limpar ao fim de cada teste não resolve: bateria na imutabilidade, que é a regra
que o sistema defende. A saída é **separar os bancos**, não limpar.

## O que já foi conferido

- **O endereço padrão se repete em 13 arquivos:** `tests/server/borda.py`,
  `tests/registry/test_ac6_leitura_auditada.py`, `tests/data/test_imutabilidade_no_banco.py`,
  `tests/data/test_papel_da_aplicacao.py`, `tests/data/test_minimo_maximo.py` e oito
  em `tests/commands/`. Para a lista exata, rode
  `grep -rln 'DATABASE_URL_TESTE' api/tests`. São três variáveis:
  `DATABASE_URL_TESTE` (dono, psycopg), `DATABASE_URL_TESTE_APP` e
  `DATABASE_URL_TESTE_APP_ASYNC` (papel restrito).
- **O app sob teste aponta para o dev por conta própria:** ele lê `DATABASE_URL`, e o
  padrão em `api/src/estoque/server/config.py:18` é `localhost:15432/estoque`. Se só
  a fixture mudar, a fixture grava num banco e o app lê de outro. Os testes falham
  alto, o que é bom, mas precisa ser tratado.
- **Um segundo database no mesmo cluster é viável:** a migração `0001` cria
  `estoque_app` com `IF NOT EXISTS`, e o papel é do cluster. Os `GRANT` são por
  database e rodam de novo na migração. O seed lê `DATABASE_URL_ADMIN`
  (`data/seed/__main__.py:198`).
- **O CI não muda:** usa `localhost:5432/estoque` num Postgres efêmero, com as três
  variáveis explícitas em `.github/workflows/ci.yml:45-49`.

## Decisão

- **Mesmo container, database novo:** `estoque_teste` no Postgres do compose.
  Container novo exigiria pergunta (ADR-0028) e não compra nada a mais.
- **Criado por `make db-teste`, idempotente:** cria o database se não existir,
  migra e semeia com `uv` local contra `localhost:15432`. **Não** usar
  `docker compose run`, que recria o container do banco sem a porta (a armadilha do
  `make migrate`, `docs/AMBIENTE.md`).
- **Endereço num lugar só:** recomendado um módulo em `api/tests/` com as três
  URLs e a guarda do AC-5. Confira o `pythonpath` do pytest no `api/pyproject.toml`
  antes de escolher onde ele mora, porque `borda.py` é importado como `from borda
  import`. O `conftest.py` da raiz dos testes define `DATABASE_URL` **antes** de o
  app ser importado.

## Arquivos de propriedade exclusiva

```
api/tests/banco.py                       (novo — nome sugerido)
```

## Toca, com registro

```
Makefile                                 alvo db-teste; test-api o menciona
api/tests/conftest.py                    DATABASE_URL do app sob teste
api/tests/server/borda.py                e os outros 12 arquivos com URL padrão
CLAUDE.md                                §3: db-teste na tabela e na armadilha
api/CLAUDE.md                            "Testes de banco pulam sem Postgres"
docs/AMBIENTE.md                         seção nova: por que dois databases
```

## Critérios de aceite

- [ ] **AC-1** `make db-teste` cria `estoque_teste` se não existir, aplica as
      migrações e o seed. Rodar duas vezes seguidas não falha.
- [ ] **AC-2** Os testes de imutabilidade (`tests/data/test_imutabilidade_no_banco.py`)
      **passam** contra `estoque_teste`, sem pular. É a prova de que papel e `GRANT`
      valem no database novo.
- [ ] **AC-3** `make test-api` e `uv run pytest` direto usam `estoque_teste`, e o app
      sob teste também. A mesma contagem de testes de antes, zero skip com
      `make db-local && make db-teste`.
- [ ] **AC-4** Depois de um `make test-api` completo, as contagens de `usuario`,
      `sessao`, `auditoria` e `movimento` do banco `estoque` são **as mesmas** de
      antes. *(negativo — verificação executada, números no fechamento)*
- [ ] **AC-5** Suíte apontada para o banco de desenvolvimento (porta `15432`,
      database `estoque`) **falha na coleta**, com mensagem que manda rodar
      `make db-teste`. Não pula: pular esconderia a volta do problema. O CI
      (porta `5432`) não é afetado. *(negativo)*
- [ ] **AC-6** Sem Postgres nenhum, os testes de banco continuam pulando com
      "sem banco", e o portão do CI ("nenhum teste pulou") continua reprovando.

## Não faz

- **Limpar o banco de desenvolvimento:** feito à mão em 2026-09-14, com
  `make reset`.
- **Testes de ponta a ponta:** são da [T-053](./T-053-e2e-playwright.md), que usa
  este banco.
- **Transação com rollback por teste:** não serve. O app sob teste abre as próprias
  conexões e faz commit, então o rollback da fixture não alcança o que ele gravou.
