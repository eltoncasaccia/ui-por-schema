"""Destinatários: só quem consegue abrir a composição.

Compartilhar aponta para uma view e não concede acesso — quem abre carrega sob
a própria permissão. A consequência é que mandar para quem não pode ver entrega
uma tela vazia, e a pessoa não sabe o que faltou.

O filtro usa a MESMA função de validação da abertura. Duas checagens diferentes
divergiriam, e a lista prometeria o que a abertura nega.
"""

import inspect

from estoque.application.schema.validar import validar_schema
from estoque.domain.identidade import Ator
from estoque.server.rotas import compartilhamento


def esquema(tipo: str, **params: object) -> dict[str, object]:
    return {"versao": 1, "blocos": [{"tipo": tipo, "params": params}]}


def test_quem_nao_abre_nao_entra_na_lista(personas: dict[str, Ator]) -> None:
    """Uma composição com valor em estoque não pode ser oferecida à Cleide:
    ela abriria uma tela vazia."""
    custo = esquema("estoque_indicador", metrica="valor_em_estoque")
    assert validar_schema(custo, personas["rafael"]).schema is not None
    assert validar_schema(custo, personas["cleide"]).schema is None


def test_composicao_comum_serve_a_todos(personas: dict[str, Ator]) -> None:
    livre = esquema("fila_vencimento", janela="90")
    for nome, ator in personas.items():
        assert validar_schema(livre, ator).schema is not None, nome


def test_meia_composicao_nao_conta_como_abrivel(personas: dict[str, Ator]) -> None:
    """Dois blocos, um deles restrito: quem só abre metade fica de fora.
    Meia tela compartilhada é pior que nenhuma."""
    misto = {
        "versao": 1,
        "blocos": [
            {"tipo": "fila_vencimento", "params": {"janela": "90"}},
            {"tipo": "estoque_indicador", "params": {"metrica": "valor_em_estoque"}},
        ],
    }
    r = validar_schema(misto, personas["cleide"])
    # Um bloco passa e o outro é rejeitado — e é a REJEIÇÃO que exclui a pessoa.
    assert r.rejeitados, "o bloco de custo tem de ser rejeitado para Cleide"
    assert validar_schema(misto, personas["rafael"]).rejeitados == []


def test_endpoint_filtra_pelo_schema_e_nao_lista_todo_mundo() -> None:
    """O endpoint recebe o schema e valida contra o ator de CADA candidato."""
    fonte = inspect.getsource(compartilhamento.destinatarios)
    assert "validar_schema" in fonte, "precisa usar a mesma validação da abertura"
    assert "_ator_de" in fonte, "precisa montar o Ator de cada candidato"
    assert "not r.rejeitados" in fonte, "rejeição parcial exclui o candidato"
