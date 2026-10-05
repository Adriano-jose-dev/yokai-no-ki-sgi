"""ocorrencias de aula (Fase 1b do roadmap)

Revision ID: e3c4d5f6a7b8
Revises: d2b3c4e5f6a7
Create Date: 2026-10-02 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3c4d5f6a7b8"
down_revision: Union[str, None] = "d2b3c4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ocorrencias_aula",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_turma", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("hora_inicio", sa.String(), nullable=True),
        sa.Column("hora_fim", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("origem", sa.String(), nullable=False),
        sa.Column("observacao", sa.String(), nullable=True),
        sa.Column("duracao_real_min", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["id_turma"], ["turmas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ocorrencias_aula_id"), "ocorrencias_aula", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_ocorrencias_aula_id_turma"),
        "ocorrencias_aula",
        ["id_turma"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ocorrencias_aula_data"), "ocorrencias_aula", ["data"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ocorrencias_aula_data"), table_name="ocorrencias_aula")
    op.drop_index(op.f("ix_ocorrencias_aula_id_turma"), table_name="ocorrencias_aula")
    op.drop_index(op.f("ix_ocorrencias_aula_id"), table_name="ocorrencias_aula")
    op.drop_table("ocorrencias_aula")
