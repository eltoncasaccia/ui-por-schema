# T-007 — Porta de dados e repositórios in-memory

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | A |
| **Tamanho** | M |
| **Depende de** | T-036 |
| **Bloqueia** | toda a W3 |
| **ADRs** | [0018](../adr/0018-postgres-em-container.md), [0004](../adr/0004-autorizacao-em-tres-momentos.md), [0022](../adr/0022-status-registrado-e-efetivo.md) |
| **Regras** | RN-A01, RN-A02, RN-M06 |

## Objetivo

A única porta para dados. Trocar in-memory por API real depois deve ser mudança
local — é o teste de que a camada está certa.

## Arquivos de propriedade exclusiva

```
api/src/estoque/data/porta.py   api/src/estoque/data/repositorios/*.py   api/src/estoque/data/repositorios/*.test.py
api/src/estoque/domain/saldo.py
```

## Só leitura

`api/src/estoque/domain/**`, `api/src/estoque/data/fixtures/**`

## Escopo

### Faz
- `ContextoDados` **com transação** (`tx`), conforme CONTRATOS §4.
- Repositórios SQLAlchemy async: produto, lote, movimento, recebimento,
  temperatura, usuário.
- `calcularSaldo(movimentos)` em `domain/saldo.ts` — **a única fonte de saldo**.
- **Escopo de unidade aplicado na porta**, não pelo chamador.
- **Projeção de campo restrito na porta:** `custoUnitario` só é preenchido se o
  ator tiver `custo.ler`.

### Não faz
Autorização por permissão de operação (T-009). Aqui só escopo de unidade e campo
restrito.

## Critérios de aceite

- [ ] **AC-1** Listar lotes como Odair **nunca** devolve lote de outra unidade,
      qualquer que seja o critério passado. *(`RN-A01`, `CA-06`)*
- [ ] **AC-2** Buscar por id um lote de Ribeirão como Odair devolve `null` —
      indistinguível de inexistente. *(negativo — ADR-0014)*
- [ ] **AC-3** Produto lido por Cleide vem **sem** a chave `custoUnitario` — não
      `undefined`, **ausente**. *(`RN-A02`, `CA-05`)*
- [ ] **AC-4** Produto lido por Rafael vem com `custoUnitario`.
- [ ] **AC-5** `calcularSaldo` de um lote com estorno reflete a soma dos dois
      movimentos. *(`RN-M06`)*
- [ ] **AC-6** Um critério malicioso que tente passar `unidadeId` de outra unidade
      é ignorado — a interseção com o escopo do ator sempre vence. *(negativo)*
- [ ] **AC-7** Toda operação corre dentro da transação de `ContextoDados`;
      exceção reverte tudo. *(negativo — o que in-memory esconderia)*
- [ ] **AC-8** Nenhum repositório devolve `status` derivado do banco — `vencido` e
      `esgotado` vêm de `status_efetivo`. *(negativo — [ADR-0022](../adr/0022-status-registrado-e-efetivo.md))*

## Armadilhas

**AC-3 é mais sutil do que parece.** `custoUnitario: undefined` vaza a existência
do campo e aparece em `Object.keys`. A chave tem de estar ausente.
