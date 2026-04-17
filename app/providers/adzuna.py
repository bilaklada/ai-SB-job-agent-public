"""
Adzuna Job Provider

Adapter for fetching jobs from Adzuna API.
Documentation: https://developer.adzuna.com/docs/search
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx

from app.providers.base import BaseJobProvider


class AdzunaProvider(BaseJobProvider):
    """
    Adzuna job board API client.

    Adzuna aggregates job listings from multiple sources and provides
    a clean REST API with good documentation and generous free tier.

    API Limits:
    - Free tier: 5,000 calls/month
    - Rate limit: Reasonable (not strictly enforced for free tier)

    Authentication:
    - Requires both app_id and app_key
    - Passed as query parameters in every request
    """

    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    # Adzuna-supported EU countries only
    # Based on Adzuna API documentation: https://developer.adzuna.com/docs/search
    # Verified supported countries in Europe
    EU_COUNTRIES = [
        "at",  # Austria
        "be",  # Belgium
        "de",  # Germany
        "fr",  # France
        "it",  # Italy
        "nl",  # Netherlands
        "pl",  # Poland
        "es",  # Spain
    ]

    # Adzuna-supported countries worldwide
    # This is the complete list of countries Adzuna API supports
    WORLD_COUNTRIES = [
        "au",  # Australia
        "at",  # Austria
        "be",  # Belgium
        "br",  # Brazil
        "ca",  # Canada
        "de",  # Germany
        "fr",  # France
        "gb",  # United Kingdom
        "in",  # India
        "it",  # Italy
        "mx",  # Mexico
        "nl",  # Netherlands
        "nz",  # New Zealand
        "pl",  # Poland
        "sg",  # Singapore
        "us",  # United States
        "za",  # South Africa
    ]

    def __init__(self, api_key: str, app_id: str):
        """
        Initialize Adzuna provider.

        Args:
            api_key: Adzuna API key
            app_id: Adzuna application ID
        """
        super().__init__(api_key=api_key, app_id=app_id)

        if not app_id:
            raise ValueError("Adzuna requires both api_key and app_id")


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
        Fetch jobs from Adzuna API.

        API Endpoint: GET /v1/api/jobs/{country}/search/{page}

        Args:
            query: What to search for (e.g., "python developer")
            location: Where to search (e.g., "New York")
            country:
                - normal country code ("us", "de", "ch", "gb", ...)
                - or "eu"  → searching in all EU_COUNTRIES
                - or "world" / "all" → seaching in WORLD_COUNTRIES
            page: Page number (starts at 1)
            results_per_page: Results per page (max 50)
        """

        # We determine which countries to make queries for
        country_lower = (country or "eu").lower()

        if country_lower == "eu":
            countries_to_fetch = self.EU_COUNTRIES
        elif country_lower in ("world", "all"):
            countries_to_fetch = self.WORLD_COUNTRIES
        else:
            countries_to_fetch = [country_lower]

        all_results: List[Dict[str, Any]] = []

        # General query parameters (the same for all countries)
        base_params: Dict[str, Any] = {
            "app_id": self.app_id,
            "app_key": self.api_key,
            "results_per_page": min(results_per_page, 50),  # Max 50
            "what": query,
        }

        # Add location if provided
        if location:
            base_params["where"] = location

        # Add optional Adzuna-specific parameters
        if "sort_by" in kwargs:
            base_params["sort_by"] = kwargs["sort_by"]
        if "salary_min" in kwargs:
            base_params["salary_min"] = kwargs["salary_min"]
        if "salary_max" in kwargs:
            base_params["salary_max"] = kwargs["salary_max"]
        if "full_time" in kwargs:
            base_params["full_time"] = kwargs["full_time"]
        if "part_time" in kwargs:
            base_params["part_time"] = kwargs["part_time"]
        if "contract" in kwargs:
            base_params["contract"] = kwargs["contract"]
        if "permanent" in kwargs:
            base_params["permanent"] = kwargs["permanent"]

        # One HTTP client for all requests
        async with httpx.AsyncClient(timeout=30.0) as client:
            for c in countries_to_fetch:
                url = f"{self.BASE_URL}/{c}/search/{page}"
                response = await client.get(url, params=base_params)
                response.raise_for_status()

                data = response.json()
                results = data.get("results", [])
                all_results.extend(results)

        return all_results

    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Adzuna job data to our standard format.

        Adzuna API Response Structure:
        {
            "id": "12345",
            "title": "Senior Python Developer",
            "company": {"display_name": "Tech Corp"},
            "location": {"display_name": "San Francisco, CA", "area": ["USA", "California", "San Francisco"]},
            "redirect_url": "https://...",
            "description": "Full job description...",
            "salary_min": 100000,
            "salary_max": 150000,
            "salary_is_predicted": "0",
            "created": "2024-01-15T10:30:00Z",
            "contract_type": "permanent",
            "category": {"label": "IT Jobs"}
        }

        Args:
            raw_job: Raw job data from Adzuna API

        Returns:
            Normalized job dictionary matching our schema
        """
        # Extract company name
        company = raw_job.get("company", {})
        company_name = company.get("display_name", "Unknown Company")

        # Extract location data
        location = raw_job.get("location", {})
        location_display = location.get("display_name", "")
        location_areas = location.get("area", [])

        # Parse city and country from location areas
        # Adzuna format: ["Country", "State/Region", "City"]
        country_raw = None  # Original country name from Adzuna (localized)
        city = None
        if location_areas:
            if len(location_areas) >= 1:
                country_raw = location_areas[0]  # First element is country (localized name)
            if len(location_areas) >= 3:
                city = location_areas[2]  # Third element is city
            elif len(location_areas) >= 2:
                city = location_areas[1]  # Or second element if no third

        # Normalize country to ISO 3166-1 alpha-2 code (uppercase, 2 letters)
        # Maps both English and localized country names to ISO codes
        country_to_iso = {
            # English names
            "USA": "US",
            "United States": "US",
            "UK": "GB",
            "United Kingdom": "GB",
            "Germany": "DE",
            "France": "FR",
            "Spain": "ES",
            "Italy": "IT",
            "Netherlands": "NL",
            "Belgium": "BE",
            "Austria": "AT",
            "Poland": "PL",
            "Switzerland": "CH",
            "Canada": "CA",
            "Australia": "AU",
            "New Zealand": "NZ",
            "India": "IN",
            "Singapore": "SG",
            "Brazil": "BR",
            "Mexico": "MX",
            "South Africa": "ZA",
            # Localized names (as returned by Adzuna API)
            "Österreich": "AT",       # Austria (German)
            "België": "BE",            # Belgium (Dutch)
            "Belgique": "BE",          # Belgium (French)
            "Deutschland": "DE",       # Germany (German)
            "Frankreich": "FR",        # France (German)
            "Francia": "FR",           # France (Spanish/Italian)
            "Spanien": "ES",           # Spain (German)
            "España": "ES",            # Spain (Spanish)
            "Spagna": "ES",            # Spain (Italian)
            "Italien": "IT",           # Italy (German)
            "Italia": "IT",            # Italy (Italian)
            "Niederlande": "NL",       # Netherlands (German)
            "Nederland": "NL",         # Netherlands (Dutch)
            "Paesi Bassi": "NL",       # Netherlands (Italian)
            "Polen": "PL",             # Poland (German)
            "Polska": "PL",            # Poland (Polish)
            "Polonia": "PL",           # Poland (Italian/Spanish)
            "Schweiz": "CH",           # Switzerland (German)
            "Suisse": "CH",            # Switzerland (French)
            "Svizzera": "CH",          # Switzerland (Italian)
            "Vereinigte Staaten": "US",  # United States (German)
            "Stati Uniti": "US",       # United States (Italian)
            "Kanada": "CA",            # Canada (German)
            "Australien": "AU",        # Australia (German)
            "Neuseeland": "NZ",        # New Zealand (German)
            "Indien": "IN",            # India (German)
            "Singapur": "SG",          # Singapore (German)
            "Brasilien": "BR",         # Brazil (German)
            "Mexiko": "MX",            # Mexico (German)
            "Südafrika": "ZA",         # South Africa (German)
        }
        # Convert to ISO code, or None if not found
        country = country_to_iso.get(country_raw) if country_raw else None

        # Extract salary data
        salary_min = raw_job.get("salary_min")
        salary_max = raw_job.get("salary_max")

        # Infer currency from ISO country code
        # Now that country is normalized to ISO codes, mapping is simpler and more reliable
        iso_to_currency = {
            "US": "USD",
            "GB": "GBP",
            "DE": "EUR",
            "FR": "EUR",
            "ES": "EUR",
            "IT": "EUR",
            "NL": "EUR",
            "BE": "EUR",
            "AT": "EUR",
            "PL": "PLN",
            "CH": "CHF",
            "CA": "CAD",
            "AU": "AUD",
            "NZ": "NZD",
            "IN": "INR",
            "SG": "SGD",
            "BR": "BRL",
            "MX": "MXN",
            "ZA": "ZAR",
        }
        # Use None instead of "USD" as default - more honest when currency is unknown
        salary_currency = iso_to_currency.get(country) if country else None

        # Parse posted date
        created_str = raw_job.get("created")
        posted_at = None
        if created_str:
            try:
                # Adzuna uses ISO 8601 format
                posted_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                posted_at = None

        # Determine apply type from URL
        redirect_url = raw_job.get("redirect_url", "")
        apply_type = "other"  # Default
        if "greenhouse.io" in redirect_url:
            apply_type = "greenhouse"
        elif "lever.co" in redirect_url:
            apply_type = "lever"
        elif "workday.com" in redirect_url:
            apply_type = "workday"
        elif "myworkdayjobs.com" in redirect_url:
            apply_type = "workday"
        elif "linkedin.com" in redirect_url:
            apply_type = "linkedin"
        elif "indeed.com" in redirect_url:
            apply_type = "indeed"
        elif raw_job.get("company", {}).get("display_name"):
            # If we have a company name and it's not a known ATS, assume company site
            apply_type = "company_site"

        # Build normalized job dictionary
        normalized = {
            "provider": "adzuna",
            "provider_job_id": str(raw_job.get("id", "")),
            "title": raw_job.get("title", ""),
            "company": company_name,
            "location_raw": location_display,
            "location_country": country,
            "location_city": city,
            "url": redirect_url,
            "description": raw_job.get("description", ""),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "posted_at": posted_at,
            "apply_type": apply_type,
            "status": "new",  # All new jobs start with "new" status
        }

        return normalized
