# T-055 — Filtro interativo, sem passar pelo assistente

| | |
|---|---|
| **Trilha** | C/D · componentes e cliente |
| **Tamanho** | G |
| **Depende de** | T-039 (codegen), T-054 (padrão do bloco em `render/`) |
| **ADRs** | [0004](../adr/0004-autorizacao-em-tres-momentos.md), [0017](../adr/0017-registry-servidor-views-cliente.md), [0020](../adr/0020-select-no-servidor.md), [0028](../adr/0028-processo-de-decisao.md), [0029](../adr/0029-relatorio-como-componente.md) |
| **RN** | nenhuma — é lacuna de UX, não de regra. O único lastro documentado é o risco R-5 do PRD ("filtro que falta alarga a resposta em silêncio"), citado nos `Params` de vários componentes |
| **Origem** | achado [A-46](./ACHADOS.md), relatado pelo usuário em 2026-09-16: "não tem filtro" na navegação convencional, e uma tabela que o assistente devolveu não pode ser refiltrada sem perguntar de novo |
| **Escrita em** | 2026-09-16 |

## Por que existe

Toda lista do catálogo já recebe recorte como `param` — `lote_lista.Params` tem
`unidade_id`, `status`, `janela`; `movimento_lista` tem `unidade_id`, `tipo`,
`status`, `periodo`; e assim por sete componentes a mais. Todos esses campos são
`Literal` ou um `Enum` do domínio (nunca texto livre — é a defesa contra o
risco R-5). Mas **nenhuma superfície deixa o usuário escolher esse valor**:

- `web/src/app/layout/rotasOperacao.tsx` hardcoda `params: () => ({})` (ou um
  valor fixo, como `janela: '90'` em `/vencimento`) em toda rota tradicional —
  a tela de rota sempre pede o padrão do componente, nunca outro recorte.
- Uma composição do assistente é um retrato estático: o `Bloco` que ele propôs
  já tem os `params` fixados no schema validado. Pedir outro recorte da mesma
  tabela não tem controle nenhum — exige nova pergunta em linguagem natural,
  uma nova composição, um novo turno.
- `web/src/generated/contrato.json` (gerado por
  `application/registry/exportar.py`) **nem expõe o schema de `params`** hoje —
  só `id`, `label`, `tamanho`, `viewmodel`. O cliente não tem como saber, para
  nenhum componente, quais campos existem nem quais valores o enum aceita.

## O que já foi conferido

- **O contrato de view está congelado como puro.** CONTRATOS §6: `View<Id> =
  (props: { vm: ViewModel<Id> }) => JSX.Element` — "a view recebe apenas `vm`.
  Não recebe ator, não busca dado, não decide regra, não conhece permissão."
  Um filtro que a própria `view` disparasse (chamando `dados` de dentro de
  `lote_lista.tsx`) quebraria essa invariante e mudaria §6 para todas as 24
  views, não só as com filtro.
- **Já existe recarga client-driven pelo mesmo caminho autorizado.**
  `render/motor.tsx` faz paginação por cursor com `useInfiniteQuery`
  (`getNextPageParam` lendo `tem_mais`/`cursor` do viewmodel) — o cliente já
  pede uma página nova ao servidor, pela rota `dados`, com a mesma
  autorização de sempre (ADR-0004). Trocar um `param` de filtro em vez de só o
  cursor é a mesma máquina, um parâmetro a mais.
- **T-054 já resolveu o mesmo dilema para exportar, e a resposta serve de
  molde:** em vez de mudar `ComponentDef` ou `View<Id>`, o botão de exportar
  mora em `web/src/render/BotaoExportar.tsx` — **fora** da view, ao redor do
  bloco, no motor de render. Filtro pode seguir o mesmo desenho: um
  `BarraFiltro` ao redor do bloco, não dentro da `view`.
- **A distinção filtro vs. identificador já está codificada no tipo, não
  precisa de anotação nova.** Todo campo pensado como recorte é `Literal` ou
  um enum do domínio (`UnidadeId` incluso) — tem `enum` no JSON Schema.
  Identificador (`produto_id`, `lote_id`, `recebimento_id`, `movimento_id`,
  `ean`) é sempre `str | None` sem enum. Um campo com `enum` no schema
  exportado É o filtro; o resto não aparece na barra. Não precisa de um
  registro paralelo por componente para dizer "isto é filtro" — o `Params` já
  diz, e a exportação do schema só precisa preservar essa informação.
