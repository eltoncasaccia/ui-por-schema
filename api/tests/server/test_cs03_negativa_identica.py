"""CS-03 · T-011 AC-7 — a negativa de registro nao diz se o registro existe.

[ADR-0014](../../../docs/adr/0014-erros-que-nao-vazam.md): registro individual
nega de forma **indistinguivel de inexistencia**. Se as duas respostas
diferissem em qualquer coisa, iterar ids mapearia o estoque das outras unidades
sem ler um dado sequer — o pedido nao precisa do conteudo, basta distinguir as
duas respostas.

**A armadilha do arquivo da tarefa:** "AC-7 quebra por detalhe — tempo de
resposta diferente, header a mais, ordem de chaves no JSON. Comparar o corpo
serializado, nao o objeto." Por isso aqui a comparacao e' de `r.content`, em
bytes, e nao de `r.json()`: dois dicionarios iguais podem ter serializacoes
diferentes, e e' a serializacao que vai pelo fio.

`test_lote_detalhe.py` compara as faces do `ErroDominio` — o objeto. Este
compara o que sai pela rede.
"""

from collections.abc import AsyncGenerator

import pytest
from borda import cliente, criar_sessao, descartar_pool


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


# Do seed (`make seed`). `l-amx-quar` esta' na Matriz; Odair alcanca so'
# Uberlandia. `l-amx-ube-quar` e' o dele, e existe para o contraponto.
LOTE_DE_OUTRA_UNIDADE = "l-amx-quar"
LOTE_INEXISTENTE = "l-jamais-existiu-0000"
LOTE_PROPRIO = "l-amx-ube-quar"

# Variam por requisicao e nao dizem nada sobre o registro pedido.
VOLATEIS = {"date", "server"}


async def _resposta(sid: str, lote_id: str) -> tuple[int, bytes, dict[str, str]]:
    async with cliente(sid) as cli:
        r = await cli.post(
            "/api/componentes/lote_detalhe/dados", json={"params": {"lote_id": lote_id}}
        )
    cabecalhos = {k.lower(): v for k, v in r.headers.items() if k.lower() not in VOLATEIS}
    return r.status_code, r.content, cabecalhos


@pytest.fixture
def odair() -> str:
    return criar_sessao(
        usuario_id="cs03-odair", papel="gerente", unidades=("filial-uberlandia",)
    )


async def test_ac7_o_corpo_e_identico_byte_a_byte(odair: str) -> None:
    """O criterio, na forma que o AC pede."""
    _, fora_do_escopo, _ = await _resposta(odair, LOTE_DE_OUTRA_UNIDADE)
    _, inexistente, _ = await _resposta(odair, LOTE_INEXISTENTE)
    assert fora_do_escopo == inexistente


async def test_ac7_o_status_e_identico(odair: str) -> None:
    fora, _, _ = await _resposta(odair, LOTE_DE_OUTRA_UNIDADE)
    nao_existe, _, _ = await _resposta(odair, LOTE_INEXISTENTE)
    assert fora == nao_existe == 404


async def test_ac7_os_cabecalhos_nao_denunciam(odair: str) -> None:
    """Um header a mais num dos caminhos e' o mesmo oraculo, por outra porta —
    `Content-Length` diferente ja' bastaria."""
    _, _, fora = await _resposta(odair, LOTE_DE_OUTRA_UNIDADE)
    _, _, nao_existe = await _resposta(odair, LOTE_INEXISTENTE)
    assert fora == nao_existe


async def test_ac7_a_resposta_nao_ecoa_o_id_perguntado(odair: str) -> None:
    """Ecoar o id confirma ao atacante o que ele mandou, e transforma a resposta
    em recibo. O id vai ao `detalhe_interno`, que e' do log."""
    _, corpo, _ = await _resposta(odair, LOTE_DE_OUTRA_UNIDADE)
    assert LOTE_DE_OUTRA_UNIDADE.encode() not in corpo
    assert b"cd-matriz" not in corpo
    assert b"cs03-odair" not in corpo


async def test_ac7_o_dono_do_escopo_ve_o_lote_dele(odair: str) -> None:
    """O contraponto. Sem ele, um endpoint que respondesse 404 para tudo
    passaria em todos os testes acima."""
    status, corpo, _ = await _resposta(odair, LOTE_PROPRIO)
    assert status == 200, corpo
    assert b"filial-uberlandia" in corpo or b"Uberl" in corpo


async def test_ac7_quem_alcanca_a_matriz_ve_o_mesmo_lote() -> None:
    """Fecha o outro lado: `l-amx-quar` EXISTE. A negativa que Odair recebe e'
    de escopo, nao de inexistencia — e e' justamente isso que nao pode aparecer
    na resposta dele."""
    ivo = criar_sessao(usuario_id="cs03-ivo", papel="gerente", unidades=("cd-matriz",))
    status, _, _ = await _resposta(ivo, LOTE_DE_OUTRA_UNIDADE)
    assert status == 200


async def test_ac7_vale_tambem_para_recebimento_detalhe(odair: str) -> None:
    """A regra e' do desenho, nao de um componente. Se so' `lote_detalhe` a
    respeitasse, o oraculo continuaria aberto pelo vizinho — e `recebimento_detalhe`
    e' o mais novo (T-022), que e' onde o padrao costuma se perder.
    """
    async with cliente(odair) as cli:
        fora = await cli.post(
            "/api/componentes/recebimento_detalhe/dados",
            json={"params": {"recebimento_id": "r-0001"}},
        )
        nao_existe = await cli.post(
            "/api/componentes/recebimento_detalhe/dados",
            json={"params": {"recebimento_id": "r-jamais-existiu"}},
        )
    assert fora.status_code == nao_existe.status_code == 404
    assert fora.content == nao_existe.content
