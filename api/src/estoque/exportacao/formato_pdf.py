"""PDF para imprimir e arquivar: cabecalho, contexto, tabela e paginacao (AC-3).

As fontes embutidas do fpdf2 so' cobrem latin-1. Portugues cabe inteiro nele;
o que nao cabe (travessao, reticencias) e' trocado antes, para o PDF nao
falhar por causa de um nome cadastrado com um caractere exotico.
"""

from fpdf import FPDF
from fpdf.fonts import FontFace

from estoque.application.exportacao.porta import Cabecalho
from estoque.application.exportacao.tabelas import Celula, Coluna, Tabela
from estoque.exportacao._celula import local, texto

TROCAS = str.maketrans({"—": "-", "–": "-", "…": "...", "“": '"', "”": '"', "‘": "'", "’": "'"})
DIREITA = frozenset({"inteiro", "decimal", "reais"})
# Largura aproximada de um caractere de Helvetica 8 pt, com respiro, em mm.
MM_POR_CARACTERE = 1.9


def _celula(v: Celula, c: Coluna) -> str:
    # No PDF o inteiro e' para ler, nao para recalcular: leva separador de
    # milhar. No CSV ele sai cru, para o Excel reconhecer como numero.
    if isinstance(v, int) and c.tipo == "inteiro":
        return f"{v:,}".replace(",", ".")
    return texto(v, c)


def _latin1(s: str) -> str:
    return s.translate(TROCAS).encode("latin-1", "replace").decode("latin-1")


class _Documento(FPDF):
    def __init__(self, rodape: str) -> None:
        # Paisagem: as tabelas de lote e de movimento tem de 9 a 12 colunas.
        super().__init__(orientation="landscape", unit="mm", format="A4")
        self._rodape = rodape

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", size=8)
        self.set_text_color(110)
        self.cell(0, 6, _latin1(self._rodape), align="L")
        self.cell(0, 6, f"página {self.page_no()} de {{nb}}", align="R")


class ExportadorPdf:
    extensao = "pdf"
    tipo_midia = "application/pdf"

    def gerar(self, tabela: Tabela, cabecalho: Cabecalho) -> bytes:
        quando = f"{local(cabecalho.gerado_em):%d/%m/%Y %H:%M}"
        rodape = f"{cabecalho.emissor} · gerado por {cabecalho.gerado_por} em {quando}"
        pdf = _Documento(rodape)
        pdf.set_title(_latin1(tabela.titulo))
        pdf.set_author(_latin1(cabecalho.emissor))
        pdf.set_auto_page_break(auto=True, margin=16)
        pdf.add_page()

        pdf.set_font("Helvetica", style="B", size=9)
        pdf.set_text_color(15, 107, 98)
        pdf.cell(0, 5, _latin1(cabecalho.emissor.upper()), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0)
        pdf.set_font("Helvetica", style="B", size=15)
        pdf.cell(0, 9, _latin1(tabela.titulo), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(80)
        for ctx in [*tabela.contexto, f"Gerado por {cabecalho.gerado_por} em {quando}"]:
            pdf.multi_cell(0, 4.5, _latin1(ctx), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0)
        pdf.ln(3)

        if not tabela.linhas:
            pdf.set_font("Helvetica", style="I", size=10)
            pdf.cell(0, 8, "Nenhum registro no recorte pedido.")
            return bytes(pdf.output())

        # Largura proporcional ao conteudo, com piso: coluna de "Sim" nao
        # precisa do espaco de uma coluna de produto.
        pesos = [
            max(
                6,
                min(
                    40,
                    max([len(c.titulo)] + [len(_celula(x[i], c)) for x in tabela.linhas[:200]]),
                ),
            )
            for i, c in enumerate(tabela.colunas)
        ]
        # Tabela estreita nao estica ate' a margem: tres colunas espalhadas na
        # pagina deitada deixam o olho sem saber qual numero e' de qual linha.
        largura = min(pdf.epw, sum(pesos) * MM_POR_CARACTERE + 4 * len(pesos))
        pdf.set_font("Helvetica", size=8)
        pdf.set_draw_color(215, 219, 223)
        pdf.set_line_width(0.2)
        cinza = FontFace(emphasis="BOLD", fill_color=(236, 238, 240))
        with pdf.table(
            width=largura,
            align="LEFT",
            col_widths=tuple(pesos),
            headings_style=cinza,
            line_height=4.8,
            text_align=tuple("RIGHT" if c.tipo in DIREITA else "LEFT" for c in tabela.colunas),
            borders_layout="HORIZONTAL_LINES",
        ) as t:
            cab = t.row()
            for c in tabela.colunas:
                cab.cell(_latin1(c.titulo))
            for linha in tabela.linhas:
                r = t.row()
                for v, c in zip(linha, tabela.colunas, strict=True):
                    # PDF nao executa formula, mas o texto sai igual ao da
                    # planilha: um so' formatador, uma so' leitura.
                    r.cell(_latin1(_celula(v, c)))
        return bytes(pdf.output())
