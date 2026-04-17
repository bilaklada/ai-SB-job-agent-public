"""create_log_ats_match_table

Revision ID: bf4d56e0cdc5
Revises: 58c4b60f4263
Create Date: 2025-12-27 11:12:02.900073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'bf4d56e0cdc5'
down_revision: Union[str, None] = '58c4b60f4263'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create log_ats_match table for tracking ATS matching LLM calls."""
    op.create_table(
        'log_ats_match',
        # Primary key
        sa.Column('lam_id', sa.BigInteger(), autoincrement=True, nullable=False),

        # Foreign keys
        sa.Column('application_id', sa.BigInteger(), nullable=False),

        # LLM Provider Information
        sa.Column('llm_provider', sa.String(length=20), nullable=False,
                  comment="LLM provider: 'gemini', 'openai', 'anthropic'"),
        sa.Column('llm_model', sa.String(length=50), nullable=False,
                  comment="Model name: e.g., 'gpt-4o-mini', 'claude-3-5-sonnet-20241022'"),

        # LLM Response Details (track both what LLM said vs what we matched)
        sa.Column('extracted_ats_id', sa.BigInteger(), nullable=True,
                  comment="What LLM initially identified (may not exist in atss table)"),
        sa.Column('extracted_ats_name', sa.String(length=50), nullable=True,
                  comment="Raw ATS name from LLM response"),
        sa.Column('best_match_ats_id', sa.BigInteger(), nullable=True,
                  comment="Matched ats_id from atss table"),
        sa.Column('best_match_ats_name', sa.String(length=50), nullable=True,
                  comment="Matched ATS name from atss table"),

        # Match Quality Metrics
        sa.Column('confidence', sa.String(length=20), nullable=True,
                  comment="Confidence level: 'high', 'medium', 'low'"),
        sa.Column('reasoning', sa.Text(), nullable=True,
                  comment="LLM's explanation for the match"),
        sa.Column('final_status', sa.String(length=30), nullable=False,
                  comment="Final status: 'ats_match' or 'ats_missing'"),

        # Performance & Cost Tracking
        sa.Column('prompt_tokens', sa.Integer(), nullable=True,
                  comment="Number of input tokens"),
        sa.Column('completion_tokens', sa.Integer(), nullable=True,
                  comment="Number of output/completion tokens"),
        sa.Column('total_tokens', sa.Integer(), nullable=True,
                  comment="Total tokens (prompt + completion)"),
        sa.Column('latency_ms', sa.Integer(), nullable=True,
                  comment="LLM call latency in milliseconds"),
        sa.Column('cost_usd', postgresql.NUMERIC(precision=10, scale=8), nullable=True,
                  comment="Actual cost in USD from API response"),

        # Error Handling
        sa.Column('error_message', sa.Text(), nullable=True,
                  comment="Error message if LLM call failed"),

        # Timestamp
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),

        # Constraints
        sa.PrimaryKeyConstraint('lam_id'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.application_id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['best_match_ats_id'], ['atss.ats_id'],
                                ondelete='SET NULL'),
    )

    # Indexes for analytics and filtering
    op.create_index('ix_log_ats_match_application_id', 'log_ats_match', ['application_id'])
    op.create_index('ix_log_ats_match_llm_provider', 'log_ats_match', ['llm_provider'])
    op.create_index('ix_log_ats_match_llm_model', 'log_ats_match', ['llm_model'])
    op.create_index('ix_log_ats_match_final_status', 'log_ats_match', ['final_status'])
    op.create_index('ix_log_ats_match_created_at', 'log_ats_match', ['created_at'])

    # Composite index for common query pattern: compare providers/models by status
    op.create_index(
        'ix_log_ats_match_provider_model_status',
        'log_ats_match',
        ['llm_provider', 'llm_model', 'final_status']
    )


def downgrade() -> None:
    """Drop log_ats_match table."""
    op.drop_index('ix_log_ats_match_provider_model_status', table_name='log_ats_match')
    op.drop_index('ix_log_ats_match_created_at', table_name='log_ats_match')
    op.drop_index('ix_log_ats_match_final_status', table_name='log_ats_match')
    op.drop_index('ix_log_ats_match_llm_model', table_name='log_ats_match')
    op.drop_index('ix_log_ats_match_llm_provider', table_name='log_ats_match')
    op.drop_index('ix_log_ats_match_application_id', table_name='log_ats_match')
    op.drop_table('log_ats_match')
