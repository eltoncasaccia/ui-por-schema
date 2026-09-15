# T-052 — Banco de teste isolado do banco de desenvolvimento

| | |
|---|---|
| **Trilha** | E · ambiente e qualidade |
| **Tamanho** | M |
| **Depende de** | — |
| **ADRs** | [0033](../adr/0033-e2e-playwright-banco-proprio.md), [0018](../adr/0018-postgres-em-container.md), [0028](../adr/0028-processo-de-decisao.md) |
| **Origem** | achado [A-44](../relatorios/achados-resolvidos.md); primeiro sinal em [R-003 §4](../relatorios/R-003-seguranca-ciclo-1.md) ("Resíduo no banco de desenvolvimento") |
| **Escrita em** | 2026-09-14 |

## Por que existe

Os testes de banco não tinham banco próprio. Sem variável de ambiente, todos caíam
em `localhost:15432/estoque`, que é o mesmo banco do `make up`. Cada execução
deixava usuários, sessões, auditoria e movimentos que **não podem ser apagados**:
`movimento` e `auditoria` são append-only, e apagar o usuário exigiria apagar
linhas delas.

Medido em 2026-09-14, antes de um `make reset` manual: **262 usuários de teste
contra 8 reais**, 3.262 linhas de auditoria, 4.181 sessões, 417 movimentos e 27
lotes. Os usuários apareciam na tela `/usuarios` do diretor. O CI não via o
problema porque usa banco efêmero.

Limpar ao fim de cada teste não resolve: bateria na imutabilidade, que é a regra
que o sistema defende. A saída é **separar os bancos**, não limpar.

## O que já foi conferido

- **O endereço padrão se repetia em 13 arquivos:** `tests/server/borda.py`,
  `tests/registry/test_ac6_leitura_auditada.py`, `tests/data/test_imutabilidade_no_banco.py`,
  `tests/data/test_papel_da_aplicacao.py`, `tests/data/test_minimo_maximo.py` e oito
  em `tests/commands/`. São três variáveis: `DATABASE_URL_TESTE` (dono, psycopg),
  `DATABASE_URL_TESTE_APP` e `DATABASE_URL_TESTE_APP_ASYNC` (papel restrito).
- **O app sob teste apontava para o dev por conta própria:** ele lê `DATABASE_URL`,
  e o padrão em `api/src/estoque/server/config.py:18` é `localhost:15432/estoque`.
  Mais cinco arquivos leem o banco por esse caminho, via `Config.do_ambiente()`:
  `test_papel_da_aplicacao`, `test_minimo_maximo`, `test_produto_por_ean`,
  `test_contrato_da_porta` e `test_repos_recebimento_temperatura`.
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
  migra e semeia com `uv` local contra `localhost:15432`. **Não** usa
  `docker compose run`, que recria o container do banco sem a porta (a armadilha do
  `make migrate`, `docs/AMBIENTE.md`).
- **Endereço num lugar só:** `api/tests/banco.py`, importado como `import banco`. O
  `conftest.py` da raiz dos testes põe `tests/` no `sys.path`.
- **`setdefault`, e não atribuição, da `DATABASE_URL`** *(decidido na execução)*:
  fixar a variável cegaria o `test_papel_da_aplicacao` (A-27), que existe para ler a
  `DATABASE_URL` declarada no ambiente e reprovar o papel dono. Quem declara (o CI)
  continua sendo lido; uma `DATABASE_URL` que caia no dev para a suíte pela guarda.

## Arquivos de propriedade exclusiva

```
api/tests/banco.py
api/tests/data/test_banco_de_teste.py
```

## Toca, com registro

```
Makefile                                 alvo db-teste
api/tests/conftest.py                    DATABASE_URL do app sob teste; a guarda
api/tests/server/borda.py                e os outros 12 arquivos com URL padrão
api/tests/server/test_t050_*, test_t051_*,
api/tests/data/test_contrato_da_porta.py, test_produto_por_ean.py,
api/tests/data/test_repos_recebimento_temperatura.py
                                         só a instrução de skip e a docstring
CLAUDE.md                                §3: db-teste na tabela e na armadilha
api/CLAUDE.md                            "Testes de banco pulam sem Postgres"
docs/AMBIENTE.md                         seção nova: por que dois databases
README.md                                fora da lista original: instrução de ambiente
.claude/skills/executar-tarefa/SKILL.md  fora da lista original: §3 Ambiente
.claude/skills/comando-novo/SKILL.md     fora da lista original: "rode make db-local"
```

