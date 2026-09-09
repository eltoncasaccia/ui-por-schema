"""`lote_status_acao` — bloquear, desbloquear, liberar vencimento.

**Três transições num componente só**, e a fusão é deliberada
([ADR-0011](../../../../docs/adr/0011-teto-de-catalogo.md)): três formulários
quase idênticos custariam ~492 tokens de prompt em toda pergunta, para todo
usuário, e o catálogo tem teto de 25.

A condição que o ADR-0001 impõe a qualquer fusão está satisfeita: **o recorte
continua existindo como valor nomeado no enum `acao`**. O modelo não perdeu
precisão — ele pede `bloquear`, não "mudar o status para alguma coisa".

O que este componente responde, e é a pergunta real de quem abre a tela: *o que
eu posso fazer com este lote agora?* A resposta vem da tabela §4.1 avaliada
contra o status corrente, no servidor. A interface desabilita o que não cabe; o
servidor recusa de novo, porque desabilitar não é controlar (`RN-A03`).
"""

from datetime import date

from pydantic import BaseModel

from estoque.commands.entradas.lote import AcaoStatus, EntradaStatus
from estoque.domain.erros import nao_encontrado
from estoque.domain.identidade import PapelId
from estoque.domain.regras.estados import EventoLote, transicao_valida
from estoque.domain.regras.validade import (
    ClasseValidade,
    classificar_validade,
    dias_ate_vencer,
    status_efetivo,
)
from estoque.domain.tipos import Lote, StatusLoteEfetivo, StatusLoteRegistrado
from estoque.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.registry.definir import CommandDef, ComponentDef, LoadContext
from estoque.registry.registry import registrar

_EVENTO_DA_ACAO: dict[AcaoStatus, EventoLote | None] = {
    "bloquear": "bloqueio",
    "desbloquear": "desbloqueio",
    # `liberar_vencimento` NÃO é transição da §4.1: o bloqueio por validade é
    # derivado da data (ADR-0022), não um status armazenado. Ver `RN-L05`.
    "liberar_vencimento": None,
}

_ROTULO: dict[AcaoStatus, str] = {
    "bloquear": "Bloquear",
    "desbloquear": "Desbloquear",
    "liberar_vencimento": "Liberar venda apesar do vencimento próximo",
}


class Params(BaseModel):
    # Identificador, não recorte. Quem protege é o escopo do repositório.
    lote_id: str


