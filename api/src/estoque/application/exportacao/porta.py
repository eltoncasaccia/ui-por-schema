"""A porta do gerador de arquivo, e a unica regra que todo formato cumpre.

`application` nao importa `openpyxl` nem `fpdf` (contrato do import-linter):
o formato e' detalhe de adaptador, e trocar de biblioteca nao pode mexer em
quem decide o que vai no arquivo.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from estoque.application.exportacao.tabelas import Tabela

Formato = Literal["csv", "xlsx", "pdf"]

# Planilha interpreta como formula a celula que comeca com estes caracteres.
# Um lote, um complemento ou um nome cadastrado com `=HYPERLINK(...)` viraria
# codigo na maquina de quem abriu o arquivo (injecao de CSV, OWASP).
INICIO_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def neutralizar(texto: str) -> str:
    """Prefixa `'` no texto que a planilha leria como formula.

    So' texto: numero negativo e' numero, e vai para a celula como numero.
    """
    return "'" + texto if texto.startswith(INICIO_DE_FORMULA) else texto


@dataclass(frozen=True, slots=True)
class Cabecalho:
    """Quem gerou, quando, e de onde — o que faz o arquivo valer fora da tela."""

    emissor: str
    gerado_por: str
    gerado_em: datetime


class Exportador(Protocol):
    extensao: str
    tipo_midia: str

    def gerar(self, tabela: Tabela, cabecalho: Cabecalho) -> bytes: ...
