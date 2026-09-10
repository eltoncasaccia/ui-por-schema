"""T-029 — `movimento_descarte`, o lado de leitura: a fila do que só sai por
descarte, e o aviso para o que não sai por aí.

O fluxo de escrita — AC-6, AC-7 e a dupla identificação — está em
`tests/commands/test_descarte_comandos.py`, contra Postgres real. Aqui prova-se a
fila, que é derivada do status EFETIVO (ADR-0022) e não do registrado: um lote
`liberado` no banco que passou da validade é `vencido` neste instante, e é
exatamente ele que precisa sair da prateleira.

O estoque falso traz os três casos (ver `fakes.py`):

  l-amox-venc      liberado no banco, vencido de fato
  l-vac-quar-venc  venceu DENTRO da quarentena — o pior caso
  l-rital-bloq     bloqueado por decisão humana, e ainda válido
"""

from dataclasses import replace

import pytest
from fakes import contexto

from estoque.application.commands.entradas.descarte import EntradaDescarte
from estoque.application.registry.componentes.movimento_descarte import (
    DESCARTAVEIS,
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

VENCIDO = "l-amox-venc"
VENCIDO_NA_QUARENTENA = "l-vac-quar-venc"
BLOQUEADO = "l-rital-bloq"
LIBERADO = "l-amox-mtz"  # liberado E válido — o caso do AC-6
ESGOTADO = "l-amox-zero"  # saldo zero: nada a descartar


async def _vm(ator: Ator, lote_id: str | None = None) -> object:
    return projetar(await carregar(Params(lote_id=lote_id), contexto(ator)))


# ------------------------------------------------- catálogo por ator (ADR-0003)
def test_so_quem_descarta_ve_o_componente(personas: dict[str, Ator]) -> None:
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        pode = {"movimento.descartar", "lote.ler"} <= set(ator.permissoes)
        assert ("movimento_descarte" in ids_permitidos(ator)) is pode, nome


def test_quem_le_lote_nao_descarta_por_isso(personas: dict[str, Ator]) -> None:
    """Os sete papéis têm `lote.ler`; três não têm `movimento.descartar`. Se a
    exigência fosse "qualquer uma", o comprador veria a fila de descarte."""
    for nome in ("cleide", "rafael", "sandra"):
        ator = personas[nome]
        assert "lote.ler" in ator.permissoes, nome
        assert "movimento_descarte" not in ids_permitidos(ator), nome


def test_recem_cadastrado_e_inativo_nao_veem(
    recem_cadastrado: Ator, personas: dict[str, Ator]
) -> None:
    assert "movimento_descarte" not in ids_permitidos(recem_cadastrado)
    assert "movimento_descarte" not in ids_permitidos(replace(personas["ivo"], ativo=False))


# ------------------------------------------------------------------- a fila
async def test_a_fila_traz_vencidos_e_bloqueados(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["ivo"])
    ids = [linha.lote_id for linha in vm.fila]  # type: ignore[attr-defined]
    assert VENCIDO in ids
    assert VENCIDO_NA_QUARENTENA in ids
    assert BLOQUEADO in ids


async def test_a_fila_nao_traz_lote_bom_nem_esgotado(personas: dict[str, Ator]) -> None:
    """O par negativo da fila. Sem ele, uma fila que listasse tudo passaria no
    teste de cima — e descarte deixaria de ser exceção."""
    vm = await _vm(personas["ivo"])
    ids = [linha.lote_id for linha in vm.fila]  # type: ignore[attr-defined]
    assert LIBERADO not in ids
    assert ESGOTADO not in ids


async def test_a_fila_e_por_status_efetivo_e_nao_pelo_registrado(
    personas: dict[str, Ator],
) -> None:
    """ADR-0022. `l-amox-venc` está `liberado` na coluna e vencido na data; um
    filtro por status registrado o deixaria de fora justamente por ele parecer
    normal no banco."""
    vm = await _vm(personas["ivo"])
    linha = next(x for x in vm.fila if x.lote_id == VENCIDO)  # type: ignore[attr-defined]
    assert linha.status_efetivo == "vencido"
    assert linha.dias_restantes < 0


async def test_a_ordem_e_do_que_venceu_ha_mais_tempo(personas: dict[str, Ator]) -> None:
    """É o que está parado ocupando endereço, e o que uma inspeção encontra
    antes."""
    vm = await _vm(personas["ivo"])
    dias = [linha.dias_restantes for linha in vm.fila]  # type: ignore[attr-defined]
    assert dias == sorted(dias)


async def test_a_fila_respeita_o_escopo(personas: dict[str, Ator]) -> None:
    """RN-A01: Odair é gerente, tem `movimento.descartar`, e não alcança a
    Matriz. A fila dele não tem os vencidos de lá.

    A comparação com a fila de Ivo é o que dá peso à asserção: uma fila vazia
    para todo mundo — por um `load` quebrado, por exemplo — passaria num teste
    que só olhasse Odair.
    """
    de_ivo = await _vm(personas["ivo"])
    de_odair = await _vm(personas["odair"])

    assert [linha.lote_id for linha in de_ivo.fila]  # type: ignore[attr-defined]
    ids = [linha.lote_id for linha in de_odair.fila]  # type: ignore[attr-defined]
    assert VENCIDO not in ids
    assert VENCIDO_NA_QUARENTENA not in ids
    assert BLOQUEADO not in ids
    for linha in de_odair.fila:  # type: ignore[attr-defined]
        assert linha.unidade == "Uberlândia", linha.lote_id


async def test_o_escopo_aparece_no_viewmodel(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["odair"])
    assert vm.escopo == "1 unidade"  # type: ignore[attr-defined]


# ------------------------------------------------- AC-6 na tela · o alvo
async def test_ac6_lote_liberado_e_valido_vem_com_impedimento(
    personas: dict[str, Ator],
) -> None:
    """A tela avisa; o servidor recusa de novo (`RN-A03`). Descarte não é atalho
    de saída — a saída de mercadoria boa tem cliente e nota fiscal."""
    vm = await _vm(personas["ivo"], LIBERADO)
    assert vm.alvo is not None  # type: ignore[attr-defined]
    assert vm.alvo.pode_descartar is False  # type: ignore[attr-defined]
    assert "RN-L06" in (vm.alvo.impedimento or "")  # type: ignore[attr-defined]


async def test_o_alvo_vencido_pode(personas: dict[str, Ator]) -> None:
    """O par positivo: sem ele, uma tela que impedisse tudo passaria."""
    vm = await _vm(personas["ivo"], VENCIDO)
    assert vm.alvo is not None  # type: ignore[attr-defined]
    assert vm.alvo.pode_descartar is True  # type: ignore[attr-defined]
    assert vm.alvo.impedimento is None  # type: ignore[attr-defined]


async def test_o_alvo_esgotado_nao_pode(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["ivo"], ESGOTADO)
    assert vm.alvo is not None  # type: ignore[attr-defined]
    assert vm.alvo.pode_descartar is False  # type: ignore[attr-defined]


async def test_sem_lote_id_nao_ha_formulario(personas: dict[str, Ator]) -> None:
    vm = await _vm(personas["ivo"])
    assert vm.alvo is None  # type: ignore[attr-defined]
    assert vm.total > 0  # type: ignore[attr-defined]


async def test_a_tela_diz_que_sao_duas_assinaturas(personas: dict[str, Ator]) -> None:
    """§4.1 — Gerente + RT, dito ANTES de preencher: descobrir na recusa que
    faltava a segunda assinatura lê-se como falha do sistema."""
    vm = await _vm(personas["ivo"], VENCIDO)
    assert vm.exige_dupla_identificacao is True  # type: ignore[attr-defined]


async def test_lote_fora_do_escopo_e_indistinguivel_de_inexistente(
    personas: dict[str, Ator],
) -> None:
    with pytest.raises(ErroDominio) as fora:
        await _vm(personas["odair"], VENCIDO)
    with pytest.raises(ErroDominio) as inexistente:
        await _vm(personas["odair"], "l-nao-existe")
    assert fora.value.codigo == inexistente.value.codigo == "nao_encontrado"
    assert fora.value.mensagem_publica == inexistente.value.mensagem_publica


# ------------------------------------------------------------------ schema
def test_motivo_fora_da_lista_e_rejeitado() -> None:
    """RN-M05. `furto` é motivo de SAÍDA — quem some com mercadoria não a
    descarta."""
    with pytest.raises(Exception):  # noqa: B017
        EntradaDescarte.model_validate(
            {
                "lote_id": VENCIDO,
                "motivo": "furto",
                "justificativa": "x" * 12,
                "segunda_identificacao_id": "u-helena",
            }
        )


def test_sem_segunda_identificacao_o_schema_rejeita() -> None:
    """§4.1 exige duas assinaturas, e o campo não é opcional: um descarte com
    uma identidade só não chega a ser avaliado pelo comando."""
    with pytest.raises(Exception):  # noqa: B017
        EntradaDescarte.model_validate(
            {"lote_id": VENCIDO, "motivo": "vencimento", "justificativa": "x" * 12}
        )


def test_justificativa_vazia_e_rejeitada() -> None:
    with pytest.raises(Exception):  # noqa: B017
        EntradaDescarte.model_validate(
            {
                "lote_id": VENCIDO,
                "motivo": "vencimento",
                "justificativa": "",
                "segunda_identificacao_id": "u-helena",
            }
        )


def test_a_entrada_completa_e_aceita() -> None:
    e = EntradaDescarte.model_validate(
        {
            "lote_id": VENCIDO,
            "motivo": "avaria",
            "justificativa": "embalagem violada no transporte",
            "segunda_identificacao_id": "u-helena",
        }
    )
    assert e.motivo == "avaria"
    assert e.segunda_identificacao_id == "u-helena"


def test_todo_motivo_tem_rotulo_na_tela() -> None:
    from typing import get_args

    from estoque.application.commands.entradas.descarte import MotivoDescarte

    assert set(ROTULO_MOTIVO) == set(get_args(MotivoDescarte))


def test_a_lista_de_estados_descartaveis_e_a_mesma_dos_dois_lados() -> None:
    """O componente não pode importar `commands.descarte` (contrato 2 do
    import-linter: sqlalchemy no caminho), então a lista existe duas vezes. Este
    teste é o que impede as duas de divergirem (achado A-11)."""
    from estoque.application.commands import descarte as comando

    assert comando.DESCARTAVEIS == DESCARTAVEIS


# -------------------------------------------------------------- invariantes
async def test_custo_nao_atravessa_a_rede(personas: dict[str, Ator]) -> None:
    for nome in ("marco", "ivo"):
        vm = await _vm(personas[nome])
        assert "custo" not in vm.model_dump_json()  # type: ignore[attr-defined]


async def test_select_e_puro(personas: dict[str, Ator]) -> None:
    dados = await carregar(Params(lote_id=VENCIDO), contexto(personas["ivo"]))
    assert projetar(dados) == projetar(dados)


def test_o_componente_e_formulario_inteiro() -> None:
    comp = buscar("movimento_descarte")
    assert comp is not None
    assert comp.tamanho == "inteira"  # ADR-0005
    assert comp.requires == ("movimento.descartar", "lote.ler")


def test_o_command_def_publicado_nao_carrega_funcao() -> None:
    comp = buscar("movimento_descarte")
    assert comp is not None
    cd = comp.commands["movimento_descarte"]
    assert isinstance(cd, CommandDef)
    assert not hasattr(cd, "aplicar")
    assert cd.confirm is True
    assert cd.endpoint == "/api/comandos/movimento_descarte"
