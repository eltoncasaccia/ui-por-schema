"""`/api/componentes/{id}/dados` — o TERCEIRO momento de autorizacao, o unico
que garante (ADR-0004). E' o endpoint que um cliente forjando schema atinge
direto, sem passar pelo modelo.
"""

from typing import Any

from fastapi import APIRouter, Cookie
from pydantic import BaseModel, Field

from estoque.application.registry.definir import LoadContext, Pagina, permissoes_base
from estoque.application.registry.registry import buscar, valores_proibidos
from estoque.auditoria import registro as aud
from estoque.autorizacao.motor import (
    autorizar_ou_falhar,
    autorizar_params_ou_falhar,
    autorizar_unidade_do_param,
)
from estoque.data.porta import ContextoDados
from estoque.domain.erros import ErroDominio
from estoque.server.deps import Tx, ator_ou_falhar, motor, ok, repos

rotas = APIRouter()


class PaginaPedido(BaseModel):
    limite: int = Field(default=20, ge=1, le=200)
    cursor: str | None = None


class PedidoDados(BaseModel):
    params: dict[str, Any] = {}
    # FORA de `params`: paginacao e' transporte, e o modelo nunca a escolhe.
    pagina: PaginaPedido = PaginaPedido()


@rotas.post("/api/componentes/{componente_id}/dados")
async def dados(
    componente_id: str, corpo: PedidoDados, sessao: str | None = Cookie(default=None)
) -> dict[str, Any]:
    """O TERCEIRO momento de autorizacao — o unico que garante (ADR-0004).

    Mesmo que a composicao ja' tenha sido validada, aqui a permissao e'
    reconferida por registro, com a identidade real. E' este endpoint que um
    cliente forjando schema atingiria direto, sem passar pelo modelo.
    """
    async with motor.connect() as c:
        ator = await ator_ou_falhar(c, sessao)
        comp = buscar(componente_id)
        if comp is None:
            raise ErroDominio("nao_encontrado", "Registro nao encontrado.")

        autorizar_ou_falhar(ator, permissoes_base(comp.requires), "este componente")
        # RequiresPorValor: permissao que depende do VALOR do param. Sem esta
        # linha, um schema forjado passa pela permissao base e o `load` roda.
        autorizar_params_ou_falhar(valores_proibidos(comp, ator), corpo.params)
        # ADR-0014: unidade pedida fora do escopo nega, nao devolve vazio.
        autorizar_unidade_do_param(ator, corpo.params.get("unidade_id"))

        params = comp.params.model_validate(corpo.params)
        ctx_dados = ContextoDados(ator=ator, unidades_permitidas=ator.unidades, tx=Tx(c))
        ctx = LoadContext(
            ator=ator,
            unidades_permitidas=ator.unidades,
            repos=repos(c),
            dados=ctx_dados,
            pagina=Pagina(limite=corpo.pagina.limite, cursor=corpo.pagina.cursor),
        )
        carga = await comp.load(params, ctx)
        # T-050: o MESMO etag que a escrita recalcula para o `If-Match` — sem
        # isto, comando com `etag_de` nunca tem o que comparar (achado A-41).
        etag = comp.etag(carga) if comp.etag else None
        # ADR-0020: `select` roda AQUI. So' o viewmodel atravessa a rede.
        vm = comp.select(carga)

    async with motor.begin() as c2:
        await aud.registrar(
            c2,
            ator_id=ator.id,
            acao="ler",
            origem="assistente",
            entidade=componente_id,
            valor_novo={"params": corpo.params},
        )
    return ok(vm.model_dump(mode="json"), etag=etag)
