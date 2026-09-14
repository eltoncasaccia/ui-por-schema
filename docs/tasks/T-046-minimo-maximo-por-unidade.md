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

## Antes de começar — o que já está decidido

**Existe um precedente exato, e é recente:** a [T-048](./T-048-porta-produto-por-ean.md)
acrescentou `RepoProduto.por_ean` e fez a mesma travessia — migração, `porta.py`,
`repositorios.py`, fake, bateria fake↔banco e revisão de CONTRATOS §4. **Leia a
T-048 e o `api/tests/data/test_produto_por_ean.py`; não leia mais nada** para
descobrir a forma.

| Fato | Valor conferido em 2026-09-10 |
|---|---|
| última migração | `0006_ean_unico.py` → a sua é **`0007`** |
| revisão de CONTRATOS | está em **2.3** (T-048) → a sua é **2.4**, aditiva |
| unidades reais | `cd-matriz` · `cd-refrigerado` · `filial-uberlandia` — as duas primeiras ficam em Ribeirão Preto, a terceira é a filial |
| bateria fake↔banco | `api/tests/data/test_produto_por_ean.py`: `Protocol` local + `_bateria(impl)` + dois testes |

**A faixa é exibida em `produto_saldo_por_unidade`, não em `produto_ficha`.** A
tarefa dizia "e/ou" e isso é decisão, não estilo: `RN-P06` é por **par** (produto,
unidade), e `produto_ficha` é a ficha do produto — ela não tem eixo de unidade
onde pendurar duas faixas diferentes. `produto_saldo_por_unidade` já lista uma
linha por unidade, e é lá que "abaixo do mínimo" quer dizer alguma coisa.
Consequência: o AC-7 da T-019 passa a ser verificado **naquele** componente.

**Os valores do seed são invenção sua, e precisam ser registrados.** Não há
mín/máx em documento nenhum (é o próprio A-30). Escolha valores plausíveis para
os produtos que já existem no seed, ponha-os no `seed/**` com um comentário
dizendo que são arbitrados, e anote no fechamento — para o cliente poder
corrigi-los sem arqueologia.

## Arquivos de propriedade exclusiva

```
api/migrations/versions/0007_minimo_maximo_por_unidade.py
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
- Seed determinístico: `filial-uberlandia` com faixa **diferente** de `cd-matriz`
  para o mesmo produto — é o exemplo do próprio `RN-P06`, e é o que faz o AC-1
  poder falhar.
- `produto_saldo_por_unidade` passa a exibir mín/máx por unidade, com marcação de
  "abaixo do mínimo" (ver a decisão registrada acima).
- Revisão de CONTRATOS §4 com nota de versão.

### Não faz

Edição de mín/máx pela interface — não há escrita de produto no ciclo 1. Ponto
de reposição / curva de consumo — é roadmap, não `RN-P06`.

## Critérios de aceite

- [x] **AC-1** Mín e máx são lidos por par (produto, unidade): o mesmo produto
      tem faixas diferentes em unidades diferentes. *(`RN-P06`)*
- [x] **AC-2** A faixa chega **intersectada com o escopo**: Odair não vê a faixa
      de uma unidade que não é dele, nem pedindo. *(negativo — `RN-A01`)*
- [x] **AC-3** O método novo da porta tem o mesmo comportamento no fake e no
      repositório real — entra na bateria da T-042 se ela já existir, ou traz o
      seu par de testes.
      *Par próprio em `test_minimo_maximo.py`, apontado na `COBERTURA` da T-042:
      a aplicação só tem `SELECT` na tabela, então a bateria da T-042 não pode
      gravar faixa na transação dela — o lado real lê o seed, como a T-048.*
- [x] **AC-4** `produto_saldo_por_unidade` exibe a faixa e a marcação de "abaixo
      do mínimo", e o AC-7 da T-019 passa a ser verificável — **inclusive o
      negativo**: um produto dentro da faixa não vem marcado.
- [x] **AC-5** CONTRATOS §4 revisado, com nota de versão e data. O `import-linter`
      e a bijeção continuam verdes.
- [x] **AC-6** `CHECK (maximo >= minimo)` recusa uma linha inválida — provado no
      banco. *(negativo)* *E `minimo >= 0`, com contraponto válido.*

## Fechamento — 2026-09-14

- Tabela `produto_unidade` (migração `0007`), `FaixaEstoque` no domínio,
  `RepoProduto.faixas` intersectando escopo, CONTRATOS rev. 2.4.
- **Valores do seed ARBITRADOS** (`dados.faixas_de_estoque`): mínimo por curva
  (A 200, B 100, C 40), máximo 4×; a filial com metade da faixa da Matriz;
  termolábil só no CD Refrigerado. Trocar pelos valores reais da Bertoni.
- A tela marca "abaixo do mínimo"; unidade com faixa e sem lote aparece com
  saldo zero, marcada.
- **Tocou, com registro:** os arquivos listados acima, e mais `data/modelos.py`
  (a tabela no SQLAlchemy), `web/src/views/produto_saldo_por_unidade.tsx` e
  `tests/data/porta_contrato.py` (cobertura).
- **Armadilha de ambiente:** `make migrate` e `make seed` usam a imagem já
  construída da API — migração nova só é vista depois de
  `docker compose build api`.

## Armadilhas

**Pôr mín/máx no `Produto`.** É a modelagem errada que o `RN-P06` existe para
impedir: a faixa não é atributo do produto, é do par com a unidade. Uma coluna
`minimo` em `produto` obriga um valor único para toda a rede.

**Faixa sem escopo.** O método novo é porta de dados: a interseção com as
unidades do ator é invariante da porta (`RN-A01`), não passo do `load`.
