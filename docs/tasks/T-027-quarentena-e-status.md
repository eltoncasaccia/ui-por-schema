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
api/src/estoque/application/registry/componentes/quarentena_liberar.py
api/src/estoque/application/registry/componentes/lote_status_acao.py
api/tests/registry/test_quarentena_liberar.py
api/tests/registry/test_lote_status_acao.py

api/src/estoque/application/commands/lote.py       api/src/estoque/application/commands/entradas/lote.py
api/tests/commands/test_lote_comandos.py
```

> **Os quatro arquivos em `commands/` não estavam na lista, e precisavam estar**
> (achado A-15). O componente **declara** o comando; ele não pode **executá-lo**:
> `registry` não importa `commands.pipeline` porque o contrato 2 do import-linter
> proíbe `registry → sqlalchemy`, inclusive por caminho indireto — verificado
> quebrando de propósito. A execução mora em `commands/`, e o corte da tarefa não
> previu isso para nenhuma das cinco tarefas de W4.
>
> `commands/entradas/lote.py` é o módulo-folha que evita a divergência: o
> `CommandDef` do registry e o comando executável apontam para **o mesmo
> schema**. Há teste percorrendo o grafo para garantir que a folha continue folha.
>
> **`commands/indice.py` é GERADO** por `make gerar-indice`, e por isso não está
> na lista: as cinco tarefas de escrita precisariam da mesma linha nele.

### Arquivos de outra tarefa, tocados por necessidade

| Arquivo | Dono | Por quê |
|---|---|---|
| `api/src/estoque/server/app.py` | T-011 | uma linha: importar `commands/indice.py`, como já se faz com `registry/indice.py` |
| `api/tests/registry/test_catalogo_por_ator.py` | T-012 | a skill `componente-novo` manda acrescentar os ids ali — é o DoD de T-012 AC-1 |

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
| `quarentena_liberar` | `POST /api/comandos/lote_liberar_quarentena` | `lote.liberar` |
| `lote_status_acao` | `POST /api/comandos/lote_status` | `lote.status` |

> **Os endpoints acima foram corrigidos na execução.** A tarefa dizia
> `POST /lotes/:id/liberacao`; [CONTRATOS §8](./CONTRATOS.md) — normativo e
> congelado — define `/api/comandos/{nome}` como a rota única de escrita. A
> hierarquia do acordo de trabalho resolve: **`RN-*` > ADR > PRD > tarefa.**

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

- [x] **AC-1** Apenas Helena passa. Diretor, gerente, conferente, comprador e
      auditoria são recusados **no servidor**, com requisição direta ao endpoint.
      *(negativo — `RN-R02`, o critério central)*
- [x] **AC-2** Nenhum dos dois componentes aparece no catálogo dos outros seis
      papéis. *(negativo — ADR-0003)*
- [x] **AC-3** Liberação sem checklist completo é recusada. *(negativo — `RN-R03`)*
- [x] **AC-4** Reprovação resulta em `bloqueado`. *(`§4.1`)*
- [x] **AC-5** Toda transição fora da tabela §4.1 é recusada, inclusive para
      Diretor. *(negativo)*
- [x] **AC-6** `liberar_vencimento` só se aplica a lote com validade ≤ 30 dias e
      exige justificativa. *(`RN-L05`)*
- [~] **AC-7** Lote com excursão de temperatura permanece bloqueado até decisão
      explícita do RT. *(`RN-F02`)* — **metade verificada.** Está provado que não
      existe caminho automático para fora de `bloqueado`: nenhum outro papel o
      move, nenhuma leitura o move, só `desbloquear` do RT com justificativa
      (`test_ac7_lote_bloqueado_so_sai_por_decisao_explicita_do_rt`). A
      **detecção** da excursão depende de `RepoTemperatura`, que não existe —
      é T-023. Fica em branco a metade que não pode ser conferida aqui.
- [x] **AC-8** `acao` fora do enum é rejeitada na validação do schema. *(negativo)*

## Definição de pronto — adicional
- [x] Contagem de catálogo no BOARD: **+2**.

## Armadilhas

AC-1 com requisição direta ao endpoint é o que separa esta tarefa de uma interface
que apenas esconde botões. Esconder não é controlar (`RN-A03`).
