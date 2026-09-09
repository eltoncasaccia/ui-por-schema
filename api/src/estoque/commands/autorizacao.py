"""A segunda identidade. T-030 — RN-C01, RN-A04, RN-M02, RN-M01.

O unico fluxo de duas pessoas do ciclo 1, e o teste mais afiado do ADR-0002:
**nenhuma saida de modelo conclui esta operacao.** Cleide submete (T-028), o
movimento fica `aguardando_autorizacao` e o saldo nao se mexe; Helena autoriza
aqui, e so' entao o estoque muda.

**Tres camadas recusam a mesma pessoa fazendo as duas coisas** (RN-A04), e as
tres existem porque a separacao de funcoes tem peso regulatorio:

  1. `requires` — `controlado.autorizar` so' existe no papel `rt`.
  2. `negar_se_mesma_pessoa` — o dominio, aqui, com a identidade real.
  3. O CHECK `autorizador_id <> autor_id` da migracao 0001 — o banco, que nao
     depende de nenhum caminho de codigo ter lembrado.

**A efetivacao reconfere o saldo.** Entre a submissao e a autorizacao pode ter
passado dias, e outras saidas podem ter esvaziado o lote. Efetivar sem reconferir
levaria o saldo a negativo em nome de uma decisao tomada sobre um estoque que nao
existe mais — `RN-M01` vale no instante em que o movimento passa a contar, nao no
instante em que foi pedido.
"""

from typing import Any

import sqlalchemy as sa

from estoque.autorizacao.motor import negar_se_mesma_pessoa
from estoque.commands.entradas.autorizacao import MOTIVO_MINIMO, EntradaAutorizacao
from estoque.commands.pipeline import etag_de_valores, registrar
from estoque.commands.saida import _saldo, _travar_lote
from estoque.commands.tipos import Comando, ContextoComando, Efeito
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio, nao_encontrado
from estoque.domain.regras.estados import resulta_negativo


async def _pendente_ou_falhar(movimento_id: str, ctx: ContextoComando) -> dict[str, Any]:
    """Le o movimento COM o escopo de unidade aplicado (RN-A01).

    A consulta e' direta porque a porta de dados nao expoe `movimento.por_id` —
    e acrescenta-la e' arquivo da T-007. O escopo, que e' o que importa, esta'
    aplicado aqui do mesmo jeito que o repositorio faria.
    """
    linha = (
        (
            await ctx.conn.execute(
                sa.select(m.movimento).where(
                    m.movimento.c.id == movimento_id,
                    m.movimento.c.unidade_id.in_(sorted(ctx.ator.unidades)),
                )
            )
        )
        .mappings()
        .first()
    )
    if linha is None:
        # Fora do escopo e inexistente saem pela mesma porta (ADR-0014).
        raise nao_encontrado({"movimento_id": movimento_id, "ator": ctx.ator.id})
    return dict(linha)


async def _etag_do_movimento(entrada: Any, ctx: ContextoComando) -> str | None:
    linha = (
        (
            await ctx.conn.execute(
                sa.select(
                    m.movimento.c.id, m.movimento.c.status, m.movimento.c.autorizador_id
                ).where(
                    m.movimento.c.id == entrada.movimento_id,
                    m.movimento.c.unidade_id.in_(sorted(ctx.ator.unidades)),
                )
            )
        )
        .mappings()
        .first()
    )
    return None if linha is None else etag_de_valores(dict(linha))


async def _aplicar(entrada: Any, ctx: ContextoComando) -> Efeito:
    mov = await _pendente_ou_falhar(entrada.movimento_id, ctx)

    motivo = entrada.motivo.strip()
    if len(motivo) < MOTIVO_MINIMO:
        raise ErroDominio(
            "invalido",
            f"O motivo precisa de ao menos {MOTIVO_MINIMO} caracteres.",
        )

    if mov["status"] != "aguardando_autorizacao":
        raise ErroDominio(
            "conflito",
            f"Este movimento já está {mov['status']}.",
            {"movimento_id": mov["id"], "status": mov["status"]},
        )

    # RN-A04 e RN-C01. A interface esconderia o botao para quem submeteu; aqui e'
    # a chamada direta que precisa ser recusada.
    negar_se_mesma_pessoa(str(mov["autor_id"]), ctx.ator.id)

    if entrada.decisao == "autorizar":
        # O saldo e' reconferido AGORA, e nao no momento da submissao.
        await _travar_lote(str(mov["lote_id"]), ctx)
        saldo = await _saldo(str(mov["lote_id"]), ctx)
        if resulta_negativo(saldo, int(mov["quantidade"])):
            raise ErroDominio(
                "conflito",
                f"Saldo insuficiente para efetivar: o lote tem {saldo} e o "
                f"movimento pede {mov['quantidade']}.",
                {"movimento_id": mov["id"], "saldo": saldo},
            )
        novo_status = "efetivado"
    else:
        # RN-M02: nada e' apagado. O movimento recusado FICA, com quem recusou e
        # por que — e continua fora do saldo, porque a view conta `efetivado`.
        saldo = await _saldo(str(mov["lote_id"]), ctx)
        novo_status = "recusado"

    await ctx.conn.execute(
        sa.update(m.movimento)
        .where(m.movimento.c.id == mov["id"])
        .values(status=novo_status, autorizador_id=ctx.ator.id)
    )

    return Efeito(
        entidade="movimento",
        entidade_id=str(mov["id"]),
        valor_anterior={"status": mov["status"], "autorizador_id": None, "saldo": saldo},
        valor_novo={
            "status": novo_status,
            "autorizador_id": ctx.ator.id,
            "autor_id": mov["autor_id"],
            "decisao": entrada.decisao,
            "motivo": motivo,
            "quantidade": mov["quantidade"],
            "lote_id": mov["lote_id"],
            "saldo_apos": saldo - int(mov["quantidade"])
            if novo_status == "efetivado"
            else saldo,
        },
        dados={
            "movimento_id": str(mov["id"]),
            "status": novo_status,
            "autor_id": mov["autor_id"],
            "autorizador_id": ctx.ator.id,
        },
    )


CONTROLADO_AUTORIZAR = registrar(
    Comando(
        nome="controlado_autorizar",
        requires=("controlado.autorizar",),
        schema=EntradaAutorizacao,
        aplicar=_aplicar,
        idempotent=False,
        confirm=True,
        etag_de=_etag_do_movimento,
    )
)
