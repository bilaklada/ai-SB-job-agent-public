"""create_profile_table

Revision ID: b8e5bc5913a4
Revises: 0f42755a2adf
Create Date: 2025-12-13 11:21:49.154046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b8e5bc5913a4'
down_revision: Union[str, None] = '0f42755a2adf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create profile table
    # README spec: Unified profile with personal data and JSON fields for experience/skills/preferences
    op.create_table(
        'profile',
        # Primary key
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),

        # Personal information
        sa.Column('first_name', sa.Text(), nullable=False),
        sa.Column('last_name', sa.Text(), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('nationality', sa.String(length=2), nullable=True),
        sa.Column('passport_id', sa.Text(), nullable=True),

        # Contact information
        sa.Column('phone_num', sa.Text(), nullable=True),
        sa.Column('email', sa.Text(), nullable=False),

        # Location information
        sa.Column('current_city', sa.Text(), nullable=True),
        sa.Column('current_country', sa.String(length=2), nullable=True),

        # Work authorization and availability
        sa.Column('work_auth_notes', sa.Text(), nullable=True),
        sa.Column('ready_to_start_when', sa.Text(), nullable=True),
        sa.Column('relocation_policy', sa.Text(), nullable=True),
        sa.Column('remote_preference', sa.String(length=20), nullable=True),

        # Structured data (JSONB)
        sa.Column('experience_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('skills_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('prefs_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Links
        sa.Column('linkedin_url', sa.Text(), nullable=True),
        sa.Column('github_url', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        # Constraints
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop profile table
    op.drop_table('profile')
