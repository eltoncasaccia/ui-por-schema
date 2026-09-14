"""O estorno. T-029 — RN-M02, RN-M03, RN-M05, RN-M06, RN-D01.

**Corrigir sem apagar.** O original nao e' tocado: `RN-M02` nao e' uma checagem
que este modulo faz, e' a ausencia de qualquer caminho que edite movimento — o
papel da aplicacao nao tem `UPDATE` nem `DELETE` em `movimento` (migracao 0001),
e o unico `UPDATE` que existe e' o da autorizacao de controlado, preso a um
gatilho (migracao 0004). Aqui so' ha' `INSERT`.

**Por que so' SAIDA se estorna no ciclo 1.** O sinal do estorno e' fixo e
positivo — `saldo_lote`, na migracao 0001, soma `estorno` junto com `entrada`, e
o esquema esta' congelado (CONTRATOS §3). Um estorno de ENTRADA precisaria
subtrair, e nao ha' como dizer isso no tipo: gravado como esta', ele SOMARIA de
novo a quantidade que se queria desfazer. Entrada errada, portanto, nao tem
correcao no ciclo 1 — e' o achado A-38, e o caminho recusa dizendo isso, em vez
de gravar um saldo errado em silencio.

**O que a trava do lote protege.** Dois estornos simultaneos do mesmo movimento
leem "ainda nao estornado" e os dois passam, dobrando o saldo devolvido. Nao ha'
UNIQUE em `estorna_movimento_id` — o esquema esta' congelado —, entao a
serializacao por lote e' o que resta, e e' a mesma trava que a saida usa.
"""

import secrets
from typing import Any

import sqlalchemy as sa

from estoque.application.commands.entradas.estorno import (
    COMPLEMENTO_MINIMO,
    TIPOS_ESTORNAVEIS,
    EntradaEstorno,
)
from estoque.application.commands.pipeline import registrar
from estoque.application.commands.saida import _saldo, _travar_lote
from estoque.application.commands.tipos import Comando, ContextoComando, Efeito
from estoque.application.etag import etag_movimento_estorno
from estoque.data import modelos as m
from estoque.data.repositorios import _para_movimento
from estoque.domain.erros import ErroDominio, nao_encontrado
from estoque.domain.regras.estados import ja_estornado, montar_estorno
from estoque.domain.tipos import Movimento


async def _movimentos_do_lote(lote_id: str, ctx: ContextoComando) -> list[Movimento]:
    """Todos os movimentos do lote, ja' na forma do dominio.

    Passa pelo `_para_movimento` do adaptador de proposito: um mapeador proprio
    aqui divergiria do que a leitura entrega no dia em que a tabela mudar, que e'
    a familia do achado A-11.
    """
    linhas = (
        (await ctx.conn.execute(sa.select(m.movimento).where(m.movimento.c.lote_id == lote_id)))
        .mappings()
        .all()
    )
    return [_para_movimento(dict(linha)) for linha in linhas]


