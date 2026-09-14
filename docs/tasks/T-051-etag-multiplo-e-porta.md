# T-051 — Etag por candidato, e a porta que falta para `RepoMovimento`

| | |
|---|---|
| **Onda** | W4 (destrava) |
| **Trilha** | A/C |
| **Tamanho** | **G**, e o levantamento abaixo é o que falta para confirmar |
| **Depende de** | T-050 |
| **Bloqueia** | **T-031**, para `movimento_saida` e `controlado_autorizar` |
| **ADRs** | [0002](../adr/0002-plano-render-plano-escrita.md), [0020](../adr/0020-select-no-servidor.md) |
| **Achado de origem** | [A-41](./ACHADOS.md) — a fatia que a T-050 não cobriu |

## Por que esta tarefa existe

A T-050 fechou o etag na leitura para os dois comandos cujo `If-Match` é
sobre **um** `Lote`, identificado por `params.lote_id`: `quarentena_liberar` e
`lote_status_acao`. Levantando os outros quatro **antes de escrever**, como o
arquivo da T-050 já registrava, apareceram dois problemas de formato
diferentes — não é o mesmo trabalho repetido quatro vezes.

## Os dois problemas, e por que não são o mesmo

### 1. `movimento_saida` — etag por CANDIDATO, não por bloco

`_etag_da_saida` (`commands/saida.py`) soma `saldo` ao dict do etag — uma
consulta assíncrona extra (`_saldo(lote.id, ctx)`) que `_etag_do_lote` não
tem. Mas o problema maior é outro: o componente `movimento_saida` mostra uma
**lista** de lotes candidatos (`proposta` + `alternativas`), e a pessoa
escolhe qual usar DEPOIS da leitura, na tela. O `lote_id` que vai para o
comando não é `params.lote_id` — não existe esse param — é o `lote_id` da
linha escolhida.

`ComponentDef.etag: Callable[[D], str] | None` (o campo que a T-050
acrescentou) devolve **um** etag por leitura do bloco inteiro. Não serve
aqui: precisa de um etag **por linha** do viewmodel (`proposta.etag`,
`alternativas[].etag`), e o cliente manda o etag da linha que a pessoa
selecionou — não o do bloco.

**Isto muda o formato do lado do cliente também.** `render/motor.tsx`
(`enviarAtual`/`api.etagAtual`) hoje lê um etag por `(tipo, params)`; para
`movimento_saida` precisa ler por `(tipo, params, lote_id_escolhido)`, ou a
view precisa incluir o etag da linha escolhida no próprio `corpo` do
`CustomEvent('comando')` — **decisão a tomar antes de escrever**, com uma
recomendação: o segundo caminho (view inclui o etag no `corpo`) é mais
simples porque não exige um mapa de chave composta em `api.ts`, e a view já
tem a linha escolhida em mãos no momento do clique. O `corpo` continuaria
sem afetar o schema do comando — o etag vai no cabeçalho `If-Match`, então
sairia do `corpo` antes do POST, num campo à parte do `DetalheComando`
(`{ acao, corpo, etag }` em vez de só `{ acao, corpo }`).

### 2. `controlado_autorizar` e `movimento_estorno` — a porta não expõe a coluna

`_etag_do_movimento` (`commands/autorizacao.py`) e `_etag_do_original`
(`commands/estorno.py`) não usam `RepoMovimento` — fazem `sa.select()` direto
contra `m.movimento`, lendo `status`/`autorizador_id` (autorização) ou o flag
de já-estornado (estorno). Nenhum método de `data/porta.py` devolve essas
colunas hoje. Para a leitura (`registry/`) calcular o mesmo etag sem repetir
SQL bruto (que violaria o contrato 2 de qualquer forma), `RepoMovimento`
precisa de um método novo — **tarefa de contrato, aditiva**, do mesmo tipo
que a T-048 abriu para `RepoProduto.por_ean`.

### 3. `movimento_descarte` — não conferido

Comece por ele. Pode cair num dos dois casos acima, ou ser um terceiro.

