# T-039 — Codegen OpenAPI → TypeScript e teste de bijeção

| | |
|---|---|
| **Onda** | W0 — Contratos |
| **Trilha** | C |
| **Tamanho** | M |
| **Depende de** | T-003, T-004 |
| **Bloqueia** | T-015, T-016, toda a W3 |
| **Estado** | ✅ **concluída** em 2026-09-08 |
| **ADRs** | [0016](../adr/0016-api-python-cliente-typescript.md), [0017](../adr/0017-registry-servidor-views-cliente.md) |

## Objetivo

Reconstruir, com tipos gerados e um teste, a garantia que o compilador dava quando
tudo era TypeScript. **Sem esta tarefa, o ADR-0017 é uma regressão em relação ao
ADR-0006.**

## Arquivos de propriedade exclusiva

```
web/scripts/gerar-tipos.ts            web/src/generated/**   (gerado)
api/tests/registry/test_bijecao.py    web/src/views/indice.ts (gerado)
```

## Escopo

### Faz
- `make types`: OpenAPI da API → `openapi-typescript` → `web/src/generated/api.ts`.
- Exporta `ComponentId` como união de literais, e `ViewModel<Id>` por componente.
- `web/src/views/indice.ts` gerado varrendo `web/src/views/*.tsx`.
- **O teste de bijeção**, nos dois lados:

```
todo id registrado na API  → existe exatamente uma view no cliente
toda view no cliente       → existe exatamente um id registrado na API
```

- Cliente HTTP tipado com `openapi-fetch`.

### Não faz
Motor de render (T-015). Views (W3/W4).

## Critérios de aceite

> **Verificado por** `web/src/testes/bijecao.test.ts` (8 testes) e por
> `tsc --noEmit`. Todos os seis foram conferidos **provocando a falha** — a
> regra da casa: regra que nunca falhou não é evidência de nada.

- [x] **AC-1** Registrar componente na API sem criar a view quebra o CI.
      *(negativo — **o critério central desta tarefa**)*
      → *removi `vencimento_grafico` do índice → 1 erro de `tsc` e 2 testes falhando*
- [x] **AC-2** Criar view sem registro correspondente quebra o CI. *(negativo)*
      → *criei `views/orfa.tsx` → `expected [ 'orfa' ] to deeply equal []`*
- [x] **AC-3** `web/src/generated/**` regenerado é idêntico ao versionado; CI falha
      se alguém editou à mão. *(negativo)*
      → *acrescentei uma linha ao gerado → 1 teste falhando; regeneração comparada byte a byte*
- [x] **AC-4** Um `ComponentId` inexistente não compila no cliente.
      → *`const x: ComponentId = 'relatorio_secreto'` → `TS2322: not assignable to type ComponentId`*
- [x] **AC-5** Mudar o viewmodel na API e não regenerar quebra o `typecheck` do
      cliente — a divergência aparece **no build**, não em produção.
      → *renomeei um campo no gerado → 6 erros de `tsc`, incluindo `Property 'total' does not exist`*
- [x] **AC-6** O cliente não tem nenhum tipo de domínio escrito à mão que duplique
      um tipo da API. *(negativo)*
      → *nenhuma view declara `interface VM`; todas importam de `generated/componentes`*

## Armadilhas

O ADR-0006 se orgulhava de não ter uma segunda lista. Agora ela existe. **AC-1 e
AC-2 são o que impede o apodrecimento** que o ADR-0006 descrevia — se forem
desligados ou ficarem frágeis, o sistema volta a divergir em silêncio, e desta vez
sem o compilador avisando.
