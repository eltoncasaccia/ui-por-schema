"""ADR-0003 e CS-02 — o catalogo e' o vocabulario DESTE ator.

O teste que vale aqui e' o negativo: provar que Cleide NAO recebe custo por
nenhum caminho, inclusive por valor de enum.
"""

from estoque.application.registry.orcamento import ALERTA_TOKENS, tokens_do_catalogo
from estoque.application.registry.registry import ids_permitidos
from estoque.domain.identidade import Ator

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")

# Exigem so' `lote.ler`, que todos os sete papeis tem.
SO_LOTE_LER = ("fila_vencimento", "lote_lista", "lote_detalhe", "quarentena_fila")


def test_todo_papel_com_lote_ler_ve_os_componentes_de_lote(
    personas: dict[str, Ator],
) -> None:
    for nome in TODAS_AS_PERSONAS:
        catalogo = ids_permitidos(personas[nome])
        for componente in SO_LOTE_LER:
            assert componente in catalogo, f"{nome} nao ve {componente}"


def test_lote_movimentos_exige_as_duas_permissoes(personas: dict[str, Ator]) -> None:
    """`requires` e' tupla, e tupla e' conjuncao — nao disjuncao.

    Rafael (comprador) tem `lote.ler` e NAO tem `movimento.ler`. Se a exigencia
    fosse "qualquer uma", ele veria o extrato do lote, que e' historico de
    movimentacao e nao lhe diz respeito. Este e' o teste negativo que separa as
    duas leituras de uma tupla de permissoes.
    """
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        pode = {"movimento.ler", "lote.ler"} <= set(ator.permissoes)
        assert ("lote_movimentos" in ids_permitidos(ator)) is pode, nome

    assert "movimento.ler" not in personas["rafael"].permissoes
    assert "lote_movimentos" not in ids_permitidos(personas["rafael"])


def test_recem_cadastrado_tem_catalogo_vazio(recem_cadastrado: Ator) -> None:
    """ADR-0019 — o cadastro nao abre buraco de permissao."""
    assert ids_permitidos(recem_cadastrado) == frozenset()


def test_ator_inativo_tem_catalogo_vazio(personas: dict[str, Ator]) -> None:
    """RN-A06 (negativo): desativar tem efeito imediato."""
    from dataclasses import replace

    inativo = replace(personas["helena"], ativo=False)
    assert ids_permitidos(inativo) == frozenset()


# --- T-024: leitura de movimento e de trilha ---------------------------------
def test_movimento_lista_segue_movimento_ler(personas: dict[str, Ator]) -> None:
    """Rafael (comprador) e' o contraexemplo: tem `lote.ler`, nao tem
    `movimento.ler`. Extrato de movimentacao nao lhe diz respeito."""
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "movimento.ler" in ator.permissoes
        assert ("movimento_lista" in ids_permitidos(ator)) is esperado, nome
    assert "movimento_lista" not in ids_permitidos(personas["rafael"])


def test_auditoria_trilha_so_para_quem_tem_auditoria_ler(
    personas: dict[str, Ator],
) -> None:
    """T-024 AC-4, enumerado. Ivo, Odair e Cleide movimentam estoque e nao leem
    a trilha de quem fez o que — sao papeis operacionais, nao de controle."""
    assert "auditoria_trilha" in ids_permitidos(personas["marco"])
    assert "auditoria_trilha" in ids_permitidos(personas["sandra"])
    for nome in ("ivo", "odair", "cleide", "rafael"):
        assert "auditoria_trilha" not in ids_permitidos(personas[nome]), nome


# --- ADR-0003: as acoes privativas do RT (T-027) -----------------------------
# `lote.liberar` e `lote.status` existem num papel so' (documento 02 §6). Este
# par de testes e' o ADR-0003 na forma mais limpa que o projeto tem: o
# vocabulario do modelo E' o do ator, e para seis dos sete papeis estes dois ids
# simplesmente nao existem.
SO_DO_RT = ("quarentena_liberar", "lote_status_acao")


def test_so_o_rt_ve_as_acoes_privativas(personas: dict[str, Ator]) -> None:
    catalogo = ids_permitidos(personas["helena"])
    for componente in SO_DO_RT:
        assert componente in catalogo, componente


def test_os_outros_seis_papeis_nao_veem_as_acoes_do_rt(
    personas: dict[str, Ator],
) -> None:
    """RN-R02: "nenhum outro papel, em nenhuma circunstancia".

    Enumerado papel a papel de proposito. Um laco que so' afirmasse sobre
    Helena ficaria verde com o catalogo aberto para todo mundo.
    """
    for nome in ("marco", "ivo", "odair", "cleide", "rafael", "sandra"):
        catalogo = ids_permitidos(personas[nome])
        for componente in SO_DO_RT:
            assert componente not in catalogo, f"{nome} ve {componente}"


