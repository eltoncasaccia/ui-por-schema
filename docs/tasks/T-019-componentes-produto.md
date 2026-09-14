# T-019 — Componentes de produto e custo restrito

| | |
|---|---|
| **Onda** | W3 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-007, T-009, T-012, T-015 · liberada por T-017 |
| **Componentes** | `produto_ficha` `produto_saldo_por_unidade` |
| **ADRs** | [0003](../adr/0003-catalogo-por-ator.md) |
| **Regras** | RN-P01, RN-P05, RN-P06, RN-A02 |
| **Requisitos** | RF-14 · `CA-05` · `CS-02` |

## Objetivo

Os dois componentes de produto — e o teste mais importante de confidencialidade do
release: **custo invisível por todos os caminhos.**

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/application/registry/componentes/produto_ficha.py
api/src/estoque/application/registry/componentes/produto_saldo_por_unidade.py
api/tests/registry/test_produto_ficha.py
api/tests/registry/test_produto_saldo_por_unidade.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/produto_ficha.tsx
web/src/views/produto_saldo_por_unidade.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 2 ids tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

| Componente | Params | `requires` | Tamanho |
|---|---|---|---|
| `produto_ficha` | `produtoId` | `produto.ler` | `meia` |
| `produto_saldo_por_unidade` | `produtoId` | `lote.ler` | `meia` |

- `produto_ficha` exibe custo **apenas** quando o ator tem `custo.ler`. Na
  execução: **não** é um segundo id (isso seria +3 no catálogo, contra o "+2"
  desta tarefa e o teto do ADR-0011), e **não** é campo condicional no viewmodel.
  É um **valor de param** — `variante="com_custo"` — que o catálogo REMOVE de
  quem não tem `custo.ler` via `RequiresPorValor`, o mesmo mecanismo do
  `valor_em_estoque` no `estoque_indicador` (achado A-05). A chave
  `custo_unitario_centavos` fica ausente do viewmodel nos demais casos.
- Produto inativo aparece marcado, com saldo visível até esgotar (`RN-P05`).
- ~~Mínimo e máximo são **por produto e por unidade** (`RN-P06`).~~ **Fora** —
  não há armazenamento no sistema. Achado [A-30](./ACHADOS.md), tarefa
  [T-046](./T-046-minimo-maximo-por-unidade.md).

### Não faz
Cadastro ou edição de produto — não há escrita de produto no ciclo 1.

## Critérios de aceite

- [x] **AC-1** Como Cleide, Helena, Ivo ou Odair: a resposta **não contém a chave**
      `custoUnitario` — ausente, não `undefined`. *(negativo — `CA-05`)*
      → `test_produto_ficha.py::test_ac1_*` — chave ausente do `model_dump()` e
      `"custo"` ausente do JSON, inclusive forçando `variante=com_custo`.
      Omissão estrutural via `@model_serializer` no VM.
- [x] **AC-2** Como Rafael, Marco ou Sandra: custo presente.
      → `test_ac2_custo_presente_quando_pedido` (valor 1250) e
      `test_ac2_custo_ausente_quando_nao_pedido` (só com `variante=com_custo`).
- [x] **AC-3** Nenhum componente que exponha custo entra no catálogo dos quatro
      papéis sem `custo.ler`. *(negativo — `CS-02`)*
      → `test_catalogo_por_ator.py::test_variante_de_custo_da_ficha_some_do_enum_de_quem_nao_pode`.
      `produto_ficha` fica no catálogo dos 7; o **valor** `com_custo` é que some
      (mecanismo A-05, igual a `valor_em_estoque`).
- [x] **AC-4** Perguntar explicitamente "qual o custo deste produto" como Cleide
      não produz o valor **por nenhum caminho**, incluindo agregados derivados
      (valor total em estoque). *(negativo — `CA-05`, o caso mais fácil de esquecer)*
      → `test_ac4_schema_forjado_com_variante_de_custo_e_rejeitado` (revalidação
      no servidor recusa pelo valor do param) e
      `test_ac4_agregado_de_custo_tambem_continua_barrado`.
- [x] **AC-5** Exportação do componente respeita a mesma regra. *(`CA-05` diz
      "inclusive em exportação")*
      → `test_ac5_exportacao_do_viewmodel_nao_leva_custo`. Não há caminho de
      exportação separado; a omissão é do `@model_serializer`, então
      `model_dump(mode="json")` (formato da borda) e qualquer export herdam.
- [x] **AC-6** Produto inativo é exibido com marcação e saldo. *(`RN-P05`)*
      → `test_ac6_produto_inativo_exibido_com_marcacao_e_saldo` (`vm.ativo is
      False`, `saldo_total == 40`); view põe etiqueta "Inativo".
- [x] **AC-7** Mínimo e máximo variam por unidade no mesmo produto. *(`RN-P06`)*
      *Fechado pela [T-046](./T-046-minimo-maximo-por-unidade.md), em
      `produto_saldo_por_unidade` (a ficha não tem eixo de unidade).*
      → **EM BRANCO.** Não há armazenamento para `RN-P06` no sistema (sem tabela,
      sem campo de domínio, sem método de porta, sem seed). Achado [A-30](./ACHADOS.md);
      fechamento na [T-046](./T-046-minimo-maximo-por-unidade.md).

## Definição de pronto — adicional
- [x] Contagem de catálogo no BOARD: **+2** (`produto_ficha`,
      `produto_saldo_por_unidade`) — 13 → 15 registrados.

## Armadilhas

**AC-4 é o critério que pega o vazamento real.** Esconder o campo e deixar passar
"valor total em estoque" entrega a mesma informação por soma. Todo agregado
derivado de custo carrega `custo.ler`.
