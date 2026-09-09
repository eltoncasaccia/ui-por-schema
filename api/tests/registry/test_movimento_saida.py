"""T-028 — `movimento_saida`, o lado de leitura: a proposta do FEFO.

AC-1 mora aqui. A escrita — AC-2 a AC-8 — está em
`tests/commands/test_saida_comandos.py`, contra Postgres real.

O fixture compartilhado tem dois lotes de amoxicilina na Matriz (`l-amox-mtz`
liberado, `l-amox-venc` vencido, `l-amox-zero` esgotado) e um em Uberlândia. É o
estoque montado para os casos difíceis: a proposta certa aqui é a que ignora o
vencido e o esgotado, e não a primeira da lista.
"""

from dataclasses import replace
from datetime import date, timedelta

import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.commands.entradas.saida import EntradaSaida
from estoque.application.registry.componentes.movimento_saida import (
    VM,
    Dados,
    Params,
    carregar,
    projetar,
)
from estoque.application.registry.registry import buscar, ids_permitidos
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator
from estoque.domain.regras.validade import classificar_validade
from estoque.domain.tipos import Lote

TODAS_AS_PERSONAS = ("marco", "helena", "ivo", "odair", "cleide", "rafael", "sandra")


async def vm_de(produto_id: str, ator: Ator, unidade: str | None = None) -> VM:
    params = Params.model_validate(
        {"produto_id": produto_id} | ({"unidade_id": unidade} if unidade else {})
    )
    return projetar(await carregar(params, contexto(ator)))


# --------------------------------------------------------- AC-1 · a proposta
async def test_ac1_propoe_o_liberado_de_menor_validade(personas: dict[str, Ator]) -> None:
    """RN-L02. `l-amox-venc` vence antes de todos e é o primeiro da lista
    ordenada por validade — e mesmo assim NÃO é a proposta, porque está vencido.
    Um FEFO que ordenasse sem filtrar proporia exatamente ele."""
    vm = await vm_de("p-amox", personas["ivo"], "cd-matriz")
    assert vm.proposta is not None
    assert vm.proposta.lote_id == "l-amox-mtz"
    assert vm.proposta.proposto is True
    assert vm.proposta.disponivel is True


async def test_ac1_o_vencido_e_o_esgotado_aparecem_indisponiveis(
    personas: dict[str, Ator],
) -> None:
    """Continuam na lista, com o motivo. Sumir com eles faria o operador
    procurar de novo o lote que ele viu na prateleira."""
    vm = await vm_de("p-amox", personas["ivo"], "cd-matriz")
    por_id = {c.lote_id: c for c in vm.alternativas}
    assert por_id["l-amox-venc"].disponivel is False
    assert "descarte" in (por_id["l-amox-venc"].motivo or "")
    assert por_id["l-amox-zero"].disponivel is False
    assert "saldo" in (por_id["l-amox-zero"].motivo or "").lower()


async def test_ac1_so_um_candidato_e_o_proposto(personas: dict[str, Ator]) -> None:
    vm = await vm_de("p-amox", personas["ivo"], "cd-matriz")
    propostos = [
        c for c in [*([vm.proposta] if vm.proposta else []), *vm.alternativas] if c.proposto
    ]
    assert len(propostos) == 1


def test_ac1_desempate_e_deterministico() -> None:
    """T-008 AC-3: mesma validade decide pelo id, crescente. Sem isso, a mesma
    pergunta daria respostas diferentes entre execuções — e o operador
    aprenderia a não confiar na proposta."""
    hoje = date.today()

    def lote(lote_id: str) -> Lote:
        return Lote(
            id=lote_id,
            produto_id="p-amox",
            numero=lote_id.upper(),
            unidade_id="cd-matriz",
            fabricacao=hoje - timedelta(days=100),
            validade=hoje + timedelta(days=200),
            status="liberado",
            endereco=None,
        )

    lotes = [lote("l-b"), lote("l-a")]
    d = Dados(
        lotes=lotes,
        saldos={"l-a": 10, "l-b": 10},
        produto="Amoxicilina",
        classe="antimicrobiano",
        escopo="CD Matriz",
        hoje=hoje,
        proposta_id="l-a",
    )
    vm = projetar(d)
    assert vm.proposta is not None
    assert vm.proposta.lote_id == "l-a"


async def test_ac1_sem_lote_disponivel_nao_ha_proposta(personas: dict[str, Ator]) -> None:
    """`p-rital` só tem lote bloqueado. Propor o que não pode sair seria propor
    um erro — e a tela precisa dizer que não há saída, não mostrar um botão."""
    vm = await vm_de("p-rital", personas["ivo"], "cd-matriz")
    assert vm.proposta is None
    assert vm.sem_estoque is True


# ------------------------------------------------------------- RN-C01 na tela
async def test_controlado_avisa_que_exige_autorizacao(personas: dict[str, Ator]) -> None:
    """Dito ANTES de preencher: descobrir depois que a saída ficou pendente
    lê-se como falha do sistema, e não como a regra que é."""
    vm = await vm_de("p-rital", personas["ivo"], "cd-matriz")
    assert vm.exige_autorizacao is True


