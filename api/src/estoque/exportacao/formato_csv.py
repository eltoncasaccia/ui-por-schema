"""CSV para o Excel em portugues: `;`, virgula decimal e BOM.

Sem o BOM, o Excel abre UTF-8 como Windows-1252 e "Licitação" vira
"LicitaÃ§Ã£o". Sem o `;`, a virgula decimal parte a coluna em duas.
"""

import csv
import io

from estoque.application.exportacao.porta import Cabecalho
from estoque.application.exportacao.tabelas import Coluna, Tabela
from estoque.exportacao._celula import local, texto

_TEXTO = Coluna("")


class ExportadorCsv:
    extensao = "csv"
    tipo_midia = "text/csv; charset=utf-8"

    def gerar(self, tabela: Tabela, cabecalho: Cabecalho) -> bytes:
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
        # O contexto vai ANTES da tabela, em linhas proprias: CSV nao tem
        # cabecalho de documento, e o numero sem o filtro e' numero errado.
        w.writerow([texto(tabela.titulo, _TEXTO)])
        for ctx in tabela.contexto:
            w.writerow([texto(ctx, _TEXTO)])
        w.writerow(
            [
                f"{cabecalho.emissor} · gerado por {texto(cabecalho.gerado_por, _TEXTO)} "
                f"em {local(cabecalho.gerado_em):%d/%m/%Y %H:%M}"
            ]
        )
        w.writerow([])
        w.writerow([texto(c.titulo, c) for c in tabela.colunas])
        for linha in tabela.linhas:
            w.writerow([texto(v, c) for v, c in zip(linha, tabela.colunas, strict=True)])
        return ("﻿" + buf.getvalue()).encode("utf-8")
