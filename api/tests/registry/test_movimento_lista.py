"""T-024 — `movimento_lista`. AC-1, AC-2, AC-3 e AC-7.

O componente tem dois usos, e o AC-1 é o segundo: `status:
aguardando_autorizacao` é como Helena encontra o que precisa autorizar. Foi assim
que o catálogo coube em 23 (ADR-0011), e é a peça que a T-030 teve de improvisar
enquanto esta tarefa não existia.
"""

from dataclasses import replace

import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.movimento_lista import (
    VM,
    LinhaMovimento,
    Params,
    carregar,
    projetar,
)
from estoque.application.registry.registry import buscar, ids_permitidos
from estoque.domain.identidade import Ator

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")


async def vm_de(ator: Ator, **params: object) -> VM:
    return projetar(await carregar(Params.model_validate(params), contexto(ator)))


def por_id(vm: VM, mid: str) -> LinhaMovimento | None:
    return next((linha for linha in vm.linhas if linha.movimento_id == mid), None)


# ------------------------------------------------- AC-1 · a fila do RT
async def test_ac1_o_status_pendente_devolve_so_os_pendentes(
    personas: dict[str, Ator],
) -> None:
    """`m-11` é a saída de controlado esperando a segunda identificação."""
    vm = await vm_de(personas["marco"], status="aguardando_autorizacao", periodo="tudo")
    assert vm.total >= 1
    assert {linha.status for linha in vm.linhas} == {"aguardando_autorizacao"}
    assert por_id(vm, "m-11") is not None


async def test_ac1_o_pendente_respeita_o_escopo_de_unidade(
    personas: dict[str, Ator],
) -> None:
    """RN-A01, e é a metade do AC-1 que diz "das unidades do ator".

    `m-11` está na Matriz. Odair só alcança Uberlândia: a fila dele não o contém,
    e não é por filtro do componente — é o repositório que intersecta.
    """
    de_odair = await vm_de(personas["odair"], status="aguardando_autorizacao", periodo="tudo")
    assert por_id(de_odair, "m-11") is None
    de_ivo = await vm_de(personas["ivo"], status="aguardando_autorizacao", periodo="tudo")
    assert por_id(de_ivo, "m-11") is not None


async def test_ac1_sem_filtro_o_pendente_aparece_junto_com_o_resto(
    personas: dict[str, Ator],
) -> None:
    """O par negativo do filtro: se `status` fosse sempre aplicado, a lista geral
    esconderia o pendente e o contador não teria de onde sair."""
    vm = await vm_de(personas["marco"], periodo="tudo")
    assert por_id(vm, "m-11") is not None
    assert {linha.status for linha in vm.linhas} > {"aguardando_autorizacao"}


async def test_ac1_o_contador_de_pendentes_aparece_sem_filtro(
    personas: dict[str, Ator],
) -> None:
    """Um controlado parado é estoque travado. Só quem filtrou por ele veria, e
    quem não filtrou é justamente quem precisa ser avisado."""
    vm = await vm_de(personas["marco"], periodo="tudo")
    assert vm.pendentes >= 1
    assert vm.pendentes == sum(
        1 for linha in vm.linhas if linha.status == "aguardando_autorizacao"
    )


async def test_ac1_o_pendente_traz_ha_quantos_dias_esta_parado(
    personas: dict[str, Ator],
) -> None:
    vm = await vm_de(personas["marco"], status="aguardando_autorizacao", periodo="tudo")
    linha = por_id(vm, "m-11")
    assert linha is not None
    assert linha.parado_ha_dias is not None
    assert linha.parado_ha_dias >= 0


async def test_ac1_movimento_efetivado_nao_tem_dias_parado(
    personas: dict[str, Ator],
) -> None:
    """O par negativo: se o campo viesse sempre preenchido, ele deixaria de
    significar "esperando decisão"."""
    vm = await vm_de(personas["marco"], periodo="tudo")
    efetivado = next(linha for linha in vm.linhas if linha.status == "efetivado")
    assert efetivado.parado_ha_dias is None


# ------------------------------------------ AC-2 · estorno e original, ambos
async def test_ac2_o_estorno_e_o_original_aparecem_os_dois(
    personas: dict[str, Ator],
) -> None:
    """RN-M03. Esconder o original depois do estorno seria apagar história com
    outro nome — a lista precisa mostrar o erro E a correção."""
    vm = await vm_de(personas["marco"], periodo="tudo")
    original, estorno = por_id(vm, "m-02"), por_id(vm, "m-12")
    assert original is not None, "o original sumiu depois de estornado"
    assert estorno is not None


