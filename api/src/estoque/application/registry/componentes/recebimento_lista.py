"""`recebimento_lista` — o que entrou, e em que estado da conferencia esta.

Base de leitura para o formulario de registro (T-026). Duas decisoes carregam
o arquivo:

1. **Recorte e' valor nomeado.** `periodo` e' enum de dias, nao `de`/`ate`
   soltos. A tarefa pedia as duas datas; data livre convida o modelo a inventar
   recorte, e filtro que falta alarga a resposta EM SILENCIO (risco R-5 do PRD).
   O irmao `movimento_lista` ja' resolveu assim. O viewmodel devolve `recorte`
   para o corte ficar visivel na resposta.

2. **A divergencia aparece na lista, nao so' no detalhe** (`RN-R04`). Uma
   pendencia aberta e' o que trava a conclusao do recebimento; quem varre a
   lista precisa ver onde ela esta' sem abrir um por um.
"""

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel

from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.identidade import UnidadeId
from estoque.domain.tipos import Recebimento

StatusRecebimento = Literal["rascunho", "conferido", "liberado"]

ROTULO_STATUS: dict[StatusRecebimento, str] = {
    "rascunho": "Rascunho",
    "conferido": "Conferido",
    "liberado": "Liberado",
}

# Recorte por enum, nunca por data solta (risco R-5). `None` = todo o periodo.
DIAS: dict[str, int | None] = {"7": 7, "30": 30, "90": 90, "365": 365, "tudo": None}


class Params(BaseModel):
    unidade_id: UnidadeId | None = None
    # Enum fechado: valor invalido e' recusado na validacao, antes do `load`
    # (AC-6). E' assim que o status chega de verdade, no JSON do modelo.
    status: StatusRecebimento | None = None
    periodo: Literal["7", "30", "90", "365", "tudo"] = "90"


class LinhaRecebimento(BaseModel):
    recebimento_id: str
    recebido_em: datetime
    unidade: str
    nota_fiscal: str
    fornecedor: str
    status: StatusRecebimento
    status_rotulo: str
    # RN-R04: pendencia aberta. Nao impede a conclusao — e' sinal, nao bloqueio.
    divergencia: bool


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05, ADR-0020). `Recebimento` nao carrega
    custo e nada aqui o busca — o AC-7 e' verdadeiro por construcao, e testado."""

    total: int
    escopo: str
    recorte: str
    # Quantos recebimentos do recorte tem divergencia aberta.
    com_divergencia: int
    linhas: list[LinhaRecebimento]


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    recebimentos: list[Recebimento]
    escopo: str
    recorte: str


def _recorte(params: Params) -> str:
    dias = DIAS[params.periodo]
    return "todo o período" if dias is None else f"últimos {dias} dias"


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    # `agora` em UTC: `recebido_em` e' `timestamptz` (modelos.py), e comparar com
    # `date.today()` erra por um dia perto da virada — foi o achado A-29.
    agora = datetime.now(UTC)
    dias = DIAS[params.periodo]
    de = agora - timedelta(days=dias) if dias else None

    # `listar` NAO filtra: o escopo de unidade (RN-A01) ja' vem aplicado pela
    # porta, e os demais recortes sao deste componente. Filtrar por unidade aqui
    # nao contorna a intersecao — ela ja' aconteceu.
    todos = list(await ctx.repos.recebimento.listar(ctx.dados))
    if params.unidade_id:
        todos = [r for r in todos if r.unidade_id == params.unidade_id]
    if params.status:
        todos = [r for r in todos if r.status == params.status]
    if de is not None:
        todos = [r for r in todos if r.recebido_em >= de]

    if params.unidade_id:
        escopo = NOME_UNIDADE.get(params.unidade_id, params.unidade_id)
    else:
        n = len(ctx.unidades_permitidas)
        escopo = f"{n} unidade{'s' if n != 1 else ''}"

    return Dados(recebimentos=todos, escopo=escopo, recorte=_recorte(params))


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: sem I/O, sem relogio."""
    linhas = [
        LinhaRecebimento(
            recebimento_id=r.id,
            recebido_em=r.recebido_em,
            unidade=NOME_UNIDADE.get(r.unidade_id, r.unidade_id),
            nota_fiscal=r.nota_fiscal,
            fornecedor=r.fornecedor,
            status=r.status,
            status_rotulo=ROTULO_STATUS[r.status],
            divergencia=r.divergencia,
        )
        for r in d.recebimentos
    ]
    # Mais recente primeiro: quem abre a lista olha o que acabou de chegar.
    linhas.sort(key=lambda x: (x.recebido_em, x.recebimento_id), reverse=True)
    return VM(
        total=len(linhas),
        escopo=d.escopo,
        recorte=d.recorte,
        com_divergencia=sum(1 for x in linhas if x.divergencia),
        linhas=linhas,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="recebimento_lista",
        label="Recebimentos",
        description=(
            "Lista os recebimentos de mercadoria — o que entrou, de qual "
            "fornecedor, com qual nota fiscal e em que estado da conferência "
            "(rascunho, conferido ou liberado) — apenas das unidades do "
            "usuário. Marca os que têm divergência entre nota e físico. Use "
            "quando perguntarem o que foi recebido, quais entradas estão "
            "pendentes de conferência, ou o que chegou num período."
        ),
        examples=(
            "o que foi recebido nos últimos 30 dias",
            "quais recebimentos ainda estão como rascunho",
            "que entradas tiveram divergência",
        ),
        params=Params,
        requires="recebimento.ler",
        tamanho="inteira",
        load=carregar,
        select=projetar,
    )
)
