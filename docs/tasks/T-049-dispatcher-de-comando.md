# T-049 — Dispatcher de comando no cliente: o clique aprende a chegar ao servidor

| | |
|---|---|
| **Onda** | W4 (destrava) |
| **Trilha** | B/D |
| **Tamanho** | **G** |
| **Tipo** | **Tarefa de contrato** — altera `CONTRATOS §6` e `§8` |
| **Depende de** | T-011, T-025, T-026, T-027, T-028, T-029, T-030 (todas ✅) |
| **Bloqueia** | **T-031** |
| **ADRs** | [0002](../adr/0002-plano-render-plano-escrita.md), [0004](../adr/0004-autorizacao-em-tres-momentos.md), [0005](../adr/0005-l2-leitura-l1-escrita.md), [0028](../adr/0028-processo-de-decisao.md) |
| **Requisitos** | RF-15 |
| **Achado de origem** | [A-40](./ACHADOS.md) |

## Por que esta tarefa existe

Lida a T-031 (telas com rota), abrindo o editor: as oito rotas incluem quatro
operações de escrita (`recebimento_registrar`, `quarentena_liberar`,
`movimento_saida`, `controlado_autorizar`). Antes de desenhar rota alguma,
conferi se elas funcionam hoje pelo caminho que já existe — o assistente.

**Não funcionam. Em nenhuma das duas superfícies.**

```
grep -rn "onClick" web/src/views/{recebimento_registrar,quarentena_liberar,
  lote_status_acao,movimento_saida,movimento_estorno,movimento_descarte,
  controlado_autorizar}.tsx
```

Zero resultado, nos sete componentes de escrita do ciclo 1. Todo botão de ação
é `type="button"` com `disabled` calculado — e mais nada. `data-acao` e
`data-decisao` existem em três deles, lidos por ninguém. Também não há, em lugar
nenhum do cliente, `useMutation`, `Idempotency-Key`, `If-Match`, nem uma
chamada a `/api/comandos/`. Confirmado por busca no código, não por inferência.

