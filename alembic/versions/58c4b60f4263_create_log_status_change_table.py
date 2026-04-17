"""create_log_status_change_table

Revision ID: 58c4b60f4263
Revises: 604af3214252
Create Date: 2025-12-24 06:03:57.636287

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58c4b60f4263'
down_revision: Union[str, None] = '604af3214252'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create log_status_change table for tracking status changes."""
    op.create_table(
        'log_status_change',
        # Primary key
        sa.Column('lsc_id', sa.BigInteger(), autoincrement=True, nullable=False),

        # Table indicator (which table's status we're logging)
        sa.Column('lsc_table', sa.String(length=20), nullable=False),

        # Foreign keys
        sa.Column('profile_id', sa.BigInteger(), nullable=False),
        sa.Column('job_id', sa.BigInteger(), nullable=False),
        sa.Column('application_id', sa.BigInteger(), nullable=True),

        # Status change tracking
        sa.Column('initial_status', sa.String(length=50), nullable=False),
        sa.Column('final_status', sa.String(length=50), nullable=False),

        # Timestamp
        sa.Column('updated_at', sa.DateTime(), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('lsc_id'),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.profile_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.job_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.application_id'], ondelete='CASCADE'),

        # Check constraint for lsc_table (only 'jobs' or 'applications')
        sa.CheckConstraint("lsc_table IN ('jobs', 'applications')", name='check_lsc_table_valid')
    )

    # Indexes for performance
    op.create_index('ix_log_status_change_lsc_table', 'log_status_change', ['lsc_table'])
    op.create_index('ix_log_status_change_profile_id', 'log_status_change', ['profile_id'])
    op.create_index('ix_log_status_change_job_id', 'log_status_change', ['job_id'])
    op.create_index('ix_log_status_change_application_id', 'log_status_change', ['application_id'])
    op.create_index('ix_log_status_change_updated_at', 'log_status_change', ['updated_at'])

    # Composite index for common query patterns
    op.create_index(
        'ix_log_status_change_job_table',
        'log_status_change',
        ['job_id', 'lsc_table']
    )


def downgrade() -> None:
    """Drop log_status_change table."""
    op.drop_index('ix_log_status_change_job_table', table_name='log_status_change')
    op.drop_index('ix_log_status_change_updated_at', table_name='log_status_change')
    op.drop_index('ix_log_status_change_application_id', table_name='log_status_change')
    op.drop_index('ix_log_status_change_job_id', table_name='log_status_change')
    op.drop_index('ix_log_status_change_profile_id', table_name='log_status_change')
    op.drop_index('ix_log_status_change_lsc_table', table_name='log_status_change')
    op.drop_table('log_status_change')
