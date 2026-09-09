# CLAUDE.md — o que uma sessão precisa saber antes de tocar neste repositório

Sistema de controle de estoque para a Bertoni Distribuidora Farmacêutica (caso
fictício), com um assistente que **compõe telas escolhendo componentes
registrados** — nunca gerando código.

Monorepo de dois projetos: `api/` (Python) e `web/` (TypeScript). Cada um tem
seu próprio `CLAUDE.md`, com as convenções da linguagem. **Este arquivo é o que
vale para os dois.**

---

## 1. A tese, em três frases

Estas são as três decisões de que tudo o mais decorre. Uma mudança que as
contrarie não é um refactor, é outro projeto.

1. **O modelo escolhe a composição. Nunca o código, nunca os dados, nunca a
   autorização.** ([ADR-0001](docs/adr/0001-ui-por-schema.md))
2. **A saída do modelo autoriza renderizar. Nunca autoriza escrever.**
   ([ADR-0002](docs/adr/0002-plano-render-plano-escrita.md))
3. **Autorização acontece em três momentos, e só o terceiro protege** — o que
   roda em cada `load` e cada `command`, com a identidade real.
   ([ADR-0004](docs/adr/0004-autorizacao-em-tres-momentos.md))

---

## 2. Antes de escrever qualquer linha: o protocolo de leitura

Este projeto tem muita documentação **de propósito**, e ler tudo é o erro.
O [acordo de trabalho](docs/tasks/README.md) §2 define o que ler, e nada além:

1. o arquivo da tarefa — `docs/tasks/T-0NN-*.md`
2. [`docs/tasks/CONTRATOS.md`](docs/tasks/CONTRATOS.md) — interfaces congeladas
3. **só** os ADRs que a tarefa citar
4. **só** as regras `RN-*` que a tarefa citar, em `docs/02-regras-de-negocio.md`

Cada arquivo de tarefa é auto-contido. Se uma tarefa não pode ser executada com
essa leitura, **a tarefa está mal escrita** — corrigir a tarefa é a ação certa,
não ler mais.

Hierarquia em caso de conflito: **`RN-*` > ADR > PRD > tarefa.**

**Estado do projeto é apurado, nunca presumido:** a verdade está em
[`docs/tasks/PROGRESSO.md`](docs/tasks/PROGRESSO.md) e
[`docs/tasks/BOARD.md`](docs/tasks/BOARD.md), e muda **no mesmo commit da
entrega**. Não deduza o estado da conversa — foi assim que o board passou a
dizer que nada tinha sido feito enquanto 19 tarefas estavam prontas, e o CSRF
ficou prometido em três documentos e implementado em nenhum
([A-002](docs/relatorios/A-002-auditoria-de-execucao.md)).

---

## 3. Subir, derrubar, e a armadilha do meio

```bash
make up          # sobe tudo: db + api + web, via docker compose
make down        # derruba os serviços
make reset       # derruba e APAGA os dados (volumes)
make logs        # acompanha
```

**Para desenvolver e rodar teste localmente**, o banco precisa estar publicado
em `localhost:15432`:

```bash
make db-local    # publica o Postgres na porta local (exige -f explícito)
make migrate     # alembic upgrade head
make seed        # dados da Bertoni, idempotente
```

> ⚠️ **A armadilha:** `make migrate` roda com o `docker-compose.yml` sozinho, e
> isso **recria o container do banco sem o mapeamento de porta**. Depois de
> migrar, rode `make db-local` de novo. Sem a porta, nove testes de
> imutabilidade **pulam** — e teste que pula é teste que não existe.

**Ambiente:**

```bash
make env             # compara .env com .env.example e aponta o que falta
make env-completar   # acrescenta as variáveis novas
make modelo          # mostra provedor, modelo e modo em uso
```

`make env` existe por um motivo concreto ([ADR-0027](docs/adr/0027-ambiente-verificado.md)):
acrescentar variável ao `.env.example` **não** atualiza o `.env` de quem já
rodou, e a variável ausente cai num padrão que funciona — e é por funcionar que
passa despercebida. Foi exatamente assim que o LangFuse ficou apontando para a
região errada por semanas.

**Derrubar processo preso:**

