---
name: testes-python
description: Escreve testes do backend deste projeto — pytest, asyncio, personas, repositórios falsos e a regra do teste negativo. Use ao criar ou alterar qualquer teste em api/tests/, ao adicionar um componente do registry, ou quando um critério de aceite precisar virar teste no lado Python.
---

# Testes do `api/`

`pytest` com `asyncio_mode = "auto"` — teste `async def` roda direto, sem
decorador. Configuração em `pyproject.toml`; **não existe** `pytest.ini`.

```bash
uv run pytest -q                    # tudo
uv run pytest tests/registry -q     # um diretório
uv run pytest -k lote_lista -q      # por nome
uv run pytest -q -rs                # mostra o que pulou, e por quê
```

---

## A regra que governa tudo

Para todo mecanismo de proteção, **dois** testes:

1. prova que funciona quando deveria funcionar;
2. **prova que falha quando deveria falhar.**

O segundo é o que vale. *Testar que Helena consegue liberar quarentena prova
pouco. Testar que Ivo não consegue, nem por requisição forjada, é o que prova a
arquitetura.*

Um teste positivo sozinho, num caminho de autorização, é um teste que ainda não
foi escrito.

---

## As sete personas

`tests/conftest.py` expõe a fixture `personas`. **O conjunto de papéis É o teste
de permissão** — não remova nenhum para "simplificar".

| | papel | unidades | tem `custo.ler`? |
|---|---|---|---|
| marco | diretor | todas | sim |
| helena | rt | todas | não |
| ivo | gerente | matriz + refrigerado | não |
| odair | gerente | **só Uberlândia** | não |
| cleide | conferente | matriz + refrigerado | não |
| rafael | comprador | todas | sim · **sem `movimento.ler`** |
| sandra | auditoria | todas | sim |

**Odair é o par de Ivo**: escopos disjuntos, é o que prova `CA-06`.
**Rafael é o contraexemplo de permissão em tupla**: `requires` com duas
permissões é conjunção, e ele tem uma só.
Há ainda `recem_cadastrado` — catálogo vazio, porque cadastro não concede papel.

---

## Componentes do registry: use os fakes

`tests/registry/fakes.py` traz repositórios falsos e um estoque montado **para os
casos difíceis, não para parecer real**:

```python
from fakes import contexto, LOTES, MOVIMENTOS, SINAL

async def test_algo(personas):
    vm = projetar(await carregar(Params(), contexto(personas["odair"])))
```

| Lote | Serve para |
|---|---|
| `l-amox-mtz` / `l-amox-uber` | mesmo número, unidades diferentes (`RN-L08`) |
| `l-amox-venc` | gravado `liberado`, **vencido** de fato (ADR-0022) |
| `l-vac-quar` / `l-vac-quar-venc` | quarentena em dia / que venceu esperando |
| `l-amox-zero` | entrada = saída → saldo zero, `esgotado` |
| `l-rital-bloq` | controlado, com `autorizador_id` (`RN-C01`) |

O custo está **presente** no fixture de propósito: custo ausente faria o teste de
custo invisível passar por acidente, provando nada.

> **O que os fakes NÃO provam:** que o adaptador SQLAlchemy real intersecta
> escopo. Eles provam que o *componente* não contorna a porta. O contract test
> entre fake e repositório real é a T-042, e está aberto.

---

## Idioms deste repositório

**Enum inválido entra por dicionário.** É assim que ele chega de verdade — JSON
do modelo, sem tipo nenhum:

```python
with pytest.raises(ValidationError):
    Params.model_validate({"janela": "45"})     # ✅
    # Params(janela="45")                        # ❌ briga com o verificador
```

**Negativa que não vaza:** compare a face pública **inteira**, não só o código.

```python
def face(e: ErroDominio) -> tuple[str, str, str]:
    return (e.codigo, e.mensagem_publica, repr(e))

assert face(fora_de_escopo) == face(inexistente)
```

Bastaria a mensagem diferir para a negativa virar oráculo de enumeração.

**Custo invisível:** afirme sobre o JSON serializado, não sobre campos.

```python
bruto = vm.model_dump_json()
assert "custo" not in bruto
assert "1250" not in bruto      # o custo do fixture, por outro nome
```

**`select` puro:** `assert projetar(dados) == projetar(dados)`.

**Banco:** `tests/data/` pula sem Postgres. `make db-local && make migrate`, e
`make db-local` **de novo** — migrate derruba o mapeamento de porta.

---

## Antes de entregar

```bash
uv run pytest -q
uv run mypy --strict src
uv run mypy --strict tests      # make typecheck NÃO faz isto — achado A-09
uv run ruff check src tests && uv run ruff format src tests
uv run lint-imports
```

E a pergunta final, para cada teste que você escreveu: **se eu quebrasse a regra
que este teste protege, ele ficaria vermelho?** Se não tiver certeza, quebre de
propósito e confirme.
