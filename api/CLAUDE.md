# CLAUDE.md — `api/`

Backend em Python 3.13, FastAPI, SQLAlchemy, Pydantic v2. Gerenciado por `uv`.

Leia primeiro o [`CLAUDE.md` da raiz](../CLAUDE.md) — a tese, o protocolo de
leitura e o processo valem para os dois projetos. Este arquivo cobre só o que é
específico do Python.

---

## Comandos

Rode da raiz do repositório (`make ...`) ou aqui dentro:

```bash
uv sync                              # instala/atualiza o venv a partir do uv.lock
uv run pytest -q                     # testes
uv run pytest tests/registry -q      # só um diretório
uv run pytest -k lote_lista -q       # por nome
uv run mypy --strict src             # tipos
uv run ruff check src tests          # lint
uv run ruff format src tests         # formata
uv run lint-imports                  # contratos de camada
```

> O pacote é instalado em **modo editável**. Uma worktree git com `.venv`
> compartilhado importaria o código da árvore principal e testaria a coisa
> errada em silêncio — cada worktree precisa do seu `uv sync`.

---

## O padrão: Ports & Adapters (hexagonal)

O desenho tem nome, e é o de sempre: **arquitetura hexagonal**, com a regra de
dependência do Clean — **as setas apontam para dentro**. Nada no núcleo conhece
Postgres, HTTP ou o modelo de linguagem.

O que este projeto faz e a maioria não: **a regra é CI, não revisão**
([ADR-0031](../docs/adr/0031-ports-and-adapters.md)).

```
                        ADAPTERS PRIMÁRIOS
                     (quem CHAMA o sistema)
                              │
                        server/  ← HTTP
                              │
        ┌─────────────────────▼─────────────────────┐
        │              APPLICATION                  │
        │   registry/  leitura   (load, select)     │
        │   commands/  escrita   (pipeline)         │
        │   schema/    valida a entrada hostil      │
        │                                           │
        │        ┌───────────────────────┐          │
        │        │        DOMAIN         │          │
        │        │  tipos · regras puras │          │
        │        │  FEFO · validade      │          │
        │        │  máquina de estados   │          │
        │        └───────────────────────┘          │
        └───────────────────┬───────────────────────┘
                            │  fala só com PORTAS
        ┌───────────────────▼───────────────────────┐
        │  data/porta.py         6 Protocol         │
        │  assistant/adapter.py  AdaptadorModelo    │
        │  assistant/observador.py  Observador      │
        └───────────────────┬───────────────────────┘
                            │
                     ADAPTERS SECUNDÁRIOS
                    (o que o sistema chama)
     data/repositorios.py · assistant/fabrica.py · langfuse_obs.py
             Postgres          OpenRouter/Ollama      LangFuse
```

### Onde cada coisa mora, e por quê

| Pasta | Papel no hexágono | Por que existe separada |
|---|---|---|
| `domain/` | **núcleo** | Regra que precisa de banco é regra que ninguém testa. Não importar nada é o que deixa `RN-L02` ser exercitada sem subir Postgres |
| `application/registry/` | caso de uso de **leitura** | Componente descreve **o quê**, não **como buscar** |
| `application/commands/` | caso de uso de **escrita** | Separado de `registry` **para o contrato 3 poder existir** — não é arrumação |
| `application/schema/` | validação de entrada | Schema recebido é payload não-confiável **venha do modelo ou do cliente** |
| `data/porta.py` | **portas** (6 `Protocol`) | O que a aplicação precisa, sem dizer de onde vem |
| `data/repositorios.py` | **adapter** Postgres | Aplica escopo (`RN-A01`) e some com campo restrito (`RN-A02`) — num lugar só |
| `assistant/` | **porta + adapter** do LLM | `adapter.py` é a porta; `fabrica.py` escolhe OpenRouter, Ollama ou Anthropic |
| `server/app.py` | **raiz de composição** | Monta a aplicação e registra o que vale para TODA rota: middleware de CSRF, os três handlers de erro, o ciclo de vida. Nenhuma regra de negócio |
| `server/deps.py` | núcleo compartilhado | `motor`, `CFG`, `OBS`, `ok`, `ator_ou_falhar`, `repos`, `Tx`. Existe para que os routers **não** importem `app.py` — importariam de volta e o ciclo só se resolveria com import tardio |
| `server/rotas/` | **adapter primário**, uma área por arquivo | A borda HTTP, e o único módulo que conhece os dois planos. Um router **nunca** importa outro — contrato 5 ([ADR-0032](../docs/adr/0032-borda-http-por-router.md)) |
| `auth/`, `autorizacao/`, `auditoria/` | serviços transversais | Fora de `server/` de propósito: `autorizacao/motor.py` é chamado pela borda **e** pelo pipeline. Dentro de `server/`, `commands` teria que importar a borda para autorizar |

