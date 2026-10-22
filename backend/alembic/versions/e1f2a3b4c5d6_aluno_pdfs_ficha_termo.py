"""aluno: ficha_inscricao_pdf e termo_risco_pdf (P4 — armazenamento de documentos assinados)

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-10-21 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("alunos", sa.Column("ficha_inscricao_pdf", sa.LargeBinary(), nullable=True))
    op.add_column("alunos", sa.Column("ficha_inscricao_nome", sa.String(), nullable=True))
    op.add_column("alunos", sa.Column("termo_risco_pdf", sa.LargeBinary(), nullable=True))
    op.add_column("alunos", sa.Column("termo_risco_nome", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("alunos", "termo_risco_nome")
    op.drop_column("alunos", "termo_risco_pdf")
    op.drop_column("alunos", "ficha_inscricao_nome")
    op.drop_column("alunos", "ficha_inscricao_pdf")
