"""A saida de estoque. T-028 — RN-L02, RN-L03, RN-L05, RN-L06, RN-M01, RN-M04, RN-C01.

O movimento mais frequente do sistema, e o que carrega mais regra por operacao.
Sete recusas antes de gravar, e cada uma existe porque a mercadoria que sai sem
ela nao volta.

**Por que o saldo NAO vem de `repos.lote.saldos`.** Aquela funcao le a view
materializada `saldo_lote`, e a view so' e' atualizada por `REFRESH MATERIALIZED
VIEW` — que o papel `estoque_app` nao tem privilegio para executar (achado A-20,
conferido no banco). Depois da primeira escrita pela aplicacao, a view fica para
tras e nunca se recupera sozinha. Ler dela para decidir uma escrita seria decidir
com dado velho, e o dado velho aqui autoriza vender o que ja' saiu.

Aqui o saldo vem da soma dos movimentos `efetivado`, que e' a fonte. E' mais
cara e e' a certa.

**Por que `FOR UPDATE`.** `RN-M01` — saldo nunca fica negativo — nao sobrevive a
duas saidas simultaneas se cada uma le o saldo e decide sozinha: as duas veem 10,
as duas tiram 8, e o lote fecha em -6. O bloqueio da linha do lote serializa as
saidas do mesmo lote, e so' delas.

**Controlado nao muda saldo** (RN-C01, e a base do CA-04). O movimento nasce em
`aguardando_autorizacao`, e a view de saldo — assim como a soma aqui — conta
apenas `efetivado`. Se o saldo mudasse na submissao e "voltasse" caso a
autorizacao nao viesse, a dupla identificacao seria teatro: a mercadoria ja' teria
saido do estoque contabil com uma identificacao so'.
"""

import secrets
from datetime import date
from typing import Any

import sqlalchemy as sa

from estoque.application.commands.entradas.saida import JUSTIFICATIVA_MINIMA, EntradaSaida
from estoque.application.commands.pipeline import registrar
from estoque.application.commands.tipos import Comando, ContextoComando, Efeito
from estoque.application.etag import etag_lote_e_saldo
from estoque.data import modelos as m
from estoque.data.porta import ContextoDados
from estoque.data.repositorios import RepoLoteSQL, RepoProdutoSQL
from estoque.domain.erros import ErroDominio, nao_encontrado
from estoque.domain.regras.estados import resulta_negativo
from estoque.domain.regras.fefo import exige_justificativa_fefo, propor_fefo
from estoque.domain.regras.validade import classificar_validade, status_efetivo
from estoque.domain.tipos import Lote, Produto


class _Tx:
    """A transacao pertence ao pipeline; o repositorio so' precisa da forma."""

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


def _dados(ctx: ContextoComando) -> ContextoDados:
    """Escopo de unidade (RN-A01) tambem na escrita — a mesma porta da leitura."""
    return ContextoDados(ator=ctx.ator, unidades_permitidas=ctx.ator.unidades, tx=_Tx())


# --------------------------------------------------------------- saldo real
async def _saldo(lote_id: str, ctx: ContextoComando) -> int:
    """A soma dos movimentos `efetivado`. A FONTE, nao a view materializada.

    `aguardando_autorizacao` e `recusado` ficam de fora — e' o que faz o
    controlado pendente nao mexer no saldo (RN-C01).
    """
    total = (
        await ctx.conn.execute(
            sa.select(
                sa.func.coalesce(
                    sa.func.sum(
                        sa.case(
                            (
                                m.movimento.c.tipo.in_(("entrada", "estorno")),
                                m.movimento.c.quantidade,
                            ),
                            else_=-m.movimento.c.quantidade,
                        )
                    ),
                    0,
                )
            ).where(
                m.movimento.c.lote_id == lote_id,
                m.movimento.c.status == "efetivado",
            )
        )
    ).scalar_one()
    return int(total)


async def _travar_lote(lote_id: str, ctx: ContextoComando) -> None:
    """Serializa as saidas DESTE lote, e so' dele.

    Sem o bloqueio, duas saidas concorrentes leem o mesmo saldo e as duas passam
    na checagem de `RN-M01`. A janela e' pequena e o estoque e' regulado: pequena
    nao e' zero.
    """
    await ctx.conn.execute(
        sa.select(m.lote.c.id).where(m.lote.c.id == lote_id).with_for_update()
    )


