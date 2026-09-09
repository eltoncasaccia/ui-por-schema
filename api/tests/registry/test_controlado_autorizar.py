"""T-030 — `controlado_autorizar`, o lado de leitura: a fila do RT.

AC-4 e AC-8 moram aqui. O fluxo de duas pessoas — AC-1, AC-2, AC-3, AC-5 — está
em `tests/commands/test_autorizacao_comandos.py`, contra Postgres real, porque
é lá que a transição de estado existe.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import grimp
import pytest
from fakes import contexto

from estoque.commands.entradas.autorizacao import EntradaAutorizacao
from estoque.domain.identidade import Ator
from estoque.domain.tipos import Movimento
from estoque.registry.componentes.controlado_autorizar import (
    VM,
    Dados,
    Params,
    projetar,
)
from estoque.registry.definir import CommandDef
from estoque.registry.registry import buscar, ids_permitidos

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")


def _mov(mov_id: str, autor: str, dias_atras: int) -> Movimento:
    return Movimento(
        id=mov_id,
        lote_id="l-rital-bloq",
        unidade_id="cd-matriz",
        tipo="saida",
        quantidade=5,
        motivo="venda",
        complemento=None,
        autor_id=autor,
        autorizador_id=None,
        status="aguardando_autorizacao",
        criado_em=datetime.now(UTC) - timedelta(days=dias_atras),
        estorna_movimento_id=None,
        cliente_id="cli-1",
        nota_fiscal="NF-1",
    )


def _dados(*, alvo: str | None, ator_id: str, movs: list[Movimento] | None = None) -> Dados:
    movimentos = movs if movs is not None else [_mov("m-1", "u-cleide", 3)]
    return Dados(
        movimentos=movimentos,
        nomes={mov.id: "Ritalina 10mg" for mov in movimentos},
        autores={mov.id: mov.autor_id for mov in movimentos},
        agora=datetime.now(UTC),
        escopo="CD Matriz",
        alvo_id=alvo,
        ator_id=ator_id,
    )


# ------------------------------------------------------- AC-4 · só o RT (matriz)
def test_ac4_so_helena_ve_o_componente(personas: dict[str, Ator]) -> None:
    """`controlado.autorizar` existe num papel só (documento 02 §6)."""
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "controlado.autorizar" in ator.permissoes
        assert ("controlado_autorizar" in ids_permitidos(ator)) is esperado, nome
    assert "controlado_autorizar" in ids_permitidos(personas["helena"])


def test_ac4_nem_marco_consegue(personas: dict[str, Ator]) -> None:
    """O Diretor tem mais permissões que a RT e nenhuma delas é esta. Papel não
    é nível, é conjunto — e `CA-04` depende disso."""
    assert "controlado.autorizar" not in personas["marco"].permissoes
    assert "controlado_autorizar" not in ids_permitidos(personas["marco"])


def test_ac4_os_outros_seis_papeis_nao_veem(personas: dict[str, Ator]) -> None:
    for nome in ("marco", "ivo", "odair", "cleide", "rafael", "sandra"):
        assert "controlado_autorizar" not in ids_permitidos(personas[nome]), nome


def test_ac4_cleide_movimenta_controlado_mas_nao_autoriza(
    personas: dict[str, Ator],
) -> None:
    """As duas permissões são distintas de propósito: `controlado.movimentar`
    inicia, `controlado.autorizar` conclui. Se fossem uma só, a dupla
    identificação não teria como existir."""
    cleide = personas["cleide"]
    assert "controlado.movimentar" in cleide.permissoes
    assert "controlado.autorizar" not in cleide.permissoes


def test_ac4_recem_cadastrado_e_inativo_nao_veem(
    recem_cadastrado: Ator, personas: dict[str, Ator]
) -> None:
    assert "controlado_autorizar" not in ids_permitidos(recem_cadastrado)
    assert "controlado_autorizar" not in ids_permitidos(
        replace(personas["helena"], ativo=False)
    )


# --------------------------------------------------- RN-A04 na tela (o 1º aviso)
def test_quem_submeteu_nao_pode_decidir() -> None:
    """RN-A04. A tela desabilita; o servidor recusa de novo; o CHECK do banco
    recusa uma terceira vez. Esta é a primeira das três, e é a mais fraca."""
    vm = projetar(_dados(alvo="m-1", ator_id="u-cleide"))
    assert vm.pode_decidir is False
    assert vm.motivo_impedimento is not None
    assert "RN-A04" in vm.motivo_impedimento


def test_outra_pessoa_pode_decidir() -> None:
    """O par positivo: sem ele, uma tela que bloqueasse todo mundo passaria."""
    vm = projetar(_dados(alvo="m-1", ator_id="u-helena"))
    assert vm.pode_decidir is True
    assert vm.motivo_impedimento is None


# ------------------------------------------------------------------- a fila
def test_a_fila_ordena_por_tempo_parado() -> None:
    """Um controlado parado há cinco dias é estoque travado. Ordenar por data de
    submissão esconderia isso atrás de uma coluna que ninguém compara de cabeça."""
    movs = [_mov("m-novo", "u-cleide", 1), _mov("m-velho", "u-ivo", 9)]
    vm = projetar(_dados(alvo=None, ator_id="u-helena", movs=movs))
    assert [p.movimento_id for p in vm.fila] == ["m-velho", "m-novo"]
    assert vm.fila[0].parado_ha_dias == 9


def test_fila_vazia_nao_quebra() -> None:
    vm = projetar(_dados(alvo=None, ator_id="u-helena", movs=[]))
    assert vm.total == 0
    assert vm.fila == []
    assert vm.alvo is None


def test_sem_alvo_nao_ha_formulario() -> None:
    vm = projetar(_dados(alvo=None, ator_id="u-helena"))
    assert vm.alvo is None
    assert vm.total == 1


def test_com_alvo_o_formulario_aponta_para_ele() -> None:
    vm = projetar(_dados(alvo="m-1", ator_id="u-helena"))
    assert vm.alvo is not None
    assert vm.alvo.movimento_id == "m-1"
    assert vm.alvo.quantidade == 5


# --------------------------------------------- AC-8 · o assistente não conclui
def test_ac8_o_command_def_publicado_nao_carrega_funcao() -> None:
    """ADR-0002, no ponto mais afiado do projeto.

    O que o catálogo entrega ao modelo é uma DESCRIÇÃO do comando. Se um dia
    ganhasse um callable, a composição do modelo passaria a segurar uma
    referência executável de uma movimentação de controlado — e a barreira
    viraria uma convenção sobre não chamá-la.
    """
    comp = buscar("controlado_autorizar")
    assert comp is not None
    cd = comp.commands["controlado_autorizar"]
    assert isinstance(cd, CommandDef)
    assert not hasattr(cd, "aplicar")
    assert cd.confirm is True


def test_ac8_o_assistente_nao_alcanca_o_comando_de_autorizacao() -> None:
    """O grafo, sem cache — `.grimp_cache` já serviu um grafo velho uma vez
    (achado A-17), e este é o teste que não pode ficar verde por atraso."""
    g = grimp.build_graph("estoque", cache_dir=None)
    caminho = g.find_shortest_chain(
        importer="estoque.assistant",
        imported="estoque.commands.autorizacao",
        as_packages=True,
    )
    assert caminho is None, f"o assistente alcança a autorização por {caminho}"


def test_ac8_o_grafo_enxerga_o_caminho_que_existe() -> None:
    """Par negativo do teste acima: `server` alcança o comando de verdade."""
    g = grimp.build_graph("estoque", cache_dir=None)
    assert (
        g.find_shortest_chain(
            importer="estoque.server",
            imported="estoque.commands.autorizacao",
            as_packages=True,
        )
        is not None
    )


# ------------------------------------------------------------------- schema
def test_decisao_fora_do_enum_e_rejeitada() -> None:
    """Entra por dicionário, que é como chega de verdade."""
    with pytest.raises(Exception):  # noqa: B017
        EntradaAutorizacao.model_validate(
            {"movimento_id": "m-1", "decisao": "talvez", "motivo": "x" * 12}
        )


def test_as_duas_decisoes_sao_aceitas() -> None:
    for d in ("autorizar", "recusar"):
        e = EntradaAutorizacao.model_validate(
            {"movimento_id": "m-1", "decisao": d, "motivo": "motivo suficiente"}
        )
        assert e.decisao == d


def test_motivo_vazio_e_rejeitado() -> None:
    """Exigido nas DUAS decisões: autorizar controlado sem motivo registrado não
    serve a quem audita depois, que é o público da trilha."""
    with pytest.raises(Exception):  # noqa: B017
        EntradaAutorizacao.model_validate(
            {"movimento_id": "m-1", "decisao": "autorizar", "motivo": ""}
        )


# -------------------------------------------------------------- invariantes
def test_custo_nao_atravessa_a_rede() -> None:
    vm = projetar(_dados(alvo="m-1", ator_id="u-helena"))
    bruto = vm.model_dump_json()
    assert "custo" not in bruto


def test_select_e_puro() -> None:
    d = _dados(alvo="m-1", ator_id="u-helena")
    assert projetar(d) == projetar(d)


def test_o_componente_e_formulario_inteiro() -> None:
    comp = buscar("controlado_autorizar")
    assert comp is not None
    assert comp.tamanho == "inteira"
    assert comp.requires == "controlado.autorizar"


async def test_a_fila_respeita_o_escopo(personas: dict[str, Ator]) -> None:
    """RN-A01: o `load` pede ao repositório, e o repositório intersecta. Odair
    não vê pendência da Matriz."""
    from estoque.registry.componentes.controlado_autorizar import carregar

    dados = await carregar(Params(), contexto(personas["odair"]))
    for mov in dados.movimentos:
        assert mov.unidade_id in personas["odair"].unidades


def _vm_tipo() -> type[VM]:
    return VM
