# T-029 — Estorno e descarte

| | |
|---|---|
| **Onda** | W4 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-025, T-024 |
| **Componentes** | `movimento_estorno` `movimento_descarte` |
| **Regras** | RN-M02, RN-M03, RN-M05, RN-L06, §4.1 |
| **Requisitos** | RF-02, RF-03 · `US-07` · `CA-08` |

## Objetivo

Corrigir sem apagar história. É a implementação direta de `CA-08` — **excluir
movimento é recusado para todos, incluindo Diretor.**

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/registry/componentes/movimento_estorno.py
api/src/estoque/registry/componentes/movimento_descarte.py
api/tests/registry/test_movimento_estorno.py
api/tests/registry/test_movimento_descarte.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/movimento_estorno.tsx
web/src/views/movimento_descarte.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 2 ids tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

| Componente | Command | `requires` |
|---|---|---|
| `movimento_estorno` | `POST /movimentos/:id/estorno` | `movimento.estornar` |
| `movimento_descarte` | `POST /movimentos/descarte` | `movimento.descartar` |

- Estorno referencia o original, exige motivo de lista fechada, e **não modifica**
  o original (`RN-M03`).
- Descarte é a única saída possível para lote vencido ou bloqueado (`RN-L06`), e
  leva o lote a `descartado` (§4.1). Exige Gerente **e** RT.
- Ambos usam `confirm_action` de T-025 — são irreversíveis.

### Não faz
Exclusão. Não existe, em lugar nenhum, para ninguém.

## Critérios de aceite

- [ ] **AC-1** Não existe rota, comando ou caminho de código que exclua ou edite
      movimento. Teste percorre as rotas registradas e afirma a ausência.
      *(negativo — `CA-08`, `RN-M02`)*
- [ ] **AC-2** Marco (Diretor) tentando excluir movimento é recusado igual a
      qualquer outro papel. *(negativo — `CA-08`)*
- [ ] **AC-3** Estorno cria movimento novo e o original permanece **byte a byte
      inalterado**. *(`RN-M03`)*
- [ ] **AC-4** Saldo após estorno é a soma dos dois movimentos, sem edição de
      campo. *(`RN-M06`, `AC-07.3` do PRD)*
- [ ] **AC-5** Estorno sem motivo de lista fechada é recusado. *(negativo)*
- [ ] **AC-6** Descarte de lote **liberado e válido** é recusado — descarte não é
      atalho de saída. *(negativo — `RN-L06`)*
- [ ] **AC-7** Descarte exige as duas identificações (Gerente e RT). *(negativo)*
- [ ] **AC-8** Ambos passam por `confirm_action` antes de aplicar.

## Definição de pronto — adicional
- [ ] Contagem de catálogo no BOARD: **+2**.

## Armadilhas

AC-1 precisa ser um teste sobre as **rotas registradas**, não sobre a interface.
Ausência de botão não é ausência de endpoint.