# --------------------------------------------- RN-L05, via trilha (achado A-14)
async def _venda_autorizada_no_vencimento(lote_id: str, ctx: ContextoComando) -> bool:
    """A autorizacao do RT para vender lote a menos de 30 dias do vencimento.

    Ela nao tem coluna: o bloqueio de `RN-L05` e' DERIVADO da data (ADR-0022), e
    o que e' derivado nao tem onde ser desfeito. T-027 gravou a decisao na trilha
    de auditoria, que e' append-only e tem o peso regulatorio certo — ver o
    achado A-14 no BOARD. Aqui ela e' lida de volta.

    Consequencia aceita: a autorizacao nao e' revogavel, porque a trilha nao se
    edita. Se o RT mudar de ideia, o caminho e' bloquear o lote (`lote_status`),
    que impede a saida por outro motivo e fica registrado como decisao nova.
    """
    achou = (
        await ctx.conn.execute(
            sa.select(sa.func.count())
            .select_from(m.auditoria)
            .where(
                m.auditoria.c.entidade == "lote",
                m.auditoria.c.entidade_id == lote_id,
                # `.as_boolean()`, e nao `.astext`: a coluna e' declarada `sa.JSON`
                # em `modelos.py`, nao `JSONB` — `.astext` e' do dialeto e nao
                # existe aqui. `as_boolean` e' o acessor tipado do SQLAlchemy, e
                # chave ausente vira NULL, que nao casa.
                m.auditoria.c.valor_novo["venda_autorizada_no_vencimento"]
                .as_boolean()
                .is_(True),
            )
        )
    ).scalar_one()
    return bool(achou)


# ------------------------------------------------------------------- recusas
async def _lote_ou_falhar(lote_id: str, ctx: ContextoComando) -> Lote:
    lote = await RepoLoteSQL(ctx.conn).por_id(lote_id, _dados(ctx))
    if lote is None:
        # Fora do escopo e inexistente saem pela mesma porta (ADR-0014).
        raise nao_encontrado({"lote_id": lote_id, "ator": ctx.ator.id})
    return lote


async def _recusar_se_nao_pode_sair(
    lote: Lote, saldo: int, hoje: date, ctx: ContextoComando
) -> None:
    """RN-L06 e RN-L05, nesta ordem — e a ordem importa.

    Vencido, bloqueado, em quarentena ou esgotado nao sai: `status_efetivo`
    responde por todos de uma vez (ADR-0022). A mensagem diz o estado, que o
    proprio operador ve na tela, e nao diz de que unidade nem de quem e'.
    """
    efetivo = status_efetivo(lote, saldo, hoje)
    if efetivo != "liberado":
        raise ErroDominio(
            "conflito",
            f"Este lote está {efetivo} e não pode ter saída.",
            {"lote_id": lote.id, "status_efetivo": efetivo},
        )

    if classificar_validade(
        lote, hoje
    ) == "bloqueio_30" and not await _venda_autorizada_no_vencimento(lote.id, ctx):
        raise ErroDominio(
            "conflito",
            "Lote a menos de 30 dias do vencimento: a venda depende de "
            "liberação do responsável técnico (RN-L05).",
            {"lote_id": lote.id},
        )


async def _recusar_se_fefo_ignorado(
    lote: Lote, entrada: Any, ctx: ContextoComando
) -> str | None:
    """RN-L02 e RN-L03.

    A proposta e' recalculada AQUI, no servidor, e nao vem do cliente. Se viesse,
    bastaria o formulario mandar `proposta = lote_escolhido` para a justificativa
    nunca ser exigida — e a regra existe justamente para o caso em que alguem
    quer pular a fila.
    """
    hoje = ctx.agora.date()
    irmaos = list(
        await RepoLoteSQL(ctx.conn).listar(
            _dados(ctx), produto_id=lote.produto_id, unidade_id=lote.unidade_id
        )
    )
    saldos = {irmao.id: await _saldo(irmao.id, ctx) for irmao in irmaos}
    # ACHADO A-21: `propor_fefo` implementa RN-L02 e nao conhece RN-L05. Sozinha,
    # ela propoe o lote de menor validade — que muitas vezes e' justamente o que
    # esta' dentro dos 30 dias e NAO pode ser vendido sem liberacao do RT.
    #
    # O sistema estaria propondo o que ele proprio recusa, e cobrando
    # justificativa de quem escolhesse o lote certo. A proposta e' calculada
    # entre os que podem SAIR de fato.
    vendaveis = [
        irmao
        for irmao in irmaos
        if classificar_validade(irmao, hoje) != "bloqueio_30"
        or await _venda_autorizada_no_vencimento(irmao.id, ctx)
    ]
    proposta = propor_fefo(vendaveis, saldos, hoje)

    if not exige_justificativa_fefo(lote, proposta):
        return None

    texto = (entrada.justificativa_fefo or "").strip()
    if len(texto) < JUSTIFICATIVA_MINIMA:
        raise ErroDominio(
            "invalido",
            "Este não é o lote de menor validade disponível. Separar outro exige "
            f"justificativa de ao menos {JUSTIFICATIVA_MINIMA} caracteres (RN-L03).",
            {"escolhido": lote.id, "proposto": proposta.id if proposta else None},
        )
    return texto


