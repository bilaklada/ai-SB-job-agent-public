"""create_companies_table

Revision ID: 2c59155a3b11
Revises: a5587e4a0821
Create Date: 2025-12-19 13:01:58.038696

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c59155a3b11'
down_revision: Union[str, None] = 'a5587e4a0821'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create companies table
    op.create_table(
        'companies',
        sa.Column('company_id', sa.BigInteger(), autoincrement=True, nullable=False, comment='Primary key'),
        sa.Column('company_name', sa.String(length=50), nullable=False, comment='Company name'),
        sa.Column('ats_id', sa.BigInteger(), nullable=False, comment='Foreign key to atss table'),
        sa.Column('ats_name', sa.String(length=50), nullable=False, comment='ATS name (denormalized from atss table)'),
        sa.Column('ats_company_token', sa.String(length=50), nullable=True, comment='Company-specific token for ATS (optional)'),
        sa.Column('account_id', sa.BigInteger(), nullable=True, comment='Foreign key to accounts table (optional)'),
        sa.Column('workflow_id', sa.BigInteger(), nullable=True, comment='Foreign key to workflows table (optional)'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False, comment='When record was created'),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False, comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('company_id'),
        sa.ForeignKeyConstraint(['ats_id'], ['atss.ats_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.account_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.workflow_id'], ondelete='SET NULL'),
    )

    # Create indexes for better query performance
    op.create_index('ix_companies_company_name', 'companies', ['company_name'])
    op.create_index('ix_companies_ats_id', 'companies', ['ats_id'])
    op.create_index('ix_companies_account_id', 'companies', ['account_id'])
    op.create_index('ix_companies_workflow_id', 'companies', ['workflow_id'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_companies_workflow_id', table_name='companies')
    op.drop_index('ix_companies_account_id', table_name='companies')
    op.drop_index('ix_companies_ats_id', table_name='companies')
    op.drop_index('ix_companies_company_name', table_name='companies')

    # Drop table
    op.drop_table('companies')
