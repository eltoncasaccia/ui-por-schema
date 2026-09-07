# ADR-0008 — Usar TanStack Query para estado de servidor

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-06 |
| **Escopo** | Ciclo 1 |

## Contexto

A v1 escreveu o próprio store observável (40 linhas, lido por `useSyncExternalStore`)
e orquestrou tudo fora do React, com zero `useEffect`. Funcionou — e o documento 00
registra a ressalva honesta: *"um app React comum com Zustand + TanStack Query
também teria componentes finos. Esse número impressiona menos do que parece."*

Sem `useEffect`, dois mecanismos viraram responsabilidade da casa:

1. **Invalidação de pedido superado** — abrir A e logo B não pode deixar a resposta
   de A sobrescrever B. A v1 resolveu com token de slot, checado depois de todo `await`.
2. **Coalescing de requisições** — quatro componentes da mesma entidade disparam
   quatro consultas idênticas. A v1 resolveu compartilhando promessas em voo.

Ambos são de graça em TanStack Query. Com composição dinâmica os dois são *mais*
prováveis que num app por rota, porque o modelo compõe várias vistas da mesma
entidade na mesma resposta.

## Decisão

> **TanStack Query para todo estado de servidor. Store observável mínimo apenas
> para estado de sessão do assistente (pergunta corrente, trace, composição ativa).**

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Reescrever o store da v1 | A v1 concluiu que o store à mão **não é a parte valiosa**. Recriar é pagar de novo por invalidação e coalescing |
| Zustand + fetch manual | Zustand resolve estado de cliente, não cache de servidor. Os dois mecanismos continuariam nossos |
| RTK Query | Equivalente técnico; peso maior e sem Redux no projeto |

## Consequências

**Positivas**
- Invalidação por chave, coalescing e deduplicação vêm prontos e testados.
- `queryKey` casa naturalmente com `viewKey` (ADR-0009).

**Negativas**
- **Não afrouxa ADR-0007.** `useQuery` não é `useEffect`, e a regra de "componente
  não busca dado" continua valendo: quem chama `useQuery` é o motor de render, não
  o componente de apresentação.
- Dependência externa numa camada que a v1 mantinha própria.

**Riscos aceitos**
- Configuração de cache errada pode servir dado de outra unidade a outro ator.
  Mitigação: **a identidade do ator entra na `queryKey`**, obrigatoriamente.

## Conformidade

- `arch:check`: `components/**` não importa `@tanstack/react-query`.
- Teste: toda `queryKey` construída pelo motor de render contém o id do ator.
  Falha se alguma não contiver.

## Referências
- [Achados v1](../00-achados-v1.md) · [Arquitetura v2 §9](../03-arquitetura-v2.md)
