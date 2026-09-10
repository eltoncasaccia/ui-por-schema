"""T-022 · `recebimento_detalhe` — AC-2, AC-3, AC-4, AC-5, AC-7.

Como `lote_detalhe`, o teste central e' o da negativa que nao vaza (AC-5): um
recebimento de outra unidade e um id inexistente produzem a MESMA resposta,
byte a byte (ADR-0014, CS-03).
"""

from typing import Any

import pytest
from fakes import contexto

from estoque.application.registry.componentes.recebimento_detalhe import (
    Params,
    carregar,
    projetar,
)
from estoque.domain.erros import ErroDominio


async def _vm(ator: Any, rid: str) -> Any:
    return projetar(await carregar(Params(recebimento_id=rid), contexto(ator)))


async def _erro(ator: Any, rid: str) -> ErroDominio:
    with pytest.raises(ErroDominio) as capturado:
        await _vm(ator, rid)
    return capturado.value


# --- AC-5 · a negativa que nao vaza (CA-06, ADR-0014, CS-03) ----------------


async def test_ac5_recebimento_de_outra_unidade_e_nao_encontrado(
    personas: dict[str, Any],
) -> None:
    """Odair pede `r-normal-mtz` — existe, e nao e' dele."""
    erro = await _erro(personas["odair"], "r-normal-mtz")
    assert erro.codigo == "nao_encontrado"


async def test_ac5_fora_de_escopo_e_inexistente_sao_indistinguiveis(
    personas: dict[str, Any],
) -> None:
    existe_mas_nao_e_dele = await _erro(personas["odair"], "r-normal-mtz")
    nao_existe = await _erro(personas["odair"], "r-nao-existe-mesmo")

    def face_publica(e: ErroDominio) -> tuple[str, str, str]:
        return (e.codigo, e.mensagem_publica, repr(e))

    assert face_publica(existe_mas_nao_e_dele) == face_publica(nao_existe)


async def test_ac5_o_id_perguntado_nao_entra_na_resposta(personas: dict[str, Any]) -> None:
    erro = await _erro(personas["odair"], "r-normal-mtz")
    assert erro.detalhe_interno is not None
    for face in (erro.mensagem_publica, repr(erro), str(erro)):
        assert "r-normal-mtz" not in face
        assert "u-odair" not in face


async def test_ac5_odair_ve_o_recebimento_da_propria_unidade(personas: dict[str, Any]) -> None:
    """O contraponto: Uberlandia e' dele."""
    vm = await _vm(personas["odair"], "r-uber")
    assert vm.recebimento_id == "r-uber"
    assert vm.unidade == "Uberlândia"


# --- AC-3 · controlado exibe as DUAS identificacoes (RN-R05) ----------------


async def test_ac3_recebimento_de_controlado_traz_conferente_e_rt(
    personas: dict[str, Any],
) -> None:
    vm = await _vm(personas["marco"], "r-controlado-mtz")
    assert vm.conferente == "u-cleide"
    assert vm.responsavel_tecnico == "u-helena"


async def test_ac3_recebimento_comum_nao_tem_segunda_identidade(
    personas: dict[str, Any],
) -> None:
    """O negativo de AC-3: sem RT, o campo e' `None` — nao um id inventado nem
    o conferente repetido."""
    vm = await _vm(personas["marco"], "r-normal-mtz")
    assert vm.conferente == "u-cleide"
    assert vm.responsavel_tecnico is None


# --- AC-4 · termolabil exibe a temperatura de chegada (RN-F01) --------------


async def test_ac4_termolabil_traz_temperatura_de_chegada(personas: dict[str, Any]) -> None:
    vm = await _vm(personas["marco"], "r-termo-ref")
    assert vm.temperatura_chegada_c == pytest.approx(5.4)


async def test_ac4_nao_termolabil_nao_traz_temperatura(personas: dict[str, Any]) -> None:
    vm = await _vm(personas["marco"], "r-normal-mtz")
    assert vm.temperatura_chegada_c is None


# --- AC-2 · pendencia de divergencia, e nao bloqueia (RN-R04) --------------


async def test_ac2_divergencia_e_um_campo_ao_lado_do_status_nao_no_lugar(
    personas: dict[str, Any],
) -> None:
    vm = await _vm(personas["marco"], "r-diverg-mtz")
    assert vm.tem_pendencia_divergencia is True
    # O status continua sendo um estado normal do fluxo — a pendencia nao o
    # substitui por um estado de erro.
    assert vm.status == "conferido"


async def test_ac2_sem_divergencia_o_campo_e_falso(personas: dict[str, Any]) -> None:
    vm = await _vm(personas["marco"], "r-normal-mtz")
    assert vm.tem_pendencia_divergencia is False


# --- AC-7 · nenhum custo exposto (CA-05) ----------------------------------


async def test_ac7_custo_nao_atravessa_nem_para_quem_pode(personas: dict[str, Any]) -> None:
    assert "custo.ler" in personas["marco"].permissoes
    bruto = (await _vm(personas["marco"], "r-controlado-mtz")).model_dump_json()
    assert "custo" not in bruto
    assert "centavos" not in bruto


# --- `select` puro ------------------------------------------------------


async def test_select_chamado_duas_vezes_da_o_mesmo(personas: dict[str, Any]) -> None:
    ctx = contexto(personas["marco"])
    dados = await carregar(Params(recebimento_id="r-controlado-mtz"), ctx)
    assert projetar(dados) == projetar(dados)
