# T-050 — Etag na leitura: sem ele, `If-Match` recusa os seis

| | |
|---|---|
| **Onda** | W4 (destrava) |
| **Trilha** | A/C |
| **Tamanho** | **G**, com risco de crescer — ver "o que não está resolvido" |
| **Depende de** | T-049 |
| **Bloqueia** | **T-031**, para `quarentena_liberar` (fechado aqui) — `movimento_saida` e `controlado_autorizar` seguem bloqueados por [T-051](./T-051-etag-multiplo-e-porta.md) |
| **ADRs** | [0002](../adr/0002-plano-render-plano-escrita.md), [0020](../adr/0020-select-no-servidor.md) |
| **Achado de origem** | [A-41](./ACHADOS.md) |

## Por que esta tarefa existe

A T-049 fez o clique chegar ao servidor. Testando contra o servidor **real**
(não mock) — login de Cleide, login de Helena, `curl` direto — apareceu isto:

```
POST /api/comandos/lote_liberar_quarentena  (corpo e cabeçalhos corretos)
→ {"ok": false, "erro": {"codigo": "invalido", "mensagem": "If-Match obrigatorio nesta operacao."}}
```

`recebimento_registrar` (o único sem `etag_de`) grava de verdade. Os outros
seis — `lote_liberar_quarentena`, `lote_status`, `movimento_saida`,
`movimento_estorno`, `movimento_descarte`, `controlado_autorizar` — têm
`etag_de` no lado de execução (`commands/*.py`) e por isso exigem `If-Match`
(CONTRATOS §8). **Nenhuma leitura do sistema devolve etag hoje** —
`GET /api/views/{id}` e `POST /api/componentes/{id}/dados` nunca populam
`meta.etag` — então não há de onde o cliente tirar o valor para mandar de
volta. A T-049 não cobria isso por desenho: o que ela expõe
(`Bloco.comandos`) é `{endpoint, confirm, idempotent}`, metadado que não muda
por instância; etag é **estado**, muda a cada escrita, e só existe depois de
ler a entidade.

## O obstáculo arquitetural, e por que não é um detalhe

`_etag_do_lote`, `_etag_do_movimento`, `_etag_do_original`, `_etag_da_saida`
vivem em `commands/*.py` — módulos que importam SQLAlchemy diretamente. O
contrato 2 do import-linter proíbe `registry → sqlalchemy`, **inclusive por
caminho indireto** (a T-027 já documentou isto ao evitar `registry →
commands.pipeline`). `registry/` não pode importar nenhum desses módulos só
para reaproveitar a fórmula do hash.

A saída é a mesma que `commands/entradas/` já usa para os schemas: **uma
definição, num módulo neutro, que os dois lados importam.**

## O que fazer — o desenho recomendado

1. **`api/src/estoque/application/etag.py`** (novo, sem SQLAlchemy nem
   FastAPI no caminho — só `hashlib`/`json`/tipos de `domain/`):
   - `etag_de_valores(valores: Mapping[str, Any]) -> str` — mover de
     `commands/pipeline.py` para aqui (o pipeline reexporta ou importa daqui;
     não duplicar).
   - Uma função pura por entidade que hoje tem `etag_de` — `etag_lote(lote:
     Lote) -> str` é o caso direto: mesma forma de `_etag_do_lote`
     (`id`, `status`, `validade`, `endereco`), só que recebendo o domínio já
     carregado em vez de buscar com `ctx.conn`.

2. **`commands/lote.py`, `commands/saida.py`**: `_etag_do_lote`/`_etag_da_saida`
   passam a ser `busca o Lote → chama etag_lote(lote)`. Mesmo hash, uma
   definição.

3. **`registry/definir.py`**: `ComponentDef` ganha um quarto campo, ao lado de
   `load`/`select`/`commands`:

   ```python
   etag: Callable[[D], str] | None = None
   ```

   Pura, como `select` — sem I/O, sem relógio. Recebe o MESMO `D` que `load`
   devolveu, antes do `select` descartar o que a tela não precisa.

4. **Os componentes com `commands`**: cada um que tiver `etag_lote` aplicável
   (`quarentena_liberar`, `lote_status_acao`, `movimento_saida`) ganha
   `etag=lambda d: etag_lote(d.lote)` — ou o nome do campo que o `D` de cada
   um já carrega.

5. **`server/rotas/dados.py`**: depois do `load()`, se `ComponentDef.etag`
   existe, calcula e inclui em `meta.etag` da resposta — o mesmo campo que
   `comandos.py` já preenche do lado da escrita (`CONTRATOS §8`).

6. **Cliente**: `api.dados` descarta `meta` hoje (só devolve `corpo.dados`).
   Alguma forma de a chamada de escrita (`render/comando.ts`/`motor.tsx`)
   saber o etag mais recente do MESMO bloco antes de montar o `If-Match`.
   **Não redesenhe a paginação para isso** — uma alternativa mais barata é um
   mapa `{queryKey → etag mais recente}` atualizado a cada resposta de
   `/dados` que trouxer `meta.etag`, lido por `enviar()` no momento do POST.

## O que foi entregue, e o que a execução cortou

Levantamento feito ANTES de escrever (como esta seção já pedia): os seis
comandos **não têm o mesmo formato de etag**, e forçar todos na mesma
tarefa teria sido o corte errado.

