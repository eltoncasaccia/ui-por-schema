# ui-por-schema — interface composta por IA, sem gerar código

Sistema de controle de estoque farmacêutico onde **um modelo compõe a interface em
tempo real** — escolhendo entre componentes registrados, nunca escrevendo código,
nunca tocando dados, nunca autorizando escrita.

> ⚠️ **A Bertoni Distribuidora Farmacêutica é uma empresa fictícia.** Todos os
> dados são gerados. O caso existe para dar restrições reais — regulação sanitária,
> separação de funções, rastreabilidade de lote — a um problema de arquitetura.

## Início rápido

```bash
git clone https://github.com/eltoncasaccia/ui-por-schema.git && cd ui-por-schema
docker compose up
```

`http://localhost:5173` · entre como **Cleide (conferente)** ou **Helena (RT)** e
compare o que cada uma consegue ver e fazer.

---

## A tese

Existem dois jeitos de uma IA montar interface:

| | Como funciona | Problema |
|---|---|---|
| **Gerar código** | o modelo emite JSX e o navegador executa | roda em sandbox isolada, **sem acesso a dados**. Nem quem gera confia no que gerou |
| **Compor** ← *este projeto* | o modelo emite **nomes de componentes registrados e parâmetros** | limitado ao catálogo — e é justamente isso que o torna seguro |

```jsonc
// tudo que o modelo produz: ~60 tokens
{ "versao": 1, "blocos": [
    { "tipo": "fila_vencimento", "params": { "janela": 90 } },
    { "tipo": "estoque_indicador", "params": { "metrica": "lotes_em_quarentena" } }
]}
```

O schema **não tem onde carregar código**: não existe campo para markup, estilo,
valor literal ou expressão. Isso é propriedade da estrutura de dados, não promessa
de prompt.

### As três regras que sustentam o desenho

1. **O modelo escolhe a composição. Nunca o código, nunca os dados, nunca a
   autorização.**
2. **A saída do modelo autoriza renderizar. Nunca autoriza escrever.** Quem grava é
   a pessoa que clica em salvar, pelo mesmo endpoint autenticado da tela comum.
3. **Autorização em três momentos, e só o terceiro protege** — o que roda em cada
   carga e cada comando, com a identidade real. Os outros dois controlam o que é
   *oferecido*; só este controla o que é *acessível*.

---

## Arquitetura

```
┌────────────┐   HTTP/JSON    ┌──────────────────┐   SQL   ┌──────────┐
│  web       │ ─────────────▶ │  api             │ ──────▶ │ postgres │
│  React/TS  │ ◀───────────── │  Python/FastAPI  │         │          │
│  só views  │   viewmodels   │  domínio         │         └──────────┘
└────────────┘                │  registry        │
                              │  autorização     │
                              └──────────────────┘
```

A separação é **fronteira de processo**, não convenção: é fisicamente impossível o
código de acesso a dados chegar ao navegador. O cliente recebe *viewmodels* — nunca
modelos de domínio, nunca linhas de banco.

| | |
|---|---|
| **api** | Python 3.13 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 · Alembic · `mypy --strict` |
| **web** | React 18 · Vite · TypeScript estrito · TanStack Query + Router · CSS Modules |
| **banco** | Postgres 17 — imutabilidade de movimento e auditoria aplicada por `REVOKE`, não por comentário |
| **modelo** | trocável por configuração, sem mudar código — ver abaixo |

### Modelo é configuração, não código

Provedor e modelo trocam no `.env`, sem tocar em código
([ADR-0025](./docs/adr/0025-agnosticismo-de-provedor.md)):

```bash
PROVEDOR=openrouter                            # roteador multi-modelo
MODELO_ASSISTENTE=anthropic/claude-haiku-4.5
MODO_DECODIFICACAO=restrito                    # restrito | ferramenta | livre
```

Funciona também com um modelo **local** via Ollama (`PROVEDOR=compativel` +
`LLM_BASE_URL`) — o modelo recebe só a pergunta e o catálogo, nunca os dados
([ADR-0012](./docs/adr/0012-injecao-de-prompt-via-dado.md)), então trocar de
provedor não muda o que sai daqui. `make modelo` mostra o que está em uso.

---

## Documentação

Este repositório é tanto o sistema quanto o registro de como ele foi decidido.

