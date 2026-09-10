"""O registro de recebimento. T-026 — RN-R01, R04, R05, L01, L07, F01, P02, P03.

**A regra que carrega o arquivo e' a `RN-R01`: todo recebimento entra em
quarentena, e nao existe entrada direta em estoque liberado.** Ela aparece em
tres lugares aqui, e os tres importam:

  1. o schema nao tem campo `status`, e recusa campo extra (`extra="forbid"`);
  2. o `INSERT` do lote escreve `"quarentena"` literal, sem vir de entrada;
  3. receber num lote que JA' EXISTE e nao esta' em quarentena e' **recusado** —
     senao a mercadoria cairia direto em estoque liberado por outro caminho, que
     e' exatamente o que a regra proibe.

O terceiro so' aparece porque o banco tem `UNIQUE (produto_id, numero,
unidade_id)`: dois recebimentos do mesmo numero de lote, mesmo produto, mesma
unidade, sao **o mesmo lote** (`RN-L08` visto do outro lado). Sem tratar isso, o
segundo recebimento estouraria a restricao e viraria 500.

**A validacao cruzada vive toda aqui, e nao no schema**, porque depende de dado:
a classe do produto decide se a temperatura e' obrigatoria (`RN-F01`) e se exige
RT (`RN-R05`); o tipo da unidade decide se o termolabil pode entrar (`RN-P02`); a
sala-cofre decide o controlado (`RN-P03`). Um schema que soubesse disso seria um
espelho do banco envelhecendo sozinho.
"""

import secrets
from typing import Any

import sqlalchemy as sa

from estoque.application.commands.entradas.recebimento import (
    DIAS_VALIDADE_MINIMA,
    EntradaRecebimento,
    ItemRecebido,
)
from estoque.application.commands.pipeline import registrar
from estoque.application.commands.tipos import Comando, ContextoComando, Efeito
from estoque.data import modelos as m
from estoque.data.porta import ContextoDados
from estoque.domain.erros import ErroDominio, nao_autorizado
from estoque.domain.tipos import Produto


class _Tx:
    """A transacao pertence ao pipeline; o repositorio so' precisa da forma."""

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


def _dados(ctx: ContextoComando) -> ContextoDados:
    return ContextoDados(ator=ctx.ator, unidades_permitidas=ctx.ator.unidades, tx=_Tx())


# --------------------------------------------------------------- leituras
async def _unidade_ou_falhar(unidade_id: str, ctx: ContextoComando) -> sa.Row[Any]:
    """Escopo de unidade tambem na escrita (`RN-A01`).

    A negativa e' EXPLICITA, e nao vazia: unidade e' escopo declarado, e o ator
    sabe que ela existe — e' a propria empresa dele (ADR-0014).
    """
    if unidade_id not in ctx.ator.unidades:
        raise nao_autorizado(f"a unidade {unidade_id}")
    linha = (
        await ctx.conn.execute(sa.select(m.unidade).where(m.unidade.c.id == unidade_id))
    ).first()
    if linha is None:
        raise ErroDominio("invalido", "Unidade desconhecida.", {"unidade_id": unidade_id})
    return linha


async def _produtos_ou_falhar(
    entrada: EntradaRecebimento, ctx: ContextoComando
) -> dict[str, Produto]:
    ids = sorted({item.produto_id for item in entrada.itens})
    linhas = (
        (await ctx.conn.execute(sa.select(m.produto).where(m.produto.c.id.in_(ids))))
        .mappings()
        .all()
    )
    achados = {
        str(r["id"]): Produto(
            id=str(r["id"]),
            ean=str(r["ean"]),
            nome=str(r["nome"]),
            fabricante=str(r["fabricante"]),
            principio_ativo=str(r["principio_ativo"]),
            classe=r["classe"],
            curva_abc=r["curva_abc"],
            ativo=bool(r["ativo"]),
        )
        for r in linhas
    }
    faltando = [i for i in ids if i not in achados]
    if faltando:
        # A mensagem NAO lista os ids: negativa nao vira catalogo do que existe
        # (`RN-A07`). O `detalhe_interno` leva a lista para o log.
        raise ErroDominio(
            "invalido",
            "Há item com produto desconhecido na nota.",
            {"produto_ids": faltando},
        )
    return achados


