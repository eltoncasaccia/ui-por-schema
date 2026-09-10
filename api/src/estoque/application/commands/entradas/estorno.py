"""Schema de entrada do estorno (T-029). Modulo-FOLHA.

Ver `entradas/__init__.py` para por que este pacote existe e o que ele nao pode
importar.
"""

from typing import Literal

from pydantic import BaseModel, Field

from estoque.domain.tipos import TipoMovimento

# So' o que DIMINUI saldo tem estorno com o sinal certo — `saldo_lote`, na
# migracao 0001, soma `estorno` junto com `entrada`. Ver a docstring de
# `commands/estorno.py` e o achado A-38.
#
# Mora aqui, e nao no comando, porque o COMPONENTE tambem precisa da lista para
# dizer na tela o que e' estornavel — e `registry` nao importa `commands.estorno`
# (contrato 2 do import-linter: sqlalchemy no caminho). Duas listas divergiriam
# no dia em que uma delas mudasse, que e' a familia do achado A-11.
TIPOS_ESTORNAVEIS: tuple[TipoMovimento, ...] = ("saida",)

# RN-M05: lista FECHADA, e fechada POR TIPO de movimento.
#
# ACHADO A-19, o mesmo que a T-028 encontrou: o documento 02 lista os motivos de
# AJUSTE (`RN-I06`) e de nenhum outro tipo. Estes dois saem do enum
# `MotivoMovimento` do dominio, ficando com os que explicam por que uma SAIDA foi
# desfeita:
#
#   recebimento, erro_de_recebimento  -> sao de ENTRADA, e entrada nao se estorna
#                                        no ciclo 1 (ver `commands/estorno.py`)
#   venda, avaria, furto              -> explicam a saida, nunca o desfazimento
#   vencimento                        -> lote vencido sai por DESCARTE (RN-L06)
#   erro_de_contagem_anterior         -> ajuste de inventario, fora do ciclo 1
#   transferencia                     -> fluxo RN-T fora do ciclo 1 (ADR-0010)
MotivoEstorno = Literal["erro_de_separacao", "estorno"]

# O complemento e' OBRIGATORIO aqui, e nao e' contradicao com `RN-M05`.
#
# A regra diz que texto livre e' complemento e nunca substituto — ela proibe o
# campo livre NO LUGAR do enum, nao ao lado dele. E `estorno` e' o valor generico
# da lista: sozinho, ele diz que a operacao foi desfeita e nao diz por que. Quem
# le a trilha depois e' o auditor, e "estorno: estorno" nao e' resposta (RN-D01).
COMPLEMENTO_MINIMO = 10


class EntradaEstorno(BaseModel):
    """Um estorno referencia o movimento original — e so' ele (RN-M03).

    Nao ha' `quantidade`: estorno parcial nao existe. A quantidade e' a do
    original, lida no servidor. Se viesse do cliente, um estorno de 10 sobre uma
    saida de 2 criaria saldo do nada, e o livro-razao deixaria de fechar por
    construcao.
    """

    movimento_id: str
    motivo: MotivoEstorno
    complemento: str = Field(min_length=1)
