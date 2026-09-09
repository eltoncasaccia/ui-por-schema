# T-024 — Movimentos e trilha de auditoria, leitura

| | |
|---|---|
| **Onda** | W3 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-007, T-009, T-010, T-012, T-015 · liberada por T-017 |
| **Bloqueia** | T-029, T-030 |
| **Componentes** | `movimento_lista` `auditoria_trilha` |
| **Regras** | RN-M02, RN-M04, RN-D01, RN-D02, RN-D05, RN-A02 |

## Objetivo

Ver movimentos e ver quem fez o quê. `movimento_lista` também é a **fila de
autorizações pendentes de controlado** — foi assim que o catálogo coube em 23
(ADR-0011).

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/application/registry/componentes/movimento_lista.py
api/src/estoque/application/registry/componentes/auditoria_trilha.py
api/tests/registry/test_movimento_lista.py
api/tests/registry/test_auditoria_trilha.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/movimento_lista.tsx
web/src/views/auditoria_trilha.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 2 ids tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

| Componente | Params | `requires` | Tamanho |
|---|---|---|---|
| `movimento_lista` | `unidadeId?` `loteId?` `tipo?` `status?` `de?` `ate?` | `movimento.ler` | `inteira` |
| `auditoria_trilha` | `atorId?` `entidade?` `de?` `ate?` | `auditoria.ler` | `inteira` |

- `status: aguardando_autorizacao` é **valor do enum** — é como Helena encontra o
  que precisa autorizar, sem componente dedicado.
- Estorno é exibido ligado ao original; **os dois permanecem visíveis** (`RN-M03`).

### Não faz
Criar movimento, estornar, autorizar — W4.

### Arquivos de outra tarefa, tocados por necessidade

| Arquivo | Dono | Por quê |
|---|---|---|
| `api/src/estoque/data/porta.py` · `repositorios.py` | T-007 | **não havia `RepoAuditoria`** — o registry não alcançava a trilha, lacuna que a T-030 já tinha registrado. `LinhaAuditoria` mora na porta e não em `domain/tipos.py`: CONTRATOS §3 congela sete entidades, e trilha não é uma delas |
| `api/src/estoque/server/app.py` | T-011 | injetar o repositório novo no `LoadContext` |
| `api/tests/registry/fakes.py` | — | o fake correspondente, mais o pendente e o par de estorno que o fixture não tinha |
| `api/tests/registry/test_catalogo_por_ator.py` | T-012 | os dois ids novos, como manda a skill `componente-novo` |
| `api/tests/registry/test_lote_movimentos.py` | T-018 | um teste pegava `linhas[0]` e presumia a ordem do fixture; passou a buscar pelo id |

### Achado durante a execução

**`fakes.AGORA` era `datetime` ingênuo**, e a coluna real é `timestamptz`
(CONTRATOS §10: *"datetime com timezone, sempre do servidor"*). `lote_movimentos`
não percebia porque compara `.date()`; `movimento_lista` passa o corte como
`datetime` ao repositório, e aí o falso quebrava onde o real funciona. É o achado
A-11 outra vez — fake divergindo do adaptador —, agora no tipo do dado e não no
escopo. Corrigido na raiz. Achado **A-29**.

## Critérios de aceite

- [x] **AC-1** `status: aguardando_autorizacao` devolve exatamente os movimentos
      pendentes das unidades do ator. *(base do `CA-04`)*
- [x] **AC-2** Movimento estornado e seu estorno aparecem **ambos**, ligados.
      *(`RN-M03`)*
- [x] **AC-3** Nenhuma ação de edição ou exclusão é oferecida na interface, para
      nenhum papel. *(negativo — `RN-M02`, `CA-08`)*
- [x] **AC-4** `auditoria_trilha` está no catálogo de Marco e Sandra; **não** está
      no de Ivo, Odair nem Cleide. *(negativo — matriz do documento 02)*
- [x] **AC-5** A trilha lida por quem não tem `custo.ler` não contém valores de
      custo em `valor anterior`/`valor novo`. *(negativo — `CA-05`, o vazamento por
      log)*
- [x] **AC-6** Consultar a trilha gera evento de auditoria. *(`RN-D05` — a consulta
      de auditoria é auditada)*
- [x] **AC-7** `tipo` e `status` são enums fechados. *(negativo — risco R-5)*

## Definição de pronto — adicional
- [x] Contagem de catálogo no BOARD: **+2**. Registrados: **13**. O acumulado
      de 15 em W3 depende de T-019, T-021, T-022 e T-023 — não fecha aqui.

## Armadilhas

**AC-5 é o vazamento mais fácil de deixar passar** no projeto inteiro: o campo é
escondido na tela de produto e reaparece na trilha de auditoria, que Sandra lê e
que um gerente poderia ler se a matriz mudasse.
