"""Viewmodel -> tabela: o que um arquivo exportado contem (T-054, ADR-0035).

A tabela sai do VIEWMODEL, nunca do `load`. O viewmodel e' o que o `select`
deixou atravessar a rede para ESTE ator (ADR-0020); partir dele e' o que faz o
arquivo nao ter nada que a tela nao teria. Custo que o `select` nao entregou
nao existe aqui para vazar (RN-A02).

Registro proprio, e nao campo em `ComponentDef`: mudar a assinatura do
contrato de componente para tudo (CONTRATOS §11). Componente fora deste
registro nao exporta.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from estoque.application.registry.componentes import (
    auditoria_trilha,
    fila_vencimento,
    lote_lista,
    movimento_lista,
    relatorio_movimentacao,
    temperatura_excursoes,
    temperatura_historico,
)
from estoque.application.registry.componentes.lote_lista import NOME_UNIDADE

TipoColuna = Literal["texto", "inteiro", "decimal", "data", "datahora", "reais"]
Celula = str | int | Decimal | date | datetime | None


@dataclass(frozen=True, slots=True)
class Coluna:
    titulo: str
    tipo: TipoColuna = "texto"


@dataclass(frozen=True, slots=True)
class Tabela:
    """Uma tabela so', com o contexto que a torna legivel fora da tela.

    `contexto` sao as linhas de recorte e escopo. Um numero exportado sem o
    filtro que o produziu e' um numero que alguem vai usar errado.
    """

    titulo: str
    colunas: tuple[Coluna, ...]
    linhas: list[tuple[Celula, ...]]
    contexto: list[str] = field(default_factory=list)
    nome_base: str = "exportacao"


def _unidade(id_ou_nome: str) -> str:
    """O viewmodel das listas leva o id; a tela troca pelo nome. O arquivo
    tambem, senao a planilha diz `cd-matriz` onde a pessoa leu "CD Matriz"."""
    return NOME_UNIDADE.get(id_ou_nome, id_ou_nome)


def _rotulo(codigo: str) -> str:
    """`alerta_90` -> "Alerta 90": o codigo do enum, legivel, sem mudar o valor."""
    return codigo.replace("_", " ").capitalize()


def _reais(centavos: int) -> Decimal:
    return (Decimal(centavos) / 100).quantize(Decimal("0.01"))


def _c1(v: float) -> Decimal:
    return Decimal(str(round(v, 1)))


def _relatorio(vm: relatorio_movimentacao.VM) -> Tabela:
    valor = vm.metrica == "valor"
    medida = Coluna("Valor (R$)", "reais") if valor else Coluna(vm.metrica_rotulo, "inteiro")
    linhas: list[tuple[Celula, ...]] = [
        (x.rotulo, _reais(x.numero) if valor else x.numero, x.movimentos) for x in vm.linhas
    ]
    linhas.append(("Total", _reais(vm.total) if valor else vm.total, None))
    return Tabela(
        titulo=f"Movimentação {vm.eixo}",
        colunas=(
            Coluna(vm.eixo.removeprefix("por ").capitalize()),
            medida,
            Coluna("Movimentos", "inteiro"),
        ),
        linhas=linhas,
        contexto=[vm.escopo, vm.recorte],
        nome_base=f"movimentacao-{vm.eixo.replace(' ', '-')}",
    )


def _temperatura(vm: temperatura_historico.VM) -> Tabela:
    contexto = [
        vm.unidade,
        f"{vm.de:%d/%m/%Y} a {vm.ate:%d/%m/%Y}",
        f"faixa {vm.faixa_min_c:g} a {vm.faixa_max_c:g} °C",
        f"{vm.total_leituras} leituras, {vm.leituras_fora_da_faixa} fora da faixa",
    ]
    # O periodo fica no conteudo; a rota acrescenta a data de geracao ao nome,
    # e duas datas no nome ja' confundiram quem abriu a pasta de downloads.
    base = f"temperatura-{vm.unidade}"
    if vm.agregado:
        return Tabela(
            titulo="Histórico de temperatura (agregado)",
            colunas=(
                Coluna("Início", "datahora"),
                Coluna("Fim", "datahora"),
                Coluna("Mínima (°C)", "decimal"),
                Coluna("Máxima (°C)", "decimal"),
                Coluna("Média (°C)", "decimal"),
                Coluna("Leituras", "inteiro"),
                Coluna("Excursão"),
            ),
            linhas=[
                (
                    b.inicio,
                    b.fim,
                    _c1(b.minimo),
                    _c1(b.maximo),
                    _c1(b.media),
                    b.leituras,
                    "sim" if b.tem_excursao else "não",
                )
                for b in vm.baldes
            ],
            contexto=contexto,
            nome_base=base,
        )
    return Tabela(
        titulo="Histórico de temperatura",
        colunas=(
            Coluna("Instante", "datahora"),
            Coluna("Temperatura (°C)", "decimal"),
            Coluna("Fora da faixa"),
        ),
        linhas=[
            (p.instante, _c1(p.celsius), "sim" if p.fora_da_faixa else "não") for p in vm.pontos
        ],
        contexto=contexto,
        nome_base=base,
    )


def _excursoes(vm: temperatura_excursoes.VM) -> Tabela:
    # Uma linha por lote presente: e' o que o recall precisa cruzar. Excursao
    # sem lote ainda aparece, com as colunas de lote vazias.
    linhas: list[tuple[Celula, ...]] = []
    for e in vm.excursoes:
        base: tuple[Celula, ...] = (
            e.inicio,
            e.fim,
            _c1(e.duracao_horas),
            e.sentido,
            _c1(e.pico_celsius),
            e.leituras,
        )
        if not e.lotes:
            linhas.append((*base, None, None, None))
        linhas.extend((*base, x.numero, x.produto, _rotulo(x.status)) for x in e.lotes)
    return Tabela(
        titulo="Excursões de temperatura",
        colunas=(
            Coluna("Início", "datahora"),
            Coluna("Fim", "datahora"),
            Coluna("Duração (h)", "decimal"),
            Coluna("Sentido"),
            Coluna("Pico (°C)", "decimal"),
            Coluna("Leituras", "inteiro"),
            Coluna("Lote"),
            Coluna("Produto"),
            Coluna("Status do lote"),
        ),
        linhas=linhas,
        contexto=[
            vm.unidade,
            f"{vm.de:%d/%m/%Y} a {vm.ate:%d/%m/%Y}",
            f"{vm.total_excursoes} excursões",
        ],
        nome_base="excursoes-temperatura",
    )


def _vencimento(vm: fila_vencimento.VM) -> Tabela:
    return Tabela(
        titulo="Fila de vencimento",
        colunas=(
            Coluna("Produto"),
            Coluna("Lote"),
            Coluna("Unidade"),
            Coluna("Validade", "data"),
            Coluna("Dias restantes", "inteiro"),
            Coluna("Saldo", "inteiro"),
            Coluna("Situação"),
        ),
        linhas=[
            (
                x.produto,
                x.numero,
                _unidade(x.unidade),
                x.validade,
                x.dias_restantes,
                x.saldo,
                _rotulo(x.situacao),
            )
            for x in vm.linhas
        ],
        contexto=[f"próximos {vm.janela_dias} dias", f"{vm.total} lotes"],
        nome_base=f"vencimento-{vm.janela_dias}d",
    )


def _lotes(vm: lote_lista.VM) -> Tabela:
    return Tabela(
        titulo="Lotes",
        colunas=(
            Coluna("Produto"),
            Coluna("Lote"),
            Coluna("Unidade"),
            Coluna("Fabricação", "data"),
            Coluna("Validade", "data"),
            Coluna("Dias restantes", "inteiro"),
            Coluna("Saldo", "inteiro"),
            Coluna("Status"),
            Coluna("Situação"),
            Coluna("Endereço"),
        ),
        linhas=[
            (
                x.produto,
                x.numero,
                _unidade(x.unidade),
                x.fabricacao,
                x.validade,
                x.dias_restantes,
                x.saldo,
                _rotulo(x.status),
                _rotulo(x.situacao),
                x.endereco,
            )
            for x in vm.linhas
        ],
        contexto=[vm.escopo, *vm.recorte, f"{vm.total} lotes"],
        nome_base="lotes",
    )


def _movimentos(vm: movimento_lista.VM) -> Tabela:
    return Tabela(
        titulo="Movimentos",
        colunas=(
            Coluna("Data", "datahora"),
            Coluna("Tipo"),
            Coluna("Quantidade", "inteiro"),
            Coluna("Motivo"),
            Coluna("Complemento"),
            Coluna("Lote"),
            Coluna("Unidade"),
            Coluna("Autor"),
            Coluna("Autorizador"),
            Coluna("Status"),
            Coluna("Estorna"),
            Coluna("Estornado por"),
        ),
        linhas=[
            (
                x.criado_em,
                _rotulo(x.tipo),
                x.quantidade,
                _rotulo(x.motivo),
                x.complemento,
                x.lote_id,
                _unidade(x.unidade),
                x.autor,
                x.autorizador,
                x.status_rotulo,
                x.estorna,
                x.estornado_por,
            )
            for x in vm.linhas
        ],
        contexto=[vm.escopo, vm.recorte, f"{vm.total} movimentos, {vm.pendentes} pendentes"],
        nome_base="movimentos",
    )


def _trilha(vm: auditoria_trilha.VM) -> Tabela:
    contexto = [vm.recorte, f"{vm.total} registros"]
    if vm.truncada:
        contexto.append("amostra: a trilha foi cortada no teto de leitura")
    return Tabela(
        titulo="Trilha de auditoria",
        colunas=(
            Coluna("Data", "datahora"),
            Coluna("Ator"),
            Coluna("Ação"),
            Coluna("Entidade"),
            Coluna("Registro"),
            Coluna("Origem"),
            Coluna("Antes"),
            Coluna("Depois"),
            Coluna("Filtrada"),
        ),
        linhas=[
            (
                x.criado_em,
                x.ator,
                x.acao,
                x.entidade,
                x.entidade_id,
                x.origem,
                _json(x.valor_anterior),
                _json(x.valor_novo),
                "sim" if x.filtrada else "não",
            )
            for x in vm.linhas
        ],
        contexto=contexto,
        nome_base="auditoria",
    )


def _json(v: object) -> str | None:
    if v is None:
        return None
    return json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)


def _tabulador[V: BaseModel](
    tipo: type[V], f: Callable[[V], Tabela]
) -> Callable[[BaseModel], Tabela]:
    def aplicar(vm: BaseModel) -> Tabela:
        if not isinstance(vm, tipo):
            msg = f"viewmodel inesperado: {type(vm).__name__}"
            raise TypeError(msg)
        return f(vm)

    return aplicar


TABULADORES: dict[str, Callable[[BaseModel], Tabela]] = {
    "relatorio_movimentacao": _tabulador(relatorio_movimentacao.VM, _relatorio),
    "temperatura_historico": _tabulador(temperatura_historico.VM, _temperatura),
    "temperatura_excursoes": _tabulador(temperatura_excursoes.VM, _excursoes),
    "fila_vencimento": _tabulador(fila_vencimento.VM, _vencimento),
    "lote_lista": _tabulador(lote_lista.VM, _lotes),
    "movimento_lista": _tabulador(movimento_lista.VM, _movimentos),
    "auditoria_trilha": _tabulador(auditoria_trilha.VM, _trilha),
}


def exportaveis() -> Sequence[str]:
    return tuple(TABULADORES)
