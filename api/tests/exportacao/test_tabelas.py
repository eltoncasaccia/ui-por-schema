"""T-054 — viewmodel -> tabela. AC-1, AC-5 (lado da tabela), AC-12.

A tabela e' construida do viewmodel e de nada mais. Estes testes provam que o
arquivo tem as linhas da tela, uma a uma, e que custo so' existe nele quando
o viewmodel ja' o trazia.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import BaseModel

from estoque.application.exportacao.tabelas import TABULADORES
from estoque.application.registry.componentes import (
    fila_vencimento,
    relatorio_movimentacao,
    temperatura_excursoes,
    temperatura_historico,
)
from estoque.application.registry.registry import buscar

T0 = datetime(2026, 9, 1, 12, tzinfo=UTC)


def _relatorio(metrica: str = "quantidade") -> relatorio_movimentacao.VM:
    return relatorio_movimentacao.VM.model_validate(
        {
            "eixo": "por unidade",
            "metrica": metrica,
            "metrica_rotulo": "Quantidade movimentada",
            "unidade_medida": "centavos" if metrica == "valor" else "unidades",
            "total": 12345,
            "grupos": 2,
            "escopo": "2 unidades",
            "recorte": "últimos 90 dias · todos os tipos · só efetivados",
            "truncado": False,
            "linhas": [
                {"chave": "cd-matriz", "rotulo": "Matriz", "numero": 12000, "movimentos": 7},
                {"chave": "filial", "rotulo": "Uberlândia", "numero": 345, "movimentos": 2},
            ],
        }
    )


def test_ac1_relatorio_tem_uma_linha_por_linha_da_tela_mais_o_total() -> None:
    vm = _relatorio()
    t = TABULADORES["relatorio_movimentacao"](vm)
    assert [x[0] for x in t.linhas] == ["Matriz", "Uberlândia", "Total"]
    assert [x[1] for x in t.linhas] == [12000, 345, 12345]
    assert [c.titulo for c in t.colunas] == ["Unidade", "Quantidade movimentada", "Movimentos"]
    # O recorte vai junto: numero sem filtro e' numero usado errado.
    assert vm.recorte in t.contexto


def test_ac5_sem_metrica_valor_a_tabela_nao_tem_coluna_de_dinheiro() -> None:
    t = TABULADORES["relatorio_movimentacao"](_relatorio("quantidade"))
    assert all(c.tipo != "reais" for c in t.colunas)
    assert not any("R$" in c.titulo for c in t.colunas)


def test_ac5_contraponto_com_metrica_valor_os_centavos_viram_reais() -> None:
    t = TABULADORES["relatorio_movimentacao"](_relatorio("valor"))
    assert t.colunas[1].tipo == "reais"
    assert t.linhas[0][1] == Decimal("120.00")
    assert t.linhas[-1][1] == Decimal("123.45")


def _pontos(n: int) -> list[temperatura_historico.Ponto]:
    return [
        temperatura_historico.Ponto(
            instante=T0 + timedelta(hours=i), celsius=5.0 + i / 10, fora_da_faixa=False
        )
        for i in range(n)
    ]


def test_ac12_temperatura_ponto_a_ponto_sai_com_os_pontos_da_tela() -> None:
    vm = temperatura_historico.VM(
        unidade="Refrigerado",
        de=date(2026, 9, 1),
        ate=date(2026, 9, 2),
        total_leituras=3,
        leituras_fora_da_faixa=0,
        agregado=False,
        pontos=_pontos(3),
    )
    t = TABULADORES["temperatura_historico"](vm)
    assert [x[0] for x in t.linhas] == [p.instante for p in vm.pontos]
    assert [x[1] for x in t.linhas] == [Decimal("5.0"), Decimal("5.1"), Decimal("5.2")]


def test_ac12_temperatura_agregada_sai_com_os_baldes_da_tela() -> None:
    baldes = [
        temperatura_historico.Balde(
            inicio=T0,
            fim=T0 + timedelta(days=1),
            minimo=4.0,
            maximo=9.1,
            media=5.55,
            leituras=4,
            tem_excursao=True,
        )
    ]
    vm = temperatura_historico.VM(
        unidade="Refrigerado",
        de=date(2021, 1, 1),
        ate=date(2026, 1, 1),
        total_leituras=4,
        leituras_fora_da_faixa=1,
        agregado=True,
        baldes=baldes,
    )
    t = TABULADORES["temperatura_historico"](vm)
    assert t.linhas == [
        (T0, T0 + timedelta(days=1), Decimal("4.0"), Decimal("9.1"), Decimal("5.5"), 4, "sim")
    ]
    assert "agregado" in t.titulo


def test_excursao_sem_lote_ainda_aparece_e_com_lotes_vira_uma_linha_por_lote() -> None:
    lote = {
        "lote_id": "l1",
        "numero": "A1",
        "produto": "Insulina",
        "status": "liberado",
        "entrou_em": T0,
    }
    exc = {
        "inicio": T0,
        "fim": T0,
        "duracao_horas": 1.0,
        "sentido": "calor",
        "pico_celsius": 11.0,
        "leituras": 2,
    }
    vm = temperatura_excursoes.VM.model_validate(
        {
            "unidade": "Refrigerado",
            "de": date(2026, 9, 1),
            "ate": date(2026, 9, 2),
            "total_excursoes": 2,
            "excursoes": [
                {**exc, "lotes": []},
                {**exc, "lotes": [lote, {**lote, "numero": "A2"}]},
            ],
        }
    )
    t = TABULADORES["temperatura_excursoes"](vm)
    assert [x[6] for x in t.linhas] == [None, "A1", "A2"]


def test_fila_de_vencimento_leva_a_validade_como_data() -> None:
    vm = fila_vencimento.VM.model_validate(
        {
            "janela_dias": 90,
            "total": 1,
            "linhas": [
                {
                    "lote_id": "l1",
                    "produto": "Dipirona",
                    "numero": "D1",
                    "unidade": "cd-matriz",
                    "validade": date(2026, 10, 1),
                    "dias_restantes": 15,
                    "saldo": 40,
                    "situacao": "bloqueio_30",
                }
            ],
        }
    )
    t = TABULADORES["fila_vencimento"](vm)
    assert t.linhas[0][3] == date(2026, 10, 1)
    # O que a tela mostra, e nao o codigo: "Bloqueio 30", "CD Matriz".
    assert t.linhas[0][6] == "Bloqueio 30"
    assert t.linhas[0][2] == "CD Matriz"
    assert next(c for c in t.colunas if c.titulo == "Validade").tipo == "data"


@pytest.mark.parametrize("componente", sorted(TABULADORES))
def test_todo_exportavel_existe_no_registry(componente: str) -> None:
    assert buscar(componente) is not None


def test_viewmodel_de_outro_componente_e_recusado() -> None:
    """Um tabulador aplicado ao viewmodel errado nao inventa colunas."""

    class Outro(BaseModel):
        x: int = 1

    with pytest.raises(TypeError):
        TABULADORES["lote_lista"](Outro())


def test_temperatura_nao_carrega_mais_o_csv_no_viewmodel() -> None:
    """AC-12: o CSV da T-023 atravessava a rede em toda leitura, usado ou nao."""
    assert "csv" not in temperatura_historico.VM.model_fields
