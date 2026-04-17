"""add_salary_and_posted_at_fields

Revision ID: 764e6e2c8203
Revises: 45d2fe3cfd59
Create Date: 2025-11-29 19:51:04.281406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '764e6e2c8203'
down_revision: Union[str, None] = '45d2fe3cfd59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add salary and posting date columns to jobs table
    op.add_column('jobs', sa.Column('salary_min', sa.Float(), nullable=True))
    op.add_column('jobs', sa.Column('salary_max', sa.Float(), nullable=True))
    op.add_column('jobs', sa.Column('salary_currency', sa.String(length=10), nullable=True))
    op.add_column('jobs', sa.Column('posted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove salary and posting date columns from jobs table
    op.drop_column('jobs', 'posted_at')
    op.drop_column('jobs', 'salary_currency')
    op.drop_column('jobs', 'salary_max')
    op.drop_column('jobs', 'salary_min')
