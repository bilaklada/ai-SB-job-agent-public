"""create_settings_table

Revision ID: ebe5aa9f74f6
Revises: b7a7d6bfc4ad
Create Date: 2025-12-30 16:33:39.294845

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ebe5aa9f74f6'
down_revision: Union[str, None] = 'b7a7d6bfc4ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create settings table for application configuration."""
    op.create_table(
        'settings',
        sa.Column('setting_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('setting_name', sa.String(length=100), nullable=False),
        sa.Column('setting_value', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.PrimaryKeyConstraint('setting_id'),
        sa.UniqueConstraint('setting_name'),
        comment='Application configuration settings'
    )

    # Create index on setting_name for fast lookups
    op.create_index('ix_settings_setting_name', 'settings', ['setting_name'])


def downgrade() -> None:
    """Drop settings table."""
    op.drop_index('ix_settings_setting_name', table_name='settings')
    op.drop_table('settings')
