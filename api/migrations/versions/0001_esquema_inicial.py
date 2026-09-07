"""Esquema inicial: entidades, restricoes de dominio e imutabilidade no banco.

A parte que importa desta migracao nao sao as tabelas — sao os REVOKE.

RN-M02 (movimento e' imutavel) e RN-D02 (auditoria nunca e' alterada) sao regras
de negocio com peso regulatorio. Deixa-las apenas no codigo significa que um
`UPDATE` no psql, um script de correcao ou um bug de ORM as violam em silencio.
Aqui elas sao privilegio negado ao papel da aplicacao.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

APP = "estoque_app"


def upgrade() -> None:
    op.execute(f"""
    -- Papel da aplicacao, separado do dono. Sem esta separacao o REVOKE abaixo
    -- nao teria efeito: o dono de uma tabela ignora privilegios negados.
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP}') THEN
            CREATE ROLE {APP} LOGIN PASSWORD 'app';
        END IF;
    END $$;
    GRANT USAGE ON SCHEMA public TO {APP};
    """)

    op.execute("""
    CREATE TABLE unidade (
        id            text PRIMARY KEY,
        nome          text NOT NULL,
        tipo          text NOT NULL CHECK (tipo IN ('seco','refrigerado')),
        sala_cofre    boolean NOT NULL DEFAULT false
    );

    CREATE TABLE produto (
        id                       text PRIMARY KEY,
        ean                      text NOT NULL,
        nome                     text NOT NULL,
        fabricante               text NOT NULL,
        principio_ativo          text NOT NULL,
        classe                   text NOT NULL
            CHECK (classe IN ('comum','controlado','termolabil','antimicrobiano')),
        curva_abc                text NOT NULL CHECK (curva_abc IN ('A','B','C')),
        ativo                    boolean NOT NULL DEFAULT true,
        -- RN-A02: campo restrito. Em centavos, nunca float.
        custo_unitario_centavos  integer NOT NULL CHECK (custo_unitario_centavos >= 0)
    );

    CREATE TABLE usuario (
        id          text PRIMARY KEY,
        nome        text NOT NULL,
        email       text NOT NULL UNIQUE,
        senha_hash  text NOT NULL,
        -- ADR-0019: cadastro cria usuario SEM papel. NULL e' o estado inicial
        -- legitimo, nao um dado faltando.
        papel       text CHECK (papel IN
                        ('diretor','rt','gerente','conferente','comprador','auditoria')),
        ativo       boolean NOT NULL DEFAULT true   -- RN-A06: desativa, nunca exclui
    );

    CREATE TABLE usuario_unidade (
        usuario_id  text NOT NULL REFERENCES usuario(id),
        unidade_id  text NOT NULL REFERENCES unidade(id),
        PRIMARY KEY (usuario_id, unidade_id)
    );

    CREATE TABLE lote (
        id           text PRIMARY KEY,
        produto_id   text NOT NULL REFERENCES produto(id),
        numero       text NOT NULL,
        unidade_id   text NOT NULL REFERENCES unidade(id),
        fabricacao   date NOT NULL,
        validade     date NOT NULL,
        -- ADR-0022: SO' os estados que sao decisao humana. `vencido` e
        -- `esgotado` sao derivados e nao existem como coluna, pela mesma razao
        -- que nao existe coluna `saldo`.
        status       text NOT NULL
            CHECK (status IN ('quarentena','liberado','bloqueado','descartado')),
        endereco     text,
        CHECK (validade >= fabricacao),
        -- RN-L08: mesmo numero em unidades diferentes sao registros distintos.
        UNIQUE (produto_id, numero, unidade_id)
    );

    CREATE TABLE movimento (
        id                     text PRIMARY KEY,
        lote_id                text NOT NULL REFERENCES lote(id),
        unidade_id             text NOT NULL REFERENCES unidade(id),
        tipo                   text NOT NULL
            CHECK (tipo IN ('entrada','saida','descarte','estorno')),
        quantidade             integer NOT NULL CHECK (quantidade > 0),
        motivo                 text NOT NULL,
        complemento            text,
        autor_id               text NOT NULL REFERENCES usuario(id),
        autorizador_id         text REFERENCES usuario(id),
        status                 text NOT NULL
            CHECK (status IN ('efetivado','aguardando_autorizacao','recusado')),
        criado_em              timestamptz NOT NULL DEFAULT now(),  -- RN-M04: do servidor
        estorna_movimento_id   text REFERENCES movimento(id),
        cliente_id             text,
        nota_fiscal            text,
        -- RN-A04 / RN-C01: quem submete nao autoriza. Aplicado no banco tambem,
        -- porque separacao de funcoes com peso regulatorio nao pode depender de
        -- um `if` no servidor.
        CHECK (autorizador_id IS NULL OR autorizador_id <> autor_id)
    );

    CREATE TABLE recebimento (
        id                    text PRIMARY KEY,
        unidade_id            text NOT NULL REFERENCES unidade(id),
        nota_fiscal           text NOT NULL,
        fornecedor            text NOT NULL,
        status                text NOT NULL CHECK (status IN ('rascunho','conferido','liberado')),
        conferente_id         text NOT NULL REFERENCES usuario(id),
        rt_id                 text REFERENCES usuario(id),
        temperatura_chegada_c double precision,
        divergencia           boolean NOT NULL DEFAULT false,
        recebido_em           timestamptz NOT NULL DEFAULT now()
    );

    CREATE TABLE registro_temperatura (
        id          text PRIMARY KEY,
        unidade_id  text NOT NULL REFERENCES unidade(id),
        medido_em   timestamptz NOT NULL,
        celsius     double precision NOT NULL
    );

    CREATE TABLE auditoria (
        id             bigserial PRIMARY KEY,
        ator_id        text,
        acao           text NOT NULL,
        entidade       text,
        entidade_id    text,
        valor_anterior jsonb,
        valor_novo     jsonb,
        origem         text NOT NULL CHECK (origem IN ('tela','assistente','sistema')),
        criado_em      timestamptz NOT NULL DEFAULT now()
    );

    CREATE TABLE sessao (
        id          text PRIMARY KEY,
        usuario_id  text NOT NULL REFERENCES usuario(id),
        criada_em   timestamptz NOT NULL DEFAULT now(),
        expira_em   timestamptz NOT NULL
    );

    -- ADR-0021: view_key (hash, interno) e view_id (opaco, publico, revogavel)
    CREATE TABLE view_registro (
        view_id      text PRIMARY KEY,
        view_key     text NOT NULL,
        schema       jsonb NOT NULL,
        criado_por   text NOT NULL REFERENCES usuario(id),
        criado_em    timestamptz NOT NULL DEFAULT now(),
        revogado_em  timestamptz
    );
    CREATE INDEX ix_view_registro_key ON view_registro (view_key);
    """)

    op.execute("""
    -- RNF-01: recall em menos de 60s e' requisito de INDICE antes de ser
    -- requisito de codigo.
    CREATE INDEX ix_movimento_lote      ON movimento (lote_id);
    CREATE INDEX ix_movimento_cliente   ON movimento (cliente_id, criado_em)
        WHERE cliente_id IS NOT NULL;
    CREATE INDEX ix_movimento_unidade   ON movimento (unidade_id, criado_em DESC);
    CREATE INDEX ix_movimento_pendente  ON movimento (status)
        WHERE status = 'aguardando_autorizacao';
    -- fila de vencimento (CA-03)
    CREATE INDEX ix_lote_unidade_val    ON lote (unidade_id, validade);
    -- RNF-06: 5 anos de temperatura, consultavel por periodo
    CREATE INDEX ix_temp_unidade_data   ON registro_temperatura (unidade_id, medido_em);
    CREATE INDEX ix_auditoria_data      ON auditoria (criado_em DESC);
    """)

    op.execute("""
    -- ADR-0022 / RN-M06: saldo DERIVADO. Reconstruivel a partir dos movimentos
    -- a qualquer momento; se divergir, a fonte e' o movimento.
    -- Movimento pendente de autorizacao NAO conta (RN-C01) — se contasse, a
    -- mercadoria sairia do estoque contabil com uma identificacao so'.
    CREATE MATERIALIZED VIEW saldo_lote AS
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
    GROUP BY l.id;
    CREATE UNIQUE INDEX ix_saldo_lote ON saldo_lote (lote_id);
    """)

    op.execute(f"""
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP};

    -- ============================================================
    -- RN-M02 e RN-D02 aplicados pelo BANCO, nao por convencao.
    -- Depois destes REVOKE, nenhum bug de ORM, script de correcao ou UPDATE
    -- manual no psql pela aplicacao consegue reescrever a historia.
    -- Corrigir movimento se faz por ESTORNO (RN-M03), que e' um INSERT.
    -- ============================================================
    REVOKE UPDATE, DELETE ON movimento FROM {APP};
    REVOKE UPDATE, DELETE ON auditoria FROM {APP};
    """)


def downgrade() -> None:
    op.execute("""
    DROP MATERIALIZED VIEW IF EXISTS saldo_lote;
    DROP TABLE IF EXISTS view_registro, sessao, auditoria, registro_temperatura,
        recebimento, movimento, lote, usuario_unidade, usuario, produto, unidade CASCADE;
    """)
