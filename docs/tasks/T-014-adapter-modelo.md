# T-014 — Adapter de modelo e Execution Trace

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | C |
| **Tamanho** | M |
| **Depende de** | T-004 |
| **Bloqueia** | T-017, T-032 |
| **Paralelizável com** | T-006, T-008, T-009, T-010, T-012 |
| **ADRs** | [0012](../adr/0012-injecao-de-prompt-via-dado.md), [0013](../adr/0013-suite-de-avaliacao.md) |
| **Requisitos** | CS-04, CS-06 |

## Objetivo

O caminho até o modelo real — **o que a v1 escreveu, compilou e nunca executou.**

## Arquivos de propriedade exclusiva

```
api/src/estoque/assistant/adapter.py   api/src/estoque/assistant/prompt.py
api/src/estoque/assistant/trace.py     api/src/estoque/assistant/*.test.py
```

## Escopo

### Faz
- Interface `AdaptadorModelo` com duas implementações: **Claude real** (`@anthropic-ai/sdk`)
  e **mock determinístico** para teste.
- Modelos suportados: `claude-haiku-4-5-20251001` e `claude-sonnet-5`, selecionáveis
  por configuração — os dois serão medidos (PRD §9).
- Montagem do prompt: pergunta do usuário + catálogo do ator + enums. **Nada mais.**
- Execution Trace: prompt enviado, tokens de entrada e saída, latência, resposta
  bruta, schema extraído, aceitos, rejeitados.
- Timeout e retry com limite. Falha do modelo é erro tratado, nunca tela quebrada.

### Não faz
Validar (T-013). Medir em escala (T-017, T-032).

## Critérios de aceite

> **Verificado por** `tests/assistant/test_adapter.py, test_agnosticismo.py` — auditado em [A-002](../relatorios/A-002-auditoria-de-execucao.md).

- [ ] **AC-1** O prompt **não contém nenhuma linha de dados do banco**. Teste
      inspeciona o prompt montado e falha se encontrar valor de fixture.
      *(negativo — ADR-0012, `CS-04`)*
- [ ] **AC-2** `arch:check` confirma que `prompt.ts` não importa `data/`.
- [ ] **AC-3** Sem `ANTHROPIC_API_KEY`, o adaptador real falha com mensagem clara —
      **nunca cai em silêncio para o mock**. *(negativo)*
- [ ] **AC-4** O mock é determinístico e explicitamente identificado no trace, para
      que nenhum número medido seja atribuído ao modelo real por engano.
- [ ] **AC-5** O trace registra tokens de entrada e saída, e a latência até o
      primeiro token.
- [ ] **AC-6** Resposta do modelo que não seja JSON válido é tratada como schema
      rejeitado, com registro no trace — não como exceção. *(negativo)*
- [ ] **AC-7** Timeout devolve erro tratado dentro do limite configurado.

## Armadilhas

**AC-3 é o critério mais importante desta tarefa.** O erro central da v1 foi medir
o mock e não perceber. Fallback silencioso para o mock repetiria isso — e desta vez
com números que parecem reais.
