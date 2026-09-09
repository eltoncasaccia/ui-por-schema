"""`saldo_lote` deixa de ser materializada. Achado A-20.

**O problema, medido.** A view materializada so' muda com `REFRESH MATERIALIZED
VIEW`, e nenhum caminho da aplicacao executa isso — o unico `REFRESH` do projeto
esta' no seed. Conferido com uma escrita real: depois de um movimento de saida de
7 unidades, a view dizia 762 e a soma dos movimentos dizia 755.

Toda LEITURA de saldo — `lote_lista`, `lote_detalhe`, `quarentena_fila`,
`fila_vencimento` — mostrava o valor de antes da ultima subida do container. Num
sistema cujo criterio de aceite e' "nenhum saldo muda sem movimento com autor e
motivo recuperaveis" (CA-02), o saldo exibido estar velho e' o pior lugar
possivel para uma defasagem.

**E ia piorar.** Com a aplicacao passando a conectar como `estoque_app` (achado
A-27), `REFRESH` deixa de ser sequer possivel: o privilegio e' do dono.

**A decisao.** A T-036 prometia a view "atualizada na mesma transacao do
movimento". Uma view COMUM entrega isso por construcao — ela nao e' atualizada,
ela e' calculada. Materializar era otimizacao para um problema que 191 lotes nao
tem, e que custou correcao.

Se um dia o volume exigir materializacao de volta, o caminho e' gatilho na
insercao do movimento, e nao `REFRESH` manual — porque foi o manual que ninguem
chamou.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

APP = "estoque_app"

# Uma definicao so', usada na ida e na volta.
SELECT_SALDO = """
    SELECT l.id AS lote_id,
           COALESCE(SUM(
               CASE m.tipo
                   WHEN 'entrada'  THEN  m.quantidade
                   WHEN 'estorno'  THEN  m.quantidade
                   WHEN 'saida'    THEN -m.quantidade
                   WHEN 'descarte' THEN -m.quantidade
               END
           ), 0)::integer AS saldo
    FROM lote l
    LEFT JOIN movimento m ON m.lote_id = l.id AND m.status = 'efetivado'
    GROUP BY l.id
"""


def upgrade() -> None:
    op.execute(f"""
    DROP MATERIALIZED VIEW IF EXISTS saldo_lote;

    -- Movimento pendente de autorizacao NAO conta (RN-C01) — se contasse, a
    -- mercadoria sairia do estoque contabil com uma identificacao so'.
    CREATE VIEW saldo_lote AS {SELECT_SALDO};

    GRANT SELECT ON saldo_lote TO {APP};
    """)


def downgrade() -> None:
    op.execute(f"""
    DROP VIEW IF EXISTS saldo_lote;
    CREATE MATERIALIZED VIEW saldo_lote AS {SELECT_SALDO};
    CREATE UNIQUE INDEX ix_saldo_lote ON saldo_lote (lote_id);
    GRANT SELECT ON saldo_lote TO {APP};
    """)
