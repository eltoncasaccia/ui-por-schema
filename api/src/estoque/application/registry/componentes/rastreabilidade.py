"""`rastreabilidade` — o recall da losartana, que levou nove dias. Alvo: 60 s.

RN-D03: dado um lote, os clientes que o receberam, com nota e data.
RN-D04: dado um cliente e um periodo, os lotes que ele recebeu.
Um componente, duas direcoes — fusao do ADR-0011. O recorte e' `direcao`, valor
nomeado no enum, nunca texto livre.

RN-D05 (consulta de auditoria e' auditada) NAO e' feito aqui: quem grava o
evento de leitura e' a borda (`server/rotas/dados.py`), num lugar so', para toda
leitura — inclusive o `direcao` e os params, em `valor_novo`.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, model_validator

from estoque.application.registry.definir import ComponentDef, LoadContext
from estoque.application.registry.registry import registrar
from estoque.domain.tipos import Movimento

# Recorte DESTE componente, nao entidade de dominio: fica aqui como Literal, que
# alimenta o enum do catalogo e a validacao cruzada de `Params`.
Direcao = Literal["lote_para_clientes", "cliente_para_lotes"]


class Params(BaseModel):
    direcao: Direcao
    # lote_para_clientes:
    lote_id: str | None = None
    # cliente_para_lotes:
    cliente_id: str | None = None
    de: date | None = None
    ate: date | None = None

    @model_validator(mode="after")
    def _coerencia(self) -> "Params":
        # AC-6: params incoerentes com a direcao sao rejeitados NA VALIDACAO,
        # antes do `load`. `validar_schema` chama `Params.model_validate`, entao
        # um schema forjado tambem bate aqui.
        if self.direcao == "lote_para_clientes":
            if not self.lote_id:
                raise ValueError("lote_para_clientes exige lote_id")
            if self.cliente_id or self.de or self.ate:
                raise ValueError("lote_para_clientes nao aceita cliente_id, de ou ate")
        else:
            if not (self.cliente_id and self.de and self.ate):
                raise ValueError("cliente_para_lotes exige cliente_id, de e ate")
            if self.lote_id:
                raise ValueError("cliente_para_lotes nao aceita lote_id")
            if self.de > self.ate:
                raise ValueError("de posterior a ate")
        return self


class SaidaParaCliente(BaseModel):
    cliente: str
    nota_fiscal: str | None
    data: date
    quantidade: int


class LoteDeCliente(BaseModel):
    lote_id: str
    numero: str
    produto: str
    quantidade_total: int
    primeira: date
    ultima: date


class VM(BaseModel):
    """Sem custo nem margem (CA-05): `Movimento` nao os carrega, e nada aqui os
    busca. So' uma das duas listas vem preenchida, conforme `direcao`."""

    direcao: Direcao
    alvo: str
    recorte: str
    total_saidas: int
    total_quantidade: int
    clientes: list[SaidaParaCliente] = []
    lotes: list[LoteDeCliente] = []


class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    direcao: Direcao
    alvo: str
    recorte: str
    saidas: list[Movimento]
    # nome de lote e de produto para o sentido cliente -> lotes
    numero_do_lote: dict[str, str]
    nome_do_produto: dict[str, str]