class AcaoDisponivel(BaseModel):
    """Uma linha da tabela §4.1, já avaliada contra este lote.

    `motivo` é preenchido quando a ação não cabe. Dizer *por que* não cabe é o
    que impede a leitura errada de que o sistema está quebrado — e o texto fala
    do estado do lote, nunca de quem poderia fazer.
    """

    acao: AcaoStatus
    rotulo: str
    disponivel: bool
    motivo: str | None = None


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05, ADR-0020)."""

    lote_id: str
    produto: str
    numero: str
    unidade: str
    validade: date
    dias_restantes: int
    saldo: int
    situacao: ClasseValidade
    # Os dois, e a diferença importa (ADR-0022): `status` é o que alguém
    # decidiu; `status_efetivo` é o que vale agora. Um lote `liberado` que
    # passou da validade é `vencido` sem nenhum processo ter rodado.
    status: StatusLoteRegistrado
    status_efetivo: StatusLoteEfetivo
    acoes: list[AcaoDisponivel]


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    lote: Lote
    produto: str
    saldo: int
    hoje: date
    papel: PapelId | None


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    lote = await ctx.repos.lote.por_id(params.lote_id, ctx.dados)
    if lote is None:
        raise nao_encontrado({"lote_id": params.lote_id, "ator": ctx.ator.id})

    produto = await ctx.repos.produto.por_id(lote.produto_id, ctx.dados)
    saldos = await ctx.repos.lote.saldos([lote.id], ctx.dados)
    return Dados(
        lote=lote,
        produto=produto.nome if produto else lote.produto_id,
        saldo=saldos.get(lote.id, 0),
        hoje=date.today(),
        # O papel entra no `Dados` porque `projetar` é puro e não recebe ator.
        # A disponibilidade é decidida com a identidade real, no servidor.
        papel=ctx.ator.papel,
    )


def _avaliar(d: Dados, acao: AcaoStatus) -> AcaoDisponivel:
    rotulo = _ROTULO[acao]
    if acao == "liberar_vencimento":
        situacao = classificar_validade(d.lote, d.hoje)
        if d.lote.status != "liberado":
            return AcaoDisponivel(
                acao=acao,
                rotulo=rotulo,
                disponivel=False,
                motivo=(
                    f"O lote está em {d.lote.status}: há um impedimento anterior "
                    "ao da validade."
                ),
            )
        if situacao == "vencido":
            # RN-L06 vence RN-L05: lote vencido não sai, exceto por descarte.
            return AcaoDisponivel(
                acao=acao,
                rotulo=rotulo,
                disponivel=False,
                motivo="O lote já venceu: não há liberação possível (RN-L06).",
            )
        if situacao != "bloqueio_30":
            return AcaoDisponivel(
                acao=acao,
                rotulo=rotulo,
                disponivel=False,
                motivo="Não há bloqueio por validade a liberar: faltam mais de 30 dias.",
            )
        return AcaoDisponivel(acao=acao, rotulo=rotulo, disponivel=True)

    evento = _EVENTO_DA_ACAO[acao]
    assert evento is not None  # noqa: S101 — só `liberar_vencimento` é None, tratado acima
    if transicao_valida(d.lote.status, evento, d.papel):
        return AcaoDisponivel(acao=acao, rotulo=rotulo, disponivel=True)
    return AcaoDisponivel(
        acao=acao,
        rotulo=rotulo,
        disponivel=False,
        motivo=f"Não se aplica a um lote em {d.lote.status}.",
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: `hoje` e `papel` chegam pelo `Dados`."""
    return VM(
        lote_id=d.lote.id,
        produto=d.produto,
        numero=d.lote.numero,
        unidade=NOME_UNIDADE.get(d.lote.unidade_id, d.lote.unidade_id),
        validade=d.lote.validade,
        dias_restantes=dias_ate_vencer(d.lote, d.hoje),
        saldo=d.saldo,
        situacao=classificar_validade(d.lote, d.hoje),
        status=d.lote.status,
        status_efetivo=status_efetivo(d.lote, d.saldo, d.hoje),
        acoes=[_avaliar(d, a) for a in ("bloquear", "desbloquear", "liberar_vencimento")],
    )


COMPONENTE = registrar(
    ComponentDef(
        id="lote_status_acao",
        label="Situação do lote",
        description=(
            "Formulário do responsável técnico para mudar a situação de um lote: "
            "bloquear por suspeita, recall ou avaria, desbloquear um lote já "
            "bloqueado, ou autorizar a venda de um lote a menos de 30 dias do "
            "vencimento. Exige justificativa registrada. Use quando pedirem para "
            "bloquear, desbloquear, suspender ou reativar um lote específico."
        ),
        examples=(
            "preciso bloquear o lote L-8842",
            "desbloquear esse lote",
            "quero autorizar a venda desse lote que vence em duas semanas",
        ),
        params=Params,
        # Só o RT tem `lote.status` (documento 02 §6) — ADR-0003 em ação.
        requires="lote.status",
        tamanho="inteira",
        load=carregar,
        select=projetar,
        commands={
            "lote_status": CommandDef(
                endpoint="/api/comandos/lote_status",
                # O mesmo schema que o comando valida. Uma definição só.
                schema=EntradaStatus,
                requires="lote.status",
                confirm=True,
                idempotent=False,
            )
        },
    )
)
