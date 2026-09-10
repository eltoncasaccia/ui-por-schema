"""Schema de entrada do registro de recebimento (T-026). Modulo-FOLHA.

O `CommandDef` que o registry publica e o comando que executa apontam para o
MESMO schema: duas declaracoes do mesmo formulario divergiriam no dia em que uma
mudasse (achado A-11, agora entre o que a tela pede e o que o servidor aceita).
Para isso este modulo nao importa mais nada alem de pydantic e `domain`:

    registry -> commands.entradas.recebimento   OK
    registry -> commands.pipeline               PROIBIDO (contrato 2: sqlalchemy)

**`extra="forbid"` aqui e' o AC-1, nao arrumacao.** O criterio diz "nao existe
caminho, NEM POR REQUISICAO FORJADA, que crie lote com status diferente de
quarentena". Nao ha campo `status` neste schema — e sem `forbid`, um cliente que
mandasse `"status": "liberado"` seria **silenciosamente ignorado**, que e' a
forma de proteger que ninguem consegue auditar depois. Com `forbid`, a
requisicao forjada e' RECUSADA, e a recusa aparece.

O que este schema NAO valida, de proposito: classe do produto, tipo da unidade e
sala-cofre. Sao dados do banco (`RN-P02`, `RN-P03`, `RN-F01`, `RN-R05`), e
validacao que depende de dado mora no comando — aqui viraria um espelho do banco
que envelhece sozinho.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from estoque.domain.identidade import UnidadeId

# RN-L07: "validade inferior a 6 meses e' recusada, salvo autorizacao expressa
# do RT". Seis meses em dias corridos.
#
# **Mora na FOLHA, e nao no comando**, porque os dois lados precisam dela: o
# comando para recusar, e o componente do registry para a tela avisar antes. O
# registry NAO pode importar `commands/recebimento.py` — ele usa sqlalchemy, e o
# contrato 2 do import-linter proibe `registry -> sqlalchemy` inclusive por
# caminho indireto. Duplicar o numero seria pior: os dois divergiriam.
DIAS_VALIDADE_MINIMA = 180


class ItemRecebido(BaseModel):
    """Uma linha da nota. Vira UM lote em quarentena e UM movimento de entrada."""

    model_config = ConfigDict(extra="forbid")

    produto_id: str = Field(min_length=1)
    # RN-L01: numero, fabricacao e validade nao sao opcionais em lote nenhum.
    # Sao obrigatorios aqui, e nao "obrigatorios na interface": formulario e'
    # payload nao-confiavel como qualquer outro.
    numero: str = Field(min_length=1)
    fabricacao: date
    validade: date
    quantidade: int = Field(gt=0)
    # RN-R04: o que a NOTA diz. Ausente = sem divergencia; diferente de
    # `quantidade` = divergencia, que gera pendencia e NAO impede a conclusao.
    quantidade_nota: int | None = Field(default=None, gt=0)
    endereco: str | None = None

    @model_validator(mode="after")
    def _datas_coerentes(self) -> "ItemRecebido":
        # O banco tem o mesmo CHECK (`validade >= fabricacao`). Aqui a recusa e'
        # `invalido` com mensagem; la' seria um erro de integridade virando 500.
        if self.validade < self.fabricacao:
            raise ValueError("validade anterior a fabricacao")
        return self


class EntradaRecebimento(BaseModel):
    """O formulario inteiro. **Nao existe campo de status** — ver o docstring."""

    model_config = ConfigDict(extra="forbid")

    unidade_id: UnidadeId
    nota_fiscal: str = Field(min_length=1)
    fornecedor: str = Field(min_length=1)
    itens: tuple[ItemRecebido, ...] = Field(min_length=1)

    # RN-F01: obrigatoria quando ha item termolabil. Opcional aqui porque a
    # obrigatoriedade depende da CLASSE do produto, que so' o comando conhece.
    temperatura_chegada_c: float | None = None

    # RN-R05: a segunda identificacao, exigida quando ha item controlado. Quem
    # verifica que sao DUAS pessoas diferentes e' o comando — um campo que
    # aceitasse o proprio conferente transformaria "dupla identificacao" em
    # "digitar o proprio nome duas vezes".
    rt_id: str | None = None

    # RN-L07: validade < 6 meses e' recusada, "salvo autorizacao expressa do RT".
    # A autorizacao e' um TEXTO, e nao um booleano: `True` nao diz quem autorizou
    # nem por que, e e' isso que a trilha precisa registrar.
    autorizacao_validade_rt: str | None = Field(default=None, min_length=10)
