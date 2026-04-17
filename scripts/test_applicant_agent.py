#!/usr/bin/env python3
"""
Test script for Applicant Agent - POC Mode

This script tests the complete job application workflow WITHOUT actually submitting:
1. Fetches oldest job with status='new' from database
2. Runs the LangGraph applicant agent
3. Agent navigates to job page and fills form
4. STOPS before final submission (POC test)
5. Updates job status to 'poc_test' if successful

Usage:
    python scripts/test_applicant_agent.py

    # Or with specific job ID:
    python scripts/test_applicant_agent.py --job-id 123

Requirements:
    - Database must have at least one job with status='new'
    - GEMINI_API_KEY must be set in .env
    - Docker container must be running with Playwright installed
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.applicant_agent import run_applicant_agent
from app.db.session import SessionLocal
from app.services.jobs_service import get_job_by_status


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Test Applicant Agent (POC Mode)")
    parser.add_argument('--job-id', type=int, help='Specific job ID to test (optional)')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()

    print_section("🤖 APPLICANT AGENT TEST (POC MODE)")
    print("⚠️  POC Mode: Form will be filled but NOT submitted")

    # Check Gemini API key
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ ERROR: GEMINI_API_KEY not set in environment")
        print("   Please add GEMINI_API_KEY to your .env file")
        sys.exit(1)
    print(f"✅ Gemini API key configured (length: {len(gemini_key)})")

    # Connect to database
    print_section("📊 DATABASE CONNECTION")
    db = SessionLocal()

    try:
        # Fetch job from database
        if args.job_id:
            print(f"Fetching job ID: {args.job_id}")
            from app.db.models import Job
            job = db.query(Job).filter(Job.id == args.job_id).first()
        else:
            print("Fetching oldest job with status='new'")
            job = get_job_by_status(db, status="new", limit=1)

        if not job:
            print("❌ ERROR: No job found")
            if args.job_id:
                print(f"   Job ID {args.job_id} does not exist")
            else:
                print("   No jobs with status='new' in database")
                print("\n💡 TIP: Fetch jobs first with:")
                print("   curl -X POST http://localhost:8000/jobs/fetch-from-adzuna \\")
                print("     -H 'Content-Type: application/json' \\")
                print("     -d '{\"query\": \"python developer\", \"country\": \"ch\"}'")
            sys.exit(1)

        # Display job details
        print(f"\n✅ Found job:")
        print(f"   ID:          {job.id}")
        print(f"   Title:       {job.title}")
        print(f"   Company:     {job.company}")
        print(f"   Location:    {job.location_city}, {job.location_country}")
        print(f"   URL:         {job.url}")
        print(f"   Status:      {job.status}")
        print(f"   Created:     {job.created_at}")
        print(f"   Provider:    {job.provider}")

    finally:
        db.close()

    # Load fake user profile for testing
    print_section("👤 USER PROFILE (FAKE TEST DATA)")
    user_data = {
        "first_name": "Alexandra",
        "last_name": "Testington",
        "email": "alex.test@example-fake.com",
        "phone": "+41791234567",
        "location": "Zurich, Switzerland",
        "linkedin": "https://linkedin.com/in/test-profile",
        "github": "https://github.com/testuser",
        "website": "https://testportfolio.example.com",
        "years_experience": 5,
        "current_company": "Test Corp AG",
        "current_title": "Senior Software Engineer",
        "education": "MSc Computer Science, ETH Zurich",
        "skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "AWS", "React"],
        "languages": ["English (Fluent)", "German (B2)", "French (A2)"],
        "visa_status": "Swiss work permit (B)",
        "notice_period": "2 months",
        "salary_expectation": "120000 CHF/year",
        "availability": "Immediately",
        "cover_letter": "I am very interested in this position and believe my skills would be a great fit...",
    }
    print("Using fake test profile (will NOT be submitted):")
    print(f"   Name:         {user_data['first_name']} {user_data['last_name']}")
    print(f"   Email:        {user_data['email']}")
    print(f"   Phone:        {user_data['phone']}")
    print(f"   Location:     {user_data['location']}")
    print(f"   Experience:   {user_data['years_experience']} years")
    print(f"   Skills:       {', '.join(user_data['skills'][:4])}...")

    # Confirm before running
    print_section("⚠️  CONFIRMATION")
    print("✅ POC Mode: Agent will STOP before submitting the form")
    print("\nThe agent will:")
    print("   1. Navigate to the job URL using Browser-Use + Gemini")
    print("   2. Attempt to fill out the application form with FAKE data")
    print("   3. STOP before clicking the final submit button")
    print("   4. Update database status to 'poc_test' if successful")
    print("\n⏱️  This may take 2-5 minutes depending on complexity.")
    print("\n✅ Safe to run - NO real application will be submitted")

    if not args.yes:
        response = input("\nContinue? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ Test cancelled")
            sys.exit(0)
    else:
        print("\n✅ Auto-confirmed (--yes flag)")


    # Run the agent
    print_section("🚀 RUNNING APPLICANT AGENT (POC MODE)")
    print(f"Job: {job.title} at {job.company}")
    print(f"URL: {job.url}")
    print("\nAgent workflow:")
    print("  1. Fetch job from database")
    print("  2. Analyze portal type")
    print("  3. Choose automation strategy (Playwright or Browser-Use)")
    print("  4. Execute automation (fill form, DO NOT submit)")
    print("  5. Update database with result")
    print("\n" + "="*80)

    try:
        # Run the applicant agent
        result = run_applicant_agent(
            job_id=job.id,
            job_url=job.url,
            company=job.company,
            title=job.title,
            user_data=user_data
        )

        # Display results
        print_section("📊 RESULTS")
        print(f"Success:           {result['success']}")
        print(f"Portal Type:       {result['portal_type']}")
        print(f"Strategy Used:     {result['automation_strategy']}")
        print(f"Current Step:      {result['current_step']}")

        if result['application_submitted_at']:
            print(f"Test Completed At: {result['application_submitted_at']}")

        # Display logs
        if result['logs']:
            print_section("📝 EXECUTION LOGS")
            for i, log in enumerate(result['logs'], 1):
                print(f"{i}. {log}")

        # Display errors
        if result['errors']:
            print_section("❌ ERRORS")
            for i, error in enumerate(result['errors'], 1):
                print(f"{i}. {error}")

        # Display screenshots
        if result['screenshots']:
            print_section("📸 SCREENSHOTS")
            for screenshot in result['screenshots']:
                print(f"   {screenshot}")

        # Final status
        print_section("✅ TEST COMPLETE")
        if result['success']:
            print("🎉 POC Test Successful!")
            print(f"✅ Agent navigated to job page and filled form successfully")
            print(f"✅ Job {job.id} status updated to 'poc_test' in database")
            print("\n💡 This means:")
            print("   - Agent can navigate to job URLs")
            print("   - Agent can identify and fill form fields")
            print("   - Form filling logic works correctly")
            print("\n📋 Next steps:")
            print("   - Review logs above to verify correct fields were filled")
            print("   - Check screenshots if available")
            print("   - When ready for production, remove POC mode")
        else:
            print("❌ POC Test Failed")
            print(f"⚠️  Job {job.id} status updated to 'application_failed' in database")
            print("\n💡 Check errors above for details")

    except Exception as e:
        print_section("💥 EXCEPTION")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
