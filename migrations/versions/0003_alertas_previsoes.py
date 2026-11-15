"""Alertas (sensor e previsão) e histórico das previsões do modelo de IA.

Revision ID: 0003_alertas_previsoes
Revises: 0002_status_ponto
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_alertas_previsoes"
down_revision = "0002_status_ponto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alertas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("estacao_id", sa.Integer(), nullable=True),
        sa.Column("nivel", sa.String(20), nullable=False),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("mensagem", sa.String(200), nullable=False),
        sa.Column("data_alvo", sa.Date(), nullable=True),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alertas")),
        sa.ForeignKeyConstraint(
            ["estacao_id"], ["estacoes.id"], name=op.f("fk_alertas_estacao_id_estacoes"), ondelete="SET NULL"
        ),
        sa.CheckConstraint("nivel IN ('Normal', 'Atencao', 'Alerta', 'Perigo')", name=op.f("ck_alertas_nivel")),
        sa.CheckConstraint("origem IN ('Sensor', 'Previsao')", name=op.f("ck_alertas_origem")),
    )
    op.create_index("ix_alertas_fim", "alertas", ["fim"])

    op.create_table(
        "previsoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data_alvo", sa.Date(), nullable=False),
        sa.Column("probabilidade", sa.Float(), nullable=False),
        sa.Column("risco", sa.Boolean(), nullable=False),
        sa.Column("versao_modelo", sa.String(40), nullable=False),
        sa.Column("leituras_usadas", sa.Integer(), nullable=False),
        sa.Column("atributos", sa.JSON(), nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_previsoes")),
        sa.CheckConstraint("probabilidade >= 0 AND probabilidade <= 1", name=op.f("ck_previsoes_probabilidade_faixa")),
    )
    op.create_index("ix_previsoes_data_alvo", "previsoes", ["data_alvo"])


def downgrade() -> None:
    op.drop_index("ix_previsoes_data_alvo", table_name="previsoes")
    op.drop_table("previsoes")
    op.drop_index("ix_alertas_fim", table_name="alertas")
    op.drop_table("alertas")
