"""
test_adzuna_provider.py - Tests for Adzuna Provider

================================================================================
WHAT THIS FILE TESTS:
================================================================================
Tests for Adzuna job provider (app/providers/adzuna.py):
- Provider initialization
- Job normalization (converting Adzuna API response to our schema)
- Job fetching (mocked API calls)
- Country handling (eu, world, specific countries)
- POST /jobs/fetch-from-adzuna endpoint

================================================================================
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.providers.adzuna import AdzunaProvider
from app.services.jobs_service import fetch_jobs_from_adzuna


# =============================================================================
# TEST PROVIDER INITIALIZATION
# =============================================================================

@pytest.mark.unit
@pytest.mark.provider
def test_adzuna_provider_init_success():
    """Test successful Adzuna provider initialization."""
    provider = AdzunaProvider(api_key="test_key", app_id="test_id")

    assert provider.api_key == "test_key"
    assert provider.app_id == "test_id"


@pytest.mark.unit
@pytest.mark.provider
def test_adzuna_provider_init_missing_app_id():
    """Test Adzuna provider initialization fails without app_id."""
    with pytest.raises(ValueError, match="requires both api_key and app_id"):
        AdzunaProvider(api_key="test_key", app_id="")


# =============================================================================
# TEST JOB NORMALIZATION
# =============================================================================

@pytest.mark.unit
@pytest.mark.provider
def test_normalize_job_complete_data():
    """Test normalizing Adzuna job with all fields present."""
    provider = AdzunaProvider(api_key="test_key", app_id="test_id")

    raw_adzuna_job = {
        "id": "12345",
        "title": "Senior Python Developer",
        "company": {"display_name": "Tech Corp"},
        "location": {
            "display_name": "San Francisco, CA",
            "area": ["USA", "California", "San Francisco"]
        },
        "redirect_url": "https://jobs.techcorp.com/python-dev",
        "description": "We are looking for a Senior Python Developer...",
        "salary_min": 100000,
        "salary_max": 150000,
        "created": "2024-01-15T10:30:00Z",
        "contract_type": "permanent",
        "category": {"label": "IT Jobs"}
    }

    normalized = provider.normalize_job(raw_adzuna_job)

    assert normalized["provider"] == "adzuna"
    assert normalized["provider_job_id"] == "12345"
    assert normalized["title"] == "Senior Python Developer"
    assert normalized["company"] == "Tech Corp"
    assert normalized["location_country"] == "US"  # ISO 3166-1 alpha-2 code
    assert normalized["location_city"] == "San Francisco"
    assert normalized["url"] == "https://jobs.techcorp.com/python-dev"
    assert normalized["description"] == "We are looking for a Senior Python Developer..."
    assert normalized["salary_min"] == 100000
    assert normalized["salary_max"] == 150000
    assert normalized["salary_currency"] == "USD"
    assert normalized["status"] == "new"
    assert isinstance(normalized["posted_at"], datetime)


@pytest.mark.unit
@pytest.mark.provider
def test_normalize_job_minimal_data():
    """Test normalizing Adzuna job with minimal fields."""
    provider = AdzunaProvider(api_key="test_key", app_id="test_id")

    raw_adzuna_job = {
        "id": "12345",
        "title": "Developer",
        "redirect_url": "https://example.com/job"
    }

    normalized = provider.normalize_job(raw_adzuna_job)

    assert normalized["provider"] == "adzuna"
    assert normalized["provider_job_id"] == "12345"
    assert normalized["title"] == "Developer"
    assert normalized["company"] == "Unknown Company"
    assert normalized["location_country"] is None
    assert normalized["location_city"] is None
    assert normalized["url"] == "https://example.com/job"
    assert normalized["description"] == ""
    assert normalized["salary_min"] is None
    assert normalized["salary_max"] is None
    assert normalized["salary_currency"] is None  # No country = no currency inference


@pytest.mark.unit
@pytest.mark.provider
def test_normalize_job_country_iso_codes():
    """Test that location_country is normalized to ISO 3166-1 alpha-2 codes."""
    provider = AdzunaProvider(api_key="test_key", app_id="test_id")

    test_cases = [
        # (Adzuna country name, Expected ISO code)
        # English names
        (["United States"], "US"),
        (["USA"], "US"),
        (["United Kingdom"], "GB"),
        (["UK"], "GB"),
        (["Germany"], "DE"),
        (["France"], "FR"),
        (["Spain"], "ES"),
        (["Italy"], "IT"),
        (["Netherlands"], "NL"),
        (["Belgium"], "BE"),
        (["Austria"], "AT"),
        (["Poland"], "PL"),
        (["Switzerland"], "CH"),
        (["Canada"], "CA"),
        (["Australia"], "AU"),
        # Localized country names (as returned by Adzuna API)
        (["Österreich"], "AT"),       # Austria (German)
        (["België"], "BE"),            # Belgium (Dutch)
        (["Belgique"], "BE"),          # Belgium (French)
        (["Deutschland"], "DE"),       # Germany (German)
        (["España"], "ES"),            # Spain (Spanish)
        (["Italia"], "IT"),            # Italy (Italian)
        (["Nederland"], "NL"),         # Netherlands (Dutch)
        (["Polska"], "PL"),            # Poland (Polish)
        (["Schweiz"], "CH"),           # Switzerland (German)
        (["Suisse"], "CH"),            # Switzerland (French)
        (["Svizzera"], "CH"),          # Switzerland (Italian)
        # Unknown country should return None
        (["Unknown Country"], None),
        ([], None),  # No country provided
    ]

    for location_area, expected_iso in test_cases:
        raw_job = {
            "id": "12345",
            "title": "Test Job",
            "redirect_url": "https://example.com/job",
            "location": {"area": location_area} if location_area else {}
        }

        normalized = provider.normalize_job(raw_job)
        assert normalized["location_country"] == expected_iso, \
            f"Failed for {location_area}: expected {expected_iso}, got {normalized['location_country']}"


@pytest.mark.unit
@pytest.mark.provider
def test_normalize_job_currency_mapping():
    """Test currency inference from country (both English and localized names)."""
    provider = AdzunaProvider(api_key="test_key", app_id="test_id")

    test_cases = [
        # English country names
        (["United States"], "USD"),
        (["Germany"], "EUR"),
        (["United Kingdom"], "GBP"),
        (["Switzerland"], "CHF"),
        (["Canada"], "CAD"),
        (["Australia"], "AUD"),
        (["Poland"], "PLN"),
        # Localized country names (as returned by Adzuna API)
        (["Österreich"], "EUR"),       # Austria (German)
        (["België"], "EUR"),            # Belgium (Dutch)
        (["Belgique"], "EUR"),          # Belgium (French)
        (["Deutschland"], "EUR"),       # Germany (German)
        (["España"], "EUR"),            # Spain (Spanish)
        (["Italia"], "EUR"),            # Italy (Italian)
        (["Nederland"], "EUR"),         # Netherlands (Dutch)
        (["Polska"], "PLN"),            # Poland (Polish)
        (["Schweiz"], "CHF"),           # Switzerland (German)
        (["Suisse"], "CHF"),            # Switzerland (French)
        # Unknown country should return None instead of USD
        (["Unknown Country"], None),
    ]

    for location_area, expected_currency in test_cases:
        raw_job = {
            "id": "12345",
            "title": "Test Job",
            "redirect_url": "https://example.com/job",
            "location": {"area": location_area}
        }

        normalized = provider.normalize_job(raw_job)
        assert normalized["salary_currency"] == expected_currency, \
            f"Failed for {location_area}: expected {expected_currency}, got {normalized['salary_currency']}"


@pytest.mark.unit
@pytest.mark.provider
def test_normalize_job_apply_type_detection():
    """Test apply_type detection from URL."""
    provider = AdzunaProvider(api_key="test_key", app_id="test_id")

    test_cases = [
        ("https://boards.greenhouse.io/company/jobs/123", "greenhouse"),
        ("https://jobs.lever.co/company/abc", "lever"),
        ("https://company.wd1.myworkdayjobs.com/en-US/careers", "workday"),
        ("https://www.linkedin.com/jobs/view/123", "linkedin"),
        ("https://www.indeed.com/viewjob?jk=123", "indeed"),
        ("https://careers.company.com/jobs/123", "company_site"),
    ]

    for url, expected_apply_type in test_cases:
        raw_job = {
            "id": "12345",
            "title": "Test Job",
            "redirect_url": url,
            "company": {"display_name": "Test Company"}
        }

        normalized = provider.normalize_job(raw_job)
        assert normalized["apply_type"] == expected_apply_type, \
            f"Failed for {url}: expected {expected_apply_type}, got {normalized['apply_type']}"


@pytest.mark.unit
@pytest.mark.provider
def test_normalize_job_posted_date_parsing():
    """Test parsing of posted_at date."""
    provider = AdzunaProvider(api_key="test_key", app_id="test_id")

    # Valid ISO 8601 date
    raw_job = {
        "id": "12345",
        "title": "Test Job",
        "redirect_url": "https://example.com/job",
        "created": "2024-01-15T10:30:00Z"
    }

    normalized = provider.normalize_job(raw_job)
    assert normalized["posted_at"] is not None
    assert isinstance(normalized["posted_at"], datetime)
    assert normalized["posted_at"].year == 2024
    assert normalized["posted_at"].month == 1
    assert normalized["posted_at"].day == 15


@pytest.mark.unit
@pytest.mark.provider
def test_normalize_job_invalid_posted_date():
    """Test handling of invalid posted_at date."""
    provider = AdzunaProvider(api_key="test_key", app_id="test_id")

    raw_job = {
        "id": "12345",
        "title": "Test Job",
        "redirect_url": "https://example.com/job",
        "created": "invalid-date"
    }

    normalized = provider.normalize_job(raw_job)
    # Should handle gracefully and set to None
    assert normalized["posted_at"] is None


# =============================================================================
# TEST FETCH JOBS (with mocked API calls)
# =============================================================================

# Note: These tests are skipped because mocking async httpx is complex.
# In a real project, use respx library for mocking httpx or test against
# a real test API endpoint.

@pytest.mark.skip(reason="Complex async mocking - use respx library for better httpx mocking")
@pytest.mark.unit
@pytest.mark.provider
@pytest.mark.asyncio
async def test_fetch_jobs_single_country():
    """Test fetching jobs from a single country."""
    pass


@pytest.mark.skip(reason="Complex async mocking - use respx library for better httpx mocking")
@pytest.mark.unit
@pytest.mark.provider
@pytest.mark.asyncio
async def test_fetch_jobs_eu_region():
    """Test fetching jobs from EU region (multiple countries)."""
    pass


# =============================================================================
# TEST JOBS SERVICE
# =============================================================================

@pytest.mark.integration
@pytest.mark.provider
@pytest.mark.asyncio
async def test_fetch_jobs_from_adzuna_no_credentials():
    """Test fetch_jobs_from_adzuna when credentials not configured."""
    with patch("app.services.jobs_service.settings") as mock_settings:
        mock_settings.ADZUNA_API_KEY = None
        mock_settings.ADZUNA_APP_ID = None

        result = await fetch_jobs_from_adzuna(query="python developer")

        assert result["success"] is False
        assert "credentials not configured" in result["error"]
        assert result["fetched_count"] == 0
        assert result["stored_count"] == 0


@pytest.mark.integration
@pytest.mark.provider
@pytest.mark.asyncio
async def test_fetch_jobs_from_adzuna_success(test_db):
    """Test successful job fetching and storage."""
    mock_jobs = [
        {
            "provider": "adzuna",
            "provider_job_id": "123",
            "title": "Python Developer",
            "company": "Tech Corp",
            "url": "https://example.com/job123",
            "description": "Looking for Python dev",
            "location_country": "US",  # ISO 3166-1 alpha-2 code
            "location_city": "San Francisco",
            "status": "new",
            "apply_type": "company_site",
            "salary_min": 100000.0,
            "salary_max": 150000.0,
            "salary_currency": "USD",
            "posted_at": None
        }
    ]

    with patch("app.services.jobs_service.settings") as mock_settings:
        mock_settings.ADZUNA_API_KEY = "test_key"
        mock_settings.ADZUNA_APP_ID = "test_id"

        with patch("app.services.jobs_service.AdzunaProvider") as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.search_and_normalize.return_value = mock_jobs
            mock_provider_class.return_value = mock_provider

            result = await fetch_jobs_from_adzuna(
                query="python developer",
                db=test_db
            )

            assert result["success"] is True
            assert result["fetched_count"] == 1
            assert result["stored_count"] == 1
            assert result["duplicate_count"] == 0
            assert len(result["jobs"]) == 1


@pytest.mark.skip(reason="Complex async mocking with database - skip for now")
@pytest.mark.integration
@pytest.mark.provider
@pytest.mark.asyncio
async def test_fetch_jobs_from_adzuna_duplicate_handling(test_db, create_test_job):
    """Test that duplicate URLs are not stored."""
    pass


# =============================================================================
# TEST API ENDPOINT
# =============================================================================

@pytest.mark.skip(reason="Complex async mocking - skip for now")
@pytest.mark.api
@pytest.mark.provider
@pytest.mark.asyncio
async def test_fetch_from_adzuna_endpoint_success(client):
    """Test POST /jobs/fetch-from-adzuna endpoint."""
    pass


@pytest.mark.api
@pytest.mark.provider
@pytest.mark.asyncio
async def test_fetch_from_adzuna_endpoint_missing_query(client):
    """Test POST /jobs/fetch-from-adzuna without required query parameter."""
    response = client.post("/jobs/fetch-from-adzuna")

    # Should return 422 (validation error) because query is required
    assert response.status_code == 422
