"""`quarentena_liberar` — a decisão do RT sobre um lote em quarentena.

**A demonstração mais limpa do ADR-0003.** `lote.liberar` existe num papel só
(documento 02 §6), então este id aparece no catálogo de Helena e em mais nenhum.
Marco, Ivo, Odair, Cleide, Rafael e Sandra não recebem o vocabulário para pedir
— o modelo não consegue nem propor a tela, quanto mais a ação.

Este componente **não escreve**. Ele descreve o formulário (ADR-0002): o `load`
traz o que a decisão precisa, e o `CommandDef` diz para onde o formulário posta.
Quem grava é `commands/lote.py`, alcançado só pela pessoa que clica em salvar.

**Reprovar leva a bloqueado, nunca a liberado** (§4.1). Não existe "liberar com
pendência": um estado intermediário seria um lote vendável que ninguém conferiu,
que é precisamente o que a quarentena existe para impedir.
"""

from datetime import date

from pydantic import BaseModel

from estoque.application.commands.entradas.lote import EntradaLiberacao
from estoque.application.etag import etag_lote
from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.definir import CommandDef, ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.regras.validade import (
    ClasseValidade,
    classificar_validade,
    dias_ate_vencer,
    status_efetivo,
)
from estoque.domain.tipos import ClasseProduto, Lote, StatusLoteEfetivo, StatusLoteRegistrado

# RN-L07: recebimento com validade inferior a 6 meses é recusado, salvo
# autorização expressa do RT. Aqui a regra não recusa — ela AVISA, porque o RT
# é exatamente quem tem a autorização. Esconder o aviso seria pedir a decisão
# sem mostrar o que a torna incomum.
MESES_AVISO_VALIDADE = 6


class Params(BaseModel):
    # Identificador, não recorte — não há enum possível para um id. O que
    # protege não é a validação do param, é o escopo do repositório (RN-A01).
    lote_id: str


