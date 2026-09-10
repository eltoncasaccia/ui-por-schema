"""T-023 · `temperatura_excursoes` — AC-3, AC-4, AC-5, AC-6.

O AC-4 e' o criterio que da' valor regulatorio: o lote so' aparece vinculado se
estava na unidade quando a temperatura saiu da faixa. `l-vac-ref-tardio` entrou
DEPOIS da excursao (fixture, `m-13`) e por isso NAO deve aparecer — vincular todo
lote da camara produziria uma lista inflada e inutil na inspecao.
"""

from datetime import date
from typing import Any

import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.temperatura_excursoes import (
    Params,
    carregar,
    projetar,
)
from estoque.domain.erros import ErroDominio

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")


async def _vm(ator: Any, **over: Any) -> Any:
    p = {"unidade_id": "cd-refrigerado", **over}
    return projetar(await carregar(Params.model_validate(p), contexto(ator)))


# --- AC-5 · escopo por nao_encontrado, negativo (CA-06, ADR-0014) -----------


async def test_ac5_unidade_fora_do_escopo_e_nao_encontrado(personas: dict[str, Any]) -> None:
    with pytest.raises(ErroDominio) as capturado:
        await _vm(personas["odair"])
    assert capturado.value.codigo == "nao_encontrado"


async def test_ac5_quem_alcanca_a_unidade_ve_as_excursoes(personas: dict[str, Any]) -> None:
    vm = await _vm(personas["ivo"])
    assert vm.unidade == "CD Refrigerado"


# --- AC-6 · periodo, negativo -------------------------------------------


def test_ac6_de_posterior_a_ate_e_recusado() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate(
            {"unidade_id": "cd-refrigerado", "de": date(2026, 9, 30), "ate": date(2026, 9, 1)}
        )


def test_ac6_de_sem_ate_e_recusado() -> None:
    """Recorte pela metade alarga a resposta em silencio (risco R-5)."""
    with pytest.raises(ValidationError):
        Params.model_validate({"unidade_id": "cd-refrigerado", "de": date(2026, 1, 1)})


def test_ac6_sem_de_nem_ate_e_valido() -> None:
    Params.model_validate({"unidade_id": "cd-refrigerado"})


# --- AC-3 · toda excursao das fixtures aparece (RN-F04) -------------------


async def test_ac3_a_excursao_do_fixture_aparece(personas: dict[str, Any]) -> None:
    """A serie `TEMPERATURAS` tem UMA excursao de calor (duas leituras a 9,8 °C)."""
    vm = await _vm(personas["marco"])
    assert vm.total_excursoes == 1
    ex = vm.excursoes[0]
    assert ex.sentido == "calor"
    assert ex.pico_celsius == pytest.approx(9.8)
    assert ex.leituras == 2
    assert ex.inicio < ex.fim
    assert ex.duracao_horas == pytest.approx(6.0)


# --- AC-4 · o vinculo e' preciso, negativo ------------------------------


async def test_ac4_lotes_presentes_no_periodo_aparecem_vinculados(
    personas: dict[str, Any],
) -> None:
    vm = await _vm(personas["marco"])
    presentes = {lote.lote_id for lote in vm.excursoes[0].lotes}
    # Os dois lotes de `cd-refrigerado` que entraram ANTES da excursao.
    assert "l-vac-quar" in presentes
    assert "l-vac-quar-venc" in presentes


async def test_ac4_lote_que_entrou_depois_nao_aparece(personas: dict[str, Any]) -> None:
    """`l-vac-ref-tardio` entrou em `cd-refrigerado` hoje — depois da excursao.
    Nao estava exposto, e nao pode constar da ocorrencia."""
    vm = await _vm(personas["marco"])
    presentes = {lote.lote_id for lote in vm.excursoes[0].lotes}
    assert "l-vac-ref-tardio" not in presentes


async def test_ac4_os_lotes_vem_ordenados_pela_entrada(personas: dict[str, Any]) -> None:
    lotes = (await _vm(personas["marco"])).excursoes[0].lotes
    assert [lote.entrou_em for lote in lotes] == sorted(lote.entrou_em for lote in lotes)


# --- escopo de unidade no vinculo de lotes -----------------------------


async def test_lotes_vinculados_respeitam_o_escopo(personas: dict[str, Any]) -> None:
    """Helena alcanca tudo; a lista de lotes da excursao e' identica a de Marco.
    O que prova o escopo e' o AC-5 acima — aqui so' garantimos que o vinculo nao
    vaza lote de outra unidade (o `listar` ja' recebe `unidade_id`)."""
    de_marco = {lote.lote_id for lote in (await _vm(personas["marco"])).excursoes[0].lotes}
    de_helena = {lote.lote_id for lote in (await _vm(personas["helena"])).excursoes[0].lotes}
    assert de_marco == de_helena
    assert all(lote.startswith("l-vac") for lote in de_marco)


# --- `select` puro e custo invisivel ---------------------------------


async def test_select_chamado_duas_vezes_da_o_mesmo(personas: dict[str, Any]) -> None:
    ctx = contexto(personas["marco"])
    dados = await carregar(Params.model_validate({"unidade_id": "cd-refrigerado"}), ctx)
    assert projetar(dados) == projetar(dados)


async def test_nenhum_custo_no_viewmodel(personas: dict[str, Any]) -> None:
    bruto = (await _vm(personas["marco"])).model_dump_json()
    assert "custo" not in bruto
    assert "centavos" not in bruto


# --- catalogo por ator (ADR-0003) ----------------------------------


def test_temperatura_excursoes_segue_temperatura_ler(personas: dict[str, Any]) -> None:
    from estoque.application.registry.registry import ids_permitidos

    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "temperatura.ler" in ator.permissoes
        assert ("temperatura_excursoes" in ids_permitidos(ator)) is esperado, nome
    assert "temperatura_excursoes" not in ids_permitidos(personas["rafael"])
