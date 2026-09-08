# T-036 — Schema Postgres e migrações

| | |
|---|---|
| **Onda** | W1 — Núcleo |
| **Trilha** | A |
| **Tamanho** | **G** |
| **Depende de** | T-002, T-035 |
| **Bloqueia** | T-006, T-007 |
| **ADRs** | [0018](../adr/0018-postgres-em-container.md), [0022](../adr/0022-status-registrado-e-efetivo.md) |
| **Regras** | RN-D02, RN-M02, RN-M06, RN-L04, RNF-01, RNF-06 |

## Objetivo

O banco onde as regras do domínio viram **restrições que o código não consegue
violar**. Aqui é onde `RN-M02` deixa de ser promessa.

## Arquivos de propriedade exclusiva

```
api/migrations/**        api/src/estoque/data/modelos.py
api/tests/data/test_schema.py
```

## Escopo

### Faz
- Alembic. **Sem `create_all`** — toda mudança de schema é migração versionada.
- Tabelas das sete entidades + `sessao`, `auditoria`, `view_registro`.
- `Lote` **sem** coluna de saldo e **sem** `vencido`/`esgotado` (ADR-0022).
- **Restrições no banco, não só no código:**

| Restrição | Regra |
|---|---|
| `REVOKE UPDATE, DELETE` em `movimento` para o papel da aplicação | `RN-M02` |
| `REVOKE UPDATE, DELETE` em `auditoria` | `RN-D02` |
| `CHECK (quantidade > 0)` | `RN-M04` |
| `UNIQUE (produto_id, numero, unidade_id)` | `RN-L08` |
| `CHECK` de classe × tipo de unidade | `RN-P02`, `RN-P03` |

- **View materializada `saldo_lote`**, atualizada na mesma transação do movimento —
  derivada, reconstruível, nunca editável (ADR-0022).
- Índices para os requisitos de tempo: `movimento(lote_id)` e
  `movimento(cliente_id, criado_em)` para `RNF-01`; `lote(unidade_id, validade)`
  para a fila de vencimento; `registro_temperatura(unidade_id, medido_em)` para
  `RNF-06`.

### Não faz
Repositórios (T-007). Dados (T-006).

## Critérios de aceite

> **Verificado por** `tests/data/test_imutabilidade_no_banco.py` — auditado em [A-002](../relatorios/A-002-auditoria-de-execucao.md).

- [ ] **AC-1** `UPDATE` em `movimento` pelo papel da aplicação é **recusado pelo
      banco**. *(negativo — `RN-M02` além do código)*
- [ ] **AC-2** `DELETE` em `auditoria` é recusado pelo banco, para qualquer papel
      da aplicação. *(negativo — `RN-D02`)*
- [ ] **AC-3** Nenhuma coluna `saldo`, `vencido` ou `esgotado` existe. Teste
      inspeciona o schema real. *(negativo — ADR-0022)*
- [ ] **AC-4** `saldo_lote` reconstruída do zero é idêntica à incremental.
- [ ] **AC-5** `EXPLAIN` da consulta de recall usa índice — sem varredura completa.
      *(`RNF-01`)*
- [ ] **AC-6** Migração aplicada duas vezes é idempotente; `downgrade` funciona.
- [ ] **AC-7** Dois lotes de mesmo número em unidades diferentes são aceitos; o
      mesmo número na mesma unidade é recusado. *(`RN-L08`)*

## Armadilhas

AC-1 e AC-2 são o que separa este projeto de um CRUD com comentário dizendo "não
editar". A imutabilidade tem que ser do banco, senão é convenção.
