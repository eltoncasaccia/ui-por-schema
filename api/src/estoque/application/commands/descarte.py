"""O descarte. T-029 — RN-L06, RN-M02, RN-M05, RN-M06, §4.1.

A unica saida possivel para lote vencido ou bloqueado, e a unica operacao do
ciclo 1 que **destroi** mercadoria. Por isso duas assinaturas, e por isso o lote
termina em `descartado`, que e' estado terminal.

**Duas identidades, e o banco confere a terceira vez.** A §4.1 diz "Gerente +
RT". As camadas sao tres:

  1. `requires` — `movimento.descartar` (documento 02 §6);
  2. aqui: os dois papeis conferidos, e **diferentes entre si** — um gerente
     assinando com outro gerente nao e' o que a §4.1 pede;
  3. o `CHECK (autorizador_id <> autor_id)` da migracao 0001, que nao depende de
     nenhum caminho de codigo ter lembrado.

**Por que o Diretor nao descarta, mesmo tendo a permissao.** A matriz do §6 da'
`movimento.descartar` ao Diretor; a tabela §4.1 nao o inclui na transicao. Vale
a §4.1: a linha diz **quem** faz a transicao, e papel nao e' nivel, e' conjunto.
E' o mesmo desenho de duas camadas do `commands/lote.py` — a permissao deixa
entrar, a tabela de estados recusa.

**O saldo inteiro sai.** Descarte parcial deixaria o lote em `descartado` com
saldo positivo: o estado terminal passaria a mentir sobre o que ainda existe na
prateleira, e `RN-M06` (saldo e' a soma dos movimentos) faria a mentira aparecer
no relatorio, nao no estoque.
"""

import secrets
from typing import Any

import sqlalchemy as sa

from estoque.application.commands.entradas.descarte import (
    JUSTIFICATIVA_MINIMA,
    EntradaDescarte,
)
from estoque.application.commands.pipeline import registrar
from estoque.application.commands.saida import _dados, _saldo, _travar_lote
from estoque.application.commands.tipos import Comando, ContextoComando, Efeito
from estoque.application.etag import etag_lote_e_saldo
from estoque.data import modelos as m
from estoque.data.repositorios import RepoLoteSQL
from estoque.domain.erros import ErroDominio, nao_encontrado
from estoque.domain.identidade import PapelId
from estoque.domain.regras.estados import transicao_valida
from estoque.domain.regras.validade import status_efetivo
from estoque.domain.tipos import Lote, StatusLoteEfetivo

# §4.1: "Vencido · Bloqueado -> descarte registrado -> Descartado". Sao os dois
# estados EFETIVOS de origem (ADR-0022), e o unico destino.
DESCARTAVEIS: tuple[StatusLoteEfetivo, ...] = ("vencido", "bloqueado")


def _papel_descarta(papel: PapelId | None) -> bool:
    """§4.1 — Gerente + RT, e o conjunto vem da tabela do dominio.

    A linha da §4.1 cobre DOIS estados de origem, e a tabela de transicoes do
    dominio so' tem um deles: `vencido` e' derivado da data (ADR-0022), nao e'
    `StatusLoteRegistrado`, e portanto nao tem chave na tabela. Perguntar por
    `(bloqueado, descarte)` le' o conjunto de papeis DAQUELA linha — que e' a
    mesma linha. Uma segunda lista de papeis aqui divergiria da primeira no dia
    em que a §4.1 mudar, e ninguem descobriria pelos testes de um lado so'.
    """
    return transicao_valida("bloqueado", "descarte", papel)


async def _lote_ou_falhar(lote_id: str, ctx: ContextoComando) -> Lote:
    lote = await RepoLoteSQL(ctx.conn).por_id(lote_id, _dados(ctx))
    if lote is None:
        # Fora do escopo e inexistente saem pela mesma porta (ADR-0014).
        raise nao_encontrado({"lote_id": lote_id, "ator": ctx.ator.id})
    return lote


def _recusar_se_nao_descartavel(lote: Lote, efetivo: StatusLoteEfetivo, saldo: int) -> None:
    """RN-L06 e §4.1, e o negativo e' o que importa: descarte NAO e' atalho de
    saida. Um lote liberado e valido sai por venda, com nota e cliente — desviar
    a mercadoria para "descarte" seria furto com formulario."""
    if efetivo not in DESCARTAVEIS:
        raise ErroDominio(
            "conflito",
            f"Este lote está {efetivo}: descarte é para lote vencido ou bloqueado (RN-L06).",
            {"lote_id": lote.id, "status_efetivo": efetivo},
        )
    if saldo <= 0:
        # Sem saldo nao ha' movimento a gravar — `quantidade > 0` e' CHECK da
        # migracao 0001 — e um lote sem saldo ja' nao ocupa prateleira.
        raise ErroDominio(
            "conflito",
            "Este lote não tem saldo para descartar.",
            {"lote_id": lote.id, "saldo": saldo},
        )


async def _papel_de(usuario_id: str, ctx: ContextoComando) -> PapelId | None:
    linha = (
        (
            await ctx.conn.execute(
                sa.select(m.usuario.c.papel, m.usuario.c.ativo).where(
                    m.usuario.c.id == usuario_id
                )
            )
        )
        .mappings()
        .first()
    )
    if linha is None or not linha["ativo"]:
        # RN-A06: desativado nao assina. Inexistente e desativado devolvem a
        # mesma coisa — quem preenche o campo nao descobre quem existe.
        return None
    papel: PapelId | None = linha["papel"]
    return papel