> **Ambiguidade honesta:** `auth/` é meio adapter (sessão em cookie, CSRF) e meio
> aplicação (política de acesso). É a única fronteira do projeto que não é limpa,
> e está anotada em vez de disfarçada.

---

## Camadas — verificadas, não combinadas

`api/.importlinter` transforma o desenho em CI. Os cinco contratos:

| # | Contrato | Por quê |
|---|---|---|
| 1 | `domain` não importa **nada** do projeto | regra pura tem de ser testável sem banco, sem HTTP, sem modelo |
| 2 | `application.registry` não importa `server` nem `sqlalchemy` | componente descreve **o quê**, não **como buscar** |
| 3 | **`assistant` não importa `application.commands`** | a tese em forma de teste: se existe caminho do assistente até a escrita, "o modelo nunca autoriza escrever" deixa de ser verificável |
| 4 | `assistant.prompt` não importa `data` | prompt não pode conter dado do estoque ([ADR-0012](../docs/adr/0012-injecao-de-prompt-via-dado.md)) |
| 5 | os oito routers de `server.rotas` **não se importam** | router que importa router reconstrói o monolito por dentro: oito arquivos que só rodam juntos é pior que um de 817 linhas, porque parece resolvido ([ADR-0032](../docs/adr/0032-borda-http-por-router.md)) |

**E o verificador tem testes que provam que ele quebra.**
`tests/arquitetura/test_verificador_falha_quando_violado.py` introduz cada
violação de propósito — inclusive por caminho indireto de dois saltos — e afirma
que o `lint-imports` sai com código diferente de zero. Sem isso, verde não
significa nada: pode estar verde por não estar verificando.

Precisou violar um contrato? **Pare.** O contrato está certo e o desenho está
errado, ou é uma decisão que vira ADR. Não é para desligar a regra.

---

## Anatomia de um componente do registry

Todo componente em `src/estoque/application/registry/componentes/<id>.py` tem a mesma forma.
`fila_vencimento.py` é o exemplo canônico — **leia antes de escrever o seu**.

```python
class Params(BaseModel):
    # TODO recorte é valor NOMEADO. Nunca data solta, nunca texto livre.
    janela: Literal["30", "60", "90"] = "90"
    unidade_id: UnidadeId | None = None

class VM(BaseModel):
    """O viewmodel: é EXATAMENTE isto que atravessa a rede."""

async def carregar(params: Params, ctx: LoadContext) -> Dados: ...
def projetar(d: Dados) -> VM: ...   # PURO: sem I/O, sem relógio

COMPONENTE = registrar(ComponentDef(
    id=..., label=..., description=..., examples=...,
    params=Params, requires="lote.ler", tamanho="inteira",
    load=carregar, select=projetar,
))
```

### As cinco regras que governam isso

1. **Param é enum, não texto livre.** Todo recorte que o usuário sabe pedir
   precisa existir no catálogo como valor nomeado. Filtro que falta **alarga a
   resposta em silêncio** — o achado mais perigoso da v1 (risco R-5 do PRD), e
   uma lista maior parece uma resposta boa.
