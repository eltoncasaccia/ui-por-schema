# T-044 — `relatorio_movimentacao`

| | |
|---|---|
| **Trilha** | C · catálogo |
| **Tamanho** | M |
| **Depende de** | T-024 (`movimento_lista`), T-010 (trilha de auditoria) |
| **Decide** | [ADR-0029](../adr/0029-relatorio-como-componente.md) |
| **Custo de escopo** | **+1 no catálogo** — vai a 24, folga cai para 1 |

## Por que existe

Relatório é a mesma pergunta com eixos trocados. Um componente por corte esgota
o teto de 25 antes de esgotar a necessidade, e cada corte novo vira tarefa —
o cliente fica dependente da equipe para perguntar o que já está no banco.

Este componente troca 300 relatórios possíveis por ~164 tokens de catálogo.

## Antes de começar — o que já está decidido

**Skill:** `componente-novo` (cobre os dois lados e os testes obrigatórios).
**Imite dois arquivos, e só dois:**

- `registry/componentes/estoque_indicador.py` — tem o `RequiresPorValor` montado
  e testado, **e** o caminho do custo (`repos.produto.por_ids(...)` seguido da
  multiplicação, nas linhas do `valor_em_estoque`). É o precedente exato do seu
  `metrica: valor`.
- `registry/componentes/movimento_lista.py` — leitura de movimento com recorte de
  período, que é a sua fonte.

**A fonte é `RepoMovimento.listar(ctx, *, unidade_id, tipo, status, de, ate)`.**
Conferido no adaptador real: `de` e `ate` **são** aplicados (diferente do
`por_cliente`, que é o [A-31](./ACHADOS.md)).

## Duas coisas que a tarefa não previa, e mudam o plano

**1. `RepoMovimento.listar` trunca em 500 no adaptador real.** Há um
`.limit(500)` fixo. Um relatório de 365 dias agrupado por produto leria 500
movimentos e apresentaria o total como se fossem todos — **um número errado com
cara de certo**, que é o pior resultado possível para um relatório.

> **Recomendação:** não contorne no componente. Ou a T-042 resolve o limite na
> porta antes (ela já vai encontrar essa divergência fake↔real), ou esta tarefa
> **declara o truncamento no viewmodel** — um campo `truncado: bool` e a tela
> dizendo "amostra de 500 movimentos", nunca um total silenciosamente errado.
> Decidir isso é o **primeiro** passo da tarefa, não o último.

**2. `metrica: valor` atravessa três entidades e a porta não ajuda.** O custo
está em `Produto`; o movimento só conhece `lote_id`. O caminho é
`movimento → lote → produto`, e **`RepoLote` não tem `por_ids`** — só `por_id`
(um a um), `listar` e `saldos`.

> **Recomendação:** uma chamada a `repos.lote.listar(ctx.dados, unidade_id=...)`
> e indexar em memória, depois `produto.por_ids` sobre os `produto_id` distintos
> — dois acessos, sem N+1 e **sem mudar contrato**. O relatório já é escopado,
> então o conjunto é limitado.
> A alternativa é acrescentar `RepoLote.por_ids` à porta, o que torna esta uma
> **tarefa de contrato** (CONTRATOS §4, congelado, hoje em rev. 2.3) e muda o
> tamanho dela. Se escolher esse caminho, **pergunte antes** (ADR-0028).

**Paginação não é param.** `Pagina` é preocupação de transporte e chega por
`ctx.pagina` (ver `definir.py`); o modelo não decide quantas linhas cabem. A
armadilha "agregação sem teto", lá embaixo, se resolve por aí — e o viewmodel
diz que paginou.

## Arquivos de propriedade exclusiva

**Lado servidor**

```
api/src/estoque/application/registry/componentes/relatorio_movimentacao.py
api/tests/registry/test_relatorio_movimentacao.py
```

**Lado cliente**

```
web/src/views/relatorio_movimentacao.tsx
```

> Atravessa os dois lados pelo [ADR-0017](../adr/0017-registry-servidor-views-cliente.md).
> O teste de bijeção exige registro **e** view — entregar um lado quebra o CI.

## Só leitura

`api/src/estoque/data/porta.py`, `api/src/estoque/domain/**`,
`api/src/estoque/application/registry/definir.py`

## Escopo

### Faz

