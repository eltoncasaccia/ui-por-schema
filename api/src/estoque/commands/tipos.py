"""Vocabulario do plano de escrita. ADR-0002, ADR-0004.

O que este modulo NAO tem e' o ponto dele.

`CommandDef`, em `registry/definir.py`, descreve um comando para o motor de
render: endpoint, schema, `requires`, `confirm`. Ele nao carrega funcao nenhuma.
`Comando`, aqui, e' o que EXECUTA — e vive num registro separado, que o
`assistant` nao alcanca (import-linter, contrato 3).

A separacao e' a tese em forma de tipo: mesmo que o modelo compusesse um bloco
apontando para um comando, nao ha o que chamar do lado dele. Nao e' uma checagem
que alguem possa esquecer de fazer; e' a ausencia do caminho.

    plano de render     ComponentDef.commands -> CommandDef   (descricao)
    plano de escrita    registro de comandos  -> Comando      (execucao)
"""

from collections.abc import Awaitable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncConnection

from estoque.auditoria.registro import Origem
from estoque.domain.identidade import Ator, Permissao


@dataclass(frozen=True, slots=True)
class ContextoComando:
    """Contexto autorizado de escrita, com a identidade REAL.

    `agora` e' injetado pelo pipeline e vem do relogio do servidor (RN-M04).
    Nenhum comando chama `datetime.now()`: se chamasse, cada comando teria a sua
    propria nocao de "agora" e o timestamp do cliente voltaria pela porta dos
    fundos, num campo qualquer que ninguem revisou.
    """

    ator: Ator
    conn: AsyncConnection
    agora: datetime
    origem: Origem


@dataclass(frozen=True, slots=True)
class Efeito:
    """O que o comando fez, ja' na linguagem da auditoria (RN-D01).

    `valor_anterior` e `valor_novo` nao sao opcionais por conveniencia: sao o
    conteudo do registro de auditoria. Um comando que devolvesse so' "deu certo"
    produziria trilha que nao serve para reconstruir o que mudou — que e'
    exatamente para o que a trilha existe.
    """

    entidade: str
    entidade_id: str
    valor_anterior: dict[str, Any] | None
    valor_novo: dict[str, Any]
    dados: dict[str, Any]


class Aplicador(Protocol):
    """Aplica a regra de dominio e persiste. Roda DENTRO da transacao do pipeline."""

    def __call__(self, entrada: Any, ctx: ContextoComando) -> Awaitable[Efeito]: ...


class LeitorDeEtag(Protocol):
    """Le o estado atual da entidade alvo e devolve seu etag.

    `None` como retorno significa "a entidade nao existe" — e o pipeline traduz
    para `nao_encontrado`, indistinguivel de fora de escopo (ADR-0014).
    """

    def __call__(self, entrada: Any, ctx: ContextoComando) -> Awaitable[str | None]: ...


@dataclass(frozen=True, slots=True)
class Comando:
    """Uma entrada do registro de escrita.

    `idempotent=True` significa que repetir e' inofensivo por natureza (trocar um
    status para o mesmo valor). `False` significa que repetir DUPLICA — e ai o
    `Idempotency-Key` deixa de ser cortesia e vira obrigatorio (CONTRATOS §8).

    `etag_de` presente marca o comando como ATUALIZACAO: o pipeline passa a
    exigir `If-Match`. Ausente marca criacao, onde nao ha estado anterior contra
    o que comparar.
    """

    nome: str
    requires: tuple[Permissao, ...]
    schema: type[BaseModel]
    aplicar: Aplicador
    idempotent: bool = False
    confirm: bool = True
    etag_de: LeitorDeEtag | None = None


@dataclass(frozen=True, slots=True)
class Resultado:
    """Resposta do pipeline. `repetido` distingue efeito novo de replay.

    Quem chama precisa dessa distincao para a auditoria: repetir uma chave nao e'
    uma segunda escrita, e registrar como se fosse inflaria a trilha com eventos
    que nunca aconteceram.
    """

    dados: dict[str, Any]
    etag: str | None
    repetido: bool


class ErroDeComando(Exception):
    """Falha na aplicacao, ja' traduzida pelo comando. Nunca escapa do pipeline."""


def requires_de(cmd: Comando) -> tuple[Permissao, ...]:
    return cmd.requires


def sem_segredo(entrada: Mapping[str, Any]) -> dict[str, Any]:
    """Corpo pronto para a trilha de auditoria, sem campo sensivel.

    A trilha e' lida por quem audita, nao por quem operou. Copiar o corpo cru
    para dentro dela levaria junto qualquer campo que um comando futuro venha a
    aceitar — e a auditoria e' append-only, entao o vazamento nao teria correcao.
    """
    proibidos = {"senha", "senha_hash", "token", "csrf", "cookie"}
    return {k: v for k, v in entrada.items() if k.lower() not in proibidos}
