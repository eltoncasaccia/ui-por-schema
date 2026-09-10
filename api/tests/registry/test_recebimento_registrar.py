"""T-026 · `recebimento_registrar` — o formulário. AC-8, AC-9 e o catálogo.

O que é **do comando** (recusar termolábil em unidade seca, exigir RT, recusar
validade curta) está em `tests/commands/test_recebimento_comandos.py`. Aqui está
o que é **do formulário**: resolver o código de barras, dizer o que a classe
exige, e não vazar nada.
"""

from typing import Any

import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.recebimento_registrar import (
    VM,
    Params,
    carregar,
    projetar,
)
from estoque.application.registry.registry import buscar, ids_permitidos

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")

# Do fixture: `p-vac` é termolábil, `p-rital` é controlado, `p-amox` é comum.
EAN_VAC = "7891234000025"
EAN_RITAL = "7891234000032"
EAN_AMOX = "7891234000018"


async def vm_de(ator: Any, **params: object) -> VM:
    return projetar(await carregar(Params.model_validate(params), contexto(ator)))


# --- AC-8 · o leitor de código de barras tem para onde apontar --------------


async def test_ac8_o_ean_lido_resolve_para_produto(personas: dict[str, Any]) -> None:
    """O caminho inteiro do leitor: param `ean` → `por_ean` → viewmodel."""
    vm = await vm_de(personas["cleide"], ean=EAN_AMOX)
    assert vm.lido is not None
    assert vm.lido.produto_id == "p-amox"
    assert vm.lido.ean == EAN_AMOX
    assert vm.lido.nome == "Amoxicilina 500mg"
    assert vm.ean_nao_encontrado is None


async def test_ac8_ean_desconhecido_avisa_em_vez_de_falhar(
    personas: dict[str, Any],
) -> None:
    """Produto novo é caso normal num recebimento — não é erro.

    Devolver `nao_encontrado` aqui pararia o conferente no meio da esteira por
    algo que ele resolve digitando.
    """
    vm = await vm_de(personas["cleide"], ean="0000000000000")
    assert vm.lido is None
    assert vm.ean_nao_encontrado == "0000000000000"


async def test_ac8_sem_ean_o_formulario_abre_vazio(personas: dict[str, Any]) -> None:
    vm = await vm_de(personas["cleide"])
    assert vm.lido is None
    assert vm.ean_nao_encontrado is None
    assert vm.unidades, "o formulário precisa das unidades do ator"


async def test_ac8_a_exigencia_da_classe_vem_do_servidor(
    personas: dict[str, Any],
) -> None:
    """`exige_temperatura` e `exige_rt` são calculados aqui, não no cliente.

    Um formulário adulterado marcaria o termolábil como dispensando temperatura.
    A recusa real é do comando (`RN-F01`, `RN-R05`); isto é para a tela não pedir
    errado — e para não *deixar* de pedir.
    """
    vac = await vm_de(personas["cleide"], ean=EAN_VAC)
    assert vac.lido is not None
    assert vac.lido.classe == "termolabil"
    assert vac.lido.exige_temperatura is True
    assert vac.lido.exige_rt is False

    rital = await vm_de(personas["cleide"], ean=EAN_RITAL)
    assert rital.lido is not None
    assert rital.lido.exige_rt is True
    assert rital.lido.exige_temperatura is False

    # O par negativo: produto comum não exige nenhum dos dois. Sem ele, um
    # `exige_* = True` fixo passaria nos dois testes acima.
    amox = await vm_de(personas["cleide"], ean=EAN_AMOX)
    assert amox.lido is not None
    assert amox.lido.exige_temperatura is False
    assert amox.lido.exige_rt is False


async def test_ac8_o_ean_nao_intersecta_escopo_de_unidade(
    personas: dict[str, Any],
) -> None:
    """`RN-P01`: produto não pertence a unidade.

    Odair alcança só Uberlândia, e acha o mesmo produto que Cleide. Filtrar aqui
    faria a tela dizer que a caixa na mão dele não existe.
    """
    de_odair = await vm_de(personas["odair"], ean=EAN_VAC)
    de_cleide = await vm_de(personas["cleide"], ean=EAN_VAC)
    assert de_odair.lido is not None
    assert de_odair.lido.produto_id == de_cleide.lido.produto_id  # type: ignore[union-attr]
    # Mas as UNIDADES de destino continuam sendo só as dele (RN-A01).
    assert [u.id for u in de_odair.unidades] == ["filial-uberlandia"]


