#!/usr/bin/env python3
"""
Test ATS Matching with Multiple LLM Providers

This script tests the ATS matching functionality with Gemini, OpenAI, and Anthropic.
It creates a test job, runs the orchestrator, and verifies the results.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.db.models import Job, Application, LogATSMatch, Setting, LLMModel
from app.orchestration.job_lifecycle_graph import run_job_lifecycle_orchestrator
from app.config import get_ats_matching_llm_config
from datetime import datetime


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_section(text):
    """Print formatted section"""
    print(f"\n{'─' * 80}")
    print(f"  {text}")
    print(f"{'─' * 80}")


def get_current_llm_config():
    """Get current LLM configuration from database"""
    db = SessionLocal()
    try:
        setting = db.query(Setting).filter(
            Setting.setting_name == "ats_matching_model"
        ).first()

        if setting and setting.setting_value.get("llm_model_id"):
            model_id = setting.setting_value["llm_model_id"]
            llm_model = db.query(LLMModel).filter(
                LLMModel.llm_model_id == model_id
            ).first()

            if llm_model:
                return {
                    "provider": llm_model.llm_provider_name,
                    "model": llm_model.llm_model_name,
                    "model_id": model_id
                }

        return None
    finally:
        db.close()


def update_ats_matching_model(llm_model_id: int):
    """Update the ats_matching_model setting"""
    db = SessionLocal()
    try:
        setting = db.query(Setting).filter(
            Setting.setting_name == "ats_matching_model"
        ).first()

        if setting:
            setting.setting_value = {"llm_model_id": llm_model_id}
            setting.updated_at = datetime.utcnow()
            db.commit()
            print(f"✅ Updated ats_matching_model to llm_model_id={llm_model_id}")
        else:
            print(f"❌ Setting 'ats_matching_model' not found in database")
    except Exception as e:
        print(f"❌ Error updating setting: {e}")
        db.rollback()
    finally:
        db.close()


def create_test_job(url: str, provider: str = "manual") -> int:
    """Create a test job in the database"""
    db = SessionLocal()
    try:
        # Check if job already exists
        existing = db.query(Job).filter(Job.url == url).first()
        if existing:
            print(f"⚠️  Job already exists: job_id={existing.job_id}")
            return existing.job_id

        # Create new job
        job = Job(
            url=url,
            provider=provider,
            status="new_url",  # Will trigger deterministic match_score=1.0
            match_score=None,  # Will be set by orchestrator
            profile_id=1,  # Assuming profile_id=1 exists
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        print(f"✅ Created test job: job_id={job.job_id}")
        print(f"   URL: {url}")
        print(f"   Status: {job.status}")

        return job.job_id

    except Exception as e:
        print(f"❌ Error creating job: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def check_results(job_id: int):
    """Check the results of ATS matching"""
    db = SessionLocal()
    try:
        # Get job status
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            print(f"❌ Job {job_id} not found")
            return

        print(f"\n📊 Job Status:")
        print(f"   job_id: {job.job_id}")
        print(f"   status: {job.status}")
        print(f"   match_score: {job.match_score}")

        # Get application
        application = db.query(Application).filter(
            Application.job_id == job_id
        ).first()

        if application:
            print(f"\n📋 Application:")
            print(f"   application_id: {application.application_id}")
            print(f"   status: {application.status}")
            print(f"   ats_id: {application.ats_id}")
            print(f"   ats_name: {application.ats_name}")
            print(f"   company_id: {application.company_id}")
            print(f"   company_name: {application.company_name}")

            # Get ATS matching log
            log = db.query(LogATSMatch).filter(
                LogATSMatch.application_id == application.application_id
            ).first()

            if log:
                print(f"\n🔍 ATS Matching Log:")
                print(f"   lam_id: {log.lam_id}")
                print(f"   llm_provider_name: {log.llm_provider_name}")
                print(f"   extracted_ats_name: {log.extracted_ats_name}")
                print(f"   best_match_ats_name: {log.best_match_ats_name}")
                print(f"   ats_match_status: {log.ats_match_status}")
                print(f"   html_snapshot (length): {len(log.html_snapshot)} characters")
            else:
                print(f"\n⚠️  No ATS matching log found")
        else:
            print(f"\n⚠️  No application created")

    except Exception as e:
        print(f"❌ Error checking results: {e}")
    finally:
        db.close()


def test_provider(provider_name: str, model_name: str, llm_model_id: int):
    """Test a specific LLM provider"""
    print_header(f"Testing {provider_name}: {model_name}")

    # Update settings to use this model
    update_ats_matching_model(llm_model_id)

    # Verify config
    provider, model = get_ats_matching_llm_config()
    print(f"\n📝 Configuration:")
    print(f"   Provider: {provider}")
    print(f"   Model: {model}")

    # Create test job (Greenhouse URL - known ATS)
    test_url = "https://boards.greenhouse.io/example/jobs/123456"
    print_section("Creating Test Job")
    job_id = create_test_job(test_url)

    if not job_id:
        print(f"❌ Failed to create test job")
        return False

    # Run orchestrator
    print_section("Running Orchestrator")
    try:
        result = run_job_lifecycle_orchestrator(job_id)
        print(f"✅ Orchestrator completed")
        print(f"   Final status: {result['job_status']}")
        print(f"   Errors: {len(result.get('errors', []))}")

        if result.get('errors'):
            for error in result['errors']:
                print(f"   ⚠️  {error}")

    except Exception as e:
        print(f"❌ Orchestrator failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Check results
    print_section("Checking Results")
    check_results(job_id)

    return True


def main():
    """Main test function"""
    print_header("ATS Matching Multi-Provider Test")

    # Show current config
    print_section("Current Configuration")
    config = get_current_llm_config()
    if config:
        print(f"Current LLM Model:")
        print(f"  Provider: {config['provider']}")
        print(f"  Model: {config['model']}")
        print(f"  Model ID: {config['model_id']}")
    else:
        print("⚠️  No LLM model configured")

    # Test providers
    tests = [
        ("Gemini", "gemini-2.5-flash-lite", 5),
        ("OpenAI", "gpt-4o-mini", 8),  # Assuming gpt-5-mini is a typo, using ID 8
        ("Anthropic", "claude-sonnet-4-5-20250929", 10),
    ]

    results = {}

    for provider, model, model_id in tests:
        success = test_provider(provider, model, model_id)
        results[provider] = success

        input(f"\n⏸️  Press Enter to continue to next provider...")

    # Summary
    print_header("Test Summary")
    for provider, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{provider}: {status}")


if __name__ == "__main__":
    main()
