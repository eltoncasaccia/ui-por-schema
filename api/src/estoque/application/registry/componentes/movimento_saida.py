"""`movimento_saida` — a separação, com o FEFO já resolvido.

O componente responde à pergunta de quem separa: *de qual lote eu tiro?* E a
resposta vem pronta — `RN-L02` diz que o sistema **propõe** o lote liberado de
menor validade, e propor é trabalho do servidor, não do operador.

**As alternativas aparecem, e é de propósito.** Esconder os outros lotes faria o
FEFO parecer uma restrição do sistema em vez de uma regra do negócio; e há casos
legítimos de separar outro (avaria localizada, pedido que exige validade maior).
`RN-L03` cobra o preço certo disso: justificativa registrada. O que a tela não
faz é deixar a escolha passar em silêncio.

**Cada alternativa vem com o motivo de não ser a proposta**, calculado aqui. Uma
lista de lotes sem essa coluna obrigaria o operador a comparar datas de cabeça,
que é exatamente o erro que o FEFO existe para evitar.

Este componente **não escreve** (ADR-0002): ele mostra o formulário e diz para
onde postar. Quem grava é `commands/saida.py`.
"""

from datetime import date

from pydantic import BaseModel

from estoque.application.commands.entradas.saida import (
    EXIGEM_DESTINATARIO,
    EntradaSaida,
    MotivoSaida,
)
from estoque.application.etag import etag_lote_e_saldo
from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.definir import CommandDef, ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.identidade import UnidadeId
from estoque.domain.regras.fefo import propor_fefo
from estoque.domain.regras.validade import (
    ClasseValidade,
    classificar_validade,
    dias_ate_vencer,
    status_efetivo,
)
from estoque.domain.tipos import ClasseProduto, Lote, StatusLoteEfetivo

# Rótulos dos motivos. A lista fechada vive em `commands/entradas/saida.py`,
# junto do schema que o comando valida — aqui só a tradução para a tela, e o
# `MotivoSaida` garante que as duas não divirjam: um motivo novo lá sem rótulo
# aqui não compila.
ROTULO_MOTIVO: dict[MotivoSaida, str] = {
    "venda": "Venda",
    "avaria": "Avaria",
    "furto": "Furto ou extravio",
    "erro_de_separacao": "Erro de separação",
}


class Params(BaseModel):
    # O recorte é o PRODUTO, não o lote: quem separa parte do item do pedido, e
    # é o sistema que escolhe o lote (RN-L02). Pedir o lote no param inverteria
    # a regra — o operador escolheria e o FEFO viraria conferência.
    produto_id: str
    unidade_id: UnidadeId | None = None


class LoteCandidato(BaseModel):
    lote_id: str
    numero: str
    unidade: str
    validade: date
    dias_restantes: int
    saldo: int
    situacao: ClasseValidade
    status_efetivo: StatusLoteEfetivo
    # Verdadeiro só para um: o que o FEFO propôs.
    proposto: bool
    disponivel: bool
    # RN-L05: a ≤ 30 dias do vencimento a venda depende de liberação do RT, e a
    # liberação vive na TRILHA de auditoria (achado A-14). O registry não alcança
    # a trilha — não há repositório de auditoria na porta —, então a tela é
    # conservadora: avisa que depende de liberação e não propõe o lote. O
    # servidor decide de verdade, e aceita se o RT já tiver liberado.
    exige_liberacao_rt: bool = False
    motivo: str | None = None
    # T-051: etag DESTA linha — a pessoa escolhe qual lote usar depois de ler,
    # então o `If-Match` da escrita não pode ser um valor só para o bloco.
    etag: str


