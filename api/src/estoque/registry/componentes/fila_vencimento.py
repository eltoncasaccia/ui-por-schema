"""`fila_vencimento` — CA-03. O episodio dos R$ 183 mil vencidos em prateleira.

Exemplo completo de um componente: params, permissao, carga autorizada, projecao
no servidor (ADR-0020) e o viewmodel que atravessa a rede.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from estoque.domain.identidade import UnidadeId
from estoque.domain.regras.validade import classificar_validade, dias_ate_vencer
from estoque.domain.tipos import Lote
from estoque.registry.definir import ComponentDef, LoadContext
from estoque.registry.registry import registrar


class Params(BaseModel):
    # Enum, nunca data livre: todo recorte que o usuario sabe pedir precisa
    # existir no catalogo como VALOR NOMEADO. Filtro que falta alarga a resposta
    # em silencio — o achado mais perigoso da v1 (risco R-5 do PRD).
    janela: Literal["30", "60", "90"] = "90"
    unidade_id: UnidadeId | None = None


class LinhaVencimento(BaseModel):
    lote_id: str
    produto: str
    numero: str
    unidade: str
    validade: date
    dias_restantes: int
    saldo: int
    situacao: Literal["ok", "alerta_90", "bloqueio_30", "vencido"]


class VM(BaseModel):
    """O viewmodel. E' EXATAMENTE isto que atravessa a rede — nada de `Lote`,
    nada de linha de banco, nada de custo (ADR-0020, CA-05)."""

    janela_dias: int
    total: int
    linhas: list[LinhaVencimento]


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    lotes: list[Lote]
    saldos: dict[str, int]
    nomes: dict[str, str]
    hoje: date
    janela_dias: int


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    from datetime import timedelta

    hoje = date.today()
    limite = hoje + timedelta(days=int(params.janela))
    lotes = list(
        await ctx.repos.lote.listar(
            ctx.dados, unidade_id=params.unidade_id, validade_ate=limite
        )
    )
    ids = [lote.id for lote in lotes]
    saldos = await ctx.repos.lote.saldos(ids, ctx.dados)
    produtos = await ctx.repos.produto.por_ids([lote.produto_id for lote in lotes], ctx.dados)
    nomes = {pid: p.nome for pid, p in produtos.items()}
    return Dados(
        lotes=lotes,
        saldos=saldos,
        nomes=nomes,
        hoje=hoje,
        janela_dias=int(params.janela),
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: sem I/O, sem relogio."""
    linhas = [
        LinhaVencimento(
            lote_id=lote.id,
            produto=d.nomes.get(lote.produto_id, lote.produto_id),
            numero=lote.numero,
            unidade=lote.unidade_id,
            validade=lote.validade,
            dias_restantes=dias_ate_vencer(lote, d.hoje),
            saldo=d.saldos.get(lote.id, 0),
            situacao=classificar_validade(lote, d.hoje),
        )
        for lote in d.lotes
        if d.saldos.get(lote.id, 0) > 0
    ]
    linhas.sort(key=lambda x: (x.validade, x.lote_id))
    return VM(janela_dias=d.janela_dias, total=len(linhas), linhas=linhas)


COMPONENTE = registrar(
    ComponentDef(
        id="fila_vencimento",
        label="Fila de vencimento",
        description=(
            "Lista os lotes que vencem dentro de uma janela de 30, 60 ou 90 dias, "
            "com saldo, validade e dias restantes, apenas das unidades do usuario. "
            "Use quando perguntarem o que esta vencendo, o que vence em breve, ou "
            "o que precisa de atencao por validade."
        ),
        examples=(
            "o que vence nos proximos 90 dias",
            "lotes vencendo em Uberlandia",
            "o que precisa sair rapido",
        ),
        params=Params,
        requires="lote.ler",
        tamanho="inteira",
        load=carregar,
        select=projetar,
    )
)