class ItemConferencia(BaseModel):
    """Um item do checklist de `RN-R03`.

    `obrigatorio` é calculado no servidor, a partir da classe do produto. Se
    fosse decidido no cliente, um formulário adulterado marcaria a temperatura
    como dispensável e o termolábil passaria sem conferência — e a interface é
    payload não-confiável como qualquer outro (ADR-0004).
    """

    campo: str
    rotulo: str
    obrigatorio: bool


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05, ADR-0020)."""

    lote_id: str
    produto: str
    classe: ClasseProduto
    numero: str
    unidade: str
    fabricacao: date
    validade: date
    dias_restantes: int
    saldo: int
    situacao: ClasseValidade
    status: StatusLoteRegistrado
    status_efetivo: StatusLoteEfetivo

    # Falso quando o lote já saiu da quarentena. O formulário continua sendo
    # renderizado — quem perguntou tem direito à resposta —, mas desabilitado,
    # e a recusa real acontece no servidor de qualquer jeito (RN-A03).
    pode_decidir: bool
    motivo: str | None = None
    conferencia: list[ItemConferencia]
    aviso_validade: str | None = None


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    lote: Lote
    produto: str
    classe: ClasseProduto
    saldo: int
    hoje: date


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    lote = await ctx.repos.lote.por_id(params.lote_id, ctx.dados)
    if lote is None:
        # Fora do escopo e inexistente saem pela mesma porta (ADR-0014).
        raise nao_encontrado({"lote_id": params.lote_id, "ator": ctx.ator.id})

    produto = await ctx.repos.produto.por_id(lote.produto_id, ctx.dados)
    saldos = await ctx.repos.lote.saldos([lote.id], ctx.dados)
    return Dados(
        lote=lote,
        # Só nome e classe: `Produto` carrega custo para quem tem `custo.ler`,
        # e o que não entra no `Dados` não escorrega para o viewmodel.
        produto=produto.nome if produto else lote.produto_id,
        classe=produto.classe if produto else "comum",
        saldo=saldos.get(lote.id, 0),
        hoje=date.today(),
    )


def _conferencia(classe: ClasseProduto) -> list[ItemConferencia]:
    """RN-R03. A temperatura só é obrigatória para termolábil — exigi-la de
    todos treinaria o RT a marcar tudo sem ler, que é o oposto de conferir."""
    return [
        ItemConferencia(
            campo="integridade_conferida", rotulo="Integridade da embalagem", obrigatorio=True
        ),
        ItemConferencia(campo="validade_conferida", rotulo="Validade mínima", obrigatorio=True),
        ItemConferencia(campo="nota_fiscal_conferida", rotulo="Nota fiscal", obrigatorio=True),
        ItemConferencia(
            campo="temperatura_conferida",
            rotulo="Temperatura de chegada",
            obrigatorio=classe == "termolabil",
        ),
    ]


def _aviso(lote: Lote, hoje: date) -> str | None:
    """RN-L07, dito ao único papel que pode decidir apesar dele."""
    dias = dias_ate_vencer(lote, hoje)
    if dias < 0:
        return "Este lote já venceu. Liberar não o torna vendável (RN-L06)."
    if dias < MESES_AVISO_VALIDADE * 30:
        return (
            f"Validade em {dias} dias — abaixo dos {MESES_AVISO_VALIDADE} meses "
            "mínimos de recebimento (RN-L07). A liberação exige sua autorização expressa."
        )
    return None


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: `hoje` chega pelo `Dados`."""
    em_quarentena = d.lote.status == "quarentena"
    return VM(
        lote_id=d.lote.id,
        produto=d.produto,
        classe=d.classe,
        numero=d.lote.numero,
        unidade=NOME_UNIDADE.get(d.lote.unidade_id, d.lote.unidade_id),
        fabricacao=d.lote.fabricacao,
        validade=d.lote.validade,
        dias_restantes=dias_ate_vencer(d.lote, d.hoje),
        saldo=d.saldo,
        situacao=classificar_validade(d.lote, d.hoje),
        status=d.lote.status,
        status_efetivo=status_efetivo(d.lote, d.saldo, d.hoje),
        pode_decidir=em_quarentena,
        motivo=(
            None if em_quarentena else f"Este lote está em {d.lote.status}, não em quarentena."
        ),
        conferencia=_conferencia(d.classe),
        aviso_validade=_aviso(d.lote, d.hoje),
    )


COMPONENTE = registrar(
    ComponentDef(
        id="quarentena_liberar",
        label="Liberar quarentena",
        description=(
            "Formulário de decisão do responsável técnico sobre um lote em "
            "quarentena: liberar para venda ou reprovar, com a conferência de "
            "integridade, validade, nota fiscal e temperatura, e justificativa "
            "registrada. Use quando pedirem para liberar, aprovar ou reprovar um "
            "lote específico. Mostra o formulário; quem grava é quem confirma."
        ),
        examples=(
            "quero liberar o lote L-8842",
            "preciso aprovar a quarentena desse lote",
            "abrir a liberação do lote de amoxicilina",
        ),
        params=Params,
        # RN-R02: privativo do RT, e `lote.liberar` existe num papel só.
        requires="lote.liberar",
        # ADR-0005: formulário é unidade inteira, nunca composto peça por peça.
        tamanho="inteira",
        load=carregar,
        select=projetar,
        # T-050: o mesmo etag que `commands/lote.py:_etag_do_lote` recalcula ao
        # gravar — sem isto o `If-Match` que `lote_liberar_quarentena` exige
        # nunca tem o que comparar.
        etag=lambda d: etag_lote(d.lote),
        commands={
            # A chave É o nome do comando executável (`commands/lote.py`). A
            # bijeção entre os dois é verificada em teste: um `CommandDef` sem
            # executável é um formulário que posta para lugar nenhum.
            "lote_liberar_quarentena": CommandDef(
                endpoint="/api/comandos/lote_liberar_quarentena",
                # O MESMO schema que `commands/lote.py` usa para validar. Duas
                # declarações do formulário divergiriam no dia em que uma mudasse
                # — `commands/entradas/lote.py` existe para haver uma só.
                schema=EntradaLiberacao,
                requires="lote.liberar",
                confirm=True,
                idempotent=False,
            )
        },
    )
)
