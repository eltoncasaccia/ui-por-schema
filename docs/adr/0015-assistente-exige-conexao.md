# ADR-0015 — Assistente exige conexão; off-line adiado com a contagem

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Ciclo 1 |

## Contexto

`RNF-03`: a filial de Uberlândia perde conexão, e conferência e contagem precisam
tolerar queda e sincronizar depois.

Isso colide de frente com ADR-0003: o catálogo é gerado **no servidor**, por ator.
Sem conexão não há catálogo, e um catálogo em cache é um catálogo de permissões
possivelmente desatualizado — exatamente a classe de erro que o ADR-0003 existe
para eliminar.

Com ADR-0010, o consumidor real de off-line — a contagem — saiu do escopo.

## Decisão

> **O assistente exige conexão. Nenhuma funcionalidade do ciclo 1 opera off-line.**

Off-line volta no ciclo 2, junto com a contagem, que é quem precisa dele — e será
resolvido no lugar certo: **operação off-line sem assistente**, com sincronização
posterior. O assistente permanece on-line em qualquer cenário.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Catálogo em cache local com TTL | Permissão servida por cache é permissão desatualizada. Viola ADR-0003 e ADR-0004 |
| Assistente off-line com catálogo reduzido | Dois catálogos, dois comportamentos, duas superfícies de teste. Custo alto para valor duvidoso sem contagem no escopo |
| Adiar o assistente e entregar off-line primeiro | Inverteria a prioridade de risco: o desconhecido é a taxa de schema válido (R-1), não a sincronização |

## Consequências

**Positivas**
- Remove do ciclo 1 o item técnico mais espinhoso, sem custo de critério de aceite.
- Mantém uma única fonte de verdade para permissão.

**Negativas**
- Uberlândia não ganha nada de novo em queda de conexão neste ciclo — e é a unidade
  com o pior link. É expectativa a alinhar explicitamente com o cliente.

**Riscos aceitos**
- Off-line no ciclo 2 pode exigir mudança no modelo de dados (id gerado no cliente,
  vetor de versão). Mitigação: `RN-M06` (saldo derivado de movimentos) e movimentos
  imutáveis são a base mais favorável possível para sincronização posterior.

## Conformidade

- O endpoint do assistente não tem caminho de fallback off-line. Teste: sem rede, a
  interface exibe estado de indisponibilidade, não composição em cache.

## Referências
- `RNF-03` · [ADR-0003](./0003-catalogo-por-ator.md) · [ADR-0010](./0010-corte-de-escopo-ciclo-1.md)
