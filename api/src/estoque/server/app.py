"""A borda HTTP. ADR-0004, ADR-0014, ADR-0019, ADR-0020.

O que este modulo faz que e' o ponto do projeto:

  /api/assistente/compor   modelo -> schema -> VALIDA contra o catalogo do ator
  /api/componentes/{id}/dados  load autorizado -> select NO SERVIDOR -> viewmodel

O schema recebido e' PAYLOAD NAO-CONFIAVEL, venha do modelo ou do cliente. E'
por isso que a validacao roda de novo aqui, e por isso `/componentes/{id}/dados`
reautoriza por registro mesmo que a composicao ja' tenha sido validada.
"""

import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Cookie, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

import estoque.commands.indice  # registra os comandos de escrita
import estoque.registry.indice  # noqa: F401  — registra os componentes
from estoque.assistant.adapter import AdaptadorModelo, ErroDeModelo, extrair_json
from estoque.assistant.fabrica import criar_adaptador
from estoque.assistant.langfuse_obs import criar as criar_observador
from estoque.assistant.observador import Observador, ObservadorNulo
from estoque.auditoria import registro as aud
from estoque.auth import csrf
from estoque.auth.limite import Limitador
from estoque.autorizacao.motor import (
    autorizar_ou_falhar,
    autorizar_params_ou_falhar,
    autorizar_unidade_do_param,
)
from estoque.commands import pipeline
from estoque.data import modelos as m
from estoque.data.porta import ContextoDados, Repositorios
from estoque.data.repositorios import RepoLoteSQL, RepoMovimentoSQL, RepoProdutoSQL
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import PERMISSOES_POR_PAPEL, Ator
from estoque.registry.definir import LoadContext, Pagina, permissoes_base
from estoque.registry.registry import buscar, catalogo_de, valores_proibidos
from estoque.schema.validar import revalidar_ou_falhar, validar_schema
from estoque.schema.viewkey import novo_view_id, view_key
from estoque.server import sessao as ses
from estoque.server.config import Config

CFG = Config.do_ambiente()
# Nulo quando nao ha chave do LangFuse: telemetria e' opcional por construcao.
OBS: Observador = criar_observador() or ObservadorNulo()
PH = PasswordHasher()
_engine = create_async_engine(CFG.database_url, future=True, pool_pre_ping=True)


@asynccontextmanager
async def _ciclo(_: FastAPI) -> AsyncIterator[None]:
    yield
    await _engine.dispose()


