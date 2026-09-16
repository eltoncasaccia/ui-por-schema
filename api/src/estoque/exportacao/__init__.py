"""Adaptadores de formato da exportacao (T-054): CSV, XLSX e PDF.

Adapter secundario, como `data/` e `assistant/`. Quem escolhe o que vai no
arquivo e' `application.exportacao`; aqui so' se decide como os bytes ficam.
"""

from estoque.application.exportacao.porta import Exportador, Formato
from estoque.exportacao.formato_csv import ExportadorCsv
from estoque.exportacao.formato_pdf import ExportadorPdf
from estoque.exportacao.formato_xlsx import ExportadorXlsx

EXPORTADORES: dict[Formato, Exportador] = {
    "csv": ExportadorCsv(),
    "xlsx": ExportadorXlsx(),
    "pdf": ExportadorPdf(),
}