| Quero... | Vá para |
|---|---|
| entender o requisito por trás de uma tela | [PRD-001](./docs/prd/PRD-001-ciclo-1.md) |
| entender por que uma decisão técnica é assim | [22 ADRs](./docs/adr/) |
| ver interfaces congeladas entre tarefas | [Contratos](./docs/tasks/CONTRATOS.md) |
| ver o estado real do projeto | [BOARD](./docs/tasks/BOARD.md) · [PROGRESSO](./docs/tasks/PROGRESSO.md) |
| **rodar os testes** | [`CLAUDE.md` §4](./CLAUDE.md#4-o-ciclo-de-verificação) — `make check`, `make e2e`, o que cada verificador cobre |
| entender o ambiente (Docker, dois bancos, armadilhas) | [`docs/AMBIENTE.md`](./docs/AMBIENTE.md) |
| ver o que uma auditoria já encontrou de errado | [`docs/relatorios/`](./docs/relatorios/) |

**Por onde começar a ler:** [ADR-0002](./docs/adr/0002-plano-render-plano-escrita.md)
(a regra central) e a [auditoria A-001](./docs/relatorios/A-001-auditoria-pre-migracao.md)
— que achou uma falha de confidencialidade nos próprios documentos, corrigida no
[ADR-0020](./docs/adr/0020-select-no-servidor.md).

---

## O que este projeto não faz

Declarado de propósito — [ADR-0010](./docs/adr/0010-corte-de-escopo-ciclo-1.md) e
[ADR-0015](./docs/adr/0015-assistente-exige-conexao.md):

contagem de inventário · ajuste de saldo · transferência entre unidades · operação
off-line · nota fiscal e financeiro (permanecem no ERP)

---

## Comandos

```bash
make up          # sobe tudo: db + api + web (docker compose)
make down        # derruba os serviços
make reset       # derruba e APAGA os dados
make check       # lint + typecheck + test + arch — é o que o CI roda
```

Desenvolver contra o banco local, gerar tipos a partir do registry, entender os
arquivos gerados que ninguém edita à mão, ou destravar um processo preso: tudo em
[`CLAUDE.md` §3–4](./CLAUDE.md#3-subir-derrubar-e-a-armadilha-do-meio) e
[`docs/AMBIENTE.md`](./docs/AMBIENTE.md). `make help` lista todos os alvos.

> ⚠️ `make eval` gasta token a cada execução — não rode sem intenção
> ([ADR-0013](./docs/adr/0013-suite-de-avaliacao.md)).

---

## Organização do repositório

```
api/     backend Python — FastAPI, SQLAlchemy, Pydantic, uv
  src/estoque/
    domain/       tipos e regras puras. NÃO importa nada do projeto
    data/         porta única de dados; o único lugar com SQLAlchemy
    registry/     os componentes do catálogo: params, requires, load, select
    schema/       validação da saída do modelo, viewKey
    assistant/    adapter de modelo, prompt, trace, observabilidade
    commands/     pipeline de escrita (o assistente NÃO alcança daqui)
    server/       borda HTTP, autorização por registro, auditoria
  tests/

web/     cliente TypeScript — React, Vite, TanStack Query, Vitest
  src/
    views/        uma view por componente registrado. Só recebe `vm` e desenha
    ui/           Tabela, Indicador, BarraFaixas, Etiqueta
    render/       motor que monta a tela a partir do schema validado
    shell/        a moldura: painéis, login, workspace
    generated/    GERADO a partir do registry da API
    testes/

docs/    PRD, ADRs, regras de negócio, tarefas, relatórios de auditoria
```

As camadas do `api/` são **verificadas por `import-linter`**, não combinadas. A
mais importante: **`assistant` não importa `commands`** — é a tese em forma de
teste. Se existir caminho de código do assistente até a escrita, a promessa de
que "o modelo nunca autoriza escrever" deixa de ser verificável.

Convenções de código (pt-BR, sem `any`, `mypy --strict`, comentário explica por
quê) estão em [`CLAUDE.md`](./CLAUDE.md), com um por subprojeto
([`api/`](./api/CLAUDE.md), [`web/`](./web/CLAUDE.md)).

---

## Como este projeto foi construído

Todo o código, os 22 ADRs e as 39 tarefas foram escritos em par com um agente de
IA ([Claude Code](https://claude.com/claude-code)) — não em modo livre, mas
seguindo um processo que existe justamente para conter o que dá errado quando
um agente escreve sem esse tipo de contenção:

- **A tarefa vem antes do código.** Cada [`docs/tasks/T-0NN-*.md`](./docs/tasks/)
  é autocontida — se não dá para executá-la só com aquela leitura, o defeito é
  na tarefa, não uma licença para o agente ler o repositório inteiro. Toda
  tarefa declara os arquivos que **só ela** escreve.
- **Decisão registrada, não lembrada.** Cada [ADR](./docs/adr/) traz as
  alternativas descartadas e as consequências negativas — inclusive quando a
  escolha foi do agente. É o que permite auditar uma decisão meses depois sem
  reconstruir a conversa que a gerou.
- **Teste negativo é a regra da casa.** Para todo mecanismo de proteção, o par
  de testes que prova que ele funciona **e** o que prova que ele falha quando
  deveria — testar que alguém autorizado consegue faz pouco; testar que quem
  não é autorizado não consegue, nem por requisição forjada, é o que sustenta
  a arquitetura.
- **O board mente até ser auditado.** Duas skills —
  [`auditar-execucao`](./.claude/skills/auditar-execucao/) e
  [`auditar-testes`](./.claude/skills/auditar-testes/) — existem porque já
  aconteceu de o board dizer que nada tinha sido feito enquanto 19 tarefas
  estavam prontas, e de um CSRF prometido em três documentos e implementado em
  nenhum ([A-002](./docs/relatorios/A-002-auditoria-de-execucao.md)). Rodar
  essas auditorias, e corrigir o que elas encontram, faz parte do processo —
  não é um passo opcional de qualidade.

O `CLAUDE.md` na raiz é o manual operacional que o agente lê antes de tocar no
repositório — não documentação escrita para humano, mas para a sessão que vem
depois. É esse arquivo, mais o de cada subprojeto, que faz o processo acima
acontecer de novo em cada tarefa, com sessões diferentes, sem depender de
memória de conversa.

---

## Origem

Segunda iteração. A primeira ([achados](./docs/00-achados-v1.md)) provou a
arquitetura de composição, mas era **100% leitura, sem autenticação e nunca rodou
com uma API key real** — todos os números vieram de um parser simulado. Esta versão
existe para responder o que ficou de fora: **escrita, permissão de verdade, e com
que frequência um modelo real emite schema válido.**

Licença: MIT
