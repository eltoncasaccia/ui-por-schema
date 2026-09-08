"""T-018 · `lote_detalhe` — AC-2, AC-6, AC-8.

O AC-2 e' o mais importante do arquivo, e prova uma coisa so': **a negativa nao
diz nada**. Lote inexistente e lote de outra unidade tem de produzir a MESMA
resposta, byte a byte. Se a segunda fosse "sem permissao" e a primeira "nao
encontrado", qualquer pessoa mapearia o estoque das outras unidades perguntando
id por id e lendo qual erro volta (ADR-0014, CS-03).
"""

from typing import Any

import pytest
from fakes import contexto

from estoque.domain.erros import ErroDominio
from estoque.registry.componentes.lote_detalhe import Params, carregar, projetar


async def _vm(ator: Any, lote_id: str) -> Any:
    return projetar(await carregar(Params(lote_id=lote_id), contexto(ator)))


async def _erro(ator: Any, lote_id: str) -> ErroDominio:
    with pytest.raises(ErroDominio) as capturado:
        await _vm(ator, lote_id)
    return capturado.value


# --- AC-2 · a negativa que nao vaza, ADR-0014 e CS-03 --------------------


async def test_ac2_lote_de_outra_unidade_e_nao_encontrado(personas: dict[str, Any]) -> None:
    """Odair pede um lote REAL, que existe, e que nao e' dele."""
    erro = await _erro(personas["odair"], "l-amox-mtz")
    assert erro.codigo == "nao_encontrado"


async def test_ac2_fora_de_escopo_e_inexistente_sao_indistinguiveis(
    personas: dict[str, Any],
) -> None:
    """O teste central. Compara os dois erros inteiros, nao so' o codigo.

    Qualquer diferenca — mensagem, campo extra, contagem — vira oraculo: o
    atacante nao precisa ler o dado, basta distinguir as duas respostas.
    """
    existe_mas_nao_e_dele = await _erro(personas["odair"], "l-amox-mtz")
    nao_existe = await _erro(personas["odair"], "l-nao-existe-mesmo")

    def face_publica(e: ErroDominio) -> tuple[str, str, str]:
        return (e.codigo, e.mensagem_publica, repr(e))

    assert face_publica(existe_mas_nao_e_dele) == face_publica(nao_existe)


async def test_ac2_o_detalhe_do_diagnostico_nao_entra_na_resposta(
    personas: dict[str, Any],
) -> None:
    """O `load` passa `lote_id` e `ator` ao erro — para o log, nunca para fora.
    Se o id vazasse na resposta, a negativa confirmaria o id perguntado."""
    erro = await _erro(personas["odair"], "l-amox-mtz")
    # O id perguntado esta' no `detalhe_interno`, que e' do log...
    assert erro.detalhe_interno is not None
    # ...e nao aparece em nada que possa sair para o cliente.
    for face in (erro.mensagem_publica, repr(erro), str(erro)):
        assert "l-amox-mtz" not in face
        assert "u-odair" not in face


async def test_ac2_o_dono_do_escopo_ve_o_mesmo_lote(personas: dict[str, Any]) -> None:
    """O contraponto: se ninguem visse nada, os testes acima passariam a toa."""
    vm = await _vm(personas["ivo"], "l-amox-mtz")
    assert vm.lote_id == "l-amox-mtz"
    assert vm.unidade == "cd-matriz"


# --- ADR-0022 · os dois status ------------------------------------------


async def test_registrado_e_efetivo_sao_campos_distintos(personas: dict[str, Any]) -> None:
    """`l-amox-venc` esta' gravado como `liberado` e venceu ha' dez dias.

    A tela precisa dos dois: o efetivo diz o que vale agora, e o registrado diz
    qual decisao humana continua de pe' e precisa ser revertida pelo RT.
    """
    vm = await _vm(personas["ivo"], "l-amox-venc")
    assert vm.status_registrado == "liberado"
    assert vm.status_efetivo == "vencido"


# --- AC-6 · custo invisivel, CA-05 --------------------------------------


async def test_ac6_custo_nao_atravessa_nem_para_quem_pode(personas: dict[str, Any]) -> None:
    assert "custo.ler" in personas["marco"].permissoes
    bruto = (await _vm(personas["marco"], "l-amox-mtz")).model_dump_json()
    assert "custo" not in bruto
    assert "1250" not in bruto


# --- AC-8 · `select` e' puro --------------------------------------------


async def test_ac8_select_chamado_duas_vezes_da_o_mesmo(personas: dict[str, Any]) -> None:
    dados = await carregar(Params(lote_id="l-amox-mtz"), contexto(personas["ivo"]))
    assert projetar(dados) == projetar(dados)
