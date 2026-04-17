"""
models.py - Database ORM Models

================================================================================
WHAT THIS FILE DOES:
================================================================================
This file defines the structure of your database tables using SQLAlchemy ORM.
Each class here represents a table in the database.

Think of it like creating a blueprint:
- Class = Table
- Class attributes (Column) = Table columns
- Instance of class = A row in the table

================================================================================
HOW ORM WORKS (Object-Relational Mapping):
================================================================================
Instead of writing SQL like this:
    CREATE TABLE jobs (
        id INTEGER PRIMARY KEY,
        title VARCHAR(500) NOT NULL,
        ...
    );
    INSERT INTO jobs (title, company) VALUES ('Engineer', 'Acme');

You write Python like this:
    class Job(Base):
        id = Column(Integer, primary_key=True)
        title = Column(String(500), nullable=False)

    job = Job(title='Engineer', company='Acme')
    db.add(job)
    db.commit()

SQLAlchemy automatically translates your Python code into SQL!

================================================================================
HOW THIS CONNECTS TO THE REST OF THE PROJECT:
================================================================================

1. THIS FILE (models.py) → Defines table structure
   ↓
2. app/db/session.py → Base class and engine
   ↓
3. app/main.py → Base.metadata.create_all(engine) creates tables
   ↓
4. app/schemas/job.py → Pydantic schemas for API validation
   ↓
5. app/api/routes_jobs.py → Routes use both models and schemas

================================================================================
COLUMNS & DATA TYPES:
================================================================================
Common column types:
- Integer, BigInteger → Whole numbers
- String(length) → Text with max length
- Text → Unlimited text
- Float → Decimal numbers
- Boolean → True/False
- DateTime → Date and time
- JSON → JSON data (must be dict or list)

Common parameters:
- primary_key=True → This column is the unique identifier
- nullable=False → This column MUST have a value
- default=value → Use this value if none provided
- unique=True → No two rows can have same value
- index=True → Speed up searching on this column

================================================================================
RELATIONSHIPS:
================================================================================
When tables reference each other:
- Foreign Key → Links to another table
  Example: job_id in applications table points to id in jobs table

- relationship() → Allows easy access between tables
  Example: job.applications returns all applications for this job

================================================================================
"""

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    TIMESTAMP,
    ForeignKey,
    Index,
    CheckConstraint,
    Numeric,
    Date,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


# =============================================================================
# JOB MODEL - Represents the "jobs" table
# =============================================================================

