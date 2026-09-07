"""Validade e status efetivo. RN-L04, RN-L05, RN-L06, RN-L07 e ADR-0022.

Nenhuma funcao aqui chama `date.today()`. A data de referencia entra por
parametro, sempre: regra que le o relogio nao e' auditavel nem testavel.
"""

from datetime import date
from typing import Literal

from estoque.domain.tipos import (
    DIAS_ALERTA_VALIDADE,
    DIAS_BLOQUEIO_VALIDADE,
    MESES_MINIMOS_RECEBIMENTO,
    Lote,
    StatusLoteEfetivo,
)

ClasseValidade = Literal["ok", "alerta_90", "bloqueio_30", "vencido"]


def dias_ate_vencer(lote: Lote, hoje: date) -> int:
    return (lote.validade - hoje).days


def classificar_validade(lote: Lote, hoje: date) -> ClasseValidade:
    """RN-L04 (<=90d alerta) e RN-L05 (<=30d bloqueio).

    Fronteiras: um lote com validade EXATAMENTE hoje ainda nao venceu — vence
    no dia seguinte. `validade` e' o ultimo dia de uso.
    """
    dias = dias_ate_vencer(lote, hoje)
    if dias < 0:
        return "vencido"
    if dias <= DIAS_BLOQUEIO_VALIDADE:
        return "bloqueio_30"
    if dias <= DIAS_ALERTA_VALIDADE:
        return "alerta_90"
    return "ok"


def status_efetivo(lote: Lote, saldo: int, hoje: date) -> StatusLoteEfetivo:
    """ADR-0022 — o status que a tela mostra, calculado, nunca armazenado.

    Ordem de precedencia, e ela importa:
      1. `descartado` — estado terminal, vence tudo
      2. `vencido` — um lote vencido nao volta a ser vendavel por ter saldo
      3. `bloqueado` — decisao humana registrada
      4. `esgotado` — sem saldo
      5. o proprio status registrado

    Um lote com validade de ontem e' `vencido` NESTE INSTANTE, sem nenhum
    processo ter rodado. E' o ponto inteiro do ADR-0022.
    """
    if lote.status == "descartado":
        return "descartado"
    if dias_ate_vencer(lote, hoje) < 0:
        return "vencido"
    if lote.status == "bloqueado":
        return "bloqueado"
    if lote.status == "quarentena":
        return "quarentena"
    if saldo <= 0:
        return "esgotado"
    return "liberado"


def pode_sair(lote: Lote, saldo: int, hoje: date) -> bool:
    """RN-L06: lote vencido nao sai por nenhum motivo, exceto descarte.

    Esta funcao responde 'pode ter saida de venda?'. Descarte tem caminho
    proprio (`movimento_descarte`) e nao passa por aqui.
    """
    return status_efetivo(lote, saldo, hoje) == "liberado"


def aceita_recebimento(validade: date, hoje: date, autorizacao_rt: bool) -> bool:
    """RN-L07: recebimento com validade inferior a 6 meses e' recusado, salvo
    autorizacao expressa do RT."""
    if autorizacao_rt:
        return True
    limite = _somar_meses(hoje, MESES_MINIMOS_RECEBIMENTO)
    return validade >= limite


def _somar_meses(d: date, meses: int) -> date:
    mes = d.month - 1 + meses
    ano = d.year + mes // 12
    mes = mes % 12 + 1
    dia = min(d.day, _ultimo_dia(ano, mes))
    return date(ano, mes, dia)


def _ultimo_dia(ano: int, mes: int) -> int:
    if mes == 12:
        return 31
    proximo = date(ano + (mes // 12), mes % 12 + 1, 1)
    return (proximo - date(ano, mes, 1)).days
