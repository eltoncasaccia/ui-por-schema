"""`quarentena_fila` — o que espera a liberacao do RT.

`RN-R01`: todo recebimento entra em quarentena, e nao existe entrada direta em
estoque liberado. Esta fila e' a consequencia operacional disso — e' a lista de
trabalho de quem libera, e so' o RT libera (`RN-R02`).

**Por que o filtro e' pelo status REGISTRADO, e nao pelo efetivo.** Sao coisas
diferentes (ADR-0022): registrado e' o que alguem decidiu; efetivo e' o que
vale agora. Um lote em quarentena que passou da validade tem status efetivo
`vencido` — e continua esperando uma decisao humana, entao continua na fila.
Filtrar pelo efetivo o faria sumir daqui exatamente quando ele mais precisa
aparecer. A coluna de situacao mostra que ele venceu; a fila nao o esconde.
"""

from datetime import date

from pydantic import BaseModel

# O nome de exibicao das unidades vem de `lote_lista` em vez de ser copiado:
# duas tabelas com os mesmos tres nomes divergem no dia em que uma unidade
# muda de nome, e a divergencia aparece so' na tela.
from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.identidade import UnidadeId
from estoque.domain.regras.validade import (
    ClasseValidade,
    classificar_validade,
    dias_ate_vencer,
    status_efetivo,
)
from estoque.domain.tipos import ClasseProduto, Lote, StatusLoteEfetivo


class Params(BaseModel):
    # Unico recorte, e enum. A fila inteira e' curta por natureza: recortar
    # mais criaria a chance de esconder o que precisa de decisao.
    unidade_id: UnidadeId | None = None


class LinhaQuarentena(BaseModel):
    lote_id: str
    produto: str
    classe: ClasseProduto
    numero: str
    unidade: str
    fabricacao: date
    validade: date
    dias_restantes: int
    # Sem data de entrada em quarentena no modelo, a idade do lote e' o que ha'
    # — e ela e' dita pelo nome certo, em vez de virar um "aguarda ha" que o
    # dado nao sustenta.
    fabricado_ha_dias: int
    saldo: int
    situacao: ClasseValidade
    # ADR-0022: `quarentena` para quase todos, `vencido` para o que passou da
    # validade esperando. E' o que separa a fila normal do caso urgente.
    status_efetivo: StatusLoteEfetivo


class Faixa(BaseModel):
    rotulo: str
    valor: int
    ordem: int = 0


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05, ADR-0020)."""

    total: int
    escopo: str
    # Quantos ja' venceram esperando. E' o numero que muda a ordem do dia.
    vencidos: int
    linhas: list[LinhaQuarentena]
    resumo: list[Faixa] = []
    cursor: str | None = None
    tem_mais: bool = False


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    lotes: list[Lote]
    saldos: dict[str, int]
    nomes: dict[str, str]
    classes: dict[str, ClasseProduto]
    hoje: date
    total: int
    vencidos: int
    escopo: str
    resumo: list[Faixa]
    cursor: str | None = None
    tem_mais: bool = False


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    hoje = date.today()
    # `status="quarentena"` vai ao repositorio: e' status REGISTRADO, coluna
    # real, e a fila e' definida por decisao pendente, nao por derivacao.
    todos = list(
        await ctx.repos.lote.listar(
            ctx.dados, unidade_id=params.unidade_id, status="quarentena"
        )
    )
    saldos = await ctx.repos.lote.saldos([lote.id for lote in todos], ctx.dados)

    # Ordem da fila: o que vence antes precisa de decisao antes. O repositorio
    # ja' entrega ordenado por (validade, id), entao a ordem e' a do cursor.
    contagem: dict[str, int] = {}
    vencidos = 0
    for lote in todos:
        u = NOME_UNIDADE.get(lote.unidade_id, lote.unidade_id)
        contagem[u] = contagem.get(u, 0) + 1
        if dias_ate_vencer(lote, hoje) < 0:
            vencidos += 1

    inicio = 0
    if ctx.pagina.cursor:
        for i, lote in enumerate(todos):
            if f"{lote.validade.isoformat()}|{lote.id}" == ctx.pagina.cursor:
                inicio = i + 1
                break
    fatia = todos[inicio : inicio + ctx.pagina.limite]
    tem_mais = inicio + ctx.pagina.limite < len(todos)
    ultimo = fatia[-1] if fatia else None

    if params.unidade_id:
        escopo = NOME_UNIDADE.get(params.unidade_id, params.unidade_id)
    else:
        n = len(ctx.unidades_permitidas)
        escopo = f"{n} unidade{'s' if n != 1 else ''}"

    produtos = await ctx.repos.produto.por_ids([lote.produto_id for lote in fatia], ctx.dados)
    return Dados(
        lotes=fatia,
        saldos={lote.id: saldos.get(lote.id, 0) for lote in fatia},
        # Nome e classe, nada mais: `Produto` carrega custo para quem tem
        # `custo.ler`, e o que nao entra aqui nao chega ao viewmodel.
        nomes={pid: p.nome for pid, p in produtos.items()},
        classes={pid: p.classe for pid, p in produtos.items()},
        hoje=hoje,
        total=len(todos),
        vencidos=vencidos,
        escopo=escopo,
        # Unidade e' identidade, nao magnitude: sem rampa, sem `ordem`.
        resumo=[
            Faixa(rotulo=u, valor=v)
            for u, v in sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        cursor=f"{ultimo.validade.isoformat()}|{ultimo.id}" if ultimo and tem_mais else None,
        tem_mais=tem_mais,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: `hoje` chega pelo `Dados`."""
    return VM(
        total=d.total,
        escopo=d.escopo,
        vencidos=d.vencidos,
        linhas=[
            LinhaQuarentena(
                lote_id=lote.id,
                produto=d.nomes.get(lote.produto_id, lote.produto_id),
                classe=d.classes.get(lote.produto_id, "comum"),
                numero=lote.numero,
                unidade=lote.unidade_id,
                fabricacao=lote.fabricacao,
                validade=lote.validade,
                dias_restantes=dias_ate_vencer(lote, d.hoje),
                fabricado_ha_dias=(d.hoje - lote.fabricacao).days,
                saldo=d.saldos.get(lote.id, 0),
                situacao=classificar_validade(lote, d.hoje),
                status_efetivo=status_efetivo(lote, d.saldos.get(lote.id, 0), d.hoje),
            )
            for lote in d.lotes
        ],
        resumo=d.resumo,
        cursor=d.cursor,
        tem_mais=d.tem_mais,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="quarentena_fila",
        label="Quarentena",
        description=(
            "Lista os lotes parados em quarentena, esperando a liberação do "
            "responsável técnico, com produto, validade, saldo e há quanto tempo o "
            "lote existe, restrito às unidades do usuário. Use quando perguntarem o "
            "que está em quarentena, o que espera liberação, ou o que o RT precisa "
            "analisar. Só lista: a liberação em si é outra tela."
        ),
        examples=(
            "o que está em quarentena",
            "quais lotes esperam liberação",
            "tem alguma coisa parada esperando o RT",
        ),
        params=Params,
        requires="lote.ler",
        tamanho="inteira",
        load=carregar,
        select=projetar,
    )
)
