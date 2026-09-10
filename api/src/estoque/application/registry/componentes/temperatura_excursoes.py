"""`temperatura_excursoes` — as ocorrencias fora da faixa, com os lotes expostos.

`RN-F04`: uma excursao de temperatura gera ocorrencia **vinculada aos lotes
presentes na unidade no periodo**. E' esse vinculo que a inspecao pede — nao a
lista de todos os lotes da camara, e' quais estavam la' quando a temperatura
subiu.

**A armadilha (AC-4).** Vincular todo lote da unidade produz uma lista inflada e
inutil. O corte e': o lote conta se a entrada dele na unidade tem
`criado_em <= fim da excursao`. Um lote que entrou depois nao estava exposto, e
some. O ciclo 1 nao tem transferencia entre unidades, entao "presente" e'
"entrou ate' aquele momento" — quando houver saida/transferencia de lote inteiro,
este corte ganha um limite superior.

Escopo por `nao_encontrado` (ADR-0014), como em `temperatura_historico`:
`unidade_id` e' obrigatorio, e pedir uma unidade fora do escopo responde igual a
uma que nao existe.

Nao decide destino de lote — isso e' do RT, via `lote_status_acao` (T-027).
"""

from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel, model_validator

from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.componentes.temperatura_historico import (
    FAIXA_MAX_C,
    FAIXA_MIN_C,
)
from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.identidade import UnidadeId
from estoque.domain.tipos import Lote, RegistroTemperatura, StatusLoteRegistrado

# Sem `de`/`ate`, a janela padrao olha um ano para tras — excursao e' rara, e o
# uso tipico e' "teve excursao recente?". O periodo cheio de retencao (5 anos,
# RNF-06) se pede explicitamente.
JANELA_PADRAO_DIAS = 365


class Params(BaseModel):
    unidade_id: UnidadeId
    de: date | None = None
    ate: date | None = None

    @model_validator(mode="after")
    def _periodo_coerente(self) -> "Params":
        # AC-6: periodo invertido recusado na validacao. `de`/`ate` andam juntos:
        # so' um dos dois e' recorte pela metade, e recorte pela metade alarga a
        # resposta em silencio (risco R-5).
        if (self.de is None) != (self.ate is None):
            raise ValueError("informe de e ate juntos, ou nenhum dos dois")
        if self.de is not None and self.ate is not None and self.de > self.ate:
            raise ValueError("de posterior a ate")
        return self


class LotePresente(BaseModel):
    lote_id: str
    numero: str
    produto: str
    status: StatusLoteRegistrado
    entrou_em: datetime


class Excursao(BaseModel):
    inicio: datetime
    fim: datetime
    duracao_horas: float
    sentido: Literal["calor", "frio"]
    # A leitura mais extrema da corrida — a que mais se afasta da faixa.
    pico_celsius: float
    leituras: int
    lotes: list[LotePresente]


class VM(BaseModel):
    """Sem custo (CA-05): nada aqui busca produto por preco, so' por nome."""

    unidade: str
    de: date
    ate: date
    faixa_min_c: float = FAIXA_MIN_C
    faixa_max_c: float = FAIXA_MAX_C
    total_excursoes: int
    excursoes: list[Excursao]


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    unidade: str
    de: date
    ate: date
    leituras: list[RegistroTemperatura]
    lotes: list[Lote]
    # lote_id -> instante da PRIMEIRA entrada na unidade
    entrada_por_lote: dict[str, datetime]
    nome_produto: dict[str, str]


def _fora(celsius: float) -> bool:
    return celsius < FAIXA_MIN_C or celsius > FAIXA_MAX_C


