"""`lote_movimentos` — o extrato do lote, e a prova de onde o saldo vem.

Este componente e' o `RN-M06` visivel: cada linha traz o saldo DEPOIS dela, e a
ultima coincide com o saldo do lote porque o saldo e' a soma dos movimentos, e
nao um numero guardado em coluna. Um campo `saldo` editavel e' a divergencia de
3,8% do inventario de volta.

Duas consequencias que aparecem na tela:

- movimento `aguardando_autorizacao` NAO mexe no saldo (RN-C01). Enquanto a
  segunda identificacao nao vem, a mercadoria nao saiu — se contasse, a dupla
  identificacao viraria teatro.
- estorno nao apaga nada (RN-M02/RN-M03): entra como registro proprio, com
  referencia ao original, e o saldo volta pela soma.

O recorte de tempo e' `periodo`, enum, e nao um par de datas soltas: data livre
convida o modelo a inventar recorte, e recorte inventado erra em silencio.
"""

from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel

from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.saldo import calcular_saldo
from estoque.domain.tipos import (
    MotivoMovimento,
    Movimento,
    StatusMovimento,
    TipoMovimento,
)

DIAS: dict[str, int | None] = {"7": 7, "30": 30, "90": 90, "365": 365, "tudo": None}


class Params(BaseModel):
    lote_id: str
    # Enum, nunca `de`/`ate` como data livre. O padrao e' `tudo` de proposito:
    # um padrao que RECORTA esconderia movimento sem ninguem pedir, e o extrato
    # de um lote e' curto — a paginacao cuida do volume.
    periodo: Literal["7", "30", "90", "365", "tudo"] = "tudo"


class LinhaMovimento(BaseModel):
    movimento_id: str
    criado_em: datetime
    tipo: TipoMovimento
    # Sempre positiva (RN-M04); o sinal vem do tipo. Somar `quantidade` por
    # conta propria daria o numero errado — dai `saldo_apos`, ja' calculado.
    quantidade: int
    motivo: MotivoMovimento
    complemento: str | None
    autor_id: str
    autorizador_id: str | None
    status: StatusMovimento
    saldo_apos: int
    estorna_movimento_id: str | None


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05): o extrato responde quanto entrou e
    quanto saiu, nunca quanto vale (ADR-0020)."""

    lote_id: str
    produto: str
    numero: str
    unidade: str
    saldo_atual: int
    periodo_dias: int | None
    total: int
    linhas: list[LinhaMovimento]
    cursor: str | None = None
    tem_mais: bool = False


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    lote_id: str
    produto: str
    numero: str
    unidade: str
    saldo_atual: int
    periodo_dias: int | None
    total: int
    movimentos: list[Movimento]
    saldo_apos: dict[str, int]
    cursor: str | None = None
    tem_mais: bool = False


def _chave(m: Movimento) -> str:
    return f"{m.criado_em.isoformat()}|{m.id}"


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    # O lote vem PRIMEIRO, e por ele o escopo. Ir direto aos movimentos
    # devolveria lista vazia para lote de outra unidade — e vazio ensina que o
    # lote existe e nunca se moveu, que e' falso (ADR-0014).
    lote = await ctx.repos.lote.por_id(params.lote_id, ctx.dados)
    if lote is None:
        raise nao_encontrado({"lote_id": params.lote_id, "ator": ctx.ator.id})

    produto = await ctx.repos.produto.por_id(lote.produto_id, ctx.dados)
    todos = list(await ctx.repos.movimento.do_lote(lote.id, ctx.dados))

    # O saldo corrido cobre a HISTORIA inteira, mesmo com periodo recortado:
    # um extrato dos ultimos 30 dias nao comeca do zero.
    corrido = 0
    saldo_apos: dict[str, int] = {}
    for m in todos:
        # O sinal por tipo vive no dominio, num lugar so'. Repeti-lo aqui seria
        # uma segunda regra de saldo, e as duas divergiriam.
        corrido += calcular_saldo([m])
        saldo_apos[m.id] = corrido

    dias = DIAS[params.periodo]
    if dias is None:
        janela = todos
    else:
        corte = date.today() - timedelta(days=dias)
        janela = [m for m in todos if m.criado_em.date() >= corte]

    # Extrato se le do mais recente para o mais antigo.
    janela = sorted(janela, key=lambda m: (m.criado_em, m.id), reverse=True)

    inicio = 0
    if ctx.pagina.cursor:
        for i, m in enumerate(janela):
            if _chave(m) == ctx.pagina.cursor:
                inicio = i + 1
                break
    fatia = janela[inicio : inicio + ctx.pagina.limite]
    tem_mais = inicio + ctx.pagina.limite < len(janela)
    ultimo = fatia[-1] if fatia else None
    return Dados(
        lote_id=lote.id,
        produto=produto.nome if produto else lote.produto_id,
        numero=lote.numero,
        unidade=lote.unidade_id,
        # RN-M06: a soma dos movimentos, pela funcao do dominio. Nao existe
        # campo a ler.
        saldo_atual=calcular_saldo(todos),
        periodo_dias=dias,
        total=len(janela),
        movimentos=fatia,
        saldo_apos={m.id: saldo_apos[m.id] for m in fatia},
        cursor=_chave(ultimo) if ultimo and tem_mais else None,
        tem_mais=tem_mais,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: sem I/O e sem relogio."""
    return VM(
        lote_id=d.lote_id,
        produto=d.produto,
        numero=d.numero,
        unidade=d.unidade,
        saldo_atual=d.saldo_atual,
        periodo_dias=d.periodo_dias,
        total=d.total,
        linhas=[
            LinhaMovimento(
                movimento_id=m.id,
                criado_em=m.criado_em,
                tipo=m.tipo,
                quantidade=m.quantidade,
                motivo=m.motivo,
                complemento=m.complemento,
                autor_id=m.autor_id,
                autorizador_id=m.autorizador_id,
                status=m.status,
                saldo_apos=d.saldo_apos[m.id],
                estorna_movimento_id=m.estorna_movimento_id,
            )
            for m in d.movimentos
        ],
        cursor=d.cursor,
        tem_mais=d.tem_mais,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="lote_movimentos",
        label="Movimentos do lote",
        description=(
            "Mostra o extrato de entradas, saídas, descartes e estornos de UM lote, "
            "com motivo, autor, situação e o saldo depois de cada movimento, num "
            "período de 7, 30, 90 ou 365 dias, ou a história inteira. Use quando "
            "perguntarem o que aconteceu com um lote, por que o saldo mudou, ou o "
            "histórico dele. NÃO use para rastrear para quais clientes um lote foi "
            "vendido."
        ),
        examples=(
            "o que aconteceu com esse lote",
            "por que o saldo desse lote caiu",
            "histórico de movimentos do lote nos últimos 30 dias",
        ),
        params=Params,
        # Le movimento E le o lote (numero, produto, unidade) para o cabecalho,
        # entao pede as duas. Nao muda o catalogo de ninguem: toda persona com
        # `movimento.ler` tem `lote.ler`.
        requires=("movimento.ler", "lote.ler"),
        tamanho="inteira",
        load=carregar,
        select=projetar,
    )
)