app = FastAPI(title="Estoque Bertoni", lifespan=_ciclo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CFG.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _csrf(req: Request, seguir: Any) -> Any:
    """Confere origem em TODA escrita, antes de chegar na rota.

    Middleware e nao dependencia por rota: dependencia esquecida numa rota nova
    e' um buraco silencioso — e rota nova e' exatamente o que se acrescenta com
    pressa.
    """
    try:
        csrf.conferir(req, CFG.cors_origin)
    except ErroDominio as e:
        return await _erro(req, e)
    return await seguir(req)


@app.exception_handler(ValidationError)
async def _invalido(_: Request, e: ValidationError) -> JSONResponse:
    """Entrada que nao casa com o modelo e' `invalido`, nao erro do servidor.

    ACHADO ao escrever os cenarios de teste: uma metrica fora do enum levantava
    `ValidationError`, que nao e' `ErroDominio` — escapava do handler e virava
    500. Status errado, e um 500 num caminho que o usuario alcanca digitando.

    A mensagem NAO ecoa o valor recebido: eco devolveria conteudo hostil para
    dentro do log, e confirmaria ao atacante o que ele mandou.
    """
    return JSONResponse(
        status_code=422,
        content={"ok": False, "erro": {"codigo": "invalido", "mensagem": "Entrada invalida."}},
    )


@app.exception_handler(Exception)
async def _inesperado(_: Request, e: Exception) -> JSONResponse:
    """T-011 AC-5: erro inesperado devolve envelope generico, sem stack.

    Estava no criterio de aceite e nao existia. O traceback vai para o log do
    servidor; a resposta nao carrega nada alem do codigo.
    """
    logging.getLogger("estoque").exception("erro nao tratado")
    return JSONResponse(
        status_code=500,
        content={"ok": False, "erro": {"codigo": "invalido", "mensagem": "Erro interno."}},
    )


@app.exception_handler(ErroDominio)
async def _erro(_: Request, e: ErroDominio) -> JSONResponse:
    """Serializador unico. DESCARTA `detalhe_interno`, sempre.

    E' o unico ponto por onde erro de dominio sai — e por isso o unico lugar
    onde o vazamento poderia acontecer.
    """
    codigos = {
        "nao_autenticado": 401,
        "nao_autorizado": 403,
        "nao_encontrado": 404,
        "invalido": 422,
        "conflito": 409,
        "limite": 429,
    }
    return JSONResponse(
        status_code=codigos.get(e.codigo, 400),
        content={"ok": False, "erro": {"codigo": e.codigo, "mensagem": e.mensagem_publica}},
    )


def _ok(dados: Any, **meta: Any) -> dict[str, Any]:
    return {"ok": True, "dados": dados, "meta": meta}


async def _ator(conn: AsyncConnection, sid: str | None) -> Ator:
    if not sid:
        raise ErroDominio("nao_autenticado", "Sessao ausente.")
    ator = await ses.ator_da_sessao(conn, sid)
    if ator is None:
        raise ErroDominio("nao_autenticado", "Sessao invalida ou expirada.")
    return ator


def _repos(conn: AsyncConnection) -> Repositorios:
    return Repositorios(
        lote=RepoLoteSQL(conn),
        produto=RepoProdutoSQL(conn),
        movimento=RepoMovimentoSQL(conn),
        recebimento=None,  # type: ignore[arg-type]  # ciclo 1: T-022
        temperatura=None,  # type: ignore[arg-type]  # ciclo 1: T-023
    )


class _Tx:
    def __init__(self, c: AsyncConnection) -> None:
        self._c = c

    async def commit(self) -> None:
        await self._c.commit()

    async def rollback(self) -> None:
        await self._c.rollback()


# ---------------------------------------------------------------- saude
@app.get("/api/saude")
async def saude() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------- auth
class Entrada(BaseModel):
    email: str
    senha: str


class Cadastro(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=200)
    senha: str = Field(min_length=10, max_length=200)


@app.post("/api/auth/registrar")
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
    async with _engine.begin() as c:
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
    return _ok(
        {
            "criado": True,
            "aviso": "Seu acesso precisa ser liberado por um administrador.",
        }
    )


LIMITE = Limitador()


@app.post("/api/auth/entrar")
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
        async with _engine.begin() as c:
            await aud.registrar(
                c,
                ator_id=None,
                acao="login_bloqueado",
                origem="tela",
                entidade="usuario",
                valor_novo={"conta": conta, "ip": ip},
            )
        raise ErroDominio("limite", "Muitas tentativas. Tente de novo em alguns minutos.")

    async with _engine.begin() as c:
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
    return _ok(_eu(ator))


@app.post("/api/auth/sair")
async def sair(resposta: Response, sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    if sessao:
        async with _engine.begin() as c:
            await ses.encerrar(c, sessao)
    resposta.delete_cookie(ses.COOKIE, path="/")
    resposta.delete_cookie(ses.COOKIE_CSRF, path="/")
    return _ok({"encerrada": True})


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


@app.get("/api/auth/eu")
async def eu(sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    async with _engine.connect() as c:
        ator = await _ator(c, sessao)
    return _ok(_eu(ator))


@app.get("/api/auth/demo")
async def personas_demo() -> dict[str, Any]:
    """Atalho de demonstracao. So' existe com MODO_DEMO=true.

    Fora do modo demo a rota devolve 404 — nao 403, nao escondida na interface:
    a informacao de que ela existe tambem nao vaza.
    """
    if not CFG.modo_demo:
        raise ErroDominio("nao_encontrado", "Registro nao encontrado.")
    async with _engine.connect() as c:
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
    return _ok([dict(r) for r in rs], senha="demo")


# ---------------------------------------------------------------- catálogo
@app.get("/api/catalogo")
async def catalogo(sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    """O vocabulario DESTE ator (ADR-0003). Exposto para a interface poder
    mostrar o que o assistente e' capaz de fazer para quem esta logado."""
    async with _engine.connect() as c:
        ator = await _ator(c, sessao)
    return _ok(catalogo_de(ator))


# ---------------------------------------------------------------- assistente
class Pergunta(BaseModel):
    pergunta: str
    modo: str = CFG.modo_decodificacao


def _adaptador() -> AdaptadorModelo:
    """Escolhido por configuracao (PROVEDOR), nao por codigo."""
    return criar_adaptador(modelo=CFG.modelo)


@app.post("/api/assistente/compor")
async def compor(corpo: Pergunta, sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    async with _engine.begin() as c:
        ator = await _ator(c, sessao)
        cat = catalogo_de(ator)
        if not cat:
            # ADR-0019: recem-cadastrado sem papel nao tem vocabulario.
            raise ErroDominio("nao_autorizado", "Seu usuario ainda nao tem papel atribuido.")

        try:
            adaptador = _adaptador()
        except ErroDeModelo as e:
            raise ErroDominio("invalido", str(e)) from e

        modo = "restrito" if corpo.modo == "restrito" else "livre"
        r = await adaptador.compor(corpo.pergunta, cat, modo=modo)  # type: ignore[arg-type]
        if r.trace.erro:
            raise ErroDominio("invalido", "O assistente nao respondeu. Tente de novo.")

        try:
            bruto = extrair_json(r.bruto)
        except ValueError:
            r.trace.erro = "resposta sem JSON"
            bruto = None

        resultado = validar_schema(bruto, ator) if bruto is not None else None
        r.trace.aceitos = resultado.aceitos if resultado else []
        r.trace.rejeitados = (
            [(x.tipo, x.motivo) for x in resultado.rejeitados] if resultado else []
        )

        # Telemetria externa. Nunca levanta — e a auditoria abaixo, que e'
        # requisito regulatorio, nao depende dela.
        OBS.composicao(trace=r.trace, ator_id=ator.id, papel=ator.papel, catalogo=len(cat))

        # RN-D05 / CS-05: a resposta do assistente e' auditada, com o que foi
        # aceito E o que foi rejeitado.
        await aud.registrar(
            c,
            ator_id=ator.id,
            acao="compor",
            origem="assistente",
            valor_novo={"pergunta": corpo.pergunta, **r.trace.resumo()},
        )

    schema = resultado.schema if resultado else None
    return _ok(
        {
            "schema": schema.model_dump() if schema else None,
            "blocos": [
                {"tipo": b.tipo, "params": b.params, "tamanho": _tamanho(b.tipo)}
                for b in (schema.blocos if schema else ())
            ],
        },
        trace=r.trace.resumo(),
    )


def _tamanho(tipo: str) -> str:
    c = buscar(tipo)
    return c.tamanho if c else "inteira"


# ---------------------------------------------------------------- views
class NovaView(BaseModel):
    # `schema` colide com um metodo do BaseModel; o nome no JSON continua sendo
    # `schema`, que e' o que o contrato publico diz.
    model_config = ConfigDict(populate_by_name=True)

    titulo: str
    esquema: dict[str, Any] = Field(alias="schema")


@app.post("/api/views")
async def criar_view(
    corpo: NovaView, sessao: str | None = Cookie(default=None)
) -> dict[str, Any]:
    """Persiste um schema e devolve seu endereco publico.

    Dois identificadores, com papeis distintos (ADR-0021):
      view_key  hash do schema, INTERNO — "esta tela e' a mesma de antes?"
      view_id   opaco, PUBLICO, revogavel — o endereco em /v/:viewId
    """
    async with _engine.begin() as c:
        ator = await _ator(c, sessao)
        schema = revalidar_ou_falhar(corpo.esquema, ator)
        vid, vkey = novo_view_id(), view_key(schema)
        await c.execute(
            sa.insert(m.view_registro).values(
                view_id=vid,
                view_key=vkey,
                schema=schema.model_dump(),
                criado_por=ator.id,
                criado_em=datetime.now(UTC),
            )
        )
        await aud.registrar(
            c,
            ator_id=ator.id,
            acao="criar_view",
            origem="tela",
            entidade="view",
            entidade_id=vid,
            valor_novo={"view_key": vkey},
        )
    return _ok({"view_id": vid, "view_key": vkey})


@app.get("/api/views/{view_id}")
async def abrir_view(view_id: str, sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    """A regra que nao pode quebrar: o schema e' revalidado contra o catalogo
    DO REQUISITANTE, e os dados carregam sob a autenticacao DELE.

    Quem abre uma view compartilhada e nao pode ver o lote ve "sem acesso" — nao
    os dados de quem compartilhou.
    """
    async with _engine.begin() as c:
        ator = await _ator(c, sessao)
        r = (
            (
                await c.execute(
                    sa.select(m.view_registro).where(m.view_registro.c.view_id == view_id)
                )
            )
            .mappings()
            .first()
        )
        # Revogado responde como inexistente — ADR-0014.
        if r is None or r["revogado_em"] is not None:
            raise ErroDominio("nao_encontrado", "Registro nao encontrado.")
        schema = revalidar_ou_falhar(r["schema"], ator)
        await aud.registrar(
            c,
            ator_id=ator.id,
            acao="abrir_view",
            origem="tela",
            entidade="view",
            entidade_id=view_id,
        )
    return _ok(
        {
            "view_id": view_id,
            "schema": schema.model_dump(),
            "blocos": [
                {"tipo": b.tipo, "params": b.params, "tamanho": _tamanho(b.tipo)}
                for b in schema.blocos
            ],
        }
    )


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


@app.post("/api/destinatarios")
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
    async with _engine.connect() as c:
        ator = await _ator(c, sessao)
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
    return _ok(saida)


class Compartilhar(BaseModel):
    view_id: str
    para: str
    mensagem: str | None = None


@app.post("/api/compartilhamentos")
async def compartilhar(
    corpo: Compartilhar, sessao: str | None = Cookie(default=None)
) -> dict[str, Any]:
    """Entrega pelo SISTEMA, nao por link.

    Ganhos sobre link solto: auditoria de quem compartilhou o que, revogacao, e
    nenhum segredo em transito — link e' encaminhado, colado em grupo, fica em
    historico.
    """
    async with _engine.begin() as c:
        ator = await _ator(c, sessao)
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
    return _ok({"enviado": True})


@app.get("/api/compartilhamentos")
async def caixa(sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    async with _engine.connect() as c:
        ator = await _ator(c, sessao)
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
    return _ok(
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


# ---------------------------------------------------------------- dados
class PaginaPedido(BaseModel):
    limite: int = Field(default=20, ge=1, le=200)
    cursor: str | None = None


class PedidoDados(BaseModel):
    params: dict[str, Any] = {}
    # FORA de `params`: paginacao e' transporte, e o modelo nunca a escolhe.
    pagina: PaginaPedido = PaginaPedido()


@app.post("/api/componentes/{componente_id}/dados")
async def dados(
    componente_id: str, corpo: PedidoDados, sessao: str | None = Cookie(default=None)
) -> dict[str, Any]:
    """O TERCEIRO momento de autorizacao — o unico que garante (ADR-0004).

    Mesmo que a composicao ja' tenha sido validada, aqui a permissao e'
    reconferida por registro, com a identidade real. E' este endpoint que um
    cliente forjando schema atingiria direto, sem passar pelo modelo.
    """
    async with _engine.connect() as c:
        ator = await _ator(c, sessao)
        comp = buscar(componente_id)
        if comp is None:
            raise ErroDominio("nao_encontrado", "Registro nao encontrado.")

        autorizar_ou_falhar(ator, permissoes_base(comp.requires), "este componente")
        # RequiresPorValor: permissao que depende do VALOR do param. Sem esta
        # linha, um schema forjado passa pela permissao base e o `load` roda.
        autorizar_params_ou_falhar(valores_proibidos(comp, ator), corpo.params)
        # ADR-0014: unidade pedida fora do escopo nega, nao devolve vazio.
        autorizar_unidade_do_param(ator, corpo.params.get("unidade_id"))

        params = comp.params.model_validate(corpo.params)
        ctx_dados = ContextoDados(ator=ator, unidades_permitidas=ator.unidades, tx=_Tx(c))
        ctx = LoadContext(
            ator=ator,
            unidades_permitidas=ator.unidades,
            repos=_repos(c),
            dados=ctx_dados,
            pagina=Pagina(limite=corpo.pagina.limite, cursor=corpo.pagina.cursor),
        )
        carga = await comp.load(params, ctx)
        # ADR-0020: `select` roda AQUI. So' o viewmodel atravessa a rede.
        vm = comp.select(carga)

    async with _engine.begin() as c2:
        await aud.registrar(
            c2,
            ator_id=ator.id,
            acao="ler",
            origem="assistente",
            entidade=componente_id,
            valor_novo={"params": corpo.params},
        )
    return _ok(vm.model_dump(mode="json"))


# ---------------------------------------------------------------- comandos
@app.post("/api/comandos/{nome}")
async def comando(
    nome: str,
    corpo: dict[str, Any],
    req: Request,
    resposta: Response,
    sessao: str | None = Cookie(default=None),
) -> dict[str, Any]:
    """A borda do PLANO DE ESCRITA. T-025, T-011 AC-3 e AC-4.

    Esta rota nao e' alcancavel a partir da saida do modelo, e nao e' por
    disciplina: `assistant` nao importa `commands` (import-linter, contrato 3), e
    o `CommandDef` que o catalogo publica nao carrega funcao nenhuma. O modelo
    pode fazer o formulario aparecer; quem dispara e' a pessoa que clica em
    salvar — pela mesma rota que a tela tradicional usa (ADR-0002).

    CSRF e `Origin` ja' foram conferidos no middleware, que roda em TODA escrita.
    """
    async with _engine.connect() as c:
        ator = await _ator(c, sessao)

    r = await pipeline.executar(
        nome,
        corpo,
        ator=ator,
        motor=_engine,
        origem="tela",
        idempotency_key=req.headers.get("Idempotency-Key"),
        if_match=req.headers.get("If-Match"),
    )
    if r.etag:
        resposta.headers["ETag"] = r.etag
    return _ok(r.dados, etag=r.etag, repetido=r.repetido)
