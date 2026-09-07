"""T-008 AC-1, AC-8, AC-9 — fronteiras de validade e status efetivo (ADR-0022)."""

from datetime import date

import pytest

from estoque.domain.regras.validade import (
    aceita_recebimento,
    classificar_validade,
    pode_sair,
    status_efetivo,
)
from estoque.domain.tipos import Lote, StatusLoteRegistrado

HOJE = date(2026, 6, 15)


def lote(dias: int, status: StatusLoteRegistrado = "liberado") -> Lote:
    from datetime import timedelta

    return Lote(
        id=f"L-{dias}",
        produto_id="P-1",
        numero="A1",
        unidade_id="cd-matriz",
        fabricacao=date(2025, 1, 1),
        validade=HOJE + timedelta(days=dias),
        status=status,
        endereco=None,
    )


# AC-1: fronteiras exatas. 30 e 90 sao INCLUSIVOS.
@pytest.mark.parametrize(
    ("dias", "esperado"),
    [
        (-1, "vencido"),
        (0, "bloqueio_30"),
        (29, "bloqueio_30"),
        (30, "bloqueio_30"),
        (31, "alerta_90"),
        (89, "alerta_90"),
        (90, "alerta_90"),
        (91, "ok"),
    ],
)
def test_fronteiras_de_validade(dias: int, esperado: str) -> None:
    assert classificar_validade(lote(dias), HOJE) == esperado


# AC-8: vencido AGORA, sem nenhum processo ter rodado. E' o ADR-0022.
def test_vencido_sem_job() -> None:
    assert status_efetivo(lote(-1), saldo=100, hoje=HOJE) == "vencido"


def test_esgotado_com_saldo_zero() -> None:
    assert status_efetivo(lote(200), saldo=0, hoje=HOJE) == "esgotado"


# AC-9: estorno que devolve saldo tira de esgotado, sem escrita de status.
def test_estorno_tira_de_esgotado() -> None:
    lt = lote(200)
    assert status_efetivo(lt, saldo=0, hoje=HOJE) == "esgotado"
    assert status_efetivo(lt, saldo=10, hoje=HOJE) == "liberado"


# Precedencia: vencido vence saldo. Lote vencido com saldo nao volta a vender.
def test_vencido_vence_esgotado_e_saldo() -> None:
    assert status_efetivo(lote(-5), saldo=0, hoje=HOJE) == "vencido"
    assert status_efetivo(lote(-5), saldo=50, hoje=HOJE) == "vencido"


def test_descartado_e_terminal() -> None:
    assert status_efetivo(lote(-5, "descartado"), saldo=0, hoje=HOJE) == "descartado"


# RN-L06 (negativo): nada sai que nao esteja liberado.
@pytest.mark.parametrize("status", ["quarentena", "bloqueado", "descartado"])
def test_nao_sai_o_que_nao_esta_liberado(status: StatusLoteRegistrado) -> None:
    assert pode_sair(lote(200, status), saldo=10, hoje=HOJE) is False


def test_nao_sai_vencido_nem_esgotado() -> None:
    assert pode_sair(lote(-1), saldo=10, hoje=HOJE) is False
    assert pode_sair(lote(200), saldo=0, hoje=HOJE) is False


# RN-L07
def test_recebimento_exige_6_meses() -> None:
    assert aceita_recebimento(date(2026, 12, 15), HOJE, autorizacao_rt=False) is True
    assert aceita_recebimento(date(2026, 12, 14), HOJE, autorizacao_rt=False) is False
    assert aceita_recebimento(date(2026, 12, 14), HOJE, autorizacao_rt=True) is True
