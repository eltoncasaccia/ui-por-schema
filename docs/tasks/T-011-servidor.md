# T-011 — Servidor: autenticação, rotas e autorização por registro

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | B |
| **Tamanho** | **G** |
| **Depende de** | T-009, T-010 |
| **Bloqueia** | T-017, T-025 |
| **ADRs** | [0004](../adr/0004-autorizacao-em-tres-momentos.md), [0014](../adr/0014-erros-que-nao-vazam.md) |
| **Requisitos** | CS-01, CS-03, CS-05, CS-06 |

## Objetivo

A borda. É aqui que "schema é payload não-confiável" deixa de ser frase e vira
código.

## Arquivos de propriedade exclusiva

```
api/src/estoque/server/app.py   api/src/estoque/server/rotas/*.py
api/tests/server/*.py
```

> **Corrigido na execução.** A lista dizia `api/src/estoque/server/*.test.py`,
> caminho que nunca existiu — os testes de borda moram em `api/tests/server/`,
> onde os desta tarefa já estavam. E `server/middleware/*.py` também não existe:
> o CSRF é `@app.middleware("http")` dentro de `app.py`, de propósito
> ([ADR-0032](../adr/0032-borda-http-por-router.md)) — dependência esquecida numa
> rota nova é buraco silencioso, e rota nova é o que se acrescenta com pressa.

## Só leitura

`api/src/estoque/autorizacao/**`, `api/src/estoque/auditoria/**`, `api/src/estoque/application/schema/**`

## Escopo

### Faz
- Autenticação → `Ator` resolvido a cada requisição. Sem ator, `nao_autenticado`.
- Os quatro endpoints de CONTRATOS §7.
- **Autorização por registro** em cada `load` e cada `command` — o terceiro momento
  do ADR-0004.
- `Idempotency-Key` obrigatório em escrita não idempotente; `If-Match` em update.
- Rate limit por ator no endpoint do assistente (`CS-06`).
- Serializador único de erro — nada de `detalheInterno`, nada de stack.
- Auditoria de toda requisição.

### Não faz
Comandos de domínio (T-025 e W4). Aqui só a borda e o despacho.

## Critérios de aceite

> **Os testes de borda desta tarefa são de HTTP, contra o app real.** Os que
> existiam antes (`test_erros_da_borda.py`) afirmam por `inspect.getsource` que
> o handler existe **no código** — um handler registrado com o decorador errado
> passa neles. Os quatro arquivos novos falam pela rede.
>
> **Cada proteção foi sabotada de propósito para provar que o teste quebra**:
> rota pública sem justificativa, teto do assistente desligado, handler genérico
> ecoando a exceção, e negativa ecoando o id pedido. As quatro reprovaram.

- [x] **AC-1** Requisição sem ator devolve `nao_autenticado` em **todas** as rotas.
      *(negativo)*
      — a varredura vem do próprio `app.openapi()`, com uma lista `PUBLICAS`
      explícita e justificada rota a rota: **rota nova reprova por padrão**, e
      quem a adiciona ou exige sessão, ou escreve ali por que pode ser pública.
      10 rotas protegidas cobertas. Sessão inventada == sessão ausente.
      `test_t011_ac.py::test_ac1_*`.
- [x] **AC-2** Schema forjado, com componente fora do catálogo do ator, enviado
      direto a `/api/componentes/:id/dados` sem passar pelo modelo, é rejeitado.
      *(`CS-01` — o critério central desta tarefa)*
      — as três forjas, pelo endpoint: componente fora do catálogo (Rafael pede
      `movimento_lista`), **valor** de enum filtrado por permissão (Cleide pede
      `metrica=valor_em_estoque`) e unidade fora do escopo (Odair pede
      `cd-matriz`). Cada uma com o contraponto de quem pode — sem ele, uma rota
      que recusasse tudo passaria. `test_cs01_forja_no_endpoint.py`, 14 testes.
- [x] **AC-3** Duas requisições com a mesma `Idempotency-Key` produzem **um** efeito.
      — entregue na T-025 e testado pela borda em
      `tests/commands/test_borda_comandos.py`, com o par negativo (sem a chave,
      a rota recusa).
- [x] **AC-4** `If-Match` com etag antigo devolve `conflito`, sem aplicar.
      — idem T-025; etag correto aplica e devolve etag novo.
- [x] **AC-5** Erro inesperado (exceção não tratada) devolve envelope genérico, sem
      stack e sem detalhe. *(negativo)*
      — exceção que **não** é `ErroDominio` levantada dentro do handler: 500 com
      corpo exatamente `{"ok": false, "erro": {"codigo": "invalido", "mensagem":
      "Erro interno."}}`, sem a mensagem da exceção, sem `RuntimeError`, sem
      `Traceback`, sem caminho de arquivo. E o contraponto que faltava: os erros
      de domínio **não** foram engolidos pelo handler genérico.
      `test_t011_ac.py::test_ac5_*`.
- [x] **AC-6** Rate limit por ator dispara `limite` e é registrado em auditoria.
      — **não existia** (achado [A-34](./ACHADOS.md)): a T-040 entregou rate
      limit no *login* e o rotulou `CS-06`, mas `CS-06` é o endpoint do
      assistente. Implementado em `rotas/assistente.py`: 30 composições por ator,
      120 por IP, janela de 5 min, conferidas **antes** de falar com o modelo.
      Provado que a requisição bloqueada **não chega ao modelo** (adaptador
      espião conta 0 chamadas), que a recusa é auditada e que o registro
      **sobrevive ao `raise`**, que bloquear um ator não bloqueia outro, e que a
      chamada bem-sucedida também gasta cota — a diferença para o login, onde só
      a falha conta. `test_cs06_limite_do_assistente.py`, 9 testes.
- [x] **AC-7** Resposta a id inexistente e a id fora de escopo são **byte a byte
      idênticas**. *(negativo — ADR-0014, `CS-03`)*
      — comparação de `r.content` em bytes, mais status e cabeçalhos (menos
      `date`/`server`), como a armadilha manda. Vale para `lote_detalhe` **e**
      `recebimento_detalhe` (o mais novo, T-022), com os dois contrapontos: o
      dono do escopo vê o lote dele, e quem alcança a Matriz vê o lote que Odair
      não vê — é o que prova que a negativa dele é de escopo, não de
      inexistência. `test_cs03_negativa_identica.py`, 7 testes.
- [x] **AC-8** Toda requisição bem-sucedida gera evento de auditoria. *(`CS-05`)*
      — verificado no recorte **"toda leitura de dado de domínio"**, com a razão
      registrada no achado [A-35](./ACHADOS.md): o AC é mais largo que o `CS-05`
      que cita, e auditar `/api/catalogo`, `/api/auth/eu` e `/api/saude` encheria
      a trilha de navegação. Coberto: `/api/componentes/*/dados` (4 componentes),
      com o par negativo — requisição recusada **não** vira evento de leitura —,
      e o evento carrega quem olhou e com quais params. `test_t011_ac.py::test_ac8_*`.

## Armadilhas

AC-7 quebra por detalhe: tempo de resposta diferente, header a mais, ordem de
chaves no JSON. Comparar o corpo serializado, não o objeto.

**Feito assim:** a comparação é de `r.content` (bytes) e do dicionário de
cabeçalhos, não de `r.json()` — dois dicionários iguais podem ter serializações
diferentes, e é a serialização que vai pelo fio. **Tempo de resposta não é
medido**: teste de timing na suíte de unidade é instável, e o canal lateral de
tempo aqui é fraco (os dois caminhos passam pela mesma consulta). Fica anotado
como limite conhecido deste AC, para a T-033.