# ------------------------------------------------------------------- etag
async def _etag_da_saida(entrada: Any, ctx: ContextoComando) -> str | None:
    """Etag sobre o estado que a decisao usou: status do lote E saldo.

    Se outra pessoa deu saida entre a leitura da tela e o envio, o saldo mudou e
    o etag nao bate — o operador recarrega e decide de novo, em vez de confirmar
    uma quantidade que ja' nao existe.
    """
    lote = await RepoLoteSQL(ctx.conn).por_id(entrada.lote_id, _dados(ctx))
    if lote is None:
        return None
    return etag_lote_e_saldo(lote, await _saldo(lote.id, ctx))


# ---------------------------------------------------------------- aplicar
async def _produto(lote: Lote, ctx: ContextoComando) -> Produto | None:
    return await RepoProdutoSQL(ctx.conn).por_id(lote.produto_id, _dados(ctx))


async def _aplicar(entrada: Any, ctx: ContextoComando) -> Efeito:
    lote = await _lote_ou_falhar(entrada.lote_id, ctx)
    # O bloqueio vem ANTES de ler o saldo: ler primeiro e travar depois deixaria
    # a janela aberta exatamente onde ela importa.
    await _travar_lote(lote.id, ctx)

    saldo = await _saldo(lote.id, ctx)
    await _recusar_se_nao_pode_sair(lote, saldo, ctx.agora.date(), ctx)
    justificativa = await _recusar_se_fefo_ignorado(lote, entrada, ctx)

    if resulta_negativo(saldo, entrada.quantidade):
        # RN-M01. A mensagem diz o saldo do lote que o operador ja' esta' vendo;
        # nao revela saldo de nada que ele nao pediu.
        raise ErroDominio(
            "conflito",
            f"Saldo insuficiente: o lote tem {saldo} e a saída pede {entrada.quantidade}.",
            {"lote_id": lote.id, "saldo": saldo},
        )

    produto = await _produto(lote, ctx)
    controlado = produto is not None and produto.classe == "controlado"
    # RN-C01: nasce pendente, e o saldo nao se mexe ate T-030 autorizar.
    status = "aguardando_autorizacao" if controlado else "efetivado"

    mid = f"mov-{secrets.token_hex(8)}"
    await ctx.conn.execute(
        sa.insert(m.movimento).values(
            id=mid,
            lote_id=lote.id,
            unidade_id=lote.unidade_id,
            tipo="saida",
            quantidade=entrada.quantidade,  # positiva; o sinal vem do tipo
            motivo=entrada.motivo,
            complemento=entrada.complemento,
            autor_id=ctx.ator.id,
            # A segunda identidade e' de quem AUTORIZA, e ainda nao existe.
            # Preenche-la aqui com o proprio autor violaria o CHECK do banco
            # (RN-A04) — e o CHECK esta' certo.
            autorizador_id=None,
            status=status,
            criado_em=ctx.agora,  # RN-M04 — do servidor, via pipeline
            estorna_movimento_id=None,
            cliente_id=entrada.cliente_id,
            nota_fiscal=entrada.nota_fiscal,
        )
    )

    return Efeito(
        entidade="movimento",
        entidade_id=mid,
        # Nao ha valor anterior: movimento e' append-only (RN-M02). O que muda
        # e' o saldo do lote, e ele vai aqui para a trilha reconstruir o efeito.
        valor_anterior={"lote_id": lote.id, "saldo": saldo},
        valor_novo={
            "movimento_id": mid,
            "lote_id": lote.id,
            "quantidade": entrada.quantidade,
            "motivo": entrada.motivo,
            "complemento": entrada.complemento,
            "status": status,
            "cliente_id": entrada.cliente_id,
            "nota_fiscal": entrada.nota_fiscal,
            "justificativa_fefo": justificativa,
            "saldo_apos": saldo if controlado else saldo - entrada.quantidade,
        },
        dados={
            "movimento_id": mid,
            "lote_id": lote.id,
            "status": status,
            "controlado": controlado,
            "saldo_apos": saldo if controlado else saldo - entrada.quantidade,
        },
    )


MOVIMENTO_SAIDA = registrar(
    Comando(
        nome="movimento_saida",
        requires=("movimento.criar",),
        schema=EntradaSaida,
        aplicar=_aplicar,
        # Repetir DUPLICA a saida — nao ha estado para a segunda chamada bater
        # como acontece na liberacao de quarentena. `Idempotency-Key` obrigatorio.
        idempotent=False,
        confirm=True,
        etag_de=_etag_da_saida,
    )
)