# --- escopo das unidades de destino ----------------------------------------


async def test_as_unidades_sao_so_as_do_ator(personas: dict[str, Any]) -> None:
    ivo = await vm_de(personas["ivo"])
    assert {u.id for u in ivo.unidades} == {"cd-matriz", "cd-refrigerado"}
    assert "filial-uberlandia" not in {u.id for u in ivo.unidades}


async def test_a_unidade_sugerida_e_a_pedida(personas: dict[str, Any]) -> None:
    vm = await vm_de(personas["ivo"], unidade_id="cd-refrigerado")
    assert vm.unidade_sugerida == "cd-refrigerado"


def test_unidade_invalida_e_recusada_na_validacao() -> None:
    """`unidade_id` é enum fechado — `UnidadeId`, do domínio."""
    with pytest.raises(ValidationError):
        Params.model_validate({"unidade_id": "cd-inventado"})


# --- AC-9 · unidade inteira (ADR-0005) --------------------------------------


def test_ac9_o_formulario_e_unidade_inteira() -> None:
    comp = buscar("recebimento_registrar")
    assert comp is not None
    assert comp.tamanho == "inteira"


def test_ac9_o_componente_declara_o_comando_e_nao_o_executa() -> None:
    """ADR-0002: o `CommandDef` descreve; não carrega função nenhuma.

    Mesmo que o modelo compusesse um bloco apontando para o comando, não há o
    que chamar do lado dele — é a ausência do caminho, não uma checagem.
    """
    comp = buscar("recebimento_registrar")
    assert comp is not None
    cmd = comp.commands["recebimento_registrar"]
    assert cmd.endpoint == "/api/comandos/recebimento_registrar"
    assert cmd.idempotent is False, "repetir DUPLICA: a chave é obrigatória"
    assert cmd.confirm is True
    assert not any(callable(getattr(cmd, campo, None)) for campo in ("aplicar", "executar"))


def test_ac9_o_schema_do_formulario_e_o_mesmo_do_comando() -> None:
    """Uma definição, dois lados. Duas declarações divergiriam (achado A-11)."""
    from estoque.application.commands.entradas.recebimento import EntradaRecebimento

    comp = buscar("recebimento_registrar")
    assert comp is not None
    assert comp.commands["recebimento_registrar"].schema is EntradaRecebimento


# --- custo invisível e pureza ----------------------------------------------


async def test_nenhum_custo_no_viewmodel(personas: dict[str, Any]) -> None:
    """`p-amox` tem custo no fixture de propósito: custo ausente ali faria este
    teste passar por acidente."""
    assert "custo.ler" in personas["marco"].permissoes
    bruto = (await vm_de(personas["marco"], ean=EAN_AMOX)).model_dump_json()
    assert "custo" not in bruto
    assert "1250" not in bruto


async def test_select_chamado_duas_vezes_da_o_mesmo(personas: dict[str, Any]) -> None:
    ctx = contexto(personas["cleide"])
    dados = await carregar(Params.model_validate({"ean": EAN_AMOX}), ctx)
    assert projetar(dados) == projetar(dados)


# --- catálogo por ator (ADR-0003) ------------------------------------------


def test_recebimento_registrar_segue_recebimento_criar(
    personas: dict[str, Any],
) -> None:
    """Quem registra recebimento é gerente e conferente. **Nem o Diretor** —
    papel não é nível, é conjunto."""
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "recebimento.criar" in ator.permissoes
        assert ("recebimento_registrar" in ids_permitidos(ator)) is esperado, nome
    for nome in ("marco", "rafael", "sandra"):
        assert "recebimento_registrar" not in ids_permitidos(personas[nome]), nome
    for nome in ("ivo", "odair", "cleide"):
        assert "recebimento_registrar" in ids_permitidos(personas[nome]), nome
