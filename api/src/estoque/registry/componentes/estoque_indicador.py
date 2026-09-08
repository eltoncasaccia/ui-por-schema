"""`estoque_indicador` — um numero COM contexto.

Um numero sozinho e' uma metrica sem contexto: "3" nao diz de onde, nao diz se
e' muito, e nao diz o que fazer. Este componente responde a pergunta seguinte
antes de ela ser feita:

  - de que escopo estamos falando (quantas unidades)
  - como o numero se reparte (a decomposicao)
  - o que nele exige acao (o detalhe)

Cor: as faixas de vencimento sao uma RAMPA SEQUENCIAL de uma matiz so'. Urgencia
e' magnitude, nao identidade — e rampa separa por luminosidade, que toda forma de
daltonismo preserva. Duas matizes (ambar/laranja) foram testadas e reprovadas:
delta-E 0.4 para deuteranopia no tema claro, ou seja, indistinguiveis.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from estoque.domain.identidade import UnidadeId
from estoque.domain.regras.validade import classificar_validade, dias_ate_vencer
from estoque.registry.definir import ComponentDef, LoadContext, RequiresPorValor
from estoque.registry.registry import registrar

Metrica = Literal[
    "lotes_em_quarentena",
    "lotes_vencendo_90d",
    "lotes_bloqueados",
    "valor_em_estoque",
]

NOME_UNIDADE: dict[str, str] = {
    "cd-matriz": "CD Matriz",
    "cd-refrigerado": "CD Refrigerado",
    "filial-uberlandia": "Uberlândia",
}


class Params(BaseModel):
    metrica: Metrica
    unidade_id: UnidadeId | None = None


class Faixa(BaseModel):
    """Um pedaco da decomposicao. `ordem` posiciona na rampa sequencial."""

    rotulo: str
    valor: int
    ordem: int = 0


class VM(BaseModel):
    metrica: Metrica
    rotulo: str
    valor: int
    unidade_medida: Literal["lotes", "centavos"]
    escopo: str
    detalhe: str | None = None
    faixas: list[Faixa] = []
    tipo_faixa: Literal["urgencia", "unidade", "nenhum"] = "nenhum"


class Dados(BaseModel):
    metrica: Metrica
    valor: int
    escopo: str
    detalhe: str | None
    faixas: list[Faixa]
    tipo_faixa: Literal["urgencia", "unidade", "nenhum"]


_ROTULOS: dict[str, str] = {
    "lotes_em_quarentena": "Em quarentena",
    "lotes_vencendo_90d": "Vencendo em 90 dias",
    "lotes_bloqueados": "Bloqueados",
    "valor_em_estoque": "Valor em estoque",
}


def _escopo(params: Params, ctx: LoadContext) -> str:
    if params.unidade_id:
        return NOME_UNIDADE.get(params.unidade_id, params.unidade_id)
    n = len(ctx.unidades_permitidas)
    return f"{n} unidade{'s' if n != 1 else ''}"


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    hoje = date.today()
    lotes = list(await ctx.repos.lote.listar(ctx.dados, unidade_id=params.unidade_id))
    saldos = await ctx.repos.lote.saldos([x.id for x in lotes], ctx.dados)
    escopo = _escopo(params, ctx)

    def por_unidade(selecao: list[str]) -> list[Faixa]:
        cont: dict[str, int] = {}
        for lote in lotes:
            if lote.id in selecao:
                cont[lote.unidade_id] = cont.get(lote.unidade_id, 0) + 1
        return [
            Faixa(rotulo=NOME_UNIDADE.get(u, u), valor=v)
            for u, v in sorted(cont.items(), key=lambda kv: -kv[1])
        ]

    if params.metrica == "lotes_em_quarentena":
        sel = [x.id for x in lotes if x.status == "quarentena"]
        # O detalhe que gera acao: ha' quanto tempo o mais antigo espera o RT.
        espera = max(((hoje - x.fabricacao).days for x in lotes if x.id in sel), default=0)
        return Dados(
            metrica=params.metrica,
            valor=len(sel),
            escopo=escopo,
            detalhe=(f"o mais antigo aguarda liberação há {espera} dias" if sel else None),
            faixas=por_unidade(sel),
            tipo_faixa="unidade",
        )

    if params.metrica == "lotes_bloqueados":
        sel = [x.id for x in lotes if x.status == "bloqueado"]
        return Dados(
            metrica=params.metrica,
            valor=len(sel),
            escopo=escopo,
            detalhe="somente o RT desbloqueia" if sel else None,
            faixas=por_unidade(sel),
            tipo_faixa="unidade",
        )

    if params.metrica == "lotes_vencendo_90d":
        # Rampa sequencial: quanto menor a janela, mais urgente.
        faixas = [
            Faixa(rotulo="61–90 dias", valor=0, ordem=0),
            Faixa(rotulo="31–60 dias", valor=0, ordem=1),
            Faixa(rotulo="até 30 dias", valor=0, ordem=2),
        ]
        total = 0
        for lote in lotes:
            if saldos.get(lote.id, 0) <= 0:
                continue
            if classificar_validade(lote, hoje) not in {"alerta_90", "bloqueio_30"}:
                continue
            total += 1
            d = dias_ate_vencer(lote, hoje)
            faixas[2 if d <= 30 else 1 if d <= 60 else 0].valor += 1
        return Dados(
            metrica=params.metrica,
            valor=total,
            escopo=escopo,
            detalhe=(
                f"{faixas[2].valor} "
                + ("bloqueia" if faixas[2].valor == 1 else "bloqueiam")
                + " automaticamente em 30 dias"
                if faixas[2].valor
                else None
            ),
            faixas=faixas,
            tipo_faixa="urgencia",
        )

    # valor_em_estoque — so' chega aqui quem tem custo.ler
    produtos = await ctx.repos.produto.por_ids([x.produto_id for x in lotes], ctx.dados)
    total_c = 0
    em_risco = 0
    for lote in lotes:
        p = produtos.get(lote.produto_id)
        if p is None or p.custo_unitario_centavos is None:
            continue
        v = saldos.get(lote.id, 0) * p.custo_unitario_centavos
        total_c += v
        if classificar_validade(lote, hoje) in {"alerta_90", "bloqueio_30", "vencido"}:
            em_risco += v
    return Dados(
        metrica=params.metrica,
        valor=total_c,
        escopo=escopo,
        detalhe=(
            f"R$ {em_risco / 100:,.0f} em lotes vencendo ou vencidos".replace(",", ".")
            if em_risco
            else None
        ),
        faixas=[],
        tipo_faixa="nenhum",
    )


def projetar(d: Dados) -> VM:
    return VM(
        metrica=d.metrica,
        rotulo=_ROTULOS[d.metrica],
        valor=d.valor,
        unidade_medida="centavos" if d.metrica == "valor_em_estoque" else "lotes",
        escopo=d.escopo,
        detalhe=d.detalhe,
        faixas=d.faixas,
        tipo_faixa=d.tipo_faixa,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="estoque_indicador",
        label="Indicador",
        # A descricao NAO enumera as metricas: o enum de params ja' as lista, e
        # ele e' FILTRADO por permissao. Repetir em prosa vazaria para o catalogo
        # de quem nao pode um valor que ele nao pode propor.
        description=(
            "Mostra UM NÚMERO do estoque para a métrica escolhida em `metrica`, "
            "com a decomposição por unidade ou por faixa de urgência, sempre restrito "
            "às unidades do usuário. Use quando a resposta é uma quantidade ou um "
            "total. NÃO use quando pedirem gráfico, curva, evolução ou distribuição "
            "ao longo do tempo — para isso existe `vencimento_grafico`, inclusive "
            "quando a pergunta for por um panorama em forma de gráfico."
        ),
        # Exemplos SEM nome de unidade: uma unidade citada aqui pode nao pertencer
        # a quem esta' perguntando, e o catalogo e' o vocabulario DELE.
        examples=(
            "quantos lotes estão em quarentena",
            "quanto tem bloqueado",
            "me dê um panorama do estoque",
            "qual o total em quarentena",
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
