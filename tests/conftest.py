"""
conftest.py - Pytest Configuration and Fixtures

================================================================================
WHAT THIS FILE DOES:
================================================================================
This file provides reusable test fixtures for all test files.

Fixtures are functions that pytest runs before/after tests to set up and
tear down test environments.

WHY CONFTEST.PY?
================
- conftest.py is automatically discovered by pytest
- Fixtures defined here are available to all test files
- No need to import - pytest finds them automatically
- Centralized test configuration

FIXTURES PROVIDED:
==================
1. test_db_engine - Creates test database engine
2. TestSessionLocal - Test database session factory
3. test_db - Database session for each test (auto-rollback)
4. override_get_db - Override app's get_db dependency
5. client - FastAPI TestClient for API testing
6. sample_job_data - Sample job data for creating test jobs

================================================================================
"""

import os
import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Import app components
from app.main import app
from app.db.session import Base, get_db
from app.db.models import Job


# =============================================================================
# TEST DATABASE CONFIGURATION
# =============================================================================

# Use in-memory SQLite for fast tests (no I/O overhead)
# Alternative: Use separate test PostgreSQL database for integration tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def test_db_engine():
    """
    Create a test database engine (session scope - created once per test run).

    WHY SQLite IN-MEMORY?
    ---------------------
    - Fast: No disk I/O
    - Isolated: Each test run gets fresh database
    - No cleanup needed: Database disappears when tests finish
    - Perfect for unit tests

    WHY SESSION SCOPE?
    ------------------
    - Created once per test session (all tests)
    - Faster than creating new engine for each test
    - Shared across all tests

    PRODUCTION vs TEST:
    -------------------
    Production: PostgreSQL (app/config.py DATABASE_URL)
    Testing: SQLite in-memory (fast, isolated)
    """
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite specific
        poolclass=StaticPool,  # Keep connection alive in memory
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup: Drop all tables after tests
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="session")
def TestSessionLocal(test_db_engine):
    """
    Create a test database session factory (session scope).

    WHAT IS A SESSION FACTORY?
    ---------------------------
    It's a factory that creates database sessions (connections).

    Similar to app/db/session.py SessionLocal, but for testing.
    """
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )


@pytest.fixture(scope="function")
def test_db(test_db_engine, TestSessionLocal) -> Generator[Session, None, None]:
    """
    Provide a test database session for each test (function scope).

    WHY FUNCTION SCOPE?
    -------------------
    - Each test gets a fresh session
    - Tests are isolated from each other
    - Changes in one test don't affect others

    HOW AUTO-ROLLBACK WORKS:
    -------------------------
    1. Test starts: Create connection and begin transaction
    2. Test runs: Make changes to database
    3. Test ends: Rollback transaction (undo all changes)
    4. Next test: Starts with clean state

    This makes tests:
    - Fast (no need to delete data)
    - Isolated (tests don't interfere)
    - Reliable (same state every time)
    """
    # Create a connection
    connection = test_db_engine.connect()
    # Begin a transaction
    transaction = connection.begin()
    # Create session bound to this connection
    session = TestSessionLocal(bind=connection)

    yield session

    # After test completes, rollback the transaction
    # This undoes all changes made during the test
    session.close()
    transaction.rollback()
    connection.close()


# =============================================================================
# FASTAPI TEST CLIENT FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def client(test_db) -> Generator[TestClient, None, None]:
    """
    Provide a FastAPI TestClient for testing API endpoints.

    WHAT IS TestClient?
    -------------------
    - Makes HTTP requests to your FastAPI app without starting a server
    - No network overhead (in-process testing)
    - Same interface as httpx.Client

    HOW IT WORKS:
    -------------
    1. Overrides app's get_db() dependency to use test database
    2. Creates TestClient instance
    3. You can make requests: client.get("/jobs"), client.post("/jobs", ...)
    4. After test, restores original dependencies

    EXAMPLE USAGE IN TESTS:
    ------------------------
    def test_create_job(client):
        response = client.post("/jobs", json={"title": "Engineer", ...})
        assert response.status_code == 201
        assert response.json()["title"] == "Engineer"
    """

    # Override the get_db dependency to use test database
    def override_get_db():
        try:
            yield test_db
        finally:
            pass  # test_db fixture handles cleanup

    app.dependency_overrides[get_db] = override_get_db

    # Create test client
    with TestClient(app) as test_client:
        yield test_client

    # Cleanup: Remove dependency override
    app.dependency_overrides.clear()


