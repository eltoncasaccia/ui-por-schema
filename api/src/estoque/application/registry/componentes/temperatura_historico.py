"""`temperatura_historico` — a serie de temperatura da camara fria, por periodo.

O componente que responde ao auto de infracao da ANVISA: `RN-F03` — histórico
consultável por período — com cinco anos de retenção (`RNF-06`) e exportável
(`CA-07`).

Tres decisoes carregam o arquivo:

1. **Escopo por `nao_encontrado`, nao por serie vazia** (ADR-0014). `unidade_id`
   e' obrigatorio e nomeia UMA unidade. Pedir a temperatura de uma unidade que
   o ator nao alcanca responde `nao_encontrado`, identico a uma unidade que nao
   existe — igual a `lote_detalhe`. Serie vazia seria um oraculo: diria "a
   unidade existe, so' nao tem leitura".

2. **Agregacao automatica** (`AC-1`). Cinco anos de leitura em intervalo fixo
   sao dezenas de milhares de pontos; a tela nao aguenta, e o `RNF-04` (2 s)
   menos ainda. Acima de `LIMITE_PONTOS` o `select` agrega em baldes por
   intervalo de tempo, com min/max/media e a marca de excursao. Nao ha' param
   de balde: o modelo compoe a tela, nao escolhe resolucao.

3. **A exportacao parte deste viewmodel** (`CA-07`, `AC-2`). A T-054 gera o
   arquivo em `/api/componentes/{id}/exportar` a partir das MESMAS linhas que a
   tela desenha — pontos ou baldes —, entao "com os mesmos dados da tela" e'
   verdadeiro por construcao (`tests/exportacao`).
"""

from datetime import UTC, date, datetime, time, timedelta

from pydantic import BaseModel, model_validator

from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.identidade import UnidadeId
from estoque.domain.tipos import RegistroTemperatura

# RN-F02: a faixa util da cadeia fria. Fora dela, o lote fica em quarentena com
# bloqueio — mas a decisao de destino e' do RT (`lote_status_acao`, T-027), nao
# deste componente, que so' mostra.
FAIXA_MIN_C = 2.0
FAIXA_MAX_C = 8.0

# Orcamento de largura de um grafico de linha. Acima disso, agrega — senao viram
# 40 mil pontos de sub-pixel e o `RNF-04` estoura.
LIMITE_PONTOS = 480


class Params(BaseModel):
    unidade_id: UnidadeId
    de: date
    ate: date

    @model_validator(mode="after")
    def _periodo_coerente(self) -> "Params":
        # AC-6: periodo invertido e' recusado NA VALIDACAO, antes do `load`.
        # `validar_schema` chama `Params.model_validate`, entao um schema forjado
        # tambem bate aqui.
        if self.de > self.ate:
            raise ValueError("de posterior a ate")
        return self


class Ponto(BaseModel):
    instante: datetime
    celsius: float
    fora_da_faixa: bool


class Balde(BaseModel):
    """Um intervalo agregado. `tem_excursao` marca o balde que esconde ao menos
    uma leitura fora da faixa — sem ele, agregar apagaria a excursao."""

    inicio: datetime
    fim: datetime
    minimo: float
    maximo: float
    media: float
    leituras: int
    tem_excursao: bool


class VM(BaseModel):
    """Sem custo (CA-05): temperatura nao tem preco, e nada aqui busca produto.

    `pontos` **ou** `baldes` vem preenchido, nunca os dois — `agregado` diz qual.
    """

    unidade: str
    de: date
    ate: date
    faixa_min_c: float = FAIXA_MIN_C
    faixa_max_c: float = FAIXA_MAX_C
    total_leituras: int
    leituras_fora_da_faixa: int
    agregado: bool
    pontos: list[Ponto] = []
    baldes: list[Balde] = []


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    unidade: str
    de: date
    ate: date
    leituras: list[RegistroTemperatura]


def _fora(celsius: float) -> bool:
    return celsius < FAIXA_MIN_C or celsius > FAIXA_MAX_C


def _inicio_do_dia(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=UTC)


def _fim_do_dia(d: date) -> datetime:
    return datetime.combine(d, time.max, tzinfo=UTC)


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    if params.unidade_id not in ctx.unidades_permitidas:
        # Fora do escopo e inexistente saem pela mesma porta (ADR-0014). O
        # `detalhe_interno` vai ao log e nunca e' serializado.
        raise nao_encontrado({"unidade_id": params.unidade_id, "ator": ctx.ator.id})

    leituras = list(
        await ctx.repos.temperatura.serie(
            params.unidade_id,
            _inicio_do_dia(params.de),
            _fim_do_dia(params.ate),
            ctx.dados,
        )
    )
    return Dados(
        unidade=NOME_UNIDADE.get(params.unidade_id, params.unidade_id),
        de=params.de,
        ate=params.ate,
        leituras=leituras,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: `de`/`ate` chegam pelo `Dados`, sem
    relogio."""
    leituras = sorted(d.leituras, key=lambda r: (r.medido_em, r.id))
    fora = sum(1 for r in leituras if _fora(r.celsius))

    if len(leituras) <= LIMITE_PONTOS:
        pontos = [
            Ponto(instante=r.medido_em, celsius=r.celsius, fora_da_faixa=_fora(r.celsius))
            for r in leituras
        ]
        return VM(
            unidade=d.unidade,
            de=d.de,
            ate=d.ate,
            total_leituras=len(leituras),
            leituras_fora_da_faixa=fora,
            agregado=False,
            pontos=pontos,
        )

    # Agrega em ate' LIMITE_PONTOS baldes de tempo iguais. Um passo por leitura,
    # com o indice calculado — nao um laco por balde varrendo a serie inteira.
    inicio = _inicio_do_dia(d.de)
    fim = _fim_do_dia(d.ate)
    janela = (fim - inicio).total_seconds() or 1.0
    grupos: dict[int, list[float]] = {}
    for r in leituras:
        offset = (r.medido_em - inicio).total_seconds()
        i = min(LIMITE_PONTOS - 1, max(0, int(offset / janela * LIMITE_PONTOS)))
        grupos.setdefault(i, []).append(r.celsius)

    passo = janela / LIMITE_PONTOS
    baldes = [
        Balde(
            inicio=inicio + timedelta(seconds=i * passo),
            fim=inicio + timedelta(seconds=(i + 1) * passo),
            minimo=min(temps),
            maximo=max(temps),
            media=sum(temps) / len(temps),
            leituras=len(temps),
            tem_excursao=any(_fora(t) for t in temps),
        )
        for i, temps in sorted(grupos.items())
    ]
    return VM(
        unidade=d.unidade,
        de=d.de,
        ate=d.ate,
        total_leituras=len(leituras),
        leituras_fora_da_faixa=fora,
        agregado=True,
        baldes=baldes,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="temperatura_historico",
        label="Histórico de temperatura",
        description=(
            "Série temporal da temperatura de uma câmara fria num período, com a "
            "faixa útil de 2 a 8 °C marcada e as leituras fora dela destacadas. "
            "Períodos longos vêm agregados por intervalo. Exportável. Use para "
            "comprovar cadeia fria, responder a inspeção ou investigar quando a "
            "temperatura saiu da faixa."
        ),
        examples=(
            "histórico de temperatura da câmara fria no último ano",
            "a temperatura ficou na faixa em março",
            "quero exportar a temperatura dos últimos 5 anos",
        ),
        params=Params,
        requires="temperatura.ler",
        tamanho="alta",
        load=carregar,
        select=projetar,
    )
)
