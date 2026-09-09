# T-028 — Saída com FEFO

| | |
|---|---|
| **Onda** | W4 |
| **Trilha** | D |
| **Tamanho** | **G** |
| **Depende de** | T-025, T-008, T-018 |
| **Bloqueia** | T-030 |
| **Componentes** | `movimento_saida` |
| **Regras** | RN-L02, RN-L03, RN-L06, RN-M01, RN-M04, RN-M05, RN-C01 |
| **Requisitos** | RF-07, RF-08 · `US-05` |

## Objetivo

O movimento mais frequente do sistema, e o que carrega mais regra por operação.

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/registry/componentes/movimento_saida.py
api/tests/registry/test_movimento_saida.py

api/src/estoque/commands/saida.py
api/src/estoque/commands/entradas/saida.py
api/tests/commands/test_saida_comandos.py
```

> **Corrigido pelo achado A-15.** Os arquivos em `commands/` não estavam na lista
> original, e sem eles a tarefa não fecha: o componente **declara** o comando, mas
> não pode **executá-lo** — `registry` não importa `commands.pipeline`, porque o
> contrato 2 do import-linter proíbe `registry → sqlalchemy`, inclusive por
> caminho indireto.
>
> `commands/entradas/<dominio>.py` guarda o schema de entrada, e é módulo-folha:
> só pydantic e `domain`. O `CommandDef` do registry e o comando executável
> apontam para **o mesmo schema** — duas declarações do mesmo formulário
> divergiriam (achado A-11). Há teste percorrendo o grafo em
> `tests/registry/test_quarentena_liberar.py` que reprova a folha que deixar de
> ser folha.
>
> **`commands/indice.py` é GERADO** por `make gerar-indice` e não entra em lista
> nenhuma: as cinco tarefas de escrita precisariam da mesma linha nele, que é
> exatamente o caso do acordo de trabalho §4. Rode o gerador; não edite à mão.
>
> `T-027` é o exemplo pronto: `commands/lote.py` + `commands/entradas/lote.py`.

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/movimento_saida.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 1 id tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

> **Endpoints corrigidos pelo achado A-16.** A tarefa citava rotas REST por
> recurso; [CONTRATOS §8](./CONTRATOS.md) — normativo e congelado — define
> `/api/comandos/{nome}` como a rota **única** de escrita, com CSRF, `Origin`,
> `Idempotency-Key` e `If-Match` aplicados num lugar só. A hierarquia do acordo
> de trabalho resolve: **`RN-*` > ADR > PRD > tarefa.**

- Command `movimento_saida` — `POST /api/comandos/movimento_saida`,
  `requires: 'movimento.criar'`, **não idempotente**.
- Propõe o lote liberado de menor validade via `proporFefo` de T-008 (`RN-L02`).
- Escolher outro lote exige justificativa registrada (`RN-L03`).
- Motivo de lista fechada; texto livre é complemento (`RN-M05`).
- Cliente e nota fiscal registrados — é o que alimenta o recall (`RN-D03`).
- **Se o produto é controlado**, o movimento nasce em `aguardando_autorizacao` e o
  saldo **não** muda até T-030 autorizar (`RN-C01`).

### Não faz
Autorizar controlado (T-030). Descarte e estorno (T-029).

## Critérios de aceite

- [ ] **AC-1** A proposta é sempre o lote liberado de menor validade. *(`RN-L02`)*
- [ ] **AC-2** Escolher outro lote sem justificativa é recusado. *(negativo —
      `RN-L03`)*
- [ ] **AC-3** Saída de lote vencido, bloqueado ou em quarentena é recusada.
      *(negativo — `RN-L06`)*
- [ ] **AC-4** Saída que deixaria saldo negativo é recusada. *(negativo — `RN-M01`)*
- [ ] **AC-5** Motivo fora da lista fechada é recusado; complemento sozinho não
      substitui o motivo. *(negativo — `RN-M05`)*
- [ ] **AC-6** Saída de controlado **não altera o saldo** enquanto pendente.
      *(`RN-C01`, `AC-06.1` do PRD)*
- [ ] **AC-7** O movimento criado é imutável: nenhuma rota permite editá-lo.
      *(negativo — `RN-M02`)*
- [ ] **AC-8** Cliente e nota ficam registrados e são recuperáveis por
      `rastreabilidade`. *(liga a `CA-01`)*

## Definição de pronto — adicional
- [ ] Contagem de catálogo no BOARD: **+1**.

## Armadilhas

**AC-6 é a base do `CA-04`.** Se o saldo mudar na submissão e "voltar" caso a
autorização não venha, a dupla identificação virou teatro: a mercadoria já saiu do
estoque contábil com uma identificação só.
