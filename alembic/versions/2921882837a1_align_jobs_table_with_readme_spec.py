"""align_jobs_table_with_readme_spec

Revision ID: 2921882837a1
Revises: 764e6e2c8203
Create Date: 2025-12-13 10:05:32.481172

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2921882837a1'
down_revision: Union[str, None] = '764e6e2c8203'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Change salary fields from DOUBLE PRECISION to NUMERIC(12,2)
    # This ensures accurate currency handling without floating-point errors
    op.alter_column('jobs', 'salary_min',
                    type_=sa.Numeric(precision=12, scale=2),
                    existing_type=sa.Float(),
                    existing_nullable=True)

    op.alter_column('jobs', 'salary_max',
                    type_=sa.Numeric(precision=12, scale=2),
                    existing_type=sa.Float(),
                    existing_nullable=True)

    # 2. Add timezone support to timestamp fields
    # Convert existing timestamps to UTC timezone-aware timestamps
    # USING clause ensures existing data is preserved and interpreted as UTC
    op.alter_column('jobs', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=False,
                    postgresql_using="created_at AT TIME ZONE 'UTC'")

    op.alter_column('jobs', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=False,
                    postgresql_using="updated_at AT TIME ZONE 'UTC'")

    op.alter_column('jobs', 'posted_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=True,
                    postgresql_using="posted_at AT TIME ZONE 'UTC'")


def downgrade() -> None:
    # Revert timezone changes - convert back to plain timestamps
    op.alter_column('jobs', 'posted_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=True,
                    postgresql_using="posted_at::TIMESTAMP")

    op.alter_column('jobs', 'updated_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False,
                    postgresql_using="updated_at::TIMESTAMP")

    op.alter_column('jobs', 'created_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False,
                    postgresql_using="created_at::TIMESTAMP")

    # Revert salary type changes - back to DOUBLE PRECISION
    op.alter_column('jobs', 'salary_max',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(precision=12, scale=2),
                    existing_nullable=True)

    op.alter_column('jobs', 'salary_min',
                    type_=sa.Float(),
                    existing_type=sa.Numeric(precision=12, scale=2),
                    existing_nullable=True)
