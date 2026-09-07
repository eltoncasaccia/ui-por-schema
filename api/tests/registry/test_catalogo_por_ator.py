"""ADR-0003 e CS-02 — o catalogo e' o vocabulario DESTE ator.

O teste que vale aqui e' o negativo: provar que Cleide NAO recebe custo por
nenhum caminho, inclusive por valor de enum.
"""

from estoque.domain.identidade import Ator
from estoque.registry.orcamento import ALERTA_TOKENS, tokens_do_catalogo
from estoque.registry.registry import ids_permitidos


def test_todo_papel_com_lote_ler_ve_os_componentes_de_lote(
    personas: dict[str, Ator],
) -> None:
    for nome in ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra"):
        assert "fila_vencimento" in ids_permitidos(personas[nome]), nome


def test_recem_cadastrado_tem_catalogo_vazio(recem_cadastrado: Ator) -> None:
    """ADR-0019 — o cadastro nao abre buraco de permissao."""
    assert ids_permitidos(recem_cadastrado) == frozenset()


def test_ator_inativo_tem_catalogo_vazio(personas: dict[str, Ator]) -> None:
    """RN-A06 (negativo): desativar tem efeito imediato."""
    from dataclasses import replace

    inativo = replace(personas["helena"], ativo=False)
    assert ids_permitidos(inativo) == frozenset()


# --- CS-02 / CA-05: o vazamento de custo, por todos os caminhos --------------
SEM_CUSTO = ("cleide", "helena", "ivo", "odair")
COM_CUSTO = ("marco", "rafael", "sandra")


def test_metrica_de_custo_some_do_enum_de_quem_nao_pode(
    personas: dict[str, Ator],
) -> None:
    """O achado A-05 em acao: nao se esconde o componente, remove-se o VALOR.

    Cleide continua vendo `estoque_indicador` — ela precisa dele. O que ela nao
    ve e' a metrica `valor_em_estoque`, e por isso o modelo nao consegue propor.
    """
    from estoque.registry.registry import catalogo_de

    for nome in SEM_CUSTO:
        entrada = next(e for e in catalogo_de(personas[nome]) if e["id"] == "estoque_indicador")
        valores = entrada["params"]["metrica"]["valores"]
        assert "valor_em_estoque" not in valores, nome
        assert "lotes_em_quarentena" in valores, nome


def test_quem_tem_custo_ve_a_metrica(personas: dict[str, Ator]) -> None:
    from estoque.registry.registry import catalogo_de

    for nome in COM_CUSTO:
        entrada = next(e for e in catalogo_de(personas[nome]) if e["id"] == "estoque_indicador")
        assert "valor_em_estoque" in entrada["params"]["metrica"]["valores"], nome


def test_descricao_nunca_enumera_valor_de_enum_filtrado(
    personas: dict[str, Ator],
) -> None:
    """Invariante geral, encontrada por este teste durante a implementacao.

    O enum de params e' filtrado por permissao; a `description` nao e'. Se a
    prosa repetir um valor que o filtro removeu, o vazamento volta pela porta
    dos fundos: o modelo aprende que existe um valor que ele nao pode propor,
    e tenta.

    Regra que passa a valer: a descricao descreve o COMPONENTE; o enum descreve
    as OPCOES. Nunca as duas coisas.
    """
    from estoque.registry.registry import catalogo_de, todos, valores_proibidos

    for nome, ator in personas.items():
        for entrada in catalogo_de(ator):
            comp = todos()[entrada["id"]]
            texto = (entrada["description"] + " " + " ".join(entrada["examples"])).lower()
            for _campo, proibidos in valores_proibidos(comp, ator).items():
                for valor in proibidos:
                    # `valor_em_estoque` -> "valor em estoque"
                    frase = valor.replace("_", " ")
                    assert frase not in texto, f"{nome}/{entrada['id']}: vaza {valor!r}"


# --- ADR-0011 / RNF-08 -------------------------------------------------------
def test_orcamento_de_tokens_abaixo_do_alerta(personas: dict[str, Ator]) -> None:
    for nome, ator in personas.items():
        assert tokens_do_catalogo(ator) < ALERTA_TOKENS, nome


def test_teto_de_catalogo_e_verificado_na_importacao() -> None:
    from estoque.registry.orcamento import verificar_teto

    verificar_teto()  # nao levanta com 2 componentes
