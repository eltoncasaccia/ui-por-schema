"""`relatorio_movimentacao` — a mesma pergunta sobre movimento, com o eixo trocado.

ADR-0029: um componente por corte esgota o teto de 25 antes de esgotar a
necessidade. Aqui o corte e' param — `agrupar_por` x `metrica` x `tipo` x
`periodo` —, cada um enum fechado. Eixo que falta nao vira texto livre: vira
achado (risco R-5).

**Leitura cortada e' declarada (AC-9, A-39).** O repositorio devolve no maximo
os movimentos mais recentes ate' o teto. Total sobre leitura cortada e' numero
errado com cara de certo; o viewmodel diz `truncado`, e a tela diz que e' amostra.

**So' efetivado conta:** pendente e recusado nao movimentaram estoque (RN-M06).
"""

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel

from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.definir import ComponentDef, LoadContext, RequiresPorValor
from estoque.application.registry.registry import registrar
from estoque.domain.identidade import UnidadeId
from estoque.domain.tipos import Movimento, Produto

# Espelha `LIMITE_MOVIMENTOS` do adaptador. Importar de la' traria `sqlalchemy`
# para o registry (contrato 2); o teste deste componente prova que os dois batem.
TETO_DE_LEITURA = 500

Eixo = Literal["unidade", "produto", "motivo", "mes", "classe"]
Metrica = Literal["quantidade", "movimentos", "valor"]
Medida = Literal["unidades", "movimentos", "centavos"]

DIAS: dict[str, int] = {"30": 30, "90": 90, "180": 180, "365": 365}
ROTULO_EIXO: dict[str, str] = {
    "unidade": "por unidade",
    "produto": "por produto",
    "motivo": "por motivo",
    "mes": "por mês",
    "classe": "por classe",
}
ROTULO_METRICA: dict[str, str] = {
    "quantidade": "Quantidade movimentada",
    "movimentos": "Movimentos",
    "valor": "Valor movimentado",
}
MEDIDA: dict[str, Medida] = {
    "quantidade": "unidades",
    "movimentos": "movimentos",
    "valor": "centavos",
}


class Params(BaseModel):
    agrupar_por: Eixo
    metrica: Metrica = "quantidade"
    tipo: Literal["entrada", "saida", "descarte", "estorno", "todos"] = "todos"
    periodo: Literal["30", "90", "180", "365"] = "90"
    unidade_id: UnidadeId | None = None


class Linha(BaseModel):
    chave: str
    rotulo: str
    numero: int
    movimentos: int


class VM(BaseModel):
    """Custo so' aparece com `metrica: valor`, e ja' agregado (AC-3)."""

    eixo: str
    metrica: Metrica
    metrica_rotulo: str
    unidade_medida: Medida
    total: int
    grupos: int
    escopo: str
    recorte: str
    truncado: bool
    linhas: list[Linha]
    cursor: str | None = None
    tem_mais: bool = False


class Fato(BaseModel):
    chave: str
    rotulo: str
    quantidade: int
    valor_centavos: int


class Dados(BaseModel):
    params: Params
    fatos: list[Fato]
    escopo: str
    recorte: str
    truncado: bool
    limite: int
    cursor: str | None


