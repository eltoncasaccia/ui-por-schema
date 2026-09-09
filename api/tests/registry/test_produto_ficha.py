"""T-019 · `produto_ficha` — AC-1, AC-2, AC-4, AC-5, AC-6.

O objetivo da tarefa em uma frase: **custo invisivel por todos os caminhos.** O
que vale aqui e' o negativo — Cleide pedindo custo, por param direto e por
schema forjado, e nao recebendo nada.

AC-7 (minimo/maximo por unidade) esta' FORA: nao existe armazenamento para
`RN-P06` no sistema — sem tabela, sem campo de dominio, sem metodo de porta.
Registrado em ACHADOS (A-30) e na tarefa T-046.
"""

from datetime import timedelta
from typing import Any, Literal

import fakes
import pytest
from fakes import contexto
from pydantic import ValidationError

from estoque.application.registry.componentes.produto_ficha import Params, carregar, projetar
from estoque.application.schema.validar import validar_schema
from estoque.domain.erros import ErroDominio
from estoque.domain.tipos import Lote, Movimento, Produto

SEM_CUSTO = ("cleide", "helena", "ivo", "odair")
COM_CUSTO = ("marco", "rafael", "sandra")


async def _vm(
    ator: Any,
    produto_id: str = "p-amox",
    variante: Literal["padrao", "com_custo"] = "padrao",
) -> Any:
    params = Params(produto_id=produto_id, variante=variante)
    return projetar(await carregar(params, contexto(ator)))


# --- AC-1 · a chave de custo nao aparece para quem nao pode -----------------


async def test_ac1_custo_ausente_para_os_quatro_papeis(personas: dict[str, Any]) -> None:
    """Ausente, nao `null`: a chave nao existe no JSON."""
    for nome in SEM_CUSTO:
        vm = await _vm(personas[nome])
        assert "custo_unitario_centavos" not in vm.model_dump()
        assert "custo" not in vm.model_dump_json()


async def test_ac1_forcar_variante_com_custo_nao_vaza(personas: dict[str, Any]) -> None:
    """Mesmo que o param `variante=com_custo` chegue ao `load` (schema forjado
    que passou por alguma falha a montante), a porta ja' omitiu o campo para
    quem nao tem `custo.ler` — o `load` nao tem custo para colocar."""
    for nome in SEM_CUSTO:
        vm = await _vm(personas[nome], variante="com_custo")
        assert "custo_unitario_centavos" not in vm.model_dump()
        assert "1250" not in vm.model_dump_json()


# --- AC-2 · custo presente para quem pode, e SO' quando pedido -------------


async def test_ac2_custo_presente_quando_pedido(personas: dict[str, Any]) -> None:
    for nome in COM_CUSTO:
        vm = await _vm(personas[nome], variante="com_custo")
        assert vm.custo_unitario_centavos == 1250  # p-amox no fixture
        assert "custo_unitario_centavos" in vm.model_dump()


async def test_ac2_custo_ausente_quando_nao_pedido(personas: dict[str, Any]) -> None:
    """Quem PODE ver custo tambem nao ve por acidente: sem `variante=com_custo`,
    a chave nao esta' la'."""
    for nome in COM_CUSTO:
        vm = await _vm(personas[nome], variante="padrao")
        assert "custo_unitario_centavos" not in vm.model_dump()


# --- AC-4 · "qual o custo" como Cleide nao produz o valor por nenhum caminho -


def _bloco_com_custo() -> dict[str, Any]:
    params = {"produto_id": "p-amox", "variante": "com_custo"}
    return {"versao": 1, "blocos": [{"tipo": "produto_ficha", "params": params}]}


def test_ac4_schema_forjado_com_variante_de_custo_e_rejeitado(
    personas: dict[str, Any],
) -> None:
    """Cleide monta o schema a mao e envia `variante=com_custo` direto. A
    revalidacao no servidor rejeita pelo VALOR do param (A-05)."""
    r = validar_schema(_bloco_com_custo(), personas["cleide"])
    assert r.schema is None
    assert any("variante" in rej.motivo for rej in r.rejeitados)


def test_ac4_o_mesmo_schema_passa_para_quem_pode(personas: dict[str, Any]) -> None:
    """O contraponto: se a rejeicao acima valesse para todo mundo, provaria
    pouco."""
    r = validar_schema(_bloco_com_custo(), personas["rafael"])
    assert r.schema is not None
    assert "produto_ficha" in r.aceitos


