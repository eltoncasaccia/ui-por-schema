"""Schema de entrada da autorizacao de controlado (T-030). Modulo-FOLHA.

Ver `entradas/__init__.py` para por que este pacote existe e o que ele nao pode
importar.
"""

from typing import Literal

from pydantic import BaseModel, Field

# O motivo e' obrigatorio nas DUAS decisoes, e nao so' na recusa.
#
# Autorizar movimentacao de controlado e' ato de responsabilidade tecnica com
# peso regulatorio: "aprovei" sem por que registrado nao serve a quem audita
# depois, que e' exatamente quem vai ler isto. Exigir so' na recusa ensinaria
# que autorizar e' o caminho barato.
MOTIVO_MINIMO = 10


class EntradaAutorizacao(BaseModel):
    movimento_id: str
    decisao: Literal["autorizar", "recusar"]
    motivo: str = Field(min_length=1)
