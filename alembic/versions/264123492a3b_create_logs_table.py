"""create_logs_table

Revision ID: 264123492a3b
Revises: cb52b42a8e78
Create Date: 2025-12-13 14:37:59.169120

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '264123492a3b'
down_revision: Union[str, None] = 'cb52b42a8e78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('level', sa.String(10), nullable=False),
        sa.Column('component', sa.String(30), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_logs_timestamp', 'logs', ['timestamp'])
    op.create_index('ix_logs_level', 'logs', ['level'])
    op.create_index('ix_logs_component', 'logs', ['component'])
    op.create_index('ix_logs_level_timestamp', 'logs', ['level', 'timestamp'])


def downgrade() -> None:
    op.drop_index('ix_logs_level_timestamp', 'logs')
    op.drop_index('ix_logs_component', 'logs')
    op.drop_index('ix_logs_level', 'logs')
    op.drop_index('ix_logs_timestamp', 'logs')
    op.drop_table('logs')