async def _original_ou_falhar(movimento_id: str, ctx: ContextoComando) -> Movimento:
    """Le o movimento COM o escopo de unidade aplicado (RN-A01).

    A porta de dados nao expoe `movimento.por_id` — acrescenta-la e' arquivo da
    T-007. O escopo, que e' o que importa, esta' aplicado aqui do mesmo jeito que
    o repositorio faria.
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
    return _para_movimento(dict(linha))


def _recusar_se_nao_estornavel(original: Movimento, irmaos: list[Movimento]) -> None:
    """As quatro recusas de `RN-M03`, e cada uma tem par negativo em teste.

    A ordem e' do mais especifico para o mais generico: dizer "ja' estornado" a
    quem tenta estornar um estorno seria verdade e nao ajudaria ninguem.
    """
    if original.tipo == "estorno":
        raise ErroDominio(
            "conflito",
            "Um estorno não se estorna: para desfazer a correção, registre a "
            "operação de novo (RN-M03).",
            {"movimento_id": original.id},
        )
    if original.tipo not in TIPOS_ESTORNAVEIS:
        # Ver a docstring do modulo, e o achado A-38.
        raise ErroDominio(
            "conflito",
            f"Movimento de {original.tipo} não tem estorno neste ciclo: o estorno "
            "devolve saldo, e devolver não corrige uma entrada.",
            {"movimento_id": original.id, "tipo": original.tipo},
        )
    if original.status != "efetivado":
        # Um controlado pendente nao mexeu no saldo (RN-C01): estorna-lo devolveria
        # mercadoria que nunca saiu. O caminho dele e' a RECUSA, em T-030.
        raise ErroDominio(
            "conflito",
            f"Este movimento está {original.status} e não teve efeito no saldo.",
            {"movimento_id": original.id, "status": original.status},
        )
    if ja_estornado(original, irmaos):
        raise ErroDominio(
            "conflito",
            "Este movimento já foi estornado.",
            {"movimento_id": original.id},
        )


async def _etag_do_original(entrada: Any, ctx: ContextoComando) -> str | None:
    """Etag sobre o estado que a decisao usou: o movimento e o fato de ele ja'
    ter sido corrigido ou nao.

    Se outra pessoa estornou entre a leitura da tela e o envio, `estornado` mudou
    e o `If-Match` nao bate — o operador recarrega em vez de duplicar a correcao.
    """
    linha = (
        (
            await ctx.conn.execute(
                sa.select(
                    m.movimento.c.id,
                    m.movimento.c.status,
                    m.movimento.c.lote_id,
                    m.movimento.c.quantidade,
                ).where(
                    m.movimento.c.id == entrada.movimento_id,
                    m.movimento.c.unidade_id.in_(sorted(ctx.ator.unidades)),
                )
            )
        )
        .mappings()
        .first()
    )
    if linha is None:
        return None
    estornado = (
        await ctx.conn.execute(
            sa.select(sa.func.count())
            .select_from(m.movimento)
            .where(m.movimento.c.estorna_movimento_id == entrada.movimento_id)
        )
    ).scalar_one()
    return etag_movimento_estorno(
        linha["id"],
        linha["status"],
        linha["lote_id"],
        linha["quantidade"],
        estornado=bool(estornado),
    )


async def _aplicar(entrada: Any, ctx: ContextoComando) -> Efeito:
    original = await _original_ou_falhar(entrada.movimento_id, ctx)

    complemento = entrada.complemento.strip()
    if len(complemento) < COMPLEMENTO_MINIMO:
        raise ErroDominio(
            "invalido",
            f"O estorno precisa de uma explicação de ao menos {COMPLEMENTO_MINIMO} "
            "caracteres além do motivo (RN-M05).",
        )

    # A trava vem ANTES da leitura que decide: ler primeiro e travar depois
    # deixaria a janela aberta exatamente onde ela importa.
    await _travar_lote(original.lote_id, ctx)
    irmaos = await _movimentos_do_lote(original.lote_id, ctx)
    _recusar_se_nao_estornavel(original, irmaos)

    saldo = await _saldo(original.lote_id, ctx)
    # `montar_estorno` e' a regra `RN-M03` em forma de funcao pura (T-008): ela
    # copia lote, unidade e quantidade do original, aponta para ele e recusa o
    # que nao se estorna. Construir a linha aqui a mao seria a segunda
    # implementacao da mesma regra.
    novo = montar_estorno(
        original,
        motivo=entrada.motivo,
        autor_id=ctx.ator.id,
        novo_id=f"mov-{secrets.token_hex(8)}",
        agora=ctx.agora,  # RN-M04 — do servidor, via pipeline
    )

    await ctx.conn.execute(
        sa.insert(m.movimento).values(
            id=novo.id,
            lote_id=novo.lote_id,
            unidade_id=novo.unidade_id,
            tipo=novo.tipo,
            quantidade=novo.quantidade,  # positiva; o sinal vem do tipo
            motivo=novo.motivo,
            complemento=complemento,
            autor_id=novo.autor_id,
            # Estorno nao tem segunda identidade: quem corrige assina sozinho. A
            # dupla identificacao existe para controlado (RN-C01) e para o
            # descarte (§4.1), que destroem ou movem mercadoria de verdade.
            autorizador_id=None,
            status=novo.status,
            criado_em=novo.criado_em,
            estorna_movimento_id=novo.estorna_movimento_id,
            cliente_id=None,
            nota_fiscal=None,
        )
    )

    return Efeito(
        entidade="movimento",
        entidade_id=novo.id,
        # O valor anterior descreve o SALDO, nao o original: o original nao muda
        # (RN-M02), e o que a trilha precisa reconstruir e' o efeito no lote.
        valor_anterior={"lote_id": original.lote_id, "saldo": saldo},
        valor_novo={
            "movimento_id": novo.id,
            "estorna_movimento_id": original.id,
            "lote_id": original.lote_id,
            "quantidade": novo.quantidade,
            "motivo": entrada.motivo,
            "complemento": complemento,
            "saldo_apos": saldo + novo.quantidade,
        },
        dados={
            "movimento_id": novo.id,
            "estorna_movimento_id": original.id,
            "lote_id": original.lote_id,
            "saldo_apos": saldo + novo.quantidade,
        },
    )


MOVIMENTO_ESTORNO = registrar(
    Comando(
        nome="movimento_estorno",
        requires=("movimento.estornar",),
        schema=EntradaEstorno,
        aplicar=_aplicar,
        # Repetir DUPLICA a devolucao de saldo. O `ja_estornado` recusa a segunda
        # chamada, mas com erro de conflito — que e' resposta confusa para o que
        # foi apenas a rede repetindo. Com a chave, a repeticao devolve a mesma
        # resposta.
        idempotent=False,
        confirm=True,
        etag_de=_etag_do_original,
    )
)
