"""`produto.ean` passa a ser UNIQUE. T-048, achado A-37.

**Por que agora.** A `US-02` e o `RNF-02` pedem o recebimento pelo leitor de
codigo de barras, e um leitor devolve um EAN. Ate' a T-048 nao havia caminho de
EAN -> produto em lugar nenhum do sistema: `ean` existia na coluna, no tipo e no
viewmodel de `produto_ficha`, nunca como criterio de busca.

**Por que UNIQUE e nao so' um indice.** `por_ean` devolve `Produto | None`. Com
EAN repetido a assinatura seria mentira — a busca devolveria "algum" dos
produtos, e qual deles dependeria do plano de execucao. EAN e' identificador
global de produto comercial; dois produtos com o mesmo EAN e' erro de cadastro,
e o lugar de recusar erro de cadastro e' o banco.

O indice unico serve as duas coisas: torna a busca bem definida E a torna rapida,
que e' o que um leitor de codigo de barras exige do fluxo.

**Conferido antes de escrever:** 18 produtos no seed, zero EAN duplicado. A
restricao entra sem limpeza previa.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("produto_ean_key", "produto", ["ean"])


def downgrade() -> None:
    op.drop_constraint("produto_ean_key", "produto", type_="unique")
