"""Tabelas SQLAlchemy Core. Espelham a migracao 0001.

Core em vez de ORM de proposito: os tipos de dominio ja' existem em
`domain/tipos.py` como dataclasses frozen. Um ORM criaria uma SEGUNDA
representacao das mesmas entidades, e as duas divergiriam — o mesmo modo de
apodrecimento que o ADR-0017 combate no registry.

Aqui as tabelas descrevem o BANCO; o dominio descreve as REGRAS. O repositorio
traduz entre os dois, num lugar so'.
"""

import sqlalchemy as sa

metadata = sa.MetaData()

unidade = sa.Table(
    "unidade",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("nome", sa.Text, nullable=False),
    sa.Column("tipo", sa.Text, nullable=False),
    sa.Column("sala_cofre", sa.Boolean, nullable=False),
)

produto = sa.Table(
    "produto",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("ean", sa.Text, nullable=False),
    sa.Column("nome", sa.Text, nullable=False),
    sa.Column("fabricante", sa.Text, nullable=False),
    sa.Column("principio_ativo", sa.Text, nullable=False),
    sa.Column("classe", sa.Text, nullable=False),
    sa.Column("curva_abc", sa.Text, nullable=False),
    sa.Column("ativo", sa.Boolean, nullable=False),
    sa.Column("custo_unitario_centavos", sa.Integer, nullable=False),
)

usuario = sa.Table(
    "usuario",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("nome", sa.Text, nullable=False),
    sa.Column("email", sa.Text, nullable=False, unique=True),
    sa.Column("senha_hash", sa.Text, nullable=False),
    sa.Column("papel", sa.Text),  # NULL = cadastrado sem papel (ADR-0019)
    sa.Column("ativo", sa.Boolean, nullable=False),
)

usuario_unidade = sa.Table(
    "usuario_unidade",
    metadata,
    sa.Column("usuario_id", sa.Text, primary_key=True),
    sa.Column("unidade_id", sa.Text, primary_key=True),
)

lote = sa.Table(
    "lote",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("produto_id", sa.Text, nullable=False),
    sa.Column("numero", sa.Text, nullable=False),
    sa.Column("unidade_id", sa.Text, nullable=False),
    sa.Column("fabricacao", sa.Date, nullable=False),
    sa.Column("validade", sa.Date, nullable=False),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("endereco", sa.Text),
)

movimento = sa.Table(
    "movimento",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("lote_id", sa.Text, nullable=False),
    sa.Column("unidade_id", sa.Text, nullable=False),
    sa.Column("tipo", sa.Text, nullable=False),
    sa.Column("quantidade", sa.Integer, nullable=False),
    sa.Column("motivo", sa.Text, nullable=False),
    sa.Column("complemento", sa.Text),
    sa.Column("autor_id", sa.Text, nullable=False),
    sa.Column("autorizador_id", sa.Text),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    sa.Column("estorna_movimento_id", sa.Text),
    sa.Column("cliente_id", sa.Text),
    sa.Column("nota_fiscal", sa.Text),
)

recebimento = sa.Table(
    "recebimento",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("unidade_id", sa.Text, nullable=False),
    sa.Column("nota_fiscal", sa.Text, nullable=False),
    sa.Column("fornecedor", sa.Text, nullable=False),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("conferente_id", sa.Text, nullable=False),
    sa.Column("rt_id", sa.Text),
    sa.Column("temperatura_chegada_c", sa.Float),
    sa.Column("divergencia", sa.Boolean, nullable=False),
    sa.Column("recebido_em", sa.DateTime(timezone=True), nullable=False),
)

registro_temperatura = sa.Table(
    "registro_temperatura",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("unidade_id", sa.Text, nullable=False),
    sa.Column("medido_em", sa.DateTime(timezone=True), nullable=False),
    sa.Column("celsius", sa.Float, nullable=False),
)

auditoria = sa.Table(
    "auditoria",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("ator_id", sa.Text),
    sa.Column("acao", sa.Text, nullable=False),
    sa.Column("entidade", sa.Text),
    sa.Column("entidade_id", sa.Text),
    sa.Column("valor_anterior", sa.JSON),
    sa.Column("valor_novo", sa.JSON),
    sa.Column("origem", sa.Text, nullable=False),
    sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
)

sessao = sa.Table(
    "sessao",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("usuario_id", sa.Text, nullable=False),
    sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False),
    sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
)

view_registro = sa.Table(
    "view_registro",
    metadata,
    sa.Column("view_id", sa.Text, primary_key=True),
    sa.Column("view_key", sa.Text, nullable=False),
    sa.Column("schema", sa.JSON, nullable=False),
    sa.Column("criado_por", sa.Text, nullable=False),
    sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    sa.Column("revogado_em", sa.DateTime(timezone=True)),
)

# View materializada — derivada, nunca escrita pela aplicacao (ADR-0022)
saldo_lote = sa.Table(
    "saldo_lote",
    metadata,
    sa.Column("lote_id", sa.Text, primary_key=True),
    sa.Column("saldo", sa.Integer, nullable=False),
)

view_compartilhamento = sa.Table(
    "view_compartilhamento",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("view_id", sa.Text, nullable=False),
    sa.Column("de_usuario_id", sa.Text, nullable=False),
    sa.Column("para_usuario_id", sa.Text, nullable=False),
    sa.Column("mensagem", sa.Text),
    sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    sa.Column("lido_em", sa.DateTime(timezone=True)),
)

# Registro de idempotencia do plano de escrita (T-025). Chave composta com o
# ator: `Idempotency-Key` de um cliente nao reproduz a resposta de outro.
idempotencia = sa.Table(
    "idempotencia",
    metadata,
    sa.Column("chave", sa.Text, primary_key=True),
    sa.Column("ator_id", sa.Text, primary_key=True),
    sa.Column("comando", sa.Text, nullable=False),
    sa.Column("impressao", sa.Text, nullable=False),
    sa.Column("resposta", sa.JSON, nullable=False),
    sa.Column("etag", sa.Text),
    sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
)
