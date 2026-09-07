# ADR-0022 — Separar status registrado de status efetivo

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Fundacional |
| **Corrige** | Achado [A-04](../relatorios/A-001-auditoria-pre-migracao.md) |
| **Regras** | RN-L04, RN-L05, RN-M06 · documento 02 §4.1 |

## Contexto

[T-002](../tasks/T-002-dominio-tipos-erros.md) proíbe um campo `saldo` em `Lote`,
com o argumento correto: campo derivado e armazenado é campo editável, e campo
editável é a divergência de 3,8% de volta (`RN-M06`).

O mesmo `Lote` tinha `status: StatusLote`, e **dois dos seis valores são
igualmente derivados**:

| Status | Derivado de | Documento 02 §4.1 |
|---|---|---|
| `vencido` | data de validade vs. hoje | *"Sistema, automático"* |
| `esgotado` | soma dos movimentos = 0 | *"Sistema, automático"* |

Armazená-los reintroduz o problema que `RN-M06` evita: um lote vencido ontem
continua `liberado` no banco porque nenhum processo rodou. E **nenhuma das 34
tarefas implementava esse processo** — não havia job, agendamento nem tarefa.

Havia ainda discordância entre documentos: [T-020](../tasks/T-020-vencimento-indicador.md)
tratava validade como derivada em tempo de leitura, e o tipo a tratava como
armazenada.

## Decisão

> **Armazena-se apenas o que é decisão de alguém. O resto é função pura.**

```
StatusLoteRegistrado    quarentena · liberado · bloqueado · descartado
                        ↑ muda por ação humana, com autor, motivo e auditoria

StatusLoteEfetivo       StatusLoteRegistrado + vencido · esgotado
                        ↑ f(registrado, validade, saldo, hoje) — pura
```

`RN-L05` (bloqueio automático em 30 dias) segue a mesma regra: **não** é uma
transição gravada, é consequência calculada. Só a liberação pelo RT é gravada,
porque é decisão.

Sem job. Sem agendamento. Sem processo noturno que pode não ter rodado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Job periódico materializando os estados | Cria janela de inconsistência, e a resposta a *"por que este lote está liberado?"* passa a ser *"o job não rodou"* |
| Trigger no banco | Mesma materialização, agora invisível no código e difícil de testar |
| Armazenar e recalcular na leitura | Dois lugares com a mesma verdade — o pior dos dois mundos |

## Consequências

**Positivas**
- Coerente com `RN-M06`: mesma disciplina para saldo e para status.
- `classificarValidade` (T-008) vira fonte única, e a discordância entre T-020 e o
  tipo desaparece.
- Um lote vence no instante correto, sem depender de processo nenhum.
- A auditoria fica mais limpa: só transições humanas aparecem, que é o que
  `RN-D01` quer registrar.

**Negativas**
- **Não dá para consultar `WHERE status = 'vencido'` direto no banco.** A consulta
  passa a ser por data e por saldo derivado, o que exige índice pensado e uma view
  SQL para as consultas de leitura.
- O saldo derivado da soma de movimentos precisa ser eficiente. Sem cuidado,
  `RNF-01` e `RNF-04` sofrem.

**Riscos aceitos**
- Custo de consulta. Mitigação: view materializada de saldo por lote, atualizada na
  mesma transação do movimento — **derivada, não editável**, e reconstruível a
  partir dos movimentos a qualquer momento. Se divergir, a fonte é o movimento.

## Conformidade

- `Lote` não tem campo `saldo` **nem** os valores `vencido`/`esgotado` em coluna.
- Teste: lote com validade de ontem tem `StatusLoteEfetivo == vencido` sem
  nenhum processo ter rodado.
- Teste: lote com saldo zero tem `esgotado`; um estorno que devolve saldo o tira
  de `esgotado`, sem escrita de status.
- Teste: a view materializada de saldo, reconstruída do zero, é idêntica à
  incremental.

## Referências
- [A-001 achado A-04](../relatorios/A-001-auditoria-pre-migracao.md) · `RN-M06`
