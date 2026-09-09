# Contratos Congelados — Ciclo 1

| | |
|---|---|
| **Status** | **CONGELADO** a partir da conclusão de T-004 |
| **Autoridade** | Normativo. Código que divergir daqui está errado, não o contrário |
| **Alteração** | Só por ADR novo + tarefa de contrato. Nunca em tarefa de feature |
| **Revisão** | 2.2 — `registry/`, `commands/` e `schema/` passaram para `application/` ([ADR-0031](../adr/0031-ports-and-adapters.md)). **Só caminho mudou**: nenhuma assinatura, nenhum tipo, nenhum campo |
| | 2.1 — provedor e modo de saída viraram configuração ([ADR-0025](../adr/0025-agnosticismo-de-provedor.md)); composição vazia passou a ser resposta válida |

> **Por que este documento existe.** Trabalho paralelo em várias sessões só é
> seguro se as fronteiras entre as partes forem decididas **antes** de as partes
> existirem. Uma tarefa que precisa mudar um contrato **para**, abre uma tarefa de
> contrato e espera — nunca muda no lugar.

---

## Índice — leia só a sua seção

São 14 KB. **Ler o documento inteiro para escrever um componente é o desperdício
que o protocolo de leitura tenta evitar.** Ache a linha, leia a seção.

| Se você vai... | Leia |
|---|---|
| entender o corte api/web | §0 Onde cada coisa mora |
| escrever `requires`, ou mexer em papel/permissão | §1 Identidade e permissão |
| levantar erro de domínio | §2 Erros |
| tocar produto, lote, movimento | §3 Entidades |
| escrever um `load` | §4 Porta de dados |
| **registrar um componente** | §5 Contrato de componente **+** §6 Contrato de view |
| escrever a view React | §6 Contrato de view |
| mexer na composição do modelo | §7 Schema do assistente |
| tocar rota HTTP | §8 Borda HTTP |
| conferir o teto de 25 componentes | §9 Catálogo |
| nomear coisas | §10 Convenções |
| **mudar um contrato** | §11 O que muda este documento — e pare antes |

---

## 0. Onde cada coisa mora

```
api/  Python 3.13   domínio · dados · registry · assistente · servidor
web/  TypeScript    views · motor de render · rotas · telas

fronteira: HTTP/JSON, descrita por OpenAPI, com tipos gerados para o cliente
```

Regra que governa tudo abaixo ([ADR-0016](../adr/0016-api-python-cliente-typescript.md),
[ADR-0020](../adr/0020-select-no-servidor.md)):

> **O cliente recebe viewmodels. Nunca modelos de domínio, nunca linhas de banco,
> nunca o resultado bruto de um `load`.**

---

## 1. Identidade e permissão · `api/src/estoque/domain/identidade.py`

```python
PapelId = Literal['diretor','rt','gerente','conferente','comprador','auditoria']
UnidadeId = Literal['cd-matriz','cd-refrigerado','filial-uberlandia']

Permissao = Literal[
    # leitura
    'produto.ler','lote.ler','movimento.ler','recebimento.ler','temperatura.ler',
    'auditoria.ler','auditoria.rastrear','usuario.ler','custo.ler',
    # escrita
    'lote.liberar','lote.status','movimento.criar','movimento.estornar',
    'movimento.descartar','recebimento.criar','controlado.movimentar',
    'controlado.autorizar','usuario.gerenciar',
]

@dataclass(frozen=True, slots=True)
class Ator:
    id: str
    nome: str
    papel: PapelId | None          # None = cadastrado sem papel — ADR-0019
    unidades: frozenset[UnidadeId]
    permissoes: frozenset[Permissao]
    ativo: bool
```

**18 permissões.** As três de produto (`criar`/`editar`/`inativar`) foram removidas
por não ter nenhum componente que as use (achado A-06) — voltam quando houver CRUD
de produto.

`papel: None` é o estado do recém-cadastrado: catálogo vazio, nenhum `load`
autorizado, nenhuma tela ([ADR-0019](../adr/0019-autenticacao-e-cadastro.md)).

> **Nenhuma função recebe `Ator` opcional.** Se a assinatura permite `None`, alguém
> vai passar `None`.

### Autorização que depende de dado, não de param

