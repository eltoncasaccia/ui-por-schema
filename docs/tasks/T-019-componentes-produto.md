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
api/src/estoque/registry/componentes/produto_ficha.py
api/src/estoque/registry/componentes/produto_saldo_por_unidade.py
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

- `produto_ficha` exibe custo **apenas** quando o ator tem `custo.ler`. A variante
  com custo é **um componente distinto no catálogo**, com `requires: ['produto.ler','custo.ler']`
  — não um campo condicional dentro do mesmo componente.
- Produto inativo aparece marcado, com saldo visível até esgotar (`RN-P05`).
- Mínimo e máximo são **por produto e por unidade** (`RN-P06`).

### Não faz
Cadastro ou edição de produto — não há escrita de produto no ciclo 1.

## Critérios de aceite

- [ ] **AC-1** Como Cleide, Helena, Ivo ou Odair: a resposta **não contém a chave**
      `custoUnitario` — ausente, não `undefined`. *(negativo — `CA-05`)*
- [ ] **AC-2** Como Rafael, Marco ou Sandra: custo presente.
- [ ] **AC-3** Nenhum componente que exponha custo entra no catálogo dos quatro
      papéis sem `custo.ler`. *(negativo — `CS-02`)*
- [ ] **AC-4** Perguntar explicitamente "qual o custo deste produto" como Cleide
      não produz o valor **por nenhum caminho**, incluindo agregados derivados
      (valor total em estoque). *(negativo — `CA-05`, o caso mais fácil de esquecer)*
- [ ] **AC-5** Exportação do componente respeita a mesma regra. *(`CA-05` diz
      "inclusive em exportação")*
- [ ] **AC-6** Produto inativo é exibido com marcação e saldo. *(`RN-P05`)*
- [ ] **AC-7** Mínimo e máximo variam por unidade no mesmo produto. *(`RN-P06`)*

## Definição de pronto — adicional
- [ ] Contagem de catálogo no BOARD: **+2**.

## Armadilhas

**AC-4 é o critério que pega o vazamento real.** Esconder o campo e deixar passar
"valor total em estoque" entrega a mesma informação por soma. Todo agregado
derivado de custo carrega `custo.ler`.