async def _recusar_sem_dupla_identificacao(entrada: Any, ctx: ContextoComando) -> PapelId:
    """§4.1: Gerente **e** RT. Duas pessoas, e dois papeis distintos.

    O par negativo esta' na ultima checagem: dois gerentes assinando juntos
    passariam pelas anteriores e transformariam "Gerente + RT" em "duas pessoas
    quaisquer que possam descartar" — o RT existe na linha porque a decisao
    tecnica de destruir medicamento e' dele.
    """
    segundo_id = entrada.segunda_identificacao_id.strip()
    if segundo_id == ctx.ator.id:
        raise ErroDominio(
            "invalido",
            "A dupla identificação exige duas pessoas.",
            {"ator": ctx.ator.id},
        )
    if not _papel_descarta(ctx.ator.papel):
        # O Diretor cai aqui: tem `movimento.descartar` e nao esta' na §4.1.
        raise ErroDominio(
            "nao_autorizado",
            "Sem acesso ao descarte: ele é registrado pelo gerente junto com o "
            "responsável técnico (§4.1).",
            {"ator": ctx.ator.id, "papel": ctx.ator.papel},
        )
    papel_segundo = await _papel_de(segundo_id, ctx)
    if papel_segundo is None or not _papel_descarta(papel_segundo):
        raise ErroDominio(
            "invalido",
            "A segunda identificação não pode assinar um descarte (§4.1).",
            {"segundo": segundo_id},
        )
    if papel_segundo == ctx.ator.papel:
        raise ErroDominio(
            "invalido",
            "O descarte exige gerente e responsável técnico — não duas pessoas "
            "do mesmo papel (§4.1).",
            {"papel": ctx.ator.papel},
        )
    return papel_segundo


async def _etag_do_lote(entrada: Any, ctx: ContextoComando) -> str | None:
    """Etag sobre o estado que a decisao usou: status do lote E saldo.

    Se outra pessoa deu saida ou bloqueou entre a leitura da tela e o envio, o
    descarte que chega descreve um lote que nao existe mais.
    """
    lote = await RepoLoteSQL(ctx.conn).por_id(entrada.lote_id, _dados(ctx))
    if lote is None:
        return None
    return etag_lote_e_saldo(lote, await _saldo(lote.id, ctx))


async def _aplicar(entrada: Any, ctx: ContextoComando) -> Efeito:
    lote = await _lote_ou_falhar(entrada.lote_id, ctx)

    justificativa = entrada.justificativa.strip()
    if len(justificativa) < JUSTIFICATIVA_MINIMA:
        raise ErroDominio(
            "invalido",
            f"O descarte precisa de justificativa de ao menos {JUSTIFICATIVA_MINIMA} "
            "caracteres além do motivo (RN-M05).",
        )

    # A trava vem antes de ler o saldo, como na saida: e' o saldo lido aqui que
    # vira a quantidade descartada.
    await _travar_lote(lote.id, ctx)
    saldo = await _saldo(lote.id, ctx)
    efetivo = status_efetivo(lote, saldo, ctx.agora.date())
    _recusar_se_nao_descartavel(lote, efetivo, saldo)
    papel_segundo = await _recusar_sem_dupla_identificacao(entrada, ctx)

    mid = f"mov-{secrets.token_hex(8)}"
    await ctx.conn.execute(
        sa.insert(m.movimento).values(
            id=mid,
            lote_id=lote.id,
            unidade_id=lote.unidade_id,
            tipo="descarte",
            quantidade=saldo,  # positiva; o sinal vem do tipo
            motivo=entrada.motivo,
            complemento=justificativa,
            autor_id=ctx.ator.id,
            # A segunda identidade do descarte E' a do movimento: as duas pessoas
            # assinam o mesmo ato, no mesmo instante. No recebimento ela vive no
            # RECEBIMENTO (RN-R05), porque la' sao dois atos separados.
            autorizador_id=entrada.segunda_identificacao_id.strip(),
            status="efetivado",
            criado_em=ctx.agora,  # RN-M04 — do servidor, via pipeline
            estorna_movimento_id=None,
            cliente_id=None,
            nota_fiscal=None,
        )
    )
    # §4.1 tem um destino so' para o evento `descarte`, e ele e' terminal:
    # `status_efetivo` faz `descartado` vencer tudo o mais (ADR-0022).
    await ctx.conn.execute(
        sa.update(m.lote).where(m.lote.c.id == lote.id).values(status="descartado")
    )

    return Efeito(
        entidade="lote",
        entidade_id=lote.id,
        valor_anterior={"status": lote.status, "status_efetivo": efetivo, "saldo": saldo},
        valor_novo={
            "status": "descartado",
            "movimento_id": mid,
            "quantidade": saldo,
            "motivo": entrada.motivo,
            "justificativa": justificativa,
            # As DUAS identidades na trilha, com o papel de cada uma: e' o que
            # prova a §4.1 para quem auditar depois (RN-D01).
            "autor_id": ctx.ator.id,
            "autor_papel": ctx.ator.papel,
            "segunda_identificacao_id": entrada.segunda_identificacao_id.strip(),
            "segunda_identificacao_papel": papel_segundo,
            "saldo_apos": 0,
        },
        dados={
            "lote_id": lote.id,
            "movimento_id": mid,
            "status": "descartado",
            "quantidade": saldo,
        },
    )


MOVIMENTO_DESCARTE = registrar(
    Comando(
        nome="movimento_descarte",
        requires=("movimento.descartar",),
        schema=EntradaDescarte,
        aplicar=_aplicar,
        # Repetir NAO e' inofensivo: a segunda chamada encontraria o lote em
        # `descartado`, com saldo zero, e falharia com `conflito` — resposta
        # confusa para o que foi apenas a rede repetindo.
        idempotent=False,
        confirm=True,
        etag_de=_etag_do_lote,
    )
)
