"""T-055 — `filtros` no contrato exportado.

O que vale aqui é o negativo: identificador não pode vazar pra dentro da barra
de filtro (seria reabrir o risco R-5 pela porta dos fundos), e só os oito
componentes do escopo desta tarefa ganham o campo.
"""

from typing import Any

from estoque.application.registry.exportar import _COM_FILTRO, contrato
from estoque.application.registry.registry import todos


def _por_id() -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in contrato()["componentes"]}


def test_so_os_oito_do_escopo_tem_filtros() -> None:
    comps = _por_id()
    com_filtro = {c_id for c_id, c in comps.items() if "filtros" in c}
    assert com_filtro == _COM_FILTRO


def test_todos_os_vinte_e_quatro_estao_no_contrato() -> None:
    """(sanidade) Se este número mudar, os dois testes acima podem estar
    passando por o conjunto todo ter encolhido, não por filtro certo."""
    assert len(_por_id()) == len(todos())


def test_identificador_nunca_aparece_como_filtro() -> None:
    """(negativo) `lote_id`, `produto_id`, `recebimento_id`, `movimento_id`,
    `ean` — nenhum tem enum, e nenhum pode aparecer aqui, em componente
    nenhum. Se aparecer, alguém deu enum a um identificador sem querer."""
    identificadores = {"lote_id", "produto_id", "recebimento_id", "movimento_id", "ean"}
    for comp_id, comp in _por_id().items():
        filtros: dict[str, list[str]] = comp.get("filtros", {})
        assert not (set(filtros) & identificadores), comp_id


def test_relatorio_movimentacao_nao_expoe_agrupar_por() -> None:
    """(negativo) `agrupar_por` é o eixo que a composição já fixou — não é
    filtro que o usuário reabre na barra."""
    filtros: dict[str, list[str]] = _por_id()["relatorio_movimentacao"]["filtros"]
    assert "agrupar_por" not in filtros


def test_valores_do_enum_batem_com_o_dominio() -> None:
    filtros: dict[str, list[str]] = _por_id()["lote_lista"]["filtros"]
    assert set(filtros["status"]) == {
        "quarentena",
        "liberado",
        "bloqueado",
        "descartado",
        "vencido",
        "esgotado",
    }
