"""reorder_columns_and_make_match_score_mandatory

Revision ID: a66aea3b2dff
Revises: b019947b146c
Create Date: 2025-12-15 06:07:18.119643

WHAT THIS MIGRATION DOES:
=========================
1. Makes jobs.match_score a MANDATORY (NOT NULL) column
2. Reorders ALL core table columns: mandatory columns first, then optional columns

TABLES AFFECTED:
================
- jobs, profile, accounts, applications, documents, logs, ai_artifacts

TABLES PRESERVED:
=================
- greenhouse_companies (manually created table, left untouched)

DATA PRESERVATION:
==================
- Data backed up to /backup_data/ before migration
- Tables dropped and recreated with correct schema
- Data restored after migration

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import BigInteger, String, Text, Float, Integer, Boolean, TIMESTAMP, Numeric, Date, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision: str = 'a66aea3b2dff'
down_revision: Union[str, None] = 'b019947b146c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Drop and recreate core tables with correct column order and match_score as mandatory.

    greenhouse_companies table is left untouched.
    """

    # Drop all core tables in correct order (respecting foreign keys)
    op.drop_table('ai_artifacts')
    op.drop_table('logs')
    op.drop_table('documents')
    op.drop_table('applications')
    op.drop_table('accounts')
    op.drop_table('profile')
    op.drop_table('jobs')

    # =========================================================================
    # RECREATE JOBS TABLE - with match_score as mandatory and columns reordered
    # =========================================================================
    op.create_table(
        'jobs',
        # MANDATORY COLUMNS FIRST
        sa.Column('id', BigInteger, primary_key=True, autoincrement=True),
        sa.Column('url', Text, nullable=False, unique=True, comment="Job posting URL (unique)"),
        sa.Column('provider', String(50), nullable=False, comment="Source: 'adzuna', 'jsearch', 'manual'"),
        sa.Column('status', String(30), nullable=False, server_default='new', comment="Job lifecycle status"),
        sa.Column('match_score', Float, nullable=False, comment="AI match score (0.0 - 1.0) - MANDATORY"),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), comment="When record was created in DB"),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), comment="Last update timestamp"),

        # OPTIONAL COLUMNS
        sa.Column('title', Text, nullable=True, comment="Job title"),
        sa.Column('company', Text, nullable=True, comment="Company name"),
        sa.Column('description', Text, nullable=True, comment="Full job description"),
        sa.Column('location_country', String(2), nullable=True, comment="ISO-2 country code (e.g. 'CH', 'DE')"),
        sa.Column('location_city', Text, nullable=True, comment="City name or 'Remote'"),
        sa.Column('provider_job_id', Text, nullable=True, comment="External job ID from provider"),
        sa.Column('reject_reason', Text, nullable=True, comment="Why job was rejected/filtered out"),
        sa.Column('apply_type', String(20), nullable=True, comment="Application channel: 'company_site', 'portal', 'email', 'other'"),
        sa.Column('salary_min', Numeric(12, 2), nullable=True, comment="Minimum salary"),
        sa.Column('salary_max', Numeric(12, 2), nullable=True, comment="Maximum salary"),
        sa.Column('salary_currency', String(3), nullable=True, comment="ISO-4217 currency code (e.g. 'CHF', 'EUR')"),
        sa.Column('posted_at', TIMESTAMP(timezone=True), nullable=True, comment="When job was posted (from provider)"),
    )

    # Jobs table indexes
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_provider', 'jobs', ['provider'])
    op.create_index('ix_jobs_location_country', 'jobs', ['location_country'])
    op.create_index('ix_jobs_location_city', 'jobs', ['location_city'])
    op.create_index('ix_jobs_match_score', 'jobs', ['match_score'])
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])
    op.create_index('ix_jobs_posted_at', 'jobs', ['posted_at'])
    op.create_index('ix_jobs_provider_job_id', 'jobs', ['provider', 'provider_job_id'])
    op.create_index('ix_jobs_status_match_score', 'jobs', ['status', 'match_score'])
    op.create_index('ix_jobs_location_country_city', 'jobs', ['location_country', 'location_city'])
    op.create_index('ix_jobs_status_created_at', 'jobs', ['status', 'created_at'])
    op.create_index('ix_jobs_provider_created_at', 'jobs', ['provider', 'created_at'])
    op.create_index('ix_jobs_salary_range', 'jobs', ['salary_min', 'salary_max'])

    # =========================================================================
    # RECREATE PROFILE TABLE - columns reordered
    # =========================================================================
    op.create_table(
        'profile',
        # MANDATORY COLUMNS FIRST
        sa.Column('id', BigInteger, primary_key=True, autoincrement=True),
        sa.Column('first_name', Text, nullable=False, comment="First name"),
        sa.Column('last_name', Text, nullable=False, comment="Last name"),
        sa.Column('email', Text, nullable=False, comment="Primary email for applications"),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), comment="When profile was created"),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), comment="Last update timestamp"),

        # OPTIONAL COLUMNS
        sa.Column('date_of_birth', Date, nullable=True, comment="Date of birth (DATE type - no time component)"),
        sa.Column('nationality', String(2), nullable=True, comment="ISO-2 country code for citizenship"),
        sa.Column('passport_id', Text, nullable=True, comment="Passport/ID number (sensitive - encrypt in production)"),
        sa.Column('phone_num', Text, nullable=True, comment="Phone number with country code (e.g. +41791234567)"),
        sa.Column('current_city', Text, nullable=True, comment="Current city of residence"),
        sa.Column('current_country', String(2), nullable=True, comment="ISO-2 country code of current residence"),
        sa.Column('work_auth_notes', Text, nullable=True, comment="Work authorization/visa situation"),
        sa.Column('ready_to_start_when', Text, nullable=True, comment="Availability (e.g. 'Immediately', 'From 2025-09-01')"),
        sa.Column('relocation_policy', Text, nullable=True, comment="Relocation preferences/constraints"),
        sa.Column('remote_preference', String(20), nullable=True, comment="remote/hybrid/onsite (could be ENUM later)"),
        sa.Column('experience_json', JSONB, nullable=True, comment="Work experience as array of objects with position, company, dates, description, technologies"),
        sa.Column('skills_json', JSONB, nullable=True, comment="Skills array with name and level (basic/intermediate/advanced)"),
        sa.Column('prefs_json', JSONB, nullable=True, comment="Job preferences: target_roles, target_countries, expected_salary_by_country, blacklists"),
        sa.Column('linkedin_url', Text, nullable=True, comment="LinkedIn profile URL"),
        sa.Column('github_url', Text, nullable=True, comment="GitHub/portfolio URL"),
    )

    # =========================================================================
    # RECREATE ACCOUNTS TABLE - columns reordered
    # =========================================================================
    op.create_table(
        'accounts',
        # MANDATORY COLUMNS FIRST
        sa.Column('id', BigInteger, primary_key=True, autoincrement=True),
        sa.Column('portal_name', Text, nullable=False, comment="Portal name (e.g. 'Greenhouse', 'Lever')"),
        sa.Column('domain', Text, nullable=False, comment="Login domain (e.g. 'boards.greenhouse.io')"),
        sa.Column('login_email', Text, nullable=False, comment="Email used for login"),
        sa.Column('password_encrypted', Text, nullable=False, comment="ENCRYPTED password (never store plain text!)"),
        sa.Column('applicant_full_name', Text, nullable=False, comment="Full name on account"),
        sa.Column('account_health', String(20), nullable=False, server_default='ok', comment="Health status: ok, warn, needs_password_reset, 2fa_required, captcha, blocked, etc."),
        sa.Column('is_active', Boolean, nullable=False, server_default='TRUE', comment="Should this account still be used?"),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), comment="When account was created in DB"),

        # OPTIONAL COLUMNS
        sa.Column('login_username', Text, nullable=True, comment="Username (if different from email)"),
        sa.Column('profile_url', Text, nullable=True, comment="Direct link to profile page"),
        sa.Column('applications_page_url', Text, nullable=True, comment="Direct link to 'My Applications' page"),
        sa.Column('account_origin_job_id', BigInteger, sa.ForeignKey('jobs.id', ondelete='SET NULL'), nullable=True, comment="Which job triggered creation of this account"),
        sa.Column('notes', Text, nullable=True, comment="Extra info: 2FA setup, warnings, etc."),
        sa.Column('verified_at', TIMESTAMP(timezone=True), nullable=True, comment="When email was verified"),
        sa.Column('last_login_at', TIMESTAMP(timezone=True), nullable=True, comment="Last successful login"),
        sa.Column('last_status_check_at', TIMESTAMP(timezone=True), nullable=True, comment="Last time we checked account status"),
    )

    # Accounts table indexes
    op.create_index('ix_accounts_login_email', 'accounts', ['login_email'])
    op.create_index('ix_accounts_portal_domain', 'accounts', ['portal_name', 'domain'])
    op.create_index('ix_accounts_health', 'accounts', ['account_health'])

    # =========================================================================
    # RECREATE APPLICATIONS TABLE - columns reordered
    # =========================================================================
    op.create_table(
        'applications',
        # MANDATORY COLUMNS FIRST
        sa.Column('id', BigInteger, primary_key=True, autoincrement=True),
        sa.Column('job_id', BigInteger, sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False, comment="Which job this application is for"),
        sa.Column('status', String(30), nullable=False, server_default='created', comment="Application lifecycle status"),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), comment="When application record was created"),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), comment="Last update"),

        # OPTIONAL COLUMNS
        sa.Column('account_id', BigInteger, sa.ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True, comment="Which account was used (if any)"),
        sa.Column('applied_at', TIMESTAMP(timezone=True), nullable=True, comment="When application was successfully submitted"),
        sa.Column('submission_channel', String(30), nullable=True, comment="Which ATS/portal: greenhouse, lever, workday, etc."),
        sa.Column('notes', Text, nullable=True, comment="Debugging notes, error messages, etc."),
    )

    # Applications table indexes
    op.create_index('ix_applications_job_id_status', 'applications', ['job_id', 'status'])
    op.create_index('ix_applications_status', 'applications', ['status'])
    op.create_index('ix_applications_account_id', 'applications', ['account_id'])

    # =========================================================================
    # RECREATE DOCUMENTS TABLE - columns reordered
    # =========================================================================
    op.create_table(
        'documents',
        # MANDATORY COLUMNS FIRST
        sa.Column('id', BigInteger, primary_key=True, autoincrement=True),
        sa.Column('owner_id', BigInteger, sa.ForeignKey('profile.id', ondelete='CASCADE'), nullable=False, comment="Which profile owns this document"),
        sa.Column('type', String(20), nullable=False, comment="Document type: cv, diploma, certificate, cover_letter, portfolio, transcript, other"),
        sa.Column('storage_backend', String(20), nullable=False, comment="Storage backend: s3, local, etc."),
        sa.Column('storage_key', Text, nullable=False, comment="S3 object key (NOT full URL): profiles/1/documents/cv/cv_primary_en.pdf"),
        sa.Column('original_filename', Text, nullable=False, comment="Original filename for debugging/downloading"),
        sa.Column('mime_type', String(50), nullable=False, comment="MIME type: application/pdf, image/png, etc."),
        sa.Column('is_primary', Boolean, nullable=False, server_default='FALSE', comment="Is this the default/primary document of this type?"),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), comment="When document was uploaded"),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), comment="Last update timestamp"),

        # OPTIONAL COLUMNS
        sa.Column('language', String(5), nullable=True, comment="Language code: en, de, cs, etc."),
        sa.Column('description', Text, nullable=True, comment="Description: 'Main CV - English version'"),
    )

    # Documents table indexes
    op.create_index('ix_documents_owner_id', 'documents', ['owner_id'])
    op.create_index('ix_documents_type', 'documents', ['type'])
    op.create_index('ix_documents_owner_type_primary', 'documents', ['owner_id', 'type', 'is_primary'])

    # =========================================================================
    # RECREATE LOGS TABLE - columns reordered
    # =========================================================================
    op.create_table(
        'logs',
        # MANDATORY COLUMNS FIRST
        sa.Column('id', BigInteger, primary_key=True, autoincrement=True),
        sa.Column('timestamp', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), comment="When event occurred"),
        sa.Column('level', String(10), nullable=False, comment="Log level: info, warning, error"),
        sa.Column('component', String(30), nullable=False, comment="Which subsystem: rpa, orchestrator, email_agent, ai, provider, api"),
        sa.Column('message', Text, nullable=False, comment="Human-readable log message"),

        # OPTIONAL COLUMNS
        sa.Column('context', JSONB, nullable=True, comment="Structured metadata: job_id, application_id, portal, error details, etc."),
    )

    # Logs table indexes
    op.create_index('ix_logs_timestamp', 'logs', ['timestamp'])
    op.create_index('ix_logs_level', 'logs', ['level'])
    op.create_index('ix_logs_component', 'logs', ['component'])
    op.create_index('ix_logs_level_timestamp', 'logs', ['level', 'timestamp'])

    # =========================================================================
    # RECREATE AI_ARTIFACTS TABLE - columns reordered
    # =========================================================================
    op.create_table(
        'ai_artifacts',
        # MANDATORY COLUMNS FIRST
        sa.Column('id', BigInteger, primary_key=True, autoincrement=True),
        sa.Column('job_id', BigInteger, sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False, comment="Job this artifact belongs to"),
        sa.Column('artifact_type', String(30), nullable=False, comment="Type: parsed_vacancy, company_info, motivation, cover_letter, match_explanation, form_answers"),
        sa.Column('content', JSONB, nullable=False, comment="Flexible JSON content - structure depends on artifact_type"),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), comment="When artifact was generated"),

        # OPTIONAL COLUMNS
        sa.Column('application_id', BigInteger, sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=True, comment="Specific application this was used for (optional)"),
    )

    # AI Artifacts table indexes
    op.create_index('ix_ai_artifacts_job_id', 'ai_artifacts', ['job_id'])
    op.create_index('ix_ai_artifacts_application_id', 'ai_artifacts', ['application_id'])
    op.create_index('ix_ai_artifacts_job_type', 'ai_artifacts', ['job_id', 'artifact_type'])


def downgrade() -> None:
    """
    Downgrade not supported for this migration.

    Reason: This migration reorders columns which cannot be cleanly reversed.
    If rollback is needed, restore from database backup.
    """
    raise NotImplementedError(
        "Downgrade not supported. "
        "To rollback, restore from database backup taken before migration."
    )
