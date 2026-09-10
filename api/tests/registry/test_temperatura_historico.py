"""T-023 · `temperatura_historico` — AC-1, AC-2, AC-5, AC-6.

O AC-1 (agregacao no periodo longo) e o AC-2 (exportacao com os mesmos dados da
tela) sao os que dao valor regulatorio ao componente. O AC-5 e' a negativa de
`CA-06`: temperatura de uma unidade fora do escopo e' `nao_encontrado`, nao serie
vazia.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.temperatura_historico import (
    LIMITE_PONTOS,
    Dados,
    Params,
    carregar,
    projetar,
)
from estoque.domain.erros import ErroDominio
from estoque.domain.tipos import RegistroTemperatura

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")

# O fixture de temperatura (T-047) vive todo em `cd-refrigerado`, na ultima
# semana antes de `fakes.AGORA` (2026-09-01). Esta janela cobre com folga.
DE = date(2026, 8, 1)
ATE = date(2026, 9, 30)


async def _vm(ator: Any, **over: Any) -> Any:
    p = {"unidade_id": "cd-refrigerado", "de": DE, "ate": ATE, **over}
    return projetar(await carregar(Params.model_validate(p), contexto(ator)))


# --- AC-5 · escopo por nao_encontrado, negativo (CA-06, ADR-0014) -----------


async def test_ac5_unidade_fora_do_escopo_e_nao_encontrado(personas: dict[str, Any]) -> None:
    """Odair alcanca so' Uberlandia. Pedir `cd-refrigerado` responde igual a uma
    unidade que nao existe."""
    with pytest.raises(ErroDominio) as capturado:
        await _vm(personas["odair"])
    assert capturado.value.codigo == "nao_encontrado"


async def test_ac5_o_id_pedido_nao_vaza_na_resposta(personas: dict[str, Any]) -> None:
    with pytest.raises(ErroDominio) as capturado:
        await _vm(personas["odair"])
    erro = capturado.value
    assert erro.detalhe_interno is not None
    for face in (erro.mensagem_publica, repr(erro), str(erro)):
        assert "cd-refrigerado" not in face
        assert "u-odair" not in face


async def test_ac5_quem_alcanca_a_unidade_ve_a_serie(personas: dict[str, Any]) -> None:
    """O contraponto: Ivo alcanca `cd-refrigerado`."""
    vm = await _vm(personas["ivo"])
    assert vm.unidade == "CD Refrigerado"
    assert vm.total_leituras > 0


# --- AC-6 · periodo invertido rejeitado, negativo --------------------------


def test_ac6_de_posterior_a_ate_e_recusado_na_validacao() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate(
            {"unidade_id": "cd-refrigerado", "de": date(2026, 9, 30), "ate": date(2026, 9, 1)}
        )


def test_ac6_periodo_de_um_dia_e_valido() -> None:
    Params.model_validate(
        {"unidade_id": "cd-refrigerado", "de": date(2026, 9, 1), "ate": date(2026, 9, 1)}
    )


# --- AC-1 · agregacao no periodo longo (RNF-06) ---------------------------


def _serie_longa() -> Dados:
    """5 anos de leitura de 6 em 6 horas — ~7.300 pontos. Uma excursao de calor
    plantada no meio, para provar que a agregacao nao a apaga."""
    inicio = datetime(2021, 1, 1, tzinfo=UTC)
    leituras: list[RegistroTemperatura] = []
    for i in range(7300):
        instante = inicio + timedelta(hours=6 * i)
        celsius = 12.0 if 3650 <= i <= 3652 else 5.0
        leituras.append(
            RegistroTemperatura(
                id=f"t{i:05d}", unidade_id="cd-refrigerado", medido_em=instante, celsius=celsius
            )
        )
    return Dados(
        unidade="CD Refrigerado",
        de=date(2021, 1, 1),
        ate=date(2025, 12, 31),
        leituras=leituras,
    )


def test_ac1_periodo_longo_vem_agregado_e_cabe_na_tela() -> None:
    vm = projetar(_serie_longa())
    assert vm.agregado is True
    assert vm.pontos == []
    assert 0 < len(vm.baldes) <= LIMITE_PONTOS
    assert vm.total_leituras == 7300


def test_ac1_a_agregacao_nao_apaga_a_excursao() -> None:
    vm = projetar(_serie_longa())
    assert vm.leituras_fora_da_faixa == 3
    assert any(b.tem_excursao for b in vm.baldes), "a excursao sumiu na agregacao"


async def test_ac1_periodo_curto_vem_ponto_a_ponto(personas: dict[str, Any]) -> None:
    """O outro lado: a serie do fixture cabe, entao nao agrega."""
    vm = await _vm(personas["ivo"])
    assert vm.agregado is False
    assert vm.baldes == []
    assert len(vm.pontos) == vm.total_leituras


# --- AC-2 · exportacao com os mesmos dados da tela (CA-07) -----------------


async def test_ac2_csv_tem_uma_linha_por_ponto_da_tela(personas: dict[str, Any]) -> None:
    vm = await _vm(personas["ivo"])
    linhas = vm.csv.splitlines()
    assert linhas[0] == "instante,celsius,fora_da_faixa"
    assert len(linhas) - 1 == len(vm.pontos)
    assert vm.exportavel is True
    # Os valores sao os MESMOS objetos da tela, nao uma segunda consulta.
    primeira = vm.pontos[0]
    assert linhas[1].startswith(primeira.instante.isoformat())
    assert str(primeira.celsius) in linhas[1]


def test_ac2_csv_do_periodo_longo_segue_os_baldes() -> None:
    vm = projetar(_serie_longa())
    linhas = vm.csv.splitlines()
    assert linhas[0] == "inicio,fim,minimo,maximo,media,leituras,tem_excursao"
    assert len(linhas) - 1 == len(vm.baldes)


# --- `select` puro e custo invisivel -------------------------------------


async def test_select_chamado_duas_vezes_da_o_mesmo(personas: dict[str, Any]) -> None:
    ctx = contexto(personas["ivo"])
    dados = await carregar(
        Params.model_validate({"unidade_id": "cd-refrigerado", "de": DE, "ate": ATE}), ctx
    )
    assert projetar(dados) == projetar(dados)


async def test_nenhum_custo_no_viewmodel(personas: dict[str, Any]) -> None:
    bruto = (await _vm(personas["marco"])).model_dump_json()
    assert "custo" not in bruto
    assert "centavos" not in bruto


# --- catalogo por ator (ADR-0003) --------------------------------------


def test_temperatura_historico_segue_temperatura_ler(personas: dict[str, Any]) -> None:
    from estoque.application.registry.registry import ids_permitidos

    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "temperatura.ler" in ator.permissoes
        assert ("temperatura_historico" in ids_permitidos(ator)) is esperado, nome
    assert "temperatura_historico" not in ids_permitidos(personas["rafael"])
