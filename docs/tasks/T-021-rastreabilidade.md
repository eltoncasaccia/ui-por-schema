# T-021 — Rastreabilidade · `CA-01`

| | |
|---|---|
| **Onda** | W3 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-007, T-009, T-010, T-012, T-015 · liberada por T-017 |
| **Componentes** | `rastreabilidade` |
| **ADRs** | [0011](../adr/0011-teto-de-catalogo.md) |
| **Regras** | RN-D03, RN-D04, RN-D05, RN-A01 |
| **Requisitos** | RF-10 · `CA-01` · `RNF-01` |

## Objetivo

O componente que responde ao episódio que motivou o projeto: **o recall da
losartana, nove dias.** O alvo agora é 60 segundos.

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/application/registry/componentes/rastreabilidade.py
api/tests/registry/test_rastreabilidade.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/rastreabilidade.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 1 id tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

| Param | Valores |
|---|---|
| `direcao` | `lote_para_clientes` \| `cliente_para_lotes` |
| `loteId` | obrigatório se `direcao = lote_para_clientes` |
| `clienteId` + `de`/`ate` | obrigatórios se `direcao = cliente_para_lotes` |

`requires: 'auditoria.rastrear'` · `tamanho: 'inteira'`

Um componente, duas direções — fusão deliberada do ADR-0011. O recorte continua
sendo **valor nomeado no enum**.

- Saída no sentido lote → clientes: cliente, nota fiscal, data, quantidade.
- Exportável.

### Não faz
Bloqueio do lote em recall — é `lote_status_acao`, em T-027.

## Critérios de aceite

- [ ] **AC-1** Dado o lote de recall das fixtures (≥ 50 saídas, ≥ 3 clientes), a
      consulta responde em **menos de 60 s**. Teste de performance, não manual.
      *(`CA-01`, `RNF-01`)*
- [ ] **AC-2** O sentido inverso devolve todos os lotes de um cliente num período.
      *(`RN-D04`)*
- [ ] **AC-3** Cada consulta gera registro de auditoria com ator, direção e
      parâmetros. *(`RN-D05`, `CA-01.3`)*
- [ ] **AC-4** Como Odair, a rastreabilidade **não atravessa** para saídas de outras
      unidades. *(negativo — `CA-06`)*
- [ ] **AC-5** `direcao` ausente ou fora do enum é rejeitado. *(negativo)*
- [ ] **AC-6** Params incoerentes com a direção (ex.: `clienteId` com
      `lote_para_clientes`) são rejeitados na validação. *(negativo)*
- [ ] **AC-7** A resposta não expõe custo nem margem para nenhum papel sem
      `custo.ler`. *(`CA-05`)*

## Definição de pronto — adicional
- [ ] Contagem de catálogo no BOARD: **+1**.
- [ ] `RNF-01` medido e o número registrado no relatório de fechamento (T-034).

## Armadilhas

AC-1 precisa de volume real nas fixtures. Medir com 3 movimentos prova nada; por
isso T-006 AC-6 exige ≥ 50 saídas no lote de recall.
