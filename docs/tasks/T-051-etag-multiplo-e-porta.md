# T-051 — Etag por linha: os três onde a pessoa escolhe depois de ler

| | |
|---|---|
| **Onda** | W4 (destrava) |
| **Trilha** | A/C |
| **Tamanho** | G |
| **Depende de** | T-050 |
| **Bloqueia** | **T-031**, para `movimento_saida` e `controlado_autorizar` |
| **ADRs** | [0002](../adr/0002-plano-render-plano-escrita.md), [0020](../adr/0020-select-no-servidor.md) |
| **Achado de origem** | [A-41](./ACHADOS.md) — a fatia que a T-050 não cobriu |

## Correção antes de começar — o levantamento da T-050 estava parcialmente errado

O arquivo original desta tarefa dizia que `controlado_autorizar` e
`movimento_estorno` precisavam de um método novo em `RepoMovimento`, porque
`_etag_do_movimento`/`_etag_do_original` (em `commands/*.py`) leem colunas via
`sa.select()` direto em vez de usar a porta. **Isso é verdade sobre o
COMANDO, e não diz nada sobre o REGISTRY.**

Conferindo `domain/tipos.py`, o dataclass `Movimento` já tem `status`,
`autorizador_id` e `estorna_movimento_id` — exatamente as colunas que os dois
comandos leem à mão. E `ctx.repos.movimento.listar`/`.do_lote` (que
`controlado_autorizar.carregar` e `movimento_estorno.carregar` já chamam para
montar a própria fila) devolvem `Movimento` **completo**. Não falta método
na porta — falta só uma função pura em `application/etag.py` que projeta o
mesmo formato do hash a partir do domínio já carregado. **Nenhuma tarefa de
contrato é necessária.**

O problema real, para os três que sobraram, é outro — e esse é verdadeiro.

## O problema real: etag por LINHA, não por bloco

`quarentena_liberar` e `lote_status_acao` (T-050) recebem `lote_id` como
`params` — um alvo fixo, um etag por leitura. `movimento_saida`,
`movimento_descarte` e `movimento_estorno` mostram uma **lista** (candidatos
de saída, fila de descarte, extrato de lançamentos) e a pessoa escolhe a
linha **depois** da leitura, no cliente — `escolhido`, estado local da view,
mudando com o clique num rádio. O comando manda o `lote_id`/`movimento_id` da
linha escolhida, não um id fixo de `params`.

Um etag por bloco (`ComponentDef.etag`, o campo que a T-050 acrescentou) não
serve: não há como saber, na leitura, qual linha a pessoa vai escolher.
**O etag mora no viewmodel, um por linha** — `LoteCandidato.etag`,
`LoteDescartavel.etag`, `Lancamento.etag` — calculado em `select()` (que já
tem o domínio completo de cada linha), do mesmo jeito que qualquer outro
campo projetado.

`controlado_autorizar` **não tem esse problema**: `alvo` é fixo por
`params.movimento_id`, igual a `quarentena_liberar` — segue o padrão da T-050
sem alteração nenhuma, é só a fatia que faltava.

## O que fazer

1. **`application/etag.py`**: mais três funções puras, cada uma espelhando o
   dict exato do `_etag_do_*` correspondente:
   - `etag_lote_e_saldo(lote: Lote, saldo: int) -> str` — `{id, status,
     validade, saldo}`, para `movimento_saida` (`_etag_da_saida`) e
     `movimento_descarte` (`_etag_do_lote` de lá — nome igual, arquivo
     diferente).
   - `etag_movimento_autorizacao(mov: Movimento) -> str` — `{id, status,
     autorizador_id}`, para `controlado_autorizar`.
   - `etag_movimento_estorno(mov: Movimento, estornado: bool) -> str` —
     `{id, status, lote_id, quantidade, estornado}`, para `movimento_estorno`.
     `estornado` é `domain.regras.estados.ja_estornado(mov, todos)` — já
     calculado em `movimento_estorno.py:_lancamento` para `impedimento`.

2. **`commands/autorizacao.py`, `commands/estorno.py`, `commands/saida.py`,
   `commands/descarte.py`**: cada `_etag_do_*` passa a chamar a função de
   `application/etag.py` em vez de montar o dict à mão. Mesmo hash, uma
   definição — o que a T-050 já fez para `commands/lote.py`.

3. **`registry/componentes/controlado_autorizar.py`**: ganha
   `etag=lambda d: etag_movimento_autorizacao(mov) if (mov := next((m for m in
   d.movimentos if m.id == d.alvo_id), None)) else None` — bloc-level, como
   `quarentena_liberar`. `server/rotas/dados.py` já sabe popular `meta.etag`
   a partir de `ComponentDef.etag` (T-050) — **nenhuma mudança lá**.

4. **`registry/componentes/movimento_saida.py`**: `LoteCandidato` ganha
   `etag: str`, preenchido em `_candidato(lote, d)` com
   `etag_lote_e_saldo(lote, saldo)` — `lote` e `saldo` já estão em escopo
   ali.

5. **`registry/componentes/movimento_descarte.py`**: mesma coisa em
   `LoteDescartavel`/`_linha`.

6. **`registry/componentes/movimento_estorno.py`**: `Lancamento` ganha
   `etag: str`, preenchido em `_lancamento(mov, todos)` com
   `etag_movimento_estorno(mov, ja_estornado(mov, todos))`.

