"""Os dois comandos de escrita do lote. T-027 — RN-R02, RN-R03, RN-L05, §4.1.

**Por que estes comandos nao vivem junto do componente que os declara.**
`registry` nao pode importar `commands`: o pipeline usa SQLAlchemy, e o contrato
2 do import-linter proibe `registry -> sqlalchemy`, inclusive por caminho
indireto. A separacao acaba sendo a do ADR-0002 vista de outro angulo — o
componente DESCREVE o comando, este modulo o EXECUTA, e os dois lados se ligam
por nome, com a bijecao conferida em teste (`test_ac1_barreira.py`).

**Duas camadas recusam quem nao e' o RT, e as duas importam.**

  1. `requires` — `lote.liberar` e `lote.status` so' existem no papel `rt`
     (documento 02 §6). O pipeline recusa antes de tocar no banco.
  2. `transicao_valida` — a tabela §4.1 exige `papel == 'rt'` para cada
     transicao, INDEPENDENTE de quem tenha a permissao.

A segunda parece redundante e nao e'. Se um dia alguem acrescentar `lote.status`
ao Diretor por engano — uma linha num dicionario — a primeira camada passa a
deixar ele entrar, e e' a segunda que continua recusando. `RN-R02` diz "nenhum
outro papel, em nenhuma circunstancia", e uma regra assim nao pode depender de
uma matriz de permissao continuar correta para sempre.
"""

from typing import Any

import sqlalchemy as sa

from estoque.application.commands.entradas.lote import EntradaLiberacao, EntradaStatus
from estoque.application.commands.pipeline import etag_de_valores, registrar
from estoque.application.commands.tipos import Comando, ContextoComando, Efeito
from estoque.data import modelos as m
from estoque.data.porta import ContextoDados
from estoque.data.repositorios import RepoLoteSQL, RepoProdutoSQL
from estoque.domain.erros import ErroDominio, nao_encontrado
from estoque.domain.regras.estados import EventoLote, aplicar_transicao, transicao_valida
from estoque.domain.regras.validade import classificar_validade
from estoque.domain.tipos import Lote, Produto

# `justificativa` nunca e' opcional: toda acao do RT sobre um lote e' decisao
# registrada, e decisao sem motivo registrado nao e' auditavel (RN-D01).
JUSTIFICATIVA_MINIMA = 10


class _Tx:
    """A transacao pertence ao pipeline; o repositorio so' precisa da forma."""

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


def _contexto_de_dados(ctx: ContextoComando) -> ContextoDados:
    """Escopo de unidade (RN-A01) tambem na escrita.

    O comando vai pela mesma porta que a leitura. Um RT com escopo restrito nao
    libera lote de unidade que nao alcanca — e o `None` de fora de escopo e'
    indistinguivel de inexistente (ADR-0014).
    """
    return ContextoDados(ator=ctx.ator, unidades_permitidas=ctx.ator.unidades, tx=_Tx())


async def _lote_ou_falhar(lote_id: str, ctx: ContextoComando) -> Lote:
    lote = await RepoLoteSQL(ctx.conn).por_id(lote_id, _contexto_de_dados(ctx))
    if lote is None:
        raise nao_encontrado({"lote_id": lote_id, "ator": ctx.ator.id})
    return lote


async def _produto_do_lote(lote: Lote, ctx: ContextoComando) -> Produto | None:
    return await RepoProdutoSQL(ctx.conn).por_id(lote.produto_id, _contexto_de_dados(ctx))


async def _etag_do_lote(entrada: Any, ctx: ContextoComando) -> str | None:
    """Etag do estado corrente. `None` quando o lote nao existe ou esta' fora
    do escopo — o pipeline traduz para `nao_encontrado`, sem distinguir."""
    lote = await RepoLoteSQL(ctx.conn).por_id(entrada.lote_id, _contexto_de_dados(ctx))
    if lote is None:
        return None
    return etag_de_valores(
        {
            "id": lote.id,
            "status": lote.status,
            "validade": lote.validade,
            "endereco": lote.endereco,
        }
    )


