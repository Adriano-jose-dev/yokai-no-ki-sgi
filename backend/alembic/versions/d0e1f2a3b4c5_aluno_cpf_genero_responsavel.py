"""aluno: cpf, genero, cpf_responsavel, rg_responsavel (P2/P3/P5)

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-10-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("alunos", sa.Column("cpf", sa.String(), nullable=True))
    op.add_column("alunos", sa.Column("genero", sa.String(), nullable=True))
    op.add_column("alunos", sa.Column("cpf_responsavel", sa.String(), nullable=True))
    op.add_column("alunos", sa.Column("rg_responsavel", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("alunos", "rg_responsavel")
    op.drop_column("alunos", "cpf_responsavel")
    op.drop_column("alunos", "genero")
    op.drop_column("alunos", "cpf")
