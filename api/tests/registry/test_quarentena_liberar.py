"""T-027 — `quarentena_liberar`, o lado de leitura do formulário do RT.

O componente **não escreve**: aqui se prova o que ele mostra, o que ele esconde
e para quem ele existe. A escrita é `commands/lote.py`, testada em
`tests/commands/test_lote_comandos.py`.

AC-2 mora aqui: nenhum papel além do RT vê este id no catálogo.
"""

from dataclasses import replace

import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.quarentena_liberar import (
    VM,
    Params,
    carregar,
    projetar,
)
from estoque.application.registry.registry import buscar, ids_permitidos
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")


async def vm_de(lote_id: str, ator: Ator) -> VM:
    return projetar(await carregar(Params(lote_id=lote_id), contexto(ator)))


# ------------------------------------------------------ AC-2 · catálogo (ADR-0003)
def test_ac2_so_o_rt_ve_o_componente(personas: dict[str, Ator]) -> None:
    """`lote.liberar` existe num papel só. Este é o ADR-0003 na forma mais
    limpa que o projeto tem: o vocabulário do modelo é o do ator."""
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "lote.liberar" in ator.permissoes
        assert ("quarentena_liberar" in ids_permitidos(ator)) is esperado, nome
    assert "quarentena_liberar" in ids_permitidos(personas["helena"])


def test_ac2_nem_o_diretor_ve(personas: dict[str, Ator]) -> None:
    """RN-R02: "nenhum outro papel, em nenhuma circunstância". Papel não é
    nível — o Diretor tem mais permissões que o RT e nenhuma delas é esta."""
    assert "quarentena_liberar" not in ids_permitidos(personas["marco"])
    assert "lote.liberar" not in personas["marco"].permissoes


def test_ac2_recem_cadastrado_e_inativo_nao_veem(
    recem_cadastrado: Ator, personas: dict[str, Ator]
) -> None:
    assert "quarentena_liberar" not in ids_permitidos(recem_cadastrado)
    inativa = replace(personas["helena"], ativo=False)
    assert "quarentena_liberar" not in ids_permitidos(inativa)


# ------------------------------------------------------------ checklist RN-R03
async def test_termolabil_exige_temperatura(personas: dict[str, Ator]) -> None:
    """`l-vac-quar` é vacina — termolábil. A temperatura entra como obrigatória."""
    vm = await vm_de("l-vac-quar", personas["helena"])
    por_campo = {i.campo: i for i in vm.conferencia}
    assert por_campo["temperatura_conferida"].obrigatorio is True
    assert por_campo["integridade_conferida"].obrigatorio is True
    assert por_campo["validade_conferida"].obrigatorio is True
    assert por_campo["nota_fiscal_conferida"].obrigatorio is True


async def test_nao_termolabil_nao_exige_temperatura(personas: dict[str, Ator]) -> None:
    """O par negativo. Exigir temperatura de todo lote treinaria o RT a marcar
    tudo sem ler — e aí a conferência obrigatória não conferiria nada."""
    vm = await vm_de("l-amox-mtz", personas["helena"])
    por_campo = {i.campo: i for i in vm.conferencia}
    assert por_campo["temperatura_conferida"].obrigatorio is False
    assert por_campo["integridade_conferida"].obrigatorio is True


async def test_a_lista_de_conferencia_cobre_as_quatro_de_rn_r03(
    personas: dict[str, Ator],
) -> None:
    vm = await vm_de("l-vac-quar", personas["helena"])
    assert {i.campo for i in vm.conferencia} == {
        "integridade_conferida",
        "validade_conferida",
        "nota_fiscal_conferida",
        "temperatura_conferida",
    }


# ---------------------------------------------------------- estado do formulário
async def test_lote_em_quarentena_permite_decidir(personas: dict[str, Ator]) -> None:
    vm = await vm_de("l-vac-quar", personas["helena"])
    assert vm.pode_decidir is True
    assert vm.motivo is None


async def test_lote_fora_da_quarentena_nao_permite_e_diz_por_que(
    personas: dict[str, Ator],
) -> None:
    """`l-rital-bloq` está bloqueado. O formulário aparece — quem perguntou tem
    direito à resposta — mas desabilitado, e com o motivo dito."""
    vm = await vm_de("l-rital-bloq", personas["helena"])
    assert vm.pode_decidir is False
    assert vm.motivo is not None
    assert "bloqueado" in vm.motivo


async def test_lote_vencido_na_quarentena_avisa(personas: dict[str, Ator]) -> None:
    """`l-vac-quar-venc` venceu esperando decisão — o pior caso do fixture.
    Liberar não o torna vendável (RN-L06), e o aviso precisa dizer isso."""
    vm = await vm_de("l-vac-quar-venc", personas["helena"])
    assert vm.status_efetivo == "vencido"
    assert vm.aviso_validade is not None
    assert "venceu" in vm.aviso_validade


