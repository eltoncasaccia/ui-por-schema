# ADR-0023 — OpenRouter como provedor, atrás do adaptador

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Ciclo 1 |

## Contexto

O PRD §9 exige medir `claude-haiku-4-5` e `claude-sonnet-5` com o catálogo real.
Não há chave da Anthropic disponível; há chave da **OpenRouter**.

Três caminhos possíveis: SDK nativo da Anthropic (sem chave), **LiteLLM** como
camada de normalização, ou **OpenRouter direto** — que expõe API compatível com
OpenAI em `https://openrouter.ai/api/v1/chat/completions`, com `response_format`
e `tools`, e roteia para modelos Anthropic sob ids `anthropic/*`.

## Decisão

> **OpenRouter, acessado por HTTP compatível com OpenAI, atrás do `AdaptadorModelo`.**

O plano de medição não muda: `anthropic/claude-haiku-4.5` e
`anthropic/claude-sonnet-4.6` continuam sendo os modelos medidos. **Muda o
transporte, não o experimento.**

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **LiteLLM** | OpenRouter **já é** a abstração multi-provedor. LiteLLM por cima é uma segunda camada da mesma coisa, com uma dependência e um conceito a mais para justificar |
| SDK nativo da Anthropic | Sem chave. Fica implementado como segundo adaptador, para quando houver |
| Acoplar direto ao provedor, sem adaptador | Perde o mock determinístico dos testes e amarra o projeto a um fornecedor |

**Quando LiteLLM valeria:** roteamento entre provedores com política de custo,
fallback automático, ou proxy central com orçamento por equipe. Nada disso está
no escopo do ciclo 1, e adotá-lo agora seria complexidade sem contrapartida.

## Consequências

**Positivas**
- Destrava a medição, que é o que decide o projeto (risco R-1).
- O adaptador deixa de ser abstração de uma implementação só — há três:
  OpenRouter, Anthropic nativo e mock. Abstração com um implementador é
  decoração; com três, é fronteira.
- Trocar de provedor vira um arquivo.

**Negativas**
- Latência medida inclui o salto do roteador. **Todo número publicado tem de
  dizer que passou por OpenRouter**, senão a comparação com acesso direto é
  desonesta.
- Uma dependência a mais na cadeia de disponibilidade.

**Riscos aceitos**
- O roteador pode servir o modelo por provedores diferentes entre execuções,
  com latência distinta. Mitigação: fixar provedor quando possível e registrar
  no trace qual atendeu.

## Conformidade

- Sem chave configurada, o adaptador **falha explicitamente**. Nunca cai no mock
  em silêncio — foi o erro central da v1, e desta vez produziria números que
  parecem reais.
- O trace registra `origem`, `modelo` e provedor efetivo. Nenhum número entra em
  relatório sem essa procedência.

## Referências
- [PRD-001 §9](../prd/PRD-001-ciclo-1.md) · [ADR-0024](./0024-decodificacao-restrita.md)
