"""T-022 · `recebimento_lista` — AC-2, AC-5, AC-6, AC-7.

O AC-5 e' o que vale: **como Odair, so' os recebimentos de Uberlandia**, e nao
por filtro do componente — a porta ja' intersectou o escopo (RN-A01). O param
`unidade_id` nao contorna a intersecao.

O AC-1 ("todo recebimento listado gerou lote em quarentena") NAO e' verificavel
aqui: `lote.recebimento_id` nunca teve schema (descopado pela T-047, achado
A-32), entao nao ha' vinculo recebimento -> lote para asseverar. Fica em branco
no arquivo da tarefa, com a razao registrada.
"""

from typing import Any

import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.recebimento_lista import (
    VM,
    Params,
    carregar,
    projetar,
)
from estoque.application.registry.registry import ids_permitidos

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")


async def vm_de(ator: Any, **params: object) -> VM:
    return projetar(await carregar(Params.model_validate(params), contexto(ator)))


def ids(vm: VM) -> set[str]:
    return {linha.recebimento_id for linha in vm.linhas}


# --- AC-5 · escopo de unidade, negativo (CA-06) -------------------------------


async def test_ac5_odair_so_ve_recebimento_de_uberlandia(personas: dict[str, Any]) -> None:
    vm = await vm_de(personas["odair"], periodo="tudo")
    assert ids(vm) == {"r-uber"}
    assert all(linha.unidade == "Uberlândia" for linha in vm.linhas)


async def test_ac5_param_de_unidade_nao_contorna_a_intersecao(
    personas: dict[str, Any],
) -> None:
    """Odair PEDE `cd-matriz` — a unidade existe e tem recebimentos. A resposta
    e' vazia: a porta intersectou antes de o componente filtrar."""
    vm = await vm_de(personas["odair"], unidade_id="cd-matriz", periodo="tudo")
    assert vm.linhas == []
    assert vm.total == 0


async def test_ac5_quem_alcanca_a_matriz_ve_os_recebimentos_de_la(
    personas: dict[str, Any],
) -> None:
    """O contraponto: se ninguem visse nada, os testes acima passariam a toa."""
    vm = await vm_de(personas["ivo"], unidade_id="cd-matriz", periodo="tudo")
    assert "r-normal-mtz" in ids(vm)
    assert "r-uber" not in ids(vm)  # Ivo nao alcanca Uberlandia


# --- AC-6 · `status` e' enum fechado, negativo (risco R-5) -------------------


def test_ac6_status_invalido_e_recusado_na_validacao() -> None:
    """Chega como o modelo manda: dicionario vindo do JSON. `parcial` nao e'
    valor do enum — a recusa acontece antes do `load`."""
    with pytest.raises(ValidationError):
        Params.model_validate({"status": "parcial"})


def test_ac6_periodo_invalido_tambem_e_recusado() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate({"periodo": "365d"})


async def test_ac6_status_valido_filtra(personas: dict[str, Any]) -> None:
    vm = await vm_de(personas["marco"], status="rascunho", periodo="tudo")
    assert {linha.status for linha in vm.linhas} == {"rascunho"}
    assert "r-uber" in ids(vm)  # o unico rascunho das fixtures


# --- AC-2 · divergencia visivel na lista, nao bloqueia (RN-R04) -------------


async def test_ac2_divergencia_aparece_na_linha_e_no_contador(
    personas: dict[str, Any],
) -> None:
    vm = await vm_de(personas["marco"], periodo="tudo")
    linha = next(x for x in vm.linhas if x.recebimento_id == "r-diverg-mtz")
    assert linha.divergencia is True
    # O contador do cabecalho conta a mesma coisa.
    assert vm.com_divergencia == sum(1 for x in vm.linhas if x.divergencia)
    assert vm.com_divergencia >= 1


async def test_ac2_recebimento_com_divergencia_ainda_conclui(
    personas: dict[str, Any],
) -> None:
    """A pendencia nao trava o fluxo: `r-diverg-mtz` esta' `conferido`, nao
    preso num estado de erro."""
    vm = await vm_de(personas["marco"], periodo="tudo")
    linha = next(x for x in vm.linhas if x.recebimento_id == "r-diverg-mtz")
    assert linha.status == "conferido"


# --- AC-7 · nenhum custo exposto (CA-05) ------------------------------------


async def test_ac7_custo_nao_atravessa_nem_para_quem_pode(personas: dict[str, Any]) -> None:
    assert "custo.ler" in personas["marco"].permissoes
    bruto = (await vm_de(personas["marco"], periodo="tudo")).model_dump_json()
    assert "custo" not in bruto
    assert "centavos" not in bruto


# --- `select` puro ---------------------------------------------------------


async def test_select_chamado_duas_vezes_da_o_mesmo(personas: dict[str, Any]) -> None:
    ctx = contexto(personas["marco"])
    dados = await carregar(Params.model_validate({"periodo": "tudo"}), ctx)
    assert projetar(dados) == projetar(dados)


# --- catalogo por ator (ADR-0003) ----------------------------------------


def test_recebimento_lista_segue_recebimento_ler(personas: dict[str, Any]) -> None:
    """Rafael (comprador) e' o contraexemplo: tem `lote.ler`, nao tem
    `recebimento.ler`. O que entrou no CD nao lhe diz respeito."""
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "recebimento.ler" in ator.permissoes
        assert ("recebimento_lista" in ids_permitidos(ator)) is esperado, nome
    assert "recebimento_lista" not in ids_permitidos(personas["rafael"])
