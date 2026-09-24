"""corrige horas_franquia 4 para 3

Revision ID: bdf6715ed4b1
Revises: 639d4d737621
Create Date: 2026-09-23 22:52:36.891934

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bdf6715ed4b1'
down_revision: Union[str, None] = '639d4d737621'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migration de dados (Requisito 9.3): contratos legados foram criados com
    # horas_franquia = 4, divergindo da regra de negócio (franquia da
    # Mensalidade é de 3 horas). Corrige os registros existentes.
    op.execute("UPDATE contratos SET horas_franquia = 3 WHERE horas_franquia = 4")


def downgrade() -> None:
    # Reverte a correção de dados (best-effort): volta 3 para 4.
    op.execute("UPDATE contratos SET horas_franquia = 4 WHERE horas_franquia = 3")