| Param | Valores | |
|---|---|---|
| `agrupar_por` | `unidade` `produto` `motivo` `mes` `classe` | eixo |
| `metrica` | `quantidade` `movimentos` `valor` | `valor` exige `custo.ler` |
| `tipo` | `entrada` `saida` `descarte` `estorno` `todos` | padrão `todos` |
| `periodo` | `30` `90` `180` `365` | padrão `90` |
| `unidade_id` | `UnidadeId \| None` | opcional |

`requires: ("movimento.ler",)` como base, e `valor` acrescenta `custo.ler` via
**`RequiresPorValor`** — o mesmo mecanismo já usado e testado em
`estoque_indicador`. `tamanho: "inteira"`.

O viewmodel traz as linhas agregadas, o **total geral**, o eixo aplicado em
texto e o recorte em texto — o mesmo contrapeso ao risco R-5 que `lote_lista`
usa: um filtro esquecido devolve mais linhas, e a tela passa a dizer qual corte
ela representa.

### Não faz

- **Não** aceita dimensão nem métrica fora dos enums. Sem campo livre, sem SQL.
- **Não** exporta. Exportação é pipeline próprio, e vale para vários componentes.
- **Não** faz série temporal desenhada — `agrupar_por: mes` devolve tabela.
  Gráfico de movimentação é outra tarefa, se o cliente pedir.
- **Não** cobre perdas por motivo como relatório separado. Cabe em
  `tipo: descarte` + `agrupar_por: motivo`. Um `relatorio_perdas` estouraria o
  teto e é discussão de escopo (ADR-0011).

## Critérios de aceite

- [ ] **AC-1** `agrupar_por` fora do enum é rejeitado na validação.
      *(negativo — risco R-5)*
- [ ] **AC-2** Para Cleide, Helena, Ivo e Odair, o valor `valor` **não aparece**
      no enum de `metrica` do catálogo; para Marco, Rafael e Sandra, aparece.
      *(negativo — `CA-05`, ADR-0003)*
- [ ] **AC-3** Com `metrica` diferente de `valor`, o viewmodel **não contém
      custo** — nem para quem tem `custo.ler`. *(ADR-0020)*
- [ ] **AC-4** Odair, agrupando por `unidade`, vê **apenas Uberlândia** — mesmo
      passando `unidade_id` de outra unidade. *(negativo — `CA-06`, `RN-A01`)*
- [ ] **AC-5** Os cinco eixos produzem agregação correta sobre o mesmo conjunto:
      a soma de `quantidade` é **idêntica** nos cinco. *(a conta fecha por
      qualquer caminho, ou o agrupamento está errado)*
- [ ] **AC-6** `select` é puro: duas chamadas sobre a mesma carga dão o mesmo.
- [ ] **AC-7** Relatório vazio (período sem movimento) devolve viewmodel válido
      com `total: 0` — **não** erro, e **não** lista de outro período.
- [ ] **AC-8** A `description` do componente **não cita** `valor` como métrica
      disponível. *(a prosa não pode vazar o que o enum filtrou — invariante
      encontrada em `test_descricao_nunca_enumera_valor_de_enum_filtrado`)*
- [ ] **AC-9** Um período que ultrapassa o teto de leitura do repositório é
      **declarado** no viewmodel, não silenciado: o total nunca é apresentado
      como completo quando a leitura foi truncada. *(negativo — ver "duas coisas
      que a tarefa não previa", item 1)*

## Definição de pronto — adicional

- [ ] Contagem de catálogo no BOARD §5 atualizada: **24, folga 1**
- [ ] Entrou no teste de catálogo por persona (T-012 AC-1)
- [ ] Cenário 10 de [CENARIOS.md](../CENARIOS.md) executado à mão, e o resultado
      registrado lá — inclusive o que **falhou**

## Armadilhas

**O eixo que falta.** Se o operador pensa em "por fornecedor" e o valor não está
no enum, ele recebe um relatório **parecido e errado**. Ao escrever os
`examples`, use os eixos que existem — e registre como achado todo eixo que
aparecer nas perguntas reais e não estiver no enum.

**Descrição vaga.** Um componente com 300 saídas é difícil de descrever em ~164
tokens. Descrição genérica produz composição errada em silêncio. Escreva para o
modelo decidir *quando usar este e não `movimento_lista`* — e diga isso na
descrição, com todas as letras.

**Agregação sem teto.** `agrupar_por: produto` num período de 365 dias pode
devolver milhares de linhas. Pagine, e diga no viewmodel que paginou.