class Job(Base):
    """
    Job model - represents a single job posting.

    PURPOSE:
    --------
    This is the CORE table of the entire system. Each row = one job opportunity.
    Jobs can come from:
    - Adzuna API (provider='adzuna')
    - JSearch API (provider='jsearch')
    - Manual bulk entry via /admin/db/jobs/bulk-create-urls endpoint (provider='manual')

    LIFECYCLE:
    ----------
    1. Job is created with status='new' or 'new_mandatory'
    2. Filters and AI check the job → status changes to 'approved_for_application' or 'rejected_low_match'
    3. RPA agent applies → status becomes 'application_in_progress' then 'applied' or 'application_failed'

    RELATIONSHIPS:
    --------------
    - One Job can have many Applications (job.applications)
    - One Job can have many AI Artifacts (job.ai_artifacts) - parsed vacancy, motivations, etc.

    HOW TO USE:
    -----------
    Create a new job:
        job = Job(
            title="Python Developer",
            company="Acme Corp",
            url="https://...",
            provider="manual",
            status="new_mandatory"
        )
        db.add(job)
        db.commit()

    Query jobs:
        # Get all new jobs
        new_jobs = db.query(Job).filter(Job.status == 'new').all()

        # Get remote jobs in Switzerland
        remote_ch = db.query(Job).filter(
            Job.location_country == 'CH',
            Job.location_city == 'Remote'
        ).all()
    """

    __tablename__ = "jobs"

    # Primary Key
    job_id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Job ID (PK)")

    # Basic job information
    url = Column(Text, nullable=False, unique=True, comment="Job posting URL (unique)")
    provider = Column(String(50), nullable=False, comment="Source: 'adzuna', 'jsearch', 'manual'")
    status = Column(String(30), nullable=False, comment="Job lifecycle status")
    match_score = Column(Float, nullable=False, comment="AI match score (0.0 - 1.0)")

    # Foreign Keys
    profile_id = Column(
        BigInteger,
        ForeignKey("profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
        comment="Which candidate profile this job is for"
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When record was created in DB"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp"
    )

    # Relationships
    profile = relationship("Profile", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    ai_artifacts = relationship("AIArtifact", back_populates="job", cascade="all, delete-orphan")

    # Indexes for performance (matching database structure)
    __table_args__ = (
        Index('ix_jobs_status', 'status'),
        Index('ix_jobs_provider', 'provider'),
        Index('ix_jobs_match_score', 'match_score'),
        Index('ix_jobs_created_at', 'created_at'),
        Index('ix_jobs_profile_id', 'profile_id'),
        Index('ix_jobs_status_match_score', 'status', 'match_score'),
        Index('ix_jobs_status_created_at', 'status', 'created_at'),
        Index('ix_jobs_provider_created_at', 'provider', 'created_at'),
        Index('ix_jobs_profile_status', 'profile_id', 'status'),
    )


"""
================================================================================
JOB STATUS VALUES AND THEIR MEANINGS
================================================================================

new                        - Job fetched from provider, not yet filtered/matched
new_mandatory              - Manually added job (MUST be applied, highest priority)
filtered_out               - Failed rule-based filters (country, blacklist, etc.)
rejected_low_match         - AI match score too low
low_priority              - Acceptable but second-choice job
approved_for_application  - Passed all filters, ready to apply
cannot_apply_automatically - Cannot be automated (LinkedIn, unsupported portal)
application_in_progress   - Agent is currently working on this
requires_manual_check     - Agent needs human help
application_failed        - All application attempts failed
applied                   - Successfully applied

PRIORITY ORDER FOR APPLICATION:
1. new_mandatory (oldest first)
2. approved_for_application (oldest first)
3. low_priority (when higher queues empty)
"""


# =============================================================================
# APPLICATION MODEL - Represents the "applications" table
# =============================================================================

class Application(Base):
    """
    Application model - represents a single application attempt for a job.

    PURPOSE:
    --------
    Tracks each attempt to apply for a job. Links together:
    - Which job (job_id)
    - Which candidate profile (profile_id)
    - Which ATS platform (ats_id, ats_name)
    - Which company (company_id, company_name)
    - Which account was used (account_id)
    - Which automation workflow (workflow_id)

    REFACTORED:
    -----------
    Simplified schema focused on relationships and status tracking.
    Removed deprecated fields (applied_at, submission_channel, notes).
    Added denormalized name fields (ats_name, company_name) for performance.

    LIFECYCLE:
    ----------
    1. Created with status='created' when orchestrator decides to apply
    2. Status → 'in_progress' when RPA agent starts working
    3. Status → 'pending_email' if waiting for verification email
    4. Status → 'submitted' if successful, or 'failed'/'error' if not

    RELATIONSHIPS:
    --------------
    - Belongs to one Job (application.job)
    - Belongs to one Profile (application.profile) - which candidate is applying
    - May link to ATS (application.ats) - which ATS platform
    - May link to Company (application.company) - which company
    - May use one Account (application.account) - which portal account was used
    - May use one Workflow (application.workflow) - which automation workflow
    - May have AI Artifacts (application.ai_artifacts) - cover letters, motivations

    HOW TO USE:
    -----------
    Create application:
        app = Application(
            job_id=42,
            profile_id=1,
            status='created',
            ats_id=5,
            ats_name='greenhouse',
            company_id=10,
            company_name='TechCorp'
        )
        db.add(app)
        db.commit()

    Update status:
        app.status = 'submitted'
        db.commit()

    Query:
        # Get all failed applications
        failed = db.query(Application).filter(Application.status == 'failed').all()

        # Get applications for a specific job
        job_apps = db.query(Application).filter(Application.job_id == 42).all()

        # Get applications by ATS
        gh_apps = db.query(Application).filter(Application.ats_name == 'greenhouse').all()
    """

    __tablename__ = "applications"

    # Primary Key
    application_id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Application ID (PK)")

    # Foreign Keys (required)
    job_id = Column(
        BigInteger,
        ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        comment="Which job this application is for"
    )
    profile_id = Column(
        BigInteger,
        ForeignKey("profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
        comment="Which candidate profile is applying"
    )

    # Foreign Keys (optional - ATS/Company/Account/Workflow)
    ats_id = Column(
        BigInteger,
        ForeignKey("atss.ats_id", ondelete="SET NULL"),
        nullable=True,
        comment="Which ATS platform (FK to atss table)"
    )
    company_id = Column(
        BigInteger,
        ForeignKey("companies.company_id", ondelete="SET NULL"),
        nullable=True,
        comment="Which company (FK to companies table)"
    )
    account_id = Column(
        BigInteger,
        ForeignKey("accounts.account_id", ondelete="SET NULL"),
        nullable=True,
        comment="Which account was used (if any)"
    )
    workflow_id = Column(
        BigInteger,
        ForeignKey("workflows.workflow_id", ondelete="SET NULL"),
        nullable=True,
        comment="Which automation workflow was used"
    )

    # Denormalized fields (for performance - avoid joins in common queries)
    ats_name = Column(
        String(50),
        nullable=True,
        comment="ATS platform name (denormalized from atss.ats_name)"
    )
    company_name = Column(
        String(50),
        nullable=True,
        comment="Company name (denormalized from companies.company_name)"
    )

    # Application status
    status = Column(
        String(30),
        nullable=False,
        default='created',
        comment="Application lifecycle status"
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When application record was created"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update"
    )

    # Relationships
    job = relationship("Job", back_populates="applications")
    profile = relationship("Profile", back_populates="applications")
    ats = relationship("ATS", back_populates="applications")
    company = relationship("Company", back_populates="applications")
    account = relationship("Account", back_populates="applications")
    workflow = relationship("Workflow", back_populates="applications")
    ai_artifacts = relationship("AIArtifact", back_populates="application", cascade="all, delete-orphan")
    ats_match_logs = relationship("LogATSMatch", back_populates="application", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('ix_applications_job_id', 'job_id'),
        Index('ix_applications_profile_id', 'profile_id'),
        Index('ix_applications_status', 'status'),
        Index('ix_applications_ats_id', 'ats_id'),
        Index('ix_applications_company_id', 'company_id'),
        Index('ix_applications_account_id', 'account_id'),
        Index('ix_applications_workflow_id', 'workflow_id'),
        Index('ix_applications_job_status', 'job_id', 'status'),
    )


"""
================================================================================
APPLICATION STATUS VALUES AND THEIR MEANINGS
================================================================================

created               - Application record created, agent hasn't started yet
in_progress          - Agent is currently working on this
pending_email        - Waiting for email verification/confirmation
submitted            - Successfully submitted on portal
error                - Technical error occurred (may retry)
failed               - All retries exhausted, permanent failure
requires_manual_check - Needs human intervention

SUBMISSION CHANNELS:
greenhouse, lever, workday, successfactors, ashby, personio, bamboohr,
smartrecruiters, manual_url, unknown
"""


# =============================================================================
# ACCOUNT MODEL - Represents the "accounts" table
# =============================================================================

class Account(Base):
    """
    Account model - represents a login account created on a company's application portal.

    PURPOSE:
    --------
    Simplified account tracking for company-specific job application portals.
    Stores minimal credentials needed for the agent to log in and submit applications.

    REFACTORED:
    -----------
    This model has been simplified to focus on essential login information only.
    Removed unused fields and normalized column names for clarity.

    SECURITY:
    ---------
    login_password should contain encrypted password, NOT plain text!
    In production, use proper encryption (Fernet, AWS Secrets Manager, etc.)

    HOW TO USE:
    -----------
    Create account:
        account = Account(
            company_name="Acme Corp",
            login_url="https://jobs.acmecorp.com/login",
            login_email="alex@example.com",
            login_password=encrypt_password("secure123")
        )
        db.add(account)
        db.commit()

    Query:
        # Find account for specific company
        account = db.query(Account).filter(
            Account.company_name == "Acme Corp"
        ).first()

        # Get account by email
        account = db.query(Account).filter(
            Account.login_email == "alex@example.com"
        ).first()
    """

    __tablename__ = "accounts"

    # Primary Key
    account_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Company information
    company_name = Column(
        Text,
        nullable=False,
        comment="Company name (e.g., 'Acme Corp', 'Greenhouse Inc')"
    )

    # Login credentials
    login_url = Column(
        Text,
        nullable=False,
        comment="Full login URL (e.g., 'https://jobs.company.com/login')"
    )
    login_email = Column(
        Text,
        nullable=False,
        comment="Email used for login"
    )
    login_password = Column(
        Text,
        nullable=False,
        comment="ENCRYPTED password (never store plain text!)"
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When account was created in DB"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last time account was updated"
    )

    # Relationships
    applications = relationship("Application", back_populates="account")

    # Indexes
    __table_args__ = (
        Index('ix_accounts_login_email', 'login_email'),
        Index('ix_accounts_company_name', 'company_name'),
    )


# =============================================================================
# PROFILE MODEL - Represents the "profile" table
# =============================================================================

class Profile(Base):
    """
    Profile model - represents a candidate's profile with personal data and structured information.

    PURPOSE:
    --------
    This is the unified profile containing all candidate information needed for job applications:
    - Personal data (name, contact, location)
    - Work experience (structured as JSON)
    - Skills (structured as JSON)
    - Job preferences (structured as JSON)

    The agent uses this data to:
    - Fill form fields (name, email, phone, etc.)
    - Generate motivational answers (using experience and skills)
    - Match jobs (using preferences and target roles)

    JSONB FIELDS:
    -------------
    PostgreSQL JSONB allows flexible structured data without schema changes:

    experience_json - Array of work experience objects:
    [
        {
            "position": "Data Analyst Intern",
            "company": "Hotel XYZ",
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "description": "Analyzed booking data...",
            "technologies": ["SQL", "Excel", "Python"]
        }
    ]

    skills_json - Array of skills with levels:
    [
        {"name": "Python", "level": "basic"},
        {"name": "SQL", "level": "intermediate"},
        {"name": "C#", "level": "basic"}
    ]

    prefs_json - Job preferences and expectations:
    {
        "target_roles": ["Data Analyst", "Junior Developer"],
        "target_countries": ["CH", "DE"],
        "expected_salary_by_country": {
            "CH": [90000, 110000],
            "DE": [50000, 70000]
        },
        "blacklist_job_types": ["sales", "cold calling"],
        "blacklist_countries": ["US"]
    }

    RELATIONSHIPS:
    --------------
    - Has many Documents (profile.documents) - CVs, diplomas, certificates

    HOW TO USE:
    -----------
    Create profile:
        profile = Profile(
            first_name="Alex",
            last_name="Example",
            email="alex@example.com",
            phone_num="+41791234567",
            current_city="Zurich",
            current_country="CH",
            skills_json=[
                {"name": "Python", "level": "basic"},
                {"name": "SQL", "level": "intermediate"}
            ]
        )
        db.add(profile)
        db.commit()

    Query profile:
        profile = db.query(Profile).first()
        print(f"Name: {profile.first_name} {profile.last_name}")
        print(f"Skills: {profile.skills_json}")

    Update JSONB field:
        # Add new skill
        profile.skills_json.append({"name": "JavaScript", "level": "basic"})
        db.commit()

        # Update preferences
        prefs = profile.prefs_json or {}
        prefs["target_countries"] = ["CH", "DE", "AT"]
        profile.prefs_json = prefs
        db.commit()
    """

    __tablename__ = "profiles"

    # Primary Key
    profile_id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Profile ID (PK)")

    # Personal Information
    first_name = Column(Text, nullable=False, comment="First name")
    last_name = Column(Text, nullable=False, comment="Last name")
    date_of_birth = Column(Date, nullable=True, comment="Date of birth (DATE type - no time component)")
    nationality = Column(String(2), nullable=True, comment="ISO-2 country code for citizenship")
    passport_id = Column(Text, nullable=True, comment="Passport/ID number (sensitive - encrypt in production)")

    # Contact Information
    phone_num = Column(Text, nullable=True, comment="Phone number with country code (e.g. +41791234567)")
    email = Column(Text, nullable=False, comment="Primary email for applications")

    # Location
    current_city = Column(Text, nullable=True, comment="Current city of residence")
    current_country = Column(String(2), nullable=True, comment="ISO-2 country code of current residence")

    # Work Authorization & Availability
    work_auth_notes = Column(Text, nullable=True, comment="Work authorization/visa situation")
    ready_to_start_when = Column(Text, nullable=True, comment="Availability (e.g. 'Immediately', 'From 2025-09-01')")
    relocation_policy = Column(Text, nullable=True, comment="Relocation preferences/constraints")
    remote_preference = Column(String(20), nullable=True, comment="remote/hybrid/onsite (could be ENUM later)")

    # Structured Data (JSONB for flexibility)
    experience_json = Column(
        JSONB,
        nullable=True,
        comment="Work experience as array of objects with position, company, dates, description, technologies"
    )
    skills_json = Column(
        JSONB,
        nullable=True,
        comment="Skills array with name and level (basic/intermediate/advanced)"
    )
    prefs_json = Column(
        JSONB,
        nullable=True,
        comment="Job preferences: target_roles, target_countries, expected_salary_by_country, blacklists"
    )

    # Social/Portfolio Links
    linkedin_url = Column(Text, nullable=True, comment="LinkedIn profile URL")
    github_url = Column(Text, nullable=True, comment="GitHub/portfolio URL")

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When profile was created"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp"
    )

    # Relationships
    jobs = relationship("Job", back_populates="profile", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="profile", cascade="all, delete-orphan")


"""
================================================================================
PROFILE USAGE EXAMPLES
================================================================================

EXAMPLE 1: Create a new profile
--------------------------------
from datetime import date

profile = Profile(
    first_name="Alex",
    last_name="Example",
    date_of_birth=date(2005, 3, 15),
    nationality="CZ",
    phone_num="+41791234567",
    email="alex@example.com",
    current_city="Zurich",
    current_country="CH",
    work_auth_notes="Authorized to work in the target market",
    ready_to_start_when="Immediately",
    remote_preference="remote",
    skills_json=[
        {"name": "Python", "level": "basic"},
        {"name": "SQL", "level": "intermediate"},
        {"name": "C#", "level": "basic"}
    ],
    prefs_json={
        "target_roles": ["Data Analyst", "Junior Developer"],
        "target_countries": ["CH", "DE"],
        "expected_salary_by_country": {
            "CH": [90000, 110000],
            "DE": [50000, 70000]
        }
    }
)
db.add(profile)
db.commit()


EXAMPLE 2: Query JSONB fields
------------------------------
# Find profiles with Python skills
profiles = db.query(Profile).filter(
    Profile.skills_json.contains([{"name": "Python"}])
).all()

# Find profiles targeting Switzerland
profiles = db.query(Profile).filter(
    Profile.prefs_json["target_countries"].astext.contains("CH")
).all()


EXAMPLE 3: Update JSONB fields
-------------------------------
profile = db.query(Profile).first()

# Update skills (full replacement)
profile.skills_json = [
    {"name": "Python", "level": "advanced"},  # Updated level
    {"name": "SQL", "level": "advanced"},
    {"name": "JavaScript", "level": "basic"}  # New skill
]

# Update preferences (partial update)
current_prefs = profile.prefs_json or {}
current_prefs["expected_salary_by_country"]["CH"] = [95000, 115000]
profile.prefs_json = current_prefs

db.commit()


EXAMPLE 4: Add work experience
-------------------------------
profile = db.query(Profile).first()

# Get current experience or empty list
experience = profile.experience_json or []

# Add new experience entry
experience.append({
    "position": "Data Analyst Intern",
    "company": "Hotel XYZ",
    "start_date": "2024-01-01",
    "end_date": "2024-06-30",
    "description": "Analyzed booking data, created dashboards",
    "technologies": ["SQL", "Excel", "Python"]
})

profile.experience_json = experience
db.commit()


EXAMPLE 5: Get profile for application form
--------------------------------------------
profile = db.query(Profile).first()

# Use profile data for application
print(f"Name: {profile.first_name} {profile.last_name}")
print(f"Email: {profile.email}")
print(f"Phone: {profile.phone_num}")
print(f"Location: {profile.current_city}, {profile.current_country}")

# Extract skills
if profile.skills_json:
    skills = [skill['name'] for skill in profile.skills_json]
    print(f"Skills: {', '.join(skills)}")

# Extract target salary for specific country
if profile.prefs_json and 'expected_salary_by_country' in profile.prefs_json:
    ch_salary = profile.prefs_json['expected_salary_by_country'].get('CH', [])
    if ch_salary:
        print(f"Expected salary (CH): {ch_salary[0]} - {ch_salary[1]} CHF")
"""


# =============================================================================
# DOCUMENT MODEL - Represents the "documents" table
# =============================================================================

class Document(Base):
    """
    Document model - represents files (CVs, diplomas, certificates) stored in S3.

    PURPOSE:
    --------
    Tracks metadata for documents that the agent needs to upload during applications.
    Actual files are stored in S3 (or S3-compatible storage), NOT in the database.

    STORAGE PATTERN:
    ----------------
    1. File uploaded to S3 bucket: profiles/{profile_id}/documents/{type}/cv_primary_en.pdf
    2. Metadata stored in database: storage_backend='s3', storage_key='profiles/1/documents/cv/cv_primary_en.pdf'
    3. Agent downloads from S3 to temp file when needed for application

    DOCUMENT TYPES:
    ---------------
    - cv: Curriculum Vitae / Resume
    - cover_letter: Cover letter (if generic/reusable)
    - diploma: University diploma
    - certificate: Certifications, courses
    - portfolio: Portfolio PDF
    - transcript: Academic transcripts
    - other: Other documents

    RELATIONSHIPS:
    --------------
    - Belongs to one Profile (document.owner)

    HOW TO USE:
    -----------
    Create document record after S3 upload:
        document = Document(
            owner_id=1,
            type='cv',
            storage_backend='s3',
            storage_key='profiles/1/documents/cv/cv_primary_en.pdf',
            original_filename='cv_primary_en.pdf',
            mime_type='application/pdf',
            language='en',
            description='Main CV - English version',
            is_primary=True
        )
        db.add(document)
        db.commit()

    Find primary CV for a profile:
        cv = db.query(Document).filter(
            Document.owner_id == 1,
            Document.type == 'cv',
            Document.is_primary == True
        ).first()

    Get all documents for profile:
        docs = db.query(Document).filter(Document.owner_id == 1).all()
    """

    __tablename__ = "documents"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key
    owner_id = Column(
        BigInteger,
        ForeignKey("profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
        comment="Which profile owns this document"
    )

    # Document metadata
    type = Column(
        String(20),
        nullable=False,
        comment="Document type: cv, diploma, certificate, cover_letter, portfolio, transcript, other"
    )
    storage_backend = Column(
        String(20),
        nullable=False,
        comment="Storage backend: s3, local, etc."
    )
    storage_key = Column(
        Text,
        nullable=False,
        comment="S3 object key (NOT full URL): profiles/1/documents/cv/cv_primary_en.pdf"
    )
    original_filename = Column(
        Text,
        nullable=False,
        comment="Original filename for debugging/downloading"
    )
    mime_type = Column(
        String(50),
        nullable=False,
        comment="MIME type: application/pdf, image/png, etc."
    )

    # Document details
    language = Column(
        String(5),
        nullable=True,
        comment="Language code: en, de, cs, etc."
    )
    description = Column(
        Text,
        nullable=True,
        comment="Description: 'Main CV - English version'"
    )
    is_primary = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default='FALSE',
        comment="Is this the default/primary document of this type?"
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When document was uploaded"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp"
    )

    # Relationships
    owner = relationship("Profile", back_populates="documents")

    # Indexes
    __table_args__ = (
        Index('ix_documents_owner_id', 'owner_id'),
        Index('ix_documents_type', 'type'),
        Index('ix_documents_owner_type_primary', 'owner_id', 'type', 'is_primary'),
    )


"""
================================================================================
DOCUMENT USAGE EXAMPLES
================================================================================

EXAMPLE 1: Create document record after S3 upload
--------------------------------------------------
# After uploading file to S3 at: profiles/1/documents/cv/cv_primary_en.pdf

document = Document(
    owner_id=1,
    type='cv',
    storage_backend='s3',
    storage_key='profiles/1/documents/cv/cv_primary_en.pdf',
    original_filename='cv_primary_en.pdf',
    mime_type='application/pdf',
    language='en',
    description='Main CV - English version',
    is_primary=True
)
db.add(document)
db.commit()


EXAMPLE 2: Find primary CV for profile
---------------------------------------
primary_cv = db.query(Document).filter(
    Document.owner_id == 1,
    Document.type == 'cv',
    Document.is_primary == True
).first()

if primary_cv:
    print(f"Primary CV: {primary_cv.storage_key}")
    # Download from S3 using storage_key
else:
    print("No primary CV found")


EXAMPLE 3: Get all documents for profile
-----------------------------------------
docs = db.query(Document).filter(Document.owner_id == 1).all()

for doc in docs:
    print(f"{doc.type}: {doc.original_filename} ({doc.language})")


EXAMPLE 4: Find document by language
-------------------------------------
# Find English CV
en_cv = db.query(Document).filter(
    Document.owner_id == 1,
    Document.type == 'cv',
    Document.language == 'en'
).first()


EXAMPLE 5: Set new primary CV
------------------------------
# Unset all primary CVs
db.query(Document).filter(
    Document.owner_id == 1,
    Document.type == 'cv',
    Document.is_primary == True
).update({'is_primary': False})

# Set new primary
new_primary = db.query(Document).filter(Document.id == 42).first()
new_primary.is_primary = True
db.commit()


EXAMPLE 6: Agent downloads document for application
----------------------------------------------------
import boto3
import tempfile

# Get primary CV
cv = db.query(Document).filter(
    Document.owner_id == 1,
    Document.type == 'cv',
    Document.is_primary == True
).first()

# Download from S3 to temporary file
s3 = boto3.client('s3')
temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
s3.download_file('my-bucket', cv.storage_key, temp_file.name)

# Use temp_file.name in Playwright to upload
print(f"Downloaded to: {temp_file.name}")
"""


# =============================================================================
# LOG STATUS CHANGE MODEL - Represents the "log_status_change" table
# =============================================================================

class LogStatusChange(Base):
    """
    LogStatusChange - Tracks all status changes for jobs and applications.

    PURPOSE:
    --------
    Dedicated table for auditing every status transition in the workflow.
    Replaces the old 'logs' and 'state_change_history' tables with a simpler,
    more focused design specifically for tracking job and application statuses.

    DESIGN:
    -------
    - lsc_table: Indicates which table's status we're logging ('jobs' or 'applications')
    - Always linked to profile_id and job_id for complete context
    - application_id is nullable (jobs may not have applications yet)
    - Captures initial_status → final_status transitions
    - Timestamp for when the change occurred

    USE CASES:
    ----------
    - Audit trail: "What happened to job #42?"
    - Analytics: "How many jobs reached 'approved_for_application'?"
    - Debugging: "Why is application stuck at 'ats_missing'?"
    - Workflow monitoring: "Average time from new_url to completed?"

    EXAMPLE USAGE:
    --------------
    # Record a job status change
    log = LogStatusChange(
        lsc_table='jobs',
        profile_id=1,
        job_id=42,
        application_id=None,  # No application yet
        initial_status='new_url',
        final_status='approved_for_application',
        updated_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    # Record an application status change
    log = LogStatusChange(
        lsc_table='applications',
        profile_id=1,
        job_id=42,
        application_id=15,
        initial_status='created',
        final_status='ats_match',
        updated_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    # Query all status changes for a job
    changes = db.query(LogStatusChange).filter(
        LogStatusChange.job_id == 42
    ).order_by(LogStatusChange.updated_at).all()

    # Analytics: Count status transitions
    from sqlalchemy import func
    transitions = db.query(
        LogStatusChange.initial_status,
        LogStatusChange.final_status,
        func.count().label('count')
    ).filter(
        LogStatusChange.lsc_table == 'jobs'
    ).group_by(
        LogStatusChange.initial_status,
        LogStatusChange.final_status
    ).all()
    """

    __tablename__ = "log_status_change"

    # === PRIMARY KEY ===
    lsc_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Auto-increment primary key"
    )

    # === TABLE INDICATOR ===
    lsc_table = Column(
        String(20),
        nullable=False,
        comment="Which table: 'jobs' or 'applications'"
    )

    # === FOREIGN KEYS ===
    profile_id = Column(
        BigInteger,
        ForeignKey('profiles.profile_id', ondelete='CASCADE'),
        nullable=False,
        comment="Profile that owns this job/application"
    )

    job_id = Column(
        BigInteger,
        ForeignKey('jobs.job_id', ondelete='CASCADE'),
        nullable=False,
        comment="Job related to this status change"
    )

    application_id = Column(
        BigInteger,
        ForeignKey('applications.application_id', ondelete='CASCADE'),
        nullable=True,
        comment="Application related to this change (nullable for job-level changes)"
    )

    # === STATUS CHANGE TRACKING ===
    initial_status = Column(
        String(50),
        nullable=False,
        comment="Status before the change"
    )

    final_status = Column(
        String(50),
        nullable=False,
        comment="Status after the change"
    )

    # === TIMESTAMP ===
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="When this status change occurred"
    )

    # === INDEXES ===
    __table_args__ = (
        # Check constraint: lsc_table must be 'jobs' or 'applications'
        CheckConstraint("lsc_table IN ('jobs', 'applications')", name='check_lsc_table_valid'),

        # Indexes for query performance
        Index('ix_log_status_change_lsc_table', 'lsc_table'),
        Index('ix_log_status_change_profile_id', 'profile_id'),
        Index('ix_log_status_change_job_id', 'job_id'),
        Index('ix_log_status_change_application_id', 'application_id'),
        Index('ix_log_status_change_updated_at', 'updated_at'),

        # Composite index for common query patterns
        Index('ix_log_status_change_job_table', 'job_id', 'lsc_table'),
    )

    def __repr__(self):
        return (
            f"<LogStatusChange(id={self.lsc_id}, "
            f"table={self.lsc_table}, "
            f"job={self.job_id}, app={self.application_id}, "
            f"'{self.initial_status}' → '{self.final_status}', "
            f"at={self.updated_at})>"
        )


