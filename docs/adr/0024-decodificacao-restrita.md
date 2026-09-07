# ADR-0024 — Decodificação restrita, e o que ela faz com a métrica

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Ciclo 1 |
| **Afeta** | [PRD §9](../prd/PRD-001-ciclo-1.md) · [ADR-0013](./0013-suite-de-avaliacao.md) |

## Contexto

A pergunta que a POC v1 deixou em aberto, e que o ciclo 1 existe para responder:

> **Com que frequência um modelo real emite schema válido?**

Ela foi formulada em 2025, quando a resposta dependia de o modelo produzir JSON
bem-formado por conta própria. **A premissa mudou.** Provedores hoje oferecem
`response_format` com `json_schema` estrito: o modelo é *impedido*, na
decodificação, de emitir algo fora do schema.

E há um passo adiante, específico deste desenho: o campo `tipo` pode ser um
**enum contendo apenas os ids do catálogo deste ator**. O modelo fica
literalmente incapaz de nomear um componente que a pessoa não pode usar.

## Decisão

> **Usar decodificação restrita em produção, com o enum de `tipo` gerado do
> catálogo do ator. E medir os dois modos na suíte de avaliação.**

### Isso NÃO substitui a validação no servidor

Terceira camada, não troca de camada. O cliente continua podendo montar um schema
à mão e enviar direto ao endpoint, sem passar pelo modelo — e ali a decodificação
restrita não existe. As três checagens do [ADR-0004](./0004-autorizacao-em-tres-momentos.md)
seguem valendo, e a autorização em cada `load` continua sendo a única garantia.

### O que acontece com a métrica

| Métrica | Modo livre | Modo restrito |
|---|---|---|
| JSON parseável | mede algo real | **~100%, deixa de informar** |
| Schema válido contra o catálogo | mede algo real | ~100% para `tipo`; params ainda podem falhar |
| **Composição correta** | mede | **mede — e vira a métrica que importa** |

> **A pergunta da v1 se dissolve parcialmente, e é honesto dizer isso.** Com
> decodificação restrita, o risco migra de *"o modelo emite JSON válido?"* para
> *"o modelo escolhe o componente certo?"* — que sempre foi a pergunta difícil,
> e que nenhuma restrição de decodificação resolve.

Por isso a suíte mede **os dois modos**: o número do modo livre responde à
pergunta original e é comparável com a v1; o do modo restrito é o que o sistema
realmente entrega.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Só modo livre | Entrega pior um sistema que poderia ser mais confiável, para preservar a pureza de um experimento |
| Só modo restrito | Perde a resposta à pergunta que motivou o ciclo, e a comparação com a v1 |
| Tool calling em vez de `response_format` | Equivalente aqui, com uma indireção a mais. `json_schema` descreve melhor a intenção: não é uma ferramenta, é o formato da resposta |

## Consequências

**Positivas**
- Taxa de composição inválida cai muito em produção.
- O enum por ator vira uma terceira barreira contra o modelo propor o impossível.
- A comparação entre os dois modos é **um resultado interessante por si só** — é
  o tipo de número que quase ninguém publica.

**Negativas**
- O catálogo passa a ser serializado duas vezes: como texto no prompt e como
  JSON Schema. Divergência entre as duas é um modo de falha novo, e precisa de
  teste.
- Nem todo modelo do roteador suporta `json_schema` estrito. O adaptador precisa
  detectar e cair para modo livre — **registrando no trace**, nunca em silêncio.
- Schema grande consome tokens de entrada e pode reduzir a qualidade da escolha.

**Riscos aceitos**
- Restringir a decodificação pode empurrar o modelo a compor *alguma coisa*
  quando o certo seria não compor. **Os casos negativos da suíte** — Cleide
  pedindo custo, Odair pedindo Ribeirão — passam a ser ainda mais importantes:
  ali, composição correta significa **não compor**.

## Conformidade

- Teste: o JSON Schema gerado para Cleide não contém `valor_em_estoque` no enum
  de métrica, nem ids fora do catálogo dela.
- Teste: o enum de `tipo` do JSON Schema é **idêntico** ao conjunto de ids do
  catálogo do ator — a divergência entre as duas serializações falha o CI.
- O trace registra o modo usado. Nenhum número é publicado sem ele.

## Referências
- [ADR-0013](./0013-suite-de-avaliacao.md) · [ADR-0023](./0023-provedor-de-modelo.md) · [Achados v1](../00-achados-v1.md)
