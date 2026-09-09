"""T-027 — `lote_status_acao`, as três transições privativas do RT.

A pergunta que o componente responde é *o que eu posso fazer com este lote
agora?*, e a resposta sai da tabela §4.1 avaliada no servidor. Aqui se prova que
a avaliação bate com a tabela — inclusive nas negativas, que são a maioria: de
qualquer estado, duas das três ações não se aplicam.
"""

from dataclasses import replace
from datetime import date

import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.commands.entradas.lote import EntradaStatus
from estoque.application.registry.componentes.lote_status_acao import (
    VM,
    Dados,
    Params,
    carregar,
    projetar,
)
from estoque.application.registry.registry import buscar, ids_permitidos
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator
from estoque.domain.tipos import Lote

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")


async def vm_de(lote_id: str, ator: Ator) -> VM:
    return projetar(await carregar(Params(lote_id=lote_id), contexto(ator)))


def disponiveis(vm: VM) -> set[str]:
    return {a.acao for a in vm.acoes if a.disponivel}


# ------------------------------------------------------ AC-2 · catálogo (ADR-0003)
def test_ac2_so_o_rt_ve_o_componente(personas: dict[str, Ator]) -> None:
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "lote.status" in ator.permissoes
        assert ("lote_status_acao" in ids_permitidos(ator)) is esperado, nome
    assert "lote_status_acao" in ids_permitidos(personas["helena"])


def test_ac2_os_outros_seis_papeis_nao_veem(personas: dict[str, Ator]) -> None:
    """O negativo enumerado, papel a papel. Um `for` que não afirma nada sobre
    quem NÃO pode passaria com um catálogo aberto para todo mundo."""
    for nome in ("marco", "ivo", "odair", "cleide", "rafael", "sandra"):
        assert "lote_status_acao" not in ids_permitidos(personas[nome]), nome


def test_ac2_recem_cadastrado_e_inativo_nao_veem(
    recem_cadastrado: Ator, personas: dict[str, Ator]
) -> None:
    assert "lote_status_acao" not in ids_permitidos(recem_cadastrado)
    assert "lote_status_acao" not in ids_permitidos(replace(personas["helena"], ativo=False))


# ------------------------------------------------- AC-5 · a tabela §4.1, avaliada
async def test_lote_liberado_so_permite_bloquear(personas: dict[str, Ator]) -> None:
    """§4.1: de `Liberado` sai `bloqueio`. Desbloquear não se aplica — e
    `liberar_vencimento` só entra dentro da janela de 30 dias (RN-L05)."""
    vm = await vm_de("l-amox-mtz", personas["helena"])
    assert vm.status == "liberado"
    assert disponiveis(vm) == {"bloquear"}


async def test_lote_bloqueado_so_permite_desbloquear(personas: dict[str, Ator]) -> None:
    vm = await vm_de("l-rital-bloq", personas["helena"])
    assert vm.status == "bloqueado"
    assert disponiveis(vm) == {"desbloquear"}


async def test_lote_em_quarentena_nao_permite_nenhuma_das_tres(
    personas: dict[str, Ator],
) -> None:
    """A quarentena sai por `quarentena_liberar`, não por aqui. Se `bloquear`
    aparecesse, haveria dois caminhos para o mesmo estado, com regras
    diferentes — e um deles sem checklist."""
    vm = await vm_de("l-vac-quar", personas["helena"])
    assert disponiveis(vm) == set()


async def test_toda_acao_indisponivel_diz_por_que(personas: dict[str, Ator]) -> None:
    """Botão morto sem explicação lê-se como sistema quebrado."""
    vm = await vm_de("l-vac-quar", personas["helena"])
    for a in vm.acoes:
        assert a.disponivel is False
        assert a.motivo, a.acao


# ------------------------------------------------ AC-6 · liberar_vencimento (RN-L05)
def _dados(dias: int, status: str = "liberado") -> Dados:
    """Um lote sob medida, sem tocar em `fakes.py`.

    A janela de 30 dias não tem representante no fixture compartilhado, e
    acrescentar um lote lá mudaria as contagens de outros testes. `projetar` é
    puro: alimentá-lo direto é o jeito honesto de exercitar a fronteira.
    """
    from datetime import timedelta

    hoje = date.today()
    lote = Lote(
        id="l-janela",
        produto_id="p-amox",
        numero="AMX3001",
        unidade_id="cd-matriz",
        fabricacao=hoje - timedelta(days=200),
        validade=hoje + timedelta(days=dias),
        status=status,  # type: ignore[arg-type]
        endereco="A-01",
    )
    return Dados(lote=lote, produto="Amoxicilina 500mg", saldo=40, hoje=hoje, papel="rt")


def test_ac6_liberar_vencimento_disponivel_dentro_da_janela() -> None:
    """RN-L05: 20 dias para vencer, lote liberado — é o caso da regra."""
    vm = projetar(_dados(20))
    assert vm.situacao == "bloqueio_30"
    assert disponiveis(vm) == {"bloquear", "liberar_vencimento"}


