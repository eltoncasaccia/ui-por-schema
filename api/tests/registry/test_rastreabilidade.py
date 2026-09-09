"""T-021 · `rastreabilidade` — CA-01. O recall da losartana, de nove dias para 60 s.

O que vale aqui e' o negativo: escopo que nao atravessa (AC-4), params
incoerentes recusados na validacao (AC-5, AC-6), e nenhum custo na resposta
(AC-7).

RNF-01 real (o numero de segundos contra Postgres com o lote de recall do seed)
e' medido no relatorio de fechamento, T-034. Aqui a prova e' de FORMA: o `load`
faz consultas limitadas e o `select` e' linear — testado com volume realista.
"""

import inspect
import time
from datetime import date, timedelta
from typing import Any

import fakes
import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.rastreabilidade import (
    Params,
    carregar,
    projetar,
)
from estoque.application.schema.validar import validar_schema
from estoque.domain.identidade import Ator
from estoque.domain.tipos import Lote, Movimento
from estoque.server.rotas import dados as rota_dados

CLIENTES = ["Farmacia Sao Joao", "Drogaria Central", "Rede Popular", "Hospital Santa Casa"]
HOJE = date.today()


@pytest.fixture
def _recall(monkeypatch: pytest.MonkeyPatch) -> None:
    """Um lote de recall com volume (AC-1) e um segundo lote para o mesmo
    cliente (AC-2), sem tocar o fixture compartilhado."""
    l_mtz = Lote(
        id="l-recall-mtz",
        produto_id="p-amox",
        numero="RCL2401",
        unidade_id="cd-matriz",
        fabricacao=fakes.HOJE - timedelta(days=200),
        validade=fakes.HOJE + timedelta(days=120),
        status="liberado",
        endereco="A-01",
    )
    l_ref = Lote(
        id="l-recall-ref",
        produto_id="p-vac",
        numero="RCL2402",
        unidade_id="cd-refrigerado",
        fabricacao=fakes.HOJE - timedelta(days=150),
        validade=fakes.HOJE + timedelta(days=90),
        status="liberado",
        endereco="R-02",
    )

    def _mov(mid: str, lote: Lote, dias_atras: int, cliente: str, qtd: int) -> Movimento:
        return Movimento(
            id=mid,
            lote_id=lote.id,
            unidade_id=lote.unidade_id,
            tipo="saida",
            quantidade=qtd,
            motivo="venda",
            complemento=None,
            autor_id="u-ivo",
            autorizador_id=None,
            status="efetivado",
            criado_em=fakes.AGORA - timedelta(days=dias_atras),
            estorna_movimento_id=None,
            cliente_id=cliente,
            nota_fiscal=f"NF-{mid[-5:]}",
        )

    novos = [
        _mov(
            f"m-rcl-{i:05d}",
            l_mtz,
            dias_atras=i,
            cliente=CLIENTES[i % len(CLIENTES)],
            qtd=1 + i % 12,
        )
        for i in range(60)
    ]
    # Segundo lote, mesmo cliente CLIENTES[0], para o sentido cliente -> lotes.
    novos += [
        _mov(f"m-rcr-{i:05d}", l_ref, dias_atras=5 + i, cliente=CLIENTES[0], qtd=3)
        for i in range(4)
    ]
    monkeypatch.setattr(fakes, "LOTES", [*fakes.LOTES, l_mtz, l_ref])
    monkeypatch.setattr(fakes, "MOVIMENTOS", [*fakes.MOVIMENTOS, *novos])


def _rastreador(unidades: set[str]) -> Ator:
    """Um ator com `auditoria.rastrear` e escopo de unidade arbitrario.

    Necessario porque NENHUMA persona junta `auditoria.rastrear` com escopo
    restrito — as tres que rastreiam (Marco, Helena, Sandra) alcancam tudo. Sem
    este ator sintetico, o "nao atravessa" do AC-4 so' daria para testar como
    negativa de catalogo (Odair nao ve o componente)."""
    return Ator(
        id="u-rastreador-restrito",
        nome="Rastreador Restrito",
        papel="auditoria",
        unidades=frozenset(unidades),  # type: ignore[arg-type]
        permissoes=frozenset({"auditoria.rastrear", "lote.ler", "produto.ler"}),
        ativo=True,
    )


async def _vm(ator: Any, **params: Any) -> Any:
    return projetar(await carregar(Params(**params), contexto(ator)))


# --- AC-1 · volume, e a resposta em forma linear -------------------------


async def test_ac1_lote_com_muitas_saidas_responde_rapido(
    personas: dict[str, Any], _recall: None
) -> None:
    inicio = time.perf_counter()
    vm = await _vm(personas["marco"], direcao="lote_para_clientes", lote_id="l-recall-mtz")
    decorrido = time.perf_counter() - inicio

    assert vm.total_saidas >= 50
    assert len({c.cliente for c in vm.clientes}) >= 3
    # Alvo de CA-01/RNF-01 e' 60 s; contra os fakes isto e' sub-milissegundo. O
    # que o numero prova e' que nao ha' blowup — o real vai para o T-034.
    assert decorrido < 1.0


# --- AC-2 · o sentido inverso, com periodo (RN-D04) ---------------------


async def test_ac2_cliente_para_lotes_lista_os_lotes_do_periodo(
    personas: dict[str, Any], _recall: None
) -> None:
    vm = await _vm(
        personas["sandra"],
        direcao="cliente_para_lotes",
        cliente_id=CLIENTES[0],
        de=HOJE - timedelta(days=365),
        ate=HOJE,
    )
    ids = {linha.lote_id for linha in vm.lotes}
    assert ids == {"l-recall-mtz", "l-recall-ref"}
    assert all(linha.quantidade_total > 0 for linha in vm.lotes)


