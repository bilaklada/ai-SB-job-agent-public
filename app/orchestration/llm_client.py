"""
Multi-Provider LLM Client

Unified interface for Gemini, OpenAI, and Anthropic LLM providers.
Handles token extraction from provider-specific response formats and cost calculation.

Usage:
    from app.orchestration.llm_client import LLMClient

    # Use default provider from config
    client = LLMClient()
    response_text, metadata = client.invoke(prompt)

    # Override provider/model
    client = LLMClient(provider='openai', model='gpt-4o')
    response_text, metadata = client.invoke(prompt)
"""

import os
import time
import logging
from typing import Dict, Any, Tuple, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Provider imports with availability flags
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("[LLMClient] langchain-google-genai not installed - Gemini unavailable")

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("[LLMClient] langchain-openai not installed - OpenAI unavailable")

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("[LLMClient] langchain-anthropic not installed - Anthropic unavailable")


class LLMClient:
    """
    Unified client for multiple LLM providers.

    Provides a consistent interface for Gemini, OpenAI, and Anthropic,
    handling provider-specific token extraction and cost calculation.
    """

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize LLM client.

        Args:
            provider: LLM provider ('gemini', 'openai', 'anthropic')
                     If None, uses settings.ATS_MATCHING_LLM_PROVIDER
            model: Model name (e.g., 'gpt-4o-mini')
                  If None, uses default for the provider

        Raises:
            ValueError: If provider is unsupported or not available
        """
        self.provider = provider or settings.ATS_MATCHING_LLM_PROVIDER
        self.model = model or self._get_default_model(self.provider)

        logger.info(f"[LLMClient] Initializing provider={self.provider}, model={self.model}")

        self._check_availability()
        self._initialize_client()

    def _get_default_model(self, provider: str) -> str:
        """Get default model for provider from settings."""
        # Check if user specified override
        if settings.ATS_MATCHING_LLM_MODEL:
            return settings.ATS_MATCHING_LLM_MODEL

        # Use provider-specific defaults
        defaults = {
            'gemini': settings.GEMINI_MODEL,
            'openai': settings.OPENAI_MODEL,
            'anthropic': settings.ANTHROPIC_MODEL,
        }

        return defaults.get(provider, '')

    def _check_availability(self):
        """Check if provider is available."""
        availability = {
            'gemini': GEMINI_AVAILABLE,
            'openai': OPENAI_AVAILABLE,
            'anthropic': ANTHROPIC_AVAILABLE,
        }

        if self.provider not in availability:
            raise ValueError(
                f"Unsupported provider: {self.provider}. "
                f"Supported: {list(availability.keys())}"
            )

        if not availability[self.provider]:
            raise ValueError(
                f"Provider '{self.provider}' not available. "
                f"Install required package: langchain-{self.provider}"
            )

    def _initialize_client(self):
        """Initialize provider-specific LLM client."""
        if self.provider == 'gemini':
            api_key = os.getenv('GEMINI_API_KEY') or settings.GEMINI_API_KEY
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set in environment or config")

            self.llm = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=api_key,
                temperature=0.0  # Deterministic output for ATS matching
            )
            logger.info(f"[LLMClient] Gemini initialized: {self.model}")

        elif self.provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY') or settings.OPENAI_API_KEY
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in environment or config")

            self.llm = ChatOpenAI(
                model=self.model,
                openai_api_key=api_key,
                temperature=0.0
            )
            logger.info(f"[LLMClient] OpenAI initialized: {self.model}")

        elif self.provider == 'anthropic':
            api_key = os.getenv('ANTHROPIC_API_KEY') or settings.ANTHROPIC_API_KEY
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in environment or config")

            self.llm = ChatAnthropic(
                model=self.model,
                anthropic_api_key=api_key,
                temperature=0.0
            )
            logger.info(f"[LLMClient] Anthropic initialized: {self.model}")

    def invoke(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """
        Invoke LLM and return response with metadata.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Tuple of (response_text, metadata_dict)

            metadata_dict contains:
            - llm_provider: str (provider name)
            - llm_model: str (model name)
            - prompt_tokens: int | None
            - completion_tokens: int | None
            - total_tokens: int | None
            - latency_ms: int | None
            - cost_usd: float | None (calculated from tokens)
            - error_message: str | None

        Example:
            >>> client = LLMClient()
            >>> text, meta = client.invoke("What is 2+2?")
            >>> print(text)
            "4"
            >>> print(meta['cost_usd'])
            0.00000125
        """
        metadata = {
            'llm_provider': self.provider,
            'llm_model': self.model,
            'prompt_tokens': None,
            'completion_tokens': None,
            'total_tokens': None,
            'latency_ms': None,
            'cost_usd': None,
            'error_message': None,
        }

        try:
            # Measure latency
            start_time = time.time()
            response = self.llm.invoke(prompt)
            end_time = time.time()

            # Extract response text
            response_text = response.content.strip()
            metadata['latency_ms'] = int((end_time - start_time) * 1000)

            # Extract token usage from provider-specific response
            self._extract_token_usage(response, metadata)

            # Calculate cost from tokens
            if metadata['prompt_tokens'] and metadata['completion_tokens']:
                from app.orchestration.llm_providers import calculate_cost
                metadata['cost_usd'] = calculate_cost(
                    self.provider,
                    self.model,
                    metadata['prompt_tokens'],
                    metadata['completion_tokens']
                )

            logger.info(
                f"[LLMClient] Success - {self.provider}/{self.model}: "
                f"tokens={metadata['total_tokens']}, "
                f"cost=${metadata['cost_usd'] or 0:.6f}, "
                f"latency={metadata['latency_ms']}ms"
            )

            return response_text, metadata

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[LLMClient] Error: {error_msg}", exc_info=True)
            metadata['error_message'] = error_msg
            return '', metadata

    def _extract_token_usage(self, response, metadata: Dict[str, Any]):
        """
        Extract token usage from provider-specific response format.

        Each provider returns usage metadata in different formats:
        - OpenAI: response.response_metadata['token_usage']
        - Anthropic: response.response_metadata['usage']
        - Gemini: response.response_metadata['usage_metadata']

        Args:
            response: LLM response object
            metadata: Dict to populate with token counts
        """
        if not hasattr(response, 'response_metadata'):
            logger.warning("[LLMClient] Response has no response_metadata")
            return

        resp_meta = response.response_metadata

        # OpenAI format
        if 'token_usage' in resp_meta:
            usage = resp_meta['token_usage']
            metadata['prompt_tokens'] = usage.get('prompt_tokens')
            metadata['completion_tokens'] = usage.get('completion_tokens')
            metadata['total_tokens'] = usage.get('total_tokens')
            logger.debug(f"[LLMClient] OpenAI tokens: {metadata['total_tokens']}")

        # Anthropic format
        elif 'usage' in resp_meta:
            usage = resp_meta['usage']
            metadata['prompt_tokens'] = usage.get('input_tokens')
            metadata['completion_tokens'] = usage.get('output_tokens')
            metadata['total_tokens'] = (
                (usage.get('input_tokens', 0) + usage.get('output_tokens', 0))
                if usage.get('input_tokens') and usage.get('output_tokens')
                else None
            )
            logger.debug(f"[LLMClient] Anthropic tokens: {metadata['total_tokens']}")

        # Gemini format
        elif 'usage_metadata' in resp_meta:
            usage = resp_meta['usage_metadata']
            metadata['prompt_tokens'] = usage.get('prompt_token_count')
            metadata['completion_tokens'] = usage.get('candidates_token_count')
            metadata['total_tokens'] = usage.get('total_token_count')
            logger.debug(f"[LLMClient] Gemini tokens: {metadata['total_tokens']}")

        else:
            logger.warning(
                f"[LLMClient] Unknown metadata format for {self.provider}. "
                f"Available keys: {list(resp_meta.keys())}"
            )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_available_providers() -> list[str]:
    """
    Get list of currently available LLM providers.

    Returns:
        List of provider names that are installed and available

    Example:
        >>> get_available_providers()
        ['gemini', 'openai']  # anthropic not installed
    """
    available = []
    if GEMINI_AVAILABLE:
        available.append('gemini')
    if OPENAI_AVAILABLE:
        available.append('openai')
    if ANTHROPIC_AVAILABLE:
        available.append('anthropic')
    return available


def check_provider_config(provider: str) -> bool:
    """
    Check if provider is configured with API key.

    Args:
        provider: Provider name

    Returns:
        True if API key is set, False otherwise

    Example:
        >>> check_provider_config('gemini')
        True  # GEMINI_API_KEY is set
    """
    api_keys = {
        'gemini': os.getenv('GEMINI_API_KEY') or settings.GEMINI_API_KEY,
        'openai': os.getenv('OPENAI_API_KEY') or settings.OPENAI_API_KEY,
        'anthropic': os.getenv('ANTHROPIC_API_KEY') or settings.ANTHROPIC_API_KEY,
    }

    return bool(api_keys.get(provider))
