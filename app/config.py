"""
config.py - Application Configuration Management

================================================================================
WHAT THIS FILE DOES:
================================================================================
This file is the SINGLE SOURCE OF TRUTH for all configuration in your application.
Instead of hardcoding database URLs, API keys, and settings throughout your code,
you put them all here in one place.

Think of it like a control panel for your entire application - you can change
settings here without hunting through dozens of files.

================================================================================
HOW IT WORKS:
================================================================================
1. You create a .env file with your secrets (DATABASE_URL=..., OPENAI_API_KEY=...)
2. This Settings class automatically reads that .env file when your app starts
3. Other parts of your code import and use these settings
4. Your secrets never get hardcoded in source code (security!)

================================================================================
WHY USE PYDANTIC SETTINGS?
================================================================================
Pydantic Settings is a library that:
- Automatically loads environment variables from .env files
- Validates that all required settings are present (fails fast if missing)
- Provides type hints (IDE autocomplete and type checking)
- Converts string values to correct types (turns "993" into integer 993)
- Provides default values for optional settings
- Makes testing easier (you can override settings in tests)

================================================================================
USAGE EXAMPLES:
================================================================================

Example 1: Import settings in any file
---------------------------------------
from app.config import settings

# Access database URL
db_url = settings.DATABASE_URL
# Result: "postgresql://user:pass@localhost:5432/db"

# Access OpenAI API key
api_key = settings.OPENAI_API_KEY
# Result: "sk-proj-abc123..."

# Check if debug mode is on
if settings.DEBUG:
    print("Running in debug mode!")


Example 2: Use in database connection (app/db/session.py)
---------------------------------------------------------
from sqlalchemy import create_engine
from app.config import settings

# Settings automatically loaded from .env
engine = create_engine(settings.DATABASE_URL)


Example 3: Use in API routes
----------------------------
from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG
)


Example 4: Use with external APIs
---------------------------------
from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


Example 5: Environment-specific behavior
----------------------------------------
from app.config import settings

if settings.ENVIRONMENT == "production":
    # Send real emails
    send_email(to=user.email, subject="Welcome!")
elif settings.ENVIRONMENT == "development":
    # Just log the email instead of sending
    print(f"Would send email to {user.email}")

================================================================================
"""

# Standard library imports
import os
from typing import Optional, List, Union

# Pydantic imports for Settings management
# BaseSettings: Special Pydantic class that loads from environment variables
# Field: Allows you to add descriptions and validation rules
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