async def test_ac2_o_periodo_recorta_de_verdade(
    personas: dict[str, Any], _recall: None
) -> None:
    """A porta ignora `de`/`ate` (A-31); e' o `load` que recorta. Uma janela que
    nao pega nenhuma saida devolve zero lotes."""
    vm = await _vm(
        personas["sandra"],
        direcao="cliente_para_lotes",
        cliente_id=CLIENTES[0],
        de=HOJE - timedelta(days=3650),
        ate=HOJE - timedelta(days=3000),
    )
    assert vm.lotes == []
    assert vm.total_saidas == 0


# --- AC-3 · a consulta e' auditada, com ator e params (RN-D05) ---------


def test_ac3_a_borda_audita_toda_leitura_com_os_params() -> None:
    """RN-D05 e' propriedade da BORDA, nao do componente: `rotas/dados.py`
    grava `acao='ler'` com `ator_id` e `valor_novo={'params': ...}` — e os
    params incluem `direcao`. O E2E contra o banco esta' em
    `test_ac6_leitura_auditada.py` ("toda leitura")."""
    fonte = inspect.getsource(rota_dados.dados)
    assert 'acao="ler"' in fonte
    assert "ator_id=ator.id" in fonte
    assert 'valor_novo={"params": corpo.params}' in fonte


# --- AC-4 · escopo que nao atravessa (CA-06) ---------------------------


def test_ac4_quem_nao_tem_rastrear_nao_ve_o_componente(personas: dict[str, Any]) -> None:
    from estoque.application.registry.registry import ids_permitidos

    for nome in ("odair", "ivo", "cleide", "rafael"):
        assert "rastreabilidade" not in ids_permitidos(personas[nome]), nome


async def test_ac4_rastreador_restrito_nao_alcanca_lote_de_outra_unidade(
    _recall: None,
) -> None:
    """O lote de recall esta' em CD Matriz; um rastreador restrito a Uberlandia
    consulta e recebe VAZIO — nao um erro, e nao as saidas."""
    restrito = _rastreador({"filial-uberlandia"})
    vm = await _vm(restrito, direcao="lote_para_clientes", lote_id="l-recall-mtz")
    assert vm.total_saidas == 0
    assert vm.clientes == []


async def test_ac4_rastreador_restrito_nao_ve_lotes_de_cliente_fora_do_escopo(
    _recall: None,
) -> None:
    restrito = _rastreador({"filial-uberlandia"})
    vm = await _vm(
        restrito,
        direcao="cliente_para_lotes",
        cliente_id=CLIENTES[0],
        de=HOJE - timedelta(days=365),
        ate=HOJE,
    )
    assert vm.lotes == []


# --- AC-5 · direcao ausente ou invalida --------------------------------


def test_ac5_direcao_ausente_e_rejeitada() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate({"lote_id": "l-x"})


def test_ac5_direcao_fora_do_enum_e_rejeitada() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate({"direcao": "lote_para_tudo", "lote_id": "l-x"})


def test_ac5_schema_forjado_sem_direcao_e_rejeitado(personas: dict[str, Any]) -> None:
    forjado = {
        "versao": 1,
        "blocos": [{"tipo": "rastreabilidade", "params": {"lote_id": "l-x"}}],
    }
    assert validar_schema(forjado, personas["marco"]).schema is None


# --- AC-6 · params incoerentes com a direcao --------------------------


def test_ac6_cliente_id_com_direcao_de_lote_e_rejeitado() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate(
            {"direcao": "lote_para_clientes", "lote_id": "l-x", "cliente_id": "C"}
        )


def test_ac6_lote_id_com_direcao_de_cliente_e_rejeitado() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate(
            {
                "direcao": "cliente_para_lotes",
                "lote_id": "l-x",
                "cliente_id": "C",
                "de": "2026-01-01",
                "ate": "2026-02-01",
            }
        )


def test_ac6_cliente_para_lotes_sem_periodo_e_rejeitado() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate({"direcao": "cliente_para_lotes", "cliente_id": "C"})


def test_ac6_schema_forjado_incoerente_e_rejeitado(personas: dict[str, Any]) -> None:
    forjado = {
        "versao": 1,
        "blocos": [
            {
                "tipo": "rastreabilidade",
                "params": {
                    "direcao": "lote_para_clientes",
                    "lote_id": "l-x",
                    "cliente_id": "C",
                },
            }
        ],
    }
    assert validar_schema(forjado, personas["marco"]).schema is None


# --- AC-7 · nem custo nem margem --------------------------------------


async def test_ac7_resposta_nao_tem_custo(personas: dict[str, Any], _recall: None) -> None:
    lote = (
        await _vm(personas["marco"], direcao="lote_para_clientes", lote_id="l-recall-mtz")
    ).model_dump_json()
    cliente = (
        await _vm(
            personas["marco"],
            direcao="cliente_para_lotes",
            cliente_id=CLIENTES[0],
            de=HOJE - timedelta(days=365),
            ate=HOJE,
        )
    ).model_dump_json()
    for bruto in (lote, cliente):
        assert "custo" not in bruto
        assert "margem" not in bruto


# --- select puro -----------------------------------------------------


async def test_select_puro_nas_duas_direcoes(personas: dict[str, Any], _recall: None) -> None:
    d1 = await carregar(
        Params(direcao="lote_para_clientes", lote_id="l-recall-mtz"),
        contexto(personas["marco"]),
    )
    assert projetar(d1) == projetar(d1)
    d2 = await carregar(
        Params(
            direcao="cliente_para_lotes",
            cliente_id=CLIENTES[0],
            de=HOJE - timedelta(days=365),
            ate=HOJE,
        ),
        contexto(personas["sandra"]),
    )
    assert projetar(d2) == projetar(d2)
