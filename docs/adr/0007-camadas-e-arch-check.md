# ADR-0007 — Camadas verificadas por script, não por convenção

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-06 |
| **Escopo** | Fundacional |
| **Emendado por** | [ADR-0016](./0016-api-python-cliente-typescript.md) — o verificador passa a ser dois: `import-linter` no Python, `arch:check` no TypeScript |
| **Emendado por** | [ADR-0030](./0030-layout-de-diretorios.md) — **a tabela de camadas abaixo é a da v1.** Depois do ADR-0016, cinco das nove não existem no `api/`. A decisão deste ADR (verificar por script) continua valendo; o layout vigente está no 0030 |

## Contexto

A v1 tinha nove camadas e um script `arch:check` que falhava o build se um
componente importasse a camada de dados, usasse `useEffect` ou lesse o store
direto. Resultado medido: **zero `useEffect` em `src/`**, componentes com 280
linhas em 8 arquivos.

O detalhe que importa: as regras foram **testadas negativamente** — as três
violações foram introduzidas de propósito para confirmar que o check quebra.

> Uma regra que nunca falhou não é evidência de nada.

## Decisão

> **As camadas são verificadas por `npm run arch:check`, que falha o build. E o
> próprio check tem testes que introduzem violações e afirmam que ele quebra.**

| Camada | Responsabilidade |
|---|---|
| `domain/` | tipos + regras puras. Sem React, sem I/O |
| `data/` | única porta para dados |
| `application/` | queries, commands, pipeline |
| `registry/` | `defineComponent` + catálogo derivado |
| `schema/` | contrato do modelo + validação |
| `render/` | schema → React |
| `viewmodels/` | projeções puras |
| `components/` | apresentação. Não busca dado, não decide regra, não lê store |
| `server/` | endpoints, autorização, auditoria |

**Cortadas e que continuam cortadas:** Context Engine (duplicava session state),
Task Engine (indireção que só renomeava chamadas), Layout Engine como camada (é um
`switch` de 60 linhas).

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Convenção documentada e revisão de PR | Sobrevive a três semanas de pressa. Não sobrevive a seis meses |
| ESLint com `no-restricted-imports` | Cobre imports, não cobre "componente não lê store" nem "sem `useEffect` fora de X". Usado como complemento |

## Consequências

**Positivas**
- Disciplina vira propriedade verificável, e o argumento arquitetural sai da
  discussão de revisão.
- Onboarding de sessão nova é mais barato: o check ensina a regra.

**Negativas**
- O check é código a manter, e um check mal escrito bloqueia trabalho legítimo.
- Exceções precisam ser explícitas e comentadas, senão viram `// eslint-disable`
  espalhado.

## Conformidade

Recursivo, de propósito: `scripts/arch-check.test.ts` introduz cada violação e
afirma que o script sai com código diferente de zero.

## Referências
- [Achados v1 §2](../00-achados-v1.md) · [Arquitetura v2 §9](../03-arquitetura-v2.md)
