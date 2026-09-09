# T-022 — Recebimento, leitura

| | |
|---|---|
| **Onda** | W3 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-007, T-009, T-012, T-015 · liberada por T-017 |
| **Bloqueia** | T-026 |
| **Componentes** | `recebimento_lista` `recebimento_detalhe` |
| **Regras** | RN-R01, RN-R03, RN-R04, RN-R05, RN-F01, RN-A01 |

## Objetivo

Ver o que entrou e em que estado está. Base de leitura para o formulário de
registro (T-026).

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/application/registry/componentes/recebimento_lista.py
api/src/estoque/application/registry/componentes/recebimento_detalhe.py
api/tests/registry/test_recebimento_lista.py
api/tests/registry/test_recebimento_detalhe.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/recebimento_lista.tsx
web/src/views/recebimento_detalhe.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 2 ids tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

| Componente | Params | `requires` | Tamanho |
|---|---|---|---|
| `recebimento_lista` | `unidadeId?` `status?` `de?` `ate?` | `recebimento.ler` | `inteira` |
| `recebimento_detalhe` | `recebimentoId` | `recebimento.ler` | `inteira` |

- Detalhe mostra: conferência registrada (integridade, validade, nota,
  temperatura se termolábil), lotes gerados, **pendências** de divergência
  (`RN-R04`), e as identificações no caso de controlado (`RN-R05`).

### Não faz
Registrar recebimento (T-026). Liberar quarentena (T-027).

## Critérios de aceite

- [ ] **AC-1** Todo recebimento listado gerou lote em **quarentena**; não existe
      recebimento com lote nascido liberado nas fixtures nem no caminho.
      *(`RN-R01`)*
- [ ] **AC-2** Recebimento com divergência exibe a pendência vinculada, e a
      pendência não impede a conclusão. *(`RN-R04`)*
- [ ] **AC-3** Recebimento de controlado exibe as **duas** identificações.
      *(`RN-R05`)*
- [ ] **AC-4** Recebimento de termolábil exibe a temperatura de chegada. *(`RN-F01`)*
- [ ] **AC-5** Como Odair, apenas recebimentos de Uberlândia. *(negativo — `CA-06`)*
- [ ] **AC-6** `status` é enum fechado. *(negativo — risco R-5)*
- [ ] **AC-7** Nenhum custo exposto. *(`CA-05`)*

## Definição de pronto — adicional
- [ ] Contagem de catálogo no BOARD: **+2**.