# =============================================================================
# DATA FIXTURES (Sample Test Data)
# =============================================================================

@pytest.fixture
def sample_job_data() -> dict:
    """
    Provide sample job data for creating test jobs.

    WHY THIS FIXTURE?
    -----------------
    - DRY: Don't repeat job data in every test
    - Consistency: All tests use same valid structure
    - Maintainability: Update once, affects all tests

    USAGE IN TESTS:
    ---------------
    def test_create_job(client, sample_job_data):
        response = client.post("/jobs", json=sample_job_data)
        assert response.status_code == 201

    def test_create_multiple_jobs(client, sample_job_data):
        # Customize for each test
        job1_data = {**sample_job_data, "title": "Job 1"}
        job2_data = {**sample_job_data, "title": "Job 2"}
        ...
    """
    return {
        "title": "Senior Python Developer",
        "company": "Acme Corp",
        "url": "https://jobs.example.com/python-dev-123",
        "description": "We are looking for a Senior Python Developer with 5+ years experience",
        "location_city": "San Francisco",
        "location_country": "United States",
        "provider": "adzuna",
        "provider_job_id": "12345",
        "status": "new",
        "match_score": None,
        "reject_reason": None,
        "apply_type": None,
        "salary_min": 100000.0,
        "salary_max": 150000.0,
        "salary_currency": "USD",
        "posted_at": None
    }


@pytest.fixture
def create_test_job(test_db, sample_job_data):
    """
    Factory fixture to create test jobs in the database.

    WHY A FACTORY FIXTURE?
    ----------------------
    - Easily create multiple jobs with different data
    - Returns a function you can call multiple times
    - Handles database operations automatically

    USAGE IN TESTS:
    ---------------
    def test_list_jobs(test_db, create_test_job):
        # Create 3 test jobs
        job1 = create_test_job(title="Job 1", status="new")
        job2 = create_test_job(title="Job 2", status="approved_for_application")
        job3 = create_test_job(title="Job 3", status="rejected")

        # Now test your logic
        new_jobs = test_db.query(Job).filter(Job.status == "new").all()
        assert len(new_jobs) == 1
    """
    import uuid

    def _create_job(**kwargs):
        """Create a job with custom fields."""
        # Start with sample data
        job_data = sample_job_data.copy()
        # Override with any provided kwargs
        job_data.update(kwargs)

        # Ensure unique URL if not provided
        if "url" not in kwargs:
            job_data["url"] = f"https://jobs.example.com/job-{uuid.uuid4()}"

        # Create Job instance
        job = Job(**job_data)
        # Add to database
        test_db.add(job)
        test_db.commit()
        test_db.refresh(job)
        return job

    return _create_job


# =============================================================================
# FIXTURE USAGE PATTERNS
# =============================================================================

"""
PATTERN 1: Simple API test
---------------------------
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


PATTERN 2: Test CRUD operations
--------------------------------
def test_create_and_get_job(client, sample_job_data):
    # Create job
    create_response = client.post("/jobs", json=sample_job_data)
    assert create_response.status_code == 201
    job_id = create_response.json()["id"]

    # Get job
    get_response = client.get(f"/jobs/{job_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == sample_job_data["title"]


PATTERN 3: Test database operations
------------------------------------
def test_job_model(test_db, sample_job_data):
    # Create job directly in database
    job = Job(**sample_job_data)
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)

    # Verify
    assert job.id is not None
    assert job.status == "new"


PATTERN 4: Test with multiple jobs
-----------------------------------
def test_filter_jobs(client, create_test_job):
    # Create test data
    create_test_job(title="Job 1", status="new")
    create_test_job(title="Job 2", status="approved_for_application")
    create_test_job(title="Job 3", status="rejected")

    # Test filtering
    response = client.get("/jobs?status=new")
    assert len(response.json()) == 1


PATTERN 5: Test validation errors
----------------------------------
def test_invalid_job_data(client):
    invalid_data = {"title": ""}  # Empty title (invalid)
    response = client.post("/jobs", json=invalid_data)
    assert response.status_code == 422  # Validation error
"""