Os três últimos ficaram fora da lista escrita, e todos instruíam a rodar o banco
errado. Deixá-los seria a documentação mandando fazer o que a guarda agora recusa.

## Critérios de aceite

- [x] **AC-1** `make db-teste` cria `estoque_teste` se não existir, aplica as
      migrações e o seed. Rodar duas vezes seguidas não falha.
      *Na 1ª execução: "criado estoque_teste", migração até `0007`, seed com 7
      usuários e 178 lotes. Na 2ª: sem erro e sem recriar.*
- [x] **AC-2** Os testes de imutabilidade (`tests/data/test_imutabilidade_no_banco.py`)
      **passam** contra `estoque_teste`, sem pular. É a prova de que papel e `GRANT`
      valem no database novo. *9 de 9 passaram.*
- [x] **AC-3** `make test-api` e `uv run pytest` direto usam `estoque_teste`, e o app
      sob teste também. A mesma contagem de testes de antes, zero skip com
      `make db-local && make db-teste`.
      *883 coletados antes, mais 13 novos: 893 passaram, 1 xfail e 2 skips. Os dois
      skips são o CS-04 com modelo real (`CS04_MODELO_REAL`), intencionais; nenhum é
      por falta de banco. `test_ac3_o_app_sob_teste_le_do_banco_em_que_a_fixture_grava`
      fica vermelho sem o `setdefault`: sabotado, mostrou o app em `…15432/estoque`.*
- [x] **AC-4** Depois de um `make test-api` completo, as contagens de `usuario`,
      `sessao`, `auditoria` e `movimento` do banco `estoque` são **as mesmas** de
      antes. *(negativo — verificação executada)*
      *Antes e depois: usuario=7, sessao=1, auditoria=5, movimento=269, lote=178.
      O `estoque_teste` recebeu 92 usuários e 345 linhas de auditoria na mesma
      execução.*
- [x] **AC-5** Suíte apontada para o banco de desenvolvimento (porta `15432`,
      database `estoque`) **falha antes de coletar**, com mensagem que manda rodar
      `make db-teste`. Não pula: pular esconderia a volta do problema. O CI
      (porta `5432`) não é afetado. *(negativo)*
      *Dois testes por processo filho: `DATABASE_URL_TESTE` apontada para o dev, e
      `DATABASE_URL` com o `db:5432/estoque` do `.env`. Os dois saem com código ≠ 0
      e a mensagem. O par positivo, sem variável nenhuma, roda. Sabotado com a
      guarda desligada: os dois negativos ficaram vermelhos e o positivo, verde. A
      parada é em `pytest_configure` (`UsageError`), antes da coleta.*
- [x] **AC-6** Sem Postgres nenhum, os testes de banco continuam pulando com
      "sem banco", e o portão do CI ("nenhum teste pulou") continua reprovando.
      *Processo filho com o Postgres numa porta fechada: os testes de imutabilidade
      pulam com "sem banco", com código 0. O portão do CI grepa essa frase, e ela
      foi mantida em todas as mensagens.*

## Fechamento — 2026-09-14

O banco de desenvolvimento para de receber escrita de teste. A guarda foi provada
pelos dois lados, e as instruções nos arquivos de teste e na documentação passaram
a mandar para o banco certo. Em dois pontos, a lista escrita estava curta:

- **Arquivos com instrução:** "13 arquivos" era a contagem dos que repetiam a URL.
  Outros cinco leem o banco pela `DATABASE_URL` e só tinham instrução velha
  (`make migrate`, `make seed`), agora corrigida.
- **Contagem de dados:** o `estoque_teste` acumula dados a cada execução, como o
  `estoque` acumulava. Isso é aceitável num banco que só teste lê, e não há alvo
  para recriá-lo. Se um dia precisar: `DROP DATABASE estoque_teste` e
  `make db-teste`.

## Não faz

- **Limpar o banco de desenvolvimento:** feito à mão em 2026-09-14, com
  `make reset`.
- **Testes de ponta a ponta:** são da [T-053](./T-053-e2e-playwright.md), que usa
  este banco.
- **Transação com rollback por teste:** não serve. O app sob teste abre as próprias
  conexões e faz commit, então o rollback da fixture não alcança o que ele gravou.
