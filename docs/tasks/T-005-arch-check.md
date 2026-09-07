# T-005 — Verificadores de arquitetura, nos dois lados

| | |
|---|---|
| **Onda** | W0 |
| **Trilha** | E |
| **Tamanho** | M |
| **Depende de** | T-001, T-002 |
| **Paralelizável com** | T-003, T-004 |
| **ADRs** | [0007](../adr/0007-camadas-e-arch-check.md) emendado por [0016](../adr/0016-api-python-cliente-typescript.md) · [0002](../adr/0002-plano-render-plano-escrita.md), [0008](../adr/0008-tanstack-query.md), [0012](../adr/0012-injecao-de-prompt-via-dado.md), [0018](../adr/0018-postgres-em-container.md) |

## Objetivo

Transformar as decisões de arquitetura em **build que quebra**. Sem isto, ADR é
texto.

Com duas linguagens, são **dois verificadores** — e a disciplina passa a ser
propriedade verificável nos dois lados.

## Arquivos de propriedade exclusiva

```
api/.importlinter          api/tests/arquitetura/**
web/scripts/arch-check.ts  web/scripts/arch-check.test.ts
web/scripts/fixtures-violacao/**
```

## Escopo

### `import-linter` — lado Python

| # | Contrato | ADR |
|---|---|---|
| 1 | `domain` não importa `data`, `server`, `registry`, `assistant` | 0007 |
| 2 | `registry` não importa `server` | 0007 |
| 3 | `assistant` **não importa** `commands` | **0002** |
| 4 | `assistant.prompt` não importa `data` nem `domain.tipos` | **0012** |
| 5 | `domain` e `registry` não importam `sqlalchemy` — só `data` | 0007 |
| 6 | Seed só é importado por `data` e por testes | 0007 |

### `arch:check` — lado TypeScript

| # | Regra | ADR |
|---|---|---|
| 7 | `views/**` não importa `query/`, `generated/api-client` | 0007 |
| 8 | `views/**` não contém `useEffect` | 0007 |
| 9 | `views/**` não importa `@tanstack/react-query` | 0008 |
| 10 | `views/**` não usa `dangerouslySetInnerHTML` | 0001 |
| 11 | `generated/**` é gerado — falha se editado à mão | 0017 |
| 12 | Nenhuma string `postgres://` no bundle | **0018** |

> A regra do ADR-0006 (*"`registry/componentes/*` exporta exatamente um
> `defineComponent`"*) **morreu com a substituição pelo ADR-0017**. Seu papel foi
> assumido pelo teste de bijeção de [T-039](./T-039-codegen-e-bijecao.md).

### Não faz
Lint de estilo — é `ruff` e ESLint.

## Critérios de aceite

- [ ] **AC-1** Cada uma das 12 regras tem teste que **introduz a violação e afirma
      que o verificador falha**. *(negativo — o item que vale)*
- [ ] **AC-2** Em repositório limpo, os dois saem com código 0.
- [ ] **AC-3** A saída nomeia arquivo, linha e regra violada.
- [ ] **AC-4** Os dois rodam em menos de 5 s cada — se demorar, ninguém roda antes
      de commitar.
- [ ] **AC-5** CI executa os dois e falha o merge.
- [ ] **AC-6** A regra 3 é testada com um import indireto, em dois saltos.
      *(negativo — [ADR-0002](../adr/0002-plano-render-plano-escrita.md) é a tese
      do projeto; import transitivo a quebraria em silêncio)*

## Armadilhas

Regra que nunca falhou não é evidência de nada — **AC-1 é o critério real desta
tarefa**, e AC-6 é o que impede a regra mais importante de ser contornada por
indireção.