`controlado.movimentar` **não** entra em `requires`. Se uma saída é de controlado
depende do produto do lote, que é dado — o catálogo não tem como saber no momento
da filtragem. A checagem acontece **dentro do comando**, que é o terceiro momento
do [ADR-0004](../adr/0004-autorizacao-em-tres-momentos.md), o único que garante.

---

## 2. Erros · `domain/erros.py`

```python
CodigoErro = Literal[
    'nao_autenticado',  # não há ator
    'nao_autorizado',   # escopo declarado negado — ADR-0014
    'nao_encontrado',   # inexistente OU fora do escopo — indistinguíveis
    'invalido','conflito','limite',
]

class ErroDominio(Exception):
    def __init__(self, codigo: CodigoErro, mensagem_publica: str,
                 detalhe_interno: object | None = None) -> None: ...
```

> **`detalhe_interno` nunca é serializado.** Vai para o log do servidor, e é o
> único lugar onde `nao_encontrado` por inexistência e por escopo se distinguem
> ([ADR-0014](../adr/0014-erros-que-nao-vazam.md)).
>
> **Nenhuma `mensagem_publica` contém lista de ids.**

---

## 3. Entidades · `domain/tipos.py`

Sete entidades, completas — a revisão 1.0 definia três e as tarefas dependiam de
sete (achado A-07).

```python
ClasseProduto = Literal['comum','controlado','termolabil','antimicrobiano']
TipoUnidade   = Literal['seco','refrigerado']
TipoMovimento = Literal['entrada','saida','descarte','estorno']
StatusMovimento = Literal['efetivado','aguardando_autorizacao','recusado']

# ADR-0022 — só o que é decisão humana é armazenado
StatusLoteRegistrado = Literal['quarentena','liberado','bloqueado','descartado']
StatusLoteEfetivo    = StatusLoteRegistrado | Literal['vencido','esgotado']

@dataclass(frozen=True, slots=True)
class Produto:
    id: str; ean: str; nome: str; fabricante: str; principio_ativo: str
    classe: ClasseProduto; curva_abc: Literal['A','B','C']; ativo: bool
    custo_unitario_centavos: int | None = None   # ausente sem `custo.ler`

@dataclass(frozen=True, slots=True)
class Lote:
    id: str; produto_id: str; numero: str; unidade_id: UnidadeId
    fabricacao: date; validade: date
    status: StatusLoteRegistrado          # NÃO inclui vencido/esgotado
    endereco: str | None
    # NÃO existe campo `saldo`. NÃO existe `vencido` nem `esgotado` em coluna.

@dataclass(frozen=True, slots=True)
class Movimento:
    id: str; lote_id: str; unidade_id: UnidadeId
    tipo: TipoMovimento; quantidade: int          # positiva; sinal vem do tipo
    motivo: MotivoMovimento; complemento: str | None
    autor_id: str; autorizador_id: str | None     # 2ª identidade — RN-C01
    status: StatusMovimento
    criado_em: datetime                            # do SERVIDOR — RN-M04
    estorna_movimento_id: str | None
    cliente_id: str | None; nota_fiscal: str | None

@dataclass(frozen=True, slots=True)
class Recebimento:
    id: str; unidade_id: UnidadeId; nota_fiscal: str; fornecedor: str
    status: Literal['rascunho','conferido','liberado']
    conferente_id: str; rt_id: str | None          # RN-R05, controlados
    temperatura_chegada_c: float | None            # RN-F01, termolábeis
    divergencia: bool; recebido_em: datetime

@dataclass(frozen=True, slots=True)
class RegistroTemperatura:
    id: str; unidade_id: UnidadeId; medido_em: datetime; celsius: float

@dataclass(frozen=True, slots=True)
class Unidade:
    id: UnidadeId; nome: str; tipo: TipoUnidade; sala_cofre: bool

@dataclass(frozen=True, slots=True)
class Usuario:
    id: str; nome: str; email: str; papel: PapelId | None
    unidades: frozenset[UnidadeId]; ativo: bool
    # senha_hash NUNCA aparece neste tipo. Vive só em auth, nunca em domínio
```

### As duas ausências que são decisão

