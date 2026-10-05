"""financeiro: conta corrente (lancamentos) e abonos de falta (Fase 2 do roadmap)

Revision ID: f4d5e6a7b8c9
Revises: e3c4d5f6a7b8
Create Date: 2026-10-03 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4d5e6a7b8c9"
down_revision: Union[str, None] = "e3c4d5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lancamentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_aluno", sa.String(), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column("valor", sa.Float(), nullable=False),
        sa.Column("valor_aberto", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("descricao", sa.String(), nullable=True),
        sa.Column("data_competencia", sa.Date(), nullable=False),
        sa.Column("data_vencimento", sa.Date(), nullable=True),
        sa.Column("mes_referencia", sa.String(), nullable=True),
        sa.Column("id_ocorrencia", sa.Integer(), nullable=True),
        sa.Column("metodo", sa.String(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["id_aluno"], ["alunos.id_matricula"]),
        sa.ForeignKeyConstraint(["id_ocorrencia"], ["ocorrencias_aula.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lancamentos_id"), "lancamentos", ["id"], unique=False)
    op.create_index(
        op.f("ix_lancamentos_id_aluno"), "lancamentos", ["id_aluno"], unique=False
    )
    op.create_index(
        op.f("ix_lancamentos_mes_referencia"),
        "lancamentos",
        ["mes_referencia"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lancamentos_id_ocorrencia"),
        "lancamentos",
        ["id_ocorrencia"],
        unique=False,
    )

    op.create_table(
        "abonos_falta",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_aluno", sa.String(), nullable=False),
        sa.Column("id_ocorrencia", sa.Integer(), nullable=True),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("justificativa", sa.String(), nullable=True),
        sa.Column("autor", sa.String(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["id_aluno"], ["alunos.id_matricula"]),
        sa.ForeignKeyConstraint(["id_ocorrencia"], ["ocorrencias_aula.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_abonos_falta_id_aluno"), "abonos_falta", ["id_aluno"], unique=False
    )
    op.create_index(
        op.f("ix_abonos_falta_id_ocorrencia"),
        "abonos_falta",
        ["id_ocorrencia"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_abonos_falta_id_ocorrencia"), table_name="abonos_falta")
    op.drop_index(op.f("ix_abonos_falta_id_aluno"), table_name="abonos_falta")
    op.drop_table("abonos_falta")
    op.drop_index(op.f("ix_lancamentos_id_ocorrencia"), table_name="lancamentos")
    op.drop_index(op.f("ix_lancamentos_mes_referencia"), table_name="lancamentos")
    op.drop_index(op.f("ix_lancamentos_id_aluno"), table_name="lancamentos")
    op.drop_index(op.f("ix_lancamentos_id"), table_name="lancamentos")
    op.drop_table("lancamentos")
