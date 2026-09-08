"""Registro de idempotencia do plano de escrita. T-025 AC-3.

Por que uma tabela, e nao um cache em memoria: a promessa do `Idempotency-Key`
e' que a rede pode repetir a requisicao e o efeito acontece UMA vez. Um cache de
processo quebra essa promessa exatamente no caso que ela existe para cobrir —
o cliente que repete porque o servidor caiu antes de responder, e o processo que
subiu no lugar nao lembra de nada.

A chave e' `(chave, ator_id)`, nao `chave` sozinha. Um `Idempotency-Key` gerado
por um cliente nao pode colidir com o de outro ator, e — o que importa mais —
nao pode REPRODUZIR a resposta de outro ator. Chave global seria um canal de
leitura de resposta alheia com autenticacao propria.

`impressao` guarda o hash do corpo: mesma chave com corpo diferente e' erro do
cliente, e devolve `conflito` em vez de repetir a resposta antiga em silencio.

Sem UPDATE nem DELETE: o registro nasce junto com o efeito, na mesma transacao,
e nao se corrige depois. Se pudesse ser apagado, apagar seria o caminho para
executar duas vezes.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

APP = "estoque_app"


def upgrade() -> None:
    op.execute(f"""
    CREATE TABLE idempotencia (
        chave      text NOT NULL,
        ator_id    text NOT NULL REFERENCES usuario(id),
        comando    text NOT NULL,
        impressao  text NOT NULL,
        resposta   jsonb NOT NULL,
        etag       text,
        criado_em  timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (chave, ator_id)
    );

    GRANT SELECT, INSERT ON idempotencia TO {APP};
    -- O registro e' escrito uma vez, na transacao do efeito. Poder alteralo ou
    -- apaga-lo seria poder executar o comando duas vezes.
    REVOKE UPDATE, DELETE ON idempotencia FROM {APP};
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS idempotencia;")
