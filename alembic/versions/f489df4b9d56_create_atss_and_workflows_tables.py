"""create_atss_and_workflows_tables

Revision ID: f489df4b9d56
Revises: e198d31cb9a4
Create Date: 2025-12-19 12:31:35.494982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f489df4b9d56'
down_revision: Union[str, None] = 'e198d31cb9a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create atss and workflows reference tables.

    These tables normalize ATS platforms and automation workflows:
    - atss: Reference table for all supported ATS platforms (Greenhouse, Lever, etc.)
    - workflows: Reference table for automation workflows per ATS and application type
    """
    # Create atss table
    op.create_table(
        'atss',
        sa.Column('ats_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('ats_name', sa.String(50), nullable=False, comment="Name of the ATS platform (e.g., Greenhouse, Lever, Workday)"),
        sa.PrimaryKeyConstraint('ats_id'),
        sa.UniqueConstraint('ats_name')
    )

    # Create index for atss table
    op.create_index('ix_atss_name', 'atss', ['ats_name'])

    # Create workflows table
    op.create_table(
        'workflows',
        sa.Column('workflow_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('workflow_type', sa.String(50), nullable=False, comment="Type of workflow: standard, with_assessment, with_video, referral, custom"),
        sa.Column('workflow_name', sa.String(50), nullable=False, comment="Unique workflow identifier (e.g., greenhouse_standard_v1)"),
        sa.PrimaryKeyConstraint('workflow_id'),
        sa.UniqueConstraint('workflow_name')
    )

    # Create indexes for workflows table
    op.create_index('ix_workflows_type', 'workflows', ['workflow_type'])
    op.create_index('ix_workflows_name', 'workflows', ['workflow_name'])


def downgrade() -> None:
    """Drop atss and workflows tables and all indexes."""
    # Drop workflows table and indexes
    op.drop_index('ix_workflows_name', 'workflows')
    op.drop_index('ix_workflows_type', 'workflows')
    op.drop_table('workflows')

    # Drop atss table and index
    op.drop_index('ix_atss_name', 'atss')
    op.drop_table('atss')
