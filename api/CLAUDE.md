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

## Camadas — verificadas, não combinadas

`api/.importlinter` transforma o desenho em CI. Os contratos:

| # | Contrato | Por quê |
|---|---|---|
| 1 | `domain` não importa **nada** do projeto | regra pura tem de ser testável sem banco, sem HTTP, sem modelo |
| 2 | `registry` não importa `server` nem `sqlalchemy` | componente descreve **o quê**, não **como buscar** |
| 3 | **`assistant` não importa `commands`** | a tese em forma de teste: se existe caminho do assistente até a escrita, "o modelo nunca autoriza escrever" deixa de ser verificável |
| 4 | `assistant.prompt` não importa `data` | prompt não pode conter dado do estoque ([ADR-0012](../docs/adr/0012-injecao-de-prompt-via-dado.md)) |

Precisou violar um contrato? **Pare.** O contrato está certo e o desenho está
errado, ou é uma decisão que vira ADR. Não é para desligar a regra.

---

## Anatomia de um componente do registry

Todo componente em `src/estoque/registry/componentes/<id>.py` tem a mesma forma.
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
- Testes de banco (`tests/data/`) **pulam sem Postgres**. Rode `make db-local`.
- Valor inválido de enum entra por `Model.model_validate({...})`, com
  dicionário — é assim que ele chega de verdade, vindo do JSON do modelo. Passar
  literal inválido como kwarg só briga com o verificador de tipos.

> `make typecheck` roda `mypy --strict src` e **não** `tests`. É o achado A-09,
> endereçado à T-041. Enquanto isso, rode `uv run mypy --strict tests` antes de
> entregar teste novo.
