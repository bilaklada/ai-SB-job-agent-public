"""reorder jobs table columns

Revision ID: 5cbdb16886b0
Revises: 8a9d2c223988
Create Date: 2025-12-22 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5cbdb16886b0'
down_revision: Union[str, None] = '8a9d2c223988'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Reorder columns in jobs table to match specification:

    Correct order:
    1. job_id (PK)
    2. profile_id (FK)
    3. url
    4. provider
    5. status
    6. match_score
    7. created_at
    8. updated_at
    """

    # Step 1: Create temporary table with correct column order
    op.execute("""
        CREATE TABLE jobs_new (
            job_id BIGINT NOT NULL,
            profile_id BIGINT NOT NULL,
            url TEXT NOT NULL,
            provider VARCHAR(50) NOT NULL,
            status VARCHAR(30) NOT NULL,
            match_score DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (job_id),
            UNIQUE (url)
        )
    """)

    # Step 2: Copy all data from jobs to jobs_new
    op.execute("""
        INSERT INTO jobs_new (
            job_id, profile_id, url, provider, status, match_score, created_at, updated_at
        )
        SELECT
            job_id, profile_id, url, provider, status, match_score, created_at, updated_at
        FROM jobs
    """)

    # Step 3: Drop all indexes on jobs table
    op.drop_index('ix_jobs_status_match_score', table_name='jobs')
    op.drop_index('ix_jobs_status_created_at', table_name='jobs')
    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_index('ix_jobs_provider_created_at', table_name='jobs')
    op.drop_index('ix_jobs_provider', table_name='jobs')
    op.drop_index('ix_jobs_profile_status', table_name='jobs')
    op.drop_index('ix_jobs_profile_id', table_name='jobs')
    op.drop_index('ix_jobs_match_score', table_name='jobs')
    op.drop_index('ix_jobs_created_at', table_name='jobs')

    # Drop UNIQUE constraint on url (this is a constraint, not just an index)
    op.drop_constraint('jobs_url_key', 'jobs', type_='unique')

    # Step 4: Drop foreign key FROM jobs
    op.drop_constraint('jobs_profile_id_fkey', 'jobs', type_='foreignkey')

    # Step 5: Drop foreign keys TO jobs (from other tables)
    op.drop_constraint('applications_job_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('ai_artifacts_job_id_fkey', 'ai_artifacts', type_='foreignkey')

    # Step 6: Drop old jobs table
    op.drop_table('jobs')

    # Step 7: Rename new table to jobs
    op.rename_table('jobs_new', 'jobs')

    # Step 8: Recreate foreign key FROM jobs
    op.create_foreign_key('jobs_profile_id_fkey', 'jobs', 'profiles', ['profile_id'], ['profile_id'], ondelete='CASCADE')

    # Step 9: Recreate foreign keys TO jobs (from other tables)
    op.create_foreign_key('applications_job_id_fkey', 'applications', 'jobs', ['job_id'], ['job_id'], ondelete='CASCADE')
    op.create_foreign_key('ai_artifacts_job_id_fkey', 'ai_artifacts', 'jobs', ['job_id'], ['job_id'], ondelete='CASCADE')

    # Step 10: Recreate all indexes
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])
    op.create_index('ix_jobs_match_score', 'jobs', ['match_score'])
    op.create_index('ix_jobs_profile_id', 'jobs', ['profile_id'])
    op.create_index('ix_jobs_profile_status', 'jobs', ['profile_id', 'status'])
    op.create_index('ix_jobs_provider', 'jobs', ['provider'])
    op.create_index('ix_jobs_provider_created_at', 'jobs', ['provider', 'created_at'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_status_created_at', 'jobs', ['status', 'created_at'])
    op.create_index('ix_jobs_status_match_score', 'jobs', ['status', 'match_score'])


def downgrade() -> None:
    """
    Revert to previous column order.
    """

    # Create temp table with old order
    op.execute("""
        CREATE TABLE jobs_old (
            job_id BIGINT NOT NULL,
            url TEXT NOT NULL,
            provider VARCHAR(50) NOT NULL,
            status VARCHAR(30) NOT NULL,
            match_score DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            profile_id BIGINT NOT NULL,
            PRIMARY KEY (job_id),
            UNIQUE (url)
        )
    """)

    # Copy data back
    op.execute("""
        INSERT INTO jobs_old (
            job_id, url, provider, status, match_score, created_at, updated_at, profile_id
        )
        SELECT
            job_id, url, provider, status, match_score, created_at, updated_at, profile_id
        FROM jobs
    """)

    # Drop indexes
    op.drop_index('ix_jobs_status_match_score', table_name='jobs')
    op.drop_index('ix_jobs_status_created_at', table_name='jobs')
    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_index('ix_jobs_provider_created_at', table_name='jobs')
    op.drop_index('ix_jobs_provider', table_name='jobs')
    op.drop_index('ix_jobs_profile_status', table_name='jobs')
    op.drop_index('ix_jobs_profile_id', table_name='jobs')
    op.drop_index('ix_jobs_match_score', table_name='jobs')
    op.drop_index('ix_jobs_created_at', table_name='jobs')

    # Drop FKs
    op.drop_constraint('jobs_profile_id_fkey', 'jobs', type_='foreignkey')
    op.drop_constraint('applications_job_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('ai_artifacts_job_id_fkey', 'ai_artifacts', type_='foreignkey')

    op.drop_table('jobs')
    op.rename_table('jobs_old', 'jobs')

    # Recreate FKs
    op.create_foreign_key('jobs_profile_id_fkey', 'jobs', 'profiles', ['profile_id'], ['profile_id'], ondelete='CASCADE')
    op.create_foreign_key('applications_job_id_fkey', 'applications', 'jobs', ['job_id'], ['job_id'], ondelete='CASCADE')
    op.create_foreign_key('ai_artifacts_job_id_fkey', 'ai_artifacts', 'jobs', ['job_id'], ['job_id'], ondelete='CASCADE')

    # Recreate indexes
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])
    op.create_index('ix_jobs_match_score', 'jobs', ['match_score'])
    op.create_index('ix_jobs_profile_id', 'jobs', ['profile_id'])
    op.create_index('ix_jobs_profile_status', 'jobs', ['profile_id', 'status'])
    op.create_index('ix_jobs_provider', 'jobs', ['provider'])
    op.create_index('ix_jobs_provider_created_at', 'jobs', ['provider', 'created_at'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_status_created_at', 'jobs', ['status', 'created_at'])
    op.create_index('ix_jobs_status_match_score', 'jobs', ['status', 'match_score'])
