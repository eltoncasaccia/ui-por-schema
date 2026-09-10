# T-042 — Contract test: o fake e o repositório real obedecem à mesma porta

| | |
|---|---|
| **Trilha** | A · dados |
| **Tamanho** | M |
| **Depende de** | T-007 (repositórios), T-036 (schema) |
| **Origem** | achado da auditoria de testes, 2026-09-08 |

## Por que existe

`api/tests/registry/fakes.py` **reimplementa** a interseção de escopo que
`data/porta.py` promete (`RN-A01`). Hoje, os testes de componente provam que o
*componente* não contorna a porta — e não provam nada sobre o adaptador real.

> Se o repositório SQLAlchemy parar de intersectar escopo, **todos os testes de
> registry continuam verdes.** Um gerente passaria a ver as unidades dos outros,
> e a suíte não diria uma palavra.

`tests/data/` só tem os testes de imutabilidade. Não existe teste de escopo no
adaptador real.

## Antes de começar — o que já está decidido

**A forma já existe, para um método.** `api/tests/data/test_produto_por_ean.py`
(T-048) tem exatamente este desenho: um `Protocol` local com a assinatura, uma
função `_bateria(...)` que recebe a implementação, e dois testes que a chamam —
um com `fakes.FakeRepoProduto()`, outro com o repositório real numa conexão.
**Imite esse arquivo e generalize**; não invente formato.

**Skill:** nenhuma. Isto é teste de dados, não componente nem comando. As
convenções de pytest estão em `api/.claude/skills/testes-python`.

**A superfície a cobrir são 6 portas, 12 métodos** — de `data/porta.py`, para não
precisar abri-lo:

| Porta | Métodos | Observação |
|---|---|---|
| `RepoLote` | `por_id` `listar` `saldos` | `listar` ordena por `(validade, id)` |
| `RepoProduto` | `por_id` `por_ids` `por_ean` | **`por_ean` não intersecta unidade** — produto não pertence a unidade (`RN-P01`); só omite custo |
| `RepoMovimento` | `do_lote` `listar` `por_cliente` | o real tem `.limit(500)` em `listar` — ver armadilha |
| `RepoRecebimento` | `por_id` `listar` | ordem: `recebido_em` desc, `id` asc |
| `RepoTemperatura` | `serie` | |
| `RepoAuditoria` | `listar` | **sem escopo de unidade, de propósito** — a tabela não tem `unidade_id` |

> As duas linhas em negrito são a razão de a bateria **não** poder ser uma só
> asserção de escopo aplicada a tudo: `por_ean` e `RepoAuditoria` seriam
> reprovados por cumprirem o contrato. Trate-os como casos nomeados.

## Decisão embutida: o A-31 é desta tarefa

[A-31](./ACHADOS.md) — `RepoMovimento.por_cliente` **ignora `de` e `ate`**, no
fake e no real. A bateria vai reprovar os dois, e é para isso que ela existe.

**Consertar o adaptador real é escopo daqui** (é a porta, não o componente), e
`repositorios.py` sai de "só leitura" para "toca, com registro". O conserto do
fake também. Isso **fecha o A-31** — mova-o para `achados-resolvidos.md` no
mesmo commit.

## Arquivos de propriedade exclusiva

```
api/tests/data/test_contrato_da_porta.py
api/tests/data/porta_contrato.py        (a bateria compartilhada)
```

## Toca, com registro (fora da propriedade exclusiva — declarar no fechamento)

```
api/src/estoque/data/repositorios.py    conserto do `por_cliente` (A-31)
api/tests/registry/fakes.py             conserto do fake correspondente
```

## Só leitura

`api/src/estoque/data/porta.py`, `api/src/estoque/domain/**`

## Escopo

### Faz

Uma **bateria única** de asserções sobre a porta, executada duas vezes: contra o
fake e contra o repositório real ligado ao Postgres. Parametrize por
implementação — a mesma função de teste, dois `pytest.param`.

O que a bateria tem de cobrir, no mínimo:

| Invariante | Regra |
|---|---|
| interseção de escopo vem **antes** do critério | `RN-A01` |
| `unidade_id` de fora do escopo devolve **vazio**, nunca erro | ADR-0014 |
| `por_id` de registro fora do escopo devolve `None` | ADR-0014 |
| `saldos` só considera movimento `efetivado` | `RN-M06` |
| `saldos` de lote fora do escopo **não aparece no dicionário** | `RN-A01` |
| custo chega **ausente** para quem não tem `custo.ler` | `RN-A02` |
| ordenação estável por `(validade, id)` | paginação por cursor depende disso |

### Não faz

Imutabilidade — já é `tests/data/test_imutabilidade_no_banco.py`.
Não reescreve os fakes; corrige-os se a bateria os reprovar.

## Critérios de aceite

- [ ] **AC-1** A mesma bateria roda contra fake e repositório real, e os dois
      passam.
- [ ] **AC-2** Removendo a interseção de escopo do repositório **real**, a
      bateria **falha**. *(negativo — é o teste que prova que este teste serve)*
- [ ] **AC-3** Removendo a interseção do **fake**, a bateria falha também.
      *(negativo — um fake permissivo é pior que fake nenhum)*
- [ ] **AC-4** Um método novo na porta sem cobertura na bateria é detectado —
      por reflexão sobre o `Protocol`, ou por lista explícita que falha ao
      divergir.
- [ ] **AC-5** No CI, a bateria contra o repositório real **não pula**. Teste
      que pula é teste que não existe.

## Armadilhas

**Bateria escrita a partir do fake.** Se você derivar as asserções lendo
`fakes.py`, vai codificar o comportamento dele — inclusive os erros. Derive de
`data/porta.py` e das `RN-*` citadas; o fake é candidato a estar errado.

**Fixture divergente.** Os dois lados precisam do *mesmo* conjunto de dados, ou
a comparação não vale. O `test_produto_por_ean.py` resolveu isso semeando no
banco os **mesmos** valores que `fakes.PRODUTOS` já tem, e lendo o esperado do
próprio fake (`fakes.PRODUTOS["p-vac"].ean`). Copie a solução: uma constante
divergindo entre os dois lados faz a bateria comparar coisas diferentes e passar.

**O `.limit(500)` do `RepoMovimento.listar`.** O adaptador real trunca em 500 e o
fake **não trunca**. É divergência de contrato, e a bateria vai encontrá-la.
Decida e registre: ou o limite sobe para a porta (e o fake passa a truncar
igual), ou vira parâmetro. Não deixe passar em silêncio — um relatório de 365
dias (T-044) lê essa mesma função e receberia 500 linhas achando que são todas.
