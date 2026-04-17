"""
JSearch Job Provider

Adapter for fetching jobs from JSearch API via RapidAPI.
Documentation: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx

from app.providers.base import BaseJobProvider


class JSearchProvider(BaseJobProvider):
    """
    JSearch job board API client (via RapidAPI) - REMOTE JOBS ONLY.

    Strategic Focus: This provider is exclusively used for fetching global remote
    job opportunities. It does NOT handle location-specific European positions
    (use AdzunaProvider for that).

    JSearch aggregates remote job listings from Google for Jobs, covering major
    platforms like LinkedIn, Indeed, Glassdoor, and 30+ other sources worldwide.

    API Limits:
    - Free tier: 200 calls/month, 1000/hour rate limit
    - Pro tier: 10,000 calls/month, 5 req/sec
    - Ultra tier: 50,000 calls/month, 10 req/sec

    Authentication:
    - RapidAPI key required
    - Passed via X-RapidAPI-Key header

    Note: All requests automatically enforce remote_jobs_only=true filter.
    """

    BASE_URL = "https://jsearch.p.rapidapi.com"
    RAPIDAPI_HOST = "jsearch.p.rapidapi.com"

    def __init__(self, api_key: str):
        """
        Initialize JSearch provider.

        Args:
            api_key: RapidAPI key for JSearch API
        """
        super().__init__(api_key=api_key)

        if not api_key:
            raise ValueError("JSearch requires RapidAPI key")

    async def fetch_jobs(
        self,
        query: str,
        page: int = 1,
        results_per_page: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch REMOTE (USA/UK) jobs from JSearch API.

        API Endpoint: GET /search

        Strategic Focus: This provider ONLY fetches remote/work-from-home positions.
        Location and country parameters are NOT supported - use AdzunaProvider for
        location-specific European job searches.

        Args:
            query: What to search for (e.g., "python developer", "data scientist", "software engineer")
            page: Page number (starts at 1)
            results_per_page: Results per page (default 10, max 10 per JSearch API)
            **kwargs: Additional optional filters:
                - date_posted: "all", "today", "3days", "week", "month"
                - employment_types: "FULLTIME", "CONTRACTOR", "PARTTIME", "INTERN"
                - job_requirements: "under_3_years_experience", "more_than_3_years_experience", etc.

        Returns:
            List of raw job dictionaries from JSearch API (remote jobs only)

        Raises:
            httpx.HTTPError: If API call fails
        """
        # Build search query for remote positions
        # Always search for "remote" or "work from home" jobs globally
        search_query = f"{query} remote"

        # Prepare request parameters
        params = {
            "query": search_query,
            "page": str(page),
            "num_pages": "1",  # Number of pages to fetch (always 1 per call)
            "remote_jobs_only": "true",  # MANDATORY: Always enforce remote-only filter
        }

        # Add optional parameters
        if "date_posted" in kwargs:
            # Options: "all", "today", "3days", "week", "month"
            params["date_posted"] = kwargs["date_posted"]

        if "employment_types" in kwargs:
            # Options: "FULLTIME", "CONTRACTOR", "PARTTIME", "INTERN"
            # Can be comma-separated: "FULLTIME,PARTTIME"
            params["employment_types"] = kwargs["employment_types"]

        if "job_requirements" in kwargs:
            # Options: "under_3_years_experience", "more_than_3_years_experience", "no_experience", "no_degree"
            params["job_requirements"] = kwargs["job_requirements"]

        # Prepare headers for RapidAPI
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.RAPIDAPI_HOST,
        }

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.BASE_URL}/search"
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()

            # JSearch returns jobs in "data" array
            jobs = data.get("data", [])

            # CRITICAL: Post-process to ensure ONLY truly remote jobs
            # Even with remote_jobs_only=true, API may return non-remote jobs
            remote_jobs = []
            for job in jobs:
                if self._is_truly_remote(job):
                    remote_jobs.append(job)

            return remote_jobs

    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize JSearch job data to our standard format.

        JSearch API Response Structure:
        {
            "job_id": "O_w3qMb5yrhpAgAAAAAAAAAA==",
            "employer_name": "Tech Corp",
            "employer_logo": "https://...",
            "job_title": "Senior Python Developer",
            "job_description": "Full job description...",
            "job_employment_type": "FULLTIME",
            "job_posted_at_datetime_utc": "2024-01-15T10:30:00.000Z",
            "job_offer_expiration_datetime_utc": "2024-02-15T10:30:00.000Z",
            "job_city": "San Francisco",
            "job_state": "CA",
            "job_country": "US",
            "job_latitude": 37.7749,
            "job_longitude": -122.4194,
            "job_required_experience": {
                "no_experience_required": false,
                "required_experience_in_months": 60,
                "experience_mentioned": true
            },
            "job_required_education": {
                "postgraduate_degree": false,
                "professional_school": false,
                "high_school": false,
                "associates_degree": false,
                "bachelors_degree": true
            },
            "job_highlights": {
                "Qualifications": ["5+ years Python", "BS in CS"],
                "Responsibilities": ["Design systems", "Lead team"]
            },
            "apply_options": [
                {
                    "publisher": "LinkedIn",
                    "apply_link": "https://linkedin.com/jobs/view/...",
                    "is_direct": false
                }
            ],
            "job_min_salary": 120000,
            "job_max_salary": 180000,
            "job_salary_currency": "USD",
            "job_salary_period": "YEAR"
        }

        Args:
            raw_job: Raw job data from JSearch API

        Returns:
            Normalized job dictionary matching our schema
        """
        # Extract basic fields
        job_id = raw_job.get("job_id", "")
        title = raw_job.get("job_title", "")
        company = raw_job.get("employer_name", "Unknown Company")
        description = raw_job.get("job_description", "")

        # REMOTE JOBS ONLY: Always set location to "REMOTE"
        # JSearch is exclusively used for remote positions, so we override
        # any location data from the API and consistently mark as "REMOTE"
        city = "Remote"
        country = "USA/UK (Remote)"
        location_raw = "REMOTE"

        # Extract salary data
        salary_min = raw_job.get("job_min_salary")
        salary_max = raw_job.get("job_max_salary")
        salary_currency = raw_job.get("job_salary_currency", "USD")

        # Parse posted date
        posted_at_str = raw_job.get("job_posted_at_datetime_utc")
        posted_at = None
        if posted_at_str:
            try:
                # JSearch uses ISO 8601 format with .000Z
                posted_at = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                posted_at = None

        # Extract application URL
        # JSearch provides multiple apply_options, prioritize direct links
        apply_options = raw_job.get("apply_options", [])
        url = ""
        apply_type = "other"

        if apply_options:
            # Try to find a direct application link first
            direct_link = next(
                (opt for opt in apply_options if opt.get("is_direct")),
                None
            )
            if direct_link:
                url = direct_link.get("apply_link", "")
            else:
                # Fall back to first available link
                url = apply_options[0].get("apply_link", "")

            # Determine apply type from URL
            if "greenhouse.io" in url:
                apply_type = "greenhouse"
            elif "lever.co" in url:
                apply_type = "lever"
            elif "workday.com" in url or "myworkdayjobs.com" in url:
                apply_type = "workday"
            elif "linkedin.com" in url:
                apply_type = "linkedin"
            elif "indeed.com" in url:
                apply_type = "indeed"
            elif any(opt.get("is_direct") for opt in apply_options):
                apply_type = "company_site"

        # Build normalized job dictionary
        normalized = {
            "provider": "jsearch",
            "provider_job_id": str(job_id),
            "title": title,
            "company": company,
            "location_raw": location_raw,
            "location_country": country,
            "location_city": city,
            "url": url,
            "description": description,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "posted_at": posted_at,
            "apply_type": apply_type,
            "status": "new",  # All new jobs start with "new" status
        }

        return normalized

    def _is_truly_remote(self, job: Dict[str, Any]) -> bool:
        """
        Validate that a job is truly remote/work-from-home.

        JSearch API may return non-remote jobs even with remote_jobs_only=true.
        This function performs strict validation to ensure only genuine remote positions
        are stored in the database.

        Validation Strategy:
        1. Check job_is_remote field (primary indicator)
        2. Check title for remote keywords
        3. Check description for remote/work-from-home mentions
        4. Reject if location indicates on-site requirement

        Args:
            job: Raw job data from JSearch API

        Returns:
            True if job is truly remote, False otherwise
        """
        # Primary check: job_is_remote field (if available)
        is_remote = job.get("job_is_remote")
        if is_remote is True:
            return True
        if is_remote is False:
            return False

        # Secondary check: Title and description keywords
        title = (job.get("job_title") or "").lower()
        description = (job.get("job_description") or "").lower()

        # Remote indicators in title (high confidence)
        remote_title_keywords = [
            "remote",
            "work from home",
            "wfh",
            "telecommute",
            "virtual",
            "distributed",
            "home-based",
        ]

        for keyword in remote_title_keywords:
            if keyword in title:
                return True

        # Check description for strong remote indicators
        remote_description_keywords = [
            "fully remote",
            "100% remote",
            "work from anywhere",
            "remote position",
            "remote role",
            "remote opportunity",
            "work remotely",
            "remote work",
        ]

        for keyword in remote_description_keywords:
            if keyword in description:
                return True

        # Negative indicators (reject if found)
        # These indicate on-site or hybrid requirements
        onsite_indicators = [
            "on-site",
            "onsite",
            "in-office",
            "office-based",
            "must be located in",
            "must reside in",
            "hybrid",  # Hybrid is NOT fully remote
            "relocation required",
        ]

        for indicator in onsite_indicators:
            if indicator in title or indicator in description:
                return False

        # If no clear indicators, reject (strict mode)
        # Better to miss some remote jobs than include non-remote ones
        return False
