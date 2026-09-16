"""O nucleo que toda rota usa: a conexao, a identidade, o envelope.

Fica FORA de `app.py` para que os routers nao importem a aplicacao — se
importassem, `app.py` teria que importa-los de volta para registra-los, e o
ciclo so' se resolveria com import tardio dentro de funcao.

`motor`, `CFG` e `OBS` sao criados na importacao deste modulo, e `app.py` os
reexporta: `estoque.server.app.CFG` e `_engine` continuam existindo, apontando
para o MESMO objeto.
"""

from typing import Any

from argon2 import PasswordHasher
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from estoque.application.registry.definir import (
    ComponentDef,
    LoadContext,
    Pagina,
    permissoes_base,
)
from estoque.application.registry.registry import buscar, valores_proibidos
from estoque.application.schema.contrato import Bloco
from estoque.assistant.langfuse_obs import criar as criar_observador
from estoque.assistant.observador import Observador, ObservadorNulo
from estoque.autorizacao.motor import (
    autorizar_ou_falhar,
    autorizar_params_ou_falhar,
    autorizar_unidade_do_param,
)
from estoque.data.porta import ContextoDados, Repositorios
from estoque.data.repositorios import (
    RepoAuditoriaSQL,
    RepoLoteSQL,
    RepoMovimentoSQL,
    RepoProdutoSQL,
    RepoRecebimentoSQL,
    RepoTemperaturaSQL,
)
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator
from estoque.server import sessao as ses
from estoque.server.config import Config

CFG = Config.do_ambiente()
# Nulo quando nao ha chave do LangFuse: telemetria e' opcional por construcao.
OBS: Observador = criar_observador() or ObservadorNulo()
PH = PasswordHasher()
motor = create_async_engine(CFG.database_url, future=True, pool_pre_ping=True)


def ok(dados: Any, **meta: Any) -> dict[str, Any]:
    return {"ok": True, "dados": dados, "meta": meta}


async def ator_ou_falhar(conn: AsyncConnection, sid: str | None) -> Ator:
    if not sid:
        raise ErroDominio("nao_autenticado", "Sessao ausente.")
    ator = await ses.ator_da_sessao(conn, sid)
    if ator is None:
        raise ErroDominio("nao_autenticado", "Sessao invalida ou expirada.")
    return ator


def repos(conn: AsyncConnection) -> Repositorios:
    return Repositorios(
        lote=RepoLoteSQL(conn),
        produto=RepoProdutoSQL(conn),
        movimento=RepoMovimentoSQL(conn),
        auditoria=RepoAuditoriaSQL(conn),
        recebimento=RepoRecebimentoSQL(conn),
        temperatura=RepoTemperaturaSQL(conn),
    )


class Tx:
    def __init__(self, c: AsyncConnection) -> None:
        self._c = c

    async def commit(self) -> None:
        await self._c.commit()

    async def rollback(self) -> None:
        await self._c.rollback()


async def ler_componente(
    c: AsyncConnection,
    ator: Ator,
    componente_id: str,
    params_brutos: dict[str, Any],
    pagina: Pagina,
) -> tuple[ComponentDef, BaseModel, str | None]:
    """O TERCEIRO momento de autorizacao (ADR-0004), num lugar so'.

    `dados` e `exportar` passam por aqui. Se cada router tivesse a sua copia,
    a exportacao seria o atalho: a checagem esquecida numa das duas e' um
    arquivo com o que a tela recusaria. Devolve componente, viewmodel e etag.
    """
    comp = buscar(componente_id)
    if comp is None:
        raise ErroDominio("nao_encontrado", "Registro nao encontrado.")

    autorizar_ou_falhar(ator, permissoes_base(comp.requires), "este componente")
    # RequiresPorValor: permissao que depende do VALOR do param. Sem esta
    # linha, um schema forjado passa pela permissao base e o `load` roda.
    autorizar_params_ou_falhar(valores_proibidos(comp, ator), params_brutos)
    # ADR-0014: unidade pedida fora do escopo nega, nao devolve vazio.
    autorizar_unidade_do_param(ator, params_brutos.get("unidade_id"))

    params = comp.params.model_validate(params_brutos)
    ctx_dados = ContextoDados(ator=ator, unidades_permitidas=ator.unidades, tx=Tx(c))
    ctx = LoadContext(
        ator=ator,
        unidades_permitidas=ator.unidades,
        repos=repos(c),
        dados=ctx_dados,
        pagina=pagina,
    )
    carga = await comp.load(params, ctx)
    # T-050: o MESMO etag que a escrita recalcula para o `If-Match` — sem
    # isto, comando com `etag_de` nunca tem o que comparar (achado A-41).
    etag = comp.etag(carga) if comp.etag else None
    # ADR-0020: `select` roda AQUI. So' o viewmodel atravessa a rede.
    return comp, comp.select(carga), etag


def tamanho(tipo: str) -> str:
    c = buscar(tipo)
    return c.tamanho if c else "inteira"


def bloco_resposta(b: Bloco) -> dict[str, Any]:
    """O bloco tal como atravessa a rede — CONTRATOS §6/§8.

    `comandos` so aparece quando o componente DECLARA `commands`: ausencia, nao
    dict vazio, e' o que deixa os 15 componentes de leitura do jeito que
    sempre estiveram (T-049, achado A-40). Sem `schema` do `CommandDef` — o
    servidor revalida a entrada de qualquer forma (RN-A03), e mandar o schema
    seria mandar dado que a view nunca le.
    """
    c = buscar(b.tipo)
    d: dict[str, Any] = {
        "tipo": b.tipo,
        "params": b.params,
        "tamanho": c.tamanho if c else "inteira",
    }
    if c and c.commands:
        d["comandos"] = {
            nome: {
                "endpoint": cmd.endpoint,
                "confirm": cmd.confirm,
                "idempotent": cmd.idempotent,
            }
            for nome, cmd in c.commands.items()
        }
    return d
