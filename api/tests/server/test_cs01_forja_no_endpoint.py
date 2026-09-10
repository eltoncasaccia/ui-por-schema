"""CS-01 · T-011 AC-2 — schema forjado direto no endpoint, sem o modelo no caminho.

O criterio central da tarefa, e o terceiro momento do
[ADR-0004](../../../docs/adr/0004-autorizacao-em-tres-momentos.md): os dois
primeiros controlam o que e' **oferecido**, e so' este controla o que e'
**acessivel**. Um cliente que monta o JSON a mao nao passa pelo catalogo
filtrado nem pela revalidacao de composicao — chega aqui.

`test_regressao_forja.py` ja' prova as duas funcoes de autorizacao
isoladamente. O que faltava e' o que o AC pede com todas as letras: *"enviado
direto a `/api/componentes/:id/dados`"*. Funcao correta que a rota esqueceu de
chamar passa naquele teste e falha neste.
"""

from collections.abc import AsyncGenerator

import pytest
from borda import cliente, criar_sessao, descartar_pool


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


PARAMS_VAZIOS: dict[str, object] = {}


async def _pedir(
    sid: str, componente: str, params: dict[str, object] | None = None
) -> tuple[int, str]:
    async with cliente(sid) as cli:
        r = await cli.post(
            f"/api/componentes/{componente}/dados",
            json={"params": params if params is not None else PARAMS_VAZIOS},
        )
    return r.status_code, r.text


# --- a forja literal do AC-2: componente fora do catalogo do ator ------------


async def test_ac2_componente_fora_do_catalogo_do_ator_e_recusado() -> None:
    """Rafael e' comprador: tem `lote.ler` e `custo.ler`, NAO tem `movimento.ler`.

    `movimento_lista` nunca aparece no catalogo dele, entao o modelo nao teria
    como propor. Ele monta o JSON a mao e manda direto — e a rota recusa.
    """
    sid = criar_sessao(usuario_id="cs01-rafael", papel="comprador", unidades=("cd-matriz",))
    codigo, corpo = await _pedir(sid, "movimento_lista")
    assert codigo == 403, corpo
    assert "nao_autorizado" in corpo


async def test_ac2_acao_privativa_do_rt_e_recusada_para_os_outros() -> None:
    """`RN-R02`: liberar quarentena e' privativo do RT, "nenhum outro papel, em
    nenhuma circunstancia". Nem o diretor."""
    sid = criar_sessao(usuario_id="cs01-marco", papel="diretor", unidades=("cd-matriz",))
    codigo, corpo = await _pedir(sid, "quarentena_liberar", {"lote_id": "l-amx-quar"})
    assert codigo == 403, corpo


async def test_ac2_o_rt_passa_no_mesmo_pedido() -> None:
    """O contraponto obrigatorio. Sem ele, uma rota que recusasse TUDO deixaria
    os dois testes acima verdes e a suite nao provaria nada."""
    sid = criar_sessao(usuario_id="cs01-helena", papel="rt", unidades=("cd-matriz",))
    codigo, corpo = await _pedir(sid, "quarentena_liberar", {"lote_id": "l-amx-quar"})
    assert codigo == 200, corpo


# --- a forja por VALOR de param (achado A-05) -------------------------------


async def test_ac2_valor_de_enum_filtrado_por_permissao_e_recusado() -> None:
    """O catalogo REMOVE `valor_em_estoque` do enum de quem nao tem `custo.ler`.

    Remover do enum impede o modelo de propor; nao impede o cliente de digitar.
    Cleide (conferente) ve `estoque_indicador` e nao pode ver a metrica de
    dinheiro — e o endpoint tem de recusar, nao apenas devolver zero.
    """
    sid = criar_sessao(usuario_id="cs01-cleide", papel="conferente", unidades=("cd-matriz",))
    codigo, corpo = await _pedir(sid, "estoque_indicador", {"metrica": "valor_em_estoque"})
    assert codigo == 403, corpo
    assert "nao_autorizado" in corpo


async def test_ac2_a_mesma_metrica_passa_para_quem_tem_custo_ler() -> None:
    sid = criar_sessao(usuario_id="cs01-rafael2", papel="comprador", unidades=("cd-matriz",))
    codigo, corpo = await _pedir(sid, "estoque_indicador", {"metrica": "valor_em_estoque"})
    assert codigo == 200, corpo


async def test_ac2_a_metrica_permitida_passa_para_cleide() -> None:
    """Fecha o par: a recusa acima e' sobre o VALOR, nao sobre o componente."""
    sid = criar_sessao(usuario_id="cs01-cleide2", papel="conferente", unidades=("cd-matriz",))
    codigo, corpo = await _pedir(sid, "estoque_indicador", {"metrica": "lotes_em_quarentena"})
    assert codigo == 200, corpo


# --- a forja de ESCOPO declarado (ADR-0014) ---------------------------------


async def test_ac2_unidade_fora_do_escopo_nega_explicitamente() -> None:
    """ADR-0014: escopo DECLARADO nega por nome. Devolver lista vazia ensinaria
    que a Matriz nao tem nada — falso, e pior que negar."""
    sid = criar_sessao(
        usuario_id="cs01-odair", papel="gerente", unidades=("filial-uberlandia",)
    )
    codigo, corpo = await _pedir(sid, "lote_lista", {"unidade_id": "cd-matriz"})
    assert codigo == 403, corpo


async def test_ac2_a_unidade_propria_passa() -> None:
    sid = criar_sessao(
        usuario_id="cs01-odair2", papel="gerente", unidades=("filial-uberlandia",)
    )
    codigo, corpo = await _pedir(sid, "lote_lista", {"unidade_id": "filial-uberlandia"})
    assert codigo == 200, corpo


# --- forja de id de componente ----------------------------------------------


async def test_ac2_componente_inexistente_e_nao_encontrado() -> None:
    sid = criar_sessao(usuario_id="cs01-ivo", papel="gerente", unidades=("cd-matriz",))
    codigo, corpo = await _pedir(sid, "componente_que_nao_existe")
    assert codigo == 404, corpo


@pytest.mark.parametrize(
    "forjado",
    ["../../etc/passwd", "lote_lista;drop", "LOTE_LISTA", "lote lista"],
)
async def test_ac2_id_malformado_nao_alcanca_registro_nenhum(forjado: str) -> None:
    """O id vem da URL, e a URL e' do cliente. `buscar()` e' consulta a um dict
    de ids registrados — nao ha caminho para arquivo nem para SQL —, e este
    teste e' o que impede alguem de trocar por algo que tenha."""
    sid = criar_sessao(usuario_id="cs01-ivo2", papel="gerente", unidades=("cd-matriz",))
    codigo, _ = await _pedir(sid, forjado)
    assert codigo in (404, 405), f"{forjado} respondeu {codigo}"


# --- a recusa nao entrega dado ----------------------------------------------


async def test_ac2_o_corpo_da_recusa_nao_carrega_dado_nem_lista_de_ids() -> None:
    """`RN-A07` e ADR-0014: a negativa nao pode virar catalogo do que existe."""
    sid = criar_sessao(usuario_id="cs01-rafael3", papel="comprador", unidades=("cd-matriz",))
    _, corpo = await _pedir(sid, "movimento_lista")
    for vazamento in ("l-amx", "cd-matriz", "movimento.ler", "linhas", "dados"):
        assert vazamento not in corpo, f"a recusa vazou {vazamento!r}: {corpo}"