# =============================================================================
# LLM PROVIDER MODEL - Represents the "llm_providers" table
# =============================================================================

class LLMProvider(Base):
    """
    LLMProvider model - reference table for LLM providers.

    This table stores all available LLM providers (e.g., Gemini, OpenAI, Anthropic).
    Used as a reference for tracking which provider was used for AI operations.
    """

    __tablename__ = "llm_providers"

    # Primary key
    llm_provider_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Provider name (e.g., 'gemini', 'openai', 'anthropic')
    llm_provider_name = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="LLM provider name: 'gemini', 'openai', 'anthropic'"
    )

    # Relationships (one provider can have many models)
    models = relationship("LLMModel", back_populates="provider", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LLMProvider(id={self.llm_provider_id}, name={self.llm_provider_name})>"


# =============================================================================
# LLM MODEL - Represents the "llm_models" table
# =============================================================================

class LLMModel(Base):
    """
    LLMModel model - reference table for LLM models.

    This table stores all available LLM models with their associated provider.
    Examples: 'gpt-4o-mini', 'claude-3-5-sonnet', 'gemini-2.0-flash-exp'

    Each model MUST belong to a registered provider (enforced via foreign key).
    """

    __tablename__ = "llm_models"

    # Primary key
    llm_model_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Model name (e.g., 'gpt-4o-mini', 'claude-3-5-sonnet-20241022')
    llm_model_name = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="LLM model name"
    )

    # Foreign key to llm_providers (mandatory - model must belong to a registered provider)
    llm_provider_id = Column(
        BigInteger,
        ForeignKey('llm_providers.llm_provider_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Foreign key to llm_providers"
    )

    # Provider name (denormalized for query performance)
    llm_provider_name = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Provider name (denormalized for performance)"
    )

    # Relationships
    provider = relationship("LLMProvider", back_populates="models")

    def __repr__(self):
        return f"<LLMModel(id={self.llm_model_id}, name={self.llm_model_name}, provider={self.llm_provider_name})>"


