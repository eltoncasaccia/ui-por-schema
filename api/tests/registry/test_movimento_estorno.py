"""T-029 — `movimento_estorno`, o lado de leitura: o extrato com o que se corrige.

O fluxo de escrita — AC-1 a AC-5 e AC-8 — está em
`tests/commands/test_estorno_comandos.py`, contra Postgres real, porque é lá que
`RN-M02` existe. Aqui prova-se o que a tela mostra ANTES: quais lançamentos são
estornáveis, e o motivo de cada um que não é.

O estoque falso já traz os quatro casos difíceis (ver `fakes.py`):

  m-06  saída efetivada, nunca estornada   -> o único estornável
  m-02  saída efetivada, JÁ estornada       -> por `m-12`
  m-12  o estorno de `m-02`                 -> estorno não se estorna
  m-11  saída de controlado pendente        -> não teve efeito no saldo
"""

from dataclasses import replace
from typing import get_args

import grimp
import pytest
from fakes import contexto

from estoque.application.commands.entradas.estorno import (
    TIPOS_ESTORNAVEIS,
    EntradaEstorno,
    MotivoEstorno,
)
from estoque.application.registry.componentes.movimento_estorno import (
    ROTULO_MOTIVO,
    Params,
    carregar,
    projetar,
)
from estoque.application.registry.definir import CommandDef
from estoque.application.registry.registry import buscar, ids_permitidos
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")

LOTE_COM_ESTORNAVEL = "l-amox-zero"  # m-05 entrada, m-06 saída nunca estornada
LOTE_JA_CORRIGIDO = "l-amox-mtz"  # m-01 entrada, m-02 saída, m-12 estorno de m-02
LOTE_PENDENTE = "l-rital-bloq"  # m-09 entrada, m-11 saída aguardando autorização


async def _vm(ator: Ator, lote_id: str, movimento_id: str | None = None) -> object:
    dados = await carregar(Params(lote_id=lote_id, movimento_id=movimento_id), contexto(ator))
    return projetar(dados)


def _por_id(vm: object, movimento_id: str) -> object:
    return next(x for x in vm.lancamentos if x.movimento_id == movimento_id)  # type: ignore[attr-defined]


# ------------------------------------------------- catálogo por ator (ADR-0003)
def test_so_quem_estorna_ve_o_componente(personas: dict[str, Ator]) -> None:
    """`requires` é tupla, e tupla é conjunção: `movimento.estornar` E
    `movimento.ler`."""
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        pode = {"movimento.estornar", "movimento.ler"} <= set(ator.permissoes)
        assert ("movimento_estorno" in ids_permitidos(ator)) is pode, nome


def test_sandra_le_o_extrato_e_nao_estorna(personas: dict[str, Ator]) -> None:
    """O teste negativo que separa leitura de correção. A Auditoria lê todo
    movimento do sistema — e corrigir o livro-razão que ela audita seria a mesma
    pessoa nos dois lados."""
    sandra = personas["sandra"]
    assert "movimento.ler" in sandra.permissoes
    assert "movimento.estornar" not in sandra.permissoes
    assert "movimento_estorno" not in ids_permitidos(sandra)


def test_cleide_movimenta_e_nao_corrige(personas: dict[str, Ator]) -> None:
    cleide = personas["cleide"]
    assert "movimento.criar" in cleide.permissoes
    assert "movimento_estorno" not in ids_permitidos(cleide)


def test_recem_cadastrado_e_inativo_nao_veem(
    recem_cadastrado: Ator, personas: dict[str, Ator]
) -> None:
    assert "movimento_estorno" not in ids_permitidos(recem_cadastrado)
    assert "movimento_estorno" not in ids_permitidos(replace(personas["ivo"], ativo=False))


# ------------------------------------------------------ o que pode ser estornado
async def test_saida_efetivada_e_nao_estornada_pode(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["ivo"], LOTE_COM_ESTORNAVEL)
    saida = _por_id(vm, "m-06")
    assert saida.pode_estornar is True  # type: ignore[attr-defined]
    assert saida.impedimento is None  # type: ignore[attr-defined]


