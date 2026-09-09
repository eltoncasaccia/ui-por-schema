"""Schemas de entrada da saida de estoque (T-028). Modulo-FOLHA.

Ver `entradas/__init__.py` para por que este pacote existe e o que ele nao pode
importar.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

# RN-M05: lista FECHADA, e fechada POR TIPO de movimento.
#
# ACHADO A-19: o documento 02 lista os motivos de AJUSTE (`RN-I06`) e nunca os
# de saida. Estes quatro saem do enum `MotivoMovimento` do dominio, tirando os
# que pertencem a outro tipo:
#
#   recebimento, erro_de_recebimento  -> sao de ENTRADA
#   estorno                            -> e' o tipo `estorno` (T-029)
#   vencimento                         -> lote vencido so' sai por DESCARTE (RN-L06)
#   erro_de_contagem_anterior          -> ajuste de inventario, fora do ciclo 1
#   transferencia                      -> o fluxo RN-T esta' fora do ciclo 1
#                                         (ADR-0010); oferece-lo aqui deixaria
#                                         mercadoria sair sem destino registrado
MotivoSaida = Literal["venda", "avaria", "furto", "erro_de_separacao"]

# Motivos que exigem destinatario. `venda` alimenta o recall (RN-D03, CA-01):
# sem cliente e nota, a pergunta "quem recebeu este lote?" nao tem resposta, e
# ela e' a que o cliente precisa responder em menos de 60 segundos (RNF-01).
EXIGEM_DESTINATARIO = frozenset({"venda"})

JUSTIFICATIVA_MINIMA = 10


class EntradaSaida(BaseModel):
    """Uma saida de estoque.

    `quantidade > 0` sempre: o SINAL vem do tipo do movimento, nunca do numero
    (CONTRATOS §3). Quantidade negativa seria uma entrada disfarcada de saida, e
    o extrato do lote passaria a depender de ler o sinal junto com o tipo.
    """

    lote_id: str
    quantidade: int = Field(gt=0)
    motivo: MotivoSaida
    # Texto livre é COMPLEMENTO, nunca substituto (RN-M05). Por isso ele é
    # opcional e `motivo` não é: um campo livre obrigatório junto de um enum
    # opcional seria a mesma regra escrita ao contrário.
    complemento: str | None = None

    # RN-L03: separar lote diferente do proposto pelo FEFO exige justificativa.
    # Fica opcional no schema e obrigatória no comando, porque só lá se sabe
    # qual lote o FEFO propôs.
    justificativa_fefo: str | None = None

    cliente_id: str | None = None
    nota_fiscal: str | None = None

    @model_validator(mode="after")
    def _destinatario_quando_exigido(self) -> "EntradaSaida":
        if self.motivo in EXIGEM_DESTINATARIO and not (self.cliente_id and self.nota_fiscal):
            msg = "Venda exige cliente e nota fiscal."
            raise ValueError(msg)
        return self