# =============================================================================
# LOG ATS MATCH MODEL - Represents the "log_ats_match" table
# =============================================================================

class LogATSMatch(Base):
    """
    LogATSMatch model - simplified ATS matching log.

    PURPOSE:
    --------
    Tracks ATS matching attempts with HTML snapshot for debugging.
    Records what the LLM extracted vs what we matched in the database.

    SCHEMA (ordered as required):
    ------------------------------
    1. lam_id (PK)
    2. application_id (FK to applications, mandatory)
    3. html_snapshot (input passed to LLM, mandatory)
    4. llm_provider_name (mandatory)
    5. extracted_ats_name (ATS name extracted by LLM, mandatory)
    6. best_match_ats_name (ATS name matched in DB, mandatory)
    7. ats_match_status ('ats_match' or 'ats_missing', mandatory)
    8. updated_at (timestamp, mandatory)

    RELATIONSHIPS:
    --------------
    - Belongs to one Application (required, CASCADE delete)
    """

    __tablename__ = "log_ats_match"

    # Primary key
    lam_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign key (mandatory)
    application_id = Column(
        BigInteger,
        ForeignKey('applications.application_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Application being processed"
    )

    # HTML snapshot (mandatory) - stores the input passed to the LLM
    html_snapshot = Column(
        Text,
        nullable=False,
        comment="HTML content passed to LLM for ATS identification"
    )

    # LLM provider (mandatory)
    llm_provider_name = Column(
        String(50),
        nullable=False,
        index=True,
        comment="LLM provider name: 'gemini', 'openai', 'anthropic'"
    )

    # Extracted ATS name from LLM (mandatory)
    extracted_ats_name = Column(
        String(100),
        nullable=False,
        comment="ATS name extracted by LLM"
    )

    # Best match ATS name from database (mandatory)
    best_match_ats_name = Column(
        String(100),
        nullable=False,
        comment="ATS name matched in atss table"
    )

    # Match status (mandatory) - only two values allowed
    ats_match_status = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Match status: 'ats_match' or 'ats_missing'"
    )

    # Timestamp (mandatory)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="When this log entry was created/updated"
    )

    # Relationships
    application = relationship("Application", back_populates="ats_match_logs")

    # Table-level configuration
    __table_args__ = (
        # Check constraint: ats_match_status must be 'ats_match' or 'ats_missing'
        CheckConstraint(
            "ats_match_status IN ('ats_match', 'ats_missing')",
            name='check_ats_match_status_valid'
        ),
        # Index for common query patterns
        Index('ix_log_ats_match_provider_status', 'llm_provider_name', 'ats_match_status'),
    )

    def __repr__(self):
        return (
            f"<LogATSMatch(id={self.lam_id}, "
            f"app={self.application_id}, "
            f"provider={self.llm_provider_name}, "
            f"extracted={self.extracted_ats_name}, "
            f"matched={self.best_match_ats_name}, "
            f"status={self.ats_match_status})>"
        )


