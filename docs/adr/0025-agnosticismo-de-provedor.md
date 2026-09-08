# ADR-0025 — Provedor de modelo trocável por configuração

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-08 |
| **Escopo** | Fundacional |
| **Emenda** | [ADR-0023](./0023-provedor-de-modelo.md) — que escolhia OpenRouter mas amarrava a fiação |

## Contexto

O ADR-0023 escolheu OpenRouter e definiu `AdaptadorModelo` como porta. Mas o
servidor instanciava `AdaptadorOpenRouter` **direto**: a abstração existia e a
fiação a ignorava. Trocar de provedor exigia editar código — exatamente o que
uma porta deveria evitar.

E o modo de saída assumia `response_format: json_schema` universal, o que é
falso: modelos abertos servidos por Ollama, vLLM ou Groq costumam ter tool
calling e não ter saída estruturada estrita.

## Decisão

> **O provedor e o modo de saída são configuração, não código. Sem chave, o
> adaptador levanta — nunca cai no mock.**

```
PROVEDOR=openrouter   roteador multi-modelo (padrão)
PROVEDOR=compativel   QUALQUER API compatível com OpenAI, via LLM_BASE_URL
PROVEDOR=anthropic    SDK nativo
PROVEDOR=mock         determinístico, só teste — nunca escolhido sozinho
```

`compativel` é o que dá agnosticismo de verdade: um adaptador e uma URL cobrem
Ollama local, vLLM, Groq, Together, Azure e LM Studio.

### Três modos de saída, com queda automática

| Modo | Como | Suporte |
|---|---|---|
| `restrito` | `response_format: json_schema` | melhor, nem todo provedor tem |
| `ferramenta` | tool calling | mais amplo, uma indireção a mais |
| `livre` | JSON solto | universal, e mede a pergunta original da v1 |

O adaptador tenta na ordem e **cai para o próximo** se o provedor recusar o
envelope, registrando no trace **qual valeu**. Cair em silêncio atribuiria o
número medido ao experimento errado.

Os dois envelopes derivam da **mesma** função de schema: duas construções
divergiriam, e a divergência só apareceria em produção.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| LiteLLM | OpenRouter já é a abstração multi-provedor; LiteLLM por cima é uma segunda camada da mesma coisa. E `compativel` cobre o resto com uma URL |
| Exigir `json_schema` | Exclui a maior parte dos modelos abertos, que é justamente quem se roda local |
| Só tool calling | Funciona, mas `json_schema` descreve melhor a intenção: não é uma ferramenta, é o formato da resposta |

## Consequências

**Positivas**
- Rodar com modelo local passa a ser uma variável de ambiente.
- O trace registra modo pedido **e** modo efetivo — o número pertence ao modo
  que de fato valeu.
- Custo vem **relatado pelo provedor**, não estimado por tabela de preço:
  tabela envelhece, e o roteador pode servir por caminhos de preço distinto.

**Negativas**
- Três caminhos de saída para manter e testar.
- A queda automática mascara um provedor mal configurado: ele funciona, só que
  em modo pior. Mitigação: o modo efetivo aparece no Execution Trace.

**Números medidos** (17 casos, Claude Haiku 4.5 via OpenRouter):

| | restrito | livre |
|---|---|---|
| schema válido | 100% | 100% |
| composição correta | 100% | 100% |
| tokens de entrada (médio) | **2078** | **962** |
| custo total | US$ 0,039 | US$ 0,020 |

> **A decodificação restrita mais que dobra os tokens de entrada.** O JSON
> Schema do catálogo viaja em toda pergunta. Com este catálogo de 23
> componentes os dois modos acertam igual — o que torna o custo o único
> critério, e ele favorece o modo livre. Isso pode inverter com catálogo maior
> ou modelo mais fraco, e é o tipo de coisa que só se sabe medindo.

## Conformidade

- Teste: `_adaptador()` do servidor não menciona nenhum adaptador concreto.
- Teste: sem chave, `criar_adaptador()` levanta; o mock só sai se pedido.
- Teste: os dois envelopes usam a mesma função de schema.
- Teste: a cadeia de queda sempre termina em `livre`.

## Referências
- [ADR-0023](./0023-provedor-de-modelo.md) · [ADR-0024](./0024-decodificacao-restrita.md)
