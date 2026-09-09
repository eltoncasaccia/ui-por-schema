"""T-018 · `lote_lista` — AC-1, AC-3, AC-4, AC-6, AC-7, AC-8.

O teste que mais vale aqui e' o AC-1, e ele e' negativo: Odair PEDINDO a matriz
e nao recebendo nada. Provar que Marco ve os lotes prova pouco.
"""

from typing import Any

import pytest
from fakes import MOVIMENTOS, SINAL, contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.lote_lista import Params, carregar, projetar
from estoque.domain.tipos import Lote


async def _vm(ator: Any, **params: Any) -> Any:
    return projetar(await carregar(Params(**params), contexto(ator)))


# --- AC-1 · escopo de unidade, CA-06 -------------------------------------


async def test_ac1_odair_nao_alcanca_a_matriz_nem_pedindo(personas: dict[str, Any]) -> None:
    """O param malicioso e' ignorado porque a intersecao vem antes dele.

    Este e' o caminho que um schema forjado tomaria: o componente e' legitimo,
    o ator e' legitimo, e o `unidade_id` e' de outra unidade.
    """
    vm = await _vm(personas["odair"], unidade_id="cd-matriz")
    assert vm.total == 0
    assert vm.linhas == []


async def test_ac1_odair_sem_param_ve_so_uberlandia(personas: dict[str, Any]) -> None:
    vm = await _vm(personas["odair"])
    assert vm.total > 0, "Uberlandia tem lotes; total zero esconderia a falha"
    assert {linha.unidade for linha in vm.linhas} == {"filial-uberlandia"}


async def test_ac1_ivo_e_odair_nao_veem_o_mesmo_lote(personas: dict[str, Any]) -> None:
    """Dois gerentes, escopos disjuntos: nenhum lote aparece para os dois."""
    de_ivo = {linha.lote_id for linha in (await _vm(personas["ivo"])).linhas}
    de_odair = {linha.lote_id for linha in (await _vm(personas["odair"])).linhas}
    assert de_ivo and de_odair
    assert de_ivo & de_odair == set()


# --- AC-3 · saldo e' soma de movimento, RN-M06 ---------------------------


def test_ac3_lote_nao_tem_campo_saldo() -> None:
    """RN-M06 no tipo, nao so' na consulta: se `Lote` ganhasse `saldo`, alguem
    leria dali e o numero passaria a divergir dos movimentos em silencio."""
    assert not hasattr(Lote, "saldo")
    assert "saldo" not in Lote.__slots__


async def test_ac3_saldo_confere_com_a_soma_dos_movimentos(personas: dict[str, Any]) -> None:
    vm = await _vm(personas["marco"])
    for linha in vm.linhas:
        esperado = sum(
            SINAL[m.tipo] * m.quantidade
            for m in MOVIMENTOS
            if m.lote_id == linha.lote_id and m.status == "efetivado"
        )
        assert linha.saldo == esperado, linha.lote_id


async def test_ac3_lote_com_entrada_e_saida_iguais_fica_esgotado(
    personas: dict[str, Any],
) -> None:
    """ADR-0022: `esgotado` e `vencido` nao sao coluna — saem de saldo e data."""
    vm = await _vm(personas["marco"])
    por_id = {linha.lote_id: linha for linha in vm.linhas}
    assert por_id["l-amox-zero"].saldo == 0
    assert por_id["l-amox-zero"].status == "esgotado"
    # Gravado como `liberado`, vencido de fato: o efetivo vence o registrado.
    assert por_id["l-amox-venc"].status == "vencido"


# --- AC-4 · enum fechado, risco R-5 --------------------------------------


# `model_validate` com dicionario, e nao `Params(status=...)`, porque e' assim
# que o valor chega DE VERDADE: JSON produzido pelo modelo, sem tipo nenhum.
# Escrever o literal invalido em Python faria o verificador de tipos reclamar
# de um erro que o caminho real nao tem como cometer — e a validacao em runtime,
# que e' a unica que protege aqui, deixaria de ser o que o teste exercita.
def test_ac4_status_fora_do_enum_e_rejeitado() -> None:
    """Um recorte que o modelo inventa tem de morrer na validacao, nao virar
    filtro ignorado — filtro ignorado devolve MAIS linhas, e mais linhas
    parecem uma resposta boa."""
    with pytest.raises(ValidationError):
        Params.model_validate({"status": "quase_liberado"})


def test_ac4_janela_fora_do_enum_e_rejeitada() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate({"janela": "45"})


def test_ac4_nao_existe_campo_de_busca_livre() -> None:
    """Campo de texto livre seria a porta pela qual o recorte deixa de ser
    vocabulario e vira adivinhacao."""
    livres = {"q", "busca", "termo", "texto", "filtro", "query"}
    assert not (set(Params.model_fields) & livres)


# --- AC-6 · custo invisivel, CA-05 ---------------------------------------


async def test_ac6_custo_nao_atravessa_a_rede_nem_para_quem_pode(
    personas: dict[str, Any],
) -> None:
    """Marco TEM `custo.ler`, e ainda assim nao ha custo aqui.

    E' o ponto do ADR-0020: o que o `select` nao coloca no viewmodel nao chega
    ao navegador. Custo e' de `produto_ficha` (T-019), que e' outro componente
    no catalogo — e componente ausente do catalogo nao existe para quem nao pode.
    """
    assert "custo.ler" in personas["marco"].permissoes
    bruto = (await _vm(personas["marco"])).model_dump_json()
    assert "custo" not in bruto
    assert "1250" not in bruto, "o custo do fixture vazou por outro nome"


# --- AC-7 · numero nao identifica lote, RN-L08 ---------------------------


async def test_ac7_mesmo_numero_em_unidades_diferentes_sao_dois_registros(
    personas: dict[str, Any],
) -> None:
    vm = await _vm(personas["marco"])
    mesmos = [linha for linha in vm.linhas if linha.numero == "AMX2401"]
    assert len(mesmos) == 2
    assert {linha.lote_id for linha in mesmos} == {"l-amox-mtz", "l-amox-uber"}
    assert {linha.unidade for linha in mesmos} == {"cd-matriz", "filial-uberlandia"}
    # Saldos independentes: e' o que faz somar os dois ser um bug, nao um total.
    assert len({linha.saldo for linha in mesmos}) == 2


# --- AC-8 · `select` e' puro ---------------------------------------------


async def test_ac8_select_chamado_duas_vezes_da_o_mesmo(personas: dict[str, Any]) -> None:
    """Sem I/O e sem relogio: `hoje` chega pelo `Dados`. Se o `select` lesse a
    data, duas chamadas sobre a MESMA carga poderiam divergir na virada do dia.
    """
    dados = await carregar(Params(), contexto(personas["marco"]))
    assert projetar(dados) == projetar(dados)


# --- o recorte fica visivel na resposta ----------------------------------


async def test_recorte_aplicado_aparece_no_viewmodel(personas: dict[str, Any]) -> None:
    """Contrapeso do risco R-5: um filtro esquecido devolve lista maior, e a
    tela passa a dizer qual corte ela representa."""
    vm = await _vm(personas["marco"], status="quarentena")
    assert any("Quarentena" in r for r in vm.recorte)
    assert {linha.status for linha in vm.linhas} == {"quarentena"}
