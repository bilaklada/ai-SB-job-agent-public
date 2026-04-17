"""refactor_log_ats_match_and_add_llm_tables

Revision ID: b7a7d6bfc4ad
Revises: bf4d56e0cdc5
Create Date: 2025-12-30 13:55:05.888046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7a7d6bfc4ad'
down_revision: Union[str, None] = 'bf4d56e0cdc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Refactor log_ats_match table and add LLM reference tables.

    Changes:
    1. Drop old log_ats_match table
    2. Create llm_providers table
    3. Create llm_models table
    4. Create new simplified log_ats_match table
    """

    # Step 1: Drop old log_ats_match table if it exists (includes all indexes and constraints)
    op.execute('DROP TABLE IF EXISTS log_ats_match CASCADE')

    # Step 2: Create llm_providers table
    op.create_table(
        'llm_providers',
        sa.Column('llm_provider_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('llm_provider_name', sa.String(length=50), nullable=False, comment='LLM provider name: \'gemini\', \'openai\', \'anthropic\''),
        sa.PrimaryKeyConstraint('llm_provider_id'),
        sa.UniqueConstraint('llm_provider_name')
    )
    op.create_index('ix_llm_providers_llm_provider_name', 'llm_providers', ['llm_provider_name'])

    # Step 3: Create llm_models table
    op.create_table(
        'llm_models',
        sa.Column('llm_model_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('llm_model_name', sa.String(length=100), nullable=False, comment='LLM model name'),
        sa.Column('llm_provider_id', sa.BigInteger(), nullable=False, comment='Foreign key to llm_providers'),
        sa.Column('llm_provider_name', sa.String(length=50), nullable=False, comment='Provider name (denormalized for performance)'),
        sa.PrimaryKeyConstraint('llm_model_id'),
        sa.ForeignKeyConstraint(['llm_provider_id'], ['llm_providers.llm_provider_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('llm_model_name')
    )
    op.create_index('ix_llm_models_llm_model_name', 'llm_models', ['llm_model_name'])
    op.create_index('ix_llm_models_llm_provider_id', 'llm_models', ['llm_provider_id'])
    op.create_index('ix_llm_models_llm_provider_name', 'llm_models', ['llm_provider_name'])

    # Step 4: Create new simplified log_ats_match table
    op.create_table(
        'log_ats_match',
        # Primary key
        sa.Column('lam_id', sa.BigInteger(), autoincrement=True, nullable=False),

        # Foreign key to applications (mandatory)
        sa.Column('application_id', sa.BigInteger(), nullable=False, comment='Application being processed'),

        # HTML snapshot (mandatory) - input passed to LLM
        sa.Column('html_snapshot', sa.Text(), nullable=False, comment='HTML content passed to LLM for ATS identification'),

        # LLM provider name (mandatory)
        sa.Column('llm_provider_name', sa.String(length=50), nullable=False, comment='LLM provider name: \'gemini\', \'openai\', \'anthropic\''),

        # Extracted ATS name from LLM (mandatory)
        sa.Column('extracted_ats_name', sa.String(length=100), nullable=False, comment='ATS name extracted by LLM'),

        # Best match ATS name from database (mandatory)
        sa.Column('best_match_ats_name', sa.String(length=100), nullable=False, comment='ATS name matched in atss table'),

        # Match status (mandatory) - only 'ats_match' or 'ats_missing'
        sa.Column('ats_match_status', sa.String(length=20), nullable=False, comment='Match status: \'ats_match\' or \'ats_missing\''),

        # Timestamp (mandatory)
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'), comment='When this log entry was created/updated'),

        # Constraints
        sa.PrimaryKeyConstraint('lam_id'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.application_id'], ondelete='CASCADE'),
        sa.CheckConstraint("ats_match_status IN ('ats_match', 'ats_missing')", name='check_ats_match_status_valid')
    )

    # Create indexes for log_ats_match
    op.create_index('ix_log_ats_match_application_id', 'log_ats_match', ['application_id'])
    op.create_index('ix_log_ats_match_llm_provider_name', 'log_ats_match', ['llm_provider_name'])
    op.create_index('ix_log_ats_match_ats_match_status', 'log_ats_match', ['ats_match_status'])
    op.create_index('ix_log_ats_match_updated_at', 'log_ats_match', ['updated_at'])
    op.create_index('ix_log_ats_match_provider_status', 'log_ats_match', ['llm_provider_name', 'ats_match_status'])


def downgrade() -> None:
    """
    Reverse the refactoring: restore old log_ats_match schema and drop LLM tables.

    WARNING: This will lose data in log_ats_match, llm_providers, and llm_models tables!
    """

    # Drop new log_ats_match table
    op.drop_table('log_ats_match')

    # Drop LLM tables
    op.drop_table('llm_models')
    op.drop_table('llm_providers')

    # Recreate old log_ats_match table (from bf4d56e0cdc5 migration)
    op.create_table(
        'log_ats_match',
        sa.Column('lam_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('application_id', sa.BigInteger(), nullable=False),
        sa.Column('llm_provider', sa.String(length=20), nullable=False),
        sa.Column('llm_model', sa.String(length=50), nullable=False),
        sa.Column('extracted_ats_id', sa.BigInteger(), nullable=True),
        sa.Column('extracted_ats_name', sa.String(length=50), nullable=True),
        sa.Column('best_match_ats_id', sa.BigInteger(), nullable=True),
        sa.Column('best_match_ats_name', sa.String(length=50), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('final_status', sa.String(length=30), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 8), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('lam_id'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.application_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['best_match_ats_id'], ['atss.ats_id'], ondelete='SET NULL')
    )

    # Recreate old indexes
    op.create_index('ix_log_ats_match_application_id', 'log_ats_match', ['application_id'])
    op.create_index('ix_log_ats_match_llm_provider', 'log_ats_match', ['llm_provider'])
    op.create_index('ix_log_ats_match_llm_model', 'log_ats_match', ['llm_model'])
    op.create_index('ix_log_ats_match_final_status', 'log_ats_match', ['final_status'])
    op.create_index('ix_log_ats_match_created_at', 'log_ats_match', ['created_at'])
    op.create_index('ix_log_ats_match_provider_model_status', 'log_ats_match', ['llm_provider', 'llm_model', 'final_status'])
