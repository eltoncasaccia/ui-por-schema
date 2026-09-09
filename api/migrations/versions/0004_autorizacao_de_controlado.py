"""A transicao de autorizacao do movimento controlado. T-030 — RN-C01, RN-M02.

**Duas regras deste projeto estavam em tensao, e esta migracao e' a resolucao.**

`RN-M02` diz que movimento e' imutavel, e a migracao 0001 aplicou isso do jeito
mais forte que existe: `REVOKE UPDATE, DELETE ON movimento`. Nenhum bug de ORM,
script de correcao ou UPDATE manual reescreve a historia.

`RN-C01` exige que a saida de controlado nasca `aguardando_autorizacao` e passe a
`efetivado` quando o RT autorizar, gravando a segunda identidade. `StatusMovimento`,
em CONTRATOS §3, ja' descreve os tres estados — a transicao e' parte do contrato.

Com o REVOKE de tabela inteira, a segunda regra e' impossivel: conferido no banco,
a aplicacao recebe `permission denied for table movimento`.

**A resolucao nao e' devolver o UPDATE.** E':

  1. GRANT por COLUNA — so' `status` e `autorizador_id`. Um UPDATE em
     `quantidade`, `lote_id`, `autor_id` ou `criado_em` continua sendo recusado
     pelo mesmo `permission denied` de antes.
  2. Um GATILHO que so' deixa passar a transicao documentada:
     `aguardando_autorizacao` -> `efetivado` ou `recusado`, e nada mais. Sem ele,
     o GRANT por coluna permitiria virar um `efetivado` em `recusado` — o que
     apaga o efeito de um movimento, e apagar efeito e' reescrever historia com
     outro nome.

O que `RN-M02` protege continua protegido: **ninguem muda o que aconteceu.** O que
passa a ser possivel e' registrar a decisao que faltava.

`RN-A04` (quem submete nao autoriza) ja' era aplicado pelo CHECK da 0001, e
continua: `autorizador_id <> autor_id`.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

APP = "estoque_app"


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION movimento_so_transicao_de_autorizacao()
    RETURNS trigger AS $$
    BEGIN
        -- So' um movimento PENDENTE se resolve. Um `efetivado` e' definitivo:
        -- corrigir se faz por estorno (RN-M03), que e' INSERT.
        IF OLD.status <> 'aguardando_autorizacao' THEN
            RAISE EXCEPTION
                'movimento % nao esta pendente: status % e definitivo (RN-M02)',
                OLD.id, OLD.status;
        END IF;

        IF NEW.status NOT IN ('efetivado', 'recusado') THEN
            RAISE EXCEPTION
                'transicao invalida: aguardando_autorizacao -> % (RN-C01)', NEW.status;
        END IF;

        -- Toda coluna que descreve O QUE ACONTECEU fica igual. O GRANT por
        -- coluna ja' impede a maioria; esta checagem existe porque o dono da
        -- tabela ignora GRANT, e migracao ou script de manutencao rodam como
        -- dono. Duas camadas, nenhuma confiando na outra.
        IF ROW(NEW.id, NEW.lote_id, NEW.unidade_id, NEW.tipo, NEW.quantidade,
               NEW.motivo, NEW.complemento, NEW.autor_id, NEW.criado_em,
               NEW.estorna_movimento_id, NEW.cliente_id, NEW.nota_fiscal)
           IS DISTINCT FROM
           ROW(OLD.id, OLD.lote_id, OLD.unidade_id, OLD.tipo, OLD.quantidade,
               OLD.motivo, OLD.complemento, OLD.autor_id, OLD.criado_em,
               OLD.estorna_movimento_id, OLD.cliente_id, OLD.nota_fiscal)
        THEN
            RAISE EXCEPTION
                'so status e autorizador_id mudam na autorizacao (RN-M02)';
        END IF;

        -- RN-C01: quem resolve assina. Sem isto, `status` mudaria sozinho e a
        -- dupla identificacao ficaria com uma identidade so'.
        IF NEW.autorizador_id IS NULL THEN
            RAISE EXCEPTION 'autorizacao exige a segunda identidade (RN-C01)';
        END IF;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER movimento_autorizacao
        BEFORE UPDATE ON movimento
        FOR EACH ROW EXECUTE FUNCTION movimento_so_transicao_de_autorizacao();
    """)

    op.execute(f"""
    -- Por COLUNA. `GRANT UPDATE ON movimento` devolveria a tabela inteira.
    GRANT UPDATE (status, autorizador_id) ON movimento TO {APP};
    """)


def downgrade() -> None:
    op.execute(f"""
    REVOKE UPDATE (status, autorizador_id) ON movimento FROM {APP};
    DROP TRIGGER IF EXISTS movimento_autorizacao ON movimento;
    DROP FUNCTION IF EXISTS movimento_so_transicao_de_autorizacao();
    """)
