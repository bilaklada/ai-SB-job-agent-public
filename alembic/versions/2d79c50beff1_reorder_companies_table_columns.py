"""reorder companies table columns

Revision ID: 2d79c50beff1
Revises: 5cbdb16886b0
Create Date: 2025-12-22 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d79c50beff1'
down_revision: Union[str, None] = '5cbdb16886b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Reorder columns in companies table to match specification:

    Correct order:
    1. company_id (PK)
    2. company_name
    3. ats_id (FK)
    4. ats_name
    5. created_at
    6. updated_at
    7. ats_company_token
    8. account_id (FK)
    9. workflow_id (FK)
    """

    # Step 1: Create temporary table with correct column order
    op.execute("""
        CREATE TABLE companies_new (
            company_id BIGINT NOT NULL,
            company_name VARCHAR(50) NOT NULL,
            ats_id BIGINT NOT NULL,
            ats_name VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            ats_company_token VARCHAR(50),
            account_id BIGINT,
            workflow_id BIGINT,
            PRIMARY KEY (company_id)
        )
    """)

    # Step 2: Copy all data
    op.execute("""
        INSERT INTO companies_new (
            company_id, company_name, ats_id, ats_name, created_at, updated_at,
            ats_company_token, account_id, workflow_id
        )
        SELECT
            company_id, company_name, ats_id, ats_name, created_at, updated_at,
            ats_company_token, account_id, workflow_id
        FROM companies
    """)

    # Step 3: Drop indexes
    op.drop_index('ix_companies_workflow_id', table_name='companies')
    op.drop_index('ix_companies_company_name', table_name='companies')
    op.drop_index('ix_companies_ats_id', table_name='companies')
    op.drop_index('ix_companies_account_id', table_name='companies')

    # Step 4: Drop foreign keys FROM companies
    op.drop_constraint('companies_workflow_id_fkey', 'companies', type_='foreignkey')
    op.drop_constraint('companies_account_id_fkey', 'companies', type_='foreignkey')
    op.drop_constraint('companies_ats_id_fkey', 'companies', type_='foreignkey')

    # Step 5: Drop foreign keys TO companies (from other tables)
    op.drop_constraint('applications_company_id_fkey', 'applications', type_='foreignkey')

    # Step 6: Drop old table
    op.drop_table('companies')

    # Step 7: Rename new table
    op.rename_table('companies_new', 'companies')

    # Step 8: Recreate foreign keys FROM companies
    op.create_foreign_key('companies_ats_id_fkey', 'companies', 'atss', ['ats_id'], ['ats_id'], ondelete='CASCADE')
    op.create_foreign_key('companies_account_id_fkey', 'companies', 'accounts', ['account_id'], ['account_id'], ondelete='SET NULL')
    op.create_foreign_key('companies_workflow_id_fkey', 'companies', 'workflows', ['workflow_id'], ['workflow_id'], ondelete='SET NULL')

    # Step 9: Recreate foreign keys TO companies
    op.create_foreign_key('applications_company_id_fkey', 'applications', 'companies', ['company_id'], ['company_id'], ondelete='SET NULL')

    # Step 10: Recreate indexes
    op.create_index('ix_companies_company_name', 'companies', ['company_name'])
    op.create_index('ix_companies_ats_id', 'companies', ['ats_id'])
    op.create_index('ix_companies_account_id', 'companies', ['account_id'])
    op.create_index('ix_companies_workflow_id', 'companies', ['workflow_id'])


def downgrade() -> None:
    """
    Revert to previous column order.
    """

    # Create temp table with old order
    op.execute("""
        CREATE TABLE companies_old (
            company_id BIGINT NOT NULL,
            company_name VARCHAR(50) NOT NULL,
            ats_id BIGINT NOT NULL,
            ats_name VARCHAR(50) NOT NULL,
            ats_company_token VARCHAR(50),
            account_id BIGINT,
            workflow_id BIGINT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (company_id)
        )
    """)

    # Copy data back
    op.execute("""
        INSERT INTO companies_old (
            company_id, company_name, ats_id, ats_name, ats_company_token, account_id, workflow_id,
            created_at, updated_at
        )
        SELECT
            company_id, company_name, ats_id, ats_name, ats_company_token, account_id, workflow_id,
            created_at, updated_at
        FROM companies
    """)

    # Drop indexes
    op.drop_index('ix_companies_workflow_id', table_name='companies')
    op.drop_index('ix_companies_account_id', table_name='companies')
    op.drop_index('ix_companies_ats_id', table_name='companies')
    op.drop_index('ix_companies_company_name', table_name='companies')

    # Drop FKs
    op.drop_constraint('companies_workflow_id_fkey', 'companies', type_='foreignkey')
    op.drop_constraint('companies_account_id_fkey', 'companies', type_='foreignkey')
    op.drop_constraint('companies_ats_id_fkey', 'companies', type_='foreignkey')
    op.drop_constraint('applications_company_id_fkey', 'applications', type_='foreignkey')

    op.drop_table('companies')
    op.rename_table('companies_old', 'companies')

    # Recreate FKs
    op.create_foreign_key('companies_ats_id_fkey', 'companies', 'atss', ['ats_id'], ['ats_id'], ondelete='CASCADE')
    op.create_foreign_key('companies_account_id_fkey', 'companies', 'accounts', ['account_id'], ['account_id'], ondelete='SET NULL')
    op.create_foreign_key('companies_workflow_id_fkey', 'companies', 'workflows', ['workflow_id'], ['workflow_id'], ondelete='SET NULL')
    op.create_foreign_key('applications_company_id_fkey', 'applications', 'companies', ['company_id'], ['company_id'], ondelete='SET NULL')

    # Recreate indexes
    op.create_index('ix_companies_company_name', 'companies', ['company_name'])
    op.create_index('ix_companies_ats_id', 'companies', ['ats_id'])
    op.create_index('ix_companies_account_id', 'companies', ['account_id'])
    op.create_index('ix_companies_workflow_id', 'companies', ['workflow_id'])
