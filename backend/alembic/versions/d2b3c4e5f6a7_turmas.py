"""turmas e matriculas de turma (Fase 1a do roadmap)

Revision ID: d2b3c4e5f6a7
Revises: c1a2b3d4e5f6
Create Date: 2026-10-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2b3c4e5f6a7"
down_revision: Union[str, None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "turmas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("tipo_pagamento", sa.String(), nullable=False),
        sa.Column("classe", sa.String(), nullable=False),
        sa.Column("valor_base", sa.Float(), nullable=False),
        sa.Column("recorrencia_rrule", sa.String(), nullable=True),
        sa.Column("recorrencia_descricao", sa.String(), nullable=True),
        sa.Column("hora_inicio", sa.String(), nullable=True),
        sa.Column("hora_fim", sa.String(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_turmas_id"), "turmas", ["id"], unique=False)

    op.create_table(
        "turma_matriculas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_turma", sa.Integer(), nullable=False),
        sa.Column("id_aluno", sa.String(), nullable=False),
        sa.Column("papel", sa.String(), nullable=False),
        sa.Column("gratuito", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["id_turma"], ["turmas.id"]),
        sa.ForeignKeyConstraint(["id_aluno"], ["alunos.id_matricula"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_turma_matriculas_id_turma"),
        "turma_matriculas",
        ["id_turma"],
        unique=False,
    )
    op.create_index(
        op.f("ix_turma_matriculas_id_aluno"),
        "turma_matriculas",
        ["id_aluno"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_turma_matriculas_id_aluno"), table_name="turma_matriculas")
    op.drop_index(op.f("ix_turma_matriculas_id_turma"), table_name="turma_matriculas")
    op.drop_table("turma_matriculas")
    op.drop_index(op.f("ix_turmas_id"), table_name="turmas")
    op.drop_table("turmas")
