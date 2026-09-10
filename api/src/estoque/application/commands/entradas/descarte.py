"""Schema de entrada do descarte (T-029). Modulo-FOLHA.

Ver `entradas/__init__.py` para por que este pacote existe e o que ele nao pode
importar.
"""

from typing import Literal

from pydantic import BaseModel, Field

# RN-M05, lista fechada por tipo. Familia do achado A-19: nao ha' lista de
# motivos de descarte em documento nenhum, e estes dois saem do enum
# `MotivoMovimento` do dominio.
#
# `vencimento` e' a razao que `RN-L06` nomeia — lote vencido nao sai por nenhum
# outro caminho. `avaria` cobre o lote bloqueado por decisao do RT: recall,
# suspeita, embalagem violada. Os demais valores do enum descrevem entrada,
# venda ou ajuste, e nenhum deles termina em mercadoria destruida.
MotivoDescarte = Literal["vencimento", "avaria"]

# Como no estorno: a justificativa e' complemento do enum, nunca substituto. O
# descarte destroi mercadoria e e' irreversivel — a trilha precisa dizer o que
# foi destruido e por que, para quem for auditar (RN-D01).
JUSTIFICATIVA_MINIMA = 10


class EntradaDescarte(BaseModel):
    """§4.1: **Gerente + RT**. Duas identidades, e as duas vao na mesma
    requisicao.

    Nao ha' `quantidade`: descarte e' do lote inteiro. O saldo que sobra e' lido
    no servidor e sai todo — um descarte parcial deixaria o lote em `descartado`
    com saldo positivo, e o estado terminal passaria a mentir sobre o que ainda
    existe na prateleira.

    `segunda_identificacao_id` e' o id de quem assina junto, e o servidor confere
    o papel dele. Um campo de texto com o nome digitado seria dupla identificacao
    de mentira: quem preenche escolhe o que escrever.
    """

    lote_id: str
    motivo: MotivoDescarte
    justificativa: str = Field(min_length=1)
    segunda_identificacao_id: str