7. **Cliente — `render/comando.ts`**: `DetalheComando` ganha um campo
   opcional, `etag?: string` — a view inclui o etag da LINHA escolhida
   quando despacha o evento. Sem mudar a assinatura de `View<Id>`: é o
   `detail` do `CustomEvent`, não um prop.

8. **`render/motor.tsx`**: em `aoComando`, o etag da tentativa passa a ser
   `detail.etag ?? api.etagAtual(bloco.tipo, bloco.params)` — linha
   escolhida tem prioridade; sem ela, cai no mecanismo bloc-level que a
   T-050 já construiu (é o caso de `controlado_autorizar`).

9. **Views** `movimento_saida.tsx`, `movimento_descarte.tsx`,
   `movimento_estorno.tsx`: o `dispararComando(...)` de cada uma passa a
   incluir `etag: <candidato escolhido>.etag`. `controlado_autorizar.tsx`
   **não muda** — continua sem etag no evento, como ficou na T-050.
   `quarentena_liberar.tsx`/`lote_status_acao.tsx` também não mudam.

## Arquivos de propriedade exclusiva

```
api/src/estoque/application/etag.py
api/src/estoque/application/registry/definir.py   (etag: str | None — controlado_autorizar tem alvo opcional)
api/src/estoque/application/commands/autorizacao.py
api/src/estoque/application/commands/estorno.py
api/src/estoque/application/commands/saida.py
api/src/estoque/application/commands/descarte.py
api/src/estoque/application/registry/componentes/controlado_autorizar.py
api/src/estoque/application/registry/componentes/movimento_saida.py
api/src/estoque/application/registry/componentes/movimento_descarte.py
api/src/estoque/application/registry/componentes/movimento_estorno.py
api/tests/server/test_t051_etag_por_linha.py

web/src/render/comando.ts
web/src/render/motor.tsx
web/src/views/movimento_saida.tsx
web/src/views/movimento_descarte.tsx
web/src/views/movimento_estorno.tsx
web/src/testes/comando.test.tsx
web/src/testes/movimento_estorno_descarte.test.tsx   (fixtures ganharam o campo `etag`, agora obrigatório)
web/src/generated/componentes.ts   web/src/generated/contrato.json   (gerados, `make types`)

docs/tasks/CONTRATOS.md   (§8.1 — nota de revisão)
```

> `data/porta.py`, `data/repositorios.py`, `tests/registry/fakes.py` — **não
> tocados**. O levantamento anterior que os listava estava errado; ver a
> correção no topo deste arquivo.

## Critérios de aceite

- [x] **AC-1** `controlado_autorizar` devolve `meta.etag` na leitura, igual
      ao padrão da T-050 — testado com o mesmo par leitura→escrita→sucesso e
      o negativo (etag velho → `conflito`). `test_ac1_controlado_autorizar_
      bloc_level_ponta_a_ponta` e o negativo em
      `api/tests/server/test_t051_etag_por_linha.py`.
- [x] **AC-2** `movimento_saida`, `movimento_descarte` e `movimento_estorno`
      devolvem um `etag` por linha do viewmodel (por candidato/lançamento),
      e o valor de cada linha bate com o que a escrita recalcula PARA
      AQUELA linha — `test_ac2_cada_linha_tem_etag_proprio`,
      `test_ac2_ac3_descarte_etag_por_linha`,
      `test_ac2_ac3_estorno_etag_por_linha`.
- [x] **AC-3** Escrever com o etag da linha ESCOLHIDA é aceito nos três;
      escrever com o etag de uma linha diferente devolve `conflito` — os
      mesmos três testes acima cobrem o par positivo/negativo. *(negativo —
      prova que o etag é por linha, não um valor fixo que qualquer escolha
      aceitaria)*
- [x] **AC-4** `View<Id>` continua `(props: { vm }) => JSX.Element` — nenhuma
      das cinco views tocadas ganhou prop novo; `arch-check` e bijeção
      seguem verdes sem alteração (`make check` completo).
- [x] **AC-5** Os quatro fluxos completam de ponta a ponta contra o servidor
      real: `controlado_autorizar` e `movimento_saida` verificados por
      `curl` contra o container Docker reconstruído (login de Helena e de
      Cleide, incluindo o negativo — etag da linha errada devolvendo
      `conflito`); `movimento_descarte` e `movimento_estorno` verificados
      pelo mesmo par positivo/negativo via pytest contra o Postgres real
      (não mock).
- [x] **AC-6** `application.registry` continua sem importar
      `commands.pipeline`/`commands.autorizacao`/`commands.estorno`/
      `commands.saida`/`commands.descarte` — só `application.etag`.
      `lint-imports` (contrato 2) `KEPT`, sem alteração no verificador.

## Armadilhas

**O AC-3 é o que prova que "por linha" não virou "por bloco" por acidente.**
Um jeito errado de implementar seria calcular UM etag para o bloco inteiro
(por exemplo, hash de todos os candidatos juntos) — passaria pelos outros
critérios, porque qualquer mudança no bloco mudaria esse hash único, mas não
provaria que o etag identifica A LINHA. O teste tem que escrever com o etag
de uma linha DIFERENTE da escolhida e ver `conflito`, não só "etag velho".
