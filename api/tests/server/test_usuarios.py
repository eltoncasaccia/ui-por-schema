"""T-038 — gestao de usuarios pela borda HTTP, contra o banco real. AC-1 a AC-6."""

import json
import secrets
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import sqlalchemy as sa
from borda import cliente, criar_sessao, descartar_pool, motor_dono

from estoque.application.registry.registry import catalogo_de
from estoque.domain.identidade import PERMISSOES_POR_PAPEL, Ator


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


def _uid(nome: str) -> str:
    return f"t038-{nome}-{secrets.token_hex(4)}"


async def _alterar(sid: str, alvo: str, corpo: dict[str, Any]) -> tuple[int, str]:
    async with cliente(sid) as cli:
        r = await cli.post(f"/api/usuarios/{alvo}", json=corpo)
    return r.status_code, r.text


def _linha(uid: str) -> dict[str, Any]:
    with motor_dono().connect() as c:
        return dict(
            c.execute(sa.text("SELECT nome, papel, ativo FROM usuario WHERE id=:u"), {"u": uid})
            .mappings()
            .one()
        )


def _diretor() -> tuple[str, str]:
    uid = _uid("marco")
    return uid, criar_sessao(usuario_id=uid, papel="diretor")


# ---------------------------------------------------------------- AC-1
def test_ac1_so_o_diretor_tem_usuario_gerenciar() -> None:
    donos = {p for p, perms in PERMISSOES_POR_PAPEL.items() if "usuario.gerenciar" in perms}
    assert donos == {"diretor"}


@pytest.mark.parametrize("papel", ["rt", "gerente", "conferente", "comprador", "auditoria"])
async def test_ac1_os_outros_papeis_sao_recusados_no_servidor(papel: str) -> None:
    alvo = _uid("alvo")
    criar_sessao(usuario_id=alvo, papel="conferente")
    sid = criar_sessao(usuario_id=_uid(papel), papel=papel)

    async with cliente(sid) as cli:
        lista = await cli.get("/api/usuarios")
    assert lista.status_code == 403, lista.text
    codigo, corpo = await _alterar(sid, alvo, {"papel": "diretor"})
    assert codigo == 403, corpo
    assert _linha(alvo)["papel"] == "conferente"


async def test_ac1_o_diretor_lista_sem_senha() -> None:
    alvo = _uid("alvo")
    criar_sessao(usuario_id=alvo, papel="conferente")
    _, sid = _diretor()
    async with cliente(sid) as cli:
        r = await cli.get("/api/usuarios")
    assert r.status_code == 200, r.text
    assert any(u["id"] == alvo for u in r.json()["dados"])
    assert "senha" not in r.text


# ---------------------------------------------------------------- AC-2
def test_ac2_nao_existe_rota_que_exclua_usuario() -> None:
    from estoque.server.app import app

    for caminho, item in app.openapi()["paths"].items():
        if caminho.startswith("/api/usuarios"):
            assert {x.upper() for x in item} <= {"GET", "POST"}, caminho


async def test_ac2_desativado_continua_no_banco_e_na_lista() -> None:
    alvo = _uid("alvo")
    criar_sessao(usuario_id=alvo, papel="conferente")
    _, sid = _diretor()

    codigo, corpo = await _alterar(sid, alvo, {"ativo": False})
    assert codigo == 200, corpo
    assert _linha(alvo) == {"nome": alvo, "papel": "conferente", "ativo": False}
    async with cliente(sid) as cli:
        r = await cli.get("/api/usuarios")
    assert next(u for u in r.json()["dados"] if u["id"] == alvo)["ativo"] is False


# ---------------------------------------------------------------- AC-3
async def test_ac3_atribuir_papel_audita_anterior_e_novo() -> None:
    alvo = _uid("alvo")
    criar_sessao(usuario_id=alvo, papel="conferente", unidades=("cd-matriz",))
    diretor, sid = _diretor()

    codigo, corpo = await _alterar(
        sid, alvo, {"papel": "gerente", "unidades": ["cd-matriz", "cd-refrigerado"]}
    )
    assert codigo == 200, corpo

    with motor_dono().connect() as c:
        ev = (
            c.execute(
                sa.text(
                    "SELECT ator_id, valor_anterior, valor_novo FROM auditoria "
                    "WHERE acao='usuario_alterar' AND entidade_id=:u"
                ),
                {"u": alvo},
            )
            .mappings()
            .one()
        )
    assert ev["ator_id"] == diretor
    assert ev["valor_anterior"] == {
        "papel": "conferente",
        "ativo": True,
        "unidades": ["cd-matriz"],
    }
    assert ev["valor_novo"] == {
        "papel": "gerente",
        "ativo": True,
        "unidades": ["cd-matriz", "cd-refrigerado"],
    }


# ---------------------------------------------------------------- AC-4
@pytest.mark.parametrize(
    "corpo", [{"papel": "rt"}, {"unidades": ["filial-uberlandia"]}, {"ativo": False}]
)
async def test_ac4_ninguem_altera_o_proprio_acesso(corpo: dict[str, Any]) -> None:
    diretor, sid = _diretor()
    codigo, texto = await _alterar(sid, diretor, corpo)
    assert codigo == 403, texto
    assert _linha(diretor) == {"nome": diretor, "papel": "diretor", "ativo": True}


# ---------------------------------------------------------------- AC-5
def test_ac5_nenhum_componente_de_usuario_no_catalogo(personas: dict[str, Ator]) -> None:
    ids = [c["id"] for c in catalogo_de(personas["marco"])]
    assert "usuario.gerenciar" in personas["marco"].permissoes
    assert not [i for i in ids if "usuario" in i]


# ---------------------------------------------------------------- AC-6
async def test_ac6_desativar_derruba_a_sessao_na_hora() -> None:
    alvo = _uid("alvo")
    sid_alvo = criar_sessao(usuario_id=alvo, papel="conferente")
    _, sid = _diretor()

    async with cliente(sid_alvo) as cli:
        antes = await cli.post("/api/componentes/lote_lista/dados", json={"params": {}})
    assert antes.status_code == 200, antes.text

    assert (await _alterar(sid, alvo, {"ativo": False}))[0] == 200

    async with cliente(sid_alvo) as cli:
        depois = await cli.post("/api/componentes/lote_lista/dados", json={"params": {}})
    assert depois.status_code == 401, depois.text


# ------------------------------------------------------- entrada hostil
@pytest.mark.parametrize(
    "corpo",
    [
        {"papel": "superusuario"},
        {"unidades": ["cd-sao-paulo"]},
        {"unidades": []},
        {},
        {"senha_hash": "x"},
    ],
)
async def test_corpo_invalido_e_recusado_e_nada_muda(corpo: dict[str, Any]) -> None:
    alvo = _uid("alvo")
    criar_sessao(usuario_id=alvo, papel="conferente")
    _, sid = _diretor()
    codigo, texto = await _alterar(sid, alvo, corpo)
    assert codigo == 422, texto
    assert _linha(alvo)["papel"] == "conferente"
    assert "usuario_alterar" not in json.dumps(texto)


async def test_alvo_inexistente_e_nao_encontrado() -> None:
    _, sid = _diretor()
    codigo, texto = await _alterar(sid, "t038-ninguem", {"papel": "rt"})
    assert codigo == 404, texto
