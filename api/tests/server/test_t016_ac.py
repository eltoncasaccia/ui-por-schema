"""T-016 — AC-5 e AC-6, os dois critérios que só existem no servidor.

**AC-5 é o critério de segurança da tarefa**, e o arquivo dela diz por quê:
*"endereço de view que carrega dado com a permissão de quem criou é escalação de
privilégio disfarçada de conveniência"*. O `viewId` **aponta para** uma view; não
concede acesso a ela (ADR-0021, riscos aceitos).

Os ACs são da T-016 e os testes moram aqui, no lado da API, porque a regra vive
aqui: um teste no cliente provaria apenas que o cliente pede — e o cliente é
justamente quem não se pode obrigar a nada. A lista de propriedade exclusiva da
T-016 nomeava só arquivos de `web/`, o que não cobre os próprios ACs dela;
corrigida no arquivo da tarefa.

Duas propriedades sustentam o AC-5, e as duas são testadas:

1. `GET /api/views/{id}` devolve **schema, nunca dado**. Não há o que vazar de
   Marco, porque a resposta não carrega linha de estoque nenhuma.
2. O schema é **revalidado contra o catálogo de quem abre**, e os dados vêm
   depois, por `/api/componentes/{id}/dados`, sob a identidade de quem pediu.
"""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from borda import cliente, criar_sessao, descartar_pool


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


def schema(*blocos: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "versao": 1,
        "blocos": [{"tipo": tipo, "params": params} for tipo, params in blocos],
    }


