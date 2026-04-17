"""
Base Job Provider

Abstract base class that all job provider adapters must implement.
This ensures consistency across different job boards (Adzuna, Jooble, Indeed, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class BaseJobProvider(ABC):
    """
    Abstract base class for job provider adapters.

    All job providers (Adzuna, Jooble, Indeed, etc.) must inherit from this class
    and implement the required methods.

    This ensures that:
    1. All providers have a consistent interface
    2. We can easily add new providers
    3. The service layer can work with any provider without knowing the details
    """

    def __init__(self, api_key: str, app_id: Optional[str] = None):
        """
        Initialize the job provider.

        Args:
            api_key: API key for authentication
            app_id: Optional app ID (some providers like Adzuna require both)
        """
        self.api_key = api_key
        self.app_id = app_id

    @abstractmethod
    async def fetch_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        country: str = "eu",
        page: int = 1,
        results_per_page: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch jobs from the provider's API.

        Args:
            query: Search query (e.g., "python developer", "data scientist")
            location: Location filter (e.g., "New York", "San Francisco")
            country: Country code (e.g., "us", "gb", "de")
            page: Page number for pagination (starts at 1)
            results_per_page: Number of results per page
            **kwargs: Additional provider-specific parameters

        Returns:
            List of job dictionaries with standardized fields

        Raises:
            Exception: If API call fails
        """
        pass

    @abstractmethod
    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a raw job from provider API to our standard format.

        Each provider returns data in different formats. This method converts
        provider-specific fields to our standardized schema.

        Args:
            raw_job: Raw job data from provider API

        Returns:
            Normalized job dictionary with standard fields:
            {
                "provider": str,           # Provider name (e.g., "adzuna")
                "external_id": str,        # Provider's job ID
                "title": str,              # Job title
                "company": str,            # Company name
                "location_raw": str,       # Full location string
                "country": str,            # Country code
                "city": Optional[str],     # City name
                "url": str,                # Application URL
                "description_raw": str,    # Full job description
                "salary_min": Optional[float],  # Min salary
                "salary_max": Optional[float],  # Max salary
                "salary_currency": Optional[str],  # Currency code
                "posted_at": Optional[datetime],   # When job was posted
                "apply_type": str,         # "company_site", "portal", or "other"
            }
        """
        pass

    def get_provider_name(self) -> str:
        """
        Get the name of this provider.

        Returns:
            Provider name (e.g., "adzuna", "jooble", "indeed")
        """
        return self.__class__.__name__.replace("Provider", "").lower()

    async def search_and_normalize(
        self,
        query: str,
        location: Optional[str] = None,
        country: str = "eu",
        page: int = 1,
        results_per_page: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch jobs and normalize them in one call.

        This is a convenience method that combines fetch_jobs() and normalize_job().

        Args:
            Same as fetch_jobs()

        Returns:
            List of normalized job dictionaries
        """
        raw_jobs = await self.fetch_jobs(
            query=query,
            location=location,
            country=country,
            page=page,
            results_per_page=results_per_page,
            **kwargs
        )

        normalized_jobs = []
        for raw_job in raw_jobs:
            try:
                normalized = self.normalize_job(raw_job)
                normalized_jobs.append(normalized)
            except Exception as e:
                # Log error but continue processing other jobs
                print(f"Error normalizing job: {e}")
                continue

        return normalized_jobs
