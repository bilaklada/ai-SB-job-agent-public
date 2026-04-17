"""
LLM Provider Pricing Configuration

This module contains hardcoded pricing information for different LLM providers
and models, used to calculate costs for ATS matching and other AI operations.

Pricing is in USD per 1 million tokens (input and output separately).
Prices are current as of December 2024 and should be updated periodically.

Sources:
- Google Gemini: https://ai.google.dev/pricing
- OpenAI: https://openai.com/pricing
- Anthropic: https://www.anthropic.com/pricing
"""

import logging

logger = logging.getLogger(__name__)

# =============================================================================
# PRICING DICTIONARY (USD per 1M tokens)
# =============================================================================

LLM_PRICING = {
    'gemini': {
        # Free tier models
        'gemini-2.0-flash-exp': {
            'input': 0.0,      # Free tier (experimental)
            'output': 0.0      # Free tier (experimental)
        },
        # Production models
        'gemini-1.5-flash': {
            'input': 0.000075,   # $0.075 per 1M tokens
            'output': 0.0003     # $0.30 per 1M tokens
        },
        'gemini-1.5-pro': {
            'input': 0.00125,    # $1.25 per 1M tokens
            'output': 0.005      # $5 per 1M tokens
        },
    },
    'openai': {
        'gpt-4o': {
            'input': 0.0025,     # $2.50 per 1M tokens
            'output': 0.01       # $10 per 1M tokens
        },
        'gpt-4o-mini': {
            'input': 0.00015,    # $0.15 per 1M tokens
            'output': 0.0006     # $0.60 per 1M tokens
        },
        'gpt-3.5-turbo': {
            'input': 0.0005,     # $0.50 per 1M tokens
            'output': 0.0015     # $1.50 per 1M tokens
        },
    },
    'anthropic': {
        'claude-3-5-sonnet-20241022': {
            'input': 0.003,      # $3 per 1M tokens
            'output': 0.015      # $15 per 1M tokens
        },
        'claude-3-haiku-20240307': {
            'input': 0.00025,    # $0.25 per 1M tokens
            'output': 0.00125    # $1.25 per 1M tokens
        },
        'claude-3-opus-20240229': {
            'input': 0.015,      # $15 per 1M tokens
            'output': 0.075      # $75 per 1M tokens
        },
    },
}


# =============================================================================
# COST CALCULATION FUNCTION
# =============================================================================

def calculate_cost(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int
) -> float:
    """
    Calculate cost in USD for an LLM call based on token usage.

    Args:
        provider: LLM provider ('gemini', 'openai', 'anthropic')
        model: Model name (e.g., 'gpt-4o-mini', 'claude-3-5-sonnet-20241022')
        prompt_tokens: Number of input/prompt tokens
        completion_tokens: Number of output/completion tokens

    Returns:
        Cost in USD (rounded to 8 decimal places for precision)
        Returns 0.0 if provider/model not in pricing dictionary

    Examples:
        >>> calculate_cost('openai', 'gpt-4o-mini', 1000, 500)
        0.00045  # $0.00045 for 1K input + 500 output tokens

        >>> calculate_cost('gemini', 'gemini-2.0-flash-exp', 5000, 2000)
        0.0  # Free tier

        >>> calculate_cost('anthropic', 'claude-3-5-sonnet-20241022', 2000, 800)
        0.018  # $0.006 input + $0.012 output
    """
    # Validate inputs
    if not provider or not model:
        logger.warning(
            f"[calculate_cost] Missing provider ({provider}) or model ({model})"
        )
        return 0.0

    if prompt_tokens is None or completion_tokens is None:
        logger.warning(
            f"[calculate_cost] Missing token counts: "
            f"prompt={prompt_tokens}, completion={completion_tokens}"
        )
        return 0.0

    # Check if provider exists in pricing dictionary
    if provider not in LLM_PRICING:
        logger.warning(
            f"[calculate_cost] Unknown provider '{provider}'. "
            f"Available: {list(LLM_PRICING.keys())}"
        )
        return 0.0

    # Check if model exists for this provider
    if model not in LLM_PRICING[provider]:
        logger.warning(
            f"[calculate_cost] Unknown model '{model}' for provider '{provider}'. "
            f"Available: {list(LLM_PRICING[provider].keys())}"
        )
        return 0.0

    # Get pricing for this model
    pricing = LLM_PRICING[provider][model]

    # Calculate cost (pricing is per 1M tokens, so divide by 1,000,000)
    input_cost = (prompt_tokens / 1_000_000.0) * pricing['input']
    output_cost = (completion_tokens / 1_000_000.0) * pricing['output']
    total_cost = input_cost + output_cost

    # Round to 8 decimal places (matches NUMERIC(10, 8) in database)
    return round(total_cost, 8)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_provider_models(provider: str) -> list[str]:
    """
    Get list of available models for a provider.

    Args:
        provider: LLM provider name

    Returns:
        List of model names for this provider, empty list if provider unknown

    Example:
        >>> get_provider_models('openai')
        ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo']
    """
    return list(LLM_PRICING.get(provider, {}).keys())


def get_all_providers() -> list[str]:
    """
    Get list of all supported providers.

    Returns:
        List of provider names

    Example:
        >>> get_all_providers()
        ['gemini', 'openai', 'anthropic']
    """
    return list(LLM_PRICING.keys())


def estimate_cost_range(
    provider: str,
    model: str,
    min_tokens: int = 1000,
    max_tokens: int = 10000
) -> dict:
    """
    Estimate cost range for typical usage.

    Args:
        provider: LLM provider
        model: Model name
        min_tokens: Minimum token count (default: 1000)
        max_tokens: Maximum token count (default: 10000)

    Returns:
        Dict with min_cost, max_cost, avg_cost

    Example:
        >>> estimate_cost_range('openai', 'gpt-4o-mini', 2000, 5000)
        {
            'min_cost': 0.0003,  # 2K input + 1K output
            'max_cost': 0.00105,  # 5K input + 2.5K output
            'avg_cost': 0.000675
        }
    """
    # Assume output is ~50% of input
    min_output = int(min_tokens * 0.5)
    max_output = int(max_tokens * 0.5)

    min_cost = calculate_cost(provider, model, min_tokens, min_output)
    max_cost = calculate_cost(provider, model, max_tokens, max_output)
    avg_cost = (min_cost + max_cost) / 2.0

    return {
        'min_cost': min_cost,
        'max_cost': max_cost,
        'avg_cost': round(avg_cost, 8)
    }


# =============================================================================
# COST REPORTING
# =============================================================================

def format_cost(cost_usd: float) -> str:
    """
    Format cost as human-readable string.

    Args:
        cost_usd: Cost in USD

    Returns:
        Formatted string with appropriate precision

    Examples:
        >>> format_cost(0.00045)
        '$0.00045'

        >>> format_cost(0.0)
        '$0.00 (free)'

        >>> format_cost(1.234567)
        '$1.23'
    """
    if cost_usd == 0.0:
        return "$0.00 (free)"
    elif cost_usd < 0.01:
        return f"${cost_usd:.6f}"
    else:
        return f"${cost_usd:.2f}"
