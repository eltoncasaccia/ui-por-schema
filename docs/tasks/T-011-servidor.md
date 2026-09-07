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
api/src/estoque/server/app.py   api/src/estoque/server/middleware/*.py   api/src/estoque/server/rotas/*.py
api/src/estoque/server/*.test.py
```

## Só leitura

`api/src/estoque/autorizacao/**`, `api/src/estoque/auditoria/**`, `api/src/estoque/schema/**`

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

- [ ] **AC-1** Requisição sem ator devolve `nao_autenticado` em **todas** as rotas.
      *(negativo)*
- [ ] **AC-2** Schema forjado, com componente fora do catálogo do ator, enviado
      direto a `/api/componentes/:id/dados` sem passar pelo modelo, é rejeitado.
      *(`CS-01` — o critério central desta tarefa)*
- [ ] **AC-3** Duas requisições com a mesma `Idempotency-Key` produzem **um** efeito.
- [ ] **AC-4** `If-Match` com etag antigo devolve `conflito`, sem aplicar.
- [ ] **AC-5** Erro inesperado (exceção não tratada) devolve envelope genérico, sem
      stack e sem detalhe. *(negativo)*
- [ ] **AC-6** Rate limit por ator dispara `limite` e é registrado em auditoria.
- [ ] **AC-7** Resposta a id inexistente e a id fora de escopo são **byte a byte
      idênticas**. *(negativo — ADR-0014, `CS-03`)*
- [ ] **AC-8** Toda requisição bem-sucedida gera evento de auditoria. *(`CS-05`)*

## Armadilhas

AC-7 quebra por detalhe: tempo de resposta diferente, header a mais, ordem de
chaves no JSON. Comparar o corpo serializado, não o objeto.
