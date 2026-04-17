"""make_title_nullable_for_manual_jobs

Revision ID: 1fe2369a97fa
Revises: 2921882837a1
Create Date: 2025-12-13 10:29:42.893078

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fe2369a97fa'
down_revision: Union[str, None] = '2921882837a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make title nullable to support manual job creation with URL only
    # README spec: title | TEXT | YES (nullable)
    # Manual jobs can be added with just a URL, title will be scraped later
    op.alter_column('jobs', 'title',
                    existing_type=sa.String(length=500),
                    nullable=True)


def downgrade() -> None:
    # Revert title to NOT NULL
    # WARNING: This will fail if there are jobs with null titles
    op.alter_column('jobs', 'title',
                    existing_type=sa.String(length=500),
                    nullable=False)
