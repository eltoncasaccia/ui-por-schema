"""T-018 · `quarentena_fila` — AC-1, AC-5, AC-6, AC-8.

`RN-R01`: tudo que entra passa por quarentena, e nao ha entrada direta em
estoque vendavel. Esta fila e' portanto a lista do que ja' foi pago e ainda nao
pode ser vendido — e o numero que dela importa nao e' o tamanho, e' quantos
venceram esperando.
"""

from typing import Any

from fakes import LOTES, contexto

from estoque.registry.componentes.quarentena_fila import Params, carregar, projetar


async def _vm(ator: Any, **params: Any) -> Any:
    return projetar(await carregar(Params(**params), contexto(ator)))


# --- AC-5 · so' quarentena, RN-R01 ---------------------------------------


async def test_ac5_a_fila_traz_apenas_lotes_em_quarentena(personas: dict[str, Any]) -> None:
    vm = await _vm(personas["marco"])
    assert vm.total > 0
    registrados = {lote.id: lote.status for lote in LOTES}
    assert all(registrados[linha.lote_id] == "quarentena" for linha in vm.linhas)


async def test_ac5_liberado_e_bloqueado_ficam_de_fora(personas: dict[str, Any]) -> None:
    """O contraponto negativo: a fila que traz tudo nao e' fila."""
    ids = {linha.lote_id for linha in (await _vm(personas["marco"])).linhas}
    assert "l-amox-mtz" not in ids, "liberado nao espera liberacao"
    assert "l-rital-bloq" not in ids, "bloqueado nao esta' aguardando o RT"


async def test_ac5_o_que_venceu_na_fila_continua_na_fila(personas: dict[str, Any]) -> None:
    """ADR-0022: o status EFETIVO de `l-vac-quar-venc` e' `vencido`, e o
    registrado ainda e' `quarentena`.

    Ele nao pode sumir da fila por ter vencido — some da fila e some do
    problema. E' a pior combinacao do sistema: pago, recebido, refrigerado, e
    nunca chegou a ser vendavel. Por isso aparece contado a' parte.
    """
    vm = await _vm(personas["marco"])
    ids = {linha.lote_id for linha in vm.linhas}
    assert "l-vac-quar-venc" in ids
    assert vm.vencidos >= 1
    venceu = next(linha for linha in vm.linhas if linha.lote_id == "l-vac-quar-venc")
    assert venceu.status_efetivo == "vencido"
    assert venceu.situacao == "vencido"


# --- AC-1 · escopo de unidade, CA-06 -------------------------------------


async def test_ac1_odair_nao_ve_a_quarentena_do_refrigerado(personas: dict[str, Any]) -> None:
    """Existe lote em quarentena no `cd-refrigerado`; Odair nao alcanca."""
    vm = await _vm(personas["odair"])
    assert {linha.unidade for linha in vm.linhas} == {"filial-uberlandia"}


async def test_ac1_pedir_outra_unidade_devolve_vazio(personas: dict[str, Any]) -> None:
    """O param nao contorna a intersecao — e o resultado e' vazio, nao erro:
    uma fila vazia nao diz se a unidade existe."""
    vm = await _vm(personas["odair"], unidade_id="cd-refrigerado")
    assert vm.total == 0
    assert vm.linhas == []


# --- AC-6 · custo invisivel, CA-05 --------------------------------------


async def test_ac6_custo_nao_atravessa_nem_para_quem_pode(personas: dict[str, Any]) -> None:
    """Vale mais aqui do que nos outros tres: uma fila de quarentena e'
    exatamente onde alguem pensaria em somar "quanto esta' parado em R$"."""
    assert "custo.ler" in personas["marco"].permissoes
    bruto = (await _vm(personas["marco"])).model_dump_json()
    assert "custo" not in bruto
    assert "4800" not in bruto


# --- AC-8 · `select` e' puro --------------------------------------------


async def test_ac8_select_chamado_duas_vezes_da_o_mesmo(personas: dict[str, Any]) -> None:
    dados = await carregar(Params(), contexto(personas["marco"]))
    assert projetar(dados) == projetar(dados)
