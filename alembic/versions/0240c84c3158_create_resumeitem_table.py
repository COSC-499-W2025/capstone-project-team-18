"""create ResumeItem table

Revision ID: 0240c84c3158
Revises: a5249b44f9dd
Create Date: 2026-01-26 19:12:57.189332
Related Issue: https://github.com/COSC-499-W2025/capstone-project-team-18/issues/361
Description: Create a new ResumeItem table, which has a 1-1 relationship with ProjectReport
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '0240c84c3158'
down_revision: Union[str, Sequence[str], None] = 'a5249b44f9dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('resume_item',
                    sa.Column('id', sa.INTEGER(), nullable=False),
                    sa.Column('project_id', sa.INTEGER(), nullable=False),
                    sa.Column('title', sa.VARCHAR(), nullable=True),
                    sa.Column('frameworks', sa.JSON(), nullable=True),
                    sa.Column('start_date', sa.DATE(), nullable=True),
                    sa.Column('end_date', sa.DATE(), nullable=True),
                    sa.ForeignKeyConstraint(
                        ['project_id'], ['project_report.id']),
                    sa.PrimaryKeyConstraint('id'),
                    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('resume_item')
