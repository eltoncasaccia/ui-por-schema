"""`recebimento_detalhe` — UM recebimento, com o que decide se ele pode concluir.

Como `lote_detalhe`, o componente existe em cima de uma negativa: um recebimento
de outra unidade responde `nao_encontrado`, identico a um id que nunca existiu
(ADR-0014, `CS-03`). Quem aplica o escopo e' a porta (`RN-A01`): `por_id`
devolve `None` para fora do escopo pelo mesmo caminho do inexistente.

**O que a conferencia registra, e o que ela nao registra.** `RN-R03` exige
conferencia de integridade da embalagem, validade minima, nota fiscal e — se
termolabil — temperatura de chegada. Dessas quatro, so' `nota_fiscal` e
`temperatura_chegada_c` tem coluna no `Recebimento` congelado (CONTRATOS §3);
integridade e validade como itens conferidos separadamente NAO tem armazenamento
(achado A-33). Este componente mostra o que existe: o `status` da conferencia,
a nota, a temperatura de chegada, as duas identificacoes e a pendencia de
divergencia.
"""

from datetime import datetime

from pydantic import BaseModel

from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.componentes.recebimento_lista import (
    ROTULO_STATUS,
    StatusRecebimento,
)
from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.erros import nao_encontrado
from estoque.domain.tipos import Recebimento


class Params(BaseModel):
    # Identificador, nao recorte: nao ha' enum para um id. O que protege aqui e'
    # o escopo do repositorio, nao a validacao do param.
    recebimento_id: str


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05). `Recebimento` nao carrega custo e
    nada aqui o busca."""

    recebimento_id: str
    recebido_em: datetime
    unidade: str
    fornecedor: str
    nota_fiscal: str
    # A conferencia registrada, na forma que o schema guarda: o estado do fluxo.
    status: StatusRecebimento
    status_rotulo: str
    # RN-R05: as duas identificacoes. `responsavel_tecnico` so' vem preenchido
    # em recebimento de controlado — e' ele o sinal de que houve a dupla ID.
    # Mostrar so' o conferente esconderia metade do que a regra exige.
    conferente: str
    responsavel_tecnico: str | None
    # RN-F01: temperatura de chegada, presente so' em carga termolabil.
    temperatura_chegada_c: float | None
    # RN-R04: divergencia entre nota e fisico gera pendencia vinculada, e a
    # pendencia NAO impede a conclusao — por isso e' um campo a mais, nao um
    # estado que substitui `status`.
    tem_pendencia_divergencia: bool


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    recebimento: Recebimento


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    r = await ctx.repos.recebimento.por_id(params.recebimento_id, ctx.dados)
    if r is None:
        # Fora do escopo e inexistente chegam aqui pelo MESMO caminho e saem
        # pela mesma porta. O `detalhe_interno` vai para o log e nunca e'
        # serializado — e' o unico lugar onde os dois se distinguem.
        raise nao_encontrado({"recebimento_id": params.recebimento_id, "ator": ctx.ator.id})
    return Dados(recebimento=r)


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: sem I/O, sem relogio."""
    r = d.recebimento
    return VM(
        recebimento_id=r.id,
        recebido_em=r.recebido_em,
        unidade=NOME_UNIDADE.get(r.unidade_id, r.unidade_id),
        fornecedor=r.fornecedor,
        nota_fiscal=r.nota_fiscal,
        status=r.status,
        status_rotulo=ROTULO_STATUS[r.status],
        conferente=r.conferente_id,
        responsavel_tecnico=r.rt_id,
        temperatura_chegada_c=r.temperatura_chegada_c,
        tem_pendencia_divergencia=r.divergencia,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="recebimento_detalhe",
        label="Recebimento",
        description=(
            "Mostra UM recebimento pelo seu identificador: fornecedor, nota "
            "fiscal, data, estado da conferência, conferente e responsável "
            "técnico, temperatura de chegada quando a carga é termolábil, e a "
            "pendência de divergência entre nota e físico quando existe. Use "
            "quando a pergunta for sobre um recebimento específico já "
            "identificado, não para procurar ou listar vários — para isso "
            "existe `recebimento_lista`."
        ),
        examples=(
            "detalhes desse recebimento",
            "quem conferiu essa entrada",
            "esse recebimento teve divergência",
        ),
        params=Params,
        requires="recebimento.ler",
        tamanho="inteira",
        load=carregar,
        select=projetar,
    )
)
