"""`lote_lista` — a lista de lotes, com o recorte VISIVEL na resposta.

Duas decisoes carregam este arquivo:

1. **Todo recorte e' valor nomeado.** `janela` e' enum de 30/60/90 e nao uma
   data solta. Data livre convida o modelo a inventar recorte, e filtro que
   falta alarga a resposta EM SILENCIO — o achado mais perigoso da v1 (risco
   R-5 do PRD). Pelo mesmo motivo o viewmodel devolve `recorte`: a tela mostra
   o corte que a resposta representa, entao alargar deixa de ser silencioso.

2. **O status filtrado e' o EFETIVO** (ADR-0022). Filtrar pela coluna do banco
   devolveria como `liberado` um lote que venceu ontem — o banco guarda so' o
   que e' decisao humana; `vencido` e `esgotado` sao funcao de data e saldo.
"""

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel

from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.identidade import UnidadeId
from estoque.domain.regras.validade import (
    ClasseValidade,
    classificar_validade,
    dias_ate_vencer,
    status_efetivo,
)
from estoque.domain.tipos import Lote, StatusLoteEfetivo

NOME_UNIDADE: dict[str, str] = {
    "cd-matriz": "CD Matriz",
    "cd-refrigerado": "CD Refrigerado",
    "filial-uberlandia": "Uberlândia",
}

ROTULO_STATUS: dict[StatusLoteEfetivo, str] = {
    "quarentena": "Quarentena",
    "liberado": "Liberado",
    "bloqueado": "Bloqueado",
    "descartado": "Descartado",
    "vencido": "Vencido",
    "esgotado": "Esgotado",
}


class Params(BaseModel):
    # NENHUM campo livre de busca aqui. `produto_id` e' identificador, nao
    # termo: um id que nao existe devolve `nao_encontrado` no `load`, e nao a
    # lista vazia que ensinaria "este produto nao tem lote".
    produto_id: str | None = None
    unidade_id: UnidadeId | None = None
    # Enum FECHADO, e o efetivo (ADR-0022) — e' o status que a tela mostra.
    status: StatusLoteEfetivo | None = None
    # Enum, nunca data: ver a docstring do modulo.
    janela: Literal["30", "60", "90"] | None = None


class LinhaLote(BaseModel):
    lote_id: str
    produto: str
    # RN-L08: numero NAO identifica lote. Dois lotes de mesmo numero em
    # unidades diferentes sao registros distintos, com saldos independentes —
    # e por isso a chave da linha e' `lote_id`, nunca `numero`.
    numero: str
    unidade: str
    fabricacao: date
    validade: date
    dias_restantes: int
    saldo: int
    status: StatusLoteEfetivo
    situacao: ClasseValidade
    endereco: str | None


class Faixa(BaseModel):
    rotulo: str
    valor: int
    ordem: int = 0


class VM(BaseModel):
    """O que atravessa a rede. Sem custo, para papel nenhum (CA-05, ADR-0020):
    custo e' de `produto_ficha`, e o que nao esta' aqui nao chega ao navegador."""

    total: int
    escopo: str
    # O recorte aplicado, em texto. Sem isto, um filtro que o modelo esqueceu
    # devolve uma lista maior sem ninguem perceber.
    recorte: list[str] = []
    linhas: list[LinhaLote]
    resumo: list[Faixa] = []
    # Paginacao e' transporte: nao e' param, o modelo nunca escolhe pagina.
    cursor: str | None = None
    tem_mais: bool = False


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    lotes: list[Lote]
    saldos: dict[str, int]
    status: dict[str, StatusLoteEfetivo]
    nomes: dict[str, str]
    hoje: date
    total: int
    escopo: str
    recorte: list[str]
    resumo: list[Faixa]
    cursor: str | None = None
    tem_mais: bool = False


