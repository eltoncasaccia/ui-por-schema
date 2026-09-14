"""CS-02 · T-033 — o catalogo EXATO de cada uma das sete personas.

`test_catalogo_por_ator.py` (T-012) prova regras: quem tem `lote.ler` ve os de
lote, so' o RT ve as acoes privativas. Regra passa com componente A MAIS no
catalogo — um `requires` afrouxado num componente novo nao quebra nenhuma
delas. O conjunto congelado quebra: todo componente que entra ou sai do
vocabulario de um papel passa por este arquivo, e a mudanca aparece no diff.
"""

import json

import pytest

from estoque.application.registry.registry import catalogo_de
from estoque.domain.identidade import Ator

LEITURA_COMUM = frozenset(
    {
        "estoque_indicador",
        "fila_vencimento",
        "lote_detalhe",
        "lote_lista",
        "produto_ficha",
        "produto_saldo_por_unidade",
        "quarentena_fila",
        "vencimento_grafico",
    }
)
OPERACAO = frozenset(
    {
        "lote_movimentos",
        "movimento_lista",
        "recebimento_detalhe",
        "recebimento_lista",
        "temperatura_excursoes",
        "temperatura_historico",
    }
)
TRILHA = frozenset({"auditoria_trilha", "rastreabilidade"})
CORRECAO = frozenset({"movimento_descarte", "movimento_estorno"})

GERENTE = LEITURA_COMUM | OPERACAO | CORRECAO | {"movimento_saida", "recebimento_registrar"}

ESPERADO: dict[str, frozenset[str]] = {
    "marco": LEITURA_COMUM | OPERACAO | TRILHA | CORRECAO,
    "helena": LEITURA_COMUM
    | OPERACAO
    | TRILHA
    | CORRECAO
    | {"controlado_autorizar", "lote_status_acao", "quarentena_liberar"},
    "ivo": GERENTE,
    "odair": GERENTE,
    "cleide": LEITURA_COMUM | OPERACAO | {"movimento_saida", "recebimento_registrar"},
    "rafael": LEITURA_COMUM,
    "sandra": LEITURA_COMUM | OPERACAO | TRILHA,
}

SEM_CUSTO = ("helena", "ivo", "odair", "cleide")
COM_CUSTO = ("marco", "rafael", "sandra")
VALORES_DE_CUSTO = ("valor_em_estoque", "com_custo")


@pytest.mark.parametrize("nome", sorted(ESPERADO))
def test_cs02_catalogo_exato_da_persona(nome: str, personas: dict[str, Ator]) -> None:
    obtido = {c["id"] for c in catalogo_de(personas[nome])}
    assert obtido == ESPERADO[nome], (
        f"{nome}: a mais {sorted(obtido - ESPERADO[nome])}, "
        f"a menos {sorted(ESPERADO[nome] - obtido)}"
    )


def test_cs02_as_sete_personas_estao_aqui(personas: dict[str, Ator]) -> None:
    """Persona nova sem conjunto congelado seria persona sem CS-02."""
    assert set(ESPERADO) == set(personas)


def test_cs02_recem_cadastrado_nao_tem_vocabulario(recem_cadastrado: Ator) -> None:
    assert catalogo_de(recem_cadastrado) == []


@pytest.mark.parametrize("nome", SEM_CUSTO)
def test_cs02_nenhum_valor_de_custo_para_quem_nao_tem_custo_ler(
    nome: str, personas: dict[str, Ator]
) -> None:
    """Sobre o catalogo SERIALIZADO, todos os componentes de uma vez: pega o valor
    no enum e tambem na prosa de `description`/`examples`, que e' onde a filtragem
    de enum vaza sem ninguem notar."""
    assert "custo.ler" not in personas[nome].permissoes
    bruto = json.dumps(catalogo_de(personas[nome]), ensure_ascii=False)
    for valor in VALORES_DE_CUSTO:
        assert valor not in bruto, f"{nome} recebe {valor!r} no catalogo"


@pytest.mark.parametrize("nome", COM_CUSTO)
def test_cs02_quem_tem_custo_ler_recebe_os_valores_de_custo(
    nome: str, personas: dict[str, Ator]
) -> None:
    """O contraponto: sem ele, um catalogo que nunca oferecesse custo passaria acima."""
    assert "custo.ler" in personas[nome].permissoes
    bruto = json.dumps(catalogo_de(personas[nome]), ensure_ascii=False)
    for valor in VALORES_DE_CUSTO:
        assert valor in bruto, f"{nome} deveria receber {valor!r}"