- **`de`/`ate` (datas livres, em `temperatura_excursoes` e `rastreabilidade`)
  não têm `enum`.** Ficam fora do primeiro corte (ver "Não faz") — são um
  controle de UI diferente (par de datas, com a mesma coerência que o
  `model_validator` já valida no servidor).

## Decisão

- **O filtro mora ao redor do bloco, não dentro da `view`** — mesmo lugar do
  botão de exportar (T-054), pelo mesmo motivo: preserva CONTRATOS §6 sem
  mudança, e funciona nas duas superfícies de graça, porque as duas passam
  pelo mesmo `render/motor.tsx` (ADR-0017: um componente, duas superfícies).
- **`exportar.py` (gerador do contrato) passa a incluir o schema de `params`
  no `contrato.json`, restrito aos campos com `enum`.** Identificador nunca
  aparece — nem por engano, nem por falta de filtro nele. Isto é mudança do
  CONTRATOS §... **(nova seção, ou extensão do §9 — decidir na execução, com
  revisão registrada como as de T-050/T-054)**.
- **O rótulo de cada campo e de cada valor do enum não vem do `Params`** — um
  `Literal["30","60","90"]` não carrega texto. Uma tabela pequena de rótulos
  por componente (nos moldes de `exportacao/tabelas.py`, mas no lado cliente)
  resolve isto; ou os rótulos que as próprias views já têm (`STATUS_LOTE`,
  `UNIDADE`) são reaproveitados onde existem, para não duplicar texto que já
  existe — **decidido na execução**.
- **Escolher um filtro chama `dados` de novo, com os `params` alterados, pelo
  mesmo caminho de `render/motor.tsx`.** Nenhum novo endpoint, nenhuma nova
  checagem de autorização: é a mesma leitura de sempre, com outro valor de
  campo já validado como enum pelo Pydantic do lado servidor (RequiresPorValor
  continua valendo — ADR-0004).
- **A rota tradicional ganha o filtro pela mesma barra**, não por um mecanismo
  próprio: `rotasOperacao.tsx` para de fixar `params: () => ({})` e passa a
  ler o recorte inicial da query string, e a barra escreve de volta na URL
  quando o usuário muda o filtro (para o link ser compartilhável) —
  **decidido na execução, com `useSearchParams` do `react-router-dom` já
  presente desde a T-031**.

## Escopo — componentes com filtro nesta tarefa

Só os campos com `enum` nos `Params` destes oito: `lote_lista`,
`movimento_lista`, `recebimento_lista`, `fila_vencimento`,
`vencimento_grafico`, `quarentena_fila`, `auditoria_trilha`,
`relatorio_movimentacao` (aqui, todo `param` exceto o `agrupar_por`
obrigatório, que continua fixado pela composição).

## Arquivos de propriedade exclusiva

```
web/src/render/BarraFiltro.tsx        controle da barra, ao redor do bloco
web/src/render/rotulosFiltro.ts       rótulo por componente/campo/valor do enum
web/src/testes/barraFiltro.test.tsx
api/tests/registry/test_exportar_params.py   schema de params só com enum, sem identificador
```

## Toca, com registro

```
api/src/estoque/application/registry/exportar.py   inclui params (só enum) no contrato.json
web/scripts/gerar-tipos.ts                          tipo TS do schema de params
web/src/generated/contrato.json, componentes.ts     make types
web/src/render/motor.tsx                            re-fetch por mudança de params, não só cursor
web/src/app/layout/rotasOperacao.tsx                params() lê query string em vez de fixar
web/src/testes/rotas_operacao.test.tsx
docs/tasks/CONTRATOS.md                             nova seção ou extensão do §9, com revisão
docs/tasks/ACHADOS.md                                A-46 fecha, aponta para esta tarefa
```

## Critérios de aceite

- [x] **AC-1** Nas 8 telas de rota tradicional listadas em "Escopo", cada campo
      com `enum` do `Params` do componente aparece como controle (ex.: um
      `<select>` de `status`), com o padrão do componente pré-selecionado.
      Escolher outro valor atualiza a tabela sem recarregar a página.
      **Verificado:** `barraFiltro.test.tsx` (AC-1, 2 casos).