# ------------------------------------------------------------- validacoes
def _classes(entrada: EntradaRecebimento, produtos: dict[str, Produto]) -> set[str]:
    return {produtos[item.produto_id].classe for item in entrada.itens}


def _recusar_alocacao_invalida(
    entrada: EntradaRecebimento, produtos: dict[str, Produto], unidade: sa.Row[Any]
) -> None:
    """`RN-P02` e `RN-P03` — a mercadoria tem de caber na unidade.

    Sao regras de conservacao e de guarda legal, e a recusa e' `conflito` e nao
    `invalido`: o formulario esta' bem preenchido; o que nao se sustenta e' a
    combinacao produto × unidade.
    """
    classes = _classes(entrada, produtos)
    if "termolabil" in classes and unidade.tipo != "refrigerado":
        raise ErroDominio(
            "conflito",
            "Produto termolábil só pode entrar em unidade refrigerada (RN-P02).",
            {"unidade_id": entrada.unidade_id, "tipo": unidade.tipo},
        )
    if "controlado" in classes and not unidade.sala_cofre:
        raise ErroDominio(
            "conflito",
            "Produto controlado só pode entrar em unidade com sala-cofre (RN-P03).",
            {"unidade_id": entrada.unidade_id},
        )


def _recusar_cadeia_fria_sem_temperatura(
    entrada: EntradaRecebimento, produtos: dict[str, Produto]
) -> None:
    """`RN-F01`. Exigida so' quando ha termolabil: pedir a todos treinaria o
    conferente a digitar um numero qualquer, que e' pior que nao pedir."""
    if "termolabil" in _classes(entrada, produtos) and entrada.temperatura_chegada_c is None:
        raise ErroDominio(
            "invalido",
            "Recebimento de termolábil exige a temperatura de chegada da carga (RN-F01).",
        )


def _recusar_controlado_sem_dupla_identificacao(
    entrada: EntradaRecebimento, produtos: dict[str, Produto], ctx: ContextoComando
) -> None:
    """`RN-R05` — conferente **e** RT, e sao **duas pessoas**.

    O par negativo esta' na segunda checagem: um `rt_id` igual ao conferente
    passaria pela primeira e transformaria dupla identificacao em digitar o
    proprio nome duas vezes. E' o mesmo cuidado do `CHECK` que a T-030 pos no
    banco para a autorizacao de controlado (`RN-A04`).
    """
    if "controlado" not in _classes(entrada, produtos):
        return
    if not entrada.rt_id:
        raise ErroDominio(
            "invalido",
            "Recebimento de controlado exige a identificação do responsável técnico (RN-R05).",
        )
    if entrada.rt_id == ctx.ator.id:
        raise ErroDominio(
            "invalido",
            "A dupla identificação exige duas pessoas: o RT não pode ser o próprio conferente.",
            {"ator": ctx.ator.id},
        )


def _recusar_validade_curta(entrada: EntradaRecebimento, ctx: ContextoComando) -> list[str]:
    """`RN-L07`, e o "salvo" da regra é o ponto.

    Validade curta nao e' erro de digitacao: e' uma decisao comercial que o RT
    pode tomar. Sem a autorizacao, recusa; com ela, aceita **e registra** quais
    itens dependeram dela — a trilha precisa dizer o que foi autorizado, nao
    apenas que houve autorizacao.
    """
    limite = ctx.agora.date()
    curtos = [
        item.numero
        for item in entrada.itens
        if (item.validade - limite).days < DIAS_VALIDADE_MINIMA
    ]
    if curtos and not entrada.autorizacao_validade_rt:
        raise ErroDominio(
            "invalido",
            f"Há item com validade inferior a {DIAS_VALIDADE_MINIMA // 30} meses. "
            "É preciso a autorização expressa do RT (RN-L07).",
            {"numeros": curtos},
        )
    return curtos


