"""T-011 — AC-1, AC-5 e AC-8, pela borda de verdade.

Estes tres criterios estavam escritos e verificados **por inspecao de fonte**:
os testes de `test_erros_da_borda.py` afirmam que o handler existe no codigo,
nao que a borda se comporta assim. Um handler registrado com o decorador errado
passaria naqueles testes.

Aqui as tres afirmacoes sao feitas contra o app rodando, por HTTP.
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import sqlalchemy as sa
from borda import cliente, criar_sessao, descartar_pool, motor_dono
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


# ---------------------------------------------------------------------------
# AC-1 · nenhuma rota autenticada responde sem ator
# ---------------------------------------------------------------------------
#
# A lista de PUBLICAS e' explicita e justificada, e a varredura vem do proprio
# `openapi()`. E' o que faz uma rota NOVA reprovar por padrao: quem a adiciona
# ou exige sessao, ou vem aqui escrever por que ela pode ser publica.
PUBLICAS: dict[tuple[str, str], str] = {
    # cadastro e' publico por definicao, e nao concede papel (ADR-0019)
    ("POST", "/api/auth/registrar"): "cadastro",
    # e' a rota que CRIA a sessao; exigir sessao aqui seria circular
    ("POST", "/api/auth/entrar"): "login",
    # sair sem sessao e' no-op. Exigi-la prenderia justamente quem perdeu o cookie
    ("POST", "/api/auth/sair"): "logout",
    # health check do container: nao toca dado nem identidade
    ("GET", "/api/saude"): "health check",
    # atalho de demonstracao; fora de MODO_DEMO a propria rota devolve 404
    ("GET", "/api/auth/demo"): "demo",
}

# Corpo minimo que PASSA na validacao do Pydantic. Sem ele a resposta seria 422
# (corpo invalido) antes de chegar ao handler, e um 422 nao prova exigencia de
# sessao nenhuma — por isso o teste reprova o 422 em vez de aceita-lo.
CORPOS: dict[str, dict[str, Any]] = {
    "/api/assistente/compor": {"pergunta": "x"},
    "/api/comandos/{nome}": {},
    "/api/componentes/{componente_id}/dados": {},
    "/api/views": {"titulo": "t", "schema": {"versao": 1, "blocos": []}},
    "/api/destinatarios": {"schema": {"versao": 1, "blocos": []}},
    "/api/compartilhamentos": {"view_id": "x", "para": "y"},
    "/api/usuarios/{usuario_id}": {"papel": "rt"},
}


def rotas_protegidas() -> list[tuple[str, str]]:
    from estoque.server.app import app

    achadas: list[tuple[str, str]] = []
    for caminho, operacoes in app.openapi()["paths"].items():
        for metodo in operacoes:
            par = (metodo.upper(), caminho)
            if par[0] in {"HEAD", "OPTIONS"} or par in PUBLICAS:
                continue
            achadas.append(par)
    return sorted(achadas)


def concretizar(caminho: str) -> str:
    """Troca `{param}` por um valor qualquer: a rota tem de recusar por FALTA DE
    SESSAO antes de olhar se o id existe."""
    return (
        caminho.replace("{nome}", "qualquer")
        .replace("{componente_id}", "qualquer")
        .replace("{view_id}", "qualquer")
    )


def test_ac1_a_varredura_encontra_rotas() -> None:
    """Se `openapi()` mudar de forma, o teste abaixo passaria varrendo nada."""
    assert len(rotas_protegidas()) >= 8


@pytest.mark.parametrize(("metodo", "caminho"), rotas_protegidas())
async def test_ac1_rota_sem_ator_devolve_nao_autenticado(metodo: str, caminho: str) -> None:
    corpo = CORPOS.get(caminho)
    async with cliente(None) as cli:
        r = await cli.request(metodo, concretizar(caminho), json=corpo)

    assert r.status_code != 422, (
        f"{metodo} {caminho} recusou o CORPO antes de olhar a sessao. "
        "Acrescente um corpo valido em CORPOS — 422 nao prova exigencia de sessao."
    )
    assert r.status_code == 401, f"{metodo} {caminho} respondeu {r.status_code}: {r.text}"
    assert r.json()["erro"]["codigo"] == "nao_autenticado"


async def test_ac1_sessao_inexistente_e_igual_a_sessao_ausente() -> None:
    """Cookie com um sid inventado nao pode valer mais que cookie nenhum."""
    async with cliente("sessao-que-nunca-existiu") as cli:
        inventada = await cli.post("/api/componentes/lote_lista/dados", json={})
    async with cliente(None) as cli:
        ausente = await cli.post("/api/componentes/lote_lista/dados", json={})
    assert inventada.status_code == ausente.status_code == 401


# ---------------------------------------------------------------------------
# AC-5 · erro inesperado devolve envelope generico
# ---------------------------------------------------------------------------
SEGREDO = "detalhe-interno-que-nao-pode-vazar-8f2a"


async def test_ac5_excecao_nao_tratada_vira_envelope_generico(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uma excecao que NAO e' `ErroDominio`, levantada dentro do handler.

    `raise_app_exceptions=False` faz o transporte devolver a resposta do handler
    de erro em vez de repropagar — que e' o que um cliente HTTP de verdade ve.
    """
    from estoque.server import app as modulo_app
    from estoque.server.rotas import catalogo as rota_catalogo

    def explodir(*_a: object, **_k: object) -> None:
        raise RuntimeError(SEGREDO)

    monkeypatch.setattr(rota_catalogo, "ator_ou_falhar", explodir)

    async with AsyncClient(
        transport=ASGITransport(app=modulo_app.app, raise_app_exceptions=False),
        base_url="http://teste",
    ) as cli:
        r = await cli.get("/api/catalogo")

    assert r.status_code == 500
    assert r.json() == {
        "ok": False,
        "erro": {"codigo": "invalido", "mensagem": "Erro interno."},
    }


