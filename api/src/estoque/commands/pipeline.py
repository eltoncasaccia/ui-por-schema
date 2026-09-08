"""O caminho unico de escrita. ADR-0002, ADR-0004, RN-D01, RN-M04, RN-A03.

Tudo que grava neste sistema passa por aqui, venha da tela tradicional ou do
formulario que o assistente fez aparecer. Um segundo caminho de escrita seria um
segundo lugar onde lembrar de autorizar, de auditar e de nao duplicar — e o
segundo lugar e' sempre o que esquece.

A ordem dos passos nao e' arbitraria:

    buscar -> AUTORIZAR -> exigir chave -> validar -> replay
           -> [ transacao:  If-Match -> aplicar -> auditar -> gravar chave ]
           -> commit

`AUTORIZAR` vem antes de validar de proposito. Se a validacao viesse primeiro,
a mensagem de erro de schema informaria a quem nao pode executar o comando qual
e' o formato esperado dele — um oraculo de forma, de graca, para quem nao devia
nem saber que o comando existe.

O `replay` vem antes da transacao porque repetir uma chave nao e' escrever: e'
devolver o que ja' foi escrito. Abrir transacao para isso so' criaria contencao.

O que este modulo NAO faz: comandos concretos. Eles se registram aqui (T-026 a
T-030). O pipeline nao conhece nenhum pelo nome.
"""

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from estoque.auditoria import registro as aud
from estoque.auditoria.registro import Origem
from estoque.autorizacao.motor import autorizar_ou_falhar
from estoque.commands.tipos import (
    Comando,
    ContextoComando,
    Efeito,
    Resultado,
    sem_segredo,
)
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio, nao_encontrado
from estoque.domain.identidade import Ator

# Campos de relogio que um cliente pode mandar e que o servidor SEMPRE ignora.
# RN-M04: a hora e' do servidor. Nao basta "o comando nao usa" — basta um
# comando futuro aceitar um `criado_em` no schema para a regra virar opcional.
RELOGIO_DO_CLIENTE = frozenset(
    {"criado_em", "criadoem", "agora", "timestamp", "data_hora", "datahora", "quando"}
)

_REGISTRO: dict[str, Comando] = {}


# ------------------------------------------------------------------ registro
def registrar(cmd: Comando) -> Comando:
    """Registra um comando executavel. Chamado por T-026 a T-030, nunca pelo modelo."""
    if cmd.nome in _REGISTRO:
        msg = f"comando duplicado: {cmd.nome}"
        raise ValueError(msg)
    if not cmd.requires:
        # ADR-0004: comando sem `requires` e' brecha silenciosa. O tipo permite a
        # tupla vazia; esta linha e' o que a recusa.
        msg = f"{cmd.nome}: requires vazio — ADR-0004"
        raise ValueError(msg)
    _REGISTRO[cmd.nome] = cmd
    return cmd


def buscar(nome: str) -> Comando | None:
    return _REGISTRO.get(nome)


def registrados() -> Mapping[str, Comando]:
    return dict(_REGISTRO)


# -------------------------------------------------------------------- etags
def etag_de_valores(valores: Mapping[str, Any]) -> str:
    """Etag do estado atual de uma entidade.

    Derivado do conteudo, e nao de um contador: um contador exigiria coluna nova
    em toda tabela e um lugar a mais para esquecer de incrementar. Derivado do
    conteudo, o etag esta certo por construcao.
    """
    bruto = json.dumps(dict(sorted(valores.items())), separators=(",", ":"), default=str)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:32]


def _impressao(corpo: Mapping[str, Any]) -> str:
    return etag_de_valores(corpo)


def _sem_relogio_do_cliente(corpo: Mapping[str, Any]) -> dict[str, Any]:
    return {
        k: v for k, v in corpo.items() if k.lower().replace("-", "_") not in RELOGIO_DO_CLIENTE
    }