# ---------------------------------------------------------------- escrita
async def _lote_existente(item: ItemRecebido, unidade_id: str, ctx: ContextoComando) -> Any:
    """O banco tem `UNIQUE (produto_id, numero, unidade_id)`: essa tripla E' a
    identidade do lote. Receber de novo o mesmo numero e' receber MAIS do mesmo
    lote, nao criar outro."""
    return (
        (
            await ctx.conn.execute(
                sa.select(m.lote).where(
                    m.lote.c.produto_id == item.produto_id,
                    m.lote.c.numero == item.numero,
                    m.lote.c.unidade_id == unidade_id,
                )
            )
        )
        .mappings()
        .first()
    )


async def _lote_para(
    item: ItemRecebido, entrada: EntradaRecebimento, ctx: ContextoComando
) -> str:
    """Devolve o id do lote que recebe a entrada — criando-o se preciso.

    **`RN-R01` no caminho menos obvio.** Se o lote ja' existe e NAO esta' em
    quarentena, acrescentar mercadoria a ele a colocaria direto em estoque
    liberado — "entrada direta em estoque liberado", que e' a coisa que a regra
    nomeia e proibe. A recusa e' `conflito`, e o operador investiga: ou o numero
    esta' errado, ou aquilo e' outro lote.
    """
    existente = await _lote_existente(item, entrada.unidade_id, ctx)
    if existente is not None:
        if existente["status"] != "quarentena":
            raise ErroDominio(
                "conflito",
                f"O lote {item.numero} já existe nesta unidade e está em "
                f"{existente['status']}. Receber nele seria entrada direta em "
                "estoque liberado (RN-R01).",
                {"lote_id": existente["id"], "status": existente["status"]},
            )
        return str(existente["id"])

    lote_id = f"lote-{secrets.token_hex(8)}"
    await ctx.conn.execute(
        sa.insert(m.lote).values(
            id=lote_id,
            produto_id=item.produto_id,
            numero=item.numero,
            unidade_id=entrada.unidade_id,
            fabricacao=item.fabricacao,
            validade=item.validade,
            # RN-R01: literal, nunca vindo da entrada. Nao ha campo no schema que
            # chegue aqui, e este e' o segundo dos tres lugares onde a regra vale.
            status="quarentena",
            endereco=item.endereco,
        )
    )
    return lote_id


