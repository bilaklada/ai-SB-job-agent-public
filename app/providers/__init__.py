"""
Job Provider Adapters

This package contains adapters for various job board APIs (Adzuna, Jooble, Indeed, etc.).
Each provider implements the BaseJobProvider interface to ensure consistency.
"""

from app.providers.base import BaseJobProvider

__all__ = ["BaseJobProvider"]