# ---------------------------------------------------------------- pipeline
async def executar(
    nome: str,
    corpo: Mapping[str, Any],
    *,
    ator: Ator,
    motor: AsyncEngine,
    origem: Origem,
    idempotency_key: str | None = None,
    if_match: str | None = None,
) -> Resultado:
    """Executa um comando. E' o unico ponto de entrada de escrita do sistema."""
    cmd = buscar(nome)
    if cmd is None:
        # Indistinguivel de comando existente fora do alcance do ator (ADR-0014).
        raise nao_encontrado(f"comando {nome!r} nao registrado")

    limpo = _sem_relogio_do_cliente(corpo)
    try:
        # A partir daqui TODA recusa vira trilha. A autorizacao esta dentro do
        # `try` de proposito: a tentativa que mais interessa a quem investiga e'
        # justamente a de quem nao podia — e ela e' a que falha mais cedo.
        return await _executar_autorizado(
            cmd,
            limpo,
            motor=motor,
            ator=ator,
            origem=origem,
            idempotency_key=idempotency_key,
            if_match=if_match,
        )
    except ErroDominio as e:
        # AC-7: registrada em conexao NOVA, porque o rollback que acabou de
        # acontecer apagaria o registro junto com o efeito que ele desfez.
        await _auditar_recusa(motor, ator=ator, nome=nome, origem=origem, corpo=limpo, erro=e)
        raise


async def _executar_autorizado(
    cmd: Comando,
    corpo: Mapping[str, Any],
    *,
    motor: AsyncEngine,
    ator: Ator,
    origem: Origem,
    idempotency_key: str | None,
    if_match: str | None,
) -> Resultado:
    # TERCEIRO momento do ADR-0004 — o unico que garante. A interface ja' pode
    # ter escondido o botao; esconder nao e' controlar (RN-A03).
    #
    # Vem ANTES de validar o corpo: erro de schema devolvido a quem nao pode
    # executar o comando descreveria o formato dele de graca.
    autorizar_ou_falhar(ator, cmd.requires, f"o comando {cmd.nome}")

    if not cmd.idempotent and not idempotency_key:
        raise ErroDominio("invalido", "Idempotency-Key obrigatorio nesta operacao.")

    try:
        entrada = cmd.schema.model_validate(corpo)
    except ValidationError as e:
        # A mensagem nao ecoa o recebido: eco devolve conteudo hostil para dentro
        # do log e confirma ao atacante o que ele mandou.
        raise ErroDominio("invalido", "Entrada invalida.", detalhe_interno=e) from e

    impressao = _impressao(corpo)

    if idempotency_key:
        anterior = await _replay(motor, idempotency_key, ator.id, cmd.nome, impressao)
        if anterior is not None:
            return anterior

    return await _aplicar_em_transacao(
        cmd,
        entrada,
        motor=motor,
        ator=ator,
        origem=origem,
        agora=datetime.now(UTC),  # RN-M04 — do servidor, uma vez, para o comando inteiro
        if_match=if_match,
        idempotency_key=idempotency_key,
        impressao=impressao,
    )


async def _aplicar_em_transacao(
    cmd: Comando,
    entrada: Any,
    *,
    motor: AsyncEngine,
    ator: Ator,
    origem: Origem,
    agora: datetime,
    if_match: str | None,
    idempotency_key: str | None,
    impressao: str,
) -> Resultado:
    """Efeito, auditoria e registro de chave numa transacao so'.

    Os tres juntos ou nenhum. Auditoria fora da transacao registraria escrita que
    o rollback desfez; chave fora dela permitiria o efeito acontecer duas vezes
    na janela entre um commit e o outro.
    """
    async with motor.connect() as conn:
        ctx = ContextoComando(ator=ator, conn=conn, agora=agora, origem=origem)
        try:
            await _conferir_if_match(cmd, entrada, ctx, if_match)
            efeito = await cmd.aplicar(entrada, ctx)
            # Etag lido DEPOIS de aplicar: e' o estado que o cliente passa a ter
            # em maos, e o que ele devolvera no proximo `If-Match`.
            etag_novo = await cmd.etag_de(entrada, ctx) if cmd.etag_de else None

            # RN-D01: quem, o que, quando, valor anterior, valor novo, origem.
            await aud.registrar(
                conn,
                ator_id=ator.id,
                acao=cmd.nome,
                origem=origem,
                entidade=efeito.entidade,
                entidade_id=efeito.entidade_id,
                valor_anterior=efeito.valor_anterior,
                valor_novo=efeito.valor_novo,
            )

            if idempotency_key:
                await _gravar_chave(
                    conn,
                    chave=idempotency_key,
                    ator_id=ator.id,
                    comando=cmd.nome,
                    impressao=impressao,
                    resposta=efeito.dados,
                    etag=etag_novo,
                    agora=agora,
                )
            await conn.commit()
            return Resultado(dados=efeito.dados, etag=etag_novo, repetido=False)
        except IntegrityError:
            # Corrida: outra requisicao com a MESMA chave commitou primeiro. O
            # efeito desta e' desfeito e a resposta vencedora e' devolvida — um
            # efeito, uma resposta, que e' exatamente a promessa do AC-3.
            await conn.rollback()
            vencedor = await _replay(motor, idempotency_key or "", ator.id, cmd.nome, impressao)
            if vencedor is not None:
                return vencedor
            raise
        except BaseException:
            await conn.rollback()
            raise