async def _aplicar(entrada: Any, ctx: ContextoComando) -> Efeito:
    unidade = await _unidade_ou_falhar(entrada.unidade_id, ctx)
    produtos = await _produtos_ou_falhar(entrada, ctx)

    # A ordem importa para a mensagem que o operador recebe: alocacao invalida e'
    # problema da carga inteira, e nao adianta reclamar de temperatura antes.
    _recusar_alocacao_invalida(entrada, produtos, unidade)
    _recusar_cadeia_fria_sem_temperatura(entrada, produtos)
    _recusar_controlado_sem_dupla_identificacao(entrada, produtos, ctx)
    validade_curta = _recusar_validade_curta(entrada, ctx)

    # RN-R04: divergencia entre nota e fisico. NAO impede a conclusao — gera
    # pendencia vinculada ao recebimento, que e' a coluna `divergencia`.
    divergentes = [
        item.numero
        for item in entrada.itens
        if item.quantidade_nota is not None and item.quantidade_nota != item.quantidade
    ]

    recebimento_id = f"rec-{secrets.token_hex(8)}"
    await ctx.conn.execute(
        sa.insert(m.recebimento).values(
            id=recebimento_id,
            unidade_id=entrada.unidade_id,
            nota_fiscal=entrada.nota_fiscal,
            fornecedor=entrada.fornecedor,
            # `conferido`, nunca `liberado`: liberar e' decisao do RT sobre o
            # LOTE, e e' a T-027. Um recebimento que nascesse liberado tornaria
            # a quarentena decorativa.
            status="conferido",
            conferente_id=ctx.ator.id,
            rt_id=entrada.rt_id,
            temperatura_chegada_c=entrada.temperatura_chegada_c,
            divergencia=bool(divergentes),
            recebido_em=ctx.agora,  # RN-M04 — do servidor, via pipeline
        )
    )

    lotes: list[dict[str, Any]] = []
    for item in entrada.itens:
        lote_id = await _lote_para(item, entrada, ctx)
        movimento_id = f"mov-{secrets.token_hex(8)}"
        await ctx.conn.execute(
            sa.insert(m.movimento).values(
                id=movimento_id,
                lote_id=lote_id,
                unidade_id=entrada.unidade_id,
                tipo="entrada",
                quantidade=item.quantidade,  # positiva; o sinal vem do tipo
                motivo="recebimento",
                complemento=None,
                autor_id=ctx.ator.id,
                # A segunda identidade do recebimento vive no RECEBIMENTO
                # (`rt_id`), nao no movimento: aqui ela e' de quem autoriza uma
                # saida de controlado (RN-C01), que e' outra coisa.
                autorizador_id=None,
                status="efetivado",
                criado_em=ctx.agora,
                estorna_movimento_id=None,
                cliente_id=None,
                nota_fiscal=entrada.nota_fiscal,
            )
        )
        lotes.append(
            {
                "lote_id": lote_id,
                "numero": item.numero,
                "produto_id": item.produto_id,
                "quantidade": item.quantidade,
                "movimento_id": movimento_id,
            }
        )

    return Efeito(
        entidade="recebimento",
        entidade_id=recebimento_id,
        # Nao ha valor anterior: o recebimento nasce agora. O que a trilha
        # precisa reconstruir e' o que entrou e sob que autorizacao.
        valor_anterior=None,
        valor_novo={
            "recebimento_id": recebimento_id,
            "unidade_id": entrada.unidade_id,
            "nota_fiscal": entrada.nota_fiscal,
            "fornecedor": entrada.fornecedor,
            "conferente_id": ctx.ator.id,
            "rt_id": entrada.rt_id,
            "temperatura_chegada_c": entrada.temperatura_chegada_c,
            "divergencia": bool(divergentes),
            "itens_divergentes": divergentes,
            # RN-L07: o que foi aceito apesar da validade curta, e com que
            # autorizacao. "Houve autorizacao" sem dizer do que nao e' auditavel.
            "validade_curta_autorizada": validade_curta,
            "autorizacao_validade_rt": entrada.autorizacao_validade_rt,
            "lotes": lotes,
        },
        dados={
            "recebimento_id": recebimento_id,
            "divergencia": bool(divergentes),
            "lotes": [x["lote_id"] for x in lotes],
        },
    )


REGISTRAR_RECEBIMENTO = registrar(
    Comando(
        nome="recebimento_registrar",
        requires=("recebimento.criar",),
        schema=EntradaRecebimento,
        aplicar=_aplicar,
        # Repetir DUPLICA: cada chamada cria recebimento, lotes e movimentos
        # novos. Por isso `Idempotency-Key` deixa de ser cortesia e vira
        # obrigatorio na borda (CONTRATOS §8) — e a rede repete sozinha.
        idempotent=False,
        confirm=True,
        # Sem `etag_de`: e' CRIACAO, nao atualizacao. Nao ha estado anterior
        # contra o que comparar, e exigir `If-Match` aqui pediria ao cliente um
        # etag de uma entidade que ainda nao existe.
    )
)