- **`quarentena_liberar` e `lote_status_acao`** — os dois cujo `_etag_do_lote`
  é só sobre o `Lote` (`id`, `status`, `validade`, `endereco`), e cujo `D` do
  `load()` já carrega o `Lote` inteiro (`d.lote`), sem consulta extra. **Os
  dois fecharam nesta tarefa.**
- **`movimento_saida`** — `_etag_da_saida` soma **`saldo`** ao dict (uma
  consulta assíncrona extra, `_saldo(lote.id, ctx)`), E o `lote_id` do etag
  não vem de `params` como nos outros dois: vem de qual candidato (`proposta`
  ou uma das `alternativas`) a PESSOA escolhe na tela, depois da leitura. Um
  etag por bloco não serve — precisa de um etag por LINHA candidata no
  viewmodel, formato que `ComponentDef.etag: Callable[[D], str]` (um só,
  fixo) não cobre. **Cortado para [T-051](./T-051-etag-multiplo-e-porta.md).**
- **`controlado_autorizar` e `movimento_estorno`** — `_etag_do_movimento`
  (`commands/autorizacao.py`) e `_etag_do_original` (`commands/estorno.py`)
  não usam `RepoMovimento`: fazem `sa.select()` direto, lendo colunas
  (`autorizador_id`, o flag de já-estornado) que **nenhum método da porta
  expõe hoje**. Precisam de método novo em `data/porta.py` — tarefa de
  contrato dentro da próxima. **Cortado para T-051.**
- **`movimento_descarte`** — não conferido; T-051 começa por ele antes de
  estimar o resto.

T-031 usa `quarentena_liberar` na rota `/quarentena/:loteId` — **essa rota já
está destrancada.** `/saida` e `/controlados` continuam esperando a T-051.

## Arquivos de propriedade exclusiva

```
api/src/estoque/application/etag.py                (novo)
api/src/estoque/application/commands/lote.py
api/src/estoque/application/commands/pipeline.py    (só a remoção/reexport)
api/src/estoque/application/registry/definir.py
api/src/estoque/application/registry/componentes/quarentena_liberar.py
api/src/estoque/application/registry/componentes/lote_status_acao.py
api/src/estoque/server/rotas/dados.py
api/tests/server/test_t050_etag_na_leitura.py

web/src/api.ts
web/src/render/motor.tsx
web/src/testes/etag.test.ts
web/src/testes/comando.test.tsx   (T-049, ajustado ao 4º argumento de api.comando)

docs/tasks/CONTRATOS.md   (§8.1 — nota de revisão)
```

> `commands/saida.py`, `commands/autorizacao.py`, `commands/estorno.py`,
> `commands/descarte.py`, `data/porta.py` (novo método de `RepoMovimento`) e
> `render/comando.ts` **não foram tocados** — ficam para a
> [T-051](./T-051-etag-multiplo-e-porta.md), que os declara.

## Critérios de aceite

- [x] **AC-1** `POST /api/componentes/{id}/dados` devolve `meta.etag` para
      `quarentena_liberar` e `lote_status_acao`, e o valor bate com o que
      `_etag_do_lote` calcula no momento da escrita — testado com o MESMO
      lote, lido e depois escrito, sem passo manual no meio
      (`test_ac1_leitura_devolve_etag_para_os_dois_componentes`). **Em branco
      para `movimento_saida`, `controlado_autorizar`, `movimento_estorno`,
      `movimento_descarte`** — cortados para T-051, ver acima.
- [x] **AC-2** O etag muda quando o estado subjacente muda (liberar um lote
      muda o etag de uma leitura seguinte) e permanece igual quando nada
      mudou (`test_ac2_etag_estavel_sem_escrita_e_muda_depois_dela`).
- [x] **AC-3** Escrever com um etag **desatualizado** (lido antes de outra
      pessoa mudar o lote) devolve `conflito`, e nada é aplicado —
      `test_ac3_etag_desatualizado_e_recusado_e_nada_e_aplicado`: uma segunda
      escrita com o etag velho recusa, e o `SELECT status FROM lote` depois
      confirma que o estado da primeira escrita não foi tocado. *(negativo)*
- [x] **AC-4** O fluxo de `quarentena_liberar` completa de ponta a ponta
      contra o servidor real, no container Docker reconstruído (não só
      pytest): login de Helena por `curl`, leitura devolvendo etag, escrita
      com `If-Match` aceita (`status: liberado`) — e uma segunda tentativa com
      o etag já usado devolve `conflito`. É o mesmo `curl` que a T-049
      registrou como falha; agora completa.
- [x] **AC-5** `application.registry` continua sem importar
      `commands.pipeline` nem `commands.lote` — só `application.etag`.
      `lint-imports` (contrato 2) segue `KEPT` sem alteração no verificador.
- [x] **AC-6** `etag_de_valores` existe só em `application/etag.py`;
      `commands/pipeline.py` importa de lá, sem segunda cópia da fórmula.

## Armadilhas

**O hash tem que ser byte a byte igual nos dois lados**, ou todo `If-Match`
fica sempre errado — a leitura calcularia um etag que a escrita nunca
reproduz, e cada tentativa cairia em `conflito` mesmo sem concorrência
nenhuma. Isto não se pega olhando o código: só um teste que lê, escreve com o
etag lido, e espera sucesso pega a divergência. É o AC-4.

**Não escreva a fórmula duas vezes "só para não importar o módulo errado".**
É exatamente o achado A-11 de novo — fake e real, ou aqui, leitura e escrita,
divergindo em silêncio até uma auditoria achar.
