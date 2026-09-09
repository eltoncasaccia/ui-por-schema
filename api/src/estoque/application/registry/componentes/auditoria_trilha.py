"""`auditoria_trilha` — quem fez o quê, e o que mudou.

A trilha é `append-only` no banco (`RN-D02`, migração 0001): nem o Diretor edita
ou apaga. Aqui ela é só lida — e **ler a trilha também é auditado** (`RN-D05`),
pelo mesmo endpoint que audita toda leitura. Quem consultou o quê importa.

**A armadilha do AC-5, e ela é a mais fácil de deixar passar no projeto inteiro.**

O custo é escondido em `produto_ficha`, some do enum de `estoque_indicador` e
não entra em viewmodel nenhum. E aí reaparece pela porta dos fundos: um comando
grava `valor_novo = {"custo_unitario_centavos": 1250}` na trilha, e a trilha é
lida por quem tem `auditoria.ler`.

Hoje nenhum comando escreve custo — conferido. Mas "hoje nenhum" não é garantia:
é o estado atual de quatro comandos que outra pessoa vai estender. Por isso o
filtro está **na leitura**, e não na escrita: `_sem_custo` remove qualquer chave
que cheire a dinheiro, em qualquer profundidade, antes de o valor virar
viewmodel.

**Some para todo mundo, inclusive para Marco e Sandra**, que têm `custo.ler`. A
regra da casa é que custo não entra em viewmodel para papel nenhum (`CA-05`), e
uma exceção por papel seria mais uma condição a errar. Quando existir CRUD de
produto e auditar mudança de custo virar necessidade real, a decisão se revisa
com um caso concreto na mão — não antes.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel

from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.data.porta import LinhaAuditoria

DIAS: dict[str, int | None] = {"7": 7, "30": 30, "90": 90, "365": 365, "tudo": None}

# Fragmentos que denunciam dinheiro. Comparados em minúsculas, por substring:
# `custo_unitario_centavos`, `total_centavos` e `valorEmEstoque` caem todos aqui.
CHEIRO_DE_DINHEIRO = ("custo", "centavos", "preco", "preço", "valor_em_estoque", "margem")

LIMITE = 50


class Params(BaseModel):
    ator_id: str | None = None
    # Enum fechado, e não texto livre: são as entidades que a trilha registra.
    # Texto livre aqui deixaria o modelo inventar nome de entidade e receber
    # lista vazia, que é a falha silenciosa do risco R-5.
    entidade: Literal["lote", "movimento", "comando", "recebimento", "usuario"] | None = None
    periodo: Literal["7", "30", "90", "365", "tudo"] = "30"


class LinhaTrilha(BaseModel):
    id: int
    criado_em: datetime
    ator: str | None
    acao: str
    entidade: str | None
    entidade_id: str | None
    origem: str
    valor_anterior: dict[str, Any] | None
    valor_novo: dict[str, Any] | None
    # Verdadeiro quando `_sem_custo` tirou alguma coisa. A trilha não mente
    # sobre ter sido filtrada: dizer "havia mais aqui" é diferente de omitir.
    filtrada: bool = False


class VM(BaseModel):
    """Sem custo, para papel nenhum (CA-05) — inclusive em `valor_novo`."""

    total: int
    recorte: str
    truncada: bool
    linhas: list[LinhaTrilha]


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    linhas: list[LinhaAuditoria]
    recorte: str
    truncada: bool


def _sem_custo(valor: object) -> tuple[object, bool]:
    """Remove chave com cheiro de dinheiro, em qualquer profundidade.

    Devolve o valor limpo e se removeu algo. Recursivo porque `valor_novo` é
    JSON livre — a forma depende de qual comando escreveu, e um `{"antes":
    {"custo": 1250}}` passaria por um filtro de um nível só.
    """
    if isinstance(valor, dict):
        limpo: dict[str, Any] = {}
        removeu = False
        for chave, v in valor.items():
            if any(c in str(chave).lower() for c in CHEIRO_DE_DINHEIRO):
                removeu = True
                continue
            filho, removeu_no_filho = _sem_custo(v)
            limpo[str(chave)] = filho
            removeu = removeu or removeu_no_filho
        return limpo, removeu
    if isinstance(valor, list):
        saida = [_sem_custo(x) for x in valor]
        return [x for x, _ in saida], any(r for _, r in saida)
    return valor, False


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    agora = datetime.now(UTC)
    dias = DIAS[params.periodo]
    de = agora - timedelta(days=dias) if dias else None

    # `limite + 1` para saber se truncou sem contar a tabela inteira — a trilha
    # cresce sem parar, e `COUNT(*)` nela fica caro exatamente quando importa.
    linhas = list(
        await ctx.repos.auditoria.listar(
            ctx.dados,
            ator_id=params.ator_id,
            entidade=params.entidade,
            de=de,
            limite=LIMITE + 1,
        )
    )
    truncada = len(linhas) > LIMITE
    return Dados(
        linhas=linhas[:LIMITE],
        recorte="todo o período" if dias is None else f"últimos {dias} dias",
        truncada=truncada,
    )


def _linha(x: LinhaAuditoria) -> LinhaTrilha:
    anterior, removeu_a = _sem_custo(x.valor_anterior) if x.valor_anterior else (None, False)
    novo, removeu_n = _sem_custo(x.valor_novo) if x.valor_novo else (None, False)
    return LinhaTrilha(
        id=x.id,
        criado_em=x.criado_em,
        ator=x.ator_id,
        acao=x.acao,
        entidade=x.entidade,
        entidade_id=x.entidade_id,
        origem=x.origem,
        valor_anterior=anterior if isinstance(anterior, dict) else None,
        valor_novo=novo if isinstance(novo, dict) else None,
        filtrada=removeu_a or removeu_n,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura — a filtragem não depende de relógio."""
    return VM(
        total=len(d.linhas),
        recorte=d.recorte,
        truncada=d.truncada,
        linhas=[_linha(x) for x in d.linhas],
    )


COMPONENTE = registrar(
    ComponentDef(
        id="auditoria_trilha",
        label="Trilha de auditoria",
        description=(
            "Mostra a trilha de auditoria: quem fez o quê, quando, de onde e o "
            "que mudou, com o valor anterior e o novo. Filtra por autor, tipo de "
            "entidade e período. Serve para investigar uma operação específica ou "
            "reconstruir o que aconteceu com um registro. A trilha não pode ser "
            "editada nem apagada por ninguém."
        ),
        examples=(
            "quem liberou esse lote",
            "o que a Helena fez esta semana",
            "mostra a trilha de auditoria dos últimos 7 dias",
        ),
        params=Params,
        requires="auditoria.ler",
        tamanho="inteira",
        load=carregar,
        select=projetar,
        # Sem `commands`: RN-D02. Não há o que oferecer — a trilha não se edita.
    )
)
