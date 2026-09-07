"""RN-M06, RN-M01, RN-M02, RN-M03, RN-C01 e a tabela 4.1.

Os testes que valem aqui sao os negativos: provar que Helena consegue liberar
quarentena prova pouco; provar que Ivo NAO consegue e' o que prova a arquitetura.
"""

from datetime import UTC, datetime

import pytest

from estoque.domain.regras.estados import (
    aplicar_transicao,
    montar_estorno,
    resulta_negativo,
    transicao_valida,
    valida_alocacao,
)
from estoque.domain.saldo import calcular_saldo
from estoque.domain.tipos import Lote, Movimento, StatusMovimento

AGORA = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)


def mov(
    tipo: str, qtd: int, status: StatusMovimento = "efetivado", mid: str = "M-1"
) -> Movimento:
    return Movimento(
        id=mid,
        lote_id="L-1",
        unidade_id="cd-matriz",
        tipo=tipo,  # type: ignore[arg-type]
        quantidade=qtd,
        motivo="venda",
        complemento=None,
        autor_id="u-cleide",
        autorizador_id=None,
        status=status,
        criado_em=AGORA,
        estorna_movimento_id=None,
        cliente_id=None,
        nota_fiscal=None,
    )


# --- RN-M06 -----------------------------------------------------------------
def test_saldo_e_a_soma_dos_movimentos() -> None:
    assert calcular_saldo([mov("entrada", 100), mov("saida", 30)]) == 70


# --- RN-C01: a base do CA-04 -------------------------------------------------
def test_pendente_de_autorizacao_nao_altera_saldo() -> None:
    """Se o saldo mudasse na submissao, a mercadoria ja' teria saido do estoque
    contabil com UMA identificacao — e a dupla identificacao viraria teatro."""
    antes = calcular_saldo([mov("entrada", 100)])
    depois = calcular_saldo(
        [mov("entrada", 100), mov("saida", 40, "aguardando_autorizacao", "M-2")]
    )
    assert antes == depois == 100


def test_recusado_nao_altera_saldo_e_permanece() -> None:
    movs = [mov("entrada", 100), mov("saida", 40, "recusado", "M-2")]
    assert calcular_saldo(movs) == 100
    assert len(movs) == 2  # RN-M02: nada e' apagado


# --- RN-M01 ------------------------------------------------------------------
def test_saldo_nunca_negativo() -> None:
    assert resulta_negativo(10, 11) is True
    assert resulta_negativo(10, 10) is False


# --- Tabela 4.1: negativos ---------------------------------------------------
def test_so_rt_libera_quarentena() -> None:
    """RN-R02. O caso que da' sentido ao ADR-0003."""
    assert transicao_valida("quarentena", "liberacao", "rt") is True
    for papel in ("diretor", "gerente", "conferente", "comprador", "auditoria"):
        assert transicao_valida("quarentena", "liberacao", papel) is False  # type: ignore[arg-type]


def test_diretor_nao_e_nivel_e_conjunto() -> None:
    """Papel nao e' hierarquia. Diretor nao libera quarentena (RN-R02)."""
    assert transicao_valida("quarentena", "liberacao", "diretor") is False
    assert transicao_valida("liberado", "bloqueio", "diretor") is False


def test_recem_cadastrado_sem_papel_nao_transiciona() -> None:
    """ADR-0019: papel None nao passa em nada."""
    assert transicao_valida("quarentena", "liberacao", None) is False


@pytest.mark.parametrize(
    ("de", "evento"),
    [
        ("liberado", "liberacao"),
        ("descartado", "desbloqueio"),
        ("quarentena", "descarte"),
        ("liberado", "descarte"),
    ],
)
def test_transicoes_fora_da_tabela_sao_recusadas(de: str, evento: str) -> None:
    for papel in ("diretor", "rt", "gerente", "conferente"):
        assert transicao_valida(de, evento, papel) is False  # type: ignore[arg-type]


def test_reprovacao_vai_para_bloqueado_nunca_liberado() -> None:
    lote = Lote(
        id="L-1",
        produto_id="P-1",
        numero="A",
        unidade_id="cd-matriz",
        fabricacao=AGORA.date(),
        validade=AGORA.date(),
        status="quarentena",
        endereco=None,
    )
    assert aplicar_transicao(lote, "reprovacao", "rt").status == "bloqueado"


# --- RN-P02, RN-P03 ----------------------------------------------------------
def test_alocacao_por_classe() -> None:
    assert valida_alocacao("termolabil", "refrigerado", False) is True
    assert valida_alocacao("termolabil", "seco", True) is False  # RN-P02
    assert valida_alocacao("controlado", "seco", True) is True
    assert valida_alocacao("controlado", "seco", False) is False  # RN-P03


# --- RN-M02, RN-M03 ----------------------------------------------------------
def test_estorno_nao_toca_o_original() -> None:
    original = mov("saida", 40)
    estorno = montar_estorno(original, "erro_de_separacao", "u-ivo", "M-9", AGORA)
    assert estorno.estorna_movimento_id == "M-1"
    assert original.quantidade == 40 and original.status == "efetivado"
    # RN-M06: o saldo reflete a soma dos dois, sem edicao de campo
    assert calcular_saldo([mov("entrada", 100), original, estorno]) == 100


def test_movimento_e_imutavel() -> None:
    """RN-M02: frozen dataclass. Nao ha caminho de mutacao."""
    m = mov("saida", 40)
    with pytest.raises((AttributeError, TypeError)):
        m.quantidade = 999  # type: ignore[misc]


def test_nao_estorna_pendente_nem_estorno() -> None:
    with pytest.raises(ValueError, match="efetivado"):
        montar_estorno(mov("saida", 1, "aguardando_autorizacao"), "estorno", "u", "M-9", AGORA)
    with pytest.raises(ValueError, match="estorno de estorno"):
        montar_estorno(mov("estorno", 1), "estorno", "u", "M-9", AGORA)
