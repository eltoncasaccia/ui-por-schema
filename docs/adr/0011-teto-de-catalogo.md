# ADR-0011 — Limitar o catálogo a 25 componentes e não implementar recuperação

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Ciclo 1 |

## Contexto

Número medido na v1: **~164 tokens por componente registrado** no prompt, em toda
pergunta. A conta é linear e implacável:

| Componentes | Tokens de catálogo por pergunta |
|---|---|
| 7 (a v1) | ~1,1k |
| 23 (ciclo 1) | **~3,8k** |
| 25 | ~4,1k |
| 60 | ~10k |

> **Não escala por adição.**

Passando de ~25 componentes torna-se obrigatório recuperar catálogo — buscar só os
relevantes à pergunta. Isso é outro sistema, com falhas próprias: o componente
certo pode não ser recuperado, e a falha é **silenciosa** (ver risco R-5 do PRD).

## Decisão

> **O catálogo do ciclo 1 tem 23 componentes e o teto é 25, verificado por teste
> que falha o build. Recuperação de catálogo não é implementada neste ciclo.**

Composição dos 23: 15 de leitura, 7 de escrita, 1 utilitário (`confirm_action`).

Duas fusões deliberadas mantiveram a conta abaixo do teto:
- `rastreabilidade` cobre `RN-D03` e `RN-D04` com enum de direção — é a mesma
  pergunta, dois sentidos.
- `lote_status_acao` cobre bloquear, desbloquear e liberar vencimento ≤30 d — três
  transições do mesmo formulário, todas privativas do RT.

Ambas preservam a regra do ADR-0001: **o recorte continua existindo como valor
nomeado no enum.**

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Implementar recuperação desde já | Otimização para um problema que 23 componentes não têm, adicionando um modo de falha silencioso |
| Aceitar 40 componentes com prompt maior | ~6,5k tokens por pergunta, em toda pergunta. Custo e latência sem contrapartida |
| Catálogo por área, escolhido por heurística | É recuperação com outro nome, e com heurística pior |

## Consequências

**Positivas**
- Prompt previsível e barato; nenhuma etapa de recuperação entre a pergunta e a
  composição.
- Força modelagem econômica: params e enums em vez de proliferação de componentes.

**Negativas**
- **Folga de apenas 2 componentes.** Qualquer feature nova no ciclo 1 exige cortar
  outra ou revisar este ADR.
- O ciclo 2 (contagem, transferência) provavelmente estoura o teto e obriga a
  encarar recuperação.

## Conformidade

- `RNF-08`: teste afirma `catalogo.length <= 25` e falha o build acima disso.
- Teste de orçamento: soma dos tokens de descrição do catálogo por persona, com
  limite de alerta em 4k.

## Referências
- [Arquitetura v2 §10](../03-arquitetura-v2.md) · [Achados v1](../00-achados-v1.md)