# =============================================================================
# SETTINGS CLASS - THE HEART OF CONFIGURATION
# =============================================================================
class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    HOW THIS CLASS WORKS:
    ---------------------
    When you create an instance of this class (e.g., `settings = Settings()`),
    Pydantic automatically:
    1. Looks for a .env file in your project root
    2. Reads all KEY=VALUE pairs from it
    3. Loads them into this Settings object
    4. Validates that required fields are present
    5. Converts strings to correct types (int, bool, etc.)

    FIELD SYNTAX EXPLANATION:
    -------------------------
    Each field follows this pattern:

    FIELD_NAME: Type = default_value

    - FIELD_NAME: Name of the environment variable (must match .env)
    - Type: Expected data type (str, int, bool, Optional[str])
    - default_value: What to use if not in .env (optional fields only)

    Optional[str] means: "This can be a string OR None (if not provided)"

    VALIDATION:
    -----------
    - Required fields (no default): App crashes if missing from .env
    - Optional fields (with default): Uses default if missing from .env
    - Type checking: Automatically converts "True" -> True, "993" -> 993
    """

    # =========================================================================
    # CORE APPLICATION SETTINGS
    # =========================================================================

    PROJECT_NAME: str = "AI Job Application Agent"
    # The name of your application
    # Used in: API documentation, logs, email subjects
    # Default value means it doesn't need to be in .env

    DEBUG: bool = False
    # Controls debug mode: detailed error messages vs. user-friendly errors
    # True = Development (show stack traces, auto-reload code)
    # False = Production (hide errors from users, optimized performance)
    # Type: bool means .env value "True" or "False" converts to boolean

    ENVIRONMENT: str = "development"
    # Which environment is the app running in?
    # Options: "development", "staging", "production"
    # Used to: Enable/disable features, change logging, skip email sending in dev
    # Example: if settings.ENVIRONMENT == "production": send_real_email()

    LOG_LEVEL: str = "INFO"
    # How verbose should logging be?
    # DEBUG = Everything (verbose, for development)
    # INFO = Normal operations (API calls, job processing)
    # WARNING = Potential issues (slow queries, deprecated features)
    # ERROR = Failures only (exceptions, failed API calls)
    # CRITICAL = App-breaking issues only

    # =========================================================================
    # DATABASE CONFIGURATION
    # =========================================================================

    DATABASE_URL: str = Field(
        default="sqlite:///./app.db",
        description="PostgreSQL connection string for the database"
    )
    # Connection string telling SQLAlchemy how to connect to your database
    # Format: postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME
    #
    # Examples:
    # - Local dev: postgresql://postgres:password@localhost:5432/jobagent
    # - Docker: postgresql://jobagent:dev_password@db:5432/jobagent
    # - Production: postgresql://user:pass@prod-db.example.com:5432/jobagent
    #
    # Default "sqlite:///./app.db" is a fallback for quick local testing
    #
    # Field() allows us to add a description (shown in error messages)

    # =========================================================================
    # OPENAI API CONFIGURATION (Phase 7 - AI Components)
    # =========================================================================

    OPENAI_API_KEY: Optional[str] = None
    # API key for OpenAI (GPT models)
    # Get from: https://platform.openai.com/api-keys
    # Format: Starts with "sk-" followed by random characters
    #
    # Used by:
    # - Matching engine: Calculate job-profile match scores
    # - Vacancy parser: Extract structured data from job descriptions
    # - Field classifier: Identify form field types
    # - Answer generator: Generate personalized answers to open questions
    #
    # Optional[str] means: Can be None (for phases before AI is implemented)
    # When Phase 7 starts, this becomes required
    #
    # Cost: Pay-per-use based on tokens (prompt + response length)
    # Budget: ~$0.002 per job analyzed (with GPT-4)

    OPENAI_MODEL: str = "gpt-4o-mini"
    # Which OpenAI model to use
    # Options:
    # - gpt-4o: Most capable, expensive (~$0.03/1K tokens)
    # - gpt-4o-mini: Fast, cheap (~$0.0015/1K tokens) - RECOMMENDED
    # - gpt-3.5-turbo: Fastest, cheapest (~$0.0005/1K tokens), less accurate
    #
    # Recommendation: Start with gpt-4o-mini for development

    # =========================================================================
    # ANTHROPIC CONFIGURATION (Claude Models)
    # =========================================================================

    ANTHROPIC_API_KEY: Optional[str] = None
    # API key for Anthropic (Claude models)
    # Get from: https://console.anthropic.com/settings/keys
    # Format: Starts with "sk-ant-" followed by random characters
    #
    # Used by:
    # - ATS matching: Identify which ATS platform from job URL
    # - Company matching: Identify company from job posting
    # - Future: All AI operations (matching, parsing, generation)
    #
    # Optional[str] means: Can be None (if not using Anthropic provider)
    #
    # Cost: Pay-per-use based on tokens
    # Budget: ~$0.003-0.015 per job analyzed (Claude 3.5 Sonnet)

    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    # Which Anthropic model to use
    # Options:
    # - claude-3-5-sonnet-20241022: Best balance ($3/$15 per M tokens) - RECOMMENDED
    # - claude-3-haiku-20240307: Fastest, cheapest ($0.25/$1.25 per M tokens)
    # - claude-3-opus-20240229: Most capable ($15/$75 per M tokens)
    #
    # Recommendation: Use claude-3-5-sonnet for production

    # =========================================================================
    # GOOGLE GEMINI CONFIGURATION
    # =========================================================================

    GEMINI_API_KEY: Optional[str] = None
    # API key for Google Gemini models
    # Get from: https://aistudio.google.com/app/apikey
    # Format: Starts with "AIza" followed by random characters
    #
    # Used by:
    # - ATS matching: Identify which ATS platform from job URL (current default)
    # - Company matching: Identify company from job posting
    # - Browser automation: Adaptive form filling (via browser-use)
    #
    # Optional[str] means: Can be None (if not using Gemini provider)
    #
    # Cost: Free tier available (1500 requests/day)
    # Budget: $0.00 (free tier) or ~$0.0001 per job (paid tier)

    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    # Which Gemini model to use
    # Options:
    # - gemini-2.0-flash-exp: Experimental, fast, FREE - RECOMMENDED for dev
    # - gemini-1.5-flash: Production, fast ($0.075/$0.30 per M tokens)
    # - gemini-1.5-pro: Most capable ($1.25/$5 per M tokens)
    #
    # Recommendation: Use gemini-2.0-flash-exp for development (free tier)

    # =========================================================================
    # LLM PROVIDER SELECTION (Multi-Provider Support)
    # =========================================================================

    ATS_MATCHING_LLM_PROVIDER: str = "gemini"
    # Which LLM provider to use for ATS matching
    # Options: 'gemini', 'openai', 'anthropic'
    #
    # Default: 'gemini' (free tier, good performance)
    #
    # Use this to A/B test different providers:
    # - gemini: Free tier, fast, good accuracy
    # - openai: Paid, very reliable, gpt-4o-mini is cost-effective
    # - anthropic: Paid, excellent reasoning, Claude 3.5 Sonnet recommended
    #
    # Performance comparison (set in .env to switch):
    # ATS_MATCHING_LLM_PROVIDER=openai
    # ATS_MATCHING_LLM_PROVIDER=anthropic

    ATS_MATCHING_LLM_MODEL: Optional[str] = None
    # Override default model for ATS matching (optional)
    #
    # If None, uses default model for the selected provider:
    # - gemini → GEMINI_MODEL (gemini-2.0-flash-exp)
    # - openai → OPENAI_MODEL (gpt-4o-mini)
    # - anthropic → ANTHROPIC_MODEL (claude-3-5-sonnet-20241022)
    #
    # Set this to test specific models:
    # ATS_MATCHING_LLM_MODEL=gpt-4o  # Override to use GPT-4o instead of mini
    # ATS_MATCHING_LLM_MODEL=claude-3-haiku-20240307  # Test cheaper Claude model

    # =========================================================================
    # EMAIL CONFIGURATION (Phase 6 - Account Verification)
    # =========================================================================

    EMAIL_IMAP_HOST: Optional[str] = None
    # IMAP server address for reading emails
    # Common values:
    # - Gmail: imap.gmail.com
    # - Outlook: outlook.office365.com
    # - Yahoo: imap.mail.yahoo.com
    # - Custom domain: mail.yourdomain.com
    #
    # Used by: Email agent to check for verification emails
    # Example: After creating account on Greenhouse, check email for verify link

    EMAIL_IMAP_PORT: int = 993
    # Port number for IMAP over SSL/TLS
    # Standard ports:
    # - 993: IMAP with SSL (secure) - USE THIS
    # - 143: IMAP without SSL (insecure) - DON'T USE
    #
    # Type: int means .env value "993" automatically converts to integer

    EMAIL_IMAP_USERNAME: Optional[str] = None
    # Email address to log in with
    # Example: yourbot@gmail.com
    #
    # Used by: Email agent for IMAP authentication
    # Recommendation: Create dedicated email account for this bot

    EMAIL_IMAP_PASSWORD: Optional[str] = None
    # Password or app-specific password
    #
    # IMPORTANT FOR GMAIL USERS:
    # Don't use your regular Gmail password!
    # 1. Go to: https://myaccount.google.com/apppasswords
    # 2. Create an "App Password" (16 characters)
    # 3. Use that password here
    #
    # Why? Gmail blocks "less secure apps" (Python scripts) by default
    # App passwords are designed for scripts and bypass this restriction

    # =========================================================================
    # AWS S3 / FILE STORAGE CONFIGURATION (Phase 4 - Documents)
    # =========================================================================

    AWS_S3_ENDPOINT: Optional[str] = None
    # URL of your S3-compatible storage service
    # Options:
    # - AWS S3: https://s3.amazonaws.com or https://s3.REGION.amazonaws.com
    # - DigitalOcean Spaces: https://nyc3.digitaloceanspaces.com
    # - Backblaze B2: https://s3.us-west-001.backblazeb2.com
    # - MinIO (self-hosted): http://localhost:9000
    #
    # Used by: Document manager to upload CVs, diplomas, certificates
    # Why cloud storage? RPA bots need to access files from Docker containers

    AWS_S3_BUCKET_NAME: Optional[str] = None
    # Name of the S3 bucket where documents are stored
    # Example: "ai-job-agent-documents"
    #
    # Bucket structure might look like:
    # my-bucket/
    #   ├── cvs/
    #   │   ├── cv_software_engineer.pdf
    #   │   └── cv_data_scientist.pdf
    #   ├── diplomas/
    #   │   └── masters_degree.pdf
    #   └── certificates/
    #       └── aws_certified.pdf

    AWS_ACCESS_KEY_ID: Optional[str] = None
    # AWS access key (public part of credentials)
    # Format: Starts with "AKIA" for IAM users
    # Get from: AWS Console > IAM > Users > Security Credentials
    #
    # Think of this as a "username" for API access
    # Used by: boto3 (AWS SDK) to authenticate file uploads/downloads

    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    # AWS secret key (private part of credentials - like a password)
    # Get from: AWS Console when creating access key (shown only once!)
    #
    # SECURITY: Never commit this to Git, never share it
    # If compromised: Attacker can access your S3 bucket and rack up AWS bills
    #
    # Used by: boto3 to sign requests (proves you own the ACCESS_KEY_ID)

    AWS_REGION: str = "us-east-1"
    # AWS region where your bucket is located
    # Common regions:
    # - us-east-1: Virginia (cheapest, most services)
    # - eu-west-1: Ireland (GDPR compliance)
    # - ap-southeast-1: Singapore (Asia)
    #
    # Why it matters: Latency (closer = faster), pricing, compliance laws

    # =========================================================================
    # SECURITY CONFIGURATION
    # =========================================================================

    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production-min-50-characters-long",
        min_length=32
    )
    # Secret key for cryptographic operations
    #
    # Used for:
    # - JWT token signing (so users can't forge auth tokens)
    # - Session encryption (cookie security)
    # - CSRF protection (prevent cross-site attacks)
    # - Password reset tokens (so they can't be guessed)
    #
    # REQUIREMENTS:
    # - Minimum 32 characters (enforced by min_length=32)
    # - Should be 50+ characters in production
    # - Must be random and unpredictable
    # - Different for each environment (dev, staging, prod)
    #
    # Generate secure key:
    # python -c "import secrets; print(secrets.token_urlsafe(50))"
    #
    # Security impact if leaked:
    # - Attacker can forge JWT tokens and impersonate any user
    # - All sessions can be decrypted
    # - Password reset tokens can be generated

    # =========================================================================
    # REDIS CONFIGURATION (Phase 5+ - Celery Task Queue)
    # =========================================================================

    REDIS_URL: str = "redis://localhost:6379/0"
    # Connection string for Redis (in-memory data store)
    # Format: redis://HOST:PORT/DATABASE_NUMBER
    #
    # Examples:
    # - Local: redis://localhost:6379/0
    # - Docker: redis://redis:6379/0
    # - Cloud (Redis Labs): redis://username:password@redis-12345.cloud.redislabs.com:12345
    #
    # Used by:
    # - Celery broker: Manages background job queues
    # - Celery result backend: Stores task results
    # - Cache: Fast lookups for frequently accessed data
    # - Session storage: User session data
    #
    # Database numbers: Redis has 16 databases (0-15), we use 0 by default
    # You can use different numbers for different purposes:
    # - 0: Celery broker
    # - 1: Caching
    # - 2: Sessions

    # =========================================================================
    # JOB PROVIDER API KEYS (Phase 2-3 - Job Aggregation)
    # =========================================================================

    ADZUNA_API_KEY: Optional[str] = None
    # API key for Adzuna job board
    # Sign up: https://developer.adzuna.com/
    # Free tier: 5,000 calls/month
    #
    # Used by: Adzuna provider adapter to fetch job listings
    # Example API call: GET /v1/api/jobs/us/search/1?app_id=X&app_key=Y&what=python

    ADZUNA_APP_ID: Optional[str] = None
    # App ID for Adzuna (companion to API key)
    # Both app_id and app_key are required for authentication
    # Think of it like username (app_id) + password (app_key)

    JOOBLE_API_KEY: Optional[str] = None
    # API key for Jooble job board
    # Sign up: https://jooble.org/api/about
    # Free tier: 1,000 calls/day
    #
    # Used by: Jooble provider adapter

    INDEED_PUBLISHER_ID: Optional[str] = None
    # Publisher ID for Indeed API
    # Note: Indeed heavily restricts API access (very hard to get approved)
    # Alternative: Consider web scraping (check ToS) or skip Indeed
    #
    # Used by: Indeed provider adapter (if available)

    JSEARCH_API_KEY: Optional[str] = None
    # RapidAPI key for JSearch job board
    # Sign up: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
    # Free tier: 200 calls/month, 1000/hour rate limit
    #
    # JSearch aggregates jobs from Google for Jobs, covering major platforms
    # like LinkedIn, Indeed, Glassdoor, and 30+ other sources
    #
    # Used by: JSearch provider adapter to fetch job listings
    # Authentication: RapidAPI key passed via X-RapidAPI-Key header

    # =========================================================================
    # CORS CONFIGURATION (Phase 8 - Web UI)
    # =========================================================================

    CORS_ORIGINS: Union[str, List[str]] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )
    # List of URLs allowed to make API requests to your backend
    #
    # CORS (Cross-Origin Resource Sharing) is a security feature
    # Browsers block API calls from different domains by default
    #
    # Example scenario:
    # - Your API runs on: http://localhost:8000
    # - Your React app runs on: http://localhost:3000
    # - Without CORS: Browser blocks React from calling API ❌
    # - With CORS: You explicitly allow localhost:3000 ✅
    #
    # Development values:
    # - http://localhost:3000 (React dev server)
    # - http://localhost:8000 (API itself)
    #
    # Production values:
    # - https://app.yourdomain.com (your deployed frontend)
    # - https://admin.yourdomain.com (admin panel)
    #
    # Format in .env (comma-separated):
    # CORS_ORIGINS=http://localhost:3000,https://app.yourdomain.com

    # =========================================================================
    # OPTIONAL: MONITORING & ALERTS
    # =========================================================================

    SENTRY_DSN: Optional[str] = None
    # Sentry DSN (Data Source Name) for error tracking
    # Sign up: https://sentry.io/
    # Free tier: 5,000 events/month
    #
    # What Sentry does:
    # - Captures all exceptions automatically
    # - Shows stack traces, user context, request data
    # - Groups similar errors together
    # - Sends email/Slack alerts for new errors
    #
    # Used by: Error handling middleware
    # Example: When job parsing fails, Sentry logs it with full context

    TELEGRAM_BOT_TOKEN: Optional[str] = None
    # Telegram bot token for notifications
    # Create bot: https://t.me/BotFather
    # Format: Looks like "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    #
    # Used by: Notification service to send alerts
    # Example: "✅ 5 jobs applied successfully"

    TELEGRAM_CHAT_ID: Optional[str] = None
    # Telegram chat ID where notifications are sent
    # Get your chat ID: https://t.me/userinfobot
    # Format: Numbers like "123456789" or "-100123456789" (for groups)
    #
    # Used by: Notification service

    # =========================================================================
    # RATE LIMITING
    # =========================================================================

    RATE_LIMIT_PER_MINUTE: int = 60
    # Maximum API requests allowed per minute per IP address
    # Prevents abuse and DoS attacks
    #
    # Used by: FastAPI rate limiting middleware (slowapi)
    # Example: If user makes 61 requests in 60 seconds, block further requests

    # =========================================================================
    # PYDANTIC SETTINGS CONFIGURATION
    # =========================================================================

    model_config = SettingsConfigDict(
        # Tell Pydantic to load from .env file
        env_file=".env",

        # Look for .env in parent directory (project root)
        # This allows app/config.py to find .env at project root
        env_file_encoding="utf-8",

        # If .env doesn't exist, don't crash (use defaults)
        # Useful for CI/CD where environment variables come from system
        env_ignore_empty=True,

        # Allow extra fields in .env that aren't in Settings class
        # Useful for adding new variables without breaking existing code
        extra="ignore",

        # Case sensitive environment variable names
        # DATABASE_URL and database_url are different
        case_sensitive=True,
    )

    # =========================================================================
    # CUSTOM VALIDATORS (Optional - Advanced)
    # =========================================================================

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """
        Custom validator for DATABASE_URL

        What this does:
        ---------------
        Pydantic calls this function after loading DATABASE_URL from .env
        You can add custom checks and transformations here

        Example use cases:
        - Ensure production uses PostgreSQL (not SQLite)
        - Warn if using default password
        - Transform URL format

        Parameters:
        -----------
        cls: The Settings class itself
        v: The value of DATABASE_URL from .env

        Returns:
        --------
        The validated/transformed value

        Raises:
        -------
        ValueError: If validation fails (app won't start)
        """
        if v.startswith("sqlite") and os.getenv("ENVIRONMENT") == "production":
            # In production, force PostgreSQL (SQLite is for development only)
            raise ValueError(
                "SQLite is not allowed in production! "
                "Use PostgreSQL: DATABASE_URL=postgresql://..."
            )
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """
        Custom validator for SECRET_KEY

        Ensures the secret key is secure enough for production use
        """
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long! "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(50))'"
            )

        # Warn if using default key in production
        if "change-in-production" in v and os.getenv("ENVIRONMENT") == "production":
            raise ValueError(
                "You must change SECRET_KEY in production! "
                "Never use the default dev key."
            )

        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """
        Custom validator for CORS_ORIGINS

        Handles comma-separated string from .env and converts to list

        .env format: CORS_ORIGINS=http://localhost:3000,https://app.com
        Python result: ["http://localhost:3000", "https://app.com"]
        """
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(",")]
        return v


# =============================================================================
# CREATE SETTINGS INSTANCE (SINGLETON PATTERN)
# =============================================================================

# This is the actual settings object used throughout your application
# When this line runs (on first import), Pydantic:
# 1. Looks for .env file
# 2. Loads all environment variables
# 3. Validates them against the Settings class
# 4. Creates this settings object with all values
settings = Settings()

# Why singleton? We create settings ONCE when the app starts, then reuse it
# everywhere. This is efficient and ensures consistent configuration.

# =============================================================================
# USAGE IN OTHER FILES
# =============================================================================

# Just import and use:
#
# from app.config import settings
#
# print(settings.DATABASE_URL)  # Access any setting
# print(settings.DEBUG)          # Type hints work!
# print(settings.OPENAI_API_KEY) # IDE autocomplete works!

# =============================================================================
# DEBUGGING HELPER (Optional)
# =============================================================================

def print_settings(hide_secrets: bool = True) -> None:
    """
    Print all settings for debugging (hides secrets by default)

    Usage:
    ------
    from app.config import print_settings
    print_settings()  # See all settings

    Parameters:
    -----------
    hide_secrets: If True, mask sensitive values like API keys
    """
    print("\n" + "=" * 80)
    print("APPLICATION SETTINGS")
    print("=" * 80)

    # List of sensitive field names to mask
    sensitive_fields = {
        "OPENAI_API_KEY", "EMAIL_IMAP_PASSWORD", "AWS_SECRET_ACCESS_KEY",
        "SECRET_KEY", "ADZUNA_API_KEY", "JOOBLE_API_KEY", "TELEGRAM_BOT_TOKEN",
        "SENTRY_DSN"
    }

    # Iterate through all settings
    for field_name, field_value in settings.model_dump().items():
        # Mask sensitive values
        if hide_secrets and field_name in sensitive_fields and field_value:
            # Show first 4 and last 4 characters only
            if len(str(field_value)) > 8:
                display_value = f"{str(field_value)[:4]}...{str(field_value)[-4:]}"
            else:
                display_value = "****"
        else:
            display_value = field_value

        print(f"{field_name}: {display_value}")

    print("=" * 80 + "\n")


# =============================================================================
# DATABASE-BACKED SETTINGS (Multi-Provider LLM Selection)
# =============================================================================

def get_ats_matching_llm_config():
    """
    Get ATS matching LLM configuration from database settings.

    This function reads the 'ats_matching_model' setting from the database
    and returns the provider name and model name to use for ATS matching.

    If no setting is found in the database, falls back to environment variables:
    - ATS_MATCHING_LLM_PROVIDER (default: 'gemini')
    - ATS_MATCHING_LLM_MODEL (default: provider's default model)

    Returns:
        Tuple[str, str]: (provider_name, model_name)
        Example: ('openai', 'gpt-4o-mini')

    Database setting format:
        setting_name: 'ats_matching_model'
        setting_value: {'llm_model_id': 1}

    The function looks up the model by ID and returns the associated
    provider name and model name.
    """
    try:
        # Import here to avoid circular imports
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db.models import Setting, LLMModel

        # Create database session
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            # Fetch ATS matching model setting
            setting = db.query(Setting).filter(
                Setting.setting_name == "ats_matching_model"
            ).first()

            if setting and setting.setting_value.get("llm_model_id"):
                model_id = setting.setting_value["llm_model_id"]

                # Fetch the model from llm_models table
                llm_model = db.query(LLMModel).filter(
                    LLMModel.llm_model_id == model_id
                ).first()

                if llm_model:
                    # Return provider name (lowercase) and model name
                    provider_name = llm_model.llm_provider_name.lower()
                    model_name = llm_model.llm_model_name

                    return (provider_name, model_name)

        finally:
            db.close()

    except Exception as e:
        # Log error but don't crash - fall back to env variables
        import logging
        logging.warning(
            f"Failed to read ATS model from database: {e}. "
            f"Falling back to environment variables."
        )

    # Fallback to environment variables
    provider = settings.ATS_MATCHING_LLM_PROVIDER
    model = settings.ATS_MATCHING_LLM_MODEL

    # If model not specified, use default for provider
    if not model:
        if provider == "gemini":
            model = settings.GEMINI_MODEL
        elif provider == "openai":
            model = settings.OPENAI_MODEL
        elif provider == "anthropic":
            model = settings.ANTHROPIC_MODEL
        else:
            # Default fallback
            model = settings.GEMINI_MODEL
            provider = "gemini"

    return (provider, model)


# =============================================================================
# EXAMPLE: Run this file directly to see your settings
# =============================================================================

if __name__ == "__main__":
    """
    Test your configuration by running: python -m app.config

    This will:
    1. Load settings from .env
    2. Print all values (secrets masked)
    3. Show any validation errors
    """
    print("Testing configuration...")

    try:
        # Try to create settings (triggers validation)
        test_settings = Settings()
        print("✅ Configuration loaded successfully!")

        # Print all settings
        print_settings(hide_secrets=True)

        # Show which values came from .env vs defaults
        print("\nEnvironment variable status:")
        print("-" * 80)
        env_vars = os.environ
        for field_name in test_settings.model_dump().keys():
            if field_name in env_vars:
                print(f"✅ {field_name}: Set in environment")
            else:
                print(f"⚠️  {field_name}: Using default value")

    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("\nMake sure you have:")
        print("1. Created a .env file (cp .env.example .env)")
        print("2. Filled in required values")
        print("3. Set DATABASE_URL, SECRET_KEY at minimum")
