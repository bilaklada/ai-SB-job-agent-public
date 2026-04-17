"""
Jobs Service

Business logic for fetching, storing, and managing jobs from external providers.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.providers.adzuna import AdzunaProvider
from app.providers.jsearch import JSearchProvider
from app.db.models import Job
from app.config import settings


async def fetch_jobs_from_adzuna(
    query: str,
    location: Optional[str] = None,
    country: str = "eu",
    page: int = 1,
    results_per_page: int = 20,
    db: Optional[Session] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Fetch jobs from Adzuna and optionally store them in the database.

    This function:
    1. Calls Adzuna API to fetch jobs
    2. Normalizes the job data to our schema
    3. If db session provided, stores new jobs (deduplicates by URL)
    4. Returns statistics and fetched jobs

    Args:
        query: Search query (e.g., "python developer")
        location: Location filter (e.g., "New York")
        country: Country code or region:
            - "us", "de", "ch", ...
            - "eu"  → all EU countries
            - "world" → almost all countries
            (default: "eu")
        page: Page number (default: 1)
        results_per_page: Jobs per page (default: 20, max: 50)
        db: Database session (optional - if None, doesn't store jobs)
        **kwargs: Additional Adzuna parameters (sort_by, salary_min, etc.)

    Returns:
        Dictionary with:
        {
            "success": bool,
            "fetched_count": int,     # How many jobs fetched from API
            "stored_count": int,      # How many new jobs stored in DB
            "duplicate_count": int,   # How many were duplicates (skipped)
            "jobs": List[Dict],       # Normalized job data
            "error": Optional[str]    # Error message if failed
        }

    Example:
        # Fetch only (no storage)
        result = await fetch_jobs_from_adzuna("python developer")

        # Fetch and store
        with SessionLocal() as db:
            result = await fetch_jobs_from_adzuna(
                query="python developer",
                location="New York",
                db=db
            )
            print(f"Stored {result['stored_count']} new jobs")
    """
    try:
        # Validate Adzuna credentials
        if not settings.ADZUNA_API_KEY or not settings.ADZUNA_APP_ID:
            return {
                "success": False,
                "error": "Adzuna credentials not configured. Set ADZUNA_API_KEY and ADZUNA_APP_ID in .env",
                "fetched_count": 0,
                "stored_count": 0,
                "duplicate_count": 0,
                "jobs": []
            }

        # Initialize Adzuna provider
        provider = AdzunaProvider(
            api_key=settings.ADZUNA_API_KEY,
            app_id=settings.ADZUNA_APP_ID
        )

        # Fetch and normalize jobs
        normalized_jobs = await provider.search_and_normalize(
            query=query,
            location=location,
            country=country,
            page=page,
            results_per_page=results_per_page,
            **kwargs
        )

        fetched_count = len(normalized_jobs)
        stored_count = 0
        duplicate_count = 0

        # Store jobs in database if session provided
        if db is not None:
            for job_data in normalized_jobs:
                try:
                    # Create Job model instance
                    # Map normalized fields to Job model columns
                    job = Job(
                        provider=job_data["provider"],
                        provider_job_id=job_data["provider_job_id"],  # Correct field name
                        title=job_data["title"],
                        company=job_data["company"],
                        location_city=job_data.get("location_city"),       # Correct field name
                        location_country=job_data.get("location_country"), # Correct field name
                        url=job_data["url"],
                        description=job_data["description"],  # Correct field name
                        salary_min=job_data.get("salary_min"),
                        salary_max=job_data.get("salary_max"),
                        salary_currency=job_data.get("salary_currency"),
                        posted_at=job_data.get("posted_at"),
                        apply_type=job_data.get("apply_type", "other"),
                        status=job_data.get("status", "new"),  # Use status from normalized data
                    )

                    db.add(job)
                    db.commit()
                    db.refresh(job)
                    stored_count += 1

                except IntegrityError:
                    # Duplicate URL (unique constraint violation)
                    db.rollback()
                    duplicate_count += 1
                except Exception as e:
                    # Other database errors
                    db.rollback()
                    print(f"Error storing job: {e}")

        return {
            "success": True,
            "fetched_count": fetched_count,
            "stored_count": stored_count,
            "duplicate_count": duplicate_count,
            "jobs": normalized_jobs,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "fetched_count": 0,
            "stored_count": 0,
            "duplicate_count": 0,
            "jobs": []
        }


