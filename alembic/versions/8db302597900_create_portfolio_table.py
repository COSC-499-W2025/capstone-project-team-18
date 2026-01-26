"""create portfolio table

Revision ID: 8db302597900
Revises: 0240c84c3158
Create Date: 2026-01-26 20:37:55.830512
Related Issue: https://github.com/COSC-499-W2025/capstone-project-team-18/issues/361
Description: Created a portfolio table for storing text versions of UserReports.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '8db302597900'
down_revision: Union[str, Sequence[str], None] = '0240c84c3158'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('portfolio',
                    sa.Column('id', sa.INTEGER(), nullable=False),
                    sa.Column('user_report_id', sa.INTEGER(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['user_report_id'], ['user_report.id']),
                    sa.PrimaryKeyConstraint('id'),
                    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('portfolio')
