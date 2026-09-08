"""`lote_detalhe` — um lote, com o que decide o que fazer com ele.

O componente inteiro existe em cima de uma negativa: um lote de outra unidade
responde `nao_encontrado`, **identico a um id que nunca existiu** (ADR-0014,
`CS-03`). Distinguir "existe mas voce nao pode" de "nao existe" transformaria
este endpoint num oraculo de enumeracao — iterando ids, descobre-se o estoque
das unidades alheias sem ver um dado sequer.

Quem aplica o escopo e' a porta de dados (RN-A01): `por_id` devolve `None` para
fora do escopo, pelo mesmo caminho do inexistente. Este `load` nao tem como
distinguir os dois — e e' de proposito que nao tenha.
"""

from datetime import date

from pydantic import BaseModel

from estoque.domain.erros import nao_encontrado
from estoque.domain.regras.validade import (
    ClasseValidade,
    classificar_validade,
    dias_ate_vencer,
    status_efetivo,
)
from estoque.domain.tipos import ClasseProduto, Lote, StatusLoteEfetivo, StatusLoteRegistrado
from estoque.registry.definir import ComponentDef, LoadContext
from estoque.registry.registry import registrar


class Params(BaseModel):
    # Identificador, nao recorte: nao ha' enum possivel para um id. O que
    # protege aqui nao e' a validacao do param, e' o escopo do repositorio.
    lote_id: str


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05). O custo unitario e' de
    `produto_ficha`; nao esta' aqui, entao nao atravessa a rede (ADR-0020)."""

    lote_id: str
    produto: str
    classe: ClasseProduto
    # RN-L01: numero, fabricacao e validade nao sao opcionais em lote nenhum.
    numero: str
    unidade: str
    fabricacao: date
    validade: date
    dias_restantes: int
    saldo: int
    # ADR-0022: os dois status, lado a lado e nomeados. `registrado` e' o que
    # alguem decidiu, com autor e auditoria; `efetivo` e' o que vale agora.
    # Mostrar so' um deles seria esconder ou a decisao ou a realidade.
    status_registrado: StatusLoteRegistrado
    status_efetivo: StatusLoteEfetivo
    situacao: ClasseValidade
    endereco: str | None


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    lote: Lote
    produto: str
    classe: ClasseProduto
    saldo: int
    hoje: date


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    lote = await ctx.repos.lote.por_id(params.lote_id, ctx.dados)
    if lote is None:
        # Fora do escopo e inexistente chegam aqui pelo MESMO caminho, e saem
        # pela mesma porta. O `detalhe_interno` vai para o log e nunca e'
        # serializado — e' o unico lugar onde os dois se distinguem.
        raise nao_encontrado({"lote_id": params.lote_id, "ator": ctx.ator.id})

    produto = await ctx.repos.produto.por_id(lote.produto_id, ctx.dados)
    # RN-M06: saldo e' a soma dos movimentos, lida da view derivada — nunca uma
    # coluna em `lote`. Campo de saldo e' campo editavel, e campo editavel e' a
    # divergencia de 3,8% do inventario de volta.
    saldos = await ctx.repos.lote.saldos([lote.id], ctx.dados)
    return Dados(
        lote=lote,
        # So' nome e classe do produto entram: `Produto` carrega o custo para
        # quem tem `custo.ler`, e o que nao entra no `Dados` nao escorrega.
        produto=produto.nome if produto else lote.produto_id,
        classe=produto.classe if produto else "comum",
        saldo=saldos.get(lote.id, 0),
        hoje=date.today(),
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: `hoje` chega pelo `Dados`."""
    return VM(
        lote_id=d.lote.id,
        produto=d.produto,
        classe=d.classe,
        numero=d.lote.numero,
        unidade=d.lote.unidade_id,
        fabricacao=d.lote.fabricacao,
        validade=d.lote.validade,
        dias_restantes=dias_ate_vencer(d.lote, d.hoje),
        saldo=d.saldo,
        status_registrado=d.lote.status,
        status_efetivo=status_efetivo(d.lote, d.saldo, d.hoje),
        situacao=classificar_validade(d.lote, d.hoje),
        endereco=d.lote.endereco,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="lote_detalhe",
        label="Lote",
        description=(
            "Mostra UM lote pelo seu identificador: produto, número, unidade, "
            "fabricação, validade, endereço, saldo e o status que vale agora. Use "
            "quando a pergunta for sobre um lote específico já identificado. NÃO "
            "use para procurar lotes ou listar vários — para isso existe "
            "`lote_lista` — nem para o histórico de entradas e saídas, que é "
            "`lote_movimentos`."
        ),
        examples=(
            "detalhes deste lote",
            "qual a validade e o saldo desse lote",
            "esse lote está liberado",
        ),
        params=Params,
        requires="lote.ler",
        tamanho="meia",
        load=carregar,
        select=projetar,
    )
)
