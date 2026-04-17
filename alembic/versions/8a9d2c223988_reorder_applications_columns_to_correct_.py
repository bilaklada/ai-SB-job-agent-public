"""reorder applications columns to correct order

Revision ID: 8a9d2c223988
Revises: db1ba23714f7
Create Date: 2025-12-22 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a9d2c223988'
down_revision: Union[str, None] = 'db1ba23714f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Reorder columns in applications table to match specification:

    Correct order:
    1. application_id (PK)
    2. job_id (FK)
    3. profile_id (FK)
    4. status
    5. created_at
    6. updated_at
    7. ats_id (FK)
    8. ats_name
    9. company_id (FK)
    10. company_name
    11. account_id (FK)
    12. workflow_id (FK)
    """

    # Step 1: Create temporary table with correct column order
    op.execute("""
        CREATE TABLE applications_new (
            application_id BIGINT NOT NULL,
            job_id BIGINT NOT NULL,
            profile_id BIGINT NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'created',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            ats_id BIGINT,
            ats_name VARCHAR(50),
            company_id BIGINT,
            company_name VARCHAR(50),
            account_id BIGINT,
            workflow_id BIGINT,
            PRIMARY KEY (application_id)
        )
    """)

    # Step 2: Copy all data from applications to applications_new
    op.execute("""
        INSERT INTO applications_new (
            application_id, job_id, profile_id, status, created_at, updated_at,
            ats_id, ats_name, company_id, company_name, account_id, workflow_id
        )
        SELECT
            application_id, job_id, profile_id, status, created_at, updated_at,
            ats_id, ats_name, company_id, company_name, account_id, workflow_id
        FROM applications
    """)

    # Step 3: Drop all indexes on applications table
    op.drop_index('ix_applications_job_status', table_name='applications')
    op.drop_index('ix_applications_workflow_id', table_name='applications')
    op.drop_index('ix_applications_account_id', table_name='applications')
    op.drop_index('ix_applications_company_id', table_name='applications')
    op.drop_index('ix_applications_ats_id', table_name='applications')
    op.drop_index('ix_applications_status', table_name='applications')
    op.drop_index('ix_applications_profile_id', table_name='applications')
    op.drop_index('ix_applications_job_id', table_name='applications')

    # Step 4: Drop all foreign keys FROM applications
    op.drop_constraint('applications_workflow_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_company_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_ats_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_profile_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_account_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_job_id_fkey', 'applications', type_='foreignkey')

    # Step 5: Drop foreign keys TO applications (from other tables)
    op.drop_constraint('ai_artifacts_application_id_fkey', 'ai_artifacts', type_='foreignkey')

    # Step 6: Drop old applications table
    op.drop_table('applications')

    # Step 7: Rename new table to applications
    op.rename_table('applications_new', 'applications')

    # Step 8: Recreate all foreign keys FROM applications
    op.create_foreign_key('applications_job_id_fkey', 'applications', 'jobs', ['job_id'], ['job_id'], ondelete='CASCADE')
    op.create_foreign_key('applications_profile_id_fkey', 'applications', 'profiles', ['profile_id'], ['profile_id'], ondelete='CASCADE')
    op.create_foreign_key('applications_ats_id_fkey', 'applications', 'atss', ['ats_id'], ['ats_id'], ondelete='SET NULL')
    op.create_foreign_key('applications_company_id_fkey', 'applications', 'companies', ['company_id'], ['company_id'], ondelete='SET NULL')
    op.create_foreign_key('applications_account_id_fkey', 'applications', 'accounts', ['account_id'], ['account_id'], ondelete='SET NULL')
    op.create_foreign_key('applications_workflow_id_fkey', 'applications', 'workflows', ['workflow_id'], ['workflow_id'], ondelete='SET NULL')

    # Step 9: Recreate foreign keys TO applications (from other tables)
    op.create_foreign_key('ai_artifacts_application_id_fkey', 'ai_artifacts', 'applications', ['application_id'], ['application_id'], ondelete='CASCADE')

    # Step 10: Recreate all indexes
    op.create_index('ix_applications_job_id', 'applications', ['job_id'])
    op.create_index('ix_applications_profile_id', 'applications', ['profile_id'])
    op.create_index('ix_applications_status', 'applications', ['status'])
    op.create_index('ix_applications_ats_id', 'applications', ['ats_id'])
    op.create_index('ix_applications_company_id', 'applications', ['company_id'])
    op.create_index('ix_applications_account_id', 'applications', ['account_id'])
    op.create_index('ix_applications_workflow_id', 'applications', ['workflow_id'])
    op.create_index('ix_applications_job_status', 'applications', ['job_id', 'status'])