def test_nem_o_diretor_ve(personas: dict[str, Ator]) -> None:
    """Papel nao e' nivel, e' conjunto: Marco tem mais permissoes que Helena e
    nenhuma delas e' estas duas."""
    assert "lote.liberar" not in personas["marco"].permissoes
    assert "lote.status" not in personas["marco"].permissoes


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
    from estoque.application.registry.registry import catalogo_de

    for nome in SEM_CUSTO:
        entrada = next(e for e in catalogo_de(personas[nome]) if e["id"] == "estoque_indicador")
        valores = entrada["params"]["metrica"]["valores"]
        assert "valor_em_estoque" not in valores, nome
        assert "lotes_em_quarentena" in valores, nome


def test_quem_tem_custo_ve_a_metrica(personas: dict[str, Ator]) -> None:
    from estoque.application.registry.registry import catalogo_de

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
    from estoque.application.registry.registry import catalogo_de, todos, valores_proibidos

    for nome, ator in personas.items():
        for entrada in catalogo_de(ator):
            comp = todos()[entrada["id"]]
            texto = (entrada["description"] + " " + " ".join(entrada["examples"])).lower()
            for _campo, proibidos in valores_proibidos(comp, ator).items():
                for valor in proibidos:
                    # `valor_em_estoque` -> "valor em estoque"
                    frase = valor.replace("_", " ")
                    assert frase not in texto, f"{nome}/{entrada['id']}: vaza {valor!r}"


# --- T-019: produto e custo restrito ---------------------------------------
def test_produto_ficha_e_saldo_por_unidade_para_todos_os_papeis(
    personas: dict[str, Ator],
) -> None:
    """`produto_ficha` (produto.ler) e `produto_saldo_por_unidade` (lote.ler)
    estao no catalogo dos sete: nenhum dos dois E' o componente de custo."""
    for nome in TODAS_AS_PERSONAS:
        catalogo = ids_permitidos(personas[nome])
        assert "produto_ficha" in catalogo, nome
        assert "produto_saldo_por_unidade" in catalogo, nome


def test_variante_de_custo_da_ficha_some_do_enum_de_quem_nao_pode(
    personas: dict[str, Ator],
) -> None:
    """A-05 outra vez: nao se esconde a ficha, remove-se o VALOR `com_custo`.
    Cleide ve `produto_ficha`; nao ve a opcao de trazer o custo."""
    from estoque.application.registry.registry import catalogo_de

    for nome in SEM_CUSTO:
        entrada = next(e for e in catalogo_de(personas[nome]) if e["id"] == "produto_ficha")
        assert "com_custo" not in entrada["params"]["variante"]["valores"], nome
        assert "padrao" in entrada["params"]["variante"]["valores"], nome
    for nome in COM_CUSTO:
        entrada = next(e for e in catalogo_de(personas[nome]) if e["id"] == "produto_ficha")
        assert "com_custo" in entrada["params"]["variante"]["valores"], nome


# --- T-021: rastreabilidade ----------------------------------------------
def test_rastreabilidade_segue_auditoria_rastrear(personas: dict[str, Ator]) -> None:
    """RN-D03/D04 são "[R]" e a permissão é de controle: só Marco, Helena e
    Sandra rastreiam. Odair, Ivo, Cleide e Rafael não veem o componente — é a
    negativa de CA-06 na camada do catálogo (ADR-0003)."""
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "auditoria.rastrear" in ator.permissoes
        assert ("rastreabilidade" in ids_permitidos(ator)) is esperado, nome
    for nome in ("odair", "ivo", "cleide", "rafael"):
        assert "rastreabilidade" not in ids_permitidos(personas[nome]), nome


# --- T-022: leitura de recebimento --------------------------------------
def test_recebimento_lista_e_detalhe_seguem_recebimento_ler(
    personas: dict[str, Ator],
) -> None:
    """Rafael (comprador) e' o contraexemplo: tem `lote.ler`, nao tem
    `recebimento.ler`. O que entrou no CD nao lhe diz respeito."""
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "recebimento.ler" in ator.permissoes
        for componente in ("recebimento_lista", "recebimento_detalhe"):
            assert (componente in ids_permitidos(ator)) is esperado, f"{nome}/{componente}"
    for componente in ("recebimento_lista", "recebimento_detalhe"):
        assert componente not in ids_permitidos(personas["rafael"])


# --- T-023: cadeia fria ----------------------------------------------------
def test_temperatura_historico_e_excursoes_seguem_temperatura_ler(
    personas: dict[str, Ator],
) -> None:
    """Rafael (comprador) de novo: `lote.ler` e `custo.ler`, mas nada de
    `temperatura.ler`. A cadeia fria da câmara não é assunto de compra."""
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "temperatura.ler" in ator.permissoes
        for componente in ("temperatura_historico", "temperatura_excursoes"):
            assert (componente in ids_permitidos(ator)) is esperado, f"{nome}/{componente}"
    for componente in ("temperatura_historico", "temperatura_excursoes"):
        assert componente not in ids_permitidos(personas["rafael"])


# --- ADR-0011 / RNF-08 -------------------------------------------------------
def test_orcamento_de_tokens_abaixo_do_alerta(personas: dict[str, Ator]) -> None:
    for nome, ator in personas.items():
        assert tokens_do_catalogo(ator) < ALERTA_TOKENS, nome


def test_teto_de_catalogo_e_verificado_na_importacao() -> None:
    from estoque.application.registry.orcamento import verificar_teto

    verificar_teto()  # nao levanta abaixo do teto
