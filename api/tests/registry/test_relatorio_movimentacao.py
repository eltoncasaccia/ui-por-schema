"""T-044 — `relatorio_movimentacao`. AC-1 a AC-9."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import fakes
import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.relatorio_movimentacao import (
    COMPONENTE,
    TETO_DE_LEITURA,
    VM,
    Params,
    carregar,
    projetar,
)
from estoque.application.registry.registry import catalogo_de
from estoque.data.repositorios import LIMITE_MOVIMENTOS
from estoque.domain.identidade import Ator

EIXOS = ("unidade", "produto", "motivo", "mes", "classe")


async def vm_de(
    ator: Ator, limite: int = 20, cursor: str | None = None, **params: object
) -> VM:
    ctx = contexto(ator, limite=limite, cursor=cursor)
    return projetar(await carregar(Params.model_validate(params), ctx))


# ---------------------------------------------------------------- AC-1
@pytest.mark.parametrize(
    "bruto",
    [
        {"agrupar_por": "fornecedor"},
        {"agrupar_por": "produto", "metrica": "margem"},
        {"agrupar_por": "produto", "periodo": "45"},
        {},
    ],
)
def test_ac1_eixo_metrica_e_periodo_fora_do_enum_sao_recusados(
    bruto: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        Params.model_validate(bruto)


# ---------------------------------------------------------------- AC-2
def _metricas(ator: Ator) -> list[str] | None:
    entrada = next((c for c in catalogo_de(ator) if c["id"] == "relatorio_movimentacao"), None)
    return None if entrada is None else list(entrada["params"]["metrica"]["valores"])


@pytest.mark.parametrize("nome", ["cleide", "helena", "ivo", "odair"])
def test_ac2_valor_some_do_enum_de_quem_nao_tem_custo(
    nome: str, personas: dict[str, Ator]
) -> None:
    assert _metricas(personas[nome]) == ["quantidade", "movimentos"]


@pytest.mark.parametrize("nome", ["marco", "sandra"])
def test_ac2_valor_aparece_para_quem_tem_custo(nome: str, personas: dict[str, Ator]) -> None:
    assert _metricas(personas[nome]) == ["quantidade", "movimentos", "valor"]


def test_ac2_rafael_tem_custo_mas_nao_movimento_ler(personas: dict[str, Ator]) -> None:
    """A tarefa listava Rafael entre os que veem `valor`. O `requires` base vence:
    sem `movimento.ler`, o componente inteiro sai do catalogo dele."""
    assert _metricas(personas["rafael"]) is None


# ---------------------------------------------------------------- AC-3
@pytest.mark.parametrize("eixo", EIXOS)
async def test_ac3_sem_metrica_valor_nao_ha_custo_nem_para_marco(
    eixo: str, personas: dict[str, Ator]
) -> None:
    for metrica in ("quantidade", "movimentos"):
        vm = await vm_de(personas["marco"], agrupar_por=eixo, metrica=metrica, periodo="365")
        bruto = vm.model_dump_json()
        assert vm.unidade_medida != "centavos"
        assert "centavos" not in bruto
        for custo in ("1250", "4800", "3300"):
            assert custo not in bruto


async def test_ac3_contraponto_valor_para_quem_pode(personas: dict[str, Ator]) -> None:
    """amox 1140 x 1250 + vac 640 x 4800 + rital 40 x 3300."""
    vm = await vm_de(personas["marco"], agrupar_por="produto", metrica="valor", periodo="365")
    assert vm.unidade_medida == "centavos"
    assert vm.total == 1140 * 1250 + 640 * 4800 + 40 * 3300


# ---------------------------------------------------------------- AC-4
async def test_ac4_odair_so_ve_uberlandia(personas: dict[str, Ator]) -> None:
    vm = await vm_de(personas["odair"], agrupar_por="unidade", periodo="365")
    assert [x.chave for x in vm.linhas] == ["filial-uberlandia"]


async def test_ac4_odair_pedindo_a_matriz_recebe_nada(personas: dict[str, Ator]) -> None:
    vm = await vm_de(
        personas["odair"], agrupar_por="unidade", periodo="365", unidade_id="cd-matriz"
    )
    assert vm.linhas == []
    assert vm.total == 0


# ---------------------------------------------------------------- AC-5
async def test_ac5_a_soma_fecha_pelos_cinco_eixos(personas: dict[str, Ator]) -> None:
    totais = set()
    for eixo in EIXOS:
        vm = await vm_de(personas["marco"], agrupar_por=eixo, periodo="365")
        assert not vm.tem_mais
        assert sum(x.numero for x in vm.linhas) == vm.total
        totais.add(vm.total)
    # 12 efetivados; m-11 esta' pendente e nao conta (RN-M06)
    assert totais == {1820}


# ---------------------------------------------------------------- AC-6
async def test_ac6_select_puro(personas: dict[str, Ator]) -> None:
    dados = await carregar(
        Params.model_validate({"agrupar_por": "mes", "periodo": "365"}),
        contexto(personas["marco"]),
    )
    assert projetar(dados) == projetar(dados)


# ---------------------------------------------------------------- AC-7
async def test_ac7_relatorio_vazio_e_valido(personas: dict[str, Ator]) -> None:
    vm = await vm_de(personas["marco"], agrupar_por="motivo", tipo="descarte", periodo="365")
    assert vm.total == 0
    assert vm.linhas == []
    assert not vm.truncado


# ---------------------------------------------------------------- AC-8
def test_ac8_a_prosa_nao_cita_a_metrica_filtrada() -> None:
    prosa = " ".join((COMPONENTE.description, *COMPONENTE.examples)).lower()
    assert "valor" not in prosa


# ---------------------------------------------------------------- AC-9
def test_ac9_o_teto_do_componente_e_o_do_adaptador() -> None:
    assert TETO_DE_LEITURA == LIMITE_MOVIMENTOS


async def test_ac9_leitura_cortada_e_declarada(
    personas: dict[str, Ator], monkeypatch: pytest.MonkeyPatch
) -> None:
    recente = datetime.now(UTC) - timedelta(hours=1)
    excesso = [
        replace(fakes.MOVIMENTOS[0], id=f"m-t044-{i}", criado_em=recente)
        for i in range(LIMITE_MOVIMENTOS + 1)
    ]
    monkeypatch.setattr(fakes, "MOVIMENTOS", [*fakes.MOVIMENTOS, *excesso])
    vm = await vm_de(personas["marco"], agrupar_por="unidade", periodo="30")
    assert vm.truncado
    assert "amostra" in vm.recorte


async def test_ac9_contraponto_leitura_inteira_nao_se_diz_cortada(
    personas: dict[str, Ator],
) -> None:
    vm = await vm_de(personas["marco"], agrupar_por="unidade", periodo="365")
    assert not vm.truncado
    assert "amostra" not in vm.recorte


# ------------------------------------------------------------ paginacao
async def test_pagina_sem_repetir_grupo(personas: dict[str, Ator]) -> None:
    p1 = await vm_de(personas["marco"], limite=2, agrupar_por="mes", periodo="365")
    assert p1.tem_mais
    assert p1.cursor is not None
    p2 = await vm_de(
        personas["marco"], limite=50, cursor=p1.cursor, agrupar_por="mes", periodo="365"
    )
    chaves = [x.chave for x in p1.linhas] + [x.chave for x in p2.linhas]
    assert len(chaves) == len(set(chaves)) == p1.grupos
