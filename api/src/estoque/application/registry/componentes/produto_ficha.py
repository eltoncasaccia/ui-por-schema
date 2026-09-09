"""`produto_ficha` — a identidade do produto, e o custo so' para quem pode.

O custo unitario NAO e' campo condicional dentro do mesmo componente: e' um
VALOR de param (`variante="com_custo"`) que o catalogo REMOVE de quem nao tem
`custo.ler` — mesmo mecanismo do `valor_em_estoque` no `estoque_indicador`
(achado A-05). Cleide continua vendo a ficha; o que ela nao ve e' a opcao de
trazer o custo, entao o modelo nao consegue nem propor.

RN-P01: produto nao tem saldo. O `saldo_total` daqui e' a soma dos lotes do
produto DENTRO do escopo do ator, e existe para RN-P05 — produto inativo
continua visivel, com saldo, ate' esgotar.
"""

from typing import Any, Literal

from pydantic import BaseModel, SerializerFunctionWrapHandler, model_serializer

from estoque.application.registry.definir import (
    ComponentDef,
    LoadContext,
    RequiresPorValor,
)
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.tipos import ClasseProduto, CurvaAbc


class Params(BaseModel):
    # Identificador, nao recorte: nao ha' enum para um id. O que protege aqui e'
    # o `por_id` do repositorio, nao a validacao do param.
    produto_id: str
    # `com_custo` some do enum de quem nao tem `custo.ler` (A-05). Nao e' campo
    # condicional no viewmodel — e' opcao de catalogo que nem chega ao modelo.
    variante: Literal["padrao", "com_custo"] = "padrao"


class VM(BaseModel):
    """E' EXATAMENTE isto que atravessa a rede.

    `custo_unitario_centavos` so' aparece quando pedido E permitido — nos demais
    casos a chave fica AUSENTE (CA-05, AC-1), nunca `null`: `null` ainda
    revelaria que o campo existe.
    """

    produto_id: str
    nome: str
    ean: str
    fabricante: str
    principio_ativo: str
    classe: ClasseProduto
    curva_abc: CurvaAbc
    ativo: bool
    # RN-P01: nao e' "saldo do produto" — e' a soma dos lotes no escopo do ator.
    saldo_total: int
    custo_unitario_centavos: int | None = None

    @model_serializer(mode="wrap")
    def _omitir_custo_ausente(self, nxt: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # A borda serializa com `model_dump(mode="json")`, que emite `None` como
        # `null`. O AC-1 exige a chave AUSENTE. A remocao vive aqui para valer em
        # toda serializacao — resposta da borda e exportacao (AC-5).
        dados: dict[str, Any] = nxt(self)
        if self.custo_unitario_centavos is None:
            dados.pop("custo_unitario_centavos", None)
        return dados


class Dados(BaseModel):
    produto_id: str
    nome: str
    ean: str
    fabricante: str
    principio_ativo: str
    classe: ClasseProduto
    curva_abc: CurvaAbc
    ativo: bool
    saldo_total: int
    custo_unitario_centavos: int | None


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    produto = await ctx.repos.produto.por_id(params.produto_id, ctx.dados)
    if produto is None:
        # Produto nao e' escopo de unidade: `None` aqui e' so' inexistente. O id
        # vai ao `detalhe_interno` (log), nunca a resposta (ADR-0014).
        raise nao_encontrado({"produto_id": params.produto_id, "ator": ctx.ator.id})

    lotes = await ctx.repos.lote.listar(ctx.dados, produto_id=params.produto_id)
    saldos = await ctx.repos.lote.saldos([lote.id for lote in lotes], ctx.dados)

    # Custo so' quando pedido E disponivel. A porta ja' OMITE o campo para quem
    # nao tem `custo.ler` (RN-A02) — nesse caso `custo_unitario_centavos` chega
    # `None` aqui, e o valor `com_custo` ja' foi barrado no catalogo e na
    # revalidacao de schema. Sao tres barreiras; esta e' a ultima.
    custo = produto.custo_unitario_centavos if params.variante == "com_custo" else None

    return Dados(
        produto_id=produto.id,
        nome=produto.nome,
        ean=produto.ean,
        fabricante=produto.fabricante,
        principio_ativo=produto.principio_ativo,
        classe=produto.classe,
        curva_abc=produto.curva_abc,
        ativo=produto.ativo,
        saldo_total=sum(saldos.values()),
        custo_unitario_centavos=custo,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: sem I/O, sem relogio."""
    return VM(
        produto_id=d.produto_id,
        nome=d.nome,
        ean=d.ean,
        fabricante=d.fabricante,
        principio_ativo=d.principio_ativo,
        classe=d.classe,
        curva_abc=d.curva_abc,
        ativo=d.ativo,
        saldo_total=d.saldo_total,
        custo_unitario_centavos=d.custo_unitario_centavos,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="produto_ficha",
        label="Ficha do produto",
        # A descricao NAO menciona custo: o valor `com_custo` e' filtrado por
        # permissao, e citar em prosa o que o filtro removeu vaza pela porta dos
        # fundos (test_descricao_nunca_enumera_valor_de_enum_filtrado).
        description=(
            "Mostra os dados de um produto pelo identificador: nome, EAN, "
            "fabricante, principio ativo, classe regulatoria, curva ABC, se "
            "esta' ativo e o saldo somado das unidades do usuario. Use quando a "
            "pergunta e' sobre um produto ja' identificado, nao sobre lotes."
        ),
        examples=(
            "ficha da amoxicilina",
            "dados cadastrais desse produto",
            "esse produto ainda esta' ativo",
        ),
        params=Params,
        requires=RequiresPorValor(
            base=("produto.ler",),
            por_valor={"variante": {"com_custo": ("custo.ler",)}},
        ),
        tamanho="meia",
        load=carregar,
        select=projetar,
    )
)
