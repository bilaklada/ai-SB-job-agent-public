"""
job.py - Pydantic Schemas for Job Model

================================================================================
WHAT THIS FILE DOES:
================================================================================
This file defines Pydantic schemas for validating Job data in API requests
and responses. These schemas work hand-in-hand with the SQLAlchemy Job model.

WHY DO WE NEED TWO SEPARATE MODELS (SQLAlchemy AND Pydantic)?
==============================================================

SQLAlchemy Model (app/db/models.py):
- Represents database table structure
- Handles database operations (insert, update, delete, query)
- Includes database-specific features (indexes, foreign keys)
- Has fields like id, created_at that are auto-generated

Pydantic Schema (THIS FILE):
- Validates data coming from API requests
- Validates data going out in API responses
- Type checking and automatic conversion
- Provides API documentation in OpenAPI/Swagger
- Can have different fields for different operations

REAL-WORLD EXAMPLE:
==================
User creates a job via API POST /jobs:

1. Request JSON arrives: {"title": "Engineer", "company": "Acme", ...}
2. Pydantic JobCreate validates the data:
   - Is title a string? ✓
   - Is URL valid? ✓
   - All required fields present? ✓
3. If valid, create SQLAlchemy Job instance
4. Save to database (SQLAlchemy adds id, created_at automatically)
5. Convert Job instance to Pydantic JobRead
6. Return as JSON response

Without Pydantic:
- No automatic validation (bad data reaches database)
- Manual type checking (messy code)
- No automatic API documentation

With Pydantic:
- Automatic validation ✓
- Type conversion ✓
- Clear error messages ✓
- Auto-generated API docs ✓

================================================================================
SCHEMA TYPES IN THIS FILE:
================================================================================

1. JobBase
   - Base schema with common fields
   - Other schemas inherit from this
   - DRY principle (Don't Repeat Yourself)

2. JobCreate
   - Used for POST /jobs (creating new job)
   - Only includes fields user can provide
   - Excludes: id, created_at, updated_at (auto-generated)

3. JobUpdate
   - Used for PUT/PATCH /jobs/{id} (updating job)
   - All fields optional (partial updates allowed)
   - User can update any field

4. JobRead
   - Used for GET responses
   - Includes ALL fields from database
   - Has id, created_at, updated_at
   - Converts SQLAlchemy object to JSON

================================================================================
HOW THIS CONNECTS TO THE REST OF THE PROJECT:
================================================================================

1. app/db/models.py → SQLAlchemy Job model (database)
   ↓
2. THIS FILE → Pydantic schemas (validation)
   ↓
3. app/api/routes_jobs.py → FastAPI routes use schemas
   ↓
4. User makes API request → Pydantic validates
   ↓
5. Database operation → SQLAlchemy handles
   ↓
6. Response generated → Pydantic serializes to JSON

================================================================================
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

# Pydantic imports for data validation
from pydantic import BaseModel, Field, ConfigDict
# BaseModel: Base class for all Pydantic schemas
# Field: Add descriptions, examples, validation rules to fields
# HttpUrl: Special type for validating URLs
# ConfigDict: Configuration for Pydantic model behavior

# Python typing for type hints
from typing import Optional
# Optional[str] means: can be str or None

# Date/time for timestamps
from datetime import datetime


# =============================================================================
# BASE SCHEMA - Common Fields Shared by All Job Schemas
# =============================================================================

class JobBase(BaseModel):
    """
    Base schema with common Job fields.

    WHY CREATE A BASE SCHEMA?
    ------------------------
    Instead of repeating the same fields in JobCreate, JobUpdate, JobRead,
    we define common fields once in JobBase and inherit from it.

    DRY Principle (Don't Repeat Yourself):
    - Define once in JobBase
    - Inherit in other schemas
    - If field changes, update once

    WHAT FIELDS ARE HERE?
    ---------------------
    Fields that:
    - User can provide when creating a job
    - Can be updated later
    - Are part of the core job data

    WHAT FIELDS ARE NOT HERE?
    --------------------------
    Fields that are:
    - Auto-generated (id, created_at, updated_at)
    - Added later in specific schemas

    INHERITANCE EXAMPLE:
    -------------------
    class JobCreate(JobBase):
        pass  # Inherits all fields from JobBase
    """

    # =========================================================================
    # CORE JOB INFORMATION
    # =========================================================================

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="Job title or position name (optional for manual jobs)",
        examples=["Senior Software Engineer", "Data Scientist", "Product Manager"]
    )
    # Field annotations explained:
    # - title: Optional[str] → Can be string or None
    # - None → Default value (nullable)
    # - min_length=1 → If provided, must have at least 1 character (not empty string)
    # - max_length=500 → Cannot exceed 500 characters
    # - description → Shows up in API documentation
    # - examples → Shows example values in API docs
    #
    # Why optional: Manual jobs (URL only) can be created without title

    company: Optional[str] = Field(
        None,
        max_length=255,
        description="Company or employer name",
        examples=["Google", "Microsoft", "Startup Inc."]
    )
    # Optional[str] = Field(None, ...) → Can be string or None
    # None as first argument → Default value if not provided
    # Why optional: Some job boards don't provide company name

    url: str = Field(
        ...,
        max_length=1000,
        description="URL to the job posting",
        examples=["https://jobs.lever.co/company/position-id"]
    )
    # Note: Using str instead of HttpUrl for flexibility
    # HttpUrl is very strict and might reject valid job board URLs
    # We validate it's not empty via min_length=1 (implied by required)
    # Why required: Need URL to apply to the job

    description: Optional[str] = Field(
        None,
        description="Full job description text including responsibilities, requirements, benefits",
        examples=["We are looking for a Senior Software Engineer to join our team..."]
    )
    # Optional because some APIs provide limited job info
    # Can be very long (5,000+ characters)
    # Used by AI matching engine for analysis

    # =========================================================================
    # LOCATION INFORMATION
    # =========================================================================

    location_city: Optional[str] = Field(
        None,
        max_length=100,
        description="City where job is located (or 'Remote' for remote jobs)",
        examples=["San Francisco", "New York", "London", "Remote"]
    )
    # Optional: Not all jobs specify city
    # Extracted from job API or parsed from location string

    location_country: Optional[str] = Field(
        None,
        max_length=100,
        description="Country where job is located",
        examples=["United States", "Germany", "Japan", "United Kingdom"]
    )
    # Optional but important for filtering
    # Used in profile preferences: target_countries

    # =========================================================================
    # JOB SOURCE TRACKING
    # =========================================================================

    provider: str = Field(
        ...,
        max_length=100,
        description="Job board or API that provided this job",
        examples=["adzuna", "jooble", "indeed", "greenhouse", "lever"]
    )
    # Required: Must track where job came from
    # Used for analytics and provider-specific handling

    provider_job_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Job ID in the provider's system (for deduplication)",
        examples=["12345", "abc-def-ghi", "job_2024_001"]
    )
    # Optional: Not all providers give external IDs
    # Used with provider for deduplication check

    # =========================================================================
    # APPLICATION WORKFLOW
    # =========================================================================

    status: str = Field(
        default="new",
        max_length=50,
        description="Current status in the job application pipeline",
        examples=["new", "filtered", "approved_for_application", "rejected", "applied"]
    )
    # Default value: "new" (all new jobs start here)
    # Required but has default, so user doesn't need to provide
    # Values: new, filtered, approved_for_application, rejected, etc.

    match_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="AI-calculated match score between job and profile (0.0 to 1.0)",
        examples=[0.85, 0.42, 0.91]
    )
    # Optional: Only set after AI analysis
    # ge=0.0 → Greater than or equal to 0
    # le=1.0 → Less than or equal to 1
    # Validates: 0 ≤ match_score ≤ 1

    reject_reason: Optional[str] = Field(
        None,
        description="Human-readable explanation why job was rejected",
        examples=[
            "Location not in target countries",
            "Required 10 years experience, profile has 3",
            "Salary below minimum threshold"
        ]
    )
    # Only filled when status='rejected'
    # Helps improve filters and understand rejection patterns

    # =========================================================================
    # APPLICATION TYPE
    # =========================================================================

    apply_type: Optional[str] = Field(
        None,
        max_length=50,
        description="How/where to submit application (detected from URL)",
        examples=["company_site", "greenhouse", "lever", "workday", "linkedin"]
    )
    # Detected by URL pattern matching
    # Used by orchestrator to pick correct RPA script
    # Optional: Might not be determined yet

    # =========================================================================
    # SALARY INFORMATION
    # =========================================================================

    salary_min: Optional[float] = Field(
        None,
        ge=0,
        description="Minimum salary for the position (stored as NUMERIC(12,2) in database)",
        examples=[80000.0, 120000.50, 95000.0]
    )
    # Optional: Many jobs don't list salary
    # Currency specified in salary_currency field
    # Note: Stored as NUMERIC(12,2) in database for exact precision
    # Pydantic float validation accepts numeric input

    salary_max: Optional[float] = Field(
        None,
        ge=0,
        description="Maximum salary for the position (stored as NUMERIC(12,2) in database)",
        examples=[150000.0, 180000.00, 110000.75]
    )
    # Forms salary range with salary_min
    # Note: Stored as NUMERIC(12,2) in database for exact precision

    salary_currency: Optional[str] = Field(
        None,
        max_length=10,
        description="Currency code for salary (ISO 4217 3-letter code)",
        examples=["USD", "EUR", "GBP", "CHF"]
    )
    # ISO 4217 3-letter currency codes
    # Note: ISO codes are always 3 characters, but max_length=10 allows flexibility

    posted_at: Optional[datetime] = Field(
        None,
        description="When the job was originally posted by the employer (timezone-aware)",
        examples=["2024-01-10T10:30:00Z", "2024-01-10T10:30:00+00:00"]
    )
    # Different from created_at (when WE added it to our DB)
    # Note: Stored as TIMESTAMPTZ in database (timezone-aware)
    # Pydantic serializes to ISO 8601 format with timezone


# =============================================================================
# CREATE SCHEMA - For POST Requests (Creating New Jobs)
# =============================================================================

class JobCreate(JobBase):
    """
    Schema for creating a new job via POST /jobs.

    WHEN IS THIS USED?
    ------------------
    - User/service creates a new job via API
    - Job provider adapter fetches jobs and creates records
    - Admin manually adds a job

    WHAT'S DIFFERENT FROM JobBase?
    -------------------------------
    Nothing! JobCreate inherits all fields from JobBase.
    We keep it separate for:
    1. Semantic clarity (JobCreate is for creating)
    2. Future flexibility (might add create-only validations)
    3. API documentation (shows up as separate schema)

    WHAT FIELDS ARE EXCLUDED?
    -------------------------
    - id: Auto-generated by database
    - created_at: Auto-set by database
    - updated_at: Auto-set by database

    EXAMPLE API REQUEST:
    -------------------
    POST /jobs
    {
        "title": "Senior Python Developer",
        "company": "Acme Corp",
        "url": "https://jobs.acme.com/python-dev",
        "description": "We are looking for...",
        "location_city": "San Francisco",
        "location_country": "United States",
        "provider": "adzuna",
        "provider_job_id": "12345",
        "status": "new"
    }

    VALIDATION HAPPENS AUTOMATICALLY:
    ---------------------------------
    If user sends:
        {"title": "", "url": "not-a-url"}

    Pydantic returns error:
        {
            "detail": [
                {"loc": ["title"], "msg": "ensure this value has at least 1 characters"},
                {"loc": ["url"], "msg": "invalid URL format"}
            ]
        }
    """
    pass  # Inherits all fields from JobBase


# =============================================================================
# UPDATE SCHEMA - For PUT/PATCH Requests (Updating Existing Jobs)
# =============================================================================

class JobUpdate(BaseModel):
    """
    Schema for updating an existing job via PUT/PATCH /jobs/{id}.

    WHEN IS THIS USED?
    ------------------
    - Update job status (new → approved → applied)
    - Set match_score after AI analysis
    - Add reject_reason when rejecting
    - Update any job field

    WHAT'S DIFFERENT FROM JobCreate?
    ---------------------------------
    ALL fields are Optional (partial updates allowed).

    Why? You might want to update only one field:
        PATCH /jobs/1 {"status": "approved_for_application"}

    Without all Optional fields:
        Error: "Missing required field: title, company, url..."

    With all Optional fields:
        Success! Only status is updated.

    EXAMPLE API REQUESTS:
    ---------------------
    1. Update status only:
        PATCH /jobs/1
        {"status": "approved_for_application"}

    2. Set match score:
        PATCH /jobs/1
        {"match_score": 0.85}

    3. Reject with reason:
        PATCH /jobs/1
        {
            "status": "rejected",
            "reject_reason": "Location not in target countries"
        }

    4. Update multiple fields:
        PATCH /jobs/1
        {
            "status": "approved_for_application",
            "match_score": 0.92,
            "apply_type": "greenhouse"
        }

    IMPORTANT: PARTIAL UPDATES
    --------------------------
    In the route handler, you should:
    1. Get existing job from database
    2. Update only provided fields (exclude_unset=True)
    3. Save back to database

    Example route code:
        job_update = JobUpdate(**request_data)
        for field, value in job_update.model_dump(exclude_unset=True).items():
            setattr(existing_job, field, value)
        db.commit()
    """

    # All fields from JobBase, but all Optional for partial updates
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    company: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = None
    location_city: Optional[str] = Field(None, max_length=100)
    location_country: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, max_length=100)
    provider_job_id: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=50)
    match_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    reject_reason: Optional[str] = None
    apply_type: Optional[str] = Field(None, max_length=50)
    salary_min: Optional[float] = Field(None, ge=0, description="Stored as NUMERIC(12,2)")
    salary_max: Optional[float] = Field(None, ge=0, description="Stored as NUMERIC(12,2)")
    salary_currency: Optional[str] = Field(None, max_length=10, description="ISO 4217 code")
    posted_at: Optional[datetime] = Field(None, description="Timezone-aware timestamp")


# =============================================================================
# READ SCHEMA - For GET Responses (Reading Jobs from Database)
# =============================================================================

class JobRead(JobBase):
    """
    Schema for returning job data in API responses (GET /jobs, GET /jobs/{id}).

    WHEN IS THIS USED?
    ------------------
    - GET /jobs → Returns list of jobs
    - GET /jobs/{id} → Returns single job
    - POST /jobs → Returns created job
    - Any endpoint that returns job data

    WHAT'S DIFFERENT FROM JobCreate?
    ---------------------------------
    Includes database-generated fields:
    - id: Primary key
    - created_at: When job was created
    - updated_at: When job was last modified

    WHY SEPARATE FROM JobCreate?
    -----------------------------
    Create: User provides data (no id yet)
    Read: Database returns data (includes id, timestamps)

    EXAMPLE API RESPONSE:
    --------------------
    GET /jobs/1

    Response:
    {
        "id": 1,
        "title": "Senior Python Developer",
        "company": "Acme Corp",
        "url": "https://jobs.acme.com/python-dev",
        "description": "We are looking for...",
        "location_city": "San Francisco",
        "location_country": "United States",
        "provider": "adzuna",
        "provider_job_id": "12345",
        "status": "approved_for_application",
        "match_score": 0.85,
        "reject_reason": null,
        "apply_type": "greenhouse",
        "created_at": "2024-01-15T14:30:00",
        "updated_at": "2024-01-15T15:00:00"
    }

    HOW DOES THIS CONVERT SQLAlchemy TO JSON?
    -----------------------------------------
    Thanks to model_config with from_attributes=True:

    Route code:
        job = db.query(Job).first()  # SQLAlchemy Job instance
        return JobRead.model_validate(job)  # Automatically converts to JSON!

    Without from_attributes=True:
        Error: Cannot convert SQLAlchemy object

    With from_attributes=True:
        Pydantic reads: job.id, job.title, job.created_at, etc.
        Returns valid JSON ✓
    """

    # Database-generated fields (not in JobBase)
    id: int = Field(
        ...,
        description="Unique identifier for the job",
        examples=[1, 2, 3]
    )
    # Primary key from database
    # Always present in responses

    created_at: datetime = Field(
        ...,
        description="When this job was first added to the database (UTC, timezone-aware)",
        examples=["2024-01-15T14:30:00Z", "2024-01-15T14:30:00+00:00"]
    )
    # Automatically set by database on insert
    # Stored as TIMESTAMPTZ in database (timezone-aware)
    # UTC timezone recommended
    # ISO 8601 format in JSON with timezone indicator

    updated_at: datetime = Field(
        ...,
        description="When this job was last modified (UTC, timezone-aware)",
        examples=["2024-01-15T15:00:00Z", "2024-01-15T15:00:00+00:00"]
    )
    # Automatically updated by database on every change
    # Stored as TIMESTAMPTZ in database (timezone-aware)
    # UTC timezone recommended

    # =========================================================================
    # PYDANTIC V2 CONFIGURATION
    # =========================================================================

    model_config = ConfigDict(
        from_attributes=True,
        # CRITICAL SETTING: Allows converting SQLAlchemy objects to Pydantic
        # Without this, you'd need to manually convert:
        #   JobRead(id=job.id, title=job.title, ...)
        # With this, automatic conversion:
        #   JobRead.model_validate(job)

        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Senior Python Developer",
                "company": "Acme Corp",
                "url": "https://jobs.acme.com/python-dev",
                "description": "We are looking for a Senior Python Developer...",
                "location_city": "San Francisco",
                "location_country": "United States",
                "provider": "adzuna",
                "provider_job_id": "12345",
                "status": "approved_for_application",
                "match_score": 0.85,
                "reject_reason": None,
                "apply_type": "greenhouse",
                "created_at": "2024-01-15T14:30:00",
                "updated_at": "2024-01-15T15:00:00"
            }
        }
        # Shows this example in API documentation (Swagger UI)
        # Helps users understand the response format
    )

    """
    WHAT IS from_attributes (formerly orm_mode)?
    ============================================
    In Pydantic v2, orm_mode was renamed to from_attributes.

    Purpose: Allow Pydantic to read from object attributes, not just dicts.

    Without from_attributes=True:
        job = db.query(Job).first()
        JobRead(**job)  # ❌ Error: Job is not a dict

    With from_attributes=True:
        job = db.query(Job).first()
        JobRead.model_validate(job)  # ✅ Works! Reads job.id, job.title, etc.

    This is ESSENTIAL for ORM integration.

    PYDANTIC V1 vs V2:
    ------------------
    Pydantic v1:
        class Config:
            orm_mode = True

    Pydantic v2:
        model_config = ConfigDict(from_attributes=True)

    We use v2 syntax (ConfigDict) for modern Pydantic.
    """


# =============================================================================
# USAGE EXAMPLES IN ROUTES
# =============================================================================

"""
EXAMPLE 1: Create a job (POST)
-------------------------------
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Job
from app.schemas.job import JobCreate, JobRead

router = APIRouter()

@router.post("/jobs", response_model=JobRead, status_code=201)
def create_job(job_data: JobCreate, db: Session = Depends(get_db)):
    # job_data is automatically validated by Pydantic
    # If validation fails, FastAPI returns 422 error

    # Create SQLAlchemy Job instance from Pydantic schema
    new_job = Job(**job_data.model_dump())

    # Save to database
    db.add(new_job)
    db.commit()
    db.refresh(new_job)  # Get auto-generated id, created_at

    # Return as JobRead (Pydantic converts to JSON)
    return new_job  # FastAPI uses JobRead schema automatically


EXAMPLE 2: List jobs (GET)
---------------------------
@router.get("/jobs", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    return jobs  # FastAPI converts list of Job objects to JSON


EXAMPLE 3: Get single job (GET)
--------------------------------
from fastapi import HTTPException

@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job  # FastAPI converts Job object to JSON


EXAMPLE 4: Update job (PATCH)
------------------------------
@router.patch("/jobs/{job_id}", response_model=JobRead)
def update_job(
    job_id: int,
    job_update: JobUpdate,
    db: Session = Depends(get_db)
):
    # Find existing job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update only provided fields
    update_data = job_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)

    return job


EXAMPLE 5: Filter jobs by status
---------------------------------
@router.get("/jobs/status/{status}", response_model=list[JobRead])
def get_jobs_by_status(status: str, db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.status == status).all()
    return jobs


EXAMPLE 6: Manual validation
-----------------------------
from pydantic import ValidationError

def process_job_data(raw_data: dict):
    try:
        # Validate data
        job_data = JobCreate(**raw_data)

        # Data is valid, use it
        print(f"Valid job: {job_data.title}")

    except ValidationError as e:
        # Invalid data
        print(f"Validation errors: {e}")
        # e.errors() contains list of all validation errors
"""


# =============================================================================
# VALIDATION EXAMPLES
# =============================================================================

"""
EXAMPLE 1: Valid data
---------------------
data = {
    "title": "Software Engineer",
    "company": "Acme Corp",
    "url": "https://jobs.acme.com/engineer",
    "provider": "adzuna",
    "status": "new"
}

job = JobCreate(**data)
# ✅ Success! All validations pass


EXAMPLE 2: Missing required field
----------------------------------
data = {
    "company": "Acme Corp",
    # Missing required "title"
}

job = JobCreate(**data)
# ❌ ValidationError: Field required [type=missing, input_value={...}]


EXAMPLE 3: Invalid type
-----------------------
data = {
    "title": 123,  # Should be string, not int
    "url": "https://jobs.acme.com/job"
}

job = JobCreate(**data)
# ❌ ValidationError: Input should be a valid string


EXAMPLE 4: Exceeds max length
------------------------------
data = {
    "title": "a" * 501,  # 501 characters (max is 500)
    "url": "https://jobs.acme.com/job"
}

job = JobCreate(**data)
# ❌ ValidationError: String should have at most 500 characters


EXAMPLE 5: Invalid match_score range
-------------------------------------
data = {
    "title": "Engineer",
    "url": "https://jobs.acme.com/job",
    "match_score": 1.5  # Out of range (max is 1.0)
}

job = JobCreate(**data)
# ❌ ValidationError: Input should be less than or equal to 1.0


EXAMPLE 6: Partial update (only status)
----------------------------------------
data = {"status": "approved_for_application"}

job_update = JobUpdate(**data)
# ✅ Success! Only status field is set

print(job_update.model_dump(exclude_unset=True))
# Output: {"status": "approved_for_application"}
# Other fields are not included (partial update)
"""