def _distancia_da_faixa(celsius: float) -> float:
    if celsius > FAIXA_MAX_C:
        return celsius - FAIXA_MAX_C
    if celsius < FAIXA_MIN_C:
        return FAIXA_MIN_C - celsius
    return 0.0


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    if params.unidade_id not in ctx.unidades_permitidas:
        raise nao_encontrado({"unidade_id": params.unidade_id, "ator": ctx.ator.id})

    ate = params.ate or date.today()
    de = params.de or (ate - timedelta(days=JANELA_PADRAO_DIAS))
    de_dt = datetime.combine(de, time.min, tzinfo=UTC)
    ate_dt = datetime.combine(ate, time.max, tzinfo=UTC)

    leituras = list(
        await ctx.repos.temperatura.serie(params.unidade_id, de_dt, ate_dt, ctx.dados)
    )
    lotes = list(await ctx.repos.lote.listar(ctx.dados, unidade_id=params.unidade_id))
    entradas = list(
        await ctx.repos.movimento.listar(
            ctx.dados, unidade_id=params.unidade_id, tipo="entrada"
        )
    )
    entrada_por_lote: dict[str, datetime] = {}
    for mov in entradas:
        atual = entrada_por_lote.get(mov.lote_id)
        if atual is None or mov.criado_em < atual:
            entrada_por_lote[mov.lote_id] = mov.criado_em

    produtos = await ctx.repos.produto.por_ids([lote.produto_id for lote in lotes], ctx.dados)
    nome_produto: dict[str, str] = {}
    for lote in lotes:
        p = produtos.get(lote.produto_id)
        nome_produto[lote.id] = p.nome if p else lote.produto_id

    return Dados(
        unidade=NOME_UNIDADE.get(params.unidade_id, params.unidade_id),
        de=de,
        ate=ate,
        leituras=leituras,
        lotes=lotes,
        entrada_por_lote=entrada_por_lote,
        nome_produto=nome_produto,
    )


def _montar_excursao(corrida: list[RegistroTemperatura], d: Dados) -> Excursao:
    inicio = corrida[0].medido_em
    fim = corrida[-1].medido_em
    pico = max(corrida, key=lambda r: _distancia_da_faixa(r.celsius))
    sentido: Literal["calor", "frio"] = "calor" if pico.celsius > FAIXA_MAX_C else "frio"

    # RN-F04: os lotes presentes NO PERIODO. Presente = entrou na unidade ate' o
    # fim da excursao. Lote que entrou depois nao estava exposto (AC-4).
    presentes = [
        LotePresente(
            lote_id=lote.id,
            numero=lote.numero,
            produto=d.nome_produto.get(lote.id, lote.produto_id),
            status=lote.status,
            entrou_em=d.entrada_por_lote[lote.id],
        )
        for lote in d.lotes
        if lote.id in d.entrada_por_lote and d.entrada_por_lote[lote.id] <= fim
    ]
    presentes.sort(key=lambda p: (p.entrou_em, p.lote_id))

    return Excursao(
        inicio=inicio,
        fim=fim,
        duracao_horas=round((fim - inicio).total_seconds() / 3600, 2),
        sentido=sentido,
        pico_celsius=pico.celsius,
        leituras=len(corrida),
        lotes=presentes,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: sem I/O, sem relogio — a janela ja'
    veio resolvida no `Dados`."""
    leituras = sorted(d.leituras, key=lambda r: (r.medido_em, r.id))

    excursoes: list[Excursao] = []
    corrida: list[RegistroTemperatura] = []
    for r in leituras:
        if _fora(r.celsius):
            corrida.append(r)
            continue
        if corrida:
            excursoes.append(_montar_excursao(corrida, d))
            corrida = []
    if corrida:
        excursoes.append(_montar_excursao(corrida, d))

    return VM(
        unidade=d.unidade,
        de=d.de,
        ate=d.ate,
        total_excursoes=len(excursoes),
        excursoes=excursoes,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="temperatura_excursoes",
        label="Excursões de temperatura",
        description=(
            "Lista as ocorrências em que a temperatura de uma câmara fria saiu "
            "da faixa de 2 a 8 °C num período, cada uma com início, fim, duração, "
            "pico e os lotes que estavam na unidade quando aconteceu. Use para "
            "responder à inspeção regulatória, investigar uma excursão ou saber "
            "quais lotes foram expostos."
        ),
        examples=(
            "teve excursão de temperatura na câmara fria",
            "quais lotes foram expostos à temperatura fora da faixa",
            "excursões de temperatura no último trimestre",
        ),
        params=Params,
        requires="temperatura.ler",
        tamanho="inteira",
        load=carregar,
        select=projetar,
    )
)