async def test_entrada_nao_pode(personas: dict[str, Ator]) -> None:
    """Achado A-38: o sinal do estorno é fixo e positivo (`saldo_lote`, migração
    0001). Estornar uma entrada somaria de novo o que se queria desfazer."""
    vm = await _vm(personas["ivo"], LOTE_COM_ESTORNAVEL)
    entrada = _por_id(vm, "m-05")
    assert entrada.pode_estornar is False  # type: ignore[attr-defined]
    assert "entrada" in (entrada.impedimento or "")  # type: ignore[attr-defined]


async def test_saida_ja_estornada_nao_pode(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["ivo"], LOTE_JA_CORRIGIDO)
    assert _por_id(vm, "m-02").impedimento == "Já estornado."  # type: ignore[attr-defined]


async def test_estorno_nao_se_estorna(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["ivo"], LOTE_JA_CORRIGIDO)
    estorno = _por_id(vm, "m-12")
    assert estorno.pode_estornar is False  # type: ignore[attr-defined]
    assert "RN-M03" in (estorno.impedimento or "")  # type: ignore[attr-defined]


async def test_controlado_pendente_nao_pode(personas: dict[str, Ator]) -> None:
    """RN-C01: pendente não mexeu no saldo, e estorná-lo devolveria mercadoria
    que nunca saiu."""
    vm = await _vm(personas["ivo"], LOTE_PENDENTE)
    pendente = _por_id(vm, "m-11")
    assert pendente.pode_estornar is False  # type: ignore[attr-defined]
    assert "aguardando_autorizacao" in (pendente.impedimento or "")  # type: ignore[attr-defined]


async def test_o_par_original_e_estorno_aparece_inteiro(personas: dict[str, Ator]) -> None:
    """RN-M03 quer o erro E a correção visíveis. Uma lista que escondesse o
    movimento estornado mostraria um estado limpo que finge que o erro não
    houve — e é o histórico que a auditoria vai ler."""
    vm = await _vm(personas["ivo"], LOTE_JA_CORRIGIDO)
    ids = {x.movimento_id for x in vm.lancamentos}  # type: ignore[attr-defined]
    assert {"m-02", "m-12"} <= ids
    assert _por_id(vm, "m-12").estorna_movimento_id == "m-02"  # type: ignore[attr-defined]


async def test_a_ordem_e_do_mais_recente_para_o_mais_antigo(
    personas: dict[str, Ator],
) -> None:
    """O erro que se corrige é quase sempre o último; o extrato em ordem de
    leitura começaria pelo recebimento de meses atrás."""
    vm = await _vm(personas["ivo"], LOTE_JA_CORRIGIDO)
    datas = [x.registrado_em for x in vm.lancamentos]  # type: ignore[attr-defined]
    assert datas == sorted(datas, reverse=True)


# --------------------------------------------------------------- alvo e escopo
async def test_com_movimento_id_o_formulario_aponta_para_ele(
    personas: dict[str, Ator],
) -> None:
    vm = await _vm(personas["ivo"], LOTE_COM_ESTORNAVEL, "m-06")
    assert vm.alvo is not None  # type: ignore[attr-defined]
    assert vm.alvo.movimento_id == "m-06"  # type: ignore[attr-defined]


async def test_sem_movimento_id_nao_ha_formulario(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["ivo"], LOTE_COM_ESTORNAVEL)
    assert vm.alvo is None  # type: ignore[attr-defined]
    assert vm.total > 0  # type: ignore[attr-defined]


async def test_movimento_de_outro_lote_nao_vira_alvo(personas: dict[str, Ator]) -> None:
    """`m-06` existe e é estornável — em OUTRO lote. Aceitá-lo aqui deixaria o
    formulário corrigir um lançamento que a tela não mostrou."""
    with pytest.raises(ErroDominio) as e:
        await _vm(personas["ivo"], LOTE_JA_CORRIGIDO, "m-06")
    assert e.value.codigo == "nao_encontrado"


async def test_lote_fora_do_escopo_e_indistinguivel_de_inexistente(
    personas: dict[str, Ator],
) -> None:
    """RN-A01 e ADR-0014. Odair é gerente, tem a permissão, e só alcança
    Uberlândia."""
    with pytest.raises(ErroDominio) as fora:
        await _vm(personas["odair"], LOTE_JA_CORRIGIDO)
    with pytest.raises(ErroDominio) as inexistente:
        await _vm(personas["odair"], "l-nao-existe")
    assert fora.value.codigo == inexistente.value.codigo == "nao_encontrado"
    assert fora.value.mensagem_publica == inexistente.value.mensagem_publica