async def _conferir_if_match(
    cmd: Comando, entrada: Any, ctx: ContextoComando, if_match: str | None
) -> None:
    """Concorrencia otimista. Comando com `etag_de` e' atualizacao, e exige `If-Match`.

    Exigir, e nao apenas conferir quando presente: `If-Match` opcional e' o mesmo
    que ausente, porque o cliente que sobrescreve sem ler e' justamente o que
    omite o cabecalho.
    """
    if cmd.etag_de is None:
        return
    if if_match is None:
        raise ErroDominio("invalido", "If-Match obrigatorio nesta operacao.")
    atual = await cmd.etag_de(entrada, ctx)
    if atual is None:
        raise nao_encontrado("alvo do comando inexistente ou fora de escopo")
    if atual != if_match:
        # Sem aplicar nada: a comparacao acontece ANTES do `aplicar`.
        raise ErroDominio("conflito", "O registro mudou desde a leitura. Recarregue e refaca.")


# ------------------------------------------------------------- idempotencia
async def _replay(
    motor: AsyncEngine, chave: str, ator_id: str, comando: str, impressao: str
) -> Resultado | None:
    if not chave:
        return None
    async with motor.connect() as conn:
        linha = (
            (
                await conn.execute(
                    sa.select(m.idempotencia).where(
                        m.idempotencia.c.chave == chave,
                        m.idempotencia.c.ator_id == ator_id,
                    )
                )
            )
            .mappings()
            .first()
        )

    if linha is None:
        return None
    if linha["comando"] != comando or linha["impressao"] != impressao:
        # Mesma chave, corpo outro. Devolver a resposta antiga faria o cliente
        # crer que a segunda operacao aconteceu. E' erro dele, e precisa doer.
        raise ErroDominio("conflito", "Idempotency-Key ja' usada com outro conteudo.")
    resposta: dict[str, Any] = dict(linha["resposta"])
    return Resultado(dados=resposta, etag=linha["etag"], repetido=True)


async def _gravar_chave(
    conn: AsyncConnection,
    *,
    chave: str,
    ator_id: str,
    comando: str,
    impressao: str,
    resposta: dict[str, Any],
    etag: str | None,
    agora: datetime,
) -> None:
    await conn.execute(
        sa.insert(m.idempotencia).values(
            chave=chave,
            ator_id=ator_id,
            comando=comando,
            impressao=impressao,
            resposta=resposta,
            etag=etag,
            criado_em=agora,
        )
    )


# ------------------------------------------------------------------ recusa
async def _auditar_recusa(
    motor: AsyncEngine,
    *,
    ator: Ator,
    nome: str,
    origem: Origem,
    corpo: Mapping[str, Any],
    erro: ErroDominio,
) -> None:
    """RN-D01 vale para a tentativa recusada tambem.

    Auditoria que so' registra sucesso descreve um sistema onde ninguem nunca
    tentou o que nao podia — que e' precisamente o que se quer investigar.
    """
    async with motor.begin() as conn:
        await aud.registrar(
            conn,
            ator_id=ator.id,
            acao=f"{nome}.recusado",
            origem=origem,
            entidade="comando",
            entidade_id=nome,
            valor_novo={"codigo": erro.codigo, "entrada": sem_segredo(corpo)},
        )


__all__ = [
    "Comando",
    "ContextoComando",
    "Efeito",
    "Resultado",
    "buscar",
    "etag_de_valores",
    "executar",
    "registrados",
    "registrar",
]
