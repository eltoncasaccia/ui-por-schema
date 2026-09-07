"""Importa todos os componentes, registrando-os. Ponto unico de entrada.

Este modulo e' GERADO por `make gerar-indice` varrendo `componentes/*.py`.
Nao edite a mao: 22 componentes registrados manualmente num arquivo so' seriam
22 conflitos de merge garantidos em trabalho paralelo.
"""

from estoque.registry.componentes import estoque_indicador, fila_vencimento
from estoque.registry.orcamento import verificar_teto

__all__ = ["estoque_indicador", "fila_vencimento"]

verificar_teto()  # RNF-08: falha a inicializacao acima de 25 componentes
