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

api/src/estoque/commands/estorno.py
api/src/estoque/commands/entradas/estorno.py
api/tests/commands/test_estorno_comandos.py
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
web/src/views/movimento_estorno.tsx
web/src/views/movimento_descarte.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 2 ids tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

> **Endpoints corrigidos pelo achado A-16.** A tarefa citava rotas REST por
> recurso; [CONTRATOS §8](./CONTRATOS.md) — normativo e congelado — define
> `/api/comandos/{nome}` como a rota **única** de escrita, com CSRF, `Origin`,
> `Idempotency-Key` e `If-Match` aplicados num lugar só. A hierarquia do acordo
> de trabalho resolve: **`RN-*` > ADR > PRD > tarefa.**


| Componente | Command | `requires` |
|---|---|---|
| `movimento_estorno` | `POST /api/comandos/movimento_estorno` | `movimento.estornar` |
| `movimento_descarte` | `POST /api/comandos/movimento_descarte` | `movimento.descartar` |

- Estorno referencia o original, exige motivo de lista fechada, e **não modifica**
  o original (`RN-M03`).
- Descarte é a única saída possível para lote vencido ou bloqueado (`RN-L06`), e
  leva o lote a `descartado` (§4.1). Exige Gerente **e** RT.
- Ambos declaram `CommandDef.confirm = True` — são irreversíveis. **Não existe
  componente `confirm_action`**: confirmar é decisão do motor de render diante do
  `confirm`, não composição que o modelo escolhe (achado A-05).

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