async def fetch_jobs_from_jsearch(
    query: str,
    page: int = 1,
    results_per_page: int = 10,
    db: Optional[Session] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Fetch REMOTE jobs from JSearch and optionally store them in the database.

    Strategic Focus: JSearch is used EXCLUSIVELY for global remote job opportunities.
    Location and country parameters are NOT supported. Use fetch_jobs_from_adzuna()
    for location-specific European job searches.

    This function:
    1. Calls JSearch API (via RapidAPI) to fetch remote jobs
    2. Normalizes the job data to our schema
    3. If db session provided, stores new jobs (deduplicates by URL)
    4. Returns statistics and fetched jobs

    Args:
        query: Search query (e.g., "python developer", "data scientist", "software engineer")
        page: Page number (default: 1)
        results_per_page: Jobs per page (default: 10, max: 10 per JSearch API)
        db: Database session (optional - if None, doesn't store jobs)
        **kwargs: Additional optional filters:
            - date_posted: "all", "today", "3days", "week", "month"
            - employment_types: "FULLTIME", "CONTRACTOR", "PARTTIME", "INTERN"
            - job_requirements: "under_3_years_experience", "more_than_3_years_experience", etc.

    Returns:
        Dictionary with:
        {
            "success": bool,
            "fetched_count": int,     # How many remote jobs fetched from API
            "stored_count": int,      # How many new jobs stored in DB
            "duplicate_count": int,   # How many were duplicates (skipped)
            "jobs": List[Dict],       # Normalized job data (all remote)
            "error": Optional[str]    # Error message if failed
        }

    Example:
        # Fetch remote jobs only (no storage)
        result = await fetch_jobs_from_jsearch("python developer")

        # Fetch and store remote full-time jobs from last week
        with SessionLocal() as db:
            result = await fetch_jobs_from_jsearch(
                query="python developer",
                db=db,
                date_posted="week",
                employment_types="FULLTIME"
            )
            print(f"Stored {result['stored_count']} remote jobs")
    """
    try:
        # Validate JSearch credentials
        if not settings.JSEARCH_API_KEY:
            return {
                "success": False,
                "error": "JSearch credentials not configured. Set JSEARCH_API_KEY in .env",
                "fetched_count": 0,
                "stored_count": 0,
                "duplicate_count": 0,
                "jobs": []
            }

        # Initialize JSearch provider
        provider = JSearchProvider(api_key=settings.JSEARCH_API_KEY)

        # Fetch and normalize remote jobs only
        normalized_jobs = await provider.search_and_normalize(
            query=query,
            page=page,
            results_per_page=results_per_page,
            **kwargs
        )

        fetched_count = len(normalized_jobs)
        stored_count = 0
        duplicate_count = 0

        # Store jobs in database if session provided
        if db is not None:
            for job_data in normalized_jobs:
                try:
                    # Create Job model instance
                    # Map normalized fields to Job model columns
                    job = Job(
                        provider=job_data["provider"],
                        provider_job_id=job_data["provider_job_id"],
                        title=job_data["title"],
                        company=job_data["company"],
                        location_city=job_data.get("location_city"),
                        location_country=job_data.get("location_country"),
                        url=job_data["url"],
                        description=job_data["description"],
                        salary_min=job_data.get("salary_min"),
                        salary_max=job_data.get("salary_max"),
                        salary_currency=job_data.get("salary_currency"),
                        posted_at=job_data.get("posted_at"),
                        apply_type=job_data.get("apply_type", "other"),
                        status=job_data.get("status", "new"),
                    )

                    db.add(job)
                    db.commit()
                    db.refresh(job)
                    stored_count += 1

                except IntegrityError:
                    # Duplicate URL (unique constraint violation)
                    db.rollback()
                    duplicate_count += 1
                except Exception as e:
                    # Other database errors
                    db.rollback()
                    print(f"Error storing job: {e}")

        return {
            "success": True,
            "fetched_count": fetched_count,
            "stored_count": stored_count,
            "duplicate_count": duplicate_count,
            "jobs": normalized_jobs,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "fetched_count": 0,
            "stored_count": 0,
            "duplicate_count": 0,
            "jobs": []
        }


def get_job_by_status(
    db: Session,
    status: str = "new",
    limit: int = 1
) -> Optional[Job]:
    """
    Fetch job(s) from database by status, prioritizing OLDEST jobs first.

    This function queries the database to get jobs with a specific status,
    ordered by creation date (OLDEST first) for strategic reasons:

    1. Anti-bot behavior: Avoid applying immediately to brand new postings
    2. Priority management: Older jobs are closer to closing (higher urgency)
    3. Natural behavior: Mimics human browsing patterns

    Args:
        db: Database session
        status: Job status to filter by (default: "new")
        limit: Maximum number of jobs to return (default: 1)

    Returns:
        Single Job object if limit=1, or list of Job objects if limit > 1
        Returns None if no jobs found (when limit=1) or empty list (when limit > 1)

    Example:
        # Get oldest job with status='new' (highest priority)
        job = get_job_by_status(db, status="new")
        if job:
            print(f"Found job: {job.title} at {job.company}")
            print(f"Posted to DB: {job.created_at}")
        else:
            print("No new jobs available")

        # Get 10 oldest approved jobs
        jobs = get_job_by_status(db, status="approved_for_application", limit=10)
        print(f"Found {len(jobs)} approved jobs, oldest first")
    """
    # Order by created_at ascending (oldest first) - strategic priority
    query = db.query(Job).filter(Job.status == status).order_by(Job.created_at.asc())

    if limit == 1:
        return query.first()
    else:
        return query.limit(limit).all()


async def fetch_and_store_jobs_from_all_providers(
    query: str,
    location: Optional[str] = None,
    country: str = "eu",
    db: Session = None,
) -> Dict[str, Any]:
    """
    Fetch jobs from all configured providers and store them.

    This is a convenience function that will eventually support multiple providers.
    For now, it only uses Adzuna.

    Args:
        query: Search query
        location: Location filter
        country: Country code
        db: Database session

    Returns:
        Dictionary with aggregated results from all providers
    """
    results = {
        "adzuna": await fetch_jobs_from_adzuna(
            query=query,
            location=location,
            country=country,
            db=db
        )
    }

    # Future: Add Jooble, Indeed, etc.
    # results["jooble"] = await fetch_jobs_from_jooble(...)

    # Aggregate statistics
    total_fetched = sum(r["fetched_count"] for r in results.values())
    total_stored = sum(r["stored_count"] for r in results.values())
    total_duplicates = sum(r["duplicate_count"] for r in results.values())

    return {
        "success": all(r["success"] for r in results.values()),
        "total_fetched": total_fetched,
        "total_stored": total_stored,
        "total_duplicates": total_duplicates,
        "by_provider": results
    }
