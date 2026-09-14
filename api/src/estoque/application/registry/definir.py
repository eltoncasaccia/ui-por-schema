"""Contrato de componente — lado servidor. CONTRATOS secao 5, ADR-0017.

Este modulo NAO tem campo `render`. A view React vive em `web/src/views/<id>.tsx`
e e' ligada a este registro pelo id, com bijecao verificada em CI.

O ADR-0006 dizia "uma declaracao produz tudo" e se orgulhava de nao ter uma
segunda lista. Com a API em Python, a segunda lista existe — e o teste de
bijecao e' o que impede o apodrecimento que o ADR-0006 descrevia.
"""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from pydantic import BaseModel

from estoque.data.porta import ContextoDados, Repositorios
from estoque.domain.identidade import Ator, Permissao, UnidadeId

Tamanho = Literal["linha", "meia", "inteira", "alta"]


@dataclass(frozen=True, slots=True)
class Pagina:
    """Paginacao — preocupacao de TRANSPORTE, nunca do catalogo.

    Nao e' param de componente de proposito: o modelo compoe a tela, nao decide
    quantas linhas cabem nem por onde continuar. Isso pertence a quem rola.
    """

    limite: int = 20
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class LoadContext:
    """Contexto autorizado de carga. Nunca opcional, nunca reconstruido pelo `load`.

    Os repositorios sao INJETADOS: nenhum `load` constroi conexao nem decide
    escopo. O escopo ja' vem intersectado com as unidades do ator (RN-A01).
    """

    ator: Ator
    unidades_permitidas: frozenset[UnidadeId]
    repos: Repositorios
    dados: ContextoDados
    pagina: Pagina = field(default_factory=Pagina)


@dataclass(frozen=True, slots=True)
class RequiresPorValor:
    """Permissao que depende do VALOR de um param (achado A-05 da auditoria).

    `estoque_indicador` e' o caso: a metrica `valor_em_estoque` exige `custo.ler`,
    as demais nao. Em vez de esconder o componente inteiro de quem nao tem custo,
    o catalogo REMOVE o valor do enum — o modelo nao consegue nem propor.
    """

    base: tuple[Permissao, ...]
    # param -> valor do enum -> permissoes extras exigidas
    por_valor: Mapping[str, Mapping[str, tuple[Permissao, ...]]]


Requires = Permissao | tuple[Permissao, ...] | RequiresPorValor


def permissoes_base(req: Requires) -> tuple[Permissao, ...]:
    if isinstance(req, RequiresPorValor):
        return req.base
    if isinstance(req, tuple):
        return req
    return (req,)


@dataclass(frozen=True, slots=True)
class CommandDef:
    """Plano de escrita. O modelo NAO passa por aqui (ADR-0002).

    Ele pode fazer o formulario aparecer; quem dispara e' a pessoa que clica em
    salvar, pelo mesmo endpoint autenticado que a tela tradicional usa.
    """

    endpoint: str
    schema: type[BaseModel]  # validacao de DOMINIO, nao de UI
    requires: Requires
    confirm: bool
    idempotent: bool


class Carregador(Protocol):
    """`load` — roda no servidor, autorizado, com identidade real."""

    def __call__(self, params: Any, ctx: LoadContext) -> Awaitable[Any]: ...


@dataclass(frozen=True, slots=True)
class ComponentDef:
    """Uma entrada do vocabulario que o modelo recebe.

    `description` e `examples` vao LITERALMENTE para o prompt e custam ~164
    tokens por componente (ADR-0011). Sao escritos para o modelo decidir, nao
    para o desenvolvedor entender.
    """

    id: str
    label: str
    description: str
    examples: tuple[str, ...]
    params: type[BaseModel]
    requires: Requires
    tamanho: Tamanho
    load: Carregador
    # `select` roda AQUI, no servidor, logo apos o `load` (ADR-0020).
    # Se rodasse no cliente, `D` inteiro atravessaria a rede e tudo que o select
    # descarta ja' teria chegado ao navegador — falha de confidencialidade.
    select: Callable[[Any], BaseModel]
    commands: Mapping[str, CommandDef] = field(default_factory=dict)
    # PURA, como `select` — sem I/O, sem relogio. Recebe o MESMO `D` que `load`
    # devolveu, ANTES de `select` descartar o que a tela nao precisa. Existe so
    # para componente com `commands` cujo comando exige `If-Match` (T-050,
    # achado A-41): sem etag na leitura, a escrita nunca tem o que comparar.
    # `str | None` porque `controlado_autorizar` (T-051) não tem alvo fixo
    # quando aberto sem `movimento_id` — a fila sozinha não tem o que comparar.
    etag: Callable[[Any], str | None] | None = None

    def __post_init__(self) -> None:
        _validar(self)


_ID_VALIDO = "abcdefghijklmnopqrstuvwxyz0123456789_"


def _validar(c: ComponentDef) -> None:
    """Invariantes de CONTRATOS secao 5, checadas no registro."""
    if not c.id or any(ch not in _ID_VALIDO for ch in c.id):
        msg = f"id deve ser snake_case: {c.id!r}"
        raise ValueError(msg)
    if len(c.description) < 40:
        msg = (
            f"{c.id}: description com {len(c.description)} caracteres. "
            "E' o texto que o modelo le para decidir — descricao curta produz "
            "composicao errada, e a falha e' silenciosa."
        )
        raise ValueError(msg)
    if not c.examples:
        msg = f"{c.id}: examples vazio"
        raise ValueError(msg)
    if not permissoes_base(c.requires):
        msg = f"{c.id}: requires vazio — ADR-0004"
        raise ValueError(msg)
    # ADR-0005: formulario e' unidade inteira, nunca composto peca por peca.
    if c.commands and c.tamanho != "inteira":
        msg = f"{c.id}: componente com commands precisa de tamanho='inteira' (ADR-0005)"
        raise ValueError(msg)


def definir(**kwargs: Any) -> ComponentDef:
    """Acucar sintatico para `ComponentDef(...)`, com o mesmo efeito."""
    return ComponentDef(**kwargs)
