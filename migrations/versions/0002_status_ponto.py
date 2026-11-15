"""Moderação de pontos: status (Pendente, Aprovado, Rejeitado) e data da avaliação.

Pontos que já existiam antes desta migração entram como Aprovado.
Daqui em diante, todo ponto novo começa como Pendente até o posto avaliar.

Revision ID: 0002_status_ponto
Revises: 0001_inicial
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_status_ponto"
down_revision = "0001_inicial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) As linhas existentes recebem 'Aprovado' (eram pontos já conferidos).
    op.add_column("pontos_apoio", sa.Column("status", sa.String(20), server_default="Aprovado", nullable=False))
    # 2) O padrão para linhas novas passa a ser 'Pendente'.
    op.alter_column("pontos_apoio", "status", server_default="Pendente")
    op.create_check_constraint(
        op.f("ck_pontos_apoio_status"), "pontos_apoio", "status IN ('Pendente', 'Aprovado', 'Rejeitado')"
    )
    op.create_index("ix_pontos_apoio_status", "pontos_apoio", ["status"])
    op.add_column("pontos_apoio", sa.Column("avaliado_em", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("pontos_apoio", "avaliado_em")
    op.drop_index("ix_pontos_apoio_status", table_name="pontos_apoio")
    op.drop_constraint(op.f("ck_pontos_apoio_status"), "pontos_apoio", type_="check")
    op.drop_column("pontos_apoio", "status")