2. **`select` roda no servidor** ([ADR-0020](../docs/adr/0020-select-no-servidor.md)).
   Se rodasse no cliente, `Dados` inteiro atravessaria a rede e tudo que o
   `select` descarta já teria chegado ao navegador.
3. **`select` é puro.** Sem I/O, sem `date.today()` — a data chega pelo `Dados`.
   Duas chamadas sobre a mesma carga têm de dar o mesmo resultado.
4. **Nunca coloque custo no viewmodel**, para papel nenhum. O que não está lá
   não chega ao navegador (`CA-05`).
5. **`description` e `examples` vão LITERALMENTE para o prompt** e custam ~164
   tokens por componente. São escritos para o modelo decidir, não para o
   desenvolvedor entender. E **não citem valores de enum que o filtro de
   permissão removeu** — a prosa vaza o que o enum escondeu.

O `LoadContext` já traz `repos` injetados e o escopo **já intersectado** com as
unidades do ator (`RN-A01`). Nenhum `load` constrói conexão nem decide escopo.

Componente novo? Use a skill **`componente-novo`** — ela cobre os dois lados,
que é o que o [ADR-0017](../docs/adr/0017-registry-servidor-views-cliente.md) exige.

---

## Anatomia de um comando de escrita

A outra metade, e a que este arquivo não descreve: **componente descreve, comando
executa.** Um comando são três peças — o schema num módulo-folha
(`commands/entradas/`), o executável (`commands/`) e o `CommandDef` que o
componente publica — e quatro decisões que o tipo obriga: `requires`,
`idempotent`, `etag_de`, `confirm`.

Comando novo? Use a skill **`comando-novo`**. Ela tem a forma, o que o pipeline
já faz por você, as armadilhas de saldo (a view materializada **não** é fonte —
achado A-20) e os testes negativos obrigatórios. **Leia um exemplo, não os
cinco** — a skill diz qual, pela forma do seu comando.

---

## Erros

`ErroDominio` tem duas faces, e a distinção é de segurança, não de estilo:

```python
raise nao_encontrado({"lote_id": params.lote_id, "ator": ctx.ator.id})
#                     └── detalhe_interno: vai para o LOG, nunca para a resposta
```

**`nao_encontrado` é a resposta para inexistente E para fora de escopo**, e as
duas têm de ser indistinguíveis — mensagem, código, tudo
([ADR-0014](../docs/adr/0014-erros-que-nao-vazam.md)). Se diferissem, alguém
mapearia o estoque das outras unidades perguntando id por id e lendo qual erro
volta. Nenhum corpo de erro lista ids.

---

## Testes

Convenções em [`.claude/skills/testes-python`](.claude/skills/). O resumo:

- `pytest` com `asyncio_mode = "auto"` — teste `async def` roda direto, sem
  decorador.
- As sete personas estão em `tests/conftest.py` como fixture `personas`. **O
  conjunto de papéis É o teste de permissão** — remover um enfraquece a suíte.
- Repositórios falsos para componentes: `tests/registry/fakes.py`.
- Testes de banco **pulam sem Postgres** e gravam em `estoque_teste`, nunca no
  banco de desenvolvimento. Rode `make db-local && make db-teste`. Os endereços
  moram em `tests/banco.py` — importe de lá, não repita a URL no arquivo de
  teste. Apontar para o banco de dev para a suíte antes de coletar (T-052).
- Valor inválido de enum entra por `Model.model_validate({...})`, com
  dicionário — é assim que ele chega de verdade, vindo do JSON do modelo. Passar
  literal inválido como kwarg só briga com o verificador de tipos.

> `make typecheck` roda `mypy --strict src` e **não** `tests`. É o achado A-09,
> endereçado à T-041. Enquanto isso, rode `uv run mypy --strict tests` antes de
> entregar teste novo.
