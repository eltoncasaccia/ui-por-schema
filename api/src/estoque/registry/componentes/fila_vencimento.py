"""`fila_vencimento` — CA-03. O episodio dos R$ 183 mil vencidos em prateleira.

Exemplo completo de um componente: params, permissao, carga autorizada, projecao
no servidor (ADR-0020) e o viewmodel que atravessa a rede.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from estoque.domain.identidade import UnidadeId
from estoque.domain.regras.validade import classificar_validade, dias_ate_vencer
from estoque.domain.tipos import Lote
from estoque.registry.definir import ComponentDef, LoadContext
from estoque.registry.registry import registrar


class Params(BaseModel):
    # Enum, nunca data livre: todo recorte que o usuario sabe pedir precisa
    # existir no catalogo como VALOR NOMEADO. Filtro que falta alarga a resposta
    # em silencio — o achado mais perigoso da v1 (risco R-5 do PRD).
    janela: Literal["30", "60", "90"] = "90"
    unidade_id: UnidadeId | None = None


class LinhaVencimento(BaseModel):
    lote_id: str
    produto: str
    numero: str
    unidade: str
    validade: date
    dias_restantes: int
    saldo: int
    situacao: Literal["ok", "alerta_90", "bloqueio_30", "vencido"]


class FaixaResumo(BaseModel):
    """Uma faixa da rampa de urgencia. `ordem` cresce com a urgencia."""

    rotulo: str
    valor: int
    ordem: int


class VM(BaseModel):
    """O viewmodel. E' EXATAMENTE isto que atravessa a rede — nada de `Lote`,
    nada de linha de banco, nada de custo (ADR-0020, CA-05)."""

    janela_dias: int
    total: int
    linhas: list[LinhaVencimento]
    # Distribuicao por urgencia: responde "quao ruim e' isso?" antes de a pessoa
    # ler linha por linha.
    resumo: list[FaixaResumo] = []
    # Paginacao. NAO e' param do componente — o modelo nunca escolhe pagina.
    cursor: str | None = None
    tem_mais: bool = False


PAGINA = 40


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    lotes: list[Lote]
    saldos: dict[str, int]
    nomes: dict[str, str]
    hoje: date
    janela_dias: int
    resumo: list[FaixaResumo]
    cursor: str | None = None
    tem_mais: bool = False


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    from datetime import timedelta

    hoje = date.today()
    limite = hoje + timedelta(days=int(params.janela))
    todos = list(
        await ctx.repos.lote.listar(
            ctx.dados, unidade_id=params.unidade_id, validade_ate=limite
        )
    )
    saldos_todos = await ctx.repos.lote.saldos([lote.id for lote in todos], ctx.dados)
    # So' entra na fila o que tem saldo — lote esgotado nao e' perda a evitar.
    com_saldo = [lote for lote in todos if saldos_todos.get(lote.id, 0) > 0]

    # O resumo cobre a fila INTEIRA, nao a pagina: um resumo que muda ao rolar
    # nao e' resumo.
    faixas = [
        FaixaResumo(rotulo="61–90 dias", valor=0, ordem=0),
        FaixaResumo(rotulo="31–60 dias", valor=0, ordem=1),
        FaixaResumo(rotulo="até 30 dias", valor=0, ordem=2),
        FaixaResumo(rotulo="vencidos", valor=0, ordem=3),
    ]
    for lote in com_saldo:
        d = dias_ate_vencer(lote, hoje)
        faixas[3 if d < 0 else 2 if d <= 30 else 1 if d <= 60 else 0].valor += 1

    # Cursor estavel: a lista ja' vem ordenada por (validade, id) do repositorio.
    inicio = 0
    if ctx.pagina.cursor:
        for i, lote in enumerate(com_saldo):
            if f"{lote.validade.isoformat()}|{lote.id}" == ctx.pagina.cursor:
                inicio = i + 1
                break
    tamanho = ctx.pagina.limite
    fatia = com_saldo[inicio : inicio + tamanho]
    tem_mais = inicio + tamanho < len(com_saldo)
    ultimo = fatia[-1] if fatia else None
    cursor = f"{ultimo.validade.isoformat()}|{ultimo.id}" if ultimo and tem_mais else None

    produtos = await ctx.repos.produto.por_ids([lote.produto_id for lote in fatia], ctx.dados)
    return Dados(
        lotes=fatia,
        saldos={lote.id: saldos_todos.get(lote.id, 0) for lote in fatia},
        nomes={pid: p.nome for pid, p in produtos.items()},
        hoje=hoje,
        janela_dias=int(params.janela),
        resumo=[f for f in faixas if f.valor > 0],
        cursor=cursor,
        tem_mais=tem_mais,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: sem I/O, sem relogio."""
    linhas = [
        LinhaVencimento(
            lote_id=lote.id,
            produto=d.nomes.get(lote.produto_id, lote.produto_id),
            numero=lote.numero,
            unidade=lote.unidade_id,
            validade=lote.validade,
            dias_restantes=dias_ate_vencer(lote, d.hoje),
            saldo=d.saldos.get(lote.id, 0),
            situacao=classificar_validade(lote, d.hoje),
        )
        for lote in d.lotes
    ]
    linhas.sort(key=lambda x: (x.validade, x.lote_id))
    return VM(
        janela_dias=d.janela_dias,
        total=sum(f.valor for f in d.resumo),
        linhas=linhas,
        resumo=d.resumo,
        cursor=d.cursor,
        tem_mais=d.tem_mais,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="fila_vencimento",
        label="Fila de vencimento",
        description=(
            "Lista os lotes que vencem dentro de uma janela de 30, 60 ou 90 dias, "
            "com saldo, validade e dias restantes, apenas das unidades do usuario. "
            "Use quando perguntarem o que esta vencendo, o que vence em breve, ou "
            "o que precisa de atencao por validade."
        ),
        # Exemplos SEM nome de unidade: uma unidade citada aqui pode nao ser
        # do ator, e o catalogo e' o vocabulario DELE. Sugerir o que ele nao
        # pode pedir e' oferecer uma porta fechada.
        examples=(
            "o que vence nos próximos 90 dias",
            "quais lotes preciso escoar primeiro",
            "o que vence nos próximos 30 dias",
        ),
        params=Params,
        requires="lote.ler",
        tamanho="inteira",
        load=carregar,
        select=projetar,
    )
)
