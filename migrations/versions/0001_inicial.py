"""Inicial: usuários, estações, pontos de apoio e leituras.

Revision ID: 0001_inicial
Revises:
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_inicial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("apelido", sa.String(40), nullable=False),
        sa.Column("perfil", sa.String(20), nullable=False),
        sa.Column("bairro", sa.String(60), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuarios")),
        sa.CheckConstraint("perfil IN ('Idoso', 'TrabalhadorDeRua', 'Cuidador', 'Outro')", name=op.f("ck_usuarios_perfil")),
    )

    op.create_table(
        "estacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("ativa", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_estacoes")),
        sa.UniqueConstraint("codigo", name=op.f("uq_estacoes_codigo")),
    )

    op.create_table(
        "pontos_apoio",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("endereco", sa.String(120), nullable=False),
        sa.Column("bairro", sa.String(60), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("horario", sa.String(60), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pontos_apoio")),
        sa.ForeignKeyConstraint(
            ["criado_por_id"], ["usuarios.id"], name=op.f("fk_pontos_apoio_criado_por_id_usuarios"), ondelete="SET NULL"
        ),
        sa.CheckConstraint("tipo IN ('Agua', 'Sombra', 'Climatizado')", name=op.f("ck_pontos_apoio_tipo")),
    )
    op.create_index("ix_pontos_apoio_bairro", "pontos_apoio", ["bairro"])

    op.create_table(
        "leituras",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("estacao_id", sa.Integer(), nullable=False),
        sa.Column("temperatura", sa.Float(), nullable=False),
        sa.Column("umidade", sa.Float(), nullable=False),
        sa.Column("indice_calor", sa.Float(), nullable=False),
        sa.Column("nivel", sa.String(20), nullable=False),
        sa.Column("recebida_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leituras")),
        sa.ForeignKeyConstraint(
            ["estacao_id"], ["estacoes.id"], name=op.f("fk_leituras_estacao_id_estacoes"), ondelete="CASCADE"
        ),
        sa.CheckConstraint("nivel IN ('Normal', 'Atencao', 'Alerta', 'Perigo')", name=op.f("ck_leituras_nivel")),
        sa.CheckConstraint("umidade >= 0 AND umidade <= 100", name=op.f("ck_leituras_umidade_faixa")),
        sa.CheckConstraint("temperatura >= -10 AND temperatura <= 60", name=op.f("ck_leituras_temperatura_faixa")),
    )
    op.create_index("ix_leituras_estacao_recebida", "leituras", ["estacao_id", "recebida_em"])


def downgrade() -> None:
    op.drop_index("ix_leituras_estacao_recebida", table_name="leituras")
    op.drop_table("leituras")
    op.drop_index("ix_pontos_apoio_bairro", table_name="pontos_apoio")
    op.drop_table("pontos_apoio")
    op.drop_table("estacoes")
    op.drop_table("usuarios")