async def test_nao_controlado_nao_avisa(personas: dict[str, Ator]) -> None:
    vm = await vm_de("p-amox", personas["ivo"], "cd-matriz")
    assert vm.exige_autorizacao is False


# --------------------------------------------------------- RN-M05 · motivos
async def test_os_motivos_sao_lista_fechada_e_venda_exige_destinatario(
    personas: dict[str, Ator],
) -> None:
    vm = await vm_de("p-amox", personas["ivo"], "cd-matriz")
    assert {m.valor for m in vm.motivos} == {"venda", "avaria", "furto", "erro_de_separacao"}
    exigem = {m.valor for m in vm.motivos if m.exige_destinatario}
    assert exigem == {"venda"}


async def test_motivos_de_outro_tipo_de_movimento_nao_aparecem(
    personas: dict[str, Ator],
) -> None:
    """RN-M05: a lista é fechada POR TIPO. `recebimento` é de entrada,
    `vencimento` é de descarte (RN-L06), `estorno` é outro tipo."""
    vm = await vm_de("p-amox", personas["ivo"], "cd-matriz")
    valores = {m.valor for m in vm.motivos}
    for proibido in ("recebimento", "vencimento", "estorno", "erro_de_recebimento"):
        assert proibido not in valores


def test_motivo_fora_da_lista_morre_no_schema() -> None:
    """AC-5, primeira metade. O valor entra por DICIONÁRIO, que é como ele chega
    de verdade — JSON, sem tipo nenhum."""
    with pytest.raises(ValidationError):
        EntradaSaida.model_validate({"lote_id": "l-x", "quantidade": 1, "motivo": "vencimento"})
    with pytest.raises(ValidationError):
        EntradaSaida.model_validate({"lote_id": "l-x", "quantidade": 1, "motivo": ""})


def test_complemento_sozinho_nao_substitui_o_motivo() -> None:
    """AC-5, segunda metade — e é a que a regra realmente pede. `RN-M05`: texto
    livre é complemento, NUNCA substituto."""
    with pytest.raises(ValidationError):
        EntradaSaida.model_validate(
            {"lote_id": "l-x", "quantidade": 1, "complemento": "saiu para o cliente"}
        )


def test_venda_sem_cliente_ou_nota_e_recusada() -> None:
    """AC-8. Sem cliente e nota, a pergunta "quem recebeu este lote?" não tem
    resposta — e ela é o `CA-01`, em menos de 60 segundos."""
    base = {"lote_id": "l-x", "quantidade": 1, "motivo": "venda"}
    with pytest.raises(ValidationError):
        EntradaSaida.model_validate(base)
    with pytest.raises(ValidationError):
        EntradaSaida.model_validate(base | {"cliente_id": "c-1"})
    with pytest.raises(ValidationError):
        EntradaSaida.model_validate(base | {"nota_fiscal": "NF-1"})
    # O par positivo: com os dois, passa.
    e = EntradaSaida.model_validate(base | {"cliente_id": "c-1", "nota_fiscal": "NF-1"})
    assert e.cliente_id == "c-1"


def test_avaria_nao_exige_destinatario() -> None:
    """O par negativo: exigir cliente numa avaria seria ruído, e ruído ensina a
    preencher qualquer coisa."""
    e = EntradaSaida.model_validate({"lote_id": "l-x", "quantidade": 1, "motivo": "avaria"})
    assert e.cliente_id is None


def test_quantidade_precisa_ser_positiva() -> None:
    """O sinal vem do TIPO do movimento, nunca do número (CONTRATOS §3).
    Quantidade negativa seria uma entrada disfarçada de saída."""
    for q in (0, -5):
        with pytest.raises(ValidationError):
            EntradaSaida.model_validate({"lote_id": "l-x", "quantidade": q, "motivo": "avaria"})


# --------------------------------------------------------- escopo e catálogo
async def test_escopo_de_unidade_e_aplicado(personas: dict[str, Ator]) -> None:
    """RN-A01. Odair só alcança Uberlândia: os lotes da Matriz não entram na
    lista dele, e portanto não entram na proposta."""
    vm = await vm_de("p-amox", personas["odair"])
    ids = {c.lote_id for c in [*([vm.proposta] if vm.proposta else []), *vm.alternativas]}
    assert ids == {"l-amox-uber"}


async def test_produto_inexistente_e_fora_de_escopo_sao_indistinguiveis(
    personas: dict[str, Ator],
) -> None:
    def face(err: ErroDominio) -> tuple[str, str, str]:
        return (err.codigo, err.mensagem_publica, repr(err))

    with pytest.raises(ErroDominio) as inexistente:
        await vm_de("p-nao-existe", personas["odair"])
    assert inexistente.value.codigo == "nao_encontrado"
    assert face(inexistente.value)[1] == "Registro nao encontrado."