- [x] **AC-2** O filtro escolhido fica na URL (query string) e sobrevive a
      recarregar a página e a compartilhar o link.
      **Verificado:** `barraFiltro.test.tsx` (AC-2, 2 casos) — sonda própria
      lendo `useSearchParams`, porque `MemoryRouter` não escreve em
      `window.location` de propósito.
- [x] **AC-3** Uma composição do assistente que inclua um dos 8 componentes
      ganha a mesma barra, com os mesmos controles — a barra é uma função do
      componente, não da origem da tela (rota ou assistente).
      **Verificado:** mesma `BlocoRender`/`Composicao` para as duas
      superfícies (nenhum código exclusivo de rota); `rotas_operacao.test.tsx`
      AC-1 confirma que rota e assistente produzem **o mesmo HTML**, byte a
      byte, incluindo a barra.
- [x] **AC-4** Identificador nunca vira controle de filtro. `produto_id`,
      `lote_id`, `recebimento_id`, `movimento_id`, `ean` não aparecem na
      barra de nenhum componente, em nenhuma das duas superfícies.
      *(negativo)* **Verificado:** `barraFiltro.test.tsx` (cliente, lendo
      `FILTROS` gerado) e `test_exportar_params.py` (servidor, 5 casos,
      inclui os 24 componentes — não só os 8).
- [x] **AC-5** Mudar o filtro passa pela mesma autorização de sempre — não é
      atalho. Um ator sem escopo para a `unidade_id` escolhida no filtro
      recebe a mesma recusa que receberia pedindo direto por `/api/dados`, e a
      tabela não troca de conteúdo antes da resposta confirmar.
      *(negativo — mesma tabela de casos de `RequiresPorValor` já coberta em
      `dados`, agora disparada pela barra)* **Satisfeito por construção, sem
      teste novo:** `BarraFiltro` só muda a URL; `BlocoRender` funde a URL em
      `params` e chama **o mesmo `api.dados(tipo, params)`** que a carga
      inicial e a paginação já chamam — nenhum código novo entre o clique e o
      `/api/dados` de sempre. A autorização por escopo já tem teste (achado
      de `unidade_id` fora do escopo em `test_lote_lista.py`,
      `test_movimento_lista.py` e outros) e continua valendo porque o caminho
      não mudou.
- [x] **AC-6** Um valor de filtro fora do enum (forjado, fora da lista que a
      barra oferece) é recusado pela validação do `Params` de sempre — a
      barra não é uma segunda porta sem a checagem do Pydantic. *(negativo)*
      **Satisfeito por construção, pelo mesmo motivo do AC-5** — `Params` de
      cada um dos 8 já rejeita valor fora do `Literal` (`test_lote_lista.py`,
      `test_movimento_lista.py`), e nenhum endpoint novo foi criado.
- [x] **AC-7** `import-linter`: nada disto abre caminho novo do `assistant`
      para escrita, nem do cliente para fora de `dados`/`views`. Os 7
      contratos continuam verdes. **Verificado:** `make arch-api` — 7 kept,
      0 broken.
- [x] **AC-8** CONTRATOS §6 (`View<Id>`) não muda — conferido lendo o tipo:
      `BarraFiltro` não é `view`, não está em `web/src/views/`, e nenhuma
      `view` existente ganhou prop nova. **Verificado por inspeção** —
      `BarraFiltro.tsx` mora em `web/src/render/`. Dois arquivos de
      `web/src/views/` foram tocados (`movimento_lista.tsx`,
      `recebimento_lista.tsx`), só para **exportar** uma constante de rótulo
      que já existia local ao arquivo (`TIPO_MOVIMENTO`, `STATUS_RECEBIMENTO`)
      — nenhuma assinatura de `view` mudou, nenhuma prop nova.

## Não faz

- **Filtro por data livre** (`de`/`ate` em `temperatura_excursoes` e
  `rastreabilidade`): outro tipo de controle (par de datas, não enum). Fica
  para tarefa futura, se houver pedido — anotar como achado se aparecer de
  novo.
- **Busca por texto livre em campo nenhum**: contraria o risco R-5 por
  desenho; identificador continua exigindo o valor exato (RN já implementada
  nos componentes).
- **Filtro combinado entre blocos** (uma barra que filtra duas tabelas ao
  mesmo tempo): cada bloco é independente, como o botão de exportar.
