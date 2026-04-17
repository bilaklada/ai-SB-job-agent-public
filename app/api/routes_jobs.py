"""
routes_jobs.py - Job API Endpoints

================================================================================
WHAT THIS FILE DOES:
================================================================================
This file defines all HTTP endpoints for managing jobs in the database.
Think of it as the "interface" between the outside world and your job data.

Users/services can:
- Create new jobs (POST /jobs)
- List all jobs with filters (GET /jobs)
- Get a specific job (GET /jobs/{id})
- Update a job (PATCH /jobs/{id})
- Delete a job (DELETE /jobs/{id})

================================================================================
HOW FASTAPI ROUTES WORK:
================================================================================

1. User makes HTTP request:
   GET http://localhost:8000/jobs?status=new

2. FastAPI finds matching route:
   @router.get("/jobs")

3. FastAPI calls dependency functions:
   - get_db() creates database session

4. FastAPI calls route function:
   - list_jobs(status="new", db=<session>)

5. Function queries database:
   - db.query(Job).filter(Job.status == "new").all()

6. Function returns data:
   - return jobs

7. FastAPI serializes to JSON:
   - Uses JobRead schema to convert SQLAlchemy → JSON

8. User receives response:
   - [{"id": 1, "title": "...", ...}, ...]

================================================================================
HTTP METHODS & THEIR MEANINGS:
================================================================================

GET    - Retrieve data (read-only, no changes)
POST   - Create new resource
PUT    - Replace entire resource
PATCH  - Update part of resource (partial update)
DELETE - Remove resource

================================================================================
STATUS CODES USED IN THIS FILE:
================================================================================

200 OK              - Success (GET, PATCH, DELETE)
201 Created         - Success (POST) - new resource created
404 Not Found       - Resource doesn't exist
422 Unprocessable   - Validation error (automatic by Pydantic)
500 Internal Error  - Server error

================================================================================
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

# FastAPI imports for building the API
from fastapi import APIRouter, Depends, HTTPException, Query, status
# APIRouter: Creates a group of related routes (all job endpoints)
# Depends: Dependency injection (automatically calls get_db() for us)
# HTTPException: Raise HTTP errors (404, 500, etc.)
# Query: Define query parameters with validation and documentation
# status: HTTP status code constants (status.HTTP_404_NOT_FOUND, etc.)

# SQLAlchemy for database operations
from sqlalchemy.orm import Session
# Session: Database connection/transaction

# Python typing for type hints
from typing import Optional, List
# Optional[str]: Can be string or None
# List[JobRead]: List of JobRead objects

# Import database session dependency
from app.db.session import get_db
# get_db(): Creates database session, yields it, closes it automatically

# Import Job model (SQLAlchemy)
from app.db.models import Job
# Job: Database table model

# Import Pydantic schemas for validation
from app.schemas.job import JobCreate, JobUpdate, JobRead
# JobCreate: Validate data when creating jobs
# JobUpdate: Validate data when updating jobs
# JobRead: Format data when returning jobs


# =============================================================================
# ROUTER SETUP
# =============================================================================

router = APIRouter(
    prefix="/jobs",
    # All routes in this file will be prefixed with /jobs
    # Example: @router.get("/") becomes GET /jobs/
    #          @router.get("/{id}") becomes GET /jobs/{id}

    tags=["jobs"]
    # Organizes endpoints in API documentation
    # All routes in this file appear under "jobs" section in Swagger UI
)

"""
WHAT IS AN APIRouter?
====================
APIRouter is like a mini-application that groups related endpoints.

Benefits:
1. Organization: All job routes in one file
2. Reusability: Can use same router in multiple apps
3. Prefix: Avoid repeating /jobs in every route
4. Tags: Group in API documentation

Without router:
    @app.get("/jobs")
    @app.get("/jobs/{id}")
    @app.post("/jobs")
    # Scattered across files

With router:
    router = APIRouter(prefix="/jobs")
    @router.get("/")      # Becomes /jobs
    @router.get("/{id}")  # Becomes /jobs/{id}
    @router.post("/")     # Becomes /jobs
    # Clean and organized!
