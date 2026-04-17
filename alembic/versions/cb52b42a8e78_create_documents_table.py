"""create_documents_table

Revision ID: cb52b42a8e78
Revises: b8e5bc5913a4
Create Date: 2025-12-13 14:30:32.637854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb52b42a8e78'
down_revision: Union[str, None] = 'b8e5bc5913a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('owner_id', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('storage_backend', sa.String(20), nullable=False),
        sa.Column('storage_key', sa.Text(), nullable=False),
        sa.Column('original_filename', sa.Text(), nullable=False),
        sa.Column('mime_type', sa.String(50), nullable=False),
        sa.Column('language', sa.String(5), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='FALSE'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_foreign_key('fk_documents_owner_id', 'documents', 'profile', ['owner_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_documents_owner_id', 'documents', ['owner_id'])
    op.create_index('ix_documents_type', 'documents', ['type'])
    op.create_index('ix_documents_owner_type_primary', 'documents', ['owner_id', 'type', 'is_primary'])


def downgrade() -> None:
    op.drop_index('ix_documents_owner_type_primary', 'documents')
    op.drop_index('ix_documents_type', 'documents')
    op.drop_index('ix_documents_owner_id', 'documents')
    op.drop_constraint('fk_documents_owner_id', 'documents', type_='foreignkey')
    op.drop_table('documents')
