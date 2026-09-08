# T-018 — Componentes de lote

| | |
|---|---|
| **Onda** | W3 — Leitura |
| **Trilha** | D |
| **Tamanho** | **G** |
| **Depende de** | T-007, T-008, T-009, T-012, T-015 · liberada por T-017 |
| **Bloqueia** | T-027, T-028 |
| **Paralelizável com** | T-019 a T-024 |
| **Componentes** | `lote_lista` `lote_detalhe` `lote_movimentos` `quarentena_fila` |
| **ADRs** | [0003](../adr/0003-catalogo-por-ator.md), [0005](../adr/0005-l2-leitura-l1-escrita.md), [0006](../adr/0006-contrato-unico-de-componente.md) |
| **Regras** | RN-L01, RN-L04, RN-L08, RN-M06, RN-A01, RN-R01 |

## Objetivo

O núcleo de leitura do sistema. Quatro componentes que quase toda pergunta de
operador acaba usando.

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/registry/componentes/lote_lista.py
api/src/estoque/registry/componentes/lote_detalhe.py
api/src/estoque/registry/componentes/lote_movimentos.py
api/src/estoque/registry/componentes/quarentena_fila.py
api/tests/registry/test_lote_lista.py
api/tests/registry/test_lote_detalhe.py
api/tests/registry/test_lote_movimentos.py
api/tests/registry/test_quarentena_fila.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/lote_lista.tsx
web/src/views/lote_detalhe.tsx
web/src/views/lote_movimentos.tsx
web/src/views/quarentena_fila.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 4 ids tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

| Componente | Params | `requires` | Tamanho |
|---|---|---|---|
| `lote_lista` | `produtoId?` `unidadeId?` `status?` `validadeAte?` | `lote.ler` | `inteira` |
| `lote_detalhe` | `loteId` | `lote.ler` | `meia` |
| `lote_movimentos` | `loteId` `de?` `ate?` | `movimento.ler` | `inteira` |
| `quarentena_fila` | `unidadeId?` | `lote.ler` | `inteira` |

- Saldo **sempre** via `calcularSaldo` — nenhum campo armazenado (`RN-M06`).
- `description` e `examples` escritos para o modelo, não para o desenvolvedor.
- Todos os recortes como **enum nomeado**, nunca texto livre (risco R-5).

### Não faz
Escrita. Ações de status (T-027).

## Critérios de aceite

- [x] **AC-1** `lote_lista` como Odair devolve apenas lotes de Uberlândia,
      **qualquer que seja o param passado**. *(negativo — `CA-06`)*
- [x] **AC-2** `lote_detalhe` de um lote de outra unidade devolve `nao_encontrado`,
      idêntico a inexistente. *(negativo — ADR-0014)*
- [x] **AC-3** O saldo exibido é a soma dos movimentos; não existe campo `saldo` em
      lugar nenhum do caminho. *(`RN-M06`)*
- [x] **AC-4** `status` é enum fechado; valor fora do enum é rejeitado na validação
      do schema. *(negativo — risco R-5)*
- [x] **AC-5** `quarentena_fila` lista apenas `status: quarentena`. *(`RN-R01`)*
- [x] **AC-6** Nenhum dos quatro expõe custo, para nenhum papel — custo é de
      `produto_ficha` (T-019). *(`CA-05`)*
- [x] **AC-7** Dois lotes de mesmo número em unidades diferentes aparecem como
      **registros distintos**. *(`RN-L08`)*
- [x] **AC-8** `select` é pura; teste chama duas vezes e compara referência de
      saída estrutural.

## Definição de pronto — adicional

- [x] Contagem de catálogo no BOARD atualizada: **+4**.
- [x] Os quatro entraram no teste de catálogo por persona (T-012 AC-1).

## Armadilhas

`validadeAte` como data livre convida o modelo a inventar recorte. Prefira enum
`janela: 30 | 60 | 90` e uma data explícita só onde o usuário realmente informa.
