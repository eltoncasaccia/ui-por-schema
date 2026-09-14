# T-043 — Instrumentação ao vivo do pipeline do assistente

| | |
|---|---|
| **Trilha** | C · assistente |
| **Tamanho** | M |
| **Depende de** | T-011 |
| **ADRs** | [0026](../adr/0026-observabilidade.md), [0012](../adr/0012-injecao-de-prompt-via-dado.md) |
| **Origem** | ADR-0026, "O que continua não verificado"; achado [A-10](./ACHADOS.md) |
| **Escrita em** | 2026-09-14 — até aqui a tarefa era só uma linha no BOARD |

## Por que existe

O observador do LangFuse é chamado **depois** que a composição termina e
reconstrói a árvore de spans a partir do `Trace`. O SDK v4 não aceita
`start_time`/`end_time` (conferido na 4.15.1), então toda span nasce com duração
perto de zero e leva o metadado `duracao_da_span_e_artificial`. A latência real
só existe como nota numérica.

## O A-10, conferido antes de escrever

Os três defeitos do A-10 (ADR-0026, "Os três defeitos que só a execução
revelou") **já estão corrigidos no código**: host lido de `LANGFUSE_HOST` **ou**
`LANGFUSE_BASE_URL`, `propagate_attributes` no lugar do `update_trace` que não
existe na v4, e nota presa ao trace por `score_trace`. O que falta é **teste** —
nenhum dos três tem, e foi a ausência de teste que os deixou mudos por semanas.

## Decisão

- A porta `Observador` ganha `ao_vivo(pergunta, ator_id, papel)`: context
  manager que abre a raiz **antes** do modelo. `etapa(nome)` envolve o trabalho
  real (`gerar-composicao`, `validar-schema`); `concluir(trace, catalogo)` anexa
  saída, nível e notas.
- A rota do assistente usa `ao_vivo`. O `composicao(trace=...)` pós-fato continua
  para a eval (T-032), com a marca de artificial.
- Nunca levanta: falha do LangFuse ao abrir, detalhar ou fechar degrada com
  `warning`. Exceção do **corpo** atravessa intacta — é da requisição.
- Testes com cliente LangFuse **falso** medindo enter/exit com relógio real —
  nada sai da máquina — e um teste que prende o falso às assinaturas do SDK
  instalado.

## Arquivos de propriedade exclusiva

```
api/src/estoque/assistant/observador.py
api/src/estoque/assistant/langfuse_obs.py
api/tests/server/test_t043_observador_ao_vivo.py
```

## Toca, com registro

```
api/src/estoque/server/rotas/assistente.py   envolver o pipeline
```

## Critérios de aceite

- [x] **AC-1** Com um modelo que leva 50 ms, a span `gerar-composicao` dura
      ≥ 50 ms, `validar-schema` dura menos, e as duas são filhas da raiz
      `compor-interface`.
- [x] **AC-2** O caminho ao vivo não marca nenhuma span como artificial.
      *Com contraponto: o caminho pós-fato da eval continua marcado.*
- [x] **AC-3** Modelo, tokens e custo na geração; aceitos e rejeitados no
      guardrail; `schema_valido` e `latencia_ms` presos ao trace.
- [x] **AC-4** LangFuse fora do ar, ou falhando no meio, não derruba a composição
      e deixa `warning` no log. *(negativo)*
- [x] **AC-5** Erro do modelo continua devolvendo `invalido`, e a árvore fecha com
      nível `ERROR`. *(negativo)*
- [x] **AC-6** Os três defeitos do A-10 têm teste: host por `LANGFUSE_BASE_URL`,
      nota presa ao trace (nenhum `create_score` solto) e observador nulo sem chave.
- [x] **AC-7** O cliente falso não diverge do SDK: métodos e parâmetros usados
      existem na versão instalada. *Conferido contra `langfuse` 4.15.1.*

## Fechamento — 2026-09-14

A rota do assistente abre a observação antes do modelo e envolve cada etapa; a
eval segue no caminho pós-fato, marcado como artificial. **Não conferido contra
a nuvem do LangFuse** — fica para a rodada de LLM e eval. Tocou
`server/rotas/assistente.py`, com registro, e a conformidade do ADR-0026.

## Não faz

Instrumentar a eval (`make eval` segue pós-fato). Conferir contra a nuvem do
LangFuse — fica para a rodada de LLM e eval.
