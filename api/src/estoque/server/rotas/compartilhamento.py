"""Destinatarios e entrega. Compartilhar aponta para uma view e NAO concede
acesso: quem abre carrega sob a propria permissao (documento 03 §8).
"""

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Cookie
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncConnection

from estoque.application.schema.validar import revalidar_ou_falhar, validar_schema
from estoque.auditoria import registro as aud
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import PERMISSOES_POR_PAPEL, Ator
from estoque.server.deps import ator_ou_falhar, motor, ok

rotas = APIRouter()


class PedidoDestinatarios(BaseModel):
    """O schema que se pretende compartilhar. Sem ele nao da' para dizer QUEM
    consegue abrir — e listar quem nao consegue e' oferecer uma entrega que vai
    chegar vazia."""

    model_config = ConfigDict(populate_by_name=True)
    esquema: dict[str, Any] = Field(alias="schema")


async def _ator_de(conn: AsyncConnection, usuario_id: str) -> Ator | None:
    """Monta o Ator de outra pessoa, para saber o que o catalogo DELA contem."""
    r = (
        (await conn.execute(sa.select(m.usuario).where(m.usuario.c.id == usuario_id)))
        .mappings()
        .first()
    )
    if r is None or not r["ativo"] or r["papel"] is None:
        return None
    unis = [
        row.unidade_id
        for row in await conn.execute(
            sa.select(m.usuario_unidade.c.unidade_id).where(
                m.usuario_unidade.c.usuario_id == usuario_id
            )
        )
    ]
    return Ator(
        id=str(r["id"]),
        nome=str(r["nome"]),
        papel=r["papel"],
        unidades=frozenset(unis),
        permissoes=PERMISSOES_POR_PAPEL[r["papel"]],
        ativo=True,
    )


@rotas.post("/api/destinatarios")
async def destinatarios(
    corpo: PedidoDestinatarios, sessao: str | None = Cookie(default=None)
) -> dict[str, Any]:
    """Quem pode receber ESTE schema.

    Compartilhar aponta para uma view e nao concede acesso (documento 03 §8):
    quem abre carrega sob a propria permissao. A consequencia e' que mandar para
    quem nao pode ver entrega uma tela vazia — ruido para os dois lados.

    Entao a lista e' filtrada pelo que o catalogo DE CADA CANDIDATO aceita, com
    a MESMA funcao de validacao que roda na abertura. Duas checagens diferentes
    divergiriam, e a lista prometeria o que a abertura nega.

    Contrapartida aceita: A descobre que B nao ve certo tipo de dado. Dentro da
    empresa isso ja' e' publico — a matriz de permissoes por papel e' politica
    da casa, nao segredo. O que continua protegido e' o DADO, nunca revelado.
    """
    async with motor.connect() as c:
        ator = await ator_ou_falhar(c, sessao)
        # O schema precisa ser valido para QUEM COMPARTILHA, antes de tudo.
        revalidar_ou_falhar(corpo.esquema, ator)

        candidatos = (
            (
                await c.execute(
                    sa.select(m.usuario.c.id, m.usuario.c.nome, m.usuario.c.papel)
                    .where(
                        m.usuario.c.id != ator.id,
                        m.usuario.c.ativo.is_(True),
                        m.usuario.c.papel.is_not(None),
                    )
                    .order_by(m.usuario.c.nome)
                )
            )
            .mappings()
            .all()
        )

        saida: list[dict[str, Any]] = []
        for cand in candidatos:
            outro = await _ator_de(c, str(cand["id"]))
            if outro is None:
                continue
            r = validar_schema(corpo.esquema, outro)
            # So' entra quem abre a composicao INTEIRA. Meia tela compartilhada
            # e' pior que nenhuma: a pessoa nao sabe o que faltou.
            if r.schema is not None and not r.rejeitados:
                saida.append({"id": cand["id"], "nome": cand["nome"], "papel": cand["papel"]})
    return ok(saida)


class Compartilhar(BaseModel):
    view_id: str
    para: str
    mensagem: str | None = None


@rotas.post("/api/compartilhamentos")
async def compartilhar(
    corpo: Compartilhar, sessao: str | None = Cookie(default=None)
) -> dict[str, Any]:
    """Entrega pelo SISTEMA, nao por link.

    Ganhos sobre link solto: auditoria de quem compartilhou o que, revogacao, e
    nenhum segredo em transito — link e' encaminhado, colado em grupo, fica em
    historico.
    """
    async with motor.begin() as c:
        ator = await ator_ou_falhar(c, sessao)
        if corpo.para == ator.id:
            raise ErroDominio("invalido", "Escolha outra pessoa.")
        existe = (
            await c.execute(
                sa.select(m.view_registro.c.view_id).where(
                    m.view_registro.c.view_id == corpo.view_id,
                    m.view_registro.c.revogado_em.is_(None),
                )
            )
        ).first()
        if existe is None:
            raise ErroDominio("nao_encontrado", "Registro nao encontrado.")
        await c.execute(
            sa.insert(m.view_compartilhamento).values(
                view_id=corpo.view_id,
                de_usuario_id=ator.id,
                para_usuario_id=corpo.para,
                mensagem=corpo.mensagem,
                criado_em=datetime.now(UTC),
            )
        )
        await aud.registrar(
            c,
            ator_id=ator.id,
            acao="compartilhar",
            origem="tela",
            entidade="view",
            entidade_id=corpo.view_id,
            valor_novo={"para": corpo.para},
        )
    return ok({"enviado": True})


@rotas.get("/api/compartilhamentos")
async def caixa(sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    async with motor.connect() as c:
        ator = await ator_ou_falhar(c, sessao)
        rs = (
            (
                await c.execute(
                    sa.select(
                        m.view_compartilhamento.c.id,
                        m.view_compartilhamento.c.view_id,
                        m.view_compartilhamento.c.mensagem,
                        m.view_compartilhamento.c.criado_em,
                        m.usuario.c.nome.label("de_nome"),
                    )
                    .join(m.usuario, m.usuario.c.id == m.view_compartilhamento.c.de_usuario_id)
                    .where(m.view_compartilhamento.c.para_usuario_id == ator.id)
                    .order_by(m.view_compartilhamento.c.criado_em.desc())
                    .limit(50)
                )
            )
            .mappings()
            .all()
        )
    return ok(
        [
            {
                "id": r["id"],
                "view_id": r["view_id"],
                "mensagem": r["mensagem"],
                "de": r["de_nome"],
                "criado_em": r["criado_em"].isoformat(),
            }
            for r in rs
        ]
    )