def test_ac4_agregado_de_custo_tambem_continua_barrado(personas: dict[str, Any]) -> None:
    """CA-05 cita "agregados derivados (valor total em estoque)". A metrica
    `valor_em_estoque` do `estoque_indicador` some do enum de Cleide pelo mesmo
    mecanismo — aqui so' se afirma que o caminho segue fechado."""
    forjado = {
        "versao": 1,
        "blocos": [{"tipo": "estoque_indicador", "params": {"metrica": "valor_em_estoque"}}],
    }
    assert validar_schema(forjado, personas["cleide"]).schema is None


# --- AC-5 · exportacao respeita a mesma regra ------------------------------


async def test_ac5_exportacao_do_viewmodel_nao_leva_custo(personas: dict[str, Any]) -> None:
    """Nao ha' caminho de exportacao separado: o que sai e' a serializacao do
    proprio VM. A omissao e' estrutural (`@model_serializer`), entao qualquer
    exportacao herda — inclusive `model_dump(mode="json")`, o formato da borda.
    """
    for nome in SEM_CUSTO:
        exportado = (await _vm(personas[nome], variante="com_custo")).model_dump(mode="json")
        assert "custo_unitario_centavos" not in exportado


# --- AC-6 · produto inativo aparece com marcacao e saldo (RN-P05) ---------


@pytest.fixture
def _produto_inativo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Um produto desativado, com saldo, so' para este teste — sem tocar o
    fixture compartilhado. `FakeRepo*` le os globais de `fakes` na hora."""
    p = Produto(
        id="p-dipi",
        ean="7891234000049",
        nome="Dipirona 500mg",
        fabricante="Sanofi",
        principio_ativo="dipirona",
        classe="comum",
        curva_abc="C",
        ativo=False,
        custo_unitario_centavos=800,
    )
    lote = Lote(
        id="l-dipi-mtz",
        produto_id="p-dipi",
        numero="DIP2401",
        unidade_id="cd-matriz",
        fabricacao=fakes.HOJE - timedelta(days=100),
        validade=fakes.HOJE + timedelta(days=120),
        status="liberado",
        endereco="A-99",
    )
    mov = Movimento(
        id="m-dipi",
        lote_id="l-dipi-mtz",
        unidade_id="cd-matriz",
        tipo="entrada",
        quantidade=40,
        motivo="recebimento",
        complemento=None,
        autor_id="u-cleide",
        autorizador_id=None,
        status="efetivado",
        criado_em=fakes.AGORA - timedelta(days=15),
        estorna_movimento_id=None,
        cliente_id=None,
        nota_fiscal=None,
    )
    monkeypatch.setitem(fakes.PRODUTOS, "p-dipi", p)
    monkeypatch.setattr(fakes, "LOTES", [*fakes.LOTES, lote])
    monkeypatch.setattr(fakes, "MOVIMENTOS", [*fakes.MOVIMENTOS, mov])


async def test_ac6_produto_inativo_exibido_com_marcacao_e_saldo(
    personas: dict[str, Any], _produto_inativo: None
) -> None:
    vm = await _vm(personas["ivo"], produto_id="p-dipi")
    assert vm.ativo is False
    # RN-P05: continua com saldo visivel ate' esgotar.
    assert vm.saldo_total == 40


# --- negativa que nao vaza -----------------------------------------------


async def test_produto_inexistente_e_nao_encontrado_sem_ecoar_o_id(
    personas: dict[str, Any],
) -> None:
    with pytest.raises(ErroDominio) as capturado:
        await _vm(personas["ivo"], produto_id="p-nao-existe")
    erro = capturado.value
    assert erro.codigo == "nao_encontrado"
    for face in (erro.mensagem_publica, repr(erro), str(erro)):
        assert "p-nao-existe" not in face


# --- enum fechado / pureza ---------------------------------------------------


def test_variante_invalida_e_rejeitada() -> None:
    with pytest.raises(ValidationError):
        Params.model_validate({"produto_id": "p-amox", "variante": "com_desconto"})


async def test_select_e_puro(personas: dict[str, Any]) -> None:
    dados = await carregar(
        Params(produto_id="p-amox", variante="com_custo"),
        contexto(personas["rafael"]),
    )
    assert projetar(dados) == projetar(dados)


async def test_saldo_total_respeita_o_escopo_do_ator(personas: dict[str, Any]) -> None:
    """Odair so' alcanca Uberlandia: o `saldo_total` de p-amox nao inclui os
    lotes de CD Matriz, mesmo sem param de unidade para "contornar"."""
    odair = await _vm(personas["odair"], produto_id="p-amox")
    ivo = await _vm(personas["ivo"], produto_id="p-amox")
    assert odair.saldo_total < ivo.saldo_total
