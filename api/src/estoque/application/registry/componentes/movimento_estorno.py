"""`movimento_estorno` — corrigir sem apagar.

O extrato do lote com o que pode e o que **não** pode ser estornado, e o motivo
de cada não. É a leitura que precede a correção: quem errou uma separação precisa
achar o movimento errado no meio dos certos, e a lista sem essa coluna obrigaria
a comparar data e quantidade de cabeça.

**Os movimentos não-estornáveis continuam na lista.** Sumir com eles faria o
operador procurar de novo o lançamento que ele viu no extrato; mostrar por que
não serve encerra a busca. O par original/estorno aparece inteiro — `RN-M03` quer
o erro E a correção visíveis, não um estado limpo que finge que o erro não houve.

Este componente **não escreve** (ADR-0002): mostra o formulário e diz para onde
postar. Quem grava é `commands/estorno.py`, e ele recusa de novo, com a identidade
real (`RN-A03`).
"""

from datetime import datetime

from pydantic import BaseModel

from estoque.application.commands.entradas.estorno import (
    TIPOS_ESTORNAVEIS,
    EntradaEstorno,
    MotivoEstorno,
)
from estoque.application.etag import etag_movimento_estorno
from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.definir import CommandDef, ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.regras.estados import ja_estornado
from estoque.domain.tipos import Movimento, TipoMovimento

# Rótulos dos motivos. A lista fechada vive em `commands/entradas/estorno.py`,
# junto do schema que o comando valida — aqui só a tradução para a tela, e o
# `MotivoEstorno` garante que as duas não divirjam: um motivo novo lá sem rótulo
# aqui não compila.
ROTULO_MOTIVO: dict[MotivoEstorno, str] = {
    "erro_de_separacao": "Erro de separação",
    "estorno": "Cancelamento da operação",
}


class Params(BaseModel):
    # O recorte é o LOTE, e não o movimento: a porta de dados não expõe
    # `movimento.por_id` (é a T-007), e pedir um id de movimento que ninguém
    # consegue descobrir seria um formulário sem entrada.
    lote_id: str
    # Sem ele, só o extrato. Com ele, o formulário daquele movimento.
    movimento_id: str | None = None


class Lancamento(BaseModel):
    movimento_id: str
    tipo: TipoMovimento
    quantidade: int
    motivo: str
    autor: str
    registrado_em: datetime
    estorna_movimento_id: str | None = None
    pode_estornar: bool
    # Preenchido só quando não pode: é o que evita a segunda tentativa.
    impedimento: str | None = None
    # T-051: etag DESTE lançamento — a pessoa escolhe qual estornar no extrato.
    etag: str


