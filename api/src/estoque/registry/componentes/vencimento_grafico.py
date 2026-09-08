"""`vencimento_grafico` — a curva de vencimento ao longo do tempo.

POR QUE UM COMPONENTE NOVO, e nao um parametro do indicador:

O indicador responde "quantos?". Este responde "QUANDO?" — e sao perguntas
diferentes o bastante para pedirem formas diferentes. "12 lotes vencem em 90
dias" nao diz se sao 12 na semana que vem ou 12 espalhados no trimestre, e essa
e' exatamente a diferenca entre uma tarde de trabalho e uma perda de R$ 183 mil.

FORMA: barras verticais por quinzena. O eixo do tempo e' ordenado e continuo, e
a pergunta e' "onde estao os picos" — comparacao de magnitude ao longo de uma
sequencia. Nao e' pizza (nao e' parte-de-um-todo), nao e' linha (sao contagens
discretas por balde, nao uma serie continua).

COR: uma rampa sequencial de uma matiz, mais urgente = mais forte. Urgencia e'
magnitude. Duas matizes foram medidas e reprovadas — ver ADR do sistema de
design.

Custa 1 vaga do teto de 25 (ADR-0011). Passamos de 22 para 23, folga de 2.
"""

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel

from estoque.domain.identidade import UnidadeId
from estoque.domain.regras.validade import dias_ate_vencer
from estoque.registry.definir import ComponentDef, LoadContext
from estoque.registry.registry import registrar

NOME_UNIDADE: dict[str, str] = {
    "cd-matriz": "CD Matriz",
    "cd-refrigerado": "CD Refrigerado",
    "filial-uberlandia": "Uberlândia",
}


class Params(BaseModel):
    horizonte: Literal["90", "180", "365"] = "180"
    unidade_id: UnidadeId | None = None


class Balde(BaseModel):
    """Uma barra. `urgencia` posiciona na rampa: 0 tranquilo, 3 vencido."""

    rotulo: str
    inicio: str
    lotes: int
    unidades: int
    urgencia: int


class VM(BaseModel):
    horizonte_dias: int
    escopo: str
    total_lotes: int
    pico_rotulo: str | None
    baldes: list[Balde]
    legenda: list[str]


class Dados(BaseModel):
    horizonte_dias: int
    escopo: str
    baldes: list[Balde]


def _urgencia(dias: int) -> int:
    if dias < 0:
        return 3
    if dias <= 30:
        return 2
    if dias <= 90:
        return 1
    return 0


_MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    hoje = date.today()
    horizonte = int(params.horizonte)
    limite = hoje + timedelta(days=horizonte)
    lotes = list(
        await ctx.repos.lote.listar(
            ctx.dados, unidade_id=params.unidade_id, validade_ate=limite
        )
    )
    saldos = await ctx.repos.lote.saldos([lote.id for lote in lotes], ctx.dados)

    # Quinzenas ate' 180 dias; meses acima disso — senao viram 24 barras de 3px.
    passo = 15 if horizonte <= 180 else 30
    n = horizonte // passo
    baldes = [
        Balde(
            rotulo="",
            inicio=(hoje + timedelta(days=i * passo)).isoformat(),
            lotes=0,
            unidades=0,
            urgencia=0,
        )
        for i in range(n)
    ]
    for i, b in enumerate(baldes):
        inicio = date.fromisoformat(b.inicio)
        b.rotulo = f"{inicio.day:02d} {_MESES[inicio.month - 1]}"
        b.urgencia = _urgencia(i * passo)

    for lote in lotes:
        saldo = saldos.get(lote.id, 0)
        if saldo <= 0:
            continue
        dias = dias_ate_vencer(lote, hoje)
        i = max(0, min(n - 1, dias // passo))
        baldes[i].lotes += 1
        baldes[i].unidades += saldo

    escopo = (
        NOME_UNIDADE.get(params.unidade_id, params.unidade_id)
        if params.unidade_id
        else f"{len(ctx.unidades_permitidas)} unidades"
    )
    return Dados(horizonte_dias=horizonte, escopo=escopo, baldes=baldes)


def projetar(d: Dados) -> VM:
    pico = max(d.baldes, key=lambda b: b.lotes, default=None)
    return VM(
        horizonte_dias=d.horizonte_dias,
        escopo=d.escopo,
        total_lotes=sum(b.lotes for b in d.baldes),
        pico_rotulo=pico.rotulo if pico and pico.lotes > 0 else None,
        baldes=d.baldes,
        legenda=["vencidos", "até 30 dias", "31–90 dias", "acima de 90 dias"],
    )


COMPONENTE = registrar(
    ComponentDef(
        id="vencimento_grafico",
        label="Curva de vencimento",
        description=(
            "GRÁFICO de barras da quantidade de lotes que vence ao longo do tempo, "
            "por quinzena ou por mês, dentro do horizonte escolhido. Use SEMPRE que "
            "a pergunta mencionar gráfico, curva, evolução, distribuição, linha do "
            "tempo ou visualização — inclusive quando pedirem um panorama em forma "
            "de gráfico. Também é a escolha certa para QUANDO as coisas vencem, e "
            "não apenas quantas."
        ),
        examples=(
            "me mostre um gráfico do vencimento",
            "panorama do estoque em formato de gráfico",
            "como se distribuem os vencimentos ao longo do ano",
            "quando vencem os lotes",
        ),
        params=Params,
        requires="lote.ler",
        tamanho="inteira",
        load=carregar,
        select=projetar,
    )
)
