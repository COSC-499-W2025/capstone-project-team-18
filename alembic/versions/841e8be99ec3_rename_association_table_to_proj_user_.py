"""Rename association_table to proj_user_assoc_table

Revision ID: 841e8be99ec3
Revises:
Create Date: 2026-01-21 02:24:55.113124
Related Issue: https://github.com/COSC-499-W2025/capstone-project-team-18/issues/361
"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '841e8be99ec3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table(
        "association_table",
        "proj_user_assoc_table"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table(
        "proj_user_assoc_table",
        "association_table"
    )