def downgrade() -> None:
    """
    Revert to previous column order (not recommended, just for safety).
    """

    # Create temp table with old order
    op.execute("""
        CREATE TABLE applications_old (
            application_id BIGINT NOT NULL,
            job_id BIGINT NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'created',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            account_id BIGINT,
            profile_id BIGINT NOT NULL,
            ats_id BIGINT,
            ats_name VARCHAR(50),
            company_id BIGINT,
            company_name VARCHAR(50),
            workflow_id BIGINT,
            PRIMARY KEY (application_id)
        )
    """)

    # Copy data back
    op.execute("""
        INSERT INTO applications_old (
            application_id, job_id, status, created_at, updated_at, account_id,
            profile_id, ats_id, ats_name, company_id, company_name, workflow_id
        )
        SELECT
            application_id, job_id, status, created_at, updated_at, account_id,
            profile_id, ats_id, ats_name, company_id, company_name, workflow_id
        FROM applications
    """)

    # Drop indexes
    op.drop_index('ix_applications_job_status', table_name='applications')
    op.drop_index('ix_applications_workflow_id', table_name='applications')
    op.drop_index('ix_applications_account_id', table_name='applications')
    op.drop_index('ix_applications_company_id', table_name='applications')
    op.drop_index('ix_applications_ats_id', table_name='applications')
    op.drop_index('ix_applications_status', table_name='applications')
    op.drop_index('ix_applications_profile_id', table_name='applications')
    op.drop_index('ix_applications_job_id', table_name='applications')

    # Drop FKs
    op.drop_constraint('applications_workflow_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_company_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_ats_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_profile_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_account_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_job_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('ai_artifacts_application_id_fkey', 'ai_artifacts', type_='foreignkey')

    op.drop_table('applications')
    op.rename_table('applications_old', 'applications')

    # Recreate FKs
    op.create_foreign_key('applications_job_id_fkey', 'applications', 'jobs', ['job_id'], ['job_id'], ondelete='CASCADE')
    op.create_foreign_key('applications_profile_id_fkey', 'applications', 'profiles', ['profile_id'], ['profile_id'], ondelete='CASCADE')
    op.create_foreign_key('applications_ats_id_fkey', 'applications', 'atss', ['ats_id'], ['ats_id'], ondelete='SET NULL')
    op.create_foreign_key('applications_company_id_fkey', 'applications', 'companies', ['company_id'], ['company_id'], ondelete='SET NULL')
    op.create_foreign_key('applications_account_id_fkey', 'applications', 'accounts', ['account_id'], ['account_id'], ondelete='SET NULL')
    op.create_foreign_key('applications_workflow_id_fkey', 'applications', 'workflows', ['workflow_id'], ['workflow_id'], ondelete='SET NULL')
    op.create_foreign_key('ai_artifacts_application_id_fkey', 'ai_artifacts', 'applications', ['application_id'], ['application_id'], ondelete='CASCADE')

    # Recreate indexes
    op.create_index('ix_applications_job_id', 'applications', ['job_id'])
    op.create_index('ix_applications_profile_id', 'applications', ['profile_id'])
    op.create_index('ix_applications_status', 'applications', ['status'])
    op.create_index('ix_applications_ats_id', 'applications', ['ats_id'])
    op.create_index('ix_applications_company_id', 'applications', ['company_id'])
    op.create_index('ix_applications_account_id', 'applications', ['account_id'])
    op.create_index('ix_applications_workflow_id', 'applications', ['workflow_id'])
    op.create_index('ix_applications_job_status', 'applications', ['job_id', 'status'])
