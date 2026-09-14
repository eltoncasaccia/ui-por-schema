"""As sete entidades. CONTRATOS secao 3.

Duas ausencias neste modulo sao decisao, nao esquecimento:

1. `Lote` nao tem `saldo` — RN-M06: saldo e' a soma dos movimentos. Um campo de
   saldo e' um campo editavel, e um campo editavel e' a divergencia de 3,8% do
   inventario de volta.
2. `Lote` nao tem `vencido` nem `esgotado` no status — ADR-0022: sao derivados
   de data e de saldo. Armazena-se apenas o que e' decisao de alguem.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from estoque.domain.identidade import PapelId, UnidadeId

ClasseProduto = Literal["comum", "controlado", "termolabil", "antimicrobiano"]
TipoUnidade = Literal["seco", "refrigerado"]
CurvaAbc = Literal["A", "B", "C"]

TipoMovimento = Literal["entrada", "saida", "descarte", "estorno"]
StatusMovimento = Literal["efetivado", "aguardando_autorizacao", "recusado"]

# RN-M05: motivo vem de lista fechada por tipo; texto livre e' complemento.
MotivoMovimento = Literal[
    "recebimento",
    "venda",
    "transferencia",
    "avaria",
    "furto",
    "erro_de_separacao",
    "erro_de_recebimento",
    "vencimento",
    "erro_de_contagem_anterior",
    "estorno",
]

# ADR-0022 — o que e' gravado: decisao humana, com autor e motivo.
StatusLoteRegistrado = Literal["quarentena", "liberado", "bloqueado", "descartado"]
# ADR-0022 — o que e' calculado: f(registrado, validade, saldo, hoje).
StatusLoteEfetivo = Literal[
    "quarentena", "liberado", "bloqueado", "descartado", "vencido", "esgotado"
]

StatusRecebimento = Literal["rascunho", "conferido", "liberado"]


@dataclass(frozen=True, slots=True)
class Unidade:
    id: UnidadeId
    nome: str
    tipo: TipoUnidade
    sala_cofre: bool  # RN-P03: controlado so' em unidade com sala-cofre


@dataclass(frozen=True, slots=True)
class Produto:
    id: str
    ean: str
    nome: str
    fabricante: str
    principio_ativo: str
    classe: ClasseProduto
    curva_abc: CurvaAbc
    ativo: bool
    # RN-A02: campo restrito. A porta de dados OMITE a chave (nao envia None)
    # para quem nao tem `custo.ler` — `None` vazaria a existencia do campo.
    custo_unitario_centavos: int | None = None


@dataclass(frozen=True, slots=True)
class FaixaEstoque:
    """RN-P06 (T-046): estoque minimo e maximo do PAR (produto, unidade).

    Nao e' campo de `Produto` de proposito: um minimo no produto obrigaria um
    valor unico para a rede inteira, e a regra existe para impedir isso.
    """

    produto_id: str
    unidade_id: UnidadeId
    minimo: int
    maximo: int


@dataclass(frozen=True, slots=True)
class Lote:
    id: str
    produto_id: str
    numero: str
    unidade_id: UnidadeId
    fabricacao: date
    validade: date
    status: StatusLoteRegistrado
    endereco: str | None
    # NAO existe `saldo`. NAO existe `vencido`/`esgotado`. Ver docstring do modulo.


@dataclass(frozen=True, slots=True)
class Movimento:
    id: str
    lote_id: str
    unidade_id: UnidadeId
    tipo: TipoMovimento
    quantidade: int  # sempre positiva; o sinal vem do tipo
    motivo: MotivoMovimento
    complemento: str | None
    autor_id: str
    autorizador_id: str | None  # 2a identidade — RN-C01, controlados
    status: StatusMovimento
    criado_em: datetime  # do SERVIDOR — RN-M04
    estorna_movimento_id: str | None
    cliente_id: str | None  # presente em saida: e' o que serve ao recall
    nota_fiscal: str | None


@dataclass(frozen=True, slots=True)
class Recebimento:
    id: str
    unidade_id: UnidadeId
    nota_fiscal: str
    fornecedor: str
    status: StatusRecebimento
    conferente_id: str
    rt_id: str | None  # RN-R05: controlado exige dupla identificacao
    temperatura_chegada_c: float | None  # RN-F01: obrigatoria para termolabil
    divergencia: bool  # RN-R04: nao impede o recebimento, gera pendencia
    recebido_em: datetime


@dataclass(frozen=True, slots=True)
class RegistroTemperatura:
    id: str
    unidade_id: UnidadeId
    medido_em: datetime
    celsius: float


@dataclass(frozen=True, slots=True)
class Usuario:
    id: str
    nome: str
    email: str
    papel: PapelId | None  # None = cadastrado, sem papel atribuido (ADR-0019)
    unidades: frozenset[UnidadeId]
    ativo: bool  # RN-A06: desativa, nunca exclui
    # senha_hash NAO aparece aqui. Credencial vive em `auth`, nunca no dominio.


FAIXA_FRIA_MIN_C = 2.0
FAIXA_FRIA_MAX_C = 8.0
DIAS_ALERTA_VALIDADE = 90  # RN-L04
DIAS_BLOQUEIO_VALIDADE = 30  # RN-L05
MESES_MINIMOS_RECEBIMENTO = 6  # RN-L07