async def _gravar_status(lote: Lote, novo: str, ctx: ContextoComando) -> None:
    await ctx.conn.execute(sa.update(m.lote).where(m.lote.c.id == lote.id).values(status=novo))


def _transicionar(lote: Lote, evento: EventoLote, ctx: ContextoComando) -> Lote:
    """§4.1, com o papel real. Recusa fora da tabela, inclusive para o Diretor."""
    if not transicao_valida(lote.status, evento, ctx.ator.papel):
        # `conflito`: regra de estado violada (CONTRATOS §2). A mensagem diz o
        # estado atual, que o proprio ator ja' ve na tela, e nao diz quem pode —
        # enumerar papeis autorizados e' informacao que nao ajuda quem opera.
        raise ErroDominio(
            "conflito",
            f"Esta ação não se aplica a um lote em {lote.status}.",
            {"de": lote.status, "evento": evento, "papel": ctx.ator.papel},
        )
    return aplicar_transicao(lote, evento, ctx.ator.papel)


def _exigir_justificativa(texto: str) -> str:
    limpo = texto.strip()
    if len(limpo) < JUSTIFICATIVA_MINIMA:
        raise ErroDominio(
            "invalido",
            f"A justificativa precisa de ao menos {JUSTIFICATIVA_MINIMA} caracteres.",
        )
    return limpo


# ------------------------------------------------- liberação da quarentena
def _checklist_pendente(entrada: EntradaLiberacao, termolabil: bool) -> list[str]:
    """RN-R03. A temperatura so' entra na conta se o produto for termolabil —
    exigir de todos treinaria o RT a marcar tudo sem ler."""
    faltando = []
    if not entrada.integridade_conferida:
        faltando.append("integridade da embalagem")
    if not entrada.validade_conferida:
        faltando.append("validade mínima")
    if not entrada.nota_fiscal_conferida:
        faltando.append("nota fiscal")
    if termolabil and not entrada.temperatura_conferida:
        faltando.append("temperatura de chegada")
    return faltando


async def _aplicar_liberacao(entrada: Any, ctx: ContextoComando) -> Efeito:
    lote = await _lote_ou_falhar(entrada.lote_id, ctx)
    justificativa = _exigir_justificativa(entrada.justificativa)

    if entrada.decisao == "liberar":
        produto = await _produto_do_lote(lote, ctx)
        termolabil = produto is not None and produto.classe == "termolabil"
        pendente = _checklist_pendente(entrada, termolabil)
        if pendente:
            # RN-R03. A recusa NOMEIA o que falta: aqui a informacao ajuda quem
            # opera e nao ajuda ninguem mais — o proprio RT preencheu o resto.
            raise ErroDominio(
                "invalido",
                "Conferência incompleta: falta " + ", ".join(pendente) + ".",
            )
        evento: EventoLote = "liberacao"
    else:
        evento = "reprovacao"

    novo = _transicionar(lote, evento, ctx)
    await _gravar_status(lote, novo.status, ctx)

    return Efeito(
        entidade="lote",
        entidade_id=lote.id,
        valor_anterior={"status": lote.status},
        valor_novo={
            "status": novo.status,
            "decisao": entrada.decisao,
            "justificativa": justificativa,
            "conferencia": {
                "integridade": entrada.integridade_conferida,
                "validade": entrada.validade_conferida,
                "nota_fiscal": entrada.nota_fiscal_conferida,
                "temperatura": entrada.temperatura_conferida,
            },
        },
        dados={"lote_id": lote.id, "status": novo.status, "decisao": entrada.decisao},
    )


LIBERAR_QUARENTENA = registrar(
    Comando(
        nome="lote_liberar_quarentena",
        requires=("lote.liberar",),
        schema=EntradaLiberacao,
        aplicar=_aplicar_liberacao,
        # Repetir NAO e' inofensivo: a segunda chamada encontraria o lote fora
        # de `quarentena` e a transicao falharia com `conflito` — erro confuso
        # para o que e' apenas a rede tendo repetido. Com a chave, a repeticao
        # devolve a mesma resposta.
        idempotent=False,
        confirm=True,
        etag_de=_etag_do_lote,
    )
)


