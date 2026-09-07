# T-039 — Codegen OpenAPI → TypeScript e teste de bijeção

| | |
|---|---|
| **Onda** | W0 — Contratos |
| **Trilha** | C |
| **Tamanho** | M |
| **Depende de** | T-003, T-004 |
| **Bloqueia** | T-015, T-016, toda a W3 |
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

- [ ] **AC-1** Registrar componente na API sem criar a view quebra o CI.
      *(negativo — **o critério central desta tarefa**)*
- [ ] **AC-2** Criar view sem registro correspondente quebra o CI. *(negativo)*
- [ ] **AC-3** `web/src/generated/**` regenerado é idêntico ao versionado; CI falha
      se alguém editou à mão. *(negativo)*
- [ ] **AC-4** Um `ComponentId` inexistente não compila no cliente.
- [ ] **AC-5** Mudar o viewmodel na API e não regenerar quebra o `typecheck` do
      cliente — a divergência aparece **no build**, não em produção.
- [ ] **AC-6** O cliente não tem nenhum tipo de domínio escrito à mão que duplique
      um tipo da API. *(negativo)*

## Armadilhas

O ADR-0006 se orgulhava de não ter uma segunda lista. Agora ela existe. **AC-1 e
AC-2 são o que impede o apodrecimento** que o ADR-0006 descrevia — se forem
desligados ou ficarem frágeis, o sistema volta a divergir em silêncio, e desta vez
sem o compilador avisando.
