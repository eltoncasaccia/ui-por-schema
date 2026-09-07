# ADR-0003 — Servir o catálogo filtrado por ator, no servidor

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-06 |
| **Escopo** | Fundacional |

## Contexto

Na v1 o catálogo era uma constante no cliente — a mesma lista para todo mundo. Com
seis papéis, três unidades e campos restritos (`RN-A02`), isso significa oferecer
ao modelo um vocabulário que a pessoa não pode usar.

O problema é mais sutil que "o botão aparece e dá erro". O modelo **propõe** com
naturalidade, e a negativa chega depois, como falha do sistema, não como limite.

## Decisão

> **O catálogo é gerado no servidor, por requisição, filtrado pelas permissões e
> pelas unidades do ator.**

Consequências concretas com os papéis do documento 02:

- Cleide não tem `custo.ler` → nenhum componente que exponha custo entra no
  catálogo dela → o modelo **não consegue nem propor**.
- Odair tem escopo de unidade → os componentes chegam com o escopo já aplicado.
- Helena é a única com `lote.liberar` → só o catálogo dela contém o componente de
  liberação de quarentena.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Catálogo único + filtro na resposta | O modelo propõe o impossível e o usuário aprende que o sistema falha |
| Catálogo único + instrução no prompt ("não ofereça custo a conferentes") | Permissão dependendo do modelo. Inaceitável |
| Catálogo no cliente, filtrado no cliente | O cliente é o atacante em potencial (ver ADR-0004) |

## Consequências

**Positivas**
- Elimina a classe inteira de erro "o modelo ofereceu o que a pessoa não pode ter".
- O prompt encolhe: cada ator carrega só o seu vocabulário.
- `CA-05` e `CA-06` ganham defesa em profundidade.

**Negativas**
- O catálogo passa a ser dado dinâmico: não dá para cachear globalmente, e o cache
  de prompt do provedor perde eficácia entre atores diferentes.
- Teste fica combinatório: cada componente precisa ser testado presente **e**
  ausente, por papel.

**Riscos aceitos**
- Filtragem é higiene, não garantia. **A garantia é a autorização em cada `load` e
  cada `command`** — ADR-0004.

## Conformidade

- Teste parametrizado por persona: para cada um dos seis papéis, afirmar o conjunto
  exato de ids de componente no catálogo. Falha se entrar ou sair um.
- Teste `CS-02`: nenhum componente com `requires` contendo `custo.ler` aparece no
  catálogo de Cleide, Helena, Ivo ou Odair.

## Referências
- [Arquitetura v2 §5](../03-arquitetura-v2.md) · [Matriz de permissões](../02-regras-de-negocio.md)
