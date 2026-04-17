"""create_accounts_table

Revision ID: 0f42755a2adf
Revises: 6612c9fc98f0
Create Date: 2025-12-13 11:11:34.200580

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f42755a2adf'
down_revision: Union[str, None] = '6612c9fc98f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create accounts table
    # README spec: Track login accounts for job application portals/ATS systems
    op.create_table(
        'accounts',
        # Primary key
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),

        # Portal/ATS information
        sa.Column('portal_name', sa.Text(), nullable=False),
        sa.Column('domain', sa.Text(), nullable=False),

        # Login credentials
        sa.Column('login_email', sa.Text(), nullable=False),
        sa.Column('login_username', sa.Text(), nullable=True),
        sa.Column('password_encrypted', sa.Text(), nullable=False),

        # Applicant information
        sa.Column('applicant_full_name', sa.Text(), nullable=False),

        # URLs
        sa.Column('profile_url', sa.Text(), nullable=True),
        sa.Column('applications_page_url', sa.Text(), nullable=True),

        # Foreign keys
        sa.Column('account_origin_job_id', sa.BigInteger(), nullable=True),

        # Account status
        sa.Column('account_health', sa.String(length=20), nullable=False, server_default='ok'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_status_check_at', sa.DateTime(timezone=True), nullable=True),

        # Notes
        sa.Column('notes', sa.Text(), nullable=True),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['account_origin_job_id'], ['jobs.id'], ondelete='SET NULL')
    )

    # Add indexes for common query patterns
    # Index on login_email for account lookup during login
    op.create_index('ix_accounts_login_email', 'accounts', ['login_email'])

    # Composite index on (portal_name, domain) for finding accounts by portal
    op.create_index('ix_accounts_portal_domain', 'accounts', ['portal_name', 'domain'])

    # Index on account_health for filtering healthy/unhealthy accounts
    op.create_index('ix_accounts_health', 'accounts', ['account_health'])

    # Now add the missing foreign key constraint to applications.account_id
    # This was deferred from the applications table creation because accounts didn't exist yet
    op.create_foreign_key(
        'fk_applications_account_id',
        'applications',
        'accounts',
        ['account_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign key constraint from applications table first
    op.drop_constraint('fk_applications_account_id', 'applications', type_='foreignkey')

    # Drop indexes
    op.drop_index('ix_accounts_health', table_name='accounts')
    op.drop_index('ix_accounts_portal_domain', table_name='accounts')
    op.drop_index('ix_accounts_login_email', table_name='accounts')

    # Drop table
    op.drop_table('accounts')