def test_ac6_fronteira_de_30_dias() -> None:
    """30 dias entra, 31 não. A fronteira é onde a regra costuma ser escrita
    errada, e o teste que a fixa é o que impede o `<` virar `<=` sem ninguém
    perceber."""
    assert "liberar_vencimento" in disponiveis(projetar(_dados(30)))
    assert "liberar_vencimento" not in disponiveis(projetar(_dados(31)))


def test_ac6_lote_ja_vencido_nao_pode_ser_liberado() -> None:
    """RN-L06 é mais forte que RN-L05: vencido não sai por nenhum motivo,
    exceto descarte. Um botão aqui prometeria o que a regra proíbe."""
    vm = projetar(_dados(-1))
    assert vm.situacao == "vencido"
    assert "liberar_vencimento" not in disponiveis(vm)
    motivo = next(a.motivo for a in vm.acoes if a.acao == "liberar_vencimento")
    assert motivo is not None
    assert "RN-L06" in motivo


async def test_liberar_vencimento_indisponivel_fora_da_janela(
    personas: dict[str, Ator],
) -> None:
    """O par negativo, e o que dá sentido ao teste acima: `l-amox-mtz` vence
    daqui a muito tempo, e não há bloqueio por validade a liberar."""
    vm = await vm_de("l-amox-mtz", personas["helena"])
    assert vm.situacao == "ok"
    assert "liberar_vencimento" not in disponiveis(vm)
    motivo = next(a.motivo for a in vm.acoes if a.acao == "liberar_vencimento")
    assert motivo is not None
    assert "30 dias" in motivo


async def test_liberar_vencimento_nao_se_aplica_a_lote_bloqueado(
    personas: dict[str, Ator],
) -> None:
    """Liberar a validade de um lote bloqueado não o tornaria vendável, e daria
    a impressão contrária a quem clicou."""
    vm = await vm_de("l-rital-bloq", personas["helena"])
    assert "liberar_vencimento" not in disponiveis(vm)


# ------------------------------------------------------- AC-8 · enum fechado
def test_ac8_acao_fora_do_enum_e_rejeitada_no_schema() -> None:
    """O valor inválido entra por DICIONÁRIO, que é como ele chega de verdade —
    JSON do modelo, sem tipo nenhum."""
    with pytest.raises(ValidationError):
        EntradaStatus.model_validate(
            {"lote_id": "l-x", "acao": "descartar", "justificativa": "x" * 12}
        )
    with pytest.raises(ValidationError):
        EntradaStatus.model_validate({"lote_id": "l-x", "acao": "", "justificativa": "x" * 12})


def test_ac8_as_tres_acoes_do_enum_sao_aceitas() -> None:
    """O par positivo: sem ele, um enum vazio passaria no teste acima."""
    for acao in ("bloquear", "desbloquear", "liberar_vencimento"):
        e = EntradaStatus.model_validate(
            {"lote_id": "l-x", "acao": acao, "justificativa": "motivo suficiente"}
        )
        assert e.acao == acao


def test_justificativa_vazia_e_rejeitada_no_schema() -> None:
    with pytest.raises(ValidationError):
        EntradaStatus.model_validate(
            {"lote_id": "l-x", "acao": "bloquear", "justificativa": ""}
        )


# --------------------------------------------------------- escopo e negativa
async def test_fora_de_escopo_e_inexistente_sao_indistinguiveis(
    personas: dict[str, Ator],
) -> None:
    def face(err: ErroDominio) -> tuple[str, str, str]:
        return (err.codigo, err.mensagem_publica, repr(err))

    with pytest.raises(ErroDominio) as fora:
        await vm_de("l-amox-mtz", personas["odair"])
    with pytest.raises(ErroDominio) as inexistente:
        await vm_de("l-nao-existe", personas["odair"])
    assert face(fora.value) == face(inexistente.value)


# -------------------------------------------------------------- invariantes
async def test_mostra_os_dois_status(personas: dict[str, Ator]) -> None:
    """ADR-0022: `l-amox-venc` está `liberado` no banco e vencido de fato."""
    vm = await vm_de("l-amox-venc", personas["helena"])
    assert vm.status == "liberado"
    assert vm.status_efetivo == "vencido"


async def test_custo_nao_atravessa_a_rede(personas: dict[str, Ator]) -> None:
    vm = await vm_de("l-amox-mtz", personas["helena"])
    bruto = vm.model_dump_json()
    assert "custo" not in bruto
    assert "1250" not in bruto


async def test_select_e_puro(personas: dict[str, Ator]) -> None:
    dados = await carregar(Params(lote_id="l-amox-mtz"), contexto(personas["helena"]))
    assert projetar(dados) == projetar(dados)


def test_o_componente_declara_o_comando_e_e_formulario_inteiro() -> None:
    comp = buscar("lote_status_acao")
    assert comp is not None
    assert comp.tamanho == "inteira"
    assert set(comp.commands) == {"lote_status"}
    assert comp.commands["lote_status"].requires == "lote.status"
