"""T-024 — `auditoria_trilha`. AC-4, AC-5 e AC-7.

**O AC-5 é a armadilha mais fácil de deixar passar no projeto inteiro**, e está
escrita no arquivo da tarefa: o custo é escondido na tela de produto, some do
enum do indicador, e reaparece na trilha de auditoria — que Sandra lê, e que um
gerente leria se a matriz mudasse.

O fixture tem uma linha COM custo de propósito (`fakes.TRILHA`, id 2). Se não
tivesse, o teste de vazamento passaria por ausência de dado — o mesmo motivo de
`PRODUTOS` ter `custo_unitario_centavos` preenchido.
"""

from dataclasses import replace

import pytest
from fakes import TRILHA, contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.auditoria_trilha import (
    VM,
    Params,
    carregar,
    projetar,
)
from estoque.application.registry.registry import buscar, ids_permitidos
from estoque.domain.identidade import Ator

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")


async def vm_de(ator: Ator, **params: object) -> VM:
    return projetar(await carregar(Params.model_validate(params), contexto(ator)))


# --------------------------------------------------------- AC-4 · o catálogo
def test_ac4_esta_no_catalogo_de_marco_e_sandra(personas: dict[str, Ator]) -> None:
    """A matriz do documento 02: `auditoria.ler` é do Diretor e da Auditoria."""
    assert "auditoria_trilha" in ids_permitidos(personas["marco"])
    assert "auditoria_trilha" in ids_permitidos(personas["sandra"])


def test_ac4_nao_esta_no_de_ivo_odair_nem_cleide(personas: dict[str, Ator]) -> None:
    """O negativo, nomeando os três que a tarefa nomeia."""
    for nome in ("ivo", "odair", "cleide"):
        assert "auditoria_trilha" not in ids_permitidos(personas[nome]), nome
        assert "auditoria.ler" not in personas[nome].permissoes, nome


def test_ac4_a_regra_vale_para_os_sete(personas: dict[str, Ator]) -> None:
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "auditoria.ler" in ator.permissoes
        assert ("auditoria_trilha" in ids_permitidos(ator)) is esperado, nome


def test_ac4_helena_le_a_trilha(personas: dict[str, Ator]) -> None:
    """A RT tem `auditoria.ler` — e precisa: é ela quem responde pela decisão
    técnica que a trilha registra."""
    assert "auditoria_trilha" in ids_permitidos(personas["helena"])


def test_ac4_recem_cadastrado_e_inativo_nao_veem(
    recem_cadastrado: Ator, personas: dict[str, Ator]
) -> None:
    assert "auditoria_trilha" not in ids_permitidos(recem_cadastrado)
    assert "auditoria_trilha" not in ids_permitidos(replace(personas["sandra"], ativo=False))


# ------------------------------------------- AC-5 · o vazamento por trilha
async def test_ac5_custo_nao_atravessa_a_rede_para_quem_nao_pode(
    personas: dict[str, Ator],
) -> None:
    """Helena não tem `custo.ler` (RN-A02) e tem `auditoria.ler`. É exatamente o
    par que torna a trilha um caminho de vazamento."""
    assert "custo.ler" not in personas["helena"].permissoes
    bruto = (await vm_de(personas["helena"])).model_dump_json()
    assert "custo" not in bruto
    assert "1250" not in bruto
    assert "12500" not in bruto


async def test_ac5_custo_some_ate_para_quem_tem_custo_ler(
    personas: dict[str, Ator],
) -> None:
    """A regra da casa é mais forte que o AC: custo não entra em viewmodel para
    papel nenhum (CA-05). Uma exceção por papel seria mais uma condição a errar.

    Marco e Sandra têm `custo.ler` — e mesmo assim não recebem o valor aqui.
    """
    for nome in ("marco", "sandra"):
        assert "custo.ler" in personas[nome].permissoes
        bruto = (await vm_de(personas[nome])).model_dump_json()
        assert "custo" not in bruto, nome
        assert "1250" not in bruto, nome


async def test_ac5_o_fixture_realmente_tem_custo(personas: dict[str, Ator]) -> None:
    """O teste que impede os dois acima de passarem por acidente.

    Se a trilha do fixture não tivesse custo, eles ficariam verdes provando
    nada — que é o modo de falha que esta suíte inteira existe para evitar.
    """
    com_custo = [
        x for x in TRILHA if x.valor_novo and "custo_unitario_centavos" in x.valor_novo
    ]
    assert com_custo, "o fixture precisa ter uma linha com custo"


