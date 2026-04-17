"""refactor applications table with profile ats company workflow fks

Revision ID: a09508efc6df
Revises: 2c59155a3b11
Create Date: 2025-12-22 13:53:37.372866

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a09508efc6df'
down_revision: Union[str, None] = '2c59155a3b11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Refactor applications table:
    - Rename PK: id → application_id
    - Add profile_id FK (required)
    - Add ats_id, ats_name (optional ATS tracking)
    - Add company_id, company_name (optional company tracking)
    - Add workflow_id FK (optional workflow tracking)
    - Remove: applied_at, submission_channel, notes
    - Update all indexes
    """

    # Step 1: Drop existing indexes
    op.drop_index('ix_applications_job_id_status', table_name='applications')
    op.drop_index('ix_applications_status', table_name='applications')
    op.drop_index('ix_applications_account_id', table_name='applications')

    # Step 2: Drop existing foreign key constraint from ai_artifacts (references applications.id)
    op.drop_constraint('ai_artifacts_application_id_fkey', 'ai_artifacts', type_='foreignkey')

    # Step 3: Rename primary key column
    op.alter_column('applications', 'id', new_column_name='application_id')

    # Step 4: Add new columns
    op.add_column('applications', sa.Column('profile_id', sa.BigInteger(), nullable=True, comment='Which candidate profile is applying'))
    op.add_column('applications', sa.Column('ats_id', sa.BigInteger(), nullable=True, comment='Which ATS platform (FK to atss table)'))
    op.add_column('applications', sa.Column('ats_name', sa.String(length=50), nullable=True, comment='ATS platform name (denormalized from atss.ats_name)'))
    op.add_column('applications', sa.Column('company_id', sa.BigInteger(), nullable=True, comment='Which company (FK to companies table)'))
    op.add_column('applications', sa.Column('company_name', sa.String(length=50), nullable=True, comment='Company name (denormalized from companies.company_name)'))
    op.add_column('applications', sa.Column('workflow_id', sa.BigInteger(), nullable=True, comment='Which automation workflow was used'))

    # Step 5: Set profile_id to a default value (1) for existing rows, then make it NOT NULL
    # Note: This assumes profile with id=1 exists. Adjust if needed.
    op.execute("UPDATE applications SET profile_id = 1 WHERE profile_id IS NULL")
    op.alter_column('applications', 'profile_id', nullable=False)

    # Step 6: Create new foreign keys
    op.create_foreign_key('applications_profile_id_fkey', 'applications', 'profiles', ['profile_id'], ['profile_id'], ondelete='CASCADE')
    op.create_foreign_key('applications_ats_id_fkey', 'applications', 'atss', ['ats_id'], ['ats_id'], ondelete='SET NULL')
    op.create_foreign_key('applications_company_id_fkey', 'applications', 'companies', ['company_id'], ['company_id'], ondelete='SET NULL')
    op.create_foreign_key('applications_workflow_id_fkey', 'applications', 'workflows', ['workflow_id'], ['workflow_id'], ondelete='SET NULL')

    # Step 7: Recreate foreign key from ai_artifacts with new PK name
    op.create_foreign_key('ai_artifacts_application_id_fkey', 'ai_artifacts', 'applications', ['application_id'], ['application_id'], ondelete='CASCADE')

    # Step 8: Drop old columns
    op.drop_column('applications', 'notes')
    op.drop_column('applications', 'submission_channel')
    op.drop_column('applications', 'applied_at')

    # Step 9: Create new indexes
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
    Revert applications table to previous structure.
    """

    # Step 1: Drop new indexes
    op.drop_index('ix_applications_job_status', table_name='applications')
    op.drop_index('ix_applications_workflow_id', table_name='applications')
    op.drop_index('ix_applications_account_id', table_name='applications')
    op.drop_index('ix_applications_company_id', table_name='applications')
    op.drop_index('ix_applications_ats_id', table_name='applications')
    op.drop_index('ix_applications_status', table_name='applications')
    op.drop_index('ix_applications_profile_id', table_name='applications')
    op.drop_index('ix_applications_job_id', table_name='applications')

    # Step 2: Add back old columns
    op.add_column('applications', sa.Column('applied_at', postgresql.TIMESTAMP(timezone=True), nullable=True, comment='When application was successfully submitted'))
    op.add_column('applications', sa.Column('submission_channel', sa.String(length=30), nullable=True, comment='Which ATS/portal: greenhouse, lever, workday, etc.'))
    op.add_column('applications', sa.Column('notes', sa.Text(), nullable=True, comment='Debugging notes, error messages, etc.'))

    # Step 3: Drop foreign key from ai_artifacts
    op.drop_constraint('ai_artifacts_application_id_fkey', 'ai_artifacts', type_='foreignkey')

    # Step 4: Drop new foreign keys (in downgrade)
    op.drop_constraint('applications_workflow_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_company_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_ats_id_fkey', 'applications', type_='foreignkey')
    op.drop_constraint('applications_profile_id_fkey', 'applications', type_='foreignkey')

    # Step 5: Drop new columns
    op.drop_column('applications', 'workflow_id')
    op.drop_column('applications', 'company_name')
    op.drop_column('applications', 'company_id')
    op.drop_column('applications', 'ats_name')
    op.drop_column('applications', 'ats_id')
    op.drop_column('applications', 'profile_id')

    # Step 6: Rename primary key column back
    op.alter_column('applications', 'application_id', new_column_name='id')

    # Step 7: Recreate foreign key from ai_artifacts with old PK name
    op.create_foreign_key('ai_artifacts_application_id_fkey', 'ai_artifacts', 'applications', ['application_id'], ['id'], ondelete='CASCADE')

    # Step 8: Recreate old indexes
    op.create_index('ix_applications_account_id', 'applications', ['account_id'])
    op.create_index('ix_applications_status', 'applications', ['status'])
    op.create_index('ix_applications_job_id_status', 'applications', ['job_id', 'status'])
