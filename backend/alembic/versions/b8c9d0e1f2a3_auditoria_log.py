"""auditoria: log de segurança (Fase 4 do roadmap)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-03 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "registros_auditoria",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column("acao", sa.String(), nullable=False),
        sa.Column("id_aluno", sa.String(), nullable=True),
        sa.Column("autor", sa.String(), nullable=True),
        sa.Column("descricao", sa.String(), nullable=True),
        sa.Column("detalhes_json", sa.String(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_registros_auditoria_id"), "registros_auditoria", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_registros_auditoria_categoria"),
        "registros_auditoria",
        ["categoria"],
        unique=False,
    )
    op.create_index(
        op.f("ix_registros_auditoria_id_aluno"),
        "registros_auditoria",
        ["id_aluno"],
        unique=False,
    )
    op.create_index(
        op.f("ix_registros_auditoria_criado_em"),
        "registros_auditoria",
        ["criado_em"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_registros_auditoria_criado_em"), table_name="registros_auditoria"
    )
    op.drop_index(
        op.f("ix_registros_auditoria_id_aluno"), table_name="registros_auditoria"
    )
    op.drop_index(
        op.f("ix_registros_auditoria_categoria"), table_name="registros_auditoria"
    )
    op.drop_index(
        op.f("ix_registros_auditoria_id"), table_name="registros_auditoria"
    )
    op.drop_table("registros_auditoria")
