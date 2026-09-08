# T-020 — Fila de vencimento e indicador

| | |
|---|---|
| **Onda** | W3 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-007, T-008, T-009, T-012, T-015 · liberada por T-017 |
| **Componentes** | `fila_vencimento` `estoque_indicador` `vencimento_grafico` |
| **Regras** | RN-L04, RN-L05, RN-A01, RN-A02 |
| **Requisitos** | `CA-03` |

## Objetivo

O componente que responde ao episódio dos R$ 183 mil vencidos em prateleira — e o
indicador numérico usado em panoramas compostos.

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/registry/componentes/fila_vencimento.py
api/src/estoque/registry/componentes/estoque_indicador.py
api/tests/registry/test_fila_vencimento.py
api/tests/registry/test_estoque_indicador.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/fila_vencimento.tsx
web/src/views/estoque_indicador.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 2 ids tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

| Componente | Params | `requires` | Tamanho |
|---|---|---|---|
| `fila_vencimento` | `unidadeId?` `janela: 30\|60\|90` | `lote.ler` | `inteira` |
| `estoque_indicador` | `metrica` (enum) `unidadeId?` | varia por métrica | `linha` |
| `vencimento_grafico` | `horizonte: 90\|180\|365` `unidadeId?` | `lote.ler` | `inteira` |

> **Por que a curva é componente próprio, e não param do indicador:** o
> indicador responde *quantos*; a curva responde *quando*. "12 lotes vencem em
> 90 dias" não diz se são 12 na semana que vem ou 12 espalhados no trimestre —
> e essa é a diferença entre uma tarde de trabalho e R$ 183 mil perdidos.

Métricas do enum de `estoque_indicador`:
`lotes_em_quarentena` · `lotes_vencendo_90d` · `lotes_bloqueados` ·
`movimentos_hoje` · `valor_em_estoque` *(exige `custo.ler`)*

### Não faz
Ação sobre lote vencido — bloqueio e liberação são T-027.

## Critérios de aceite

- [ ] **AC-1** `janela: 90` lista **todo** lote com validade ≤ 90 dias das unidades
      do ator. *(`CA-03`)*
- [ ] **AC-2** Fronteiras testadas: 89, 90 e 91 dias.
- [ ] **AC-3** Lote que cruza 30 dias aparece já **bloqueado** — o componente
      reflete `RN-L05`, não o reimplementa. Usa `classificarValidade` de T-008.
- [ ] **AC-4** `metrica: valor_em_estoque` **não existe no catálogo** de quem não
      tem `custo.ler`. *(negativo — `CA-05`)*
- [ ] **AC-5** Métrica fora do enum é rejeitada na validação. *(negativo — risco R-5)*
- [ ] **AC-6** Nenhum número renderizado vem do schema. O componente não aceita
      valor literal. *(negativo — inegociável nº 3 da arquitetura)*

## Definição de pronto — adicional
- [ ] Contagem de catálogo no BOARD: **+3**.

## Armadilhas

**AC-6 é sutil e crítico.** Um componente que aceitasse valor literal renderizaria
alucinação com a mesma cara de verdade. O indicador recebe uma *métrica* e a
calcula; nunca recebe *o número*.