async def test_ac5_a_linha_filtrada_se_declara_filtrada(
    personas: dict[str, Ator],
) -> None:
    """Omitir em silêncio seria pior que mostrar: quem audita precisa saber que
    havia mais ali. É a diferença entre "não teve" e "não te mostro"."""
    vm = await vm_de(personas["sandra"])
    filtradas = [linha for linha in vm.linhas if linha.filtrada]
    assert len(filtradas) == 1
    # O que sobrou da linha continua lá — filtrar não é apagar o evento.
    assert filtradas[0].valor_novo == {"quantidade": 10}


async def test_ac5_linha_sem_custo_nao_e_marcada(personas: dict[str, Ator]) -> None:
    """O par negativo: se `filtrada` fosse sempre verdadeiro, o teste acima
    passaria e a marca deixaria de significar alguma coisa."""
    vm = await vm_de(personas["sandra"])
    liberacao = next(linha for linha in vm.linhas if linha.acao == "lote_liberar_quarentena")
    assert liberacao.filtrada is False
    assert liberacao.valor_novo == {
        "status": "liberado",
        "justificativa": "conferencia completa",
    }


def test_ac5_o_filtro_alcanca_qualquer_profundidade() -> None:
    """`valor_novo` é JSON livre — a forma depende de qual comando escreveu. Um
    filtro de um nível só deixaria passar `{"antes": {"custo": 1250}}`."""
    from estoque.application.registry.componentes.auditoria_trilha import _sem_custo

    limpo, removeu = _sem_custo(
        {"antes": {"custo_unitario_centavos": 1250}, "lista": [{"total_centavos": 99}], "ok": 1}
    )
    assert removeu is True
    assert limpo == {"antes": {}, "lista": [{}], "ok": 1}


def test_ac5_o_filtro_nao_remove_o_que_nao_e_dinheiro() -> None:
    """O par negativo do filtro: se ele removesse demais, a trilha ficaria vazia
    e o teste de vazamento continuaria verde."""
    from estoque.application.registry.componentes.auditoria_trilha import _sem_custo

    limpo, removeu = _sem_custo({"status": "liberado", "quantidade": 10, "lote_id": "l-1"})
    assert removeu is False
    assert limpo == {"status": "liberado", "quantidade": 10, "lote_id": "l-1"}


# --------------------------------------------------------- AC-7 · enum fechado
def test_ac7_entidade_fora_do_enum_e_rejeitada() -> None:
    """Entra por dicionário, como chega de verdade — JSON do modelo, sem tipo."""
    with pytest.raises(ValidationError):
        Params.model_validate({"entidade": "tabela_secreta"})
    with pytest.raises(ValidationError):
        Params.model_validate({"periodo": "45"})


def test_ac7_os_valores_do_enum_sao_aceitos() -> None:
    for e in ("lote", "movimento", "comando", "recebimento", "usuario"):
        assert Params.model_validate({"entidade": e}).entidade == e
    for p in ("7", "30", "90", "365", "tudo"):
        assert Params.model_validate({"periodo": p}).periodo == p


# ------------------------------------------------------------- AC-3 · sem ação
def test_ac3_nao_ha_comando_para_editar_nem_apagar() -> None:
    """RN-D02. A ausência de `commands` é a garantia; a tela apenas não a
    contradiz."""
    comp = buscar("auditoria_trilha")
    assert comp is not None
    assert comp.commands == {}


# -------------------------------------------------------------- invariantes
async def test_ordena_do_mais_recente_para_o_mais_antigo(
    personas: dict[str, Ator],
) -> None:
    """Quem abre a trilha está investigando o que acabou de acontecer."""
    vm = await vm_de(personas["sandra"])
    assert [linha.id for linha in vm.linhas] == sorted(
        (linha.id for linha in vm.linhas), reverse=True
    )


async def test_filtra_por_ator_e_por_entidade(personas: dict[str, Ator]) -> None:
    so_helena = await vm_de(personas["sandra"], ator_id="u-helena")
    assert {linha.ator for linha in so_helena.linhas} == {"u-helena"}
    so_lote = await vm_de(personas["sandra"], entidade="lote")
    assert {linha.entidade for linha in so_lote.linhas} == {"lote"}


async def test_select_e_puro(personas: dict[str, Ator]) -> None:
    dados = await carregar(Params(), contexto(personas["sandra"]))
    assert projetar(dados) == projetar(dados)


def test_e_formulario_inteiro() -> None:
    comp = buscar("auditoria_trilha")
    assert comp is not None
    assert comp.tamanho == "inteira"
    assert comp.requires == "auditoria.ler"