```bash
docker compose ps                 # o que está de pé
docker compose down              # encerra tudo
docker compose down -v           # ...e apaga os volumes
lsof -ti:15432 | xargs kill      # se a porta ficou órfã
```

---

## 4. O ciclo de verificação

```bash
make check       # lint + typecheck + test + arch — é o que o CI roda
```

Ou individualmente:

| Comando | O que faz |
|---|---|
| `make lint` | `ruff check` + `ruff format --check` no Python; `eslint` no TS |
| `make typecheck` | `mypy --strict src` no Python; `tsc --noEmit` no TS |
| `make test` | `pytest` no Python; `vitest run` no TS |
| `make arch` | índices em dia + `import-linter` + `arch-check.ts` |
| `make types` | regenera `contrato.json` e `componentes.ts` a partir do registry |
| `make gerar-indice` | regenera `registry/indice.py` e `views/indice.ts` |

**Nunca rode `make eval` sem intenção** — ele gasta token a cada execução
([ADR-0013](docs/adr/0013-suite-de-avaliacao.md)).

### Arquivos gerados — nunca edite à mão

| Arquivo | Gerado por |
|---|---|
| `api/src/estoque/registry/indice.py` | `make gerar-indice` |
| `api/src/estoque/commands/indice.py` | `make gerar-indice` |
| `web/src/views/indice.ts` | `make gerar-indice` |
| `web/src/generated/contrato.json` | `make types` |
| `web/src/generated/componentes.ts` | `make types` |

Eles são gerados porque são os **únicos arquivos que toda tarefa de componente
precisaria editar** — 22 componentes registrados à mão em dois arquivos seriam
44 conflitos de merge garantidos. `make arch` falha se estiverem desatualizados.

O `commands/indice.py` entrou pelo mesmo motivo, e pelo achado A-15: as **cinco**
tarefas de escrita de W4 precisariam da mesma linha de import nele.

---

## 5. Arquitetura, em uma tela

```
        pergunta do usuário
                │
                ▼
   ┌─────────────────────────────┐
   │  catálogo POR ATOR          │  só o que este papel pode ver
   │  registry/registry.py       │  (ADR-0003)
   └──────────────┬──────────────┘
                  ▼
   ┌─────────────────────────────┐
   │  modelo compõe um SCHEMA    │  ids + params. Nunca código,
   │  assistant/adapter.py       │  nunca SQL, nunca permissão
   └──────────────┬──────────────┘
                  ▼
   ┌─────────────────────────────┐
   │  VALIDAR contra o catálogo  │  ← a barreira. Componente fora
   │  schema/validar.py          │    do catálogo DESTE ator morre
   └──────────────┬──────────────┘    aqui (ADR-0002)
                  ▼
   ┌─────────────────────────────┐
   │  load  →  select            │  autorizado, com identidade real.
   │  registry/componentes/*.py  │  `select` roda NO SERVIDOR (ADR-0020)
   └──────────────┬──────────────┘
                  ▼
   ┌─────────────────────────────┐
   │  viewmodel atravessa a rede │  só o que a tela precisa.
   │  → web/src/views/<id>.tsx   │  Sem custo, sem linha de banco
   └─────────────────────────────┘
```

**Camadas do `api/`, verificadas por `import-linter`** (não é convenção, é CI):

| Módulo | Papel | Não pode importar |
|---|---|---|
| `domain/` | tipos, regras puras, erros, identidade | **nada** do projeto |
| `data/` | porta única de dados + SQLAlchemy | — |
| `registry/` | os componentes: params, `requires`, `load`, `select` | `server`, `sqlalchemy` |
| `schema/` | validação da saída do modelo, `viewKey` | — |
| `assistant/` | adapter de modelo, prompt, trace, observador | **`commands`** ← a barreira do ADR-0002 |
| `commands/` | pipeline de escrita | — |
| `server/` | borda HTTP, autorização por registro, auditoria | — |
| `auth/`, `autorizacao/`, `auditoria/` | sessão/CSRF, permissões, trilha | — |

A regra **`assistant` não importa `commands`** é a tese em forma de teste: se
existir caminho de código do assistente até um comando de escrita, a promessa
de que "o modelo nunca autoriza escrever" deixa de ser verificável.