# =============================================================================
# AI ARTIFACT MODEL - Represents the "ai_artifacts" table
# =============================================================================

class AIArtifact(Base):
    """
    AIArtifact model - represents AI-generated content cached in the database.

    PURPOSE:
    --------
    Stores AI-generated artifacts to avoid regenerating them for every application:
    - Parsed vacancy: Structured extraction of job requirements
    - Company info: Mission, values, products, tone
    - Motivation: Generated motivation letter
    - Cover letter: Full cover letter text
    - Match explanation: Why job matches/doesn't match profile

    ARTIFACT TYPES:
    ---------------
    - parsed_vacancy: Structured job requirements extracted from description
    - company_info: Company research (mission, values, products)
    - motivation: Motivation text for application
    - cover_letter: Full cover letter
    - match_explanation: AI explanation of match score
    - form_answers: Pre-generated answers for common questions

    CACHING STRATEGY:
    -----------------
    1. First application for job → Generate artifacts, save to DB
    2. Retry/second application → Reuse existing artifacts from DB
    3. Update if job description changes significantly

    RELATIONSHIPS:
    --------------
    - Belongs to one Job (always required)
    - May belong to one Application (optional - for application-specific artifacts)

    HOW TO USE:
    -----------
    Save parsed vacancy:
        artifact = AIArtifact(
            job_id=42,
            artifact_type='parsed_vacancy',
            content={
                'required_skills': ['Python', 'SQL', 'FastAPI'],
                'experience_years': 2,
                'education_level': 'Bachelor',
                'remote_ok': True,
                'responsibilities': ['Build APIs', 'Write tests'],
                'tech_stack': ['Python', 'PostgreSQL', 'Docker']
            }
        )
        db.add(artifact)
        db.commit()

    Retrieve parsed vacancy:
        parsed = db.query(AIArtifact).filter(
            AIArtifact.job_id == 42,
            AIArtifact.artifact_type == 'parsed_vacancy'
        ).first()

        if parsed:
            skills = parsed.content['required_skills']
            print(f"Required skills: {skills}")
    """

    __tablename__ = "ai_artifacts"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Keys
    job_id = Column(
        BigInteger,
        ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        comment="Job this artifact belongs to"
    )
    application_id = Column(
        BigInteger,
        ForeignKey("applications.application_id", ondelete="CASCADE"),
        nullable=True,
        comment="Specific application this was used for (optional)"
    )

    # Artifact data
    artifact_type = Column(
        String(30),
        nullable=False,
        comment="Type: parsed_vacancy, company_info, motivation, cover_letter, match_explanation, form_answers"
    )
    content = Column(
        JSONB,
        nullable=False,
        comment="Flexible JSON content - structure depends on artifact_type"
    )

    # Timestamp
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When artifact was generated"
    )

    # Relationships
    job = relationship("Job", back_populates="ai_artifacts")
    application = relationship("Application", back_populates="ai_artifacts")

    # Indexes
    __table_args__ = (
        Index('ix_ai_artifacts_job_id', 'job_id'),
        Index('ix_ai_artifacts_application_id', 'application_id'),
        Index('ix_ai_artifacts_job_type', 'job_id', 'artifact_type'),
    )


