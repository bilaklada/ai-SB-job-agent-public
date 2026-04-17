"""drop_logs_and_state_change_history_tables

Revision ID: 604af3214252
Revises: 12eddce29636
Create Date: 2025-12-24 06:03:02.474147

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '604af3214252'
down_revision: Union[str, None] = '12eddce29636'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop old logging tables: logs and state_change_history."""
    # Drop state_change_history table
    op.drop_table('state_change_history')

    # Drop logs table
    op.drop_table('logs')


def downgrade() -> None:
    """Recreate tables (structure only, data cannot be restored)."""
    # Recreate logs table (structure from original migration)
    op.create_table(
        'logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('component', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_logs_level', 'logs', ['level'])
    op.create_index('ix_logs_component', 'logs', ['component'])
    op.create_index('ix_logs_timestamp', 'logs', ['timestamp'])

    # Recreate state_change_history table (structure from original migration)
    op.create_table(
        'state_change_history',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.BigInteger(), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=True),
        sa.Column('to_status', sa.String(length=50), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.job_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_state_change_history_job_id', 'state_change_history', ['job_id'])
    op.create_index('ix_state_change_history_changed_at', 'state_change_history', ['changed_at'])
