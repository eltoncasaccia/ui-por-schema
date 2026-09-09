"""Schemas de entrada dos comandos. Modulo-FOLHA, e a folha e' o ponto.

O `CommandDef` que o registry publica precisa apontar para o schema de dominio
do comando (CONTRATOS §5), e `commands/lote.py` precisa do mesmo schema para
validar a escrita. Duas declaracoes do mesmo formulario divergiriam — e' o
achado A-11 outra vez, agora entre o que a tela pede e o que o servidor aceita.

Uma definicao, dois lados. Para isso este modulo nao pode importar mais nada:

    registry -> commands.entradas          OK, so' pydantic no caminho
    registry -> commands.pipeline          PROIBIDO (contrato 2: sqlalchemy)

Se alguem acrescentar aqui um import de `pipeline`, de `data` ou de SQLAlchemy,
o contrato 2 do import-linter quebra na hora — e ha' teste proprio afirmando
que este modulo nao alcanca nenhum dos tres (`test_quarentena_liberar.py`).
"""

from typing import Literal

from pydantic import BaseModel, Field

AcaoStatus = Literal["bloquear", "desbloquear", "liberar_vencimento"]


class EntradaLiberacao(BaseModel):
    """`decisao` e' enum fechado, e as duas saidas sao terminais.

    Nao existe "liberar com pendencia". Reprovar leva a **bloqueado**, nunca a
    liberado (§4.1) — um estado intermediario seria um lote vendavel que ninguem
    conferiu, que e' o que a quarentena existe para impedir.
    """

    lote_id: str
    decisao: Literal["liberar", "reprovar"]
    justificativa: str = Field(min_length=1)

    # RN-R03: conferencia REGISTRADA. Sao afirmacoes do RT, nao dados derivados
    # de outra tabela — e' isso que "registrada" quer dizer. Cada uma vira valor
    # da trilha de auditoria.
    integridade_conferida: bool = False
    validade_conferida: bool = False
    nota_fiscal_conferida: bool = False
    temperatura_conferida: bool = False


class EntradaStatus(BaseModel):
    """Tres transicoes num formulario so' — a fusao do ADR-0011.

    O recorte continua existindo como valor NOMEADO no enum, que e' a condicao
    que o ADR-0001 impoe a qualquer fusao: economizar componente nao pode custar
    a precisao do que o modelo consegue pedir.
    """

    lote_id: str
    acao: AcaoStatus
    justificativa: str = Field(min_length=1)
