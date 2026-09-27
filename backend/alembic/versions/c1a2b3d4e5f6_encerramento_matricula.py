"""encerramento de matricula (dossie + expurgo agendado)

Revision ID: c1a2b3d4e5f6
Revises: bdf6715ed4b1
Create Date: 2026-09-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, None] = "bdf6715ed4b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "encerramentos_matricula",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_aluno", sa.String(), nullable=True),
        sa.Column("estado_anterior", sa.String(), nullable=False),
        sa.Column("data_encerramento", sa.DateTime(), nullable=False),
        sa.Column("data_expurgo", sa.Date(), nullable=False),
        sa.Column("dossie_pdf", sa.LargeBinary(), nullable=True),
        sa.Column("dossie_nome", sa.String(), nullable=True),
        sa.Column("encerrado_por", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["id_aluno"], ["alunos.id_matricula"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_encerramentos_matricula_id_aluno"),
        "encerramentos_matricula",
        ["id_aluno"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_encerramentos_matricula_id_aluno"),
        table_name="encerramentos_matricula",
    )
    op.drop_table("encerramentos_matricula")