"""
================================================================================
AI ARTIFACT USAGE EXAMPLES
================================================================================

EXAMPLE 1: Save parsed vacancy
-------------------------------
parsed_artifact = AIArtifact(
    job_id=42,
    artifact_type='parsed_vacancy',
    content={
        'required_skills': ['Python', 'SQL', 'FastAPI'],
        'nice_to_have': ['Docker', 'AWS'],
        'experience_years': 2,
        'education_level': 'Bachelor',
        'remote_ok': True,
        'responsibilities': [
            'Build RESTful APIs',
            'Write unit tests',
            'Deploy to cloud'
        ],
        'tech_stack': ['Python', 'PostgreSQL', 'Docker', 'AWS']
    }
)
db.add(parsed_artifact)
db.commit()


EXAMPLE 2: Save company info
-----------------------------
company_artifact = AIArtifact(
    job_id=42,
    artifact_type='company_info',
    content={
        'company_name': 'Acme Corp',
        'mission': 'Building the future of cloud infrastructure',
        'values': ['Innovation', 'Collaboration', 'Customer focus'],
        'products': ['Cloud platform', 'API gateway'],
        'tone': 'professional, innovative, forward-thinking',
        'size': '50-200 employees',
        'funding': 'Series B'
    }
)
db.add(company_artifact)
db.commit()


EXAMPLE 3: Save generated motivation
-------------------------------------
motivation_artifact = AIArtifact(
    job_id=42,
    application_id=15,
    artifact_type='motivation',
    content={
        'text': 'I am excited to apply for this position because...',
        'language': 'en',
        'word_count': 150,
        'tone': 'enthusiastic, professional',
        'key_points': [
            'Relevant Python experience',
            'Passion for cloud technologies',
            'Alignment with company mission'
        ]
    }
)
db.add(motivation_artifact)
db.commit()


EXAMPLE 4: Retrieve and reuse artifacts
----------------------------------------
# Check if we already have parsed vacancy
existing_parsed = db.query(AIArtifact).filter(
    AIArtifact.job_id == 42,
    AIArtifact.artifact_type == 'parsed_vacancy'
).first()

if existing_parsed:
    print("Reusing existing parsed vacancy")
    required_skills = existing_parsed.content['required_skills']
else:
    print("Need to generate new parsed vacancy")
    # Call LLM to parse vacancy


EXAMPLE 5: Get all artifacts for job
-------------------------------------
job_artifacts = db.query(AIArtifact).filter(
    AIArtifact.job_id == 42
).all()

print(f"Found {len(job_artifacts)} artifacts for job 42:")
for artifact in job_artifacts:
    print(f"- {artifact.artifact_type}")


EXAMPLE 6: Save match explanation
----------------------------------
match_artifact = AIArtifact(
    job_id=42,
    artifact_type='match_explanation',
    content={
        'match_score': 0.85,
        'reasoning': 'Strong match because: Python experience, SQL knowledge, remote-friendly',
        'strengths': [
            'Has required Python skills',
            'SQL experience matches requirements',
            'Location preference aligns'
        ],
        'weaknesses': [
            'No AWS experience (nice-to-have)',
            'Slightly below preferred experience level'
        ],
        'recommendation': 'approved_for_application'
    }
)
db.add(match_artifact)
db.commit()


EXAMPLE 7: Query by artifact type
----------------------------------
# Get all motivations for review
motivations = db.query(AIArtifact).filter(
    AIArtifact.artifact_type == 'motivation'
).all()

for m in motivations:
    job_id = m.job_id
    text = m.content.get('text', '')
    print(f"Job {job_id}: {text[:100]}...")


EXAMPLE 8: Update artifact content
-----------------------------------
# Update company info with new data
artifact = db.query(AIArtifact).filter(
    AIArtifact.job_id == 42,
    AIArtifact.artifact_type == 'company_info'
).first()

if artifact:
    # Update content (merge with existing)
    artifact.content['funding'] = 'Series C'
    artifact.content['size'] = '200-500 employees'
    db.commit()
"""


