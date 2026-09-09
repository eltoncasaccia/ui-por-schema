"""`produto_saldo_por_unidade` — onde esta' o estoque de um produto.

RN-P01: o saldo e' sempre do lote, dentro de uma unidade. Este componente soma
os lotes de um produto POR UNIDADE, dentro do escopo do ator. Sem custo, para
papel nenhum: exige `lote.ler`, e nao toca `Produto.custo_unitario_centavos`.
"""

from pydantic import BaseModel

from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado

NOME_UNIDADE: dict[str, str] = {
    "cd-matriz": "CD Matriz",
    "cd-refrigerado": "CD Refrigerado",
    "filial-uberlandia": "Uberlândia",
}


class Params(BaseModel):
    produto_id: str


class LinhaUnidade(BaseModel):
    unidade_id: str
    unidade: str
    saldo: int
    # Lotes COM saldo — "3 lotes" some quando todos zeram, e' informacao de acao.
    lotes: int


class VM(BaseModel):
    produto_id: str
    nome: str
    ativo: bool
    total: int
    linhas: list[LinhaUnidade]


class Dados(BaseModel):
    produto_id: str
    nome: str
    ativo: bool
    linhas: list[LinhaUnidade]


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    produto = await ctx.repos.produto.por_id(params.produto_id, ctx.dados)
    if produto is None:
        raise nao_encontrado({"produto_id": params.produto_id, "ator": ctx.ator.id})

    lotes = await ctx.repos.lote.listar(ctx.dados, produto_id=params.produto_id)
    saldos = await ctx.repos.lote.saldos([lote.id for lote in lotes], ctx.dados)

    # unidade_id -> [saldo somado, lotes com saldo]. So' chegam aqui as unidades
    # do ator: a porta ja' intersectou (RN-A01), o `load` nao filtra escopo.
    acc: dict[str, list[int]] = {}
    for lote in lotes:
        s = saldos.get(lote.id, 0)
        par = acc.setdefault(lote.unidade_id, [0, 0])
        par[0] += s
        if s > 0:
            par[1] += 1

    linhas = [
        LinhaUnidade(unidade_id=u, unidade=NOME_UNIDADE.get(u, u), saldo=v[0], lotes=v[1])
        for u, v in acc.items()
    ]
    return Dados(
        produto_id=produto.id,
        nome=produto.nome,
        ativo=produto.ativo,
        linhas=linhas,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: a ordenacao e' estavel por unidade."""
    linhas = sorted(d.linhas, key=lambda x: x.unidade_id)
    return VM(
        produto_id=d.produto_id,
        nome=d.nome,
        ativo=d.ativo,
        total=sum(linha.saldo for linha in linhas),
        linhas=linhas,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="produto_saldo_por_unidade",
        label="Saldo por unidade",
        description=(
            "Mostra o saldo de um produto repartido por unidade: quanto ha' em "
            "cada CD ou filial do usuario, com a contagem de lotes com saldo. "
            "Use quando perguntarem onde esta' o estoque de um produto ou quanto "
            "tem em cada unidade. Para um lote especifico existe `lote_detalhe`."
        ),
        examples=(
            "onde tem estoque de dipirona",
            "quanto de amoxicilina tem em cada unidade",
            "o saldo desse produto por unidade",
        ),
        params=Params,
        requires="lote.ler",
        tamanho="meia",
        load=carregar,
        select=projetar,
    )
)
