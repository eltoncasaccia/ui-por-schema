"""T-019 · `produto_saldo_por_unidade` — escopo, custo invisivel, pureza.

Componente de `lote.ler`: nao toca custo por definicao. O teste que vale e' o de
escopo — Odair ve so' a unidade dele, sem param de unidade para contornar a
intersecao da porta (RN-A01).
"""

from typing import Any

import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.produto_saldo_por_unidade import (
    Params,
    carregar,
    projetar,
)
from estoque.domain.erros import ErroDominio


async def _vm(ator: Any, produto_id: str = "p-amox") -> Any:
    return projetar(await carregar(Params(produto_id=produto_id), contexto(ator)))


async def test_soma_por_unidade_e_total(personas: dict[str, Any]) -> None:
    """Ivo alcanca CD Matriz e CD Refrigerado. p-amox no fixture tem tres lotes
    em CD Matriz: `l-amox-mtz` (saldo 500), `l-amox-venc` (80) e `l-amox-zero`
    (entrou e saiu tudo, saldo 0)."""
    vm = await _vm(personas["ivo"])
    por_unidade = {linha.unidade_id: linha for linha in vm.linhas}
    assert "cd-matriz" in por_unidade
    assert vm.total == sum(linha.saldo for linha in vm.linhas)
    assert por_unidade["cd-matriz"].saldo == 580
    # `l-amox-zero` zerou: dois lotes com saldo, nao tres.
    assert por_unidade["cd-matriz"].lotes == 2


async def test_escopo_odair_nao_ve_cd_matriz(personas: dict[str, Any]) -> None:
    """O teste negativo. p-amox tem lote em CD Matriz e em Uberlandia; Odair
    (so' Uberlandia) recebe apenas a linha da unidade dele."""
    vm = await _vm(personas["odair"])
    unidades = {linha.unidade_id for linha in vm.linhas}
    assert unidades == {"filial-uberlandia"}
    assert "cd-matriz" not in unidades


async def test_linhas_ordenadas_por_unidade(personas: dict[str, Any]) -> None:
    vm = await _vm(personas["marco"], produto_id="p-vac")
    ids = [linha.unidade_id for linha in vm.linhas]
    assert ids == sorted(ids)


async def test_custo_nao_atravessa_nem_para_quem_pode(personas: dict[str, Any]) -> None:
    bruto = (await _vm(personas["marco"])).model_dump_json()
    assert "custo" not in bruto
    assert "1250" not in bruto


async def test_select_e_puro(personas: dict[str, Any]) -> None:
    dados = await carregar(Params(produto_id="p-amox"), contexto(personas["ivo"]))
    assert projetar(dados) == projetar(dados)


def test_produto_id_e_obrigatorio() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate({})


async def test_produto_inexistente_e_nao_encontrado(personas: dict[str, Any]) -> None:
    with pytest.raises(ErroDominio) as capturado:
        await _vm(personas["ivo"], produto_id="p-nao-existe")
    assert capturado.value.codigo == "nao_encontrado"
