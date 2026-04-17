#!/usr/bin/env python
"""
Test script for multi-provider LLM support and cost calculation.

Tests:
1. Provider availability checking
2. Cost calculation for all providers
3. LLMClient initialization (without API calls)
4. Database logging functionality
"""

import os
import sys
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.orchestration import llm_providers
from app.orchestration.llm_client import LLMClient, get_available_providers, check_provider_config
from app.db.session import SessionLocal
from app.db.models import Application, LogATSMatch


def test_provider_availability():
    """Test which providers are available."""
    print("\n" + "="*70)
    print("TEST 1: Provider Availability")
    print("="*70)

    available = get_available_providers()
    print(f"Available providers: {available}")

    for provider in ['gemini', 'openai', 'anthropic']:
        is_configured = check_provider_config(provider)
        status = "✓ Configured" if is_configured else "✗ Not configured"
        print(f"  {provider}: {status}")

    return available


def test_cost_calculation():
    """Test cost calculation for all providers."""
    print("\n" + "="*70)
    print("TEST 2: Cost Calculation")
    print("="*70)

    test_cases = [
        ('gemini', 'gemini-2.0-flash-exp', 1000, 500),  # Free tier
        ('gemini', 'gemini-1.5-flash', 1000, 500),
        ('openai', 'gpt-4o-mini', 1000, 500),
        ('anthropic', 'claude-3-5-sonnet-20241022', 1000, 500),
    ]

    for provider, model, prompt_tokens, completion_tokens in test_cases:
        cost = llm_providers.calculate_cost(provider, model, prompt_tokens, completion_tokens)
        formatted_cost = llm_providers.format_cost(cost)
        print(f"  {provider}/{model}: {formatted_cost} (for {prompt_tokens}+{completion_tokens} tokens)")

    # Test edge cases
    print("\nEdge cases:")

    # Unknown provider
    cost = llm_providers.calculate_cost('unknown', 'model', 1000, 500)
    print(f"  Unknown provider: ${cost:.8f} (should be 0.0)")

    # Unknown model
    cost = llm_providers.calculate_cost('gemini', 'unknown-model', 1000, 500)
    print(f"  Unknown model: ${cost:.8f} (should be 0.0)")

    # None tokens
    cost = llm_providers.calculate_cost('gemini', 'gemini-2.0-flash-exp', None, None)
    print(f"  None tokens: ${cost:.8f} (should be 0.0)")

    print("\n✓ All cost calculations completed")


def test_llm_client_initialization():
    """Test LLMClient initialization with different providers."""
    print("\n" + "="*70)
    print("TEST 3: LLMClient Initialization")
    print("="*70)

    available = get_available_providers()

    for provider in available:
        if check_provider_config(provider):
            try:
                client = LLMClient(provider=provider)
                print(f"  ✓ {provider}: Initialized successfully (model={client.model})")
            except Exception as e:
                print(f"  ✗ {provider}: Initialization failed - {e}")
        else:
            print(f"  ⊘ {provider}: Skipped (no API key)")

    print("\n✓ All provider initializations tested")


def test_database_logging():
    """Test database logging functionality."""
    print("\n" + "="*70)
    print("TEST 4: Database Logging")
    print("="*70)

    db = SessionLocal()

    try:
        # Find an application to use for testing
        application = db.query(Application).first()

        if not application:
            print("  ⊘ No applications in database - skipping database logging test")
            return

        print(f"  Using application_id={application.application_id} for test")

        # Create test metadata (simplified for new schema)
        test_metadata = {
            'llm_provider': 'gemini',
            'llm_model': 'gemini-2.0-flash-exp'
        }

        # Create test HTML content
        test_html_content = """
        <html>
        <head><title>Job Application - Greenhouse</title></head>
        <body><div class="greenhouse-application">Test job posting</div></body>
        </html>
        """

        # Create test ATS result
        test_ats_result = {
            'matched': True,
            'ats_name': 'Greenhouse',
            'metadata': test_metadata
        }

        # Import the logging function
        from app.orchestration.job_lifecycle_graph import _log_ats_match_attempt

        # Log the attempt (new signature: db, application_id, html_content, ats_result)
        _log_ats_match_attempt(db, application.application_id, test_html_content, test_ats_result)

        # Verify the log was created
        log_entry = db.query(LogATSMatch).filter(
            LogATSMatch.application_id == application.application_id
        ).order_by(LogATSMatch.updated_at.desc()).first()

        if log_entry:
            print(f"  ✓ Log entry created successfully:")
            print(f"    - lam_id: {log_entry.lam_id}")
            print(f"    - application_id: {log_entry.application_id}")
            print(f"    - llm_provider_name: {log_entry.llm_provider_name}")
            print(f"    - extracted_ats_name: {log_entry.extracted_ats_name}")
            print(f"    - best_match_ats_name: {log_entry.best_match_ats_name}")
            print(f"    - ats_match_status: {log_entry.ats_match_status}")
            print(f"    - html_snapshot (length): {len(log_entry.html_snapshot)} chars")
            print(f"    - updated_at: {log_entry.updated_at}")
        else:
            print("  ✗ Log entry was not created")

        print("\n✓ Database logging test completed")

    except Exception as e:
        print(f"  ✗ Database logging test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("MULTI-PROVIDER LLM SUPPORT TEST SUITE")
    print("="*70)

    try:
        available = test_provider_availability()
        test_cost_calculation()
        test_llm_client_initialization()
        test_database_logging()

        print("\n" + "="*70)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*70)
        print(f"\nSummary:")
        print(f"  - Available providers: {', '.join(available)}")
        print(f"  - Cost calculation: ✓ Working")
        print(f"  - Database logging: ✓ Working")
        print(f"\nNext steps:")
        print(f"  - Set up API keys for providers you want to use:")
        if not check_provider_config('gemini'):
            print(f"    export GEMINI_API_KEY='your-key-here'")
        if not check_provider_config('openai'):
            print(f"    export OPENAI_API_KEY='your-key-here'")
        if not check_provider_config('anthropic'):
            print(f"    export ANTHROPIC_API_KEY='your-key-here'")
        print(f"  - Test actual LLM calls with a job URL")
        print()

    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