class OpcaoMotivo(BaseModel):
    valor: MotivoSaida
    rotulo: str
    exige_destinatario: bool


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05, ADR-0020)."""

    produto: str
    classe: ClasseProduto
    escopo: str
    # RN-C01: controlado nasce pendente e o saldo não muda até o RT autorizar.
    # A tela precisa dizer isso ANTES, senão o operador conclui que deu errado.
    exige_autorizacao: bool
    proposta: LoteCandidato | None = None
    # Vazio quando só existe o lote proposto — e aí não há escolha a justificar.
    alternativas: list[LoteCandidato] = []
    motivos: list[OpcaoMotivo]
    sem_estoque: bool = False


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    lotes: list[Lote]
    saldos: dict[str, int]
    produto: str
    classe: ClasseProduto
    escopo: str
    hoje: date
    proposta_id: str | None


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    produto = await ctx.repos.produto.por_id(params.produto_id, ctx.dados)
    if produto is None:
        raise nao_encontrado({"produto_id": params.produto_id, "ator": ctx.ator.id})

    hoje = date.today()
    lotes = list(
        await ctx.repos.lote.listar(
            ctx.dados, produto_id=params.produto_id, unidade_id=params.unidade_id
        )
    )
    saldos = await ctx.repos.lote.saldos([lote.id for lote in lotes], ctx.dados)

    if params.unidade_id:
        escopo = NOME_UNIDADE.get(params.unidade_id, params.unidade_id)
    else:
        n = len(ctx.unidades_permitidas)
        escopo = f"{n} unidade{'s' if n != 1 else ''}"

    # ACHADO A-21: `propor_fefo` implementa RN-L02 e não conhece RN-L05. Sozinha,
    # ela propõe o lote de menor validade — que costuma ser exatamente o que está
    # dentro dos 30 dias e não pode ser vendido sem liberação do RT. O sistema
    # estaria propondo o que ele mesmo recusa.
    vendaveis = [lote for lote in lotes if classificar_validade(lote, hoje) != "bloqueio_30"]
    proposta = propor_fefo(vendaveis, saldos, hoje)
    return Dados(
        lotes=lotes,
        saldos={lote.id: saldos.get(lote.id, 0) for lote in lotes},
        # Só nome e classe: `Produto` carrega custo para quem tem `custo.ler`.
        produto=produto.nome,
        classe=produto.classe,
        escopo=escopo,
        hoje=hoje,
        proposta_id=proposta.id if proposta else None,
    )


def _motivo_de_indisponibilidade(efetivo: StatusLoteEfetivo) -> str:
    return {
        "quarentena": "Em quarentena: aguarda liberação do RT.",
        "bloqueado": "Bloqueado por decisão do RT.",
        "vencido": "Vencido — só sai por descarte (RN-L06).",
        "esgotado": "Sem saldo.",
        "descartado": "Descartado.",
    }.get(efetivo, "Indisponível.")


def _candidato(lote: Lote, d: Dados) -> LoteCandidato:
    saldo = d.saldos.get(lote.id, 0)
    efetivo = status_efetivo(lote, saldo, d.hoje)
    na_janela = classificar_validade(lote, d.hoje) == "bloqueio_30"
    disponivel = efetivo == "liberado" and not na_janela
    return LoteCandidato(
        lote_id=lote.id,
        numero=lote.numero,
        unidade=NOME_UNIDADE.get(lote.unidade_id, lote.unidade_id),
        validade=lote.validade,
        dias_restantes=dias_ate_vencer(lote, d.hoje),
        saldo=saldo,
        situacao=classificar_validade(lote, d.hoje),
        status_efetivo=efetivo,
        proposto=lote.id == d.proposta_id,
        disponivel=disponivel,
        exige_liberacao_rt=na_janela and efetivo == "liberado",
        motivo=(
            None
            if disponivel
            else (
                "A menos de 30 dias do vencimento: a venda depende de liberação "
                "do responsável técnico (RN-L05)."
                if na_janela and efetivo == "liberado"
                else _motivo_de_indisponibilidade(efetivo)
            )
        ),
        etag=etag_lote_e_saldo(lote, saldo),
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: `hoje` chega pelo `Dados`."""
    candidatos = [_candidato(lote, d) for lote in d.lotes]
    proposta = next((c for c in candidatos if c.proposto), None)
    return VM(
        produto=d.produto,
        classe=d.classe,
        escopo=d.escopo,
        exige_autorizacao=d.classe == "controlado",
        proposta=proposta,
        # Ordem: os disponíveis primeiro, e dentro deles o de menor validade —
        # a mesma ordem do FEFO, para a alternativa mais defensável ficar ao
        # lado da proposta em vez de no fim da lista.
        alternativas=sorted(
            (c for c in candidatos if not c.proposto),
            key=lambda c: (not c.disponivel, c.validade, c.lote_id),
        ),
        motivos=[
            OpcaoMotivo(valor=v, rotulo=r, exige_destinatario=v in EXIGEM_DESTINATARIO)
            for v, r in ROTULO_MOTIVO.items()
        ],
        sem_estoque=proposta is None,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="movimento_saida",
        label="Separar saída",
        description=(
            "Formulário de saída de estoque de um produto, com o lote já proposto "
            "pela regra FEFO — o liberado de menor validade — e as alternativas "
            "com o motivo de cada uma não ter sido escolhida. Separar outro lote "
            "exige justificativa. Use quando pedirem para dar baixa, separar, "
            "faturar ou registrar a saída de um produto."
        ),
        examples=(
            "preciso dar baixa de 20 caixas de amoxicilina",
            "separar saída desse produto",
            "qual lote eu tiro para essa venda",
        ),
        params=Params,
        requires="movimento.criar",
        # ADR-0005: formulário é unidade inteira, nunca composto peça por peça.
        tamanho="inteira",
        load=carregar,
        select=projetar,
        commands={
            "movimento_saida": CommandDef(
                endpoint="/api/comandos/movimento_saida",
                # O mesmo schema que o comando valida. Uma definição só.
                schema=EntradaSaida,
                requires="movimento.criar",
                confirm=True,
                idempotent=False,
            )
        },
    )
)
