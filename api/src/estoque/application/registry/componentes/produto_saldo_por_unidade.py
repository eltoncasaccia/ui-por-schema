"""`produto_saldo_por_unidade` — onde esta' o estoque de um produto, e se basta.

RN-P01: o saldo e' sempre do lote, dentro de uma unidade. Este componente soma
os lotes de um produto POR UNIDADE, dentro do escopo do ator. Sem custo, para
papel nenhum: exige `lote.ler`, e nao toca `Produto.custo_unitario_centavos`.

RN-P06 (T-046): a faixa de minimo e maximo e' do par (produto, unidade), e e'
aqui que ela aparece — a ficha do produto nao tem eixo de unidade onde pendura-la.
"""

from pydantic import BaseModel

from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.tipos import FaixaEstoque

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
    # Nulos quando a unidade nao tem faixa: sem minimo, "abaixo" nao quer dizer nada.
    minimo: int | None = None
    maximo: int | None = None
    abaixo_do_minimo: bool = False


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
    faixas: dict[str, FaixaEstoque] = {
        str(u): f
        for u, f in (await ctx.repos.produto.faixas(params.produto_id, ctx.dados)).items()
    }

    # unidade_id -> [saldo somado, lotes com saldo]. So' chegam aqui as unidades
    # do ator: a porta ja' intersectou (RN-A01), o `load` nao filtra escopo.
    # Unidade com faixa e sem lote tambem entra: saldo zero abaixo do minimo e'
    # o alerta que mais importa.
    acc: dict[str, list[int]] = {u: [0, 0] for u in faixas}
    for lote in lotes:
        s = saldos.get(lote.id, 0)
        par = acc.setdefault(lote.unidade_id, [0, 0])
        par[0] += s
        if s > 0:
            par[1] += 1

    linhas = []
    for u, (saldo, n) in acc.items():
        f = faixas.get(u)
        linhas.append(
            LinhaUnidade(
                unidade_id=u,
                unidade=NOME_UNIDADE.get(u, u),
                saldo=saldo,
                lotes=n,
                minimo=f.minimo if f else None,
                maximo=f.maximo if f else None,
                abaixo_do_minimo=f is not None and saldo < f.minimo,
            )
        )
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
            "cada CD ou filial do usuario, com a contagem de lotes com saldo e a "
            "faixa de estoque minimo e maximo de cada unidade, marcando o que "
            "esta' abaixo do minimo. Use quando perguntarem onde esta' o estoque "
            "de um produto ou se ele basta em cada unidade. Para um lote "
            "especifico existe `lote_detalhe`."
        ),
        examples=(
            "onde tem estoque de dipirona",
            "quanto de amoxicilina tem em cada unidade",
            "esse produto esta' abaixo do minimo em alguma unidade",
        ),
        params=Params,
        requires="lote.ler",
        tamanho="meia",
        load=carregar,
        select=projetar,
    )
)