async def carregar(params: Params, ctx: LoadContext) -> Dados:
    # `_coerencia` ja' garantiu os campos por direcao; os guards abaixo sao para
    # o verificador de tipos, nao logica nova. Repetem a mensagem do validador.
    if params.direcao == "lote_para_clientes":
        if params.lote_id is None:
            raise ValueError("lote_para_clientes exige lote_id")
        movs = await ctx.repos.movimento.do_lote(params.lote_id, ctx.dados)
        # So' saida com destinatario e' entrega a cliente. `do_lote` ja' aplicou
        # o escopo (RN-A01): lote de outra unidade volta vazio.
        saidas = [mv for mv in movs if mv.tipo == "saida" and mv.cliente_id]
        return Dados(
            direcao=params.direcao,
            alvo=params.lote_id,
            recorte="histórico completo do lote",
            saidas=saidas,
            numero_do_lote={},
            nome_do_produto={},
        )

    if params.cliente_id is None or params.de is None or params.ate is None:
        raise ValueError("cliente_para_lotes exige cliente_id, de e ate")
    de, ate = params.de, params.ate
    movs = await ctx.repos.movimento.por_cliente(params.cliente_id, de, ate, ctx.dados)
    # A porta NAO aplica `de`/`ate` (fake e repositorio real ignoram os dois
    # argumentos — achado A-31). O recorte de periodo do RN-D04 e' feito aqui.
    no_periodo = [mv for mv in movs if mv.tipo == "saida" and de <= mv.criado_em.date() <= ate]

    ids_lote = {mv.lote_id for mv in no_periodo}
    numero: dict[str, str] = {}
    produto_por_lote: dict[str, str] = {}
    ids_produto: dict[str, str] = {}
    for lid in sorted(ids_lote):
        lote = await ctx.repos.lote.por_id(lid, ctx.dados)
        if lote is not None:
            numero[lid] = lote.numero
            ids_produto[lid] = lote.produto_id
    produtos = await ctx.repos.produto.por_ids(sorted(set(ids_produto.values())), ctx.dados)
    for lid, pid in ids_produto.items():
        p = produtos.get(pid)
        produto_por_lote[lid] = p.nome if p else pid

    return Dados(
        direcao=params.direcao,
        alvo=params.cliente_id,
        recorte=f"{params.de.isoformat()} a {params.ate.isoformat()}",
        saidas=no_periodo,
        numero_do_lote=numero,
        nome_do_produto=produto_por_lote,
    )


def projetar(d: Dados) -> VM:
    """Roda NO SERVIDOR (ADR-0020). Pura: sem I/O, sem relogio."""
    total_qtd = sum(mv.quantidade for mv in d.saidas)

    if d.direcao == "lote_para_clientes":
        clientes = sorted(
            (
                SaidaParaCliente(
                    cliente=mv.cliente_id or "—",
                    nota_fiscal=mv.nota_fiscal,
                    data=mv.criado_em.date(),
                    quantidade=mv.quantidade,
                )
                for mv in d.saidas
            ),
            key=lambda x: (x.data, x.cliente, x.nota_fiscal or ""),
        )
        return VM(
            direcao=d.direcao,
            alvo=d.alvo,
            recorte=d.recorte,
            total_saidas=len(d.saidas),
            total_quantidade=total_qtd,
            clientes=clientes,
        )

    # cliente_para_lotes: agrega por lote
    por_lote: dict[str, list[Movimento]] = {}
    for mv in d.saidas:
        por_lote.setdefault(mv.lote_id, []).append(mv)
    lotes = sorted(
        (
            LoteDeCliente(
                lote_id=lid,
                numero=d.numero_do_lote.get(lid, lid),
                produto=d.nome_do_produto.get(lid, lid),
                quantidade_total=sum(mv.quantidade for mv in movs),
                primeira=min(mv.criado_em.date() for mv in movs),
                ultima=max(mv.criado_em.date() for mv in movs),
            )
            for lid, movs in por_lote.items()
        ),
        key=lambda x: (x.primeira, x.lote_id),
    )
    return VM(
        direcao=d.direcao,
        alvo=d.alvo,
        recorte=d.recorte,
        total_saidas=len(d.saidas),
        total_quantidade=total_qtd,
        lotes=lotes,
    )


COMPONENTE = registrar(
    ComponentDef(
        id="rastreabilidade",
        label="Rastreabilidade",
        description=(
            "Segue um lote ate' os clientes que o receberam (com nota fiscal, "
            "data e quantidade), ou um cliente ate' os lotes que ele recebeu num "
            "periodo. Escolha o sentido em `direcao`. Use para recall, "
            "investigacao de origem e resposta a orgao regulador."
        ),
        examples=(
            "quem recebeu o lote do recall",
            "para quais clientes esse lote foi",
            "que lotes a Farmacia Sao Joao recebeu no ultimo mes",
        ),
        params=Params,
        requires="auditoria.rastrear",
        tamanho="inteira",
        load=carregar,
        select=projetar,
    )
)
