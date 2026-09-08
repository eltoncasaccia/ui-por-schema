# T-008 — FEFO, validade, estados do lote e saldo

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | A |
| **Tamanho** | M |
| **Depende de** | T-002 |
| **Bloqueia** | T-028 |
| **Paralelizável com** | T-006, T-009, T-010, T-012, T-014 |
| **Regras** | RN-L02..L07, RN-M01, RN-M03, RN-M06, RN-P02, RN-P03 |

## Objetivo

As regras do documento 02 como funções puras, testáveis sem I/O, sem React e sem
banco. É onde o negócio mora.

## Arquivos de propriedade exclusiva

```
api/src/estoque/domain/regras/*.py   api/src/estoque/domain/regras/*.test.py
```

## Escopo

### Faz

| Função | Regra |
|---|---|
| `proporFefo(lotes)` → lote liberado de menor validade | RN-L02 |
| `exigeJustificativaFefo(escolhido, proposto)` | RN-L03 |
| `classificarValidade(lote, hoje)` → `ok \| alerta_90 \| bloqueio_30 \| vencido` | RN-L04, RN-L05 |
| `podeSair(lote)` | RN-L06 |
| `aceitaRecebimento(validade, hoje, autorizacaoRt)` | RN-L07 |
| `transicaoValida(de, evento, papel)` | §4.1 do documento 02 |
| `validaAlocacao(produto, unidade)` | RN-P02, RN-P03 |
| `resulta_negativo(saldo, movimento)` | RN-M01 |
| **`status_efetivo(lote, saldo, hoje)`** | **ADR-0022** — `vencido` e `esgotado` |
| `calcular_saldo(movimentos)` | RN-M06 |
| `montarEstorno(original, motivo, autor)` | RN-M03 |

### Não faz
Persistir, autorizar, renderizar. **Nenhum import fora de `domain/`.**

## Critérios de aceite

> **Verificado por** `tests/domain/test_validade.py, test_fefo.py, test_saldo_e_estados.py` — auditado em [A-002](../relatorios/A-002-auditoria-de-execucao.md).

- [ ] **AC-1** `classificarValidade` testada nas fronteiras exatas: 29, 30, 31, 89,
      90, 91 dias, e no dia do vencimento.
- [ ] **AC-2** `proporFefo` ignora lotes não `liberado`. *(negativo — `RN-L06`)*
- [ ] **AC-3** Empate de validade no FEFO tem desempate **determinístico e
      documentado** — mesma entrada, mesma saída, sempre.
- [ ] **AC-4** `transicaoValida` recusa toda transição fora da tabela §4.1,
      inclusive para Diretor. *(negativo)*
- [ ] **AC-5** `montarEstorno` produz movimento que referencia o original e **não
      modifica** o original. *(`RN-M02`)*
- [ ] **AC-6** Toda função é pura: mesma entrada, mesma saída, sem `Date.now()`
      interno — a data de referência é sempre parâmetro.
- [ ] **AC-7** `arch:check` confirma que `domain/regras/` não importa nada fora de
      `domain/`.

## Armadilhas

`Date.now()` dentro de regra torna o teste dependente do relógio e a regra
impossível de auditar. A data entra por parâmetro, sempre.
