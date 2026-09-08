# T-013 — Validador de schema e revalidação no servidor

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | C |
| **Tamanho** | M |
| **Depende de** | T-012 |
| **Bloqueia** | T-016 |
| **ADRs** | [0001](../adr/0001-ui-por-schema.md), [0004](../adr/0004-autorizacao-em-tres-momentos.md), [0005](../adr/0005-l2-leitura-l1-escrita.md) |
| **Requisitos** | CS-01 |

## Objetivo

A fronteira de segurança que a v1 provou funcionar — reconstruída, com o catálogo
por ator no lugar da constante do cliente.

## Arquivos de propriedade exclusiva

```
api/src/estoque/schema/validar.py   api/src/estoque/schema/validar.test.py   api/src/estoque/schema/adversarial.test.py
```

## Escopo

### Faz
- `validarSchema(bruto, catalogo)` → schema validado ou `ErroDominio`.
- Rejeita: componente fora do catálogo **do ator**, param fora do enum, chave
  desconhecida, tipo errado, aninhamento inválido.
- Rejeita composição de componente com `commands` junto de outros no mesmo bloco
  (ADR-0005).
- Registra aceitos e rejeitados no trace.

### Não faz
Chamar o modelo (T-014). Renderizar (T-015).

## Critérios de aceite

> **Verificado por** `tests/schema/test_adversarial.py` — auditado em [A-002](../relatorios/A-002-auditoria-de-execucao.md).

Bateria adversarial, herdada da v1 e ampliada — **todos devem ser rejeitados**:

- [ ] **AC-1** `{"tipo":"RandomReactComponent"}` *(negativo)*
- [ ] **AC-2** `{"tipo":"<script>alert(1)</script>"}` *(negativo)*
- [ ] **AC-3** `estoque_indicador` com métrica fora do enum *(negativo)*
- [ ] **AC-4** Campo `layout` com CSS injetado *(negativo)*
- [ ] **AC-5** Componente **existente no registry mas ausente do catálogo do ator**
      — o caso que a v1 não tinha como testar. *(negativo — `CS-01`)*
- [ ] **AC-6** Aninhamento profundo / schema gigante é rejeitado por limite, sem
      estourar a pilha. *(negativo)*
- [ ] **AC-7** `__proto__` ou `constructor` como chave de params *(negativo)*
- [ ] **AC-8** Schema válido passa e produz o mesmo objeto, sem campos extras.
- [ ] **AC-9** Todo rejeitado aparece no trace com o motivo.

## Armadilhas

**AC-5 é o critério que distingue esta tarefa da v1.** Validar contra o registry
global em vez do catálogo do ator seria um furo de permissão que passa em todos os
outros testes.