"""


# =============================================================================
# ENDPOINT 1: CREATE JOB (POST /jobs)
# =============================================================================

@router.post(
    "/",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job",
    description="Create a new job posting in the database. Generic job creation API"
)
def create_job(
    job_data: JobCreate,
    # Pydantic automatically validates incoming JSON against JobCreate schema
    # If validation fails, FastAPI returns 422 error with details
    # Example: {"title": "Engineer", "company": "Acme", ...}

    db: Session = Depends(get_db)
    # Dependency injection: FastAPI calls get_db() automatically
    # get_db() creates session, yields it here, closes it when done
    # We don't need to manually call db.close() - automatic cleanup!
) -> JobRead:
    """
    Create a new job posting in the database.

    REQUEST BODY (JSON):
    -------------------
    All fields from JobCreate schema:
    - title (required): Job title
    - company (optional): Company name
    - url (required): Job posting URL
    - description (optional): Full job description
    - location_city (optional): City
    - location_country (optional): Country
    - provider (required): Job board name (adzuna, jooble, etc.)
    - provider_job_id (optional): External ID from provider
    - status (optional): Defaults to "new"
    - match_score (optional): AI match score (0.0-1.0)
    - reject_reason (optional): Why job was rejected
    - apply_type (optional): How to apply (greenhouse, lever, etc.)

    RESPONSE:
    ---------
    Returns the created job with:
    - All provided fields
    - Auto-generated id
    - Auto-generated created_at
    - Auto-generated updated_at

    ERRORS:
    -------
    422 Unprocessable Entity: Validation error (missing required field, invalid type, etc.)
    500 Internal Server Error: Database error

    EXAMPLE REQUEST:
    ---------------
    POST /jobs
    {
        "title": "Senior Python Developer",
        "company": "Acme Corp",
        "url": "https://jobs.acme.com/python-dev",
        "description": "We are looking for...",
        "location_city": "San Francisco",
        "location_country": "United States",
        "provider": "adzuna",
        "provider_job_id": "12345"
    }

    EXAMPLE RESPONSE:
    ----------------
    201 Created
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
        "status": "new",
        "match_score": null,
        "reject_reason": null,
        "apply_type": null,
        "created_at": "2024-01-15T14:30:00",
        "updated_at": "2024-01-15T14:30:00"
    }
    """

    # Step 1: Convert Pydantic schema to dictionary
    # job_data.model_dump() extracts all field values as a dict
    # Example: {"title": "Engineer", "company": "Acme", ...}
    job_dict = job_data.model_dump()

    # Step 2: Create SQLAlchemy Job instance
    # **job_dict unpacks the dictionary as keyword arguments
    # Equivalent to: Job(title="Engineer", company="Acme", ...)
    new_job = Job(**job_dict)

    # Step 3: Add to database session (stages the change)
    # This doesn't save to database yet - just prepares the insert
    db.add(new_job)

    # Step 4: Commit the transaction (actually saves to database)
    # This executes: INSERT INTO jobs (title, company, ...) VALUES (...)
    # Database auto-generates: id, created_at, updated_at
    db.commit()

    # Step 5: Refresh to get auto-generated fields
    # Queries the database to get the new id, created_at, updated_at
    # Updates new_job object with these values
    db.refresh(new_job)

    # Step 6: Return the job
    # FastAPI automatically converts Job object to JSON using JobRead schema
    # JobRead.model_validate(new_job) happens automatically
    return new_job

    """
    WHAT HAPPENS BEHIND THE SCENES:
    ===============================

    1. User sends:
       POST /jobs
       {"title": "Engineer", ...}

    2. FastAPI validates with JobCreate:
       - Is title a string? ✓
       - Is url provided? ✓
       - All types correct? ✓

    3. Function creates Job instance:
       job = Job(title="Engineer", ...)

    4. SQLAlchemy generates SQL:
       INSERT INTO jobs (title, company, url, created_at, ...)
       VALUES ('Engineer', 'Acme', 'https://...', '2024-01-15 14:30:00', ...)

    5. Database executes SQL:
       - Assigns id = 1 (auto-increment)
       - Sets created_at = now()
       - Sets updated_at = now()

    6. Function returns job:
       return new_job

    7. FastAPI serializes with JobRead:
       {
         "id": 1,
         "title": "Engineer",
         "created_at": "2024-01-15T14:30:00",
         ...
       }

    8. User receives 201 Created response
    """


# =============================================================================
# ENDPOINT 2: LIST JOBS (GET /jobs)
# =============================================================================

@router.get(
    "/",
    response_model=List[JobRead],
    summary="List all jobs with optional filters",
    description="Retrieve a list of jobs from the database. Supports filtering by status, provider, country, and city."
)
def list_jobs(
    # Query parameters (from URL: ?status=new&country=Germany)
    # Optional[str] = None means: parameter is optional, defaults to None if not provided
    # Query(...) adds validation and documentation

    status: Optional[str] = Query(
        None,
        description="Filter by job status (new, approved_for_application, rejected, etc.)",
        examples=["new"]
    ),
    # Example: GET /jobs?status=new
    # Returns only jobs where status='new'

    provider: Optional[str] = Query(
        None,
        description="Filter by job provider (adzuna, jooble, indeed, etc.)",
        examples=["adzuna"]
    ),
    # Example: GET /jobs?provider=adzuna
    # Returns only jobs from Adzuna API

    country: Optional[str] = Query(
        None,
        description="Filter by country",
        examples=["Germany"]
    ),
    # Example: GET /jobs?country=Germany
    # Returns only jobs in Germany

    city: Optional[str] = Query(
        None,
        description="Filter by city",
        examples=["San Francisco"]
    ),
    # Example: GET /jobs?city=San%20Francisco
    # Returns only jobs in San Francisco

    skip: int = Query(
        0,
        ge=0,
        description="Number of records to skip (for pagination)",
        examples=[0]
    ),
    # Example: GET /jobs?skip=20
    # Skips first 20 jobs (for page 2 if limit=20)
    # ge=0 means: must be Greater than or Equal to 0

    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of records to return (for pagination)",
        examples=[100]
    ),
    # Example: GET /jobs?limit=50
    # Returns maximum 50 jobs
    # le=1000 means: must be Less than or Equal to 1000

    db: Session = Depends(get_db)
    # Database session injected automatically
) -> List[JobRead]:
    """
    List all jobs from the database with optional filtering and pagination.

    QUERY PARAMETERS:
    ----------------
    - status (optional): Filter by job status
    - provider (optional): Filter by job provider
    - country (optional): Filter by location country
    - city (optional): Filter by location city
    - skip (optional): Number of records to skip (default: 0)
    - limit (optional): Maximum records to return (default: 100, max: 1000)

    RESPONSE:
    --------
    Returns array of jobs matching the filters.
    Empty array [] if no jobs found.

    EXAMPLE REQUESTS:
    ----------------
    1. Get all jobs:
       GET /jobs

    2. Get jobs with status "new":
       GET /jobs?status=new

    3. Get jobs from Adzuna in Germany:
       GET /jobs?provider=adzuna&country=Germany

    4. Pagination (page 2, 20 per page):
       GET /jobs?skip=20&limit=20

    5. Multiple filters:
       GET /jobs?status=approved_for_application&country=United%20States&city=San%20Francisco

    EXAMPLE RESPONSE:
    ----------------
    200 OK
    [
        {
            "id": 1,
            "title": "Python Developer",
            "company": "Acme Corp",
            "status": "new",
            ...
        },
        {
            "id": 2,
            "title": "Data Scientist",
            "company": "Tech Inc",
            "status": "new",
            ...
        }
    ]
    """

    # Step 1: Start with base query
    # db.query(Job) prepares a SELECT statement
    # No filters applied yet - will select all jobs
    query = db.query(Job)

    # Step 2: Apply filters conditionally
    # Only add WHERE clauses for provided parameters

    if status:
        # If status parameter provided, filter by it
        # Adds: WHERE status = 'new' (or whatever value provided)
        query = query.filter(Job.status == status)

    if provider:
        # Adds: WHERE provider = 'adzuna'
        query = query.filter(Job.provider == provider)

    if country:
        # Adds: WHERE location_country = 'Germany'
        query = query.filter(Job.location_country == country)

    if city:
        # Adds: WHERE location_city = 'San Francisco'
        query = query.filter(Job.location_city == city)

    # Step 3: Apply pagination
    # offset(skip): Skip first N records
    # limit(limit): Return maximum N records
    # Adds: LIMIT 100 OFFSET 0
    query = query.offset(skip).limit(limit)

    # Step 4: Execute query and get results
    # .all() executes the SELECT query and returns list of Job objects
    # If no jobs found, returns empty list []
    jobs = query.all()

    # Step 5: Return jobs
    # FastAPI automatically converts list of Job objects to JSON
    # Each Job is serialized using JobRead schema
    return jobs

    """
    QUERY BUILDING EXAMPLE:
    ======================

    Request: GET /jobs?status=new&country=Germany&limit=10

    Query building steps:
    1. query = db.query(Job)
       → SELECT * FROM jobs

    2. query = query.filter(Job.status == "new")
       → SELECT * FROM jobs WHERE status = 'new'

    3. query = query.filter(Job.location_country == "Germany")
       → SELECT * FROM jobs WHERE status = 'new' AND location_country = 'Germany'

    4. query = query.offset(0).limit(10)
       → SELECT * FROM jobs WHERE status = 'new' AND location_country = 'Germany' LIMIT 10 OFFSET 0

    5. jobs = query.all()
       → Executes query, returns list of Job objects

    6. return jobs
       → FastAPI converts to JSON array

    PAGINATION EXAMPLE:
    ==================
    Total jobs: 150
    Page size: 20 jobs per page

    Page 1: GET /jobs?skip=0&limit=20   → Jobs 1-20
    Page 2: GET /jobs?skip=20&limit=20  → Jobs 21-40
    Page 3: GET /jobs?skip=40&limit=20  → Jobs 41-60
    ...
    Page 8: GET /jobs?skip=140&limit=20 → Jobs 141-150
    """


# =============================================================================
# ENDPOINT 3: GET SINGLE JOB (GET /jobs/{id})
# =============================================================================

@router.get(
    "/{id}",
    response_model=JobRead,
    summary="Get a single job by ID",
    description="Retrieve detailed information about a specific job."
)
def get_job(
    id: int,
    # Path parameter: extracted from URL
    # Example: GET /jobs/42 → id = 42
    # Must be an integer, FastAPI validates this automatically

    db: Session = Depends(get_db)
) -> JobRead:
    """
    Get a single job by its ID.

    PATH PARAMETER:
    --------------
    - id (required): Job ID (integer)

    RESPONSE:
    --------
    Returns job data if found.

    ERRORS:
    ------
    404 Not Found: Job with given ID doesn't exist

    EXAMPLE REQUEST:
    ---------------
    GET /jobs/1

    EXAMPLE RESPONSE (Success):
    --------------------------
    200 OK
    {
        "id": 1,
        "title": "Senior Python Developer",
        "company": "Acme Corp",
        "url": "https://jobs.acme.com/python-dev",
        ...
    }

    EXAMPLE RESPONSE (Not Found):
    ----------------------------
    404 Not Found
    {
        "detail": "Job with id 999 not found"
    }
    """

    # Step 1: Query database for job with matching ID
    # .filter(Job.id == id) adds: WHERE id = 1
    # .first() returns first matching row, or None if not found
    job = db.query(Job).filter(Job.id == id).first()

    # Step 2: Check if job exists
    if not job:
        # Job not found - raise 404 error
        # HTTPException stops execution and returns error response
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {id} not found"
        )

    # Step 3: Return job
    # FastAPI automatically converts Job object to JSON using JobRead schema
    return job

    """
    WHAT HAPPENS WITH HTTPException:
    ===============================

    Normal flow:
    1. User: GET /jobs/1
    2. Database: SELECT * FROM jobs WHERE id = 1
    3. Result: Job object
    4. Response: 200 OK with job data

    Not found flow:
    1. User: GET /jobs/999
    2. Database: SELECT * FROM jobs WHERE id = 999
    3. Result: None (no job with id 999)
    4. Code: if not job → raise HTTPException
    5. FastAPI: Catches exception, stops execution
    6. Response: 404 Not Found
       {
         "detail": "Job with id 999 not found"
       }

    ALTERNATIVE QUERY METHODS:
    =========================

    Method 1 (current):
        job = db.query(Job).filter(Job.id == id).first()

    Method 2:
        job = db.query(Job).get(id)  # Shortcut for primary key lookup

    Method 3 (SQLAlchemy 2.0 style):
        from sqlalchemy import select
        stmt = select(Job).where(Job.id == id)
        job = db.execute(stmt).scalar_one_or_none()

    We use Method 1 for consistency and clarity.
    """


# =============================================================================
# ENDPOINT 4: UPDATE JOB (PATCH /jobs/{id})
# =============================================================================

@router.patch(
    "/{id}",
    response_model=JobRead,
    summary="Update a job",
    description="Update one or more fields of an existing job. Only provided fields are updated."
)
def update_job(
    id: int,
    # Path parameter: job ID to update

    job_update: JobUpdate,
    # Request body: fields to update
    # All fields optional in JobUpdate, so partial updates are allowed

    db: Session = Depends(get_db)
) -> JobRead:
    """
    Update an existing job (partial update).

    PATH PARAMETER:
    --------------
    - id (required): Job ID to update

    REQUEST BODY:
    ------------
    Any fields from JobUpdate schema (all optional):
    - title, company, url, description
    - location_city, location_country
    - provider, provider_job_id
    - status, match_score, reject_reason, apply_type

    Only provided fields will be updated.
    Omitted fields remain unchanged.

    RESPONSE:
    --------
    Returns the updated job with all fields.

    ERRORS:
    ------
    404 Not Found: Job with given ID doesn't exist
    422 Unprocessable: Validation error (e.g., match_score > 1.0)

    EXAMPLE REQUESTS:
    ----------------
    1. Update status only:
       PATCH /jobs/1
       {"status": "approved_for_application"}

    2. Set match score:
       PATCH /jobs/1
       {"match_score": 0.85}

    3. Reject job with reason:
       PATCH /jobs/1
       {
           "status": "rejected",
           "reject_reason": "Location not in target countries"
       }

    4. Update multiple fields:
       PATCH /jobs/1
       {
           "company": "New Company Name",
           "location_city": "Berlin",
           "apply_type": "greenhouse"
       }

    EXAMPLE RESPONSE:
    ----------------
    200 OK
    {
        "id": 1,
        "title": "Senior Python Developer",  # Unchanged
        "company": "New Company Name",        # Updated
        "status": "approved_for_application", # Unchanged
        "location_city": "Berlin",            # Updated
        "apply_type": "greenhouse",           # Updated
        ...all other fields...
        "updated_at": "2024-01-15T16:00:00"  # Automatically updated!
    }
    """

    # Step 1: Find the existing job
    job = db.query(Job).filter(Job.id == id).first()

    # Step 2: Check if job exists
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {id} not found"
        )

    # Step 3: Get only the fields that were actually provided in the request
    # exclude_unset=True means: only include fields that user explicitly set
    # This allows partial updates!
    #
    # Example 1: User sends {"status": "approved"}
    #   update_data = {"status": "approved"}
    #   → Only status will be updated
    #
    # Example 2: User sends {"status": "approved", "match_score": 0.85}
    #   update_data = {"status": "approved", "match_score": 0.85}
    #   → Both fields will be updated
    update_data = job_update.model_dump(exclude_unset=True)

    # Step 4: Update each provided field
    # Loop through the update_data dictionary
    # For each field, set the corresponding attribute on the job object
    #
    # Example: update_data = {"status": "approved", "match_score": 0.85}
    #   Iteration 1: setattr(job, "status", "approved") → job.status = "approved"
    #   Iteration 2: setattr(job, "match_score", 0.85) → job.match_score = 0.85
    for field, value in update_data.items():
        setattr(job, field, value)

    # Step 5: Commit changes to database
    # This executes: UPDATE jobs SET status='approved', match_score=0.85, updated_at='...' WHERE id=1
    # Note: updated_at is automatically set by SQLAlchemy (onupdate=datetime.utcnow)
    db.commit()

    # Step 6: Refresh to get updated values
    # Ensures we have the latest updated_at timestamp
    db.refresh(job)

    # Step 7: Return updated job
    return job

    """
    PARTIAL UPDATE DEEP DIVE:
    ========================

    Why exclude_unset=True is critical:

    Without it (BAD):
        job_update = JobUpdate(status="approved")  # User only wants to update status
        update_data = job_update.model_dump()      # Gets ALL fields!
        # Result: {"title": None, "company": None, "status": "approved", ...}
        # Problem: Will set title=None, company=None (erasing data!) ❌

    With it (GOOD):
        job_update = JobUpdate(status="approved")
        update_data = job_update.model_dump(exclude_unset=True)
        # Result: {"status": "approved"}
        # Problem: Only updates status, leaves other fields unchanged ✓

    SETATTR EXPLANATION:
    ===================
    setattr(object, attribute_name, value) sets an attribute dynamically.

    These are equivalent:
        setattr(job, "status", "approved")
        job.status = "approved"

    Why use setattr? We don't know field names in advance (they come from loop).

    Manual version (without loop):
        if "status" in update_data:
            job.status = update_data["status"]
        if "match_score" in update_data:
            job.match_score = update_data["match_score"]
        if "company" in update_data:
            job.company = update_data["company"]
        # ... repeat for all 12 fields (verbose!)

    With setattr loop:
        for field, value in update_data.items():
            setattr(job, field, value)
        # Clean and handles any number of fields!

    AUTOMATIC updated_at:
    ====================
    In models.py, we defined:
        updated_at = Column(DateTime, onupdate=datetime.utcnow)

    This means SQLAlchemy automatically updates the timestamp on commit().
    We don't need to manually set it!
    """


# =============================================================================
# ENDPOINT 5: DELETE JOB (DELETE /jobs/{id})
# =============================================================================

@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a job",
    description="Permanently delete a job from the database."
)
def delete_job(
    id: int,
    # Path parameter: job ID to delete

    db: Session = Depends(get_db)
) -> dict:
    """
    Delete a job from the database.

    PATH PARAMETER:
    --------------
    - id (required): Job ID to delete

    RESPONSE:
    --------
    Returns success message if deleted.

    ERRORS:
    ------
    404 Not Found: Job with given ID doesn't exist

    EXAMPLE REQUEST:
    ---------------
    DELETE /jobs/1

    EXAMPLE RESPONSE (Success):
    --------------------------
    200 OK
    {
        "message": "Job deleted successfully",
        "id": 1
    }

    EXAMPLE RESPONSE (Not Found):
    ----------------------------
    404 Not Found
    {
        "detail": "Job with id 999 not found"
    }

    WARNING:
    -------
    This permanently deletes the job. There is no undo!
    Consider adding a "soft delete" (status='deleted') instead for production.
    """

    # Step 1: Find the job to delete
    job = db.query(Job).filter(Job.id == id).first()

    # Step 2: Check if job exists
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {id} not found"
        )

    # Step 3: Delete the job
    # Marks the job for deletion in the session
    db.delete(job)

    # Step 4: Commit the deletion
    # This executes: DELETE FROM jobs WHERE id = 1
    db.commit()

    # Step 5: Return success message
    # Note: We return a dict, not JobRead (job no longer exists!)
    return {
        "message": "Job deleted successfully",
        "id": id
    }

    """
    SOFT DELETE vs HARD DELETE:
    ==========================

    Hard Delete (current implementation):
        db.delete(job)
        db.commit()
        → Job is permanently removed from database
        → Cannot be recovered
        → Disk space is freed

    Soft Delete (recommended for production):
        job.status = "deleted"
        job.deleted_at = datetime.utcnow()
        db.commit()
        → Job still exists in database
        → Can be recovered if needed
        → Can track when/who deleted it
        → Queries should filter: WHERE status != 'deleted'

    Trade-offs:

    Hard Delete:
        Pros: Clean database, reclaim space
        Cons: No recovery, no audit trail, breaks foreign keys

    Soft Delete:
        Pros: Recoverable, audit trail, safe
        Cons: Database grows, queries more complex

    For this project, hard delete is fine for now. In production, consider:

    @router.delete("/{id}")
    def delete_job(id: int, db: Session = Depends(get_db)):
        job = db.query(Job).filter(Job.id == id).first()
        if not job:
            raise HTTPException(404, "Not found")

        # Soft delete
        job.status = "deleted"
        job.deleted_at = datetime.utcnow()
        db.commit()

        return {"message": "Job marked as deleted"}

    Then in list_jobs():
        query = db.query(Job).filter(Job.status != "deleted")
    """


# =============================================================================
# ENDPOINT 6: FETCH JOBS FROM ADZUNA (POST /jobs/fetch-from-adzuna)
# =============================================================================

@router.post(
    "/fetch-from-adzuna",
    status_code=status.HTTP_200_OK,
    summary="Fetch jobs from Adzuna API",
    description="Fetch jobs from Adzuna job board and store them in the database."
)
async def fetch_from_adzuna(
    query: str = Query(
        ...,
        description="Search query (e.g., 'python developer', 'data scientist')",
        examples=["python developer"]
    ),
    location: Optional[str] = Query(
        None,
        description="Location filter (e.g., 'New York', 'San Francisco')",
        examples=["New York"]
    ),
    country: str = Query(
        "eu",
        description="Country code (e.g., 'de', 'ch', 'gb') or region ('eu' for all EU countries, 'world' for global search)",
        examples=["eu"]
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number (starts at 1)",
        examples=[1]
    ),
    results_per_page: int = Query(
        20,
        ge=1,
        le=50,
        description="Results per page (max 50)",
        examples=[20]
    ),
    db: Session = Depends(get_db)
) -> dict:
    """
    Fetch jobs from Adzuna API and store them in the database.

    This endpoint:
    1. Calls Adzuna API with provided search parameters
    2. Normalizes job data to our schema
    3. Stores new jobs in database (deduplicates by URL)
    4. Returns statistics about the fetch operation

    QUERY PARAMETERS:
    ----------------
    - query (required): What to search for
    - location (optional): Where to search
    - country (optional): Country code (default: "us")
    - page (optional): Page number (default: 1)
    - results_per_page (optional): Jobs per page (default: 20, max: 50)

    RESPONSE:
    --------
    Returns statistics about fetched and stored jobs:
    {
        "success": true,
        "fetched_count": 20,      # Jobs fetched from Adzuna
        "stored_count": 15,       # New jobs stored in DB
        "duplicate_count": 5,     # Jobs skipped (already in DB)
        "jobs": [...]             # Array of normalized job data
    }

    ERRORS:
    ------
    - 500: Adzuna API error or database error
    - Error details included in response

    EXAMPLE REQUESTS:
    ----------------
    1. Basic search:
       POST /jobs/fetch-from-adzuna?query=python%20developer

    2. Search in specific location:
       POST /jobs/fetch-from-adzuna?query=data%20scientist&location=New%20York

    3. Search in UK:
       POST /jobs/fetch-from-adzuna?query=software%20engineer&country=gb

    4. Pagination:
       POST /jobs/fetch-from-adzuna?query=python&page=2&results_per_page=50

    EXAMPLE RESPONSE (Success):
    --------------------------
    200 OK
    {
        "success": true,
        "fetched_count": 20,
        "stored_count": 18,
        "duplicate_count": 2,
        "jobs": [
            {
                "provider": "adzuna",
                "external_id": "12345",
                "title": "Senior Python Developer",
                "company": "Tech Corp",
                "url": "https://...",
                ...
            },
            ...
        ]
    }

    EXAMPLE RESPONSE (Error):
    ------------------------
    200 OK (still returns 200, but success=false)
    {
        "success": false,
        "error": "Adzuna credentials not configured",
        "fetched_count": 0,
        "stored_count": 0,
        "duplicate_count": 0,
        "jobs": []
    }
    """
    from app.services.jobs_service import fetch_jobs_from_adzuna

    result = await fetch_jobs_from_adzuna(
        query=query,
        location=location,
        country=country,
        page=page,
        results_per_page=results_per_page,
        db=db
    )

    return result


# =============================================================================
# ENDPOINT 7: FETCH JOBS FROM JSEARCH (POST /jobs/fetch-from-jsearch)
# =============================================================================

@router.post(
    "/fetch-from-jsearch",
    status_code=status.HTTP_200_OK,
    summary="Fetch REMOTE jobs from JSearch API",
    description="Fetch global remote job opportunities from JSearch (via RapidAPI). This endpoint ONLY returns remote positions - use /fetch-from-adzuna for location-specific European jobs."
)
async def fetch_from_jsearch(
    query: str = Query(
        ...,
        description="Search query (e.g., 'python developer', 'data scientist', 'software engineer')",
        examples=["python developer"]
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number (starts at 1)",
        examples=[1]
    ),
    results_per_page: int = Query(
        10,
        ge=1,
        le=10,
        description="Results per page (max 10 per JSearch API)",
        examples=[10]
    ),
    date_posted: Optional[str] = Query(
        None,
        description="Filter by date posted: 'all', 'today', '3days', 'week', 'month'",
        examples=["week"]
    ),
    employment_types: Optional[str] = Query(
        None,
        description="Filter by employment types (comma-separated): 'FULLTIME', 'CONTRACTOR', 'PARTTIME', 'INTERN'",
        examples=["FULLTIME"]
    ),
    db: Session = Depends(get_db)
) -> dict:
    """
    Fetch REMOTE jobs from JSearch API and store them in the database.

    Strategic Focus: This endpoint is dedicated to global REMOTE job opportunities only.
    All results are automatically filtered for remote/work-from-home positions.

    For location-specific European jobs (Switzerland, Germany, Austria, Czech Republic),
    use POST /jobs/fetch-from-adzuna instead.

    This endpoint:
    1. Calls JSearch API (via RapidAPI) with remote_jobs_only=true
    2. Normalizes job data to our schema
    3. Stores new jobs in database (deduplicates by URL)
    4. Returns statistics about the fetch operation

    QUERY PARAMETERS:
    ----------------
    - query (required): What to search for (automatically appends "remote")
    - page (optional): Page number (default: 1)
    - results_per_page (optional): Jobs per page (default: 10, max: 10)
    - date_posted (optional): Filter by date ('today', '3days', 'week', 'month')
    - employment_types (optional): Filter by type ('FULLTIME', 'CONTRACTOR', 'PARTTIME', 'INTERN')

    RESPONSE:
    --------
    Returns statistics about fetched and stored jobs:
    {
        "success": true,
        "fetched_count": 10,      # Jobs fetched from JSearch
        "stored_count": 8,        # New jobs stored in DB
        "duplicate_count": 2,     # Jobs skipped (already in DB)
        "jobs": [...]             # Array of normalized job data
    }

    ERRORS:
    ------
    - 500: JSearch API error or database error
    - Error details included in response

    EXAMPLE REQUESTS:
    ----------------
    1. Basic remote job search:
       POST /jobs/fetch-from-jsearch?query=python%20developer

    2. Remote jobs from last week:
       POST /jobs/fetch-from-jsearch?query=data%20scientist&date_posted=week

    3. Full-time remote positions:
       POST /jobs/fetch-from-jsearch?query=software%20engineer&employment_types=FULLTIME

    4. Remote internships:
       POST /jobs/fetch-from-jsearch?query=software%20developer&employment_types=INTERN

    5. Remote contractor positions from last 3 days:
       POST /jobs/fetch-from-jsearch?query=frontend%20developer&employment_types=CONTRACTOR&date_posted=3days

    EXAMPLE RESPONSE (Success):
    --------------------------
    200 OK
    {
        "success": true,
        "fetched_count": 10,
        "stored_count": 9,
        "duplicate_count": 1,
        "jobs": [
            {
                "provider": "jsearch",
                "provider_job_id": "O_w3qMb5yrhpAgAAAAAAAAAA==",
                "title": "Senior Python Developer",
                "company": "Tech Corp",
                "url": "https://...",
                ...
            },
            ...
        ]
    }

    EXAMPLE RESPONSE (Error):
    ------------------------
    200 OK (still returns 200, but success=false)
    {
        "success": false,
        "error": "JSearch credentials not configured",
        "fetched_count": 0,
        "stored_count": 0,
        "duplicate_count": 0,
        "jobs": []
    }
    """
    from app.services.jobs_service import fetch_jobs_from_jsearch

    # Build kwargs for optional parameters
    kwargs = {}
    if date_posted:
        kwargs["date_posted"] = date_posted
    if employment_types:
        kwargs["employment_types"] = employment_types

    result = await fetch_jobs_from_jsearch(
        query=query,
        page=page,
        results_per_page=results_per_page,
        db=db,
        **kwargs
    )

    return result
