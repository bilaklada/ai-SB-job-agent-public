"""fix_job_id_sequence

Revision ID: 12eddce29636
Revises: 5cbdb16886b0
Create Date: 2025-12-23 06:30:00.000000

PROBLEM:
Migration 5cbdb16886b0 (reorder jobs table columns) recreated the jobs table
but defined job_id as plain BIGINT instead of BIGSERIAL. This caused the
sequence to be lost, breaking auto-increment functionality.

FIX:
1. Create jobs_job_id_seq sequence
2. Set its value to max(job_id) + 1
3. Set job_id DEFAULT to nextval('jobs_job_id_seq')
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12eddce29636'
down_revision: Union[str, None] = '2d79c50beff1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix job_id auto-increment by creating sequence and setting default.
    """
    # Step 1: Create the sequence
    op.execute("CREATE SEQUENCE IF NOT EXISTS jobs_job_id_seq")

    # Step 2: Set sequence value to max existing job_id + 1
    # This ensures new inserts won't conflict with existing IDs
    op.execute("""
        SELECT setval('jobs_job_id_seq',
            COALESCE((SELECT MAX(job_id) FROM jobs), 0) + 1,
            false)
    """)

    # Step 3: Set job_id column default to use the sequence
    op.execute("ALTER TABLE jobs ALTER COLUMN job_id SET DEFAULT nextval('jobs_job_id_seq')")

    # Step 4: Make the sequence owned by the column (for proper CASCADE behavior)
    op.execute("ALTER SEQUENCE jobs_job_id_seq OWNED BY jobs.job_id")


def downgrade() -> None:
    """
    Remove sequence and default (reverting to broken state).
    """
    # Remove default
    op.execute("ALTER TABLE jobs ALTER COLUMN job_id DROP DEFAULT")

    # Drop sequence (CASCADE will handle ownership)
    op.execute("DROP SEQUENCE IF EXISTS jobs_job_id_seq CASCADE")
