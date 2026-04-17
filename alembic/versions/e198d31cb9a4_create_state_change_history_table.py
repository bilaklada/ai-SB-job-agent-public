"""create state_change_history table

Revision ID: e198d31cb9a4
Revises: a66aea3b2dff
Create Date: 2025-12-15 13:54:50.031443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e198d31cb9a4'
down_revision: Union[str, None] = 'a66aea3b2dff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create state_change_history table for complete audit trail.

    This table tracks every state change across all entities (jobs, applications, accounts).
    Optimized for audit queries with multiple indexes for performance.
    """
    # Create state_change_history table
    op.create_table(
        'state_change_history',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('entity_type', sa.String(20), nullable=False, comment="Type: 'job', 'application', 'account'"),
        sa.Column('entity_id', sa.BigInteger(), nullable=False, comment="ID of the entity that changed"),
        sa.Column('field_name', sa.String(50), nullable=False, comment="Field: 'status', 'match_score', etc."),
        sa.Column('old_value', sa.String(100), nullable=True, comment="Previous value (NULL for initial state)"),
        sa.Column('new_value', sa.String(100), nullable=False, comment="New value after transition"),
        sa.Column('changed_by', sa.String(50), nullable=False, comment="Actor: 'orchestrator', 'admin_api', etc."),
        sa.Column('reason', sa.Text(), nullable=True, comment="Human-readable explanation"),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Additional metadata"),
        sa.Column('changed_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False, comment="When change occurred"),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for optimal query performance
    # Index 1: Get all changes for a specific entity (most common query)
    op.create_index('ix_state_change_entity', 'state_change_history', ['entity_type', 'entity_id'])

    # Index 2: Filter by specific field (e.g., only status changes)
    op.create_index('ix_state_change_entity_field', 'state_change_history', ['entity_type', 'entity_id', 'field_name'])

    # Index 3: Analytics - transition patterns (e.g., new_url → approved_for_application)
    op.create_index('ix_state_change_field_values', 'state_change_history', ['field_name', 'old_value', 'new_value'])

    # Index 4: Time-based queries (recent changes, date ranges)
    op.create_index('ix_state_change_changed_at', 'state_change_history', ['changed_at'])

    # Index 5: Filter by actor (what did orchestrator change?)
    op.create_index('ix_state_change_changed_by', 'state_change_history', ['changed_by'])

    # Index 6: Time-ordered entity history (most efficient for timeline views)
    op.create_index('ix_state_change_entity_time', 'state_change_history', ['entity_type', 'entity_id', 'changed_at'])


def downgrade() -> None:
    """Drop state_change_history table and all indexes."""
    # Drop indexes first (in reverse order of creation)
    op.drop_index('ix_state_change_entity_time', 'state_change_history')
    op.drop_index('ix_state_change_changed_by', 'state_change_history')
    op.drop_index('ix_state_change_changed_at', 'state_change_history')
    op.drop_index('ix_state_change_field_values', 'state_change_history')
    op.drop_index('ix_state_change_entity_field', 'state_change_history')
    op.drop_index('ix_state_change_entity', 'state_change_history')

    # Drop table
    op.drop_table('state_change_history')