# ------------------------------------------------------- bloqueio e status
_EVENTO_DA_ACAO: dict[str, EventoLote] = {
    "bloquear": "bloqueio",
    "desbloquear": "desbloqueio",
}


async def _aplicar_status(entrada: Any, ctx: ContextoComando) -> Efeito:
    lote = await _lote_ou_falhar(entrada.lote_id, ctx)
    justificativa = _exigir_justificativa(entrada.justificativa)

    if entrada.acao == "liberar_vencimento":
        return await _liberar_vencimento(lote, justificativa, ctx)

    novo = _transicionar(lote, _EVENTO_DA_ACAO[entrada.acao], ctx)
    await _gravar_status(lote, novo.status, ctx)
    return Efeito(
        entidade="lote",
        entidade_id=lote.id,
        valor_anterior={"status": lote.status},
        valor_novo={
            "status": novo.status,
            "acao": entrada.acao,
            "justificativa": justificativa,
        },
        dados={"lote_id": lote.id, "status": novo.status, "acao": entrada.acao},
    )


async def _liberar_vencimento(lote: Lote, justificativa: str, ctx: ContextoComando) -> Efeito:
    """RN-L05 — e a unica acao daqui que NAO muda o status registrado.

    "Lote com validade <= 30 dias e' bloqueado automaticamente para venda. So' o
    RT libera, com justificativa." O bloqueio e' DERIVADO da data (ADR-0022): nao
    ha coluna para ele, e portanto nao ha coluna para desfaze-lo.

    A autorizacao do RT persiste como fato da trilha de auditoria, que e'
    append-only e tem o peso regulatorio certo. Nao ha documento do projeto
    dizendo onde ela deveria morar — ver achado A-14. Quem for consumir isso e' a
    saida (T-028), consultando a trilha; se essa consulta nao couber em T-028, a
    decisao vira ADR e uma coluna.
    """
    # `ctx.agora`, nunca `date.today()`: a hora e' a do servidor, injetada uma
    # vez pelo pipeline (RN-M04). Um comando que le o proprio relogio tem uma
    # nocao de 'hoje' diferente da que a auditoria registrou.
    situacao = classificar_validade(lote, ctx.agora.date())
    if situacao == "vencido":
        # RN-L06 e' mais forte que RN-L05: lote vencido nao sai por nenhum
        # motivo, exceto descarte. Deixar o RT "liberar o vencimento" de um lote
        # que JA' venceu daria a ele um botao que promete o que a regra proibe.
        raise ErroDominio(
            "conflito",
            "Este lote já venceu: não há liberação possível (RN-L06). O caminho é o descarte.",
            {"lote_id": lote.id},
        )
    if situacao != "bloqueio_30":
        raise ErroDominio(
            "invalido",
            "Este lote não está na janela de 30 dias: não há bloqueio por "
            "validade para liberar.",
            {"lote_id": lote.id, "situacao": situacao},
        )
    if lote.status != "liberado":
        # Um lote em quarentena ou bloqueado tem outro impedimento antes deste;
        # liberar a validade dele nao o tornaria vendavel, e daria a impressao
        # contraria a quem clicou.
        raise ErroDominio(
            "conflito",
            f"Esta ação não se aplica a um lote em {lote.status}.",
            {"status": lote.status},
        )
    return Efeito(
        entidade="lote",
        entidade_id=lote.id,
        valor_anterior={"venda_autorizada_no_vencimento": False},
        valor_novo={
            "venda_autorizada_no_vencimento": True,
            "acao": "liberar_vencimento",
            "justificativa": justificativa,
            "validade": lote.validade.isoformat(),
        },
        dados={"lote_id": lote.id, "status": lote.status, "acao": "liberar_vencimento"},
    )


STATUS_ACAO = registrar(
    Comando(
        nome="lote_status",
        requires=("lote.status",),
        schema=EntradaStatus,
        aplicar=_aplicar_status,
        idempotent=False,
        confirm=True,
        etag_de=_etag_do_lote,
    )
)