async def test_validade_folgada_nao_gera_aviso(personas: dict[str, Ator]) -> None:
    """O par negativo do aviso: `l-vac-quar` vence em 400 dias."""
    vm = await vm_de("l-vac-quar", personas["helena"])
    assert vm.aviso_validade is None


# --------------------------------------------------------- escopo e negativa
async def test_lote_de_outra_unidade_nao_e_encontrado(personas: dict[str, Ator]) -> None:
    """RN-A01: quem aplica o escopo é a porta. Odair só alcança Uberlândia."""
    with pytest.raises(ErroDominio) as e:
        await vm_de("l-vac-quar", personas["odair"])
    assert e.value.codigo == "nao_encontrado"


async def test_fora_de_escopo_e_inexistente_sao_indistinguiveis(
    personas: dict[str, Ator],
) -> None:
    """ADR-0014, CS-03. Bastaria a mensagem diferir para virar oráculo de
    enumeração: iterando ids, descobre-se o estoque das outras unidades."""

    def face(err: ErroDominio) -> tuple[str, str, str]:
        return (err.codigo, err.mensagem_publica, repr(err))

    with pytest.raises(ErroDominio) as fora:
        await vm_de("l-vac-quar", personas["odair"])
    with pytest.raises(ErroDominio) as inexistente:
        await vm_de("l-nao-existe", personas["odair"])
    assert face(fora.value) == face(inexistente.value)


# -------------------------------------------------------------- invariantes
async def test_custo_nao_atravessa_a_rede(personas: dict[str, Ator]) -> None:
    """CA-05. O fixture TEM custo de propósito — se ele estivesse ausente, este
    teste passaria por acidente e não provaria nada."""
    vm = await vm_de("l-vac-quar", personas["helena"])
    bruto = vm.model_dump_json()
    assert "custo" not in bruto
    assert "4800" not in bruto


async def test_select_e_puro(personas: dict[str, Ator]) -> None:
    dados = await carregar(Params(lote_id="l-vac-quar"), contexto(personas["helena"]))
    assert projetar(dados) == projetar(dados)


def test_params_exige_o_lote() -> None:
    """O param chega por dicionário, do JSON do modelo — sem tipo nenhum. Um
    `lote_id` ausente precisa morrer na validação, não virar busca vazia."""
    with pytest.raises(ValidationError):
        Params.model_validate({})
    with pytest.raises(ValidationError):
        Params.model_validate({"lote_id": 123})


def test_o_componente_declara_o_comando_e_e_formulario_inteiro() -> None:
    """ADR-0005: formulário é unidade inteira, nunca composto peça por peça."""
    comp = buscar("quarentena_liberar")
    assert comp is not None
    assert comp.tamanho == "inteira"
    assert set(comp.commands) == {"lote_liberar_quarentena"}
    assert comp.commands["lote_liberar_quarentena"].confirm is True
    assert comp.commands["lote_liberar_quarentena"].idempotent is False


def test_o_modulo_de_entradas_nao_alcanca_o_pipeline() -> None:
    """`registry` importa `commands.entradas.*` para declarar o `CommandDef`, e
    isso só é legal porque o pacote é folha: se um módulo dele passasse a
    importar o pipeline, `registry` alcançaria SQLAlchemy e o contrato 2
    quebraria.

    A asserção é sobre o PACOTE inteiro, não sobre `lote.py`: as quatro tarefas
    restantes de W4 vão acrescentar módulos aqui, e é este teste que impede o
    quinto de ser escrito errado.

    O teste não confia no comentário do módulo — percorre o grafo.
    """
    import grimp

    # `cache_dir=None`: cache pode servir grafo velho — ver a docstring do
    # fixture `grafo` em `tests/commands/test_ac1_barreira.py`.
    g = grimp.build_graph("estoque", include_external_packages=True, cache_dir=None)
    for proibido in ("estoque.application.commands.pipeline", "estoque.data", "sqlalchemy"):
        caminho = g.find_shortest_chain(
            importer="estoque.application.commands.entradas",
            imported=proibido,
            as_packages=True,
        )
        assert caminho is None, f"entradas alcança {proibido} por {caminho}"


def test_o_grafo_enxerga_o_import_que_existe() -> None:
    """Par negativo do teste acima: `commands.lote` ALCANÇA o pipeline. Se este
    caminho também sumisse, o problema seria a ferramenta."""
    import grimp

    g = grimp.build_graph("estoque", cache_dir=None)
    assert (
        g.find_shortest_chain(
            importer="estoque.application.commands.lote",
            imported="estoque.application.commands.pipeline",
            as_packages=True,
        )
        is not None
    )
