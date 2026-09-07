# ADR-0005 — L2 para leitura, L1 para escrita

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-06 |
| **Escopo** | Fundacional |

## Contexto

Dado que o modelo compõe (ADR-0001), quanta liberdade ele recebe? Três níveis
possíveis:

| Nível | O modelo produz |
|---|---|
| **L1 — Roteamento** | uma view registrada + parâmetros |
| **L2 — Composição** | schema compondo vários componentes registrados |
| **L3 — Código** | JSX/HTML arbitrário em sandbox |

L3 está fora por ADR-0001. Resta decidir entre L1 e L2, e a resposta não é a mesma
para leitura e para escrita.

Formulário composto peça por peça quebra em validação cruzada, ordem de campos,
estado entre etapas e foco. É trabalho de UI que o schema não expressa e que o
modelo não tem como acertar de forma estável.

## Decisão

> **L2 para leitura. L1 para escrita.**

- Consultar, comparar, montar panorama → o modelo compõe à vontade.
- Fluxo com etapas, validação cruzada ou wizard → **registrado como uma unidade
  inteira**. O modelo escolhe *qual* formulário abrir; nunca monta formulário peça
  por peça.

L1 responde por ~70% dos casos e é trivialmente seguro; L2 existe para o panorama
sob demanda, que é onde está o valor diferencial.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| L2 também para escrita | Onde isto quebra primeiro, segundo a v1. Não vale a briga |
| L1 para tudo | Perde panorama e comparação — metade do valor do assistente |

## Consequências

**Positivas**
- Ganho colateral grande: **um componente de escrita registrado como unidade
  inteira serve simultaneamente como rota tradicional e como alvo do assistente.**
  Uma declaração, duas superfícies.
- O formulário complexo continua sendo código React normal, testável do jeito normal.

**Negativas**
- Cada formulário novo é um item de catálogo, consumindo orçamento de tokens
  (ADR-0011).
- Variações pequenas de um mesmo formulário viram parâmetro, não composição —
  exige disciplina de modelagem de params.

## Conformidade

- Todo `ComponentDef` com `commands` declara `tamanho: 'inteira'` e não é
  composto junto de outros no mesmo bloco. Teste no validador de schema.

## Referências
- [Arquitetura v2 §3 e §11.1](../03-arquitetura-v2.md)