# ------------------------------------------------------------------ schema
def test_motivo_fora_da_lista_e_rejeitado() -> None:
    """Entra por dicionário, que é como chega de verdade — vindo do JSON."""
    with pytest.raises(Exception):  # noqa: B017
        EntradaEstorno.model_validate(
            {"movimento_id": "m-06", "motivo": "devolucao", "complemento": "x" * 12}
        )


def test_os_motivos_da_lista_sao_aceitos() -> None:
    for motivo in get_args(MotivoEstorno):
        e = EntradaEstorno.model_validate(
            {"movimento_id": "m-06", "motivo": motivo, "complemento": "erro na separação"}
        )
        assert e.motivo == motivo


def test_complemento_vazio_e_rejeitado() -> None:
    """RN-M05: texto livre é complemento, nunca substituto — e `estorno` é o
    valor genérico da lista. Sozinho, ele não diz por quê."""
    with pytest.raises(Exception):  # noqa: B017
        EntradaEstorno.model_validate(
            {"movimento_id": "m-06", "motivo": "estorno", "complemento": ""}
        )


def test_todo_motivo_tem_rotulo_na_tela() -> None:
    """Um motivo novo no schema sem rótulo aqui apareceria como valor cru na
    tela — e o `dict[MotivoEstorno, str]` já não compilaria, mas o teste diz
    qual falta."""
    assert set(ROTULO_MOTIVO) == set(get_args(MotivoEstorno))


def test_a_lista_de_tipos_estornaveis_tem_uma_fonte_so() -> None:
    """O componente e o comando leem a MESMA constante, do módulo-folha.

    A pergunta é feita ao grafo de imports, e não comparando os dois valores:
    dois módulos com listas iguais escritas à mão passariam na comparação e
    divergiriam na primeira mudança — que é o achado A-11. O que este teste
    afirma é a fonte única, e de quebra que o componente NÃO alcança
    `commands.estorno` (contrato 2 do import-linter: sqlalchemy no caminho).
    """
    folha = "estoque.application.commands.entradas.estorno"
    g = grimp.build_graph("estoque", cache_dir=None)

    for modulo in (
        "estoque.application.commands.estorno",
        "estoque.application.registry.componentes.movimento_estorno",
    ):
        assert folha in g.find_modules_directly_imported_by(modulo), modulo

    assert (
        g.find_shortest_chain(
            importer="estoque.application.registry.componentes.movimento_estorno",
            imported="estoque.application.commands.estorno",
        )
        is None
    )
    # A constante existe e é o que o componente usa — sem isso, um grafo com os
    # imports certos e a lista vazia passaria.
    assert TIPOS_ESTORNAVEIS == ("saida",)


# -------------------------------------------------------------- invariantes
async def test_custo_nao_atravessa_a_rede(personas: dict[str, Ator]) -> None:
    """CA-05: quem tem `custo.ler` também não recebe custo aqui — o que não está
    no viewmodel não chega ao navegador."""
    for nome in ("marco", "ivo"):
        vm = await _vm(personas[nome], LOTE_JA_CORRIGIDO)
        assert "custo" not in vm.model_dump_json()  # type: ignore[attr-defined]


async def test_select_e_puro(personas: dict[str, Ator]) -> None:
    dados = await carregar(Params(lote_id=LOTE_JA_CORRIGIDO), contexto(personas["ivo"]))
    assert projetar(dados) == projetar(dados)


def test_o_componente_e_formulario_inteiro() -> None:
    comp = buscar("movimento_estorno")
    assert comp is not None
    assert comp.tamanho == "inteira"  # ADR-0005
    assert comp.requires == ("movimento.estornar", "movimento.ler")


def test_o_command_def_publicado_nao_carrega_funcao() -> None:
    """ADR-0002: o que o catálogo entrega ao modelo é uma DESCRIÇÃO do comando.
    Um callable aqui daria à composição do modelo uma referência executável."""
    comp = buscar("movimento_estorno")
    assert comp is not None
    cd = comp.commands["movimento_estorno"]
    assert isinstance(cd, CommandDef)
    assert not hasattr(cd, "aplicar")
    assert cd.confirm is True
    assert cd.endpoint == "/api/comandos/movimento_estorno"