class ATS(Base):
    """
    ATS model - represents Application Tracking Systems (job portals).

    PURPOSE:
    --------
    Reference table for all supported ATS platforms. This normalizes ATS names
    and provides a single source of truth for portal identification across the system.

    USE CASES:
    ----------
    - Identify which ATS a job URL belongs to (Greenhouse, Lever, Workday, etc.)
    - Track which ATS platforms the agent can handle
    - Link accounts and workflows to specific ATS platforms
    - Generate statistics on which ATS systems are most common

    EXAMPLES OF ATS PLATFORMS:
    ---------------------------
    - Greenhouse
    - Lever
    - Workday
    - Ashby
    - SmartRecruiters
    - iCIMS
    - Taleo
    - BambooHR
    - JazzHR
    - Custom (company-specific portals)

    HOW TO USE:
    -----------
    Create ATS entry:
        ats = ATS(ats_name='Greenhouse')
        db.add(ats)
        db.commit()

    Query ATS:
        # Find specific ATS
        greenhouse = db.query(ATS).filter(ATS.ats_name == 'Greenhouse').first()

        # Get all ATS platforms
        all_ats = db.query(ATS).order_by(ATS.ats_name).all()

    Link to other tables:
        # When creating account or workflow, reference ats_id
        account = Account(
            portal_name='Greenhouse',
            ats_id=greenhouse.ats_id,  # FK reference
            ...
        )
    """

    __tablename__ = "atss"

    # Primary Key
    ats_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # ATS data
    ats_name = Column(
        String(50),
        nullable=False,
        unique=True,
        comment="Name of the ATS platform (e.g., Greenhouse, Lever, Workday)"
    )

    # Relationships
    applications = relationship("Application", back_populates="ats")

    # Indexes
    __table_args__ = (
        Index('ix_atss_name', 'ats_name'),
    )

    def __repr__(self):
        return f"<ATS(id={self.ats_id}, name='{self.ats_name}')>"


class Workflow(Base):
    """
    Workflow model - represents automation workflows for specific ATS platforms.

    PURPOSE:
    --------
    Reference table for all automation workflows. Each workflow defines a specific
    sequence of steps to complete an application on a particular ATS platform.

    USE CASES:
    ----------
    - Match jobs to appropriate automation workflow based on ATS and job type
    - Track which workflows are implemented and tested
    - Version control for workflow changes (e.g., "greenhouse_standard_v2")
    - Link applications to the workflow used for submission

    WORKFLOW TYPES:
    ---------------
    - standard: Basic job application flow (most common)
    - with_assessment: Application includes coding test or assessment
    - with_video: Application includes video interview questions
    - referral: Application submitted with employee referral
    - custom: Company-specific custom workflow

    WORKFLOW NAMING CONVENTION:
    ---------------------------
    Format: {ats}_{type}_{version}
    Examples:
    - greenhouse_standard_v1
    - lever_with_assessment_v1
    - workday_standard_v2
    - ashby_custom_v1

    HOW TO USE:
    -----------
    Create workflow entry:
        workflow = Workflow(
            workflow_type='standard',
            workflow_name='greenhouse_standard_v1'
        )
        db.add(workflow)
        db.commit()

    Query workflows:
        # Find specific workflow
        workflow = db.query(Workflow).filter(
            Workflow.workflow_name == 'greenhouse_standard_v1'
        ).first()

        # Get all standard workflows
        standard_workflows = db.query(Workflow).filter(
            Workflow.workflow_type == 'standard'
        ).all()

        # Get all workflows for a specific ATS (using naming convention)
        greenhouse_workflows = db.query(Workflow).filter(
            Workflow.workflow_name.like('greenhouse_%')
        ).all()

    Link to applications:
        # When creating application, reference workflow_id
        application = Application(
            job_id=42,
            workflow_id=workflow.workflow_id,  # FK reference
            status='created',
            ...
        )
    """

    __tablename__ = "workflows"

    # Primary Key
    workflow_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Workflow data
    workflow_type = Column(
        String(50),
        nullable=False,
        comment="Type of workflow: standard, with_assessment, with_video, referral, custom"
    )
    workflow_name = Column(
        String(50),
        nullable=False,
        unique=True,
        comment="Unique workflow identifier (e.g., greenhouse_standard_v1)"
    )

    # Relationships
    applications = relationship("Application", back_populates="workflow")

    # Indexes
    __table_args__ = (
        Index('ix_workflows_type', 'workflow_type'),
        Index('ix_workflows_name', 'workflow_name'),
    )

    def __repr__(self):
        return f"<Workflow(id={self.workflow_id}, type='{self.workflow_type}', name='{self.workflow_name}')>"


