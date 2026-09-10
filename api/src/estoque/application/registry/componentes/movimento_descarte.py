"""`movimento_descarte` — a única saída de lote vencido ou bloqueado.

`RN-L06`: lote vencido não sai por nenhum motivo, **exceto** descarte. Este
componente é o outro lado dessa frase — a fila do que só tem esse caminho, e o
formulário que o percorre com as duas assinaturas que a §4.1 exige.

**A fila é por status EFETIVO, e é o oposto da `quarentena_fila`.** Lá o filtro é
o status registrado, porque a fila é de decisão pendente. Aqui é o efetivo
(ADR-0022), porque o que define o descarte é a situação de agora: um lote
`liberado` no banco que passou da validade é `vencido` neste instante, sem nenhum
processo ter rodado, e é exatamente ele que precisa sair da prateleira.

**Descarte não é atalho de saída.** Lote liberado e válido aparece com o
impedimento dito, e o servidor recusa de novo (`RN-A03`): desviar mercadoria boa
para "descarte" seria furto com formulário.

Este componente **não escreve** (ADR-0002). Quem grava é `commands/descarte.py`.
"""

from datetime import date

from pydantic import BaseModel

from estoque.application.commands.entradas.descarte import (
    EntradaDescarte,
    MotivoDescarte,
)
from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.definir import CommandDef, ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.identidade import UnidadeId
from estoque.domain.regras.validade import dias_ate_vencer, status_efetivo
from estoque.domain.tipos import Lote, StatusLoteEfetivo

# §4.1: "Vencido · Bloqueado -> descarte registrado -> Descartado". A lista vive
# aqui e no comando pelo mesmo motivo do estorno: o `registry` não importa
# `commands.descarte` (contrato 2 — sqlalchemy no caminho). O que impede as duas
# de divergirem é o teste que compara as duas em `tests/registry/`.
DESCARTAVEIS: tuple[StatusLoteEfetivo, ...] = ("vencido", "bloqueado")

ROTULO_MOTIVO: dict[MotivoDescarte, str] = {
    "vencimento": "Vencimento",
    "avaria": "Avaria, recall ou suspeita",
}


class Params(BaseModel):
    # Sem lote, a fila. Com lote, o formulário daquele lote.
    lote_id: str | None = None
    unidade_id: UnidadeId | None = None


class LoteDescartavel(BaseModel):
    lote_id: str
    produto: str
    numero: str
    unidade: str
    validade: date
    dias_restantes: int
    saldo: int
    # ADR-0022: `vencido` ou `bloqueado` na fila. No alvo pode ser qualquer um —
    # é o que sustenta o aviso quando alguém pede o descarte de um lote bom.
    status_efetivo: StatusLoteEfetivo
    pode_descartar: bool
    impedimento: str | None = None


