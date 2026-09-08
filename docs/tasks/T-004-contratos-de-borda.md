# T-004 — Schema do assistente e envelope HTTP · **congela os contratos**

| | |
|---|---|
| **Onda** | W0 — Contratos · **serial** |
| **Trilha** | C |
| **Tamanho** | M |
| **Depende de** | T-002, T-003 |
| **Bloqueia** | **toda a W1** |
| **ADRs** | [0001](../adr/0001-ui-por-schema.md), [0021](../adr/0021-viewkey-e-viewid.md), [0014](../adr/0014-erros-que-nao-vazam.md), [0019](../adr/0019-autenticacao-e-cadastro.md) |

## Objetivo

Seções 6 e 7 de [CONTRATOS.md](./CONTRATOS.md) em código. **Concluir esta tarefa
congela os contratos** e abre as onze tarefas paralelas de W1.

## Arquivos de propriedade exclusiva

```
api/src/estoque/schema/contrato.py   api/src/estoque/schema/viewkey.py   api/src/estoque/schema/*.test.py
api/src/estoque/server/envelope.py   api/src/estoque/server/rotas.py       (apenas as assinaturas)
```

## Escopo

### Faz
- `ViewSchema` e `Bloco` — sem campo de markup, estilo, layout livre ou literal.
- **`view_key`** — hash do schema canonicalizado, **interno, nunca em URL**.
- **`view_id`** — opaco, ≥128 bits, gerado no servidor, **público e revogável**
  ([ADR-0021](../adr/0021-viewkey-e-viewid.md), achado A-03).
- Canonicalização: chaves ordenadas, `undefined` e defaults removidos, **ordem de
  blocos preservada**, números normalizados.
- `Resposta<T>`, `Meta`, e o serializador único de erro.
- Assinaturas dos quatro endpoints. **Sem implementação** — é T-011.

### Não faz
- Validar contra catálogo (T-013 — o catálogo ainda não existe).
- Servidor HTTP de verdade (T-011).

## Critérios de aceite

> **Verificado por** `tests/schema/test_viewkey.py` — auditado em [A-002](../relatorios/A-002-auditoria-de-execucao.md).

- [ ] **AC-1** `ViewSchema` não aceita campo desconhecido; chave extra é erro de
      validação. *(negativo — ADR-0001)*
- [ ] **AC-2** O mesmo schema com chaves em ordem diferente produz **a mesma**
      `viewKey`. *(ADR-0009)*
- [ ] **AC-3** Trocar a ordem dos **blocos** produz `viewKey` **diferente** — ordem
      é significado.
- [ ] **AC-4** O serializador de erro nunca emite `detalheInterno`, em nenhum
      caminho, incluindo erro inesperado. *(negativo)*
- [ ] **AC-5** Nenhum corpo de erro contém lista de ids. *(negativo — ADR-0014)*
- [ ] **AC-6** `view_key` é estável entre execuções e entre processos — sem
      `hash()` do Python, que é salgado por processo.
- [ ] **AC-7** Recompor a mesma view produz `view_id` **diferente** e `view_key`
      **igual**. *(ADR-0021)*
- [ ] **AC-8** Nenhuma URL do sistema contém `view_key`. *(negativo)*
- [ ] **AC-9** O envelope de escrita exige `Idempotency-Key` e token CSRF.
      *(negativo — achado A-02)*

## Definição de pronto — adicional

- [ ] `CONTRATOS.md` marcado como **CONGELADO** e anunciado no BOARD.
- [ ] Divergência entre `CONTRATOS.md` e o código: **o código é corrigido**.

## Armadilhas

Canonicalização é onde `viewKey` silenciosamente quebra: `{a:1,b:2}` e `{b:2,a:1}`
precisam gerar a mesma chave, e `1` e `1.0` também.
