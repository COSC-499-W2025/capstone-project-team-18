"""add contribution pattern columns

Revision ID: 7b9c0f4c4c1a
Revises: 3275deff618c
Create Date: 2026-01-29 05:20:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from src.database.utils.column_statistic_serializer import ColumnStatisticSerializer

# revision identifiers, used by Alembic.
revision: str = '7b9c0f4c4c1a'
down_revision: Union[str, Sequence[str], None] = '3275deff618c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_report', sa.Column('commit_type_distribution', ColumnStatisticSerializer(), nullable=True))
    op.add_column('project_report', sa.Column('work_pattern', sa.String(), nullable=True))
    op.add_column('project_report', sa.Column('collaboration_role', sa.String(), nullable=True))
    op.add_column('project_report', sa.Column('activity_metrics', ColumnStatisticSerializer(), nullable=True))
    op.add_column('project_report', sa.Column('role_description', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('project_report', 'role_description')
    op.drop_column('project_report', 'activity_metrics')
    op.drop_column('project_report', 'collaboration_role')
    op.drop_column('project_report', 'work_pattern')
    op.drop_column('project_report', 'commit_type_distribution')
