"""Regressao dos dois bugs achados em teste ponta a ponta.

Os dois passavam em toda a suite unitaria e so' apareceram com o sistema no ar.
Ambos violavam ADRs deste proprio projeto — o que e' o argumento a favor de
rodar o sistema cedo, e nao so' os testes.
"""

import pytest

from estoque.autorizacao.motor import (
    autorizar_params_ou_falhar,
    autorizar_unidade_do_param,
)
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator
from estoque.registry.registry import buscar, valores_proibidos


# --- BUG 1 · CS-01: schema forjado direto no endpoint -----------------------
def test_valor_de_enum_proibido_e_recusado_no_endpoint(personas: dict[str, Ator]) -> None:
    """O endpoint conferia so' a permissao BASE (`lote.ler`). Cleide passava e o
    `load` rodava com `metrica=valor_em_estoque`.

    O dano foi contido por acaso — a porta de dados ja' removia o custo, entao o
    total voltou zerado. Defesa em profundidade que salva por acidente e' uma
    camada que falhou."""
    comp = buscar("estoque_indicador")
    assert comp is not None
    proibidos = valores_proibidos(comp, personas["cleide"])
    with pytest.raises(ErroDominio) as e:
        autorizar_params_ou_falhar(proibidos, {"metrica": "valor_em_estoque"})
    assert e.value.codigo == "nao_autorizado"


def test_quem_pode_passa(personas: dict[str, Ator]) -> None:
    comp = buscar("estoque_indicador")
    assert comp is not None
    autorizar_params_ou_falhar(
        valores_proibidos(comp, personas["rafael"]), {"metrica": "valor_em_estoque"}
    )


def test_metrica_permitida_passa_para_todos(personas: dict[str, Ator]) -> None:
    comp = buscar("estoque_indicador")
    assert comp is not None
    for ator in personas.values():
        autorizar_params_ou_falhar(
            valores_proibidos(comp, ator), {"metrica": "lotes_em_quarentena"}
        )


# --- BUG 2 · ADR-0014: escopo declarado nega, nao devolve vazio --------------
def test_unidade_fora_do_escopo_nega_explicitamente(personas: dict[str, Ator]) -> None:
    """Odair pedindo a Matriz recebia lista VAZIA, porque o repositorio apenas
    intersectava com o escopo. Vazio ensina um fato falso — que a Matriz nao tem
    nada vencendo — e o ADR-0014 rejeita isso: a unidade existe e ele sabe."""
    with pytest.raises(ErroDominio) as e:
        autorizar_unidade_do_param(personas["odair"], "cd-matriz")
    assert e.value.codigo == "nao_autorizado"
    assert "cd-matriz" in e.value.mensagem_publica


def test_unidade_propria_passa(personas: dict[str, Ator]) -> None:
    autorizar_unidade_do_param(personas["odair"], "filial-uberlandia")


def test_sem_unidade_no_param_nao_nega(personas: dict[str, Ator]) -> None:
    """Sem `unidade_id`, a consulta e' sobre TODAS as unidades do ator — o
    escopo do repositorio resolve, e negar aqui seria errado."""
    autorizar_unidade_do_param(personas["odair"], None)


def test_ator_inativo_nao_acessa_nenhuma_unidade(personas: dict[str, Ator]) -> None:
    from dataclasses import replace

    inativo = replace(personas["odair"], ativo=False)
    with pytest.raises(ErroDominio):
        autorizar_unidade_do_param(inativo, "filial-uberlandia")
