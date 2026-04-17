"""create_applications_table

Revision ID: 6612c9fc98f0
Revises: 1fe2369a97fa
Create Date: 2025-12-13 10:53:56.256208

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6612c9fc98f0'
down_revision: Union[str, None] = '1fe2369a97fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create applications table
    # README spec: Track application submission attempts with status lifecycle
    # NOTE: Foreign key to accounts.id will be added later when accounts table is created
    op.create_table(
        'applications',
        # Primary key
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),

        # Foreign keys
        sa.Column('job_id', sa.BigInteger(), nullable=False),
        sa.Column('account_id', sa.BigInteger(), nullable=True),  # FK constraint added later

        # Application data
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('submission_channel', sa.String(length=30), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE')
        # Note: FK constraint for account_id → accounts.id will be added in later migration
        # when accounts table is created (Phase 3 task)
    )

    # Add composite index on (job_id, status) for query performance
    # This optimizes queries like: "Get all submitted applications for job X"
    op.create_index(
        'ix_applications_job_id_status',
        'applications',
        ['job_id', 'status']
    )


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_applications_job_id_status', table_name='applications')

    # Drop table
    op.drop_table('applications')