**`Lote` não tem `saldo`** (`RN-M06`) e **não tem `vencido`/`esgotado`**
([ADR-0022](../adr/0022-status-registrado-e-efetivo.md)). Ambos são derivados:

```python
def calcular_saldo(movimentos: Sequence[Movimento]) -> int: ...
def status_efetivo(lote: Lote, saldo: int, hoje: date) -> StatusLoteEfetivo: ...
```

Campo derivado e armazenado é campo editável, e campo editável é a divergência de
3,8% de volta.

---

## 4. Porta de dados · `data/porta.py`

```python
@dataclass(frozen=True, slots=True)
class ContextoDados:
    ator: Ator
    unidades_permitidas: frozenset[UnidadeId]   # já intersectadas. Nunca confie no chamador
    tx: Transacao                                # ADR-0018 — transação real
```

**A porta aplica o escopo de unidade e remove campo restrito.** Não é
responsabilidade do chamador lembrar de filtrar: `RN-A01` e `RN-A02` são aplicados
aqui, e testados aqui.

---

## 5. Contrato de componente · `registry/definir.py`

Lado servidor do [ADR-0017](../adr/0017-registry-servidor-views-cliente.md).

```python
Tamanho = Literal['linha','meia','inteira','alta']

@dataclass(frozen=True, slots=True)
class RequiresPorValor:
    """Permissão que depende do valor de um param — achado A-05."""
    base: tuple[Permissao, ...]
    por_valor: Mapping[str, Mapping[str, tuple[Permissao, ...]]]
    # param -> valor do enum -> permissões extras exigidas

Requires = Permissao | tuple[Permissao, ...] | RequiresPorValor

@dataclass(frozen=True, slots=True)
class CommandDef[E: BaseModel]:
    endpoint: str
    schema: type[E]              # validação de DOMÍNIO, não de UI
    requires: Requires
    confirm: bool
    idempotent: bool

@dataclass(frozen=True, slots=True)
class ComponentDef[P: BaseModel, D, V: BaseModel]:
    id: ComponentId
    label: str
    description: str             # vai para o prompt — ~164 tokens
    examples: tuple[str, ...]
    params: type[P]
    requires: Requires           # OBRIGATÓRIO — ADR-0004
    tamanho: Tamanho
    load:   Callable[[P, LoadContext], Awaitable[D]]   # servidor
    select: Callable[[D], V]                            # servidor — ADR-0020
    commands: Mapping[str, CommandDef[Any]] = field(default_factory=dict)
    # NÃO existe `render`. Ele vive em web/src/views — ADR-0017
```

**Invariantes verificadas por teste:**

1. `requires` é obrigatório — `mypy --strict` recusa a omissão.
2. `select` é pura: sem I/O, sem `datetime.now()`, sem acesso a repositório.
3. `V` é um modelo Pydantic e **é o que atravessa a rede**. `D` nunca sai do processo.
4. Componente com `commands` tem `tamanho='inteira'` ([ADR-0005](../adr/0005-l2-leitura-l1-escrita.md)).
5. Todo id registrado tem exatamente uma view no cliente, e vice-versa (ADR-0017).

### Filtragem de enum por permissão

Quando `requires` é `RequiresPorValor`, o catálogo **remove do enum** os valores
cujas permissões o ator não tem. `estoque_indicador` chega a Cleide sem a métrica
`valor_em_estoque` — o modelo não consegue nem propor.

---

## 6. Contrato de view · `web/src/views/tipos.ts`

Lado cliente do ADR-0017.

```ts
import type { ComponentId, ViewModel } from '../generated/api'

export type View<Id extends ComponentId> =
  (props: { vm: ViewModel<Id> }) => JSX.Element

// web/src/views/lote_lista.tsx
export const view: View<'lote_lista'> = ({ vm }) => <TabelaLotes linhas={vm.linhas} />
```

`ComponentId` e `ViewModel<Id>` são **gerados** do OpenAPI. O cliente não inventa
id e não escreve o tipo do viewmodel.

> **A view recebe apenas `vm`.** Não recebe ator, não busca dado, não decide regra,
> não conhece permissão.

---

## 7. Schema do assistente · `schema/contrato.py`

