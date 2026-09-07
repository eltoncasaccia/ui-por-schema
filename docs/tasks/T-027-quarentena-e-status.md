# T-027 — Quarentena e status do lote

| | |
|---|---|
| **Onda** | W4 |
| **Trilha** | D |
| **Tamanho** | **G** |
| **Depende de** | T-025, T-018 |
| **Componentes** | `quarentena_liberar` `lote_status_acao` |
| **ADRs** | [0003](../adr/0003-catalogo-por-ator.md), [0011](../adr/0011-teto-de-catalogo.md) |
| **Regras** | RN-R02, RN-R03, RN-L05, RN-F02, §4.1 do documento 02 |
| **Requisitos** | RF-05 · `US-03`, `US-04` |

## Objetivo

As ações privativas do RT. **A demonstração mais limpa do ADR-0003:** só o catálogo
de Helena contém estes componentes.

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/registry/componentes/quarentena_liberar.py
api/src/estoque/registry/componentes/lote_status_acao.py
api/tests/registry/test_quarentena_liberar.py
api/tests/registry/test_lote_status_acao.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/quarentena_liberar.tsx
web/src/views/lote_status_acao.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 2 ids tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

| Componente | Command | `requires` |
|---|---|---|
| `quarentena_liberar` | `POST /lotes/:id/liberacao` | `lote.liberar` |
| `lote_status_acao` | `POST /lotes/:id/status` | `lote.status` |

`lote_status_acao` cobre três transições por enum `acao`: `bloquear`,
`desbloquear`, `liberar_vencimento` — fusão do ADR-0011, com o recorte preservado
como valor nomeado.

- Liberação exige checklist: integridade, validade (`RN-L07`), nota, e temperatura
  se termolábil (`RN-R03`).
- Reprovação leva a **Bloqueado**, nunca a liberado.
- Toda ação exige justificativa registrada.

### Não faz
Descarte — é T-029.

## Critérios de aceite

- [ ] **AC-1** Apenas Helena passa. Diretor, gerente, conferente, comprador e
      auditoria são recusados **no servidor**, com requisição direta ao endpoint.
      *(negativo — `RN-R02`, o critério central)*
- [ ] **AC-2** Nenhum dos dois componentes aparece no catálogo dos outros seis
      papéis. *(negativo — ADR-0003)*
- [ ] **AC-3** Liberação sem checklist completo é recusada. *(negativo — `RN-R03`)*
- [ ] **AC-4** Reprovação resulta em `bloqueado`. *(`§4.1`)*
- [ ] **AC-5** Toda transição fora da tabela §4.1 é recusada, inclusive para
      Diretor. *(negativo)*
- [ ] **AC-6** `liberar_vencimento` só se aplica a lote com validade ≤ 30 dias e
      exige justificativa. *(`RN-L05`)*
- [ ] **AC-7** Lote com excursão de temperatura permanece bloqueado até decisão
      explícita do RT. *(`RN-F02`)*
- [ ] **AC-8** `acao` fora do enum é rejeitada na validação do schema. *(negativo)*

## Definição de pronto — adicional
- [ ] Contagem de catálogo no BOARD: **+2**.

## Armadilhas

AC-1 com requisição direta ao endpoint é o que separa esta tarefa de uma interface
que apenas esconde botões. Esconder não é controlar (`RN-A03`).
