"""T-013 — a fronteira de seguranca, com entrada hostil.

Herdada da v1 e ampliada. Todos os casos abaixo devem ser REJEITADOS, e o
rejeitado deve aparecer no resultado com motivo — falha silenciosa e' pior que
falha ruidosa.
"""

from typing import Any

import pytest

from estoque.domain.identidade import Ator
from estoque.schema.validar import validar_schema


def bloco(tipo: str, **params: Any) -> dict[str, Any]:
    return {"versao": 1, "blocos": [{"tipo": tipo, "params": params}]}


# --- casos herdados da v1 ---------------------------------------------------
@pytest.mark.parametrize(
    ("bruto", "porque"),
    [
        (bloco("RandomReactComponent"), "componente inventado"),
        (bloco("<script>alert(1)</script>"), "markup como id"),
        (bloco("estoque_indicador", metrica="lucro_do_trimestre"), "valor fora do enum"),
        (bloco("fila_vencimento", janela="tudo"), "valor fora do enum"),
        (
            {"versao": 1, "blocos": [{"tipo": "fila_vencimento", "layout": "grid"}]},
            "campo desconhecido no bloco",
        ),
        (
            {"versao": 2, "blocos": [{"tipo": "fila_vencimento", "params": {}}]},
            "versao invalida",
        ),
        ({"versao": 1, "blocos": []}, "sem blocos"),
        (bloco("fila_vencimento", **{"__proto__": "x"}), "chave perigosa"),
        (bloco("fila_vencimento", **{"constructor": "x"}), "chave perigosa"),
        (
            {
                "versao": 1,
                "titulo": "x",
                "blocos": [{"tipo": "fila_vencimento", "params": {}}] * 50,
            },
            "blocos demais",
        ),
    ],
)
def test_entrada_hostil_e_rejeitada(bruto: Any, porque: str, personas: dict[str, Ator]) -> None:
    r = validar_schema(bruto, personas["marco"])
    assert r.schema is None, porque
    assert r.rejeitados, "rejeicao precisa aparecer no trace"


def test_schema_valido_passa(personas: dict[str, Ator]) -> None:
    r = validar_schema(bloco("fila_vencimento", janela="90"), personas["marco"])
    assert r.schema is not None
    assert r.aceitos == ["fila_vencimento"]
    assert not r.rejeitados


# --- CS-01: o caso que a v1 NAO tinha como testar ---------------------------
def test_componente_registrado_mas_fora_do_catalogo_do_ator(
    personas: dict[str, Ator],
) -> None:
    """O furo de permissao que passaria em todos os outros testes.

    A v1 validava contra o registry GLOBAL. Aqui a validacao e' contra o
    catalogo DESTE ator — schema forjado com componente que ele nao pode usar
    e' rejeitado, mesmo o componente existindo.
    """
    from dataclasses import replace

    sem_lote = replace(personas["cleide"], permissoes=frozenset({"produto.ler"}))
    r = validar_schema(bloco("fila_vencimento", janela="90"), sem_lote)
    assert r.schema is None
    assert r.rejeitados[0].motivo == "componente fora do catalogo do ator"


def test_valor_de_enum_proibido_para_o_ator(personas: dict[str, Ator]) -> None:
    """Cleide montando o schema A MAO com a metrica de custo, sem passar pelo
    modelo. Achado A-05 + CS-01: o schema e' payload nao-confiavel."""
    r = validar_schema(
        bloco("estoque_indicador", metrica="valor_em_estoque"), personas["cleide"]
    )
    assert r.schema is None
    assert "valor nao permitido" in r.rejeitados[0].motivo


def test_mesma_metrica_passa_para_quem_pode(personas: dict[str, Ator]) -> None:
    r = validar_schema(
        bloco("estoque_indicador", metrica="valor_em_estoque"), personas["rafael"]
    )
    assert r.schema is not None


def test_erro_nunca_ecoa_o_valor_hostil(personas: dict[str, Ator]) -> None:
    """O motivo da rejeicao vai para o trace, e o trace pode alimentar log.
    Ecoar o valor recebido devolveria conteudo hostil para dentro do sistema."""
    hostil = "<script>alert('xss')</script>"
    r = validar_schema(bloco("estoque_indicador", metrica=hostil), personas["marco"])
    assert r.schema is None
    assert all(hostil not in rej.motivo for rej in r.rejeitados)


def test_composicao_parcial_mantem_o_que_e_valido(personas: dict[str, Ator]) -> None:
    """Um bloco invalido nao derruba os validos — e o invalido fica no trace."""
    bruto = {
        "versao": 1,
        "blocos": [
            {"tipo": "fila_vencimento", "params": {"janela": "90"}},
            {"tipo": "componente_que_nao_existe", "params": {}},
        ],
    }
    r = validar_schema(bruto, personas["marco"])
    assert r.schema is not None
    assert r.aceitos == ["fila_vencimento"]
    assert r.rejeitados[0].tipo == "componente_que_nao_existe"