T-025 descrevia a confirmação como *"decisão do motor de render, disparada por
`CommandDef.confirm`"* — essa peça nunca foi escrita. As cinco tarefas de escrita
(T-026 a T-030) entregaram, do lado cliente, **só a view** — a lista de arquivos
de propriedade delas dizia isso literalmente ("apenas o React que recebe o
viewmodel"). Ninguém cortou a tarefa que liga o clique ao servidor. É esta.

**Por que é tarefa de contrato e não ADR.** [CONTRATOS §11](./CONTRATOS.md)
classifica: campo novo, opcional, sem quebrar assinatura existente, sem
alternativa em disputa — a alternativa (deixar os botões inertes) já foi
rejeitada pela própria T-031 tentar existir. ADR é para decisão com alternativas
vivas; aqui a única pergunta real (como o `Bloco` carrega os dados do
`CommandDef`; como a view avisa alguém sem ganhar prop novo) já foi decidida com
o cliente, registrada abaixo.

## As duas decisões já tomadas — não redecidir

1. **`Bloco` ganha um campo novo, opcional: `comandos`.** Populado a partir de
   `ComponentDef.commands` só quando o componente declara `commands`; ausente
   (não `{}`) nos 15 componentes de leitura. Forma:

   ```ts
   comandos?: Record<string, { endpoint: string; confirm: boolean; idempotent: boolean }>
   ```

   Sem o `schema` do `CommandDef` — a view já monta o corpo a partir do próprio
   estado local, e o servidor revalida de qualquer forma (`RN-A03`, AC-2 da
   T-025). Mandar o schema seria mandar dado que ninguém lê.

2. **A view não ganha prop novo.** `View<Id> = (props: { vm }) => JSX.Element`
   continua **exatamente assim** — é o que `web/CLAUDE.md` chama de "só isso", e
   as cinco views de T-026 a T-030 não são reabertas para receber parâmetro.
   Em vez disso, a view despacha um `CustomEvent`:

   ```ts
   el.dispatchEvent(new CustomEvent('comando', {
     bubbles: true,
     detail: { acao: 'liberar', corpo: { ...campos do estado local } },
   }))
   ```

   e um wrapper em `render/motor.tsx` — o mesmo módulo que já envolve toda view
   lida para injetar `vm` — escuta esse evento no contêiner e executa o POST.
   Simétrico ao que `BlocoRender` já faz para leitura: a view não sabe que existe
   rede, só que existe um evento. O acoplamento é por nome do evento e forma do
   `detail`, verificável em teste unitário de cada view (dispara o clique,
   afirma o evento).

## Arquivos de propriedade exclusiva

```
api/src/estoque/server/deps.py            (+1 função: comandos(tipo))
api/src/estoque/server/rotas/views.py     (bloco de resposta ganha "comandos")
api/src/estoque/server/rotas/assistente.py (idem)
api/tests/server/test_t049_comandos_no_bloco.py

web/src/render/comando.ts                 (novo — o wrapper e o tipo do evento)
web/src/render/motor.tsx                  (BlocoRender escuta 'comando')
web/src/api.ts                            (+1 método: api.comando)
web/src/views/recebimento_registrar.tsx   (+onClick, sem novo import)
web/src/views/quarentena_liberar.tsx      (idem)
web/src/views/lote_status_acao.tsx        (idem)
web/src/views/movimento_saida.tsx         (idem)
web/src/views/movimento_estorno.tsx       (idem)
web/src/views/movimento_descarte.tsx      (idem)
web/src/views/controlado_autorizar.tsx    (idem)
web/src/testes/comando.test.tsx           (novo)

docs/tasks/CONTRATOS.md                   (§6 Bloco, §8 — nota de revisão)
web/CLAUDE.md                             (uma linha: o CustomEvent é o canal)
```

> **Toca `render/motor.tsx`, arquivo de propriedade da T-015 (fechada).** É o
> mesmo padrão de T-048/A-37: a alteração mora onde o contrato que ela estende
> já vive. `web/CLAUDE.md` continua valendo tal como está — nenhuma frase de lá
> muda, só se acrescenta a nota do canal de evento.

## Escopo

### Faz

- `server/deps.py`: `comandos(tipo: str) -> dict[str, dict] | None`, espelho de
  `tamanho()` — lê `ComponentDef.commands` do catálogo e serializa
  `{endpoint, confirm, idempotent}` por nome de comando; `None` quando o
  componente não declara `commands`.
- `server/rotas/views.py` e `server/rotas/assistente.py`: o dict de bloco de
  resposta ganha `"comandos": comandos(b.tipo)` quando não for `None` — as duas
  rotas que hoje montam `{"tipo", "params", "tamanho"}`.
- `web/src/api.ts`: `api.comando(endpoint, corpo, opts)` — reaproveita `chamar()`
  (CSRF já incluso ali para método não-GET); gera `Idempotency-Key` com
  `crypto.randomUUID()` por invocação; inclui `If-Match` quando `opts.etag`
  vier preenchido.
- `web/src/render/comando.ts`: o tipo do evento (`DetalheComando`), e a função
  que o wrapper chama ao capturá-lo — confirma (dois passos, sem
  `window.confirm`: um clique arma, o segundo confirma ou expira), chama
  `api.comando`, e devolve o resultado para invalidar a query de leitura do
  mesmo bloco (o saldo/status que a tela mostra precisa recarregar depois de
  escrever).
- `render/motor.tsx`: o contêiner de cada `BlocoRender` ganha
  `onComandoCapture` (ou `addEventListener` no ref) para o evento `comando`.
- As sete views: um `onClick` por botão de ação, despachando o evento com o
  `acao` e o `corpo` já calculado do estado local que a view já tem — nenhuma
  optou por buscar dado nem importar `api`/`query`.

### Não faz

- Rotas com URL — é a T-031, que só volta a valer depois desta.
- Componente novo no catálogo, ou mudança de `requires`/regra de negócio de
  qualquer um dos sete comandos existentes.
- Tela de confirmação genérica bonita — o AC-2 pede só que um clique não baste;
  a UI dos dois passos pode ser mínima.

## Critérios de aceite

- [~] **AC-1** Clicar no botão de ação de cada um dos sete componentes de
      escrita produz **uma** chamada a `POST /api/comandos/{endpoint}` com o
      corpo esperado — espionando `fetch`, não inspecionando estado interno.
      **Metade verificada.** A chamada em si — endpoint, corpo, cabeçalhos — foi
      testada com mock (4 testes em `web/src/testes/comando.test.tsx`) e depois
      confirmada contra o **servidor real** com `curl` autenticado como Cleide e
      Helena. `recebimento_registrar` completa o ciclo e grava (resposta
      `ok: true`, lote criado). Os outros seis devolvem `invalido: "If-Match
      obrigatorio"` — a chamada chega certa, mas nenhuma leitura hoje devolve
      etag para preencher o cabeçalho. Achado [A-41](./ACHADOS.md), tarefa
      [T-050](./T-050-etag-na-leitura.md). Fica em branco a metade que depende
      dela.
- [x] **AC-2** Comando com `confirm: true` não dispara no primeiro clique — exige
      um segundo passo explícito. *(negativo — o critério central: um clique só
      nunca escreve)*
- [x] **AC-3** Toda chamada de `api.comando` leva `Idempotency-Key` distinta por
      invocação e `X-CSRF-Token` do mesmo mecanismo que `api.dados` já usa.
- [x] **AC-4** Erro do servidor (`conflito`, `nao_autorizado`, `recusado`) chega
      à tela sem aplicar nada de otimista: o estado anterior ao clique continua
      visível, com a mensagem do servidor. *(negativo)*
- [x] **AC-5** `Bloco` ganha `comandos` só quando o componente declara
      `commands`; os 15 componentes de leitura continuam **sem** o campo
      (ausente, não vazio) — testado nas duas rotas que montam blocos
      (`/api/views/{id}` e `/api/assistente/compor`).
- [x] **AC-6** `application.assistant` continua sem alcançar
      `application.commands` — o teste de import do contrato 3 (T-025 AC-1)
      segue passando sem alteração. *(negativo — esta tarefa não pode abrir um
      segundo caminho de escrita)*
- [x] **AC-7** `View<Id>` continua `(props: { vm }) => JSX.Element` — nenhuma das
      sete views ganhou prop novo. `arch-check` de `views/` (sem `useEffect`,
      sem import de `query`/`api`) e o teste de bijeção continuam verdes sem
      alteração.
- [x] **AC-8** Repetir o clique de confirmação com a MESMA `Idempotency-Key` (uma
      segunda tentativa depois de um erro de rede, antes de qualquer nova
      composição) produz um efeito só — testado no cliente (a mesma chave nas
      duas chamadas de `api.comando`); o replay em si — **um** efeito, mesma
      resposta — já está provado no servidor pela T-025 AC-3, não refeito aqui.

## Definição de pronto — adicional

- [x] Contagem de catálogo no BOARD: **+0** — nenhum componente novo.
- [x] `docs/tasks/CONTRATOS.md` com a revisão do `Bloco` (§6) e a nota em §8.

## Armadilhas

**AC-6 é o que impede esta tarefa de desfazer a T-025.** Um jeito errado de
implementar seria o wrapper do cliente chamar algo que, no servidor, tivesse
caminho de `assistant` até `commands` — não existe esse caminho hoje (o
contrato 3 do import-linter proíbe), e esta tarefa só adiciona metadado ao
`Bloco` e um `POST` autenticado à mesma rota `/api/comandos/{nome}` que já
existe. Nada aqui muda quem pode escrever — só faz o botão parar de estar morto.

**O evento `comando`, não um callback.** A tentação de "só acrescentar um prop"
é grande porque é mais direto — e é exatamente a alternativa que o cliente já
rejeitou (reabriria as cinco views fechadas e quebraria a frase literal do
`web/CLAUDE.md`). Se a implementação achar o `CustomEvent` insuficiente no
meio do caminho, **pare e sinalize** em vez de trocar por callback sem
registrar — foi decisão explícita, não default.

## O que a execução encontrou — registro

Os testes automatizados (mock de `api.comando`) passaram os oito ACs. Antes de
fechar, o servidor **real** foi chamado por HTTP — login de Cleide e de Helena,
`curl` contra o container do Docker Compose, não contra um duble. Foi assim que
apareceu o que o mock não podia mostrar: `recebimento_registrar` grava de
verdade; os outros seis (todos com `etag_de` no lado de execução) recusam com
`If-Match obrigatorio`, porque nenhuma leitura devolve etag. **Isso não é uma
falha desta tarefa** — o dispatcher chama o endpoint certo, com o corpo certo,
os cabeçalhos certos; é a T-025 recusando corretamente uma escrita sem
concorrência controlada. É uma peça que faltava e que a T-049, por desenho, não
cobria (endpoint/confirm/idempotent, nunca etag). Achado
[A-41](./ACHADOS.md), tarefa [T-050](./T-050-etag-na-leitura.md), que passa a
bloquear a T-031 para `quarentena_liberar`, `movimento_saida` e
`controlado_autorizar`.