---

## 6. Como se trabalha aqui

Use a skill **`executar-tarefa`** — ela tem o laço completo (DoR → leitura →
implementar → DoD → commit). O essencial:

### Propriedade exclusiva de arquivo
Toda tarefa declara os arquivos que **só ela** escreve. Uma tarefa que precisa
escrever num arquivo que não é seu **está bloqueada** — não é exceção
justificável, é sinal de que o corte de tarefas está errado.

### Teste negativamente — a regra da casa
Para todo mecanismo de proteção, escreva os dois testes:

1. o que prova que funciona quando deveria funcionar;
2. **o que prova que falha quando deveria falhar.**

O segundo é o que vale. *Testar que Helena consegue liberar quarentena prova
pouco. Testar que Ivo **não** consegue, nem por requisição forjada, é o que
prova a arquitetura.*

> **Uma regra que nunca falhou não é evidência de nada.**

### Status é entrega, não relatório
Ao concluir, três coisas **no mesmo commit**: marcar os `- [ ]` do arquivo da
tarefa que foram *de fato verificados*, mudar a linha no BOARD e no PROGRESSO,
e revisar o PRD se o escopo mudou.

**Critério de aceite não conferido fica em branco.** Marcar por otimismo é pior
que deixar vazio: cria evidência falsa, e evidência falsa só é descoberta
quando alguém confia nela.

### Quando perguntar, e quando parar
Antes de implementar, **uma linha com a recomendação** ([ADR-0028](docs/adr/0028-processo-de-decisao.md)):

| Exige pergunta | Não exige |
|---|---|
| acrescentar dependência ou container | corrigir bug |
| mudar contrato congelado | escrever teste |
| escolher entre caminhos com custo ou risco distintos | seguir ADR já registrado |

**Pare e sinalize** — não improvise — se precisar mudar contrato congelado,
escrever em arquivo de outra tarefa, ou se achar critério de aceite ambíguo,
conflito entre regras `RN-*`, ou decisão de negócio que não está em documento
nenhum. Os dois últimos viram **achado**, registrado no BOARD.

### Commits
`T-0NN: <o que mudou>` — o id no começo, sempre. A mensagem explica **por quê**,
e cita o critério de aceite que passou a valer.

---

## 7. Convenções que atravessam os dois projetos

- **Idioma:** código, comentários, commits e documentos em **pt-BR**. No Python
  os comentários vão **sem acento** (convenção herdada); no TypeScript, com.
- **Comentário explica *por quê*, não *o quê*.** Se descreve o que a linha faz,
  apague — a linha já faz isso. Se registra a razão de uma escolha, ou a
  armadilha que ela evita, mantenha.
- **Nada de `any` no TS, nada de `Any` sem justificativa no Python.**
  `mypy --strict` é obrigatório.
- **Nenhum dado de estoque sai para serviço de terceiro.** O prompt não contém
  dados ([ADR-0012](docs/adr/0012-injecao-de-prompt-via-dado.md)) e o observador
  do LangFuse registra métrica, nunca linha.

---

## 8. Auditoria

Duas skills, para as duas coisas que já falharam neste projeto:

- **`auditar-execucao`** — o board diz a verdade? Toda tarefa ✅ tem os ACs
  realmente testados? Promessa em ADR tem código correspondente?
- **`auditar-testes`** — todo AC tem teste? Toda proteção tem teste negativo?
  Algum teste pula em silêncio? Os fakes divergiram do adaptador real?

Rode-as antes de fechar uma onda, e sempre que desconfiar de que documento e
código andaram separados.

---

## 9. Mapa dos documentos

| Quero... | Vá para |
|---|---|
| executar uma tarefa | `docs/tasks/README.md` → `BOARD.md` → o arquivo da tarefa |
| entender o projeto | `docs/README.md` → `docs/01-o-cliente.md` → `docs/prd/PRD-001-ciclo-1.md` |
| saber por que uma decisão técnica é assim | `docs/adr/` |
| saber onde uma regra está implementada | `docs/RASTREABILIDADE.md` |
| saber o estado real | `docs/tasks/PROGRESSO.md` |
| ver o que já deu errado | `docs/relatorios/` |
