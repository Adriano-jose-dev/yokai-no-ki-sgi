"""anamnese versionada + card de alerta crítico (Fase 3 do roadmap)

Revision ID: a7b8c9d0e1f2
Revises: f4d5e6a7b8c9
Create Date: 2026-10-03 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f4d5e6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "anamneses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_aluno", sa.String(), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("ativa", sa.Boolean(), nullable=False),
        sa.Column("data_preenchimento", sa.Date(), nullable=False),
        sa.Column("validade_meses", sa.Integer(), nullable=False),
        sa.Column("data_validade", sa.Date(), nullable=True),
        sa.Column("respostas_json", sa.String(), nullable=True),
        sa.Column("condicoes_criticas_json", sa.String(), nullable=True),
        sa.Column("observacao", sa.String(), nullable=True),
        sa.Column("contato_emergencia_nome", sa.String(), nullable=True),
        sa.Column("contato_emergencia_parentesco", sa.String(), nullable=True),
        sa.Column("contato_emergencia_telefone", sa.String(), nullable=True),
        sa.Column("autor", sa.String(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["id_aluno"], ["alunos.id_matricula"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_anamneses_id"), "anamneses", ["id"], unique=False)
    op.create_index(
        op.f("ix_anamneses_id_aluno"), "anamneses", ["id_aluno"], unique=False
    )
    op.create_index(op.f("ix_anamneses_ativa"), "anamneses", ["ativa"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_anamneses_ativa"), table_name="anamneses")
    op.drop_index(op.f("ix_anamneses_id_aluno"), table_name="anamneses")
    op.drop_index(op.f("ix_anamneses_id"), table_name="anamneses")
    op.drop_table("anamneses")
