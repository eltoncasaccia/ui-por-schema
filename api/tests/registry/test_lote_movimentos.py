"""T-018 · `lote_movimentos` — AC-2, AC-3, AC-4, AC-6, AC-8.

O extrato de um lote e' a prova de que o saldo nao e' um numero guardado: cada
linha traz `saldo_apos`, e a ultima tem de bater com o saldo do lote. Se um dia
existisse coluna `saldo`, este teste continuaria passando e o de `lote_lista`
tambem — o que os separa e' que aqui a conta e' refeita linha a linha.
"""

from typing import Any

import pytest
from fakes import MOVIMENTOS, SINAL, contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.lote_movimentos import Params, carregar, projetar
from estoque.domain.erros import ErroDominio


async def _vm(ator: Any, lote_id: str, **params: Any) -> Any:
    return projetar(await carregar(Params(lote_id=lote_id, **params), contexto(ator)))


# --- AC-2 · negativa indistinguivel, ADR-0014 ----------------------------


async def test_ac2_lote_de_outra_unidade_e_inexistente_sao_iguais(
    personas: dict[str, Any],
) -> None:
    def face(e: ErroDominio) -> tuple[str, str]:
        return (e.codigo, e.mensagem_publica)

    with pytest.raises(ErroDominio) as fora_de_escopo:
        await _vm(personas["odair"], "l-amox-mtz")
    with pytest.raises(ErroDominio) as inexistente:
        await _vm(personas["odair"], "l-nao-existe-mesmo")

    assert face(fora_de_escopo.value) == face(inexistente.value)
    assert fora_de_escopo.value.codigo == "nao_encontrado"


# --- AC-3 · saldo e' soma de movimento, RN-M06 ---------------------------


async def test_ac3_saldo_apos_e_cumulativo_e_fecha_no_saldo_atual(
    personas: dict[str, Any],
) -> None:
    """A conta refeita do zero, linha a linha.

    O extrato vem do mais RECENTE para o mais antigo — e' assim que se le um
    extrato —, entao a conta cumulativa percorre ao contrario. `saldo_apos` e'
    o saldo depois daquele movimento, e o do topo tem de ser o saldo atual.
    """
    vm = await _vm(personas["ivo"], "l-amox-mtz")
    acumulado = 0
    for linha in reversed(vm.linhas):
        acumulado += SINAL[linha.tipo] * linha.quantidade
        assert linha.saldo_apos == acumulado, linha.movimento_id
    assert vm.saldo_atual == acumulado


async def test_ac3_quantidade_e_sempre_positiva_o_sinal_vem_do_tipo(
    personas: dict[str, Any],
) -> None:
    """Guardar quantidade negativa faria o estorno de uma saida virar +10 e um
    bug de sinal em movimento imutavel (RN-M02) nao teria conserto: so' restaria
    outro estorno explicando o erro."""
    vm = await _vm(personas["ivo"], "l-amox-mtz")
    assert vm.linhas
    assert all(linha.quantidade > 0 for linha in vm.linhas)


async def test_ac3_o_extrato_bate_com_os_movimentos_do_fixture(
    personas: dict[str, Any],
) -> None:
    vm = await _vm(personas["ivo"], "l-amox-mtz")
    # Mais recente primeiro: e' a ordem de leitura de um extrato.
    esperados = [m.id for m in MOVIMENTOS if m.lote_id == "l-amox-mtz"][::-1]
    assert [linha.movimento_id for linha in vm.linhas] == esperados


# --- AC-4 · enum fechado, risco R-5 --------------------------------------


def test_ac4_periodo_fora_do_enum_e_rejeitado() -> None:
    # Dicionario, nao kwarg tipado: e' a forma como o param chega do modelo.
    with pytest.raises(ValidationError):
        Params.model_validate({"lote_id": "l-amox-mtz", "periodo": "45"})


def test_ac4_periodo_nao_aceita_data_livre() -> None:
    """`de`/`ate` como data solta convidam o modelo a inventar recorte."""
    assert "de" not in Params.model_fields
    assert "ate" not in Params.model_fields


def test_ac4_o_padrao_nao_recorta() -> None:
    """Padrao que recorta esconde movimento sem ninguem ter pedido — e num
    extrato regulatorio, o que some nao levanta suspeita."""
    assert Params(lote_id="l-amox-mtz").periodo == "tudo"


# --- AC-6 · custo invisivel, CA-05 --------------------------------------


async def test_ac6_custo_nao_atravessa_nem_para_quem_pode(personas: dict[str, Any]) -> None:
    assert "custo.ler" in personas["marco"].permissoes
    bruto = (await _vm(personas["marco"], "l-amox-mtz")).model_dump_json()
    assert "custo" not in bruto
    assert "1250" not in bruto


# --- a dupla identificacao aparece inteira, RN-C01 -----------------------


async def test_os_dois_ids_do_controlado_vem_na_mesma_linha(
    personas: dict[str, Any],
) -> None:
    """Autor e autorizador separados em telas diferentes tornam impossivel
    provar, numa auditoria, que houve duas pessoas."""
    vm = await _vm(personas["marco"], "l-rital-bloq")
    linha = vm.linhas[0]
    assert linha.autor_id == "u-cleide"
    assert linha.autorizador_id == "u-helena"
    assert linha.autor_id != linha.autorizador_id


# --- AC-8 · `select` e' puro --------------------------------------------


async def test_ac8_select_chamado_duas_vezes_da_o_mesmo(personas: dict[str, Any]) -> None:
    dados = await carregar(Params(lote_id="l-amox-mtz"), contexto(personas["ivo"]))
    assert projetar(dados) == projetar(dados)