def test_quem_nao_pode_criar_movimento_nao_ve_o_componente(
    personas: dict[str, Ator],
) -> None:
    """ADR-0003. Rafael (comprador) e Sandra (auditoria) não criam movimento;
    Marco (diretor) também não — papel não é nível."""
    for nome in TODAS_AS_PERSONAS:
        ator = personas[nome]
        esperado = "movimento.criar" in ator.permissoes
        assert ("movimento_saida" in ids_permitidos(ator)) is esperado, nome
    for nome in ("marco", "rafael", "sandra", "helena"):
        assert "movimento_saida" not in ids_permitidos(personas[nome]), nome


def test_recem_cadastrado_e_inativo_nao_veem(
    recem_cadastrado: Ator, personas: dict[str, Ator]
) -> None:
    assert "movimento_saida" not in ids_permitidos(recem_cadastrado)
    assert "movimento_saida" not in ids_permitidos(replace(personas["ivo"], ativo=False))


# -------------------------------------------------------------- invariantes
async def test_custo_nao_atravessa_a_rede(personas: dict[str, Ator]) -> None:
    """CA-05. O fixture TEM custo de propósito."""
    vm = await vm_de("p-amox", personas["ivo"], "cd-matriz")
    bruto = vm.model_dump_json()
    assert "custo" not in bruto
    assert "1250" not in bruto


async def test_select_e_puro(personas: dict[str, Ator]) -> None:
    dados = await carregar(Params(produto_id="p-amox"), contexto(personas["ivo"]))
    assert projetar(dados) == projetar(dados)


def test_o_componente_declara_o_comando_e_e_formulario_inteiro() -> None:
    comp = buscar("movimento_saida")
    assert comp is not None
    assert comp.tamanho == "inteira"
    assert set(comp.commands) == {"movimento_saida"}
    assert comp.commands["movimento_saida"].idempotent is False
    assert comp.commands["movimento_saida"].confirm is True


# ----------------------------------------------- RN-L05 na proposta (achado A-21)
def _dados_com(dias_proposta: int, dias_outro: int) -> Dados:
    """Dois lotes liberados do mesmo produto, com validades sob medida."""
    hoje = date.today()

    def lote(lote_id: str, dias: int) -> Lote:
        return Lote(
            id=lote_id,
            produto_id="p-amox",
            numero=lote_id.upper(),
            unidade_id="cd-matriz",
            fabricacao=hoje - timedelta(days=300),
            validade=hoje + timedelta(days=dias),
            status="liberado",
            endereco=None,
        )

    lotes = [lote("l-perto", dias_proposta), lote("l-longe", dias_outro)]
    from estoque.domain.regras.fefo import propor_fefo

    saldos = {"l-perto": 50, "l-longe": 50}
    vendaveis = [x for x in lotes if classificar_validade(x, hoje) != "bloqueio_30"]
    proposta = propor_fefo(vendaveis, saldos, hoje)
    return Dados(
        lotes=lotes,
        saldos=saldos,
        produto="Amoxicilina 500mg",
        classe="antimicrobiano",
        escopo="CD Matriz",
        hoje=hoje,
        proposta_id=proposta.id if proposta else None,
    )


def test_a21_lote_na_janela_de_30_dias_nao_e_proposto() -> None:
    """RN-L02 × RN-L05. O FEFO puro proporia `l-perto` — é o de menor validade.

    Mas ele está a 20 dias do vencimento, e `RN-L05` bloqueia a venda até o RT
    liberar. Propor esse lote seria o sistema propondo o que ele mesmo recusa, e
    ainda cobrando justificativa de quem escolhesse o lote certo.
    """
    vm = projetar(_dados_com(dias_proposta=20, dias_outro=200))
    assert vm.proposta is not None
    assert vm.proposta.lote_id == "l-longe"


def test_a21_o_lote_da_janela_aparece_com_o_motivo() -> None:
    """Não some da lista: o operador precisa saber que ele existe e o que falta."""
    vm = projetar(_dados_com(dias_proposta=20, dias_outro=200))
    perto = next(c for c in vm.alternativas if c.lote_id == "l-perto")
    assert perto.disponivel is False
    assert perto.exige_liberacao_rt is True
    assert "RN-L05" in (perto.motivo or "")


def test_a21_fora_da_janela_o_fefo_puro_vale() -> None:
    """O par negativo: sem ele, um filtro que descartasse tudo passaria acima."""
    vm = projetar(_dados_com(dias_proposta=40, dias_outro=200))
    assert vm.proposta is not None
    assert vm.proposta.lote_id == "l-perto"
    assert vm.proposta.exige_liberacao_rt is False


def test_a21_fronteira_de_30_dias_na_proposta() -> None:
    """30 dias ainda é janela; 31 já não é."""
    assert projetar(_dados_com(30, 200)).proposta.lote_id == "l-longe"  # type: ignore[union-attr]
    assert projetar(_dados_com(31, 200)).proposta.lote_id == "l-perto"  # type: ignore[union-attr]
