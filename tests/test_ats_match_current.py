#!/usr/bin/env python3
"""
Test ATS Matching with Currently Selected LLM Provider

Tests the ATS matching functionality using the model currently configured
in the settings table.
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


def get_current_config():
    """Get current LLM configuration"""
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


def create_test_job(url: str) -> int:
    """Create a test job"""
    db = SessionLocal()
    try:
        job = Job(
            url=url,
            provider="manual",
            status="new_url",
            match_score=1.0,  # Manual jobs get deterministic match_score=1.0
            profile_id=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        print(f"✅ Created test job: job_id={job.job_id}")
        print(f"   URL: {url}")

        return job.job_id

    except Exception as e:
        print(f"❌ Error creating job: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def check_results(job_id: int):
    """Check results"""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            print(f"❌ Job {job_id} not found")
            return

        print(f"\n📊 Job Results:")
        print(f"   job_id: {job.job_id}")
        print(f"   status: {job.status}")
        print(f"   match_score: {job.match_score}")

        application = db.query(Application).filter(
            Application.job_id == job_id
        ).order_by(Application.application_id.desc()).first()

        if application:
            print(f"\n📋 Application Results:")
            print(f"   application_id: {application.application_id}")
            print(f"   status: {application.status}")
            print(f"   ats_id: {application.ats_id}")
            print(f"   ats_name: {application.ats_name}")
            print(f"   company_id: {application.company_id}")
            print(f"   company_name: {application.company_name}")

            log = db.query(LogATSMatch).filter(
                LogATSMatch.application_id == application.application_id
            ).first()

            if log:
                print(f"\n🔍 ATS Matching Log:")
                print(f"   llm_provider_name: {log.llm_provider_name}")
                print(f"   extracted_ats_name: {log.extracted_ats_name}")
                print(f"   best_match_ats_name: {log.best_match_ats_name}")
                print(f"   ats_match_status: {log.ats_match_status}")

                # Success/failure indicator
                if log.ats_match_status == "ats_match":
                    print(f"\n✅ SUCCESS: ATS correctly identified as {log.best_match_ats_name}")
                else:
                    print(f"\n❌ FAILED: Could not match ATS")
                    print(f"   Extracted: {log.extracted_ats_name}")
            else:
                print(f"\n⚠️  No ATS matching log found")
        else:
            print(f"\n⚠️  No application created")

    except Exception as e:
        print(f"❌ Error checking results: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def main():
    """Main test"""
    print_header("ATS Matching Test - Current Configuration")

    # Show current config
    config = get_current_config()
    if not config:
        print("❌ No LLM model configured in settings")
        return

    print(f"\n📝 Current Configuration:")
    print(f"   Provider: {config['provider']}")
    print(f"   Model: {config['model']}")
    print(f"   Model ID: {config['model_id']}")

    # Also check via get_ats_matching_llm_config()
    provider, model = get_ats_matching_llm_config()
    print(f"\n📝 Config from get_ats_matching_llm_config():")
    print(f"   Provider: {provider}")
    print(f"   Model: {model}")

    # Create test job with Greenhouse URL
    print(f"\n{'─' * 80}")
    print("Creating Test Job (Greenhouse URL)")
    print(f"{'─' * 80}")

    test_url = "https://boards.greenhouse.io/anthropic/jobs/4098038008"
    job_id = create_test_job(test_url)

    if not job_id:
        print("❌ Failed to create test job")
        return

    # Run orchestrator
    print(f"\n{'─' * 80}")
    print("Running Orchestrator")
    print(f"{'─' * 80}")

    try:
        result = run_job_lifecycle_orchestrator(job_id)
        print(f"\n✅ Orchestrator completed")
        print(f"   Final job status: {result['job_status']}")

        if result.get('errors'):
            print(f"\n⚠️  Errors encountered:")
            for error in result['errors']:
                print(f"   - {error}")

    except Exception as e:
        print(f"\n❌ Orchestrator failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Check results
    print(f"\n{'─' * 80}")
    print("Final Results")
    print(f"{'─' * 80}")
    check_results(job_id)


if __name__ == "__main__":
    main()
