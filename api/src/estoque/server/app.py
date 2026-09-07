"""A borda HTTP. ADR-0004, ADR-0014, ADR-0019, ADR-0020.

O que este modulo faz que e' o ponto do projeto:

  /api/assistente/compor   modelo -> schema -> VALIDA contra o catalogo do ator
  /api/componentes/{id}/dados  load autorizado -> select NO SERVIDOR -> viewmodel

O schema recebido e' PAYLOAD NAO-CONFIAVEL, venha do modelo ou do cliente. E'
por isso que a validacao roda de novo aqui, e por isso `/componentes/{id}/dados`
reautoriza por registro mesmo que a composicao ja' tenha sido validada.
"""

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
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

import estoque.registry.indice  # noqa: F401  — registra os componentes
from estoque.assistant.adapter import (
    AdaptadorModelo,
    AdaptadorOpenRouter,
    ErroDeModelo,
    extrair_json,
)
from estoque.auditoria import registro as aud
from estoque.autorizacao.motor import (
    autorizar_ou_falhar,
    autorizar_params_ou_falhar,
    autorizar_unidade_do_param,
)
from estoque.data import modelos as m
from estoque.data.porta import ContextoDados, Repositorios
from estoque.data.repositorios import RepoLoteSQL, RepoMovimentoSQL, RepoProdutoSQL
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator
from estoque.registry.definir import LoadContext, Pagina, permissoes_base
from estoque.registry.registry import buscar, catalogo_de, valores_proibidos
from estoque.schema.validar import revalidar_ou_falhar, validar_schema
from estoque.schema.viewkey import novo_view_id, view_key
from estoque.server import sessao as ses
from estoque.server.config import Config

CFG = Config.do_ambiente()
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


@app.post("/api/auth/entrar")
async def entrar(corpo: Entrada, resposta: Response) -> dict[str, Any]:
    """Resposta e tempo UNIFORMES para usuario inexistente e senha errada.

    E' o ADR-0014 aplicado ao login: distinguir os dois casos enumera contas.
    Por isso o hash e' verificado mesmo quando o usuario nao existe — senao a
    diferenca de tempo faria o mesmo vazamento.
    """
    async with _engine.begin() as c:
        r = (
            (await c.execute(sa.select(m.usuario).where(m.usuario.c.email == corpo.email)))
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
            raise ErroDominio("nao_autenticado", "E-mail ou senha invalidos.")

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
    """Sem chave, FALHA. Nunca cai para o mock em silencio — o erro da v1."""
    try:
        return AdaptadorOpenRouter(modelo=CFG.modelo)
    except ErroDeModelo:
        raise


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


@app.get("/api/destinatarios")
async def destinatarios(sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    """Lista filtrada de quem pode receber. Nao e' um catalogo de usuarios:
    e' a lista de quem ESTE ator pode contatar."""
    async with _engine.connect() as c:
        ator = await _ator(c, sessao)
        rs = (
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
    return _ok([dict(r) for r in rs])


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
    limite: int = Field(default=40, ge=1, le=200)
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