class Company(Base):
    """
    Company model - represents companies and their ATS/workflow configurations.

    PURPOSE:
    --------
    Central registry of all companies the agent interacts with. Links companies to:
    - Their ATS platform (which portal system they use)
    - Agent accounts (login credentials for their portal)
    - Automation workflows (how to apply on their portal)

    USE CASES:
    ----------
    - Track which ATS platform a company uses
    - Reuse existing accounts for multiple jobs at the same company
    - Select appropriate automation workflow based on company's ATS
    - Store company-specific ATS tokens or identifiers
    - Avoid creating duplicate accounts for the same company

    DENORMALIZATION:
    ----------------
    ats_name is denormalized (duplicated) from the atss table for quick lookups
    without joins. This is intentional for performance.

    RELATIONSHIPS:
    --------------
    - Links to ATS platform (companies.ats_id → atss.ats_id) [REQUIRED]
    - May link to an Account (companies.account_id → accounts.account_id) [OPTIONAL]
    - May link to a Workflow (companies.workflow_id → workflows.workflow_id) [OPTIONAL]

    HOW TO USE:
    -----------
    Create company entry:
        company = Company(
            company_name='Acme Corp',
            ats_id=1,  # FK to atss table (e.g., Greenhouse)
            ats_name='Greenhouse',  # Denormalized for performance
            ats_company_token='acmecorp',  # Company identifier in Greenhouse
            account_id=5,  # FK to existing account (optional)
            workflow_id=2  # FK to workflow (optional)
        )
        db.add(company)
        db.commit()

    Query companies:
        # Find company by name
        company = db.query(Company).filter(
            Company.company_name == 'Acme Corp'
        ).first()

        # Get all companies using Greenhouse
        greenhouse_companies = db.query(Company).filter(
            Company.ats_name == 'Greenhouse'
        ).all()

        # Get all companies with existing accounts
        companies_with_accounts = db.query(Company).filter(
            Company.account_id.isnot(None)
        ).all()

    Check if account exists for company:
        company = db.query(Company).filter(
            Company.company_name == 'Acme Corp'
        ).first()

        if company and company.account_id:
            print(f"Account exists: {company.account_id}")
        else:
            print("Need to create new account")
    """

    __tablename__ = "companies"

    # Primary Key
    company_id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Primary key")

    # Company information
    company_name = Column(
        String(50),
        nullable=False,
        comment="Company name"
    )

    # ATS information (required)
    ats_id = Column(
        BigInteger,
        ForeignKey("atss.ats_id", ondelete="CASCADE"),
        nullable=False,
        comment="Foreign key to atss table"
    )
    ats_name = Column(
        String(50),
        nullable=False,
        comment="ATS name (denormalized from atss table for performance)"
    )

    # Company-specific ATS token (optional)
    ats_company_token = Column(
        String(50),
        nullable=True,
        comment="Company-specific token/identifier in the ATS (e.g., 'acmecorp' in Greenhouse URL)"
    )

    # Linked resources (optional)
    account_id = Column(
        BigInteger,
        ForeignKey("accounts.account_id", ondelete="SET NULL"),
        nullable=True,
        comment="Foreign key to accounts table (optional)"
    )
    workflow_id = Column(
        BigInteger,
        ForeignKey("workflows.workflow_id", ondelete="SET NULL"),
        nullable=True,
        comment="Foreign key to workflows table (optional)"
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When record was created"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp"
    )

    # Relationships
    ats = relationship("ATS")
    account = relationship("Account")
    workflow = relationship("Workflow")
    applications = relationship("Application", back_populates="company")

    # Indexes for query performance
    __table_args__ = (
        Index('ix_companies_company_name', 'company_name'),
        Index('ix_companies_ats_id', 'ats_id'),
        Index('ix_companies_account_id', 'account_id'),
        Index('ix_companies_workflow_id', 'workflow_id'),
    )

    def __repr__(self):
        return (
            f"<Company(id={self.company_id}, "
            f"name='{self.company_name}', "
            f"ats='{self.ats_name}', "
            f"account_id={self.account_id}, "
            f"workflow_id={self.workflow_id})>"
        )


class Setting(Base):
    """
    Setting - Application configuration settings stored in database.

    PURPOSE:
    --------
    Stores system-wide configuration settings that can be modified at runtime
    without requiring environment variable changes or application restarts.

    DESIGN:
    -------
    - setting_id: Primary key (auto-increment)
    - setting_name: Unique setting identifier (e.g., 'ats_match_model')
    - setting_value: Setting value as JSON (flexible for different data types)
    - created_at: When setting was first created
    - updated_at: When setting was last modified

    USE CASES:
    ----------
    - Configure which LLM model to use for ATS matching
    - Future: Configure company matching model, job filtering thresholds, etc.
    - Allows UI-based configuration without code deployment

    EXAMPLES:
    ---------
    - setting_name='ats_match_model', setting_value='{"provider": "openai", "model": "gpt-4o-mini"}'
    - setting_name='company_match_model', setting_value='{"provider": "gemini", "model": "gemini-2.0-flash-exp"}'
    - setting_name='match_score_threshold', setting_value='{"value": 0.7}'

    TABLE:
    ------
    CREATE TABLE settings (
        setting_id BIGSERIAL PRIMARY KEY,
        setting_name VARCHAR(100) NOT NULL UNIQUE,
        setting_value JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """

    __tablename__ = "settings"

    # Primary Key
    setting_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Primary key for settings table"
    )

    # Setting Identification
    setting_name = Column(
        String(100),
        nullable=False,
        unique=True,
        comment="Unique setting identifier (e.g., 'ats_match_model')"
    )

    # Setting Value (stored as JSONB for flexibility)
    setting_value = Column(
        JSONB,
        nullable=False,
        comment="Setting value stored as JSONB (flexible for different data types)"
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When setting was created"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When setting was last updated"
    )

    # Indexes
    __table_args__ = (
        Index('ix_settings_setting_name', 'setting_name'),
    )

    def __repr__(self):
        return (
            f"<Setting(id={self.setting_id}, "
            f"name='{self.setting_name}', "
            f"value={self.setting_value})>"
        )
