"""Importa todos os componentes, registrando-os. Ponto unico de entrada.

Este modulo e' GERADO por `make gerar-indice` varrendo `componentes/*.py`.
Nao edite a mao: 22 componentes registrados manualmente num arquivo so' seriam
22 conflitos de merge garantidos em trabalho paralelo.
"""

from estoque.application.registry.componentes import (
    auditoria_trilha,
    controlado_autorizar,
    estoque_indicador,
    fila_vencimento,
    lote_detalhe,
    lote_lista,
    lote_movimentos,
    lote_status_acao,
    movimento_descarte,
    movimento_estorno,
    movimento_lista,
    movimento_saida,
    produto_ficha,
    produto_saldo_por_unidade,
    quarentena_fila,
    quarentena_liberar,
    rastreabilidade,
    recebimento_detalhe,
    recebimento_lista,
    recebimento_registrar,
    relatorio_movimentacao,
    temperatura_excursoes,
    temperatura_historico,
    vencimento_grafico,
)
from estoque.application.registry.orcamento import verificar_teto

__all__ = [
    "auditoria_trilha",
    "controlado_autorizar",
    "estoque_indicador",
    "fila_vencimento",
    "lote_detalhe",
    "lote_lista",
    "lote_movimentos",
    "lote_status_acao",
    "movimento_descarte",
    "movimento_estorno",
    "movimento_lista",
    "movimento_saida",
    "produto_ficha",
    "produto_saldo_por_unidade",
    "quarentena_fila",
    "quarentena_liberar",
    "rastreabilidade",
    "recebimento_detalhe",
    "recebimento_lista",
    "recebimento_registrar",
    "relatorio_movimentacao",
    "temperatura_excursoes",
    "temperatura_historico",
    "vencimento_grafico",
]

verificar_teto()  # RNF-08: falha a inicializacao acima de 25 componentes
