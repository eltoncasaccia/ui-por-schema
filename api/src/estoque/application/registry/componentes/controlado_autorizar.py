"""`controlado_autorizar` — a segunda identidade, e o `CA-04` inteiro.

O único fluxo de duas pessoas do ciclo 1. Cleide submete a saída de controlado
(T-028), o movimento fica `aguardando_autorizacao` e **o saldo não se mexe**;
Helena decide aqui.

**Este componente é a prova mais afiada do ADR-0002.** Ele mostra a fila e o
formulário — plano de render. Quem conclui é a pessoa que clica, com a identidade
dela, pelo endpoint autenticado. Não há saída de modelo que efetive uma
movimentação de controlado, e não é por disciplina: `assistant` não alcança
`commands` (import-linter, contrato 3) e o `CommandDef` publicado não carrega
função nenhuma.

**Sem `movimento_id`, mostra a fila.** A descoberta pelo `movimento_lista` é
T-024 e ainda não existe; um formulário que só funciona com um id que ninguém
consegue obter seria uma entrega pela metade. Não é componente novo — o catálogo
continua com +1 — e quando T-024 chegar, esta lista vira o atalho do RT em vez
do único caminho.
"""

from datetime import UTC, datetime

from pydantic import BaseModel

from estoque.application.commands.entradas.autorizacao import EntradaAutorizacao
from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.definir import CommandDef, ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.identidade import UnidadeId
from estoque.domain.tipos import Movimento


class Params(BaseModel):
    # Sem id, a fila. Com id, o formulário daquele movimento.
    movimento_id: str | None = None
    unidade_id: UnidadeId | None = None


class Pendente(BaseModel):
    movimento_id: str
    lote_id: str
    produto: str
    unidade: str
    quantidade: int
    motivo: str
    autor: str
    submetido_em: datetime
    # Quantos dias o pedido está parado. É o número que ordena o trabalho do RT,
    # e o que mostra que a fila parou de andar.
    parado_ha_dias: int


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05, ADR-0020)."""

    total: int
    escopo: str
    fila: list[Pendente] = []
    # Preenchido só quando `movimento_id` foi pedido: é o alvo da decisão.
    alvo: Pendente | None = None
    # RN-A04: falso quando quem abriu foi quem submeteu. A interface desabilita;
    # o servidor recusa de novo, e o banco recusa uma terceira vez (CHECK).
    pode_decidir: bool = True
    motivo_impedimento: str | None = None


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    movimentos: list[Movimento]
    nomes: dict[str, str]
    autores: dict[str, str]
    # `datetime` em UTC, e não `date.today()`.
    #
    # ACHADO EM TESTE: `criado_em` é gravado em UTC (RN-M04) e `date.today()`
    # devolve a data LOCAL do servidor. Perto da virada do dia as duas discordam,
    # e "parado há 9 dias" virava 8 — um erro que não aparece de dia e aparece de
    # madrugada, que é o pior tipo.
    agora: datetime
    escopo: str
    alvo_id: str | None
    ator_id: str


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    pendentes = [
        mov
        for mov in await ctx.repos.movimento.listar(
            ctx.dados,
            unidade_id=params.unidade_id,
            status="aguardando_autorizacao",
        )
    ]
    if params.movimento_id and not any(mov.id == params.movimento_id for mov in pendentes):
        # Já resolvido, inexistente ou fora do escopo — os três indistinguíveis
        # (ADR-0014). Distinguir "existe mas já foi autorizado" contaria ao
        # curioso que a operação aconteceu.
        raise nao_encontrado({"movimento_id": params.movimento_id, "ator": ctx.ator.id})

    lotes = {
        lote.id: lote
        for lote in [await ctx.repos.lote.por_id(mov.lote_id, ctx.dados) for mov in pendentes]
        if lote is not None
    }
    produtos = await ctx.repos.produto.por_ids(
        [lote.produto_id for lote in lotes.values()], ctx.dados
    )
    nomes = {
        mov.id: (
            produtos[lotes[mov.lote_id].produto_id].nome
            if mov.lote_id in lotes and lotes[mov.lote_id].produto_id in produtos
            else mov.lote_id
        )
        for mov in pendentes
    }

    if params.unidade_id:
        escopo = NOME_UNIDADE.get(params.unidade_id, params.unidade_id)
    else:
        n = len(ctx.unidades_permitidas)
        escopo = f"{n} unidade{'s' if n != 1 else ''}"

    return Dados(
        movimentos=pendentes,
        nomes=nomes,
        # O nome de quem submeteu não é buscado: `usuario.ler` é permissão à
        # parte, e o RT tem. O id basta e não depende dela — quem precisa do
        # nome tem a trilha de auditoria.
        autores={mov.id: mov.autor_id for mov in pendentes},
        agora=datetime.now(UTC),
        escopo=escopo,
        alvo_id=params.movimento_id,
        ator_id=ctx.ator.id,
    )


def _pendente(mov: Movimento, d: Dados) -> Pendente:
    return Pendente(
        movimento_id=mov.id,
        lote_id=mov.lote_id,
        produto=d.nomes.get(mov.id, mov.lote_id),
        unidade=NOME_UNIDADE.get(mov.unidade_id, mov.unidade_id),
        quantidade=mov.quantidade,
        motivo=mov.motivo,
        autor=d.autores.get(mov.id, mov.autor_id),
        submetido_em=mov.criado_em,
        parado_ha_dias=(d.agora - mov.criado_em).days,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: `agora` e o ator chegam pelo `Dados`."""
    fila = [_pendente(mov, d) for mov in d.movimentos]
    # Mais parado primeiro: a fila do RT é ordenada por quanto tempo o estoque
    # está travado, não por quando o pedido chegou.
    fila.sort(key=lambda p: (-p.parado_ha_dias, p.movimento_id))

    alvo = next((p for p in fila if p.movimento_id == d.alvo_id), None) if d.alvo_id else None
    mesma_pessoa = alvo is not None and alvo.autor == d.ator_id
    return VM(
        total=len(fila),
        escopo=d.escopo,
        fila=fila,
        alvo=alvo,
        pode_decidir=not mesma_pessoa,
        motivo_impedimento=(
            "Quem submeteu não autoriza a própria movimentação (RN-A04)."
            if mesma_pessoa
            else None
        ),
    )


COMPONENTE = registrar(
    ComponentDef(
        id="controlado_autorizar",
        label="Autorizar controlado",
        description=(
            "Fila de movimentações de medicamento controlado aguardando a segunda "
            "identificação do responsável técnico, e o formulário para autorizar "
            "ou recusar uma delas com motivo registrado. O estoque só muda quando "
            "o responsável autoriza. Use quando perguntarem o que espera "
            "autorização, o que está pendente de controlado, ou pedirem para "
            "autorizar uma saída."
        ),
        examples=(
            "o que está esperando minha autorização",
            "tem controlado pendente",
            "quero autorizar essa saída de controlado",
        ),
        params=Params,
        # RN-C01: a segunda identidade é do RT, e `controlado.autorizar` existe
        # num papel só. Nem o Diretor tem — papel não é nível.
        requires="controlado.autorizar",
        tamanho="inteira",
        load=carregar,
        select=projetar,
        commands={
            "controlado_autorizar": CommandDef(
                endpoint="/api/comandos/controlado_autorizar",
                schema=EntradaAutorizacao,
                requires="controlado.autorizar",
                confirm=True,
                idempotent=False,
            )
        },
    )
)
