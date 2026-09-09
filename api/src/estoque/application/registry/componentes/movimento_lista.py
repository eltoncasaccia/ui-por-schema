"""`movimento_lista` — os movimentos, e a fila de autorizações pendentes.

**Um componente com dois usos, e a fusão é o que fez o catálogo caber em 23**
([ADR-0011](../../../../../../docs/adr/0011-teto-de-catalogo.md)). `status:
aguardando_autorizacao` é valor do enum, e é assim que Helena encontra o que
precisa autorizar — sem componente dedicado para a fila.

A condição que o ADR-0001 impõe a qualquer fusão está satisfeita: **o recorte
existe como valor nomeado**. O modelo pede `aguardando_autorizacao`, não "os
movimentos que estão esperando alguma coisa".

**Nada aqui edita nem exclui** (`RN-M02`, `CA-08`). O componente não declara
`commands`, e é isso — não a ausência de um botão na tela — que faz a interface
não oferecer o caminho. Corrigir movimento se faz por estorno, que é T-029.

**Estorno e original aparecem os dois, ligados** (`RN-M03`). Esconder o original
depois do estorno seria apagar história com outro nome: quem lê a lista precisa
ver que houve um erro e que ele foi corrigido, não um estado limpo que finge que
o erro nunca existiu.
"""

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel

from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.identidade import UnidadeId
from estoque.domain.tipos import (
    MotivoMovimento,
    Movimento,
    StatusMovimento,
    TipoMovimento,
)

# Recorte de tempo por enum, nunca por data solta: data livre convida o modelo a
# inventar recorte, e recorte inventado erra em silêncio (risco R-5 do PRD).
DIAS: dict[str, int | None] = {"7": 7, "30": 30, "90": 90, "365": 365, "tudo": None}

ROTULO_STATUS: dict[StatusMovimento, str] = {
    "efetivado": "Efetivado",
    "aguardando_autorizacao": "Aguardando autorização",
    "recusado": "Recusado",
}


class Params(BaseModel):
    unidade_id: UnidadeId | None = None
    lote_id: str | None = None
    tipo: TipoMovimento | None = None
    # O valor que transforma esta lista na fila do RT.
    status: StatusMovimento | None = None
    periodo: Literal["7", "30", "90", "365", "tudo"] = "30"


class LinhaMovimento(BaseModel):
    movimento_id: str
    criado_em: datetime
    tipo: TipoMovimento
    quantidade: int
    motivo: MotivoMovimento
    complemento: str | None
    lote_id: str
    unidade: str
    autor: str
    # RN-C01: a segunda identidade, quando houve. Nulo em movimento comum.
    autorizador: str | None
    status: StatusMovimento
    status_rotulo: str
    # RN-M03: o vínculo nos DOIS sentidos. `estorna` aponta para o original;
    # `estornado_por` marca o original que já foi corrigido — e é o que impede a
    # lista de parecer que o erro continua de pé.
    estorna: str | None
    estornado_por: str | None
    # Só em `aguardando_autorizacao`. É o número que ordena o trabalho do RT.
    parado_ha_dias: int | None = None


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05, ADR-0020)."""

    total: int
    escopo: str
    recorte: str
    # Quantos esperam autorização dentro do que foi pedido. Aparece mesmo quando
    # o filtro não é esse: é a pendência que trava estoque.
    pendentes: int
    linhas: list[LinhaMovimento]


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    movimentos: list[Movimento]
    estornado_por: dict[str, str]
    agora: datetime
    escopo: str
    recorte: str
    total: int
    pendentes: int


def _recorte(params: Params) -> str:
    dias = DIAS[params.periodo]
    return "todo o período" if dias is None else f"últimos {dias} dias"


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    # `agora` em UTC, e não `date.today()`: `criado_em` é gravado em UTC (RN-M04),
    # e misturar os dois erra por um dia perto da virada — foi o bug que o teste
    # de `controlado_autorizar` pegou.
    agora = datetime.now(UTC)
    dias = DIAS[params.periodo]
    de = agora - timedelta(days=dias) if dias else None

    todos = list(
        await ctx.repos.movimento.listar(
            ctx.dados,
            unidade_id=params.unidade_id,
            tipo=params.tipo,
            status=params.status,
            de=de,
        )
    )
    if params.lote_id:
        todos = [mov for mov in todos if mov.lote_id == params.lote_id]

    # RN-M03: o vínculo inverso. Um estorno referencia o original; o original não
    # sabe que foi estornado, e é essa metade que a tela precisa.
    #
    # A busca é sobre a MESMA janela: um estorno fora do recorte não marca o
    # original, e é honesto que não marque — a lista mostra o que aconteceu no
    # período, não conclusões sobre o que ficou de fora.
    estornado_por = {
        mov.estorna_movimento_id: mov.id for mov in todos if mov.estorna_movimento_id
    }

    if params.unidade_id:
        escopo = NOME_UNIDADE.get(params.unidade_id, params.unidade_id)
    else:
        n = len(ctx.unidades_permitidas)
        escopo = f"{n} unidade{'s' if n != 1 else ''}"

    return Dados(
        movimentos=todos,
        estornado_por=estornado_por,
        agora=agora,
        escopo=escopo,
        recorte=_recorte(params),
        total=len(todos),
        pendentes=sum(1 for mov in todos if mov.status == "aguardando_autorizacao"),
    )


def _linha(mov: Movimento, d: Dados) -> LinhaMovimento:
    pendente = mov.status == "aguardando_autorizacao"
    return LinhaMovimento(
        movimento_id=mov.id,
        criado_em=mov.criado_em,
        tipo=mov.tipo,
        quantidade=mov.quantidade,
        motivo=mov.motivo,
        complemento=mov.complemento,
        lote_id=mov.lote_id,
        unidade=NOME_UNIDADE.get(mov.unidade_id, mov.unidade_id),
        autor=mov.autor_id,
        autorizador=mov.autorizador_id,
        status=mov.status,
        status_rotulo=ROTULO_STATUS[mov.status],
        estorna=mov.estorna_movimento_id,
        estornado_por=d.estornado_por.get(mov.id),
        parado_ha_dias=(d.agora - mov.criado_em).days if pendente else None,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: `agora` chega pelo `Dados`."""
    linhas = [_linha(mov, d) for mov in d.movimentos]
    # Mais recente primeiro. Quem abre a lista está olhando o que acabou de
    # acontecer — e quem procura o antigo tem o recorte de período para isso.
    linhas.sort(key=lambda x: (x.criado_em, x.movimento_id), reverse=True)
    return VM(
        total=d.total,
        escopo=d.escopo,
        recorte=d.recorte,
        pendentes=d.pendentes,
        linhas=linhas,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="movimento_lista",
        label="Movimentos",
        description=(
            "Lista os movimentos de estoque — entradas, saídas, descartes e "
            "estornos — com autor, motivo, quantidade e situação, filtrando por "
            "unidade, lote, tipo, período ou situação. A situação "
            "'aguardando_autorizacao' mostra o que espera a segunda "
            "identificação do responsável técnico. Só lista: corrigir movimento "
            "se faz por estorno, que é outra tela."
        ),
        examples=(
            "o que saiu esta semana",
            "quais movimentos estão esperando autorização",
            "mostra as saídas desse lote",
        ),
        params=Params,
        requires="movimento.ler",
        tamanho="inteira",
        load=carregar,
        select=projetar,
        # Sem `commands`: RN-M02 e CA-08. Não há edição nem exclusão a oferecer,
        # e a ausência aqui é o que garante isso — não a tela.
    )
)
