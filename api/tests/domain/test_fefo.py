"""RN-L02, RN-L03 — FEFO com desempate deterministico (T-008 AC-2, AC-3)."""

from datetime import date, timedelta

from estoque.domain.regras.fefo import exige_justificativa_fefo, propor_fefo
from estoque.domain.tipos import Lote, StatusLoteRegistrado

HOJE = date(2026, 6, 15)


def lote(lid: str, dias: int, status: StatusLoteRegistrado = "liberado") -> Lote:
    return Lote(
        id=lid,
        produto_id="P-1",
        numero=lid,
        unidade_id="cd-matriz",
        fabricacao=date(2025, 1, 1),
        validade=HOJE + timedelta(days=dias),
        status=status,
        endereco=None,
    )


def test_propoe_o_de_menor_validade() -> None:
    lotes = [lote("L-C", 200), lote("L-A", 40), lote("L-B", 90)]
    escolhido = propor_fefo(lotes, {"L-A": 5, "L-B": 5, "L-C": 5}, HOJE)
    assert escolhido is not None and escolhido.id == "L-A"


def test_ignora_o_que_nao_esta_liberado() -> None:
    """AC-2 (negativo): propor lote que nao pode sair seria propor um erro."""
    lotes = [lote("L-Q", 10, "quarentena"), lote("L-B", 20, "bloqueado"), lote("L-OK", 200)]
    escolhido = propor_fefo(lotes, {"L-Q": 9, "L-B": 9, "L-OK": 9}, HOJE)
    assert escolhido is not None and escolhido.id == "L-OK"


def test_ignora_vencido_e_esgotado() -> None:
    lotes = [lote("L-V", -1), lote("L-E", 30), lote("L-OK", 200)]
    escolhido = propor_fefo(lotes, {"L-V": 9, "L-E": 0, "L-OK": 9}, HOJE)
    assert escolhido is not None and escolhido.id == "L-OK"


def test_desempate_deterministico() -> None:
    """AC-3: mesma entrada, mesma saida, sempre — em qualquer ordem de entrada."""
    a, b = lote("L-A", 40), lote("L-B", 40)
    saldos = {"L-A": 5, "L-B": 5}
    r1 = propor_fefo([a, b], saldos, HOJE)
    r2 = propor_fefo([b, a], saldos, HOJE)
    assert r1 is not None and r2 is not None
    assert r1.id == r2.id == "L-A"


def test_sem_lote_elegivel() -> None:
    assert propor_fefo([lote("L-V", -1)], {"L-V": 5}, HOJE) is None


def test_justificativa_quando_diverge_do_fefo() -> None:
    a, b = lote("L-A", 40), lote("L-B", 90)
    assert exige_justificativa_fefo(a, a) is False
    assert exige_justificativa_fefo(b, a) is True  # RN-L03
    assert exige_justificativa_fefo(b, None) is True
