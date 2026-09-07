# ADR-0001 — Compor a interface por schema, nunca por código gerado

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-06 |
| **Escopo** | Fundacional — vale para todos os ciclos |

## Contexto

A hipótese do produto é ter uma IA compondo interface em tempo real. Existem dois
caminhos conhecidos:

1. **O modelo gera código** (JSX/HTML) e o código roda no navegador.
2. **O modelo escolhe composição** a partir de um catálogo de componentes já
   escritos, emitindo apenas nomes e parâmetros.

O caminho 1 é o que o Claude faz no chat — e mesmo lá o código gerado roda num
iframe de origem separada, sem acesso a dados. Nem quem o gera confia nele.

A POC v1 mediu os dois lados:

| | tokens |
|---|---|
| Schema de tela com 3 componentes | **~60** |
| Panorama de 6 componentes | ~123 |
| Componente React equivalente, gerado | ~800–2000 |

E testou o caminho 2 com entrada hostil: `{"type":"RandomReactComponent"}`,
`{"type":"<script>alert(1)</script>"}`, métrica fora do enum e CSS injetado em
campo de layout — **todos rejeitados**.

## Decisão

> **O modelo emite apenas um schema: nomes de componentes registrados e parâmetros
> validados. Nunca código, nunca dados, nunca markup, nunca estilo.**

O schema **não tem onde carregar código**: não existe campo para markup, estilo,
valor literal ou expressão. Isso é propriedade da estrutura de dados, não promessa
de prompt.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Modelo gera React em sandbox (L3) | Sandbox implica origem isolada e sem dados. Este produto **é** dados e permissão. Serve quando o artefato é o entregável — não é o caso |
| Modelo gera SQL ou filtro livre | Move o problema de autorização para dentro de uma string. Pior versão do mesmo risco |
| Modelo escolhe rota e nada mais (só L1) | Perde o panorama sob demanda, que é metade do valor. Ver ADR-0005 |

## Consequências

**Positivas**
- Uma ordem de grandeza menos tokens. É a diferença entre "a tela aparece" e "a
  tela é digitada na sua frente".
- Superfície de ataque fechada por construção, não por filtro.
- O componente é escrito por humano: acessibilidade, i18n e design system valem.

**Negativas**
- **O modelo só consegue expressar o que existe no catálogo.** Pergunta legítima
  fora do vocabulário não tem resposta parcial — tem resposta errada ou vazia.
- Todo recorte novo exige código novo. Não há escape hatch.
- O catálogo tem custo de prompt linear — ver ADR-0011.

**Riscos aceitos**
- Cobertura desconhecida: se este caminho responde 60% ou 95% das perguntas reais
  de um operador é pergunta em aberto desde a v1, e o ciclo 1 mede (PRD-001 §9).

## Conformidade

- O tipo `ViewSchema` não possui campo de texto livre renderizável. Teste que falha
  se um campo `string` não pertencente a um enum for adicionado sem validador.
- Testes adversariais de `CS-01` em T-033.

## Referências
- [Achados v1 §4](../00-achados-v1.md) — registry como fronteira de segurança
- [Arquitetura v2 §1 e §3](../03-arquitetura-v2.md)