## O que fazer — ordem recomendada

1. Confira `movimento_descarte` primeiro — decide se ele é "caso 1" (múltiplo,
   como `movimento_saida`) ou "caso 2" (porta faltando, como os outros dois).
2. Resolva o caso 2 primeiro (`controlado_autorizar`, `movimento_estorno`,
   possivelmente `movimento_descarte`): método novo em `RepoMovimento`,
   seguindo o padrão da T-048 (porta + adaptador + fake, bateria fake↔banco).
   Depois disso, o etag de cada um é uma função pura em `application/etag.py`,
   igual ao `etag_lote` que a T-050 já deixou — sem obstáculo novo.
3. Resolva `movimento_saida` (e o que mais cair no caso 1) por último: exige
   a decisão de formato registrada acima, e é o único que toca
   `render/comando.ts`.

## Arquivos de propriedade exclusiva

```
api/src/estoque/application/etag.py
api/src/estoque/application/commands/saida.py
api/src/estoque/application/commands/autorizacao.py
api/src/estoque/application/commands/estorno.py
api/src/estoque/application/commands/descarte.py
api/src/estoque/application/registry/definir.py
api/src/estoque/application/registry/componentes/movimento_saida.py
api/src/estoque/application/registry/componentes/controlado_autorizar.py
api/src/estoque/application/registry/componentes/movimento_estorno.py
api/src/estoque/application/registry/componentes/movimento_descarte.py
api/src/estoque/data/porta.py                  (+método(s) em RepoMovimento)
api/src/estoque/data/repositorios.py           (+método(s) em RepoMovimentoSQL)
api/src/estoque/server/rotas/dados.py
api/tests/registry/fakes.py                    (+método(s) em FakeRepoMovimento)
api/tests/server/test_t051_etag_multiplo_e_porta.py

web/src/api.ts
web/src/render/motor.tsx
web/src/render/comando.ts
web/src/views/movimento_saida.tsx
web/src/testes/comando.test.tsx

docs/tasks/CONTRATOS.md   (§4 — método novo de RepoMovimento; §8.1 — formato de etag múltiplo)
```

## Critérios de aceite

- [ ] **AC-1** `controlado_autorizar`, `movimento_estorno` e (se for o caso)
      `movimento_descarte` devolvem `meta.etag` na leitura, calculado por uma
      função pura em `application/etag.py` — a MESMA que a escrita usa.
- [ ] **AC-2** O método novo de `RepoMovimento` tem a MESMA bateria fake↔banco
      que os demais (achado A-11) — sabotar o fake reprova só o lado do fake.
- [ ] **AC-3** `movimento_saida` devolve um etag por LINHA candidata
      (`proposta` e cada item de `alternativas`), e escrever com o etag da
      linha escolhida — não o da proposta, se a pessoa trocou — é aceito.
- [ ] **AC-4** Escrever `movimento_saida` com o etag de uma linha QUE NÃO a
      escolhida (ou desatualizado) devolve `conflito`. *(negativo)*
- [ ] **AC-5** `View<Id>` continua `(props: { vm }) => JSX.Element` — a
      mudança de formato do `DetalheComando` (se `etag` entrar no evento) não
      muda a assinatura da view, só o que ela despacha.
- [ ] **AC-6** Os quatro fluxos completam de ponta a ponta contra o servidor
      real, como a T-050 provou para `quarentena_liberar`.
- [ ] **AC-7** `application.registry` continua sem importar
      `commands.pipeline`/`commands.saida`/`commands.autorizacao`/
      `commands.estorno`/`commands.descarte` — só `application.etag`.
      *(negativo — contrato 2)*

## Armadilhas

**Não generalize `ComponentDef.etag` para aceitar lista antes de confirmar
que só `movimento_saida` precisa disso.** Se `movimento_descarte` cair no
mesmo caso, generalize então — mudar o tipo duas vezes é mais barato que
adivinhar a forma certa sem o segundo exemplo na mão.
