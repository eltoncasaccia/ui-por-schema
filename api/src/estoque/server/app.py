"""A borda HTTP: monta a aplicacao e registra o que vale para TODA rota.

O que este projeto tem de proprio esta em `rotas/`:

  rotas/assistente.py   modelo -> schema -> VALIDA contra o catalogo do ator
  rotas/dados.py        load autorizado -> select NO SERVIDOR -> viewmodel
  rotas/comandos.py     o unico caminho de escrita, inalcancavel pelo modelo

Aqui ficam so' as tres coisas que nao podem morar numa rota, porque valem para
todas: o middleware de CSRF, os tres handlers de erro, e o ciclo de vida.

**O CSRF e' middleware e nao dependencia por rota de proposito.** Dependencia
esquecida numa rota nova e' um buraco silencioso — e rota nova e' exatamente o
que se acrescenta com pressa (ADR-0031, ADR-0032).

`CFG` e `_engine` sao reexportados de `deps`: continuam importaveis daqui, e sao
o mesmo objeto.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

import estoque.application.commands.indice  # registra os comandos de escrita
import estoque.application.registry.indice  # noqa: F401  — registra os componentes
from estoque.auth import csrf
from estoque.domain.erros import ErroDominio
from estoque.server.deps import CFG, OBS
from estoque.server.deps import motor as _engine
from estoque.server.rotas import (
    assistente,
    auth,
    catalogo,
    comandos,
    compartilhamento,
    dados,
    saude,
    usuarios,
    views,
)

# Reexportados de `deps` de proposito, e declarados aqui porque `mypy --strict`
# so' aceita reexport explicito. Sao o MESMO objeto: quem importa
# `estoque.server.app.CFG` ou `._engine` recebe o de `deps`.
__all__ = ["CFG", "OBS", "_engine", "app"]


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


# A ordem nao importa para o roteamento — cada rota traz o proprio caminho
# completo. Importa para quem le: e' o mapa da borda, do publico ao privativo.
for _mod in (
    saude,
    auth,
    catalogo,
    assistente,
    views,
    compartilhamento,
    dados,
    comandos,
    usuarios,
):
    app.include_router(_mod.rotas)
