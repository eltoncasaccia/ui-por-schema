"""Cadastro, entrada, saida e identidade. ADR-0019, ADR-0014."""

import secrets
from typing import Any

import sqlalchemy as sa
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Cookie, Request, Response
from pydantic import BaseModel, Field

from estoque.auditoria import registro as aud
from estoque.auth.limite import Limitador
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator
from estoque.server import sessao as ses
from estoque.server.deps import CFG, PH, ator_ou_falhar, motor, ok

rotas = APIRouter()


class Entrada(BaseModel):
    email: str
    senha: str


class Cadastro(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=200)
    senha: str = Field(min_length=10, max_length=200)


@rotas.post("/api/auth/registrar")
async def registrar(corpo: Cadastro) -> dict[str, Any]:
    """Cadastro cria usuario SEM papel e SEM unidade. ADR-0019.

    Zero permissoes: catalogo vazio, nenhum `load` autorizado, nenhuma tela.
    Papel e unidades sao atribuidos por quem tem `usuario.gerenciar`, com
    auditoria.

    Este e' um distribuidor farmaceutico com papeis regulados. Se o cadastro
    deixasse a pessoa ESCOLHER o proprio papel, `RN-R02` (liberacao privativa
    do RT) e `CA-04` (dupla identificacao) virariam enfeite — seria escalacao
    de privilegio por formulario.

    A resposta e' a MESMA para e-mail novo e e-mail ja' cadastrado. Distinguir
    os dois transforma o cadastro num verificador de contas (ADR-0014).
    """
    email = corpo.email.strip().lower()
    async with motor.begin() as c:
        ja = (
            await c.execute(sa.select(m.usuario.c.id).where(m.usuario.c.email == email))
        ).first()
        if ja is None:
            uid = f"u-{secrets.token_hex(8)}"
            await c.execute(
                sa.insert(m.usuario).values(
                    id=uid,
                    nome=corpo.nome.strip(),
                    email=email,
                    senha_hash=PH.hash(corpo.senha),
                    papel=None,  # ← o ponto inteiro deste endpoint
                    ativo=True,
                )
            )
            await aud.registrar(
                c,
                ator_id=uid,
                acao="registrar",
                origem="tela",
                entidade="usuario",
                entidade_id=uid,
            )
        else:
            # Gasta o mesmo tempo de hash, para nao vazar por temporizacao.
            PH.hash(corpo.senha)
    return ok(
        {
            "criado": True,
            "aviso": "Seu acesso precisa ser liberado por um administrador.",
        }
    )


LIMITE = Limitador()


@rotas.post("/api/auth/entrar")
async def entrar(corpo: Entrada, req: Request, resposta: Response) -> dict[str, Any]:
    """Resposta e tempo UNIFORMES para usuario inexistente e senha errada.

    E' o ADR-0014 aplicado ao login: distinguir os dois casos enumera contas.
    Por isso o hash e' verificado mesmo quando o usuario nao existe — senao a
    diferenca de tempo faria o mesmo vazamento.
    """
    ip = req.client.host if req.client else "desconhecido"
    conta = corpo.email.strip().lower()

    # Consulta ANTES de tocar no banco: bloqueado nao gasta consulta nem hash.
    if LIMITE.bloqueado(conta=conta, ip=ip):
        async with motor.begin() as c:
            await aud.registrar(
                c,
                ator_id=None,
                acao="login_bloqueado",
                origem="tela",
                entidade="usuario",
                valor_novo={"conta": conta, "ip": ip},
            )
        raise ErroDominio("limite", "Muitas tentativas. Tente de novo em alguns minutos.")

    async with motor.begin() as c:
        r = (
            (await c.execute(sa.select(m.usuario).where(m.usuario.c.email == conta)))
            .mappings()
            .first()
        )
        hash_alvo = r["senha_hash"] if r else PH.hash("inexistente")
        try:
            PH.verify(hash_alvo, corpo.senha)
            valido = r is not None and bool(r["ativo"])
        except VerifyMismatchError:
            valido = False
        if not valido or r is None:
            LIMITE.registrar_falha(conta=conta, ip=ip)
            raise ErroDominio("nao_autenticado", "E-mail ou senha invalidos.")

        # Provou a identidade: nao carrega as tentativas erradas de antes.
        LIMITE.limpar_conta(conta)
        sid = await ses.criar(c, str(r["id"]))
        await aud.registrar(c, ator_id=str(r["id"]), acao="entrar", origem="tela")
        # BUG achado em uso: esta resposta devolvia apenas {id, nome, papel}, e o
        # cliente a usava como o ator completo. `unidades` chegava `undefined` e
        # a tela quebrava em branco ate' o refresh, quando `/auth/eu` devolvia o
        # objeto inteiro. Duas formas do mesmo conceito e' um bug esperando.
        ator = await ses.ator_da_sessao(c, sid)

    csrf = ses.novo_token_csrf()
    resposta.set_cookie(ses.COOKIE, sid, httponly=True, samesite="lax", path="/")
    # Dupla submissao: este cookie e' legivel pelo JS de proposito, e precisa
    # voltar como header. Um site de terceiro consegue disparar a requisicao,
    # mas nao consegue LER o cookie para montar o header.
    resposta.set_cookie(ses.COOKIE_CSRF, csrf, httponly=False, samesite="lax", path="/")
    if ator is None:  # pragma: no cover — sessao recem-criada
        raise ErroDominio("nao_autenticado", "Falha ao abrir sessao.")
    return ok(_eu(ator))


@rotas.post("/api/auth/sair")
async def sair(resposta: Response, sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    if sessao:
        async with motor.begin() as c:
            await ses.encerrar(c, sessao)
    resposta.delete_cookie(ses.COOKIE, path="/")
    resposta.delete_cookie(ses.COOKIE_CSRF, path="/")
    return ok({"encerrada": True})


def _eu(ator: Ator) -> dict[str, Any]:
    """Forma UNICA do ator para o cliente. Login e /auth/eu devolvem isto, os dois.

    Regressao do bug da tela branca: havia duas formas do mesmo conceito, e o
    cliente tratava as duas como iguais.
    """
    return {
        "id": ator.id,
        "nome": ator.nome,
        "papel": ator.papel,
        "unidades": sorted(ator.unidades),
        "permissoes": sorted(ator.permissoes),
    }


@rotas.get("/api/auth/eu")
async def eu(sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    async with motor.connect() as c:
        ator = await ator_ou_falhar(c, sessao)
    return ok(_eu(ator))


@rotas.get("/api/auth/demo")
async def personas_demo() -> dict[str, Any]:
    """Atalho de demonstracao. So' existe com MODO_DEMO=true.

    Fora do modo demo a rota devolve 404 — nao 403, nao escondida na interface:
    a informacao de que ela existe tambem nao vaza.
    """
    if not CFG.modo_demo:
        raise ErroDominio("nao_encontrado", "Registro nao encontrado.")
    async with motor.connect() as c:
        rs = (
            (
                await c.execute(
                    sa.select(m.usuario.c.email, m.usuario.c.nome, m.usuario.c.papel)
                    .where(m.usuario.c.papel.is_not(None))
                    .order_by(m.usuario.c.nome)
                )
            )
            .mappings()
            .all()
        )
    return ok([dict(r) for r in rs], senha="demo")
