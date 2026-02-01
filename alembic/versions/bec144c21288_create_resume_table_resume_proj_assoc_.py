"""create resume table & resume_proj_assoc

Revision ID: bec144c21288
Revises: 841e8be99ec3 (Rename association_table to proj_user_assoc)
Create Date: 2026-01-22 00:10:53.634111
Related Issue: https://github.com/COSC-499-W2025/capstone-project-team-18/issues/361
Description: Define the ORM for two new tables: Resume and resume_proj_assoc
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bec144c21288'
down_revision: Union[str, Sequence[str], None] = '841e8be99ec3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'resume',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('list', sa.JSON(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('github', sa.String(), nullable=True),
        sa.Column('skills', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'resume_proj_assoc',
        sa.Column('project_report_id', sa.Integer(), nullable=False),
        sa.Column('resume_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['project_report_id'],
            ['project_report.id'],
        ),
        sa.ForeignKeyConstraint(
            ['resume_id'],
            ['resume.id'],
        ),
        sa.PrimaryKeyConstraint('project_report_id', 'resume_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('resume_proj_assoc')
    op.drop_table('resume')
