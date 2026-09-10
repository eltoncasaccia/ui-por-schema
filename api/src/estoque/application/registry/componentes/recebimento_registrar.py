"""`recebimento_registrar` — o primeiro formulário de escrita. T-026, ADR-0005.

**Unidade inteira, nunca composta peça por peça** (`tamanho="inteira"`, AC-9).
Este é o formulário que testa o ADR-0005 na prática: nota → itens → conferência →
confirmação tem estado entre etapas, validação cruzada e foco. Se a tentação de
quebrá-lo em blocos aparecer, ela é exatamente o que o ADR proíbe.

**O `ean` é param, e é assim que o leitor de código de barras funciona** (AC-8,
`RNF-02`). O operador dispara o leitor, o cliente repede os dados deste
componente com `ean=<o que veio>`, e o `load` resolve para produto com
`RepoProduto.por_ean` (T-048). Nenhuma rota nova: o recorte é param, a resolução
é `load`, a projeção é `select` — a mesma forma de todo componente do catálogo.

**Este componente não escreve.** Ele descreve o formulário (ADR-0002): o `load`
traz o que o preenchimento precisa, e o `CommandDef` diz para onde postar. Quem
grava é `commands/recebimento.py`, alcançado só por quem clica em confirmar.
"""

from pydantic import BaseModel

from estoque.application.commands.entradas.recebimento import (
    DIAS_VALIDADE_MINIMA,
    EntradaRecebimento,
)
from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE
from estoque.application.registry.definir import CommandDef, ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.identidade import UnidadeId
from estoque.domain.tipos import ClasseProduto, Produto

# RN-L01: os três que não são opcionais em lote nenhum. Vão para o viewmodel
# porque a tela precisa marcá-los, e o servidor os exige de qualquer jeito.
OBRIGATORIOS_DO_ITEM = ("numero", "fabricacao", "validade")


class Params(BaseModel):
    unidade_id: UnidadeId | None = None
    # O que o LEITOR devolveu. Identificador externo, não recorte — não há enum
    # possível para um EAN, e o que protege aqui não é a validação do param: é
    # `por_ean` não intersectar escopo porque produto não pertence a unidade.
    ean: str | None = None


class UnidadeDestino(BaseModel):
    id: str
    nome: str


class ProdutoLido(BaseModel):
    """O que o leitor resolveu, já com o que a classe do produto exige.

    `exige_temperatura` e `exige_rt` são calculados **no servidor**, a partir da
    classe. Se fossem decididos no cliente, um formulário adulterado marcaria o
    termolábil como dispensando temperatura — e a interface é payload
    não-confiável como qualquer outro (ADR-0004). A recusa real acontece no
    comando de qualquer forma; isto aqui é para a tela não pedir errado.
    """

    produto_id: str
    ean: str
    nome: str
    fabricante: str
    classe: ClasseProduto
    exige_temperatura: bool
    exige_rt: bool


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05, ADR-0020).

    `Produto` carrega custo para quem tem `custo.ler`, e `ProdutoLido` não o
    declara — o que não entra no viewmodel não chega ao navegador.
    """

    unidades: list[UnidadeDestino]
    unidade_sugerida: str | None
    # RN-L07, para a tela avisar antes de o servidor recusar.
    validade_minima_dias: int
    obrigatorios_do_item: list[str]

    # Preenchido quando veio `ean`. Um dos dois, nunca os dois.
    lido: ProdutoLido | None = None
    ean_nao_encontrado: str | None = None


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    unidades: list[str]
    unidade_sugerida: str | None
    ean_pedido: str | None
    produto: Produto | None


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    produto: Produto | None = None
    if params.ean:
        # T-048. Não intersecta unidade de propósito: o conferente tem a caixa na
        # mão, e esconder o produto porque ele "não é desta unidade" faria a tela
        # dizer que a mercadoria não existe.
        produto = await ctx.repos.produto.por_ean(params.ean, ctx.dados)

    return Dados(
        # As unidades vêm do escopo já intersectado (RN-A01), não de consulta:
        # não há `RepoUnidade` na porta, e o formulário não precisa dos atributos
        # dela — quem recusa termolábil em unidade seca é o comando (RN-P02).
        unidades=sorted(ctx.unidades_permitidas),
        unidade_sugerida=params.unidade_id,
        ean_pedido=params.ean,
        produto=produto,
    )


def _lido(p: Produto) -> ProdutoLido:
    return ProdutoLido(
        produto_id=p.id,
        ean=p.ean,
        nome=p.nome,
        fabricante=p.fabricante,
        classe=p.classe,
        # RN-F01 e RN-R05: a exigência vem da CLASSE, e é o servidor que a diz.
        exige_temperatura=p.classe == "termolabil",
        exige_rt=p.classe == "controlado",
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: sem I/O, sem relógio."""
    return VM(
        unidades=[UnidadeDestino(id=u, nome=NOME_UNIDADE.get(u, u)) for u in d.unidades],
        unidade_sugerida=d.unidade_sugerida,
        validade_minima_dias=DIAS_VALIDADE_MINIMA,
        obrigatorios_do_item=list(OBRIGATORIOS_DO_ITEM),
        lido=_lido(d.produto) if d.produto else None,
        # Scan que não achou: a tela avisa e o operador digita. Não é erro —
        # produto novo é caso normal num recebimento.
        ean_nao_encontrado=d.ean_pedido if (d.ean_pedido and d.produto is None) else None,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="recebimento_registrar",
        label="Registrar recebimento",
        description=(
            "Formulário para registrar a entrada de mercadoria: nota fiscal, "
            "fornecedor, itens com número de lote, fabricação, validade e "
            "quantidade, e a conferência. Aceita o código de barras do produto "
            "no parâmetro `ean`. Use quando pedirem para registrar, dar entrada "
            "ou lançar um recebimento. Mostra o formulário; quem grava é quem "
            "confirma."
        ),
        examples=(
            "quero registrar um recebimento",
            "chegou mercadoria do fornecedor",
            "dar entrada nessa nota fiscal",
        ),
        params=Params,
        requires="recebimento.criar",
        # ADR-0005 e AC-9: formulário é unidade inteira. O validador de schema
        # recusa compor este bloco junto de outros.
        tamanho="inteira",
        load=carregar,
        select=projetar,
        commands={
            # A chave É o nome do comando executável (`commands/recebimento.py`),
            # e a bijeção entre os dois é verificada em teste.
            "recebimento_registrar": CommandDef(
                endpoint="/api/comandos/recebimento_registrar",
                # O MESMO schema que o comando usa para validar. Duas declarações
                # do formulário divergiriam no dia em que uma mudasse.
                schema=EntradaRecebimento,
                requires="recebimento.criar",
                confirm=True,
                # Repetir DUPLICA: cria recebimento, lotes e movimentos novos.
                # `Idempotency-Key` vira obrigatório na borda (CONTRATOS §8).
                idempotent=False,
            )
        },
    )
)
