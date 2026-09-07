# T-016 — TanStack Query, viewKey e URL

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-013, T-015 |
| **Bloqueia** | T-017 |
| **ADRs** | [0008](../adr/0008-tanstack-query.md), [0021](../adr/0021-viewkey-e-viewid.md) |
| **Requisitos** | RF-19 |

## Objetivo

Resolver os dois mecanismos que a v1 escreveu à mão — invalidação de pedido
superado e coalescing — e dar endereço à composição.

## Arquivos de propriedade exclusiva

```
web/src/query/*.ts   web/src/state/sessao.ts   web/src/app/rotas.tsx
web/src/query/*.test.ts
```

## Escopo

### Faz
- `QueryClient` configurado; `queryKey` derivada de `[atorId, componenteId, params]`.
- Store observável mínimo para sessão do assistente: pergunta corrente, trace,
  composição ativa. **Só isso** (ADR-0008).
- Rota **`/v/:viewId`** — o endereço público é opaco e revogável; `view_key`
  nunca aparece em URL ([ADR-0021](../adr/0021-viewkey-e-viewid.md)).
- Ao abrir uma `viewKey`: **revalida o schema contra o catálogo do requisitante** e
  carrega sob a autenticação dele.

### Não faz
Compartilhamento entre usuários (ciclo 2, NO-6). Aqui só identidade e endereço.

## Critérios de aceite

- [ ] **AC-1** Toda `queryKey` contém o id do ator. Teste percorre as chaves geradas
      e falha se alguma não contiver. *(ADR-0008, risco de cache cruzado)*
- [ ] **AC-2** Abrir a view A e imediatamente a B: a resposta tardia de A **não**
      sobrescreve B. *(invalidação de pedido superado)*
- [ ] **AC-3** Quatro blocos da mesma entidade disparam **uma** requisição.
      *(coalescing)*
- [ ] **AC-4** Recarregar `/v/:viewId` reproduz a mesma tela. *(o bug do favorito
      da v1)*
- [ ] **AC-4b** `viewId` revogado devolve `nao_encontrado`; a `view_key` continua
      válida e o favorito sobrevive. *(ADR-0021)*
- [ ] **AC-5** Uma `viewKey` criada por Marco, aberta por Odair, carrega sob a
      permissão de Odair — ou nega. **Nunca devolve dado de Marco.**
      *(negativo — ADR-0009, escalação de privilégio)*
- [ ] **AC-6** Uma `viewKey` cujo schema referencia componente fora do catálogo do
      requisitante é rejeitada na abertura. *(negativo)*
- [ ] **AC-7** `arch:check` confirma que nenhum componente de apresentação importa
      TanStack Query.

## Armadilhas

**AC-5 é o critério de segurança desta tarefa.** Endereço de view que carrega dado
com a permissão de quem criou é escalação de privilégio disfarçada de conveniência.