async def test_ac2_o_vinculo_aparece_nos_dois_sentidos(
    personas: dict[str, Ator],
) -> None:
    """Um estorno referencia o original; o original não sabe que foi estornado.
    É essa segunda metade que a tela precisa — sem ela, quem lê o original não
    tem como saber que ele já foi corrigido."""
    vm = await vm_de(personas["marco"], periodo="tudo")
    original, estorno = por_id(vm, "m-02"), por_id(vm, "m-12")
    assert estorno is not None and original is not None
    assert estorno.estorna == "m-02"
    assert original.estornado_por == "m-12"


async def test_ac2_movimento_sem_estorno_nao_e_marcado(
    personas: dict[str, Ator],
) -> None:
    """O par negativo: se `estornado_por` viesse sempre preenchido, o teste
    acima passaria e a marca não significaria nada."""
    vm = await vm_de(personas["marco"], periodo="tudo")
    intacto = por_id(vm, "m-01")
    assert intacto is not None
    assert intacto.estornado_por is None
    assert intacto.estorna is None


# --------------------------------------------------- AC-3 · nenhuma ação
def test_ac3_nao_ha_comando_de_edicao_nem_exclusao() -> None:
    """RN-M02 e CA-08, para papel nenhum.

    A garantia é o componente não declarar `commands` — não a ausência de um
    botão na tela. Sem `CommandDef`, o motor de render não tem o que oferecer, e
    o modelo não tem o que compor.
    """
    comp = buscar("movimento_lista")
    assert comp is not None
    assert comp.commands == {}


def test_ac3_vale_para_os_dois_componentes_de_leitura() -> None:
    for cid in ("movimento_lista", "auditoria_trilha"):
        comp = buscar(cid)
        assert comp is not None
        assert comp.commands == {}, cid


# ------------------------------------------------------ AC-7 · enums fechados
def test_ac7_tipo_fora_do_enum_e_rejeitado() -> None:
    """Entra por dicionário, como chega de verdade — JSON, sem tipo nenhum."""
    with pytest.raises(ValidationError):
        Params.model_validate({"tipo": "transferencia"})
    with pytest.raises(ValidationError):
        Params.model_validate({"tipo": ""})


def test_ac7_status_fora_do_enum_e_rejeitado() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate({"status": "pendente"})
    with pytest.raises(ValidationError):
        Params.model_validate({"status": "aguardando"})


def test_ac7_periodo_fora_do_enum_e_rejeitado() -> None:
    """Recorte de tempo por enum: data livre convida o modelo a inventar
    recorte, e recorte inventado erra em silêncio (risco R-5)."""
    with pytest.raises(ValidationError):
        Params.model_validate({"periodo": "45"})


def test_ac7_os_valores_validos_passam() -> None:
    """O par positivo — sem ele, um enum vazio passaria em todos os negativos."""
    for t in ("entrada", "saida", "descarte", "estorno"):
        assert Params.model_validate({"tipo": t}).tipo == t
    for st in ("efetivado", "aguardando_autorizacao", "recusado"):
        assert Params.model_validate({"status": st}).status == st


# ------------------------------------------------------------ escopo e catálogo
async def test_escopo_de_unidade(personas: dict[str, Ator]) -> None:
    vm = await vm_de(personas["odair"], periodo="tudo")
    assert {linha.unidade for linha in vm.linhas} == {"Uberlândia"}


def test_quem_nao_tem_movimento_ler_nao_ve(personas: dict[str, Ator]) -> None:
    """Rafael é comprador: tem `lote.ler` e não tem `movimento.ler`."""
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "movimento.ler" in ator.permissoes
        assert ("movimento_lista" in ids_permitidos(ator)) is esperado, nome
    assert "movimento_lista" not in ids_permitidos(personas["rafael"])


def test_recem_cadastrado_e_inativo_nao_veem(
    recem_cadastrado: Ator, personas: dict[str, Ator]
) -> None:
    assert "movimento_lista" not in ids_permitidos(recem_cadastrado)
    assert "movimento_lista" not in ids_permitidos(replace(personas["marco"], ativo=False))


# -------------------------------------------------------------- invariantes
async def test_custo_nao_atravessa_a_rede(personas: dict[str, Ator]) -> None:
    vm = await vm_de(personas["marco"], periodo="tudo")
    bruto = vm.model_dump_json()
    assert "custo" not in bruto
    assert "1250" not in bruto


async def test_ordena_do_mais_recente_para_o_mais_antigo(
    personas: dict[str, Ator],
) -> None:
    vm = await vm_de(personas["marco"], periodo="tudo")
    datas = [linha.criado_em for linha in vm.linhas]
    assert datas == sorted(datas, reverse=True)


async def test_select_e_puro(personas: dict[str, Ator]) -> None:
    dados = await carregar(Params(periodo="tudo"), contexto(personas["marco"]))
    assert projetar(dados) == projetar(dados)


def test_e_formulario_inteiro() -> None:
    comp = buscar("movimento_lista")
    assert comp is not None
    assert comp.tamanho == "inteira"
    assert comp.requires == "movimento.ler"
