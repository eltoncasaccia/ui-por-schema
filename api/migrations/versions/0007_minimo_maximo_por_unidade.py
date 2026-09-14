"""Estoque minimo e maximo por produto E por unidade. T-046, `RN-P06`, achado A-30.

**Por que tabela e nao coluna em `produto`.** `RN-P06` diz que a faixa e' por
produto E por unidade. Uma coluna `minimo` em `produto` obrigaria um valor unico
para a rede inteira — exatamente o que a regra existe para impedir.

**As duas restricoes vivem no banco.** Faixa invertida ou negativa e' erro de
cadastro, e o lugar de recusar erro de cadastro e' aqui.

**So' SELECT para a aplicacao:** nao ha escrita de faixa no ciclo 1.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

APP = "estoque_app"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE produto_unidade (
            produto_id  text NOT NULL REFERENCES produto(id),
            unidade_id  text NOT NULL REFERENCES unidade(id),
            minimo      integer NOT NULL CHECK (minimo >= 0),
            maximo      integer NOT NULL,
            PRIMARY KEY (produto_id, unidade_id),
            CHECK (maximo >= minimo)
        );
        GRANT SELECT ON produto_unidade TO {APP};
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE produto_unidade")