def _fato(m: Movimento, params: Params, p: Produto | None) -> Fato:
    eixo = params.agrupar_por
    chave: str
    rotulo: str
    if eixo == "unidade":
        chave, rotulo = m.unidade_id, NOME_UNIDADE.get(m.unidade_id, m.unidade_id)
    elif eixo == "motivo":
        chave, rotulo = m.motivo, m.motivo.replace("_", " ")
    elif eixo == "mes":
        chave, rotulo = m.criado_em.strftime("%Y-%m"), m.criado_em.strftime("%m/%Y")
    elif eixo == "classe":
        chave = rotulo = p.classe if p else "desconhecida"
    else:
        chave, rotulo = (p.id, p.nome) if p else (m.lote_id, m.lote_id)
    custo = p.custo_unitario_centavos if p and p.custo_unitario_centavos is not None else 0
    return Fato(
        chave=chave,
        rotulo=rotulo,
        quantidade=m.quantidade,
        valor_centavos=m.quantidade * custo if params.metrica == "valor" else 0,
    )


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    agora = datetime.now(UTC)
    movs = list(
        await ctx.repos.movimento.listar(
            ctx.dados,
            unidade_id=params.unidade_id,
            tipo=None if params.tipo == "todos" else params.tipo,
            status="efetivado",
            de=agora - timedelta(days=DIAS[params.periodo]),
        )
    )

    produto_de_lote: dict[str, Produto] = {}
    if params.agrupar_por in {"produto", "classe"} or params.metrica == "valor":
        # Duas leituras, sem N+1 e sem `RepoLote.por_ids`, que a porta nao tem.
        lotes = await ctx.repos.lote.listar(ctx.dados, unidade_id=params.unidade_id)
        produtos = await ctx.repos.produto.por_ids(
            sorted({x.produto_id for x in lotes}), ctx.dados
        )
        produto_de_lote = {
            x.id: produtos[x.produto_id] for x in lotes if x.produto_id in produtos
        }

    if params.unidade_id:
        escopo = NOME_UNIDADE.get(params.unidade_id, params.unidade_id)
    else:
        n = len(ctx.unidades_permitidas)
        escopo = f"{n} unidade{'s' if n != 1 else ''}"

    truncado = len(movs) >= TETO_DE_LEITURA
    tipo = "todos os tipos" if params.tipo == "todos" else params.tipo
    recorte = f"últimos {DIAS[params.periodo]} dias · {tipo} · só efetivados"
    if truncado:
        recorte += f" · amostra: os {TETO_DE_LEITURA} mais recentes"

    return Dados(
        params=params,
        fatos=[_fato(m, params, produto_de_lote.get(m.lote_id)) for m in movs],
        escopo=escopo,
        recorte=recorte,
        truncado=truncado,
        limite=ctx.pagina.limite,
        cursor=ctx.pagina.cursor,
    )


def _numero(metrica: Metrica, fatos: list[Fato]) -> int:
    if metrica == "movimentos":
        return len(fatos)
    if metrica == "valor":
        return sum(f.valor_centavos for f in fatos)
    return sum(f.quantidade for f in fatos)


def projetar(d: Dados) -> VM:
    """Pura: agrega, ordena e pagina o que o `load` trouxe."""
    metrica = d.params.metrica
    grupos: dict[str, list[Fato]] = {}
    for f in d.fatos:
        grupos.setdefault(f.chave, []).append(f)
    linhas = [
        Linha(chave=k, rotulo=fs[0].rotulo, numero=_numero(metrica, fs), movimentos=len(fs))
        for k, fs in grupos.items()
    ]
    if d.params.agrupar_por == "mes":
        linhas.sort(key=lambda x: x.chave)
    else:
        linhas.sort(key=lambda x: (-x.numero, x.rotulo))

    inicio = 0
    if d.cursor:
        inicio = next((i + 1 for i, x in enumerate(linhas) if x.chave == d.cursor), len(linhas))
    fatia = linhas[inicio : inicio + d.limite]
    tem_mais = inicio + d.limite < len(linhas)

    return VM(
        eixo=ROTULO_EIXO[d.params.agrupar_por],
        metrica=metrica,
        metrica_rotulo=ROTULO_METRICA[metrica],
        unidade_medida=MEDIDA[metrica],
        total=_numero(metrica, d.fatos),
        grupos=len(linhas),
        escopo=d.escopo,
        recorte=d.recorte,
        truncado=d.truncado,
        linhas=fatia,
        cursor=fatia[-1].chave if fatia and tem_mais else None,
        tem_mais=tem_mais,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="relatorio_movimentacao",
        label="Relatório de movimentação",
        # Nao enumera as metricas: o enum de `metrica` e' filtrado por permissao,
        # e a prosa vazaria o que o filtro tirou (AC-8).
        description=(
            "Relatório AGREGADO de movimentos efetivados: agrupa pelo eixo de "
            "`agrupar_por` e soma a métrica de `metrica`, no período e tipo pedidos, "
            "com o total geral. Use para totais, comparação ou ranking. NÃO use para "
            "ver movimentos um a um, pendências de autorização ou o histórico de um "
            "lote — isso é `movimento_lista`."
        ),
        examples=(
            "quanto saiu por produto nos últimos 90 dias",
            "descartes por motivo no último ano",
            "movimentação por mês",
            "entradas por unidade",
        ),
        params=Params,
        requires=RequiresPorValor(
            base=("movimento.ler",),
            por_valor={"metrica": {"valor": ("custo.ler",)}},
        ),
        tamanho="inteira",
        load=carregar,
        select=projetar,
    )
)