def _escopo(params: Params, ctx: LoadContext) -> str:
    if params.unidade_id:
        return NOME_UNIDADE.get(params.unidade_id, params.unidade_id)
    n = len(ctx.unidades_permitidas)
    return f"{n} unidade{'s' if n != 1 else ''}"


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    hoje = date.today()
    limite = hoje + timedelta(days=int(params.janela)) if params.janela else None

    recorte: list[str] = []
    if params.produto_id:
        produto = await ctx.repos.produto.por_id(params.produto_id, ctx.dados)
        if produto is None:
            # ADR-0014: registro individual nega de forma indistinguivel de
            # inexistente. O detalhe fica no log, nunca na resposta.
            raise nao_encontrado({"produto_id": params.produto_id, "ator": ctx.ator.id})
        recorte.append(f"produto {produto.nome}")
    if params.unidade_id:
        recorte.append(NOME_UNIDADE.get(params.unidade_id, params.unidade_id))
    if params.status:
        recorte.append(f"status {ROTULO_STATUS[params.status]}")
    if params.janela:
        recorte.append(f"vence em até {params.janela} dias")

    todos = list(
        await ctx.repos.lote.listar(
            ctx.dados,
            produto_id=params.produto_id,
            unidade_id=params.unidade_id,
            validade_ate=limite,
        )
    )
    saldos = await ctx.repos.lote.saldos([lote.id for lote in todos], ctx.dados)
    # RN-M06 e ADR-0022: nem saldo nem `vencido`/`esgotado` sao coluna. O saldo
    # vem da view derivada dos movimentos; o status sai de funcao pura.
    efetivos = {lote.id: status_efetivo(lote, saldos.get(lote.id, 0), hoje) for lote in todos}
    selecao = [
        lote for lote in todos if params.status is None or efetivos[lote.id] == params.status
    ]

    # O resumo descreve a RESPOSTA inteira, nao a pagina: um resumo que muda ao
    # rolar nao e' resumo. Status e' identidade, nao magnitude — dai `ordem` 0
    # em todas as faixas, que a barra desenha em tom neutro.
    contagem: dict[StatusLoteEfetivo, int] = {}
    for lote in selecao:
        s = efetivos[lote.id]
        contagem[s] = contagem.get(s, 0) + 1
    resumo = [
        Faixa(rotulo=ROTULO_STATUS[s], valor=v)
        for s, v in sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    # Cursor estavel: a lista ja' vem ordenada por (validade, id) do repositorio.
    inicio = 0
    if ctx.pagina.cursor:
        for i, lote in enumerate(selecao):
            if f"{lote.validade.isoformat()}|{lote.id}" == ctx.pagina.cursor:
                inicio = i + 1
                break
    fatia = selecao[inicio : inicio + ctx.pagina.limite]
    tem_mais = inicio + ctx.pagina.limite < len(selecao)
    ultimo = fatia[-1] if fatia else None
    cursor = f"{ultimo.validade.isoformat()}|{ultimo.id}" if ultimo and tem_mais else None

    produtos = await ctx.repos.produto.por_ids([lote.produto_id for lote in fatia], ctx.dados)
    return Dados(
        lotes=fatia,
        saldos={lote.id: saldos.get(lote.id, 0) for lote in fatia},
        status={lote.id: efetivos[lote.id] for lote in fatia},
        # So' o nome. `Produto` traz custo para quem tem `custo.ler`, e o que
        # nao entra no `Dados` nao tem como escorregar para o viewmodel.
        nomes={pid: p.nome for pid, p in produtos.items()},
        hoje=hoje,
        total=len(selecao),
        escopo=_escopo(params, ctx),
        recorte=recorte,
        resumo=resumo,
        cursor=cursor,
        tem_mais=tem_mais,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: sem I/O, sem relogio — `hoje` chega
    pelo `Dados`, senao duas chamadas com a mesma carga poderiam divergir."""
    return VM(
        total=d.total,
        escopo=d.escopo,
        recorte=d.recorte,
        linhas=[
            LinhaLote(
                lote_id=lote.id,
                produto=d.nomes.get(lote.produto_id, lote.produto_id),
                numero=lote.numero,
                unidade=lote.unidade_id,
                fabricacao=lote.fabricacao,
                validade=lote.validade,
                dias_restantes=dias_ate_vencer(lote, d.hoje),
                saldo=d.saldos.get(lote.id, 0),
                status=d.status[lote.id],
                situacao=classificar_validade(lote, d.hoje),
                endereco=lote.endereco,
            )
            for lote in d.lotes
        ],
        resumo=d.resumo,
        cursor=d.cursor,
        tem_mais=d.tem_mais,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="lote_lista",
        label="Lotes",
        description=(
            "Lista os lotes com número, validade, saldo e situação, filtrando por "
            "produto, unidade, status ou faixa de validade, sempre restrito às "
            "unidades do usuário. Use quando pedirem a relação de lotes, os lotes "
            "de um produto, ou o que está em determinado status. NÃO use para o "
            "que está vencendo por urgência — para isso existe `fila_vencimento` — "
            "nem para um lote específico, que é `lote_detalhe`."
        ),
        # Exemplos SEM nome de unidade: uma unidade citada aqui pode nao ser do
        # ator, e o catalogo e' o vocabulario DELE.
        examples=(
            "quais lotes existem da amoxicilina",
            "me mostre os lotes bloqueados",
            "lista de lotes vencidos",
            "quais lotes vencem nos próximos 60 dias",
        ),
        params=Params,
        requires="lote.ler",
        tamanho="inteira",
        load=carregar,
        select=projetar,
    )
)
