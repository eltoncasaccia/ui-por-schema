# ADR-0013 — Suíte de avaliação como rede de regressão

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Ciclo 1 |

## Contexto

UI não-determinística não tem teste de regressão comum. Mudar uma palavra na
`description` de um componente, acrescentar um componente ao catálogo ou trocar de
modelo pode alterar composições que funcionavam — **sem quebrar nenhum teste e sem
erro em lugar nenhum**.

É o mesmo formato do risco R-5: a falha não se manifesta como exceção, se manifesta
como resposta pior.

## Decisão

> **Uma suíte de ~40 perguntas com composição esperada, executada em CI a cada
> mudança de catálogo, de prompt ou de modelo. Desde a primeira semana.**

Cada caso registra: pergunta, persona, catálogo esperado, composição esperada
(conjunto de ids, não ordem exata) e a regra ou critério que justifica o caso.

Quatro métricas por execução:

| Métrica | Alvo |
|---|---|
| Taxa de schema válido | ≥ 95% |
| Taxa de composição correta dado schema válido | ≥ 85% |
| p95 até o primeiro componente | ≤ 3 s |
| Tokens de entrada por pergunta | alerta em 4k |

A suíte cobre também **casos negativos por persona**: Cleide perguntando por custo,
Odair perguntando por Ribeirão. Composição correta ali significa **não** compor.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Testes unitários do parser apenas | Foi o erro da v1: o mock acerta porque foi escrito para acertar |
| Revisão manual a cada mudança | Não escala e não produz série histórica |
| Snapshot da composição | Frágil demais: qualquer variação legítima quebra tudo |

## Consequências

**Positivas**
- Produz a série histórica que responde a pergunta central do projeto.
- Torna visível a degradação silenciosa por crescimento de catálogo.

**Negativas**
- Custa tokens a cada execução em CI. Mitigação: rodar completa apenas quando
  catálogo, prompt ou modelo mudam; subconjunto de fumaça nos demais commits.
- Composição esperada é julgamento humano e pode envelhecer mal.

**Riscos aceitos**
- Alvos de 95% e 85% são hipóteses, não linhas de base. **A primeira execução
  define a linha de base real** e os alvos são revisados com o número em mãos.

## Conformidade

- CI falha se a taxa de schema válido cair mais de 5 pontos percentuais em relação
  à execução anterior registrada.

## Referências
- [Arquitetura v2 §12.6](../03-arquitetura-v2.md) · [PRD-001 §9](../prd/PRD-001-ciclo-1.md)