async def test_ac5_a_resposta_nao_carrega_stack_nem_detalhe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O par negativo, e o que o AC realmente pede: nada do interior escapa."""
    from estoque.server import app as modulo_app
    from estoque.server.rotas import catalogo as rota_catalogo

    def explodir(*_a: object, **_k: object) -> None:
        raise RuntimeError(SEGREDO)

    monkeypatch.setattr(rota_catalogo, "ator_ou_falhar", explodir)

    async with AsyncClient(
        transport=ASGITransport(app=modulo_app.app, raise_app_exceptions=False),
        base_url="http://teste",
    ) as cli:
        r = await cli.get("/api/catalogo")

    corpo = r.text
    assert SEGREDO not in corpo
    assert "RuntimeError" not in corpo
    assert "Traceback" not in corpo
    assert "estoque/server" not in corpo, "caminho de arquivo do servidor na resposta"


async def test_ac5_erro_de_dominio_continua_com_o_codigo_certo() -> None:
    """O contraponto: o handler generico nao pode ter engolido os de dominio.

    Sem esta afirmacao, um `exception_handler(Exception)` cedo demais
    transformaria todo 401 e 404 em 500 e o AC-5 continuaria verde.
    """
    async with cliente(None) as cli:
        r = await cli.get("/api/catalogo")
    assert r.status_code == 401
    assert r.json()["erro"]["codigo"] == "nao_autenticado"


# ---------------------------------------------------------------------------
# AC-8 · toda leitura de dado gera evento de auditoria (CS-05, RN-D05)
# ---------------------------------------------------------------------------
#
# LEITURA DE DADO, e nao "toda requisicao": `/api/catalogo`, `/api/auth/eu` e
# `/api/saude` nao alcancam dado de dominio — o primeiro devolve o vocabulario
# calculado do proprio ator, o segundo a identidade de quem ja' esta' logado, o
# terceiro nada. Auditar os tres encheria a trilha de linhas que nao respondem
# a pergunta do `RN-D05` ("quem olhou o que"), e trilha ruidosa e' trilha que
# ninguem le. O recorte esta' registrado como achado A-35.
COMPONENTES_DE_LEITURA = ("lote_lista", "fila_vencimento", "estoque_indicador", "produto_ficha")

# `produto_ficha` exige um id, e o AC e' sobre a requisicao BEM-SUCEDIDA: com id
# inventado a resposta e' 404 e o teste pularia — teste que pula e' teste que
# nao existe. O id vem do seed (`make seed`).
PARAMS_POR_COMPONENTE: dict[str, dict[str, Any]] = {
    "produto_ficha": {"produto_id": "p-amoxicilina"},
    "estoque_indicador": {"metrica": "lotes_em_quarentena"},
}


def eventos_de_leitura(ator: str, entidade: str) -> int:
    with motor_dono().connect() as c:
        return int(
            c.execute(
                sa.text(
                    "SELECT count(*) FROM auditoria "
                    "WHERE acao='ler' AND entidade=:e AND ator_id=:a"
                ),
                {"e": entidade, "a": ator},
            ).scalar_one()
        )


@pytest.mark.parametrize("componente", COMPONENTES_DE_LEITURA)
async def test_ac8_toda_leitura_bem_sucedida_e_auditada(componente: str) -> None:
    ator = "t011-ac8-marco"
    sid = criar_sessao(usuario_id=ator, papel="diretor", unidades=("cd-matriz",))
    antes = eventos_de_leitura(ator, componente)

    async with cliente(sid) as cli:
        params = PARAMS_POR_COMPONENTE.get(componente, {})
        r = await cli.post(f"/api/componentes/{componente}/dados", json={"params": params})

    assert r.status_code == 200, f"{componente} respondeu {r.status_code}: {r.text}"
    assert eventos_de_leitura(ator, componente) == antes + 1


async def test_ac8_o_evento_diz_quem_olhou_e_com_quais_params() -> None:
    """ "Gerou evento" nao basta: sem ator e sem recorte, a trilha nao responde
    a pergunta que o `RN-D05` faz."""
    ator = "t011-ac8-ivo"
    sid = criar_sessao(usuario_id=ator, papel="gerente", unidades=("cd-matriz",))
    async with cliente(sid) as cli:
        r = await cli.post(
            "/api/componentes/lote_lista/dados",
            json={"params": {"unidade_id": "cd-matriz"}},
        )
    assert r.status_code == 200, r.text

    with motor_dono().connect() as c:
        linha = (
            c.execute(
                sa.text(
                    "SELECT ator_id, entidade, origem, valor_novo FROM auditoria "
                    "WHERE acao='ler' AND ator_id=:a ORDER BY id DESC LIMIT 1"
                ),
                {"a": ator},
            )
            .mappings()
            .one()
        )
    assert linha["ator_id"] == ator
    assert linha["entidade"] == "lote_lista"
    valor = linha["valor_novo"]
    if isinstance(valor, str):
        valor = json.loads(valor)
    assert valor["params"]["unidade_id"] == "cd-matriz"


async def test_ac8_requisicao_recusada_nao_vira_evento_de_leitura() -> None:
    """O par negativo: nao se registra ter lido o que nao foi lido.

    Rafael (comprador) nao tem `movimento.ler`. A recusa acontece antes do
    `load`, e portanto antes do registro.
    """
    ator = "t011-ac8-rafael"
    sid = criar_sessao(usuario_id=ator, papel="comprador", unidades=("cd-matriz",))
    antes = eventos_de_leitura(ator, "movimento_lista")
    async with cliente(sid) as cli:
        r = await cli.post("/api/componentes/movimento_lista/dados", json={"params": {}})
    assert r.status_code == 403
    assert eventos_de_leitura(ator, "movimento_lista") == antes
