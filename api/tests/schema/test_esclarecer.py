"""Esclarecimento: pergunta vaga devolve ids candidatos, nunca texto livre.

O lado que vale e' o negativo: opcao fora do catalogo do ator nao chega a pessoa
— nem pela validacao no servidor, nem pelo schema restrito que o modelo recebe.
"""

from estoque.application.registry.registry import catalogo_de
from estoque.application.schema.validar import validar_schema
from estoque.assistant.adapter import json_schema_do_catalogo
from estoque.domain.identidade import Ator


def _vaga(*opcoes: str) -> dict[str, object]:
    return {"versao": 1, "blocos": [], "esclarecer": list(opcoes)}


def test_opcoes_do_catalogo_chegam_na_ordem(personas: dict[str, Ator]) -> None:
    r = validar_schema(_vaga("recebimento_registrar", "movimento_saida"), personas["ivo"])
    assert r.schema is not None
    assert r.schema.esclarecer == ("recebimento_registrar", "movimento_saida")
    assert r.rejeitados == []


def test_opcao_fora_do_catalogo_do_ator_e_descartada(personas: dict[str, Ator]) -> None:
    # `quarentena_liberar` e' privativo do RT (RN-R02): Ivo nao ve nem a opcao.
    r = validar_schema(_vaga("quarentena_liberar", "recebimento_registrar"), personas["ivo"])
    assert r.schema is not None
    assert r.schema.esclarecer == ("recebimento_registrar",)
    assert [x.tipo for x in r.rejeitados] == ["quarentena_liberar"]


def test_so_opcoes_proibidas_nao_e_resposta(personas: dict[str, Ator]) -> None:
    assert validar_schema(_vaga("quarentena_liberar"), personas["ivo"]).schema is None


def test_id_inventado_e_descartado(personas: dict[str, Ator]) -> None:
    assert validar_schema(_vaga("componente_que_nao_existe"), personas["ivo"]).schema is None


def test_texto_livre_no_lugar_de_id_nao_passa(personas: dict[str, Ator]) -> None:
    """Uma pergunta escrita pelo modelo seria o `titulo` do A-42 outra vez."""
    r = validar_schema(_vaga("O que voce quer registrar?"), personas["ivo"])
    assert r.schema is None


def test_mais_de_quatro_opcoes_e_recusado(personas: dict[str, Ator]) -> None:
    assert validar_schema(_vaga(*["lote_lista"] * 5), personas["ivo"]).schema is None


def test_opcao_repetida_aparece_uma_vez(personas: dict[str, Ator]) -> None:
    r = validar_schema(_vaga("lote_lista", "lote_lista"), personas["ivo"])
    assert r.schema is not None
    assert r.schema.esclarecer == ("lote_lista",)


def test_schema_restrito_so_oferece_ids_do_catalogo(personas: dict[str, Ator]) -> None:
    cat = catalogo_de(personas["ivo"])
    enum = json_schema_do_catalogo(cat)["properties"]["esclarecer"]["items"]["enum"]
    assert set(enum) == {c["id"] for c in cat}
    assert "quarentena_liberar" not in enum
