#!/usr/bin/env python3
"""
Test script to verify application_id sequence is working correctly.
"""
from app.db.session import SessionLocal
from app.db.models import Application
from datetime import datetime

def test_application_sequence():
    """Test that application_id auto-increments properly."""
    db = SessionLocal()

    try:
        print("Testing application_id sequence...")

        # Try to create a test application (without specifying application_id)
        # This should auto-generate the ID from the sequence
        test_app = Application(
            job_id=1,  # Assuming job with ID 1 exists
            profile_id=1,  # Assuming profile with ID 1 exists
            status='created',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(test_app)
        db.flush()  # Get the ID without committing

        print(f"✅ SUCCESS: Application created with auto-generated ID: {test_app.application_id}")
        print(f"   - job_id: {test_app.job_id}")
        print(f"   - profile_id: {test_app.profile_id}")
        print(f"   - status: {test_app.status}")

        # Rollback to avoid cluttering the database with test data
        db.rollback()
        print("   (Test data rolled back)")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        db.rollback()
        return False

    finally:
        db.close()

if __name__ == "__main__":
    success = test_application_sequence()
    exit(0 if success else 1)
