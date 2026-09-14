"""CS-01 · T-033 — schema gigante e escrita forjada, pela borda que recebe schema.

`test_cs01_forja_no_endpoint.py` (T-011) cobre a forja em `/dados`. O escopo do
CS-01 pede mais duas, que nenhum teste de borda cobria: schema GIGANTE e
componente de escrita composto junto de outros. `POST /api/views` e' a porta
certa: recebe schema do cliente, persiste, e o `GET` o devolve a quem abrir.
"""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from borda import cliente, criar_sessao, descartar_pool


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


LEITURA: dict[str, Any] = {"tipo": "lote_lista", "params": {}}
ESCRITA: dict[str, Any] = {"tipo": "quarentena_liberar", "params": {"lote_id": "cs01-lote"}}


async def _criar(
    sid: str, schema: dict[str, Any], titulo: str = "cs01"
) -> tuple[int, str, Any]:
    async with cliente(sid) as cli:
        r = await cli.post("/api/views", json={"titulo": titulo, "schema": schema})
        if r.status_code != 200:
            return r.status_code, r.text, None
        vid = r.json()["dados"]["view_id"]
        aberta = await cli.get(f"/api/views/{vid}")
    assert aberta.status_code == 200, aberta.text
    return r.status_code, r.text, aberta.json()["dados"]


def _tipos(dados: Any) -> list[str]:
    return [str(b["tipo"]) for b in dados["blocos"]]


# --- gigante ------------------------------------------------------------------


async def test_cs01_treze_blocos_e_recusado() -> None:
    sid = criar_sessao(usuario_id="cs01g-helena", papel="rt")
    codigo, corpo, _ = await _criar(sid, {"versao": 1, "blocos": [LEITURA] * 13})
    assert codigo == 422, corpo
    assert "invalido" in corpo


async def test_cs01_doze_blocos_passam() -> None:
    """O contraponto: sem ele, um teto de zero passaria no teste acima."""
    sid = criar_sessao(usuario_id="cs01g-helena2", papel="rt")
    codigo, corpo, dados = await _criar(sid, {"versao": 1, "blocos": [LEITURA] * 12})
    assert codigo == 200, corpo
    assert len(dados["blocos"]) == 12


async def test_cs01_treze_params_e_recusado() -> None:
    sid = criar_sessao(usuario_id="cs01g-helena3", papel="rt")
    params = {f"p{i}": 1 for i in range(13)}
    codigo, corpo, _ = await _criar(
        sid, {"versao": 1, "blocos": [{"tipo": "lote_lista", "params": params}]}
    )
    assert codigo == 422, corpo


@pytest.mark.xfail(
    strict=True,
    reason="A-42: `titulo` do schema nao tem teto — 1 MB e' aceito, persistido e devolvido",
)
async def test_cs01_titulo_de_um_megabyte_e_recusado() -> None:
    """Blocos e params tem teto; o titulo, nao. `strict`: se alguem puser o teto,
    o xfail vira falha e obriga a tirar esta marca — o achado nao fica aberto
    no documento depois de fechado no codigo."""
    sid = criar_sessao(usuario_id="cs01g-helena4", papel="rt")
    codigo, _, _ = await _criar(
        sid, {"versao": 1, "titulo": "x" * 1_000_000, "blocos": [LEITURA]}
    )
    assert codigo == 422


# --- escrita composta junto de leitura ----------------------------------------


async def test_cs01_escrita_fora_do_catalogo_some_da_composicao_forjada() -> None:
    """Cleide nao tem `lote.liberar`. O formulario de liberacao vem colado num
    bloco que ela pode ver — e sai; o que fica e' so' o que ela ja' alcancava."""
    sid = criar_sessao(usuario_id="cs01g-cleide", papel="conferente")
    codigo, corpo, dados = await _criar(sid, {"versao": 1, "blocos": [LEITURA, ESCRITA]})
    assert codigo == 200, corpo
    assert _tipos(dados) == ["lote_lista"]
    assert "quarentena_liberar" not in str(dados)


async def test_cs01_escrita_forjada_sozinha_e_recusada() -> None:
    sid = criar_sessao(usuario_id="cs01g-cleide2", papel="conferente")
    codigo, corpo, _ = await _criar(sid, {"versao": 1, "blocos": [ESCRITA]})
    assert codigo == 422, corpo


async def test_cs01_o_rt_abre_o_formulario_de_liberacao() -> None:
    """Contraponto por permissao, com o bloco SOZINHO — a composicao de escrita
    com leitura e' o achado A-43, e este teste nao a abencoa."""
    sid = criar_sessao(usuario_id="cs01g-helena5", papel="rt")
    codigo, corpo, dados = await _criar(sid, {"versao": 1, "blocos": [ESCRITA]})
    assert codigo == 200, corpo
    assert _tipos(dados) == ["quarentena_liberar"]