class OpcaoMotivo(BaseModel):
    valor: MotivoEstorno
    rotulo: str


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05, ADR-0020)."""

    produto: str
    lote: str
    unidade: str
    saldo: int
    total: int
    lancamentos: list[Lancamento] = []
    # Preenchido só quando `movimento_id` foi pedido: é o alvo da correção.
    alvo: Lancamento | None = None
    motivos: list[OpcaoMotivo]


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    movimentos: list[Movimento]
    produto: str
    lote_numero: str
    unidade: str
    saldo: int
    alvo_id: str | None


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    lote = await ctx.repos.lote.por_id(params.lote_id, ctx.dados)
    if lote is None:
        # Fora do escopo e inexistente saem pela mesma porta (ADR-0014).
        raise nao_encontrado({"lote_id": params.lote_id, "ator": ctx.ator.id})

    movimentos = list(await ctx.repos.movimento.do_lote(lote.id, ctx.dados))
    if params.movimento_id and not any(mov.id == params.movimento_id for mov in movimentos):
        raise nao_encontrado({"movimento_id": params.movimento_id, "ator": ctx.ator.id})

    produto = await ctx.repos.produto.por_id(lote.produto_id, ctx.dados)
    saldos = await ctx.repos.lote.saldos([lote.id], ctx.dados)
    return Dados(
        movimentos=movimentos,
        # Só o nome: `Produto` carrega custo para quem tem `custo.ler`.
        produto=produto.nome if produto else lote.produto_id,
        lote_numero=lote.numero,
        unidade=NOME_UNIDADE.get(lote.unidade_id, lote.unidade_id),
        saldo=saldos.get(lote.id, 0),
        alvo_id=params.movimento_id,
    )


def _impedimento(mov: Movimento, todos: list[Movimento]) -> str | None:
    """As mesmas quatro recusas de `commands/estorno.py`, na ordem dela.

    A tela avisa; o servidor decide (`RN-A03`). Que a regra apareça duas vezes é
    consequência do ADR-0002 — o componente descreve, o comando executa —, e as
    duas leem `ja_estornado` do domínio, que é onde `RN-M03` mora de fato.
    """
    if mov.tipo == "estorno":
        return "Um estorno não se estorna (RN-M03)."
    if mov.tipo not in TIPOS_ESTORNAVEIS:
        return f"Movimento de {mov.tipo} não tem estorno neste ciclo."
    if mov.status != "efetivado":
        return f"Está {mov.status}: não teve efeito no saldo."
    if ja_estornado(mov, todos):
        return "Já estornado."
    return None


def _lancamento(mov: Movimento, todos: list[Movimento]) -> Lancamento:
    impedimento = _impedimento(mov, todos)
    return Lancamento(
        movimento_id=mov.id,
        tipo=mov.tipo,
        quantidade=mov.quantidade,
        motivo=mov.motivo,
        # O id basta, e não depende de `usuario.ler`, que é permissão à parte:
        # quem precisa do nome tem a trilha de auditoria.
        autor=mov.autor_id,
        registrado_em=mov.criado_em,
        estorna_movimento_id=mov.estorna_movimento_id,
        pode_estornar=impedimento is None,
        impedimento=impedimento,
        etag=etag_movimento_estorno(
            mov.id, mov.status, mov.lote_id, mov.quantidade, estornado=ja_estornado(mov, todos)
        ),
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: nada aqui lê relógio nem banco."""
    lancamentos = [_lancamento(mov, d.movimentos) for mov in d.movimentos]
    # Mais recente primeiro: o erro que se corrige é quase sempre o último, e o
    # extrato em ordem de leitura começaria pelo recebimento de meses atrás.
    lancamentos.sort(key=lambda linha: (linha.registrado_em, linha.movimento_id), reverse=True)
    return VM(
        produto=d.produto,
        lote=d.lote_numero,
        unidade=d.unidade,
        saldo=d.saldo,
        total=len(lancamentos),
        lancamentos=lancamentos,
        alvo=next((x for x in lancamentos if x.movimento_id == d.alvo_id), None),
        motivos=[OpcaoMotivo(valor=v, rotulo=r) for v, r in ROTULO_MOTIVO.items()],
    )


COMPONENTE = registrar(
    ComponentDef(
        id="movimento_estorno",
        label="Estornar movimento",
        description=(
            "Extrato de um lote com o que pode ser estornado e o motivo de cada "
            "lançamento que não pode, e o formulário para registrar o estorno de "
            "uma saída. O estorno cria um movimento novo que referencia o "
            "original; nada é apagado nem editado. Use quando falarem em corrigir, "
            "estornar, desfazer ou cancelar uma baixa já registrada."
        ),
        examples=(
            "preciso estornar aquela saída errada",
            "dei baixa no lote errado, como corrijo",
            "quero desfazer essa movimentação",
        ),
        params=Params,
        # Tupla é conjunção: estornar mexe no saldo e ler o extrato é `movimento.ler`.
        # Sandra (auditoria) lê o extrato e não estorna — e não vê este componente.
        requires=("movimento.estornar", "movimento.ler"),
        # ADR-0005: formulário é unidade inteira, nunca composto peça por peça.
        tamanho="inteira",
        load=carregar,
        select=projetar,
        commands={
            "movimento_estorno": CommandDef(
                endpoint="/api/comandos/movimento_estorno",
                # O mesmo schema que o comando valida. Uma definição só.
                schema=EntradaEstorno,
                requires="movimento.estornar",
                confirm=True,
                idempotent=False,
            )
        },
    )
)
