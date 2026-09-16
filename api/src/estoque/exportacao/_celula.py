"""Conversao de celula comum aos tres formatos."""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from estoque.application.exportacao.porta import neutralizar
from estoque.application.exportacao.tabelas import Celula, Coluna

FUSO = ZoneInfo("America/Sao_Paulo")


def local(v: datetime) -> datetime:
    """Hora de Sao Paulo, sem fuso: planilha nao guarda fuso, e UTC confunde."""
    return v.astimezone(FUSO).replace(tzinfo=None) if v.tzinfo else v


def texto(v: Celula, coluna: Coluna) -> str:
    """A celula como a pessoa le: data em dd/mm/aaaa, decimal com virgula."""
    if v is None:
        return ""
    if isinstance(v, datetime):
        return f"{local(v):%d/%m/%Y %H:%M}"
    if isinstance(v, date):
        return f"{v:%d/%m/%Y}"
    if isinstance(v, Decimal):
        casas = 2 if coluna.tipo == "reais" else 1
        inteiro, _, frac = f"{v:,.{casas}f}".partition(".")
        return inteiro.replace(",", ".") + "," + frac
    if isinstance(v, int):
        return str(v)
    return neutralizar(v)
