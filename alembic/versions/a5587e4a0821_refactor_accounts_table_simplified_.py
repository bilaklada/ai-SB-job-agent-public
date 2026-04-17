"""refactor_accounts_table_simplified_schema

Revision ID: a5587e4a0821
Revises: f489df4b9d56
Create Date: 2025-12-19 12:44:31.524050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5587e4a0821'
down_revision: Union[str, None] = 'f489df4b9d56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Refactor accounts table with simplified schema.

    Changes:
    - Rename PK: id → account_id
    - Rename: portal_name → company_name
    - Rename: domain → login_url
    - Rename: password_encrypted → login_password
    - Add: updated_at column
    - Remove: All unused columns (login_username, applicant_full_name, profile_url,
              applications_page_url, account_origin_job_id, account_health, is_active,
              notes, verified_at, last_login_at, last_status_check_at)
    - Update indexes to match new columns

    Note: Table is empty, so we can safely drop and recreate.
    """

    # Drop old indexes
    op.drop_index('ix_accounts_health', 'accounts')
    op.drop_index('ix_accounts_portal_domain', 'accounts')
    op.drop_index('ix_accounts_login_email', 'accounts')

    # Drop foreign key constraint from applications table
    op.drop_constraint('applications_account_id_fkey', 'applications', type_='foreignkey')

    # Drop the old accounts table
    op.drop_table('accounts')

    # Create new simplified accounts table
    op.create_table(
        'accounts',
        sa.Column('account_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('company_name', sa.Text(), nullable=False, comment="Company name (e.g., 'Acme Corp', 'Greenhouse Inc')"),
        sa.Column('login_url', sa.Text(), nullable=False, comment="Full login URL (e.g., 'https://jobs.company.com/login')"),
        sa.Column('login_email', sa.Text(), nullable=False, comment="Email used for login"),
        sa.Column('login_password', sa.Text(), nullable=False, comment="ENCRYPTED password (never store plain text!)"),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False, comment="When account was created in DB"),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False, comment="Last time account was updated"),
        sa.PrimaryKeyConstraint('account_id')
    )

    # Create new indexes
    op.create_index('ix_accounts_login_email', 'accounts', ['login_email'])
    op.create_index('ix_accounts_company_name', 'accounts', ['company_name'])

    # Recreate foreign key constraint in applications table pointing to new PK
    op.create_foreign_key(
        'applications_account_id_fkey',
        'applications',
        'accounts',
        ['account_id'],
        ['account_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """
    Revert accounts table to previous schema.

    Note: This will lose data if any accounts were created in the new schema.
    """

    # Drop new indexes
    op.drop_index('ix_accounts_company_name', 'accounts')
    op.drop_index('ix_accounts_login_email', 'accounts')

    # Drop foreign key constraint from applications
    op.drop_constraint('applications_account_id_fkey', 'applications', type_='foreignkey')

    # Drop new table
    op.drop_table('accounts')

    # Recreate old accounts table with all original columns
    op.create_table(
        'accounts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('portal_name', sa.Text(), nullable=False, comment="Portal name (e.g. 'Greenhouse', 'Lever')"),
        sa.Column('domain', sa.Text(), nullable=False, comment="Login domain (e.g. 'boards.greenhouse.io')"),
        sa.Column('login_email', sa.Text(), nullable=False, comment="Email used for login"),
        sa.Column('login_username', sa.Text(), nullable=True, comment="Username (if different from email)"),
        sa.Column('password_encrypted', sa.Text(), nullable=False, comment="ENCRYPTED password (never store plain text!)"),
        sa.Column('applicant_full_name', sa.Text(), nullable=False, comment="Full name on account"),
        sa.Column('profile_url', sa.Text(), nullable=True, comment="Direct link to profile page"),
        sa.Column('applications_page_url', sa.Text(), nullable=True, comment="Direct link to 'My Applications' page"),
        sa.Column('account_origin_job_id', sa.BigInteger(), nullable=True, comment="Which job triggered creation of this account"),
        sa.Column('account_health', sa.String(20), nullable=False, server_default='ok', comment="Health status"),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='TRUE', comment="Should this account still be used?"),
        sa.Column('notes', sa.Text(), nullable=True, comment="Extra info: 2FA setup, warnings, etc."),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False, comment="When account was created in DB"),
        sa.Column('verified_at', sa.TIMESTAMP(timezone=True), nullable=True, comment="When email was verified"),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True, comment="Last successful login"),
        sa.Column('last_status_check_at', sa.TIMESTAMP(timezone=True), nullable=True, comment="Last time we checked account status"),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['account_origin_job_id'], ['jobs.id'], ondelete='SET NULL')
    )

    # Recreate old indexes
    op.create_index('ix_accounts_login_email', 'accounts', ['login_email'])
    op.create_index('ix_accounts_portal_domain', 'accounts', ['portal_name', 'domain'])
    op.create_index('ix_accounts_health', 'accounts', ['account_health'])

    # Recreate foreign key in applications pointing to old PK
    op.create_foreign_key(
        'applications_account_id_fkey',
        'applications',
        'accounts',
        ['account_id'],
        ['id'],
        ondelete='SET NULL'
    )
