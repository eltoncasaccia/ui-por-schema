"""CS-05 · T-033 — a resposta do assistente e' auditada, e a trilha nao carrega custo.

T-011 AC-8 prova que toda LEITURA de dado gera evento. Faltavam as outras duas
metades do CS-05, pela borda e contra o banco real:

- a composicao do assistente vira evento, com o que foi REJEITADO — tentativa
  recusada e' o sinal que a auditoria existe para guardar;
- a trilha lida por quem nao tem `custo.ler` nao traz custo. Hoje nenhum comando
  grava custo na auditoria, entao o custo e' PLANTADO direto no banco: sem isso
  o teste passaria porque nao ha' o que esconder.
"""

import json
import secrets
from collections.abc import AsyncGenerator, Iterator, Mapping, Sequence
from typing import Any

import pytest
import sqlalchemy as sa
from borda import cliente, criar_sessao, descartar_pool, motor_dono

from estoque.assistant.adapter import Resposta
from estoque.assistant.trace import Modo, Trace
from estoque.server.rotas import assistente


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


@pytest.fixture(autouse=True)
def _limite_limpo() -> Iterator[None]:
    assistente.LIMITE._por_chave.clear()
    yield
    assistente.LIMITE._por_chave.clear()


class ModeloFixo:
    def __init__(self, bruto: str) -> None:
        self._bruto = bruto

    async def compor(
        self, pergunta: str, catalogo: Sequence[Mapping[str, Any]], modo: Modo = "restrito"
    ) -> Resposta:
        trace = Trace(origem="mock", modelo="mock", pergunta=pergunta, modo=modo)
        return Resposta(self._bruto, trace)


def _ultimo_evento(ator: str, acao: str) -> Any:
    with motor_dono().connect() as c:
        return (
            c.execute(
                sa.text(
                    "SELECT acao, origem, valor_novo FROM auditoria "
                    "WHERE ator_id=:a AND acao=:x ORDER BY id DESC LIMIT 1"
                ),
                {"a": ator, "x": acao},
            )
            .mappings()
            .one_or_none()
        )


# --- a composicao e' auditada, inclusive o que foi recusado -------------------


async def test_cs05_composicao_recusada_fica_na_trilha(monkeypatch: pytest.MonkeyPatch) -> None:
    resposta = json.dumps(
        {
            "versao": 1,
            "blocos": [
                {"tipo": "lote_lista", "params": {}},
                {"tipo": "auditoria_trilha", "params": {}},
            ],
        }
    )
    monkeypatch.setattr(assistente, "_adaptador", lambda: ModeloFixo(resposta))
    ator = f"cs05-cleide-{secrets.token_hex(4)}"
    sid = criar_sessao(usuario_id=ator, papel="conferente")

    async with cliente(sid) as cli:
        r = await cli.post("/api/assistente/compor", json={"pergunta": "mostre a trilha"})
    assert r.status_code == 200, r.text
    assert [b["tipo"] for b in r.json()["dados"]["blocos"]] == ["lote_lista"]

    evento = _ultimo_evento(ator, "compor")
    assert evento is not None, "composicao sem evento de auditoria"
    assert evento["origem"] == "assistente"
    registrado = json.dumps(evento["valor_novo"])
    assert "mostre a trilha" in registrado
    assert "auditoria_trilha" in registrado, "o bloco recusado nao ficou registrado"


# --- a trilha nao carrega custo -----------------------------------------------


def _plantar_custo(autor: str, marcador: str) -> None:
    """O que um comando futuro que ajustasse custo gravaria — nas duas formas que
    um filtro raso deixaria passar: na raiz e aninhado."""
    valor = {
        "produto_id": "cs05-produto",
        "marcador": marcador,
        "custo_unitario_centavos": 987654,
        "antes": {"total_centavos": 123457},
    }
    with motor_dono().begin() as c:
        c.execute(
            sa.text(
                "INSERT INTO auditoria "
                "(ator_id, acao, entidade, entidade_id, origem, valor_novo) "
                "VALUES (:a, 'ajustar_custo', 'produto', 'cs05-produto', 'tela', "
                "CAST(:v AS jsonb))"
            ),
            {"a": autor, "v": json.dumps(valor)},
        )


async def _ler_trilha(leitor: str, papel: str, autor: str) -> str:
    sid = criar_sessao(usuario_id=leitor, papel=papel)
    async with cliente(sid) as cli:
        r = await cli.post(
            "/api/componentes/auditoria_trilha/dados",
            json={"params": {"ator_id": autor, "periodo": "7"}},
        )
    assert r.status_code == 200, r.text
    return r.text


@pytest.mark.parametrize(
    ("leitor", "papel"),
    [
        ("cs05-helena", "rt"),  # auditoria.ler SEM custo.ler — o caso do CS-05
        ("cs05-sandra", "auditoria"),  # tem custo.ler, e a regra da casa vale igual
    ],
)
async def test_cs05_custo_gravado_na_auditoria_nao_sai_pela_trilha(
    leitor: str, papel: str
) -> None:
    autor = f"cs05-autor-{secrets.token_hex(4)}"
    marcador = f"cs05-{secrets.token_hex(6)}"
    _plantar_custo(autor, marcador)

    corpo = await _ler_trilha(leitor, papel, autor)

    # O canario: a linha plantada ESTA na resposta. Sem ele, uma trilha vazia
    # passaria na asserção de ausencia.
    assert marcador in corpo, "a linha com custo nao chegou a trilha"
    assert "987654" not in corpo
    assert "123457" not in corpo
    assert "custo_unitario_centavos" not in corpo
