# ADR-0006 — Uma declaração produz validador, descrição, carga, projeção, render e comandos

| | |
|---|---|
| **Status** | **Substituído por [ADR-0017](./0017-registry-servidor-views-cliente.md)** em 2026-09-07 |
| **Data** | 2026-09-06 |
| **Escopo** | Fundacional |

> **Substituído.** O mecanismo deste ADR — uma declaração única em TypeScript —
> tornou-se impossível com o [ADR-0016](./0016-api-python-cliente-typescript.md)
> (API em Python, cliente em TypeScript). **O alvo continua válido** e foi
> mantido: evitar que a lista que o modelo conhece divirja da lista que o sistema
> sabe renderizar. O [ADR-0017](./0017-registry-servidor-views-cliente.md) troca o
> mecanismo — duas declarações ligadas por id, com bijeção verificada em CI —
> sem trocar o alvo. Preservado aqui pelo raciocínio.

## Contexto

Sistemas assim apodrecem de um jeito específico: existe a lista de componentes que
o modelo conhece, e existe a lista de componentes que o sistema sabe renderizar.
As duas divergem. O modelo passa a propor o que não existe, ou deixa de propor o
que existe.

A v1 testou a alternativa e o resultado foi o achado mais positivo do documento 00:
o registry como fonte única **funcionou melhor do que o esperado**.

## Decisão

> **`defineComponent` é a fonte única. Registrar um componente produz, de uma
> declaração só: o validador de params, a descrição enviada ao modelo, a carga de
> dados autorizada, a projeção pura, o componente React e as operações de escrita.**

```ts
defineComponent({
  id, label, description, examples, params,   // vocabulário do modelo
  requires, tamanho,                          // permissão e layout
  load, select, render,                       // plano de render
  commands,                                   // plano de escrita
})
```

Não existe segunda lista para esquecer de atualizar.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Catálogo declarado em JSON separado do código | É exatamente a divergência descrita no contexto |
| Geração do catálogo por reflexão sobre os componentes React | Frágil e implícito; a descrição para o modelo não é derivável do JSX |

## Consequências

**Positivas**
- Impossível registrar componente sem descrição, sem validador ou sem `requires` —
  o tipo não compila.
- O custo de token por componente é conhecido e medível na própria declaração
  (~164 tokens na v1).

**Negativas**
- A declaração fica grande e mistura preocupações (dados, permissão, UI) num
  arquivo só. É o preço da fonte única, e foi aceito conscientemente.
- Mudar a assinatura de `defineComponent` toca todos os componentes — daí o
  congelamento do contrato antes da paralelização (ver `tasks/CONTRATOS.md`).

## Conformidade

- `arch:check`: todo arquivo em `registry/componentes/` exporta exatamente uma
  chamada a `defineComponent`.
- Teste: o catálogo servido é derivado do registry, nunca escrito à mão.

## Referências
- [Achados v1 §6](../00-achados-v1.md) · [Arquitetura v2 §4](../03-arquitetura-v2.md)
