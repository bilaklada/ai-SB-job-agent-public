"""create_ai_artifacts_table

Revision ID: b019947b146c
Revises: 264123492a3b
Create Date: 2025-12-13 14:39:01.904133

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b019947b146c'
down_revision: Union[str, None] = '264123492a3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_artifacts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.BigInteger(), nullable=False),
        sa.Column('application_id', sa.BigInteger(), nullable=True),
        sa.Column('artifact_type', sa.String(30), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_foreign_key('fk_ai_artifacts_job_id', 'ai_artifacts', 'jobs', ['job_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_ai_artifacts_application_id', 'ai_artifacts', 'applications', ['application_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_ai_artifacts_job_id', 'ai_artifacts', ['job_id'])
    op.create_index('ix_ai_artifacts_application_id', 'ai_artifacts', ['application_id'])
    op.create_index('ix_ai_artifacts_job_type', 'ai_artifacts', ['job_id', 'artifact_type'])


def downgrade() -> None:
    op.drop_index('ix_ai_artifacts_job_type', 'ai_artifacts')
    op.drop_index('ix_ai_artifacts_application_id', 'ai_artifacts')
    op.drop_index('ix_ai_artifacts_job_id', 'ai_artifacts')
    op.drop_constraint('fk_ai_artifacts_application_id', 'ai_artifacts', type_='foreignkey')
    op.drop_constraint('fk_ai_artifacts_job_id', 'ai_artifacts', type_='foreignkey')
    op.drop_table('ai_artifacts')