class OpcaoMotivo(BaseModel):
    valor: MotivoDescarte
    rotulo: str


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05, ADR-0020)."""

    total: int
    escopo: str
    fila: list[LoteDescartavel] = []
    # Preenchido só quando `lote_id` foi pedido: é o alvo do descarte.
    alvo: LoteDescartavel | None = None
    motivos: list[OpcaoMotivo]
    # §4.1 — Gerente + RT. Dito ANTES de preencher: descobrir na recusa que
    # faltava a segunda assinatura lê-se como falha do sistema, e não como a
    # regra que é.
    exige_dupla_identificacao: bool = True


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    lotes: list[Lote]
    alvo: Lote | None
    saldos: dict[str, int]
    nomes: dict[str, str]
    hoje: date
    escopo: str


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    hoje = date.today()
    todos = list(await ctx.repos.lote.listar(ctx.dados, unidade_id=params.unidade_id))
    saldos = await ctx.repos.lote.saldos([lote.id for lote in todos], ctx.dados)

    alvo = None
    if params.lote_id:
        alvo = next((lote for lote in todos if lote.id == params.lote_id), None)
        if alvo is None:
            # Fora do escopo e inexistente saem pela mesma porta (ADR-0014).
            raise nao_encontrado({"lote_id": params.lote_id, "ator": ctx.ator.id})

    # A fila é derivada aqui, no `load`, porque `status_efetivo` é função de data
    # e saldo e o repositório só conhece o status registrado (ADR-0022).
    fila = [
        lote
        for lote in todos
        if status_efetivo(lote, saldos.get(lote.id, 0), hoje) in DESCARTAVEIS
        and saldos.get(lote.id, 0) > 0
    ]
    relevantes = fila if alvo is None else [*fila, alvo]

    if params.unidade_id:
        escopo = NOME_UNIDADE.get(params.unidade_id, params.unidade_id)
    else:
        n = len(ctx.unidades_permitidas)
        escopo = f"{n} unidade{'s' if n != 1 else ''}"

    produtos = await ctx.repos.produto.por_ids(
        [lote.produto_id for lote in relevantes], ctx.dados
    )
    return Dados(
        lotes=fila,
        alvo=alvo,
        saldos={lote.id: saldos.get(lote.id, 0) for lote in relevantes},
        # Só o nome: `Produto` carrega custo para quem tem `custo.ler`, e o que
        # não entra aqui não chega ao viewmodel.
        nomes={pid: p.nome for pid, p in produtos.items()},
        hoje=hoje,
        escopo=escopo,
    )


def _impedimento(efetivo: StatusLoteEfetivo, saldo: int) -> str | None:
    """As mesmas recusas de `commands/descarte.py`, na ordem dela. A tela avisa;
    o servidor decide (`RN-A03`)."""
    if efetivo not in DESCARTAVEIS:
        return f"Está {efetivo}: descarte é para lote vencido ou bloqueado (RN-L06)."
    if saldo <= 0:
        return "Sem saldo para descartar."
    return None


def _linha(lote: Lote, d: Dados) -> LoteDescartavel:
    saldo = d.saldos.get(lote.id, 0)
    efetivo = status_efetivo(lote, saldo, d.hoje)
    impedimento = _impedimento(efetivo, saldo)
    return LoteDescartavel(
        lote_id=lote.id,
        produto=d.nomes.get(lote.produto_id, lote.produto_id),
        numero=lote.numero,
        unidade=NOME_UNIDADE.get(lote.unidade_id, lote.unidade_id),
        validade=lote.validade,
        dias_restantes=dias_ate_vencer(lote, d.hoje),
        saldo=saldo,
        status_efetivo=efetivo,
        pode_descartar=impedimento is None,
        impedimento=impedimento,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: `hoje` chega pelo `Dados`."""
    fila = [_linha(lote, d) for lote in d.lotes]
    # O que venceu há mais tempo primeiro: é o que está parado na prateleira
    # ocupando endereço, e o que uma inspeção encontra antes.
    fila.sort(key=lambda linha: (linha.dias_restantes, linha.lote_id))
    return VM(
        total=len(fila),
        escopo=d.escopo,
        fila=fila,
        alvo=_linha(d.alvo, d) if d.alvo is not None else None,
        motivos=[OpcaoMotivo(valor=v, rotulo=r) for v, r in ROTULO_MOTIVO.items()],
    )


COMPONENTE = registrar(
    ComponentDef(
        id="movimento_descarte",
        label="Descartar lote",
        description=(
            "Lotes vencidos ou bloqueados que só podem sair do estoque por "
            "descarte, e o formulário para registrar o descarte de um deles. O "
            "lote sai inteiro e o registro exige a identificação do gerente e do "
            "responsável técnico. Use quando falarem em descartar, destruir, dar "
            "baixa de vencido ou tirar da prateleira o que não pode ser vendido."
        ),
        examples=(
            "o que eu preciso descartar",
            "quero dar baixa nesse lote vencido",
            "esse lote bloqueado vai para descarte",
        ),
        params=Params,
        # Tupla é conjunção: descartar move estoque, e a fila é leitura de lote.
        requires=("movimento.descartar", "lote.ler"),
        # ADR-0005: formulário é unidade inteira, nunca composto peça por peça.
        tamanho="inteira",
        load=carregar,
        select=projetar,
        commands={
            "movimento_descarte": CommandDef(
                endpoint="/api/comandos/movimento_descarte",
                # O mesmo schema que o comando valida. Uma definição só.
                schema=EntradaDescarte,
                requires="movimento.descartar",
                confirm=True,
                idempotent=False,
            )
        },
    )
)