async def criar_view(sid: str, esquema: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    async with cliente(sid) as cli:
        r = await cli.post("/api/views", json={"titulo": "t", "schema": esquema})
    return r.status_code, (r.json().get("dados") or {})


async def abrir_view(sid: str, view_id: str) -> tuple[int, dict[str, Any], str]:
    async with cliente(sid) as cli:
        r = await cli.get(f"/api/views/{view_id}")
    return r.status_code, (r.json().get("dados") or {}), r.text


def marco() -> str:
    """Diretor, alcança as três unidades, tem `auditoria.ler`."""
    return criar_sessao(
        usuario_id="t016-marco",
        papel="diretor",
        unidades=("cd-matriz", "cd-refrigerado", "filial-uberlandia"),
    )


def odair() -> str:
    """Gerente de Uberlândia. Não alcança a Matriz e não tem `auditoria.ler`."""
    return criar_sessao(
        usuario_id="t016-odair", papel="gerente", unidades=("filial-uberlandia",)
    )


# --- AC-5 · quem abre carrega sob a PRÓPRIA permissão -----------------------


async def test_ac5_abrir_view_nao_devolve_dado_nenhum() -> None:
    """A primeira metade do AC-5, e a que o torna simples: a resposta de
    `/api/views/{id}` é schema e layout. Não há dado de Marco para vazar porque
    não há dado na resposta."""
    esquema = schema(("lote_lista", {"unidade_id": "cd-matriz"}))
    codigo, dados = await criar_view(marco(), esquema)
    assert codigo == 200, dados

    codigo, corpo, bruto = await abrir_view(odair(), dados["view_id"])
    assert codigo == 200, bruto
    assert set(corpo) == {"view_id", "schema", "blocos"}
    # Nada de linha, saldo ou id de lote — nem sob outro nome.
    for vazamento in ("linhas", "saldo", "l-amx", "total"):
        assert vazamento not in bruto, f"a abertura devolveu {vazamento!r}"


async def test_ac5_o_bloco_chega_a_odair_mas_o_dado_dele_e_negado() -> None:
    """A segunda metade, e o desenho inteiro em dois passos.

    O bloco pede `unidade_id=cd-matriz` — unidade que Odair não alcança. Abrir a
    view devolve o bloco (é só composição); **buscar o dado dele é recusado**,
    porque o terceiro momento do ADR-0004 roda com a identidade de Odair.
    """
    _, dados = await criar_view(marco(), schema(("lote_lista", {"unidade_id": "cd-matriz"})))
    sid_odair = odair()

    codigo, corpo, _ = await abrir_view(sid_odair, dados["view_id"])
    assert codigo == 200
    assert [b["tipo"] for b in corpo["blocos"]] == ["lote_lista"]

    # E agora o que a tela faria em seguida, com a identidade de quem abriu.
    async with cliente(sid_odair) as cli:
        r = await cli.post(
            "/api/componentes/lote_lista/dados",
            json={"params": {"unidade_id": "cd-matriz"}},
        )
    assert r.status_code == 403, r.text
    assert "cd-matriz" not in r.text or "nao_autorizado" in r.text


async def test_ac5_marco_ve_o_dado_que_odair_nao_ve() -> None:
    """O contraponto obrigatório: se ninguém visse nada, os testes acima
    passariam a toa. A mesma view, o mesmo bloco, o outro ator."""
    sid_marco = marco()
    _, dados = await criar_view(sid_marco, schema(("lote_lista", {"unidade_id": "cd-matriz"})))
    codigo, _, _ = await abrir_view(sid_marco, dados["view_id"])
    assert codigo == 200

    async with cliente(sid_marco) as cli:
        r = await cli.post(
            "/api/componentes/lote_lista/dados",
            json={"params": {"unidade_id": "cd-matriz"}},
        )
    assert r.status_code == 200, r.text


async def test_ac5_view_de_outro_ator_nao_exige_ser_o_dono() -> None:
    """A view não é privada por autor — ela é revalidada por quem abre.

    Se abrir exigisse ser o criador, o compartilhamento não existiria; se não
    revalidasse, seria escalação. O desenho é o do meio, e este teste fixa isso.
    """
    _, dados = await criar_view(marco(), schema(("fila_vencimento", {"janela": "90"})))
    codigo, corpo, bruto = await abrir_view(odair(), dados["view_id"])
    assert codigo == 200, bruto
    assert corpo["view_id"] == dados["view_id"]


# --- AC-6 · componente fora do catálogo de quem abre ------------------------


async def test_ac6_componente_fora_do_catalogo_e_rejeitado_na_abertura() -> None:
    """`auditoria_trilha` exige `auditoria.ler`. Marco tem; Odair não.

    Marco compõe e salva. Odair abre o mesmo endereço: o bloco **não** chega —
    e como era o único, a abertura inteira é recusada.
    """
    codigo, dados = await criar_view(marco(), schema(("auditoria_trilha", {})))
    assert codigo == 200, dados

    codigo, _, bruto = await abrir_view(odair(), dados["view_id"])
    assert codigo == 422, bruto
    assert "auditoria_trilha" not in bruto, "a recusa nomeou o componente negado"


async def test_ac6_o_bloco_negado_some_e_o_permitido_fica() -> None:
    """Schema misto: um bloco que Odair pode e um que não pode.

    O negado **some**; o permitido continua. Recusar a view inteira por causa de
    um bloco seria pior para quem recebe — e devolver os dois seria o vazamento.
    """
    codigo, dados = await criar_view(
        marco(),
        schema(("fila_vencimento", {"janela": "90"}), ("auditoria_trilha", {})),
    )
    assert codigo == 200, dados

    codigo, corpo, bruto = await abrir_view(odair(), dados["view_id"])
    assert codigo == 200, bruto
    tipos = [b["tipo"] for b in corpo["blocos"]]
    assert tipos == ["fila_vencimento"], tipos
    assert "auditoria_trilha" not in bruto


async def test_ac6_o_mesmo_endereco_traz_os_dois_blocos_para_quem_pode() -> None:
    """O contraponto do AC-6: a view não foi mutilada na gravação, foi filtrada
    na abertura. Marco abre o mesmo id e recebe os dois."""
    sid_marco = marco()
    _, dados = await criar_view(
        sid_marco,
        schema(("fila_vencimento", {"janela": "90"}), ("auditoria_trilha", {})),
    )
    _, corpo, _ = await abrir_view(sid_marco, dados["view_id"])
    assert [b["tipo"] for b in corpo["blocos"]] == ["fila_vencimento", "auditoria_trilha"]


async def test_ac6_criar_view_com_componente_que_o_autor_nao_pode_e_recusado() -> None:
    """A barreira também na entrada: Odair não salva uma view de
    `auditoria_trilha`. Sem isso, ele fabricaria o endereço e pediria a alguém
    com permissão para abrir — o schema é payload não-confiável nas duas pontas.
    """
    codigo, _ = await criar_view(odair(), schema(("auditoria_trilha", {})))
    assert codigo == 422


# --- o endereço é opaco (ADR-0021) -----------------------------------------


async def test_view_id_nao_e_derivado_do_conteudo() -> None:
    """Recompor a MESMA tela gera `view_id` diferente e `view_key` igual.

    É a conformidade do ADR-0021, e a razão de os dois identificadores
    existirem: hash de conteúdo não é revogável, então não pode ser o endereço.
    """
    sid = marco()
    esquema = schema(("fila_vencimento", {"janela": "90"}))
    _, um = await criar_view(sid, esquema)
    _, dois = await criar_view(sid, esquema)

    assert um["view_id"] != dois["view_id"], "o endereço não pode ser o hash"
    assert um["view_key"] == dois["view_key"], "a mesma tela precisa se reconhecer"


async def test_view_id_tem_entropia_suficiente() -> None:
    """ADR-0021: ao menos 128 bits. Endereço curto é endereço enumerável."""
    _, dados = await criar_view(marco(), schema(("fila_vencimento", {"janela": "90"})))
    # `token_urlsafe` rende ~6 bits por caractere; 22 caracteres ≥ 128 bits.
    assert len(dados["view_id"]) >= 22, dados["view_id"]


async def test_view_key_nunca_aparece_no_endereco() -> None:
    """O teste negativo do ADR-0021, do lado do servidor: a `view_key` é
    devolvida no corpo — para deduplicar favorito — e **não** é aceita como
    endereço. Quem tentar abrir por ela recebe a negativa de sempre."""
    sid = marco()
    _, dados = await criar_view(sid, schema(("fila_vencimento", {"janela": "90"})))
    codigo, _, _ = await abrir_view(sid, dados["view_key"])
    assert codigo == 404