```python
class Bloco(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tipo: ComponentId
    params: Mapping[str, object]

class ViewSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')
    versao: Literal[1]
    titulo: str | None = None
    blocos: tuple[Bloco, ...]
```

**O que o schema não tem, e nunca terá:** markup, estilo, layout livre, valor
literal de dado, expressão. Acrescentar qualquer um exige revogar o
[ADR-0001](../adr/0001-ui-por-schema.md).

### Os dois identificadores · [ADR-0021](../adr/0021-viewkey-e-viewid.md)

| | O que é | Onde |
|---|---|---|
| `view_key` | hash do schema canonicalizado | **interno** — deduplicação, favorito, histórico |
| `view_id` | opaco, ≥128 bits de entropia | **público** — URL `/v/:viewId`, revogação, auditoria |

```python
def view_key(s: ViewSchema) -> str: ...     # determinístico, nunca em URL
```

Canonicalização: chaves ordenadas, `None` e defaults removidos, **ordem de blocos
preservada** (ordem é significado), números normalizados.

---

## 8. Borda HTTP · `server/envelope.py`

```python
class Meta(BaseModel):
    view_id: str | None = None
    etag: str | None = None
    duracao_ms: int

class RespostaOk[T](BaseModel):
    ok: Literal[True] = True
    dados: T
    meta: Meta

class RespostaErro(BaseModel):
    ok: Literal[False] = False
    erro: ErroPublico            # codigo + mensagem. Nada mais
```

| Endpoint | Método | Autorização |
|---|---|---|
| `/api/auth/registrar` | POST | pública — cria ator **sem papel** |
| `/api/auth/entrar` | POST | pública — rate limit, resposta uniforme |
| `/api/auth/sair` | POST | sessão |
| `/api/assistente/compor` | POST | sessão + CSRF + rate limit (`CS-06`) |
| `/api/view/{view_id}` | GET | revalida schema contra o catálogo **do requisitante** |
| `/api/componentes/{id}/dados` | POST | `requires` do componente, por registro |
| `/api/comandos/{nome}` | POST | `requires` do command + CSRF + `Idempotency-Key` |
| `/api/usuarios` | GET/PATCH | `usuario.gerenciar` — só tela, fora do catálogo |

**Regras da borda:**

- Escrita exige **token CSRF** de dupla submissão e `Origin` conferido (achado A-02).
- Escrita não idempotente exige `Idempotency-Key`; atualização exige `If-Match`.
- Todo erro passa por um serializador único que **descarta `detalhe_interno`**.
- Todo acesso — leitura inclusive — gera auditoria (`RN-D05`).

---

## 9. Catálogo — 22 componentes

Era 23. `confirm_action` **saiu do catálogo do modelo** (achado A-05): confirmação
é decisão do motor de render diante de `CommandDef.confirm`, não composição que o
modelo escolhe — mesmo tratamento que `sem_acesso` já tinha.

Teto de 25 ([ADR-0011](../adr/0011-teto-de-catalogo.md)): **22, folga de 3.**

---

## 10. Convenções

| Item | Convenção |
|---|---|
| Id de componente | `snake_case`, entidade primeiro — `lote_lista` |
| Registro (Python) | `api/src/estoque/application/registry/componentes/<id>.py` |
| View (TypeScript) | `web/src/views/<id>.tsx` |
| Permissão | `<recurso>.<acao>` |
| Teste de critério de aceite | `test_<us>_ac.py` / `*.ac.test.ts` |
| Teste de segurança | `test_cs<NN>_*.py` |
| Data/hora | `date`/`datetime` com timezone, **sempre do servidor** |
| Dinheiro | inteiro em **centavos**, sufixo `_centavos`. Nunca `float` |
| Nomes | Python `snake_case`; a serialização JSON também. O cliente não converte |

---

## 11. O que muda este documento

| Mudança | Caminho |
|---|---|
| Campo opcional novo num tipo | Tarefa normal, avisar no BOARD |
| Assinatura de `ComponentDef` | **Para tudo.** ADR + tarefa de contrato + migração |
| `Permissao` nova | Tarefa de contrato, rápida, mas serial |
| Campo no `ViewSchema` | ADR revogando ou emendando ADR-0001 |
| Qualquer coisa em `web/src/generated/**` | **Nunca.** É gerado; mude a API |
