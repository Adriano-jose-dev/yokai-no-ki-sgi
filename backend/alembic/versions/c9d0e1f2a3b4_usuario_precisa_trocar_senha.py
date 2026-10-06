"""usuario: flag precisa_trocar_senha (hardening S2)

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-04 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default garante valor para as linhas já existentes; novos usuários
    # recebem True (devem trocar a senha no primeiro acesso).
    op.add_column(
        "usuarios",
        sa.Column(
            "precisa_trocar_senha",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "precisa_trocar_senha")
