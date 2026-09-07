"""Compartilhamento de view.

A regra que nao pode quebrar (documento 03 secao 8):

    Compartilhar aponta para uma view. NAO concede acesso.

Guardamos o SCHEMA, nunca os dados. O destinatario abre sob a permissao DELE,
com o schema revalidado contra o catalogo DELE. Se ele nao pode ver o lote, ele
ve "sem acesso" — nao os dados de quem compartilhou. Sem isso, compartilhamento
vira canal de escalacao de privilegio.

Guardar o schema em vez do resultado tambem faz o item continuar correto meses
depois: ele re-executa, nao mostra uma foto velha.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

APP = "estoque_app"


def upgrade() -> None:
    op.execute(f"""
    CREATE TABLE view_compartilhamento (
        id            bigserial PRIMARY KEY,
        view_id       text NOT NULL REFERENCES view_registro(view_id),
        de_usuario_id text NOT NULL REFERENCES usuario(id),
        para_usuario_id text NOT NULL REFERENCES usuario(id),
        mensagem      text,
        criado_em     timestamptz NOT NULL DEFAULT now(),
        lido_em       timestamptz,
        -- Ninguem compartilha consigo mesmo; e' ruido na caixa.
        CHECK (de_usuario_id <> para_usuario_id)
    );
    CREATE INDEX ix_compart_para ON view_compartilhamento (para_usuario_id, criado_em DESC);

    GRANT SELECT, INSERT, UPDATE ON view_compartilhamento TO {APP};
    GRANT USAGE, SELECT ON SEQUENCE view_compartilhamento_id_seq TO {APP};
    -- Sem DELETE: quem compartilhou nao apaga o registro de ter compartilhado.
    -- E' evidencia de auditoria (RN-D01), nao mensagem de chat.
    REVOKE DELETE ON view_compartilhamento FROM {APP};
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS view_compartilhamento;")
