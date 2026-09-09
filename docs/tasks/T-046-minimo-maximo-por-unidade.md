# T-046 — Estoque mínimo e máximo por produto e por unidade (`RN-P06`)

| | |
|---|---|
| **Trilha** | A · dados (com mudança de contrato) |
| **Tamanho** | M |
| **Depende de** | T-002, T-007, T-036, T-006 |
| **Bloqueia** | AC-7 da [T-019](./T-019-componentes-produto.md) |
| **Origem** | achado [A-30](./ACHADOS.md), execução da T-019 (2026-09-09) |
| **Regras** | `RN-P06` |

## Por que existe

`RN-P06` — *"estoque mínimo e máximo são por produto **e** por unidade"* — é
regra do documento 02, e **a camada de dados nunca a implementou**. Na execução
da T-019 o `produto_ficha` precisava exibir a faixa e não havia de onde ler:

| Onde deveria estar | Situação em 2026-09-09 |
|---|---|
| tabela `produto` (migração 0001) | sem coluna |
| tabela `produto_unidade` ou equivalente | não existe |
| `Produto` em `domain/tipos.py` | só `custo_unitario_centavos` |
| `RepoProduto` em `data/porta.py` (CONTRATOS §4, **congelado**) | só `por_id` / `por_ids` |
| seed da Bertoni (T-006) | nada |

A T-019 entregou `produto_ficha` e `produto_saldo_por_unidade` cobrindo AC-1 a
AC-6; **o AC-7 ficou em branco** e é o que esta tarefa fecha.

## É também uma tarefa de contrato

Adicionar um método a `RepoProduto` altera CONTRATOS §4, que é congelado. Esta
tarefa **é** a tarefa de contrato — trata a mudança de §4 explicitamente, não
"de passagem". Nenhuma tarefa de feature pode fazer isso no lugar.

## Arquivos de propriedade exclusiva

```
api/migrations/versions/00NN_minimo_maximo_por_unidade.py
api/tests/data/test_minimo_maximo.py
```

## Toca, com registro (fora da propriedade exclusiva — declarar no fechamento)

```
api/src/estoque/domain/tipos.py        campo/estrutura de mín/máx por unidade
api/src/estoque/data/porta.py          método novo em RepoProduto  ← CONTRATOS §4
api/src/estoque/data/repositorios.py   implementação real
api/tests/registry/fakes.py            o fake correspondente + fixture
api/src/estoque/data/seed/**           dados de mín/máx da Bertoni
docs/tasks/CONTRATOS.md                §4, com nota de revisão
api/src/estoque/application/registry/componentes/produto_ficha.py            exibe a faixa
api/src/estoque/application/registry/componentes/produto_saldo_por_unidade.py exibe a faixa
```

> A intersecção com `produto_ficha.py` e `produto_saldo_por_unidade.py` (da
> T-019) é esperada: a T-019 os entregou sem a faixa, esta tarefa a acrescenta.
> Coordenar se as duas estiverem abertas ao mesmo tempo.

## Escopo

### Faz

- Modelagem de mín/máx **por par (produto, unidade)** — tabela associativa, com
  `CHECK (maximo >= minimo)` e `CHECK (minimo >= 0)`.
- Campo/estrutura no domínio, método na `RepoProduto` que devolve a faixa por
  unidade **já intersectada com o escopo do ator** (`RN-A01`), como todo o resto
  da porta.
- Seed determinístico: Uberlândia com faixa diferente de Ribeirão para o mesmo
  produto — é o exemplo do próprio `RN-P06`.
- `produto_ficha` (variante padrão) e/ou `produto_saldo_por_unidade` passam a
  exibir mín/máx por unidade, com marcação de "abaixo do mínimo".
- Revisão de CONTRATOS §4 com nota de versão.

### Não faz

Edição de mín/máx pela interface — não há escrita de produto no ciclo 1. Ponto
de reposição / curva de consumo — é roadmap, não `RN-P06`.

## Critérios de aceite

- [ ] **AC-1** Mín e máx são lidos por par (produto, unidade): o mesmo produto
      tem faixas diferentes em unidades diferentes. *(`RN-P06`)*
- [ ] **AC-2** A faixa chega **intersectada com o escopo**: Odair não vê a faixa
      de uma unidade que não é dele, nem pedindo. *(negativo — `RN-A01`)*
- [ ] **AC-3** O método novo da porta tem o mesmo comportamento no fake e no
      repositório real — entra na bateria da T-042 se ela já existir, ou traz o
      seu par de testes.
- [ ] **AC-4** `produto_ficha` / `produto_saldo_por_unidade` exibem a faixa e a
      marcação de "abaixo do mínimo", e o AC-7 da T-019 passa a ser verificável.
- [ ] **AC-5** CONTRATOS §4 revisado, com nota de versão e data. O `import-linter`
      e a bijeção continuam verdes.
- [ ] **AC-6** `CHECK (maximo >= minimo)` recusa uma linha inválida — provado no
      banco. *(negativo)*

## Armadilhas

**Pôr mín/máx no `Produto`.** É a modelagem errada que o `RN-P06` existe para
impedir: a faixa não é atributo do produto, é do par com a unidade. Uma coluna
`minimo` em `produto` obriga um valor único para toda a rede.

**Faixa sem escopo.** O método novo é porta de dados: a interseção com as
unidades do ator é invariante da porta (`RN-A01`), não passo do `load`.
