"""`estoque_indicador` — o componente que expos o achado A-05 da auditoria.

`requires` era declarado obrigatorio E estatico em CONTRATOS. Este componente
nao cabia: a metrica `valor_em_estoque` exige `custo.ler`, as outras nao.

Resolucao (ADR/achado A-05): `RequiresPorValor`. O catalogo REMOVE o valor do
enum para quem nao tem a permissao — Cleide nao ve `valor_em_estoque`, e o
modelo nao consegue nem propor.

E o inegociavel numero 3 da arquitetura vale aqui com forca: o componente recebe
uma METRICA e a calcula. Nunca recebe O NUMERO. Um componente que aceitasse
valor literal renderizaria alucinacao com a mesma cara de verdade.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from estoque.domain.identidade import UnidadeId
from estoque.domain.regras.validade import classificar_validade
from estoque.registry.definir import ComponentDef, LoadContext, RequiresPorValor
from estoque.registry.registry import registrar

Metrica = Literal[
    "lotes_em_quarentena",
    "lotes_vencendo_90d",
    "lotes_bloqueados",
    "valor_em_estoque",  # exige custo.ler
]


class Params(BaseModel):
    metrica: Metrica
    unidade_id: UnidadeId | None = None


class VM(BaseModel):
    metrica: Metrica
    rotulo: str
    valor: int
    unidade_medida: Literal["lotes", "centavos"]


class Dados(BaseModel):
    metrica: Metrica
    valor: int


_ROTULOS: dict[str, str] = {
    "lotes_em_quarentena": "Lotes em quarentena",
    "lotes_vencendo_90d": "Vencendo em 90 dias",
    "lotes_bloqueados": "Lotes bloqueados",
    "valor_em_estoque": "Valor em estoque",
}


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    hoje = date.today()
    lotes = list(await ctx.repos.lote.listar(ctx.dados, unidade_id=params.unidade_id))
    saldos = await ctx.repos.lote.saldos([x.id for x in lotes], ctx.dados)

    if params.metrica == "lotes_em_quarentena":
        valor = sum(1 for x in lotes if x.status == "quarentena")
    elif params.metrica == "lotes_bloqueados":
        valor = sum(1 for x in lotes if x.status == "bloqueado")
    elif params.metrica == "lotes_vencendo_90d":
        valor = sum(
            1
            for x in lotes
            if classificar_validade(x, hoje) in {"alerta_90", "bloqueio_30"}
            and saldos.get(x.id, 0) > 0
        )
    else:  # valor_em_estoque — so' chega aqui quem tem custo.ler
        produtos = await ctx.repos.produto.por_ids([x.produto_id for x in lotes], ctx.dados)
        valor = sum(
            saldos.get(x.id, 0) * (produtos[x.produto_id].custo_unitario_centavos or 0)
            for x in lotes
            if x.produto_id in produtos
        )
    return Dados(metrica=params.metrica, valor=valor)


def projetar(d: Dados) -> VM:
    return VM(
        metrica=d.metrica,
        rotulo=_ROTULOS[d.metrica],
        valor=d.valor,
        unidade_medida="centavos" if d.metrica == "valor_em_estoque" else "lotes",
    )


COMPONENTE = registrar(
    ComponentDef(
        id="estoque_indicador",
        label="Indicador",
        # ATENCAO: esta descricao NAO enumera as metricas disponiveis, e isso e'
        # deliberado. O enum `params.metrica.valores` ja' as lista, e ele e'
        # FILTRADO por permissao. Repetir os valores em prosa vazaria para o
        # catalogo de Cleide que existe um valor em estoque — ensinando o modelo
        # a tentar algo que ela nao pode ver (CA-05).
        #
        # Invariante: descricao descreve o COMPONENTE; o enum descreve as OPCOES.
        description=(
            "Mostra um numero unico do estoque para a metrica escolhida em `metrica`, "
            "sempre restrito as unidades do usuario. Use para responder perguntas de "
            "contagem, de total, ou para compor um panorama com varios indicadores."
        ),
        examples=(
            "quantos lotes estao em quarentena",
            "quanto tem bloqueado",
            "panorama do CD Matriz",
        ),
        params=Params,
        requires=RequiresPorValor(
            base=("lote.ler",),
            por_valor={"metrica": {"valor_em_estoque": ("custo.ler",)}},
        ),
        tamanho="linha",
        load=carregar,
        select=projetar,
    )
)
