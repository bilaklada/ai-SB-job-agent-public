#!/usr/bin/env python3
"""
Database Connection Test Script
Tests connection to AWS RDS PostgreSQL database and verifies schema.

Usage:
    python scripts/test_db_connection.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()


def test_connection():
    """Test basic database connection."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        print("   Make sure .env file exists and contains DATABASE_URL")
        return False

    # Mask password in display
    masked_url = database_url
    if "@" in database_url:
        parts = database_url.split("@")
        if ":" in parts[0]:
            user_pass = parts[0].split("://")[-1]
            user = user_pass.split(":")[0]
            masked_url = database_url.replace(user_pass, f"{user}:****")

    print(f"\n🔗 Testing connection to: {masked_url}")
    print("=" * 80)

    try:
        # Create engine
        engine = create_engine(database_url, echo=False)

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print("✅ Connection successful!")
            print(f"📊 PostgreSQL version: {version}")

            # Get database name
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.fetchone()[0]
            print(f"🗄️  Database name: {db_name}")

            # Get connection info
            result = conn.execute(text("SELECT inet_server_addr(), inet_server_port()"))
            server_info = result.fetchone()
            if server_info[0]:
                print(f"🌐 Server address: {server_info[0]}:{server_info[1]}")

            return True

    except OperationalError as e:
        print("❌ Connection failed!")
        print(f"   Error: {str(e)}")
        print("\n🔍 Troubleshooting tips:")
        print("   1. Check if DATABASE_URL in .env is correct")
        print("   2. Verify RDS security group allows your IP address")
        print("   3. Ensure RDS instance is publicly accessible (if connecting remotely)")
        print("   4. Verify database credentials are correct")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


def list_tables():
    """List all tables in the database."""
    database_url = os.getenv("DATABASE_URL")

    try:
        engine = create_engine(database_url, echo=False)
        inspector = inspect(engine)

        tables = inspector.get_table_names()

        print(f"\n📋 Tables in database: {len(tables)}")
        print("=" * 80)

        if not tables:
            print("⚠️  No tables found in database")
            print("   Run the FastAPI application to create tables automatically")
            return False

        for i, table_name in enumerate(tables, 1):
            print(f"{i}. {table_name}")

        return True

    except Exception as e:
        print(f"❌ Error listing tables: {str(e)}")
        return False


def verify_jobs_table():
    """Verify the jobs table structure and contents."""
    database_url = os.getenv("DATABASE_URL")

    try:
        engine = create_engine(database_url, echo=False)
        inspector = inspect(engine)

        # Check if jobs table exists
        tables = inspector.get_table_names()
        if 'jobs' not in tables:
            print("\n❌ 'jobs' table not found!")
            print("   Available tables:", ", ".join(tables) if tables else "None")
            return False

        print("\n✅ 'jobs' table found!")
        print("=" * 80)

        # Get columns
        columns = inspector.get_columns('jobs')
        print(f"\n📊 Columns ({len(columns)}):")
        print("-" * 80)
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f"DEFAULT {col['default']}" if col['default'] else ""
            print(f"  • {col['name']:<20} {str(col['type']):<20} {nullable:<10} {default}")

        # Get indexes
        indexes = inspector.get_indexes('jobs')
        print(f"\n🔍 Indexes ({len(indexes)}):")
        print("-" * 80)
        for idx in indexes:
            unique = "UNIQUE" if idx['unique'] else "NON-UNIQUE"
            cols = ", ".join(idx['column_names'])
            print(f"  • {idx['name']:<35} {unique:<12} ({cols})")

        # Get unique constraints
        unique_constraints = inspector.get_unique_constraints('jobs')
        print(f"\n🔒 Unique Constraints ({len(unique_constraints)}):")
        print("-" * 80)
        for constraint in unique_constraints:
            cols = ", ".join(constraint['column_names'])
            print(f"  • {constraint['name']:<35} ({cols})")

        # Count records
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM jobs"))
            count = result.fetchone()[0]
            print(f"\n📈 Total records in 'jobs' table: {count}")

            if count > 0:
                # Show sample records
                result = conn.execute(text("SELECT id, title, company, status, created_at FROM jobs LIMIT 5"))
                records = result.fetchall()
                print("\n📝 Sample records (first 5):")
                print("-" * 80)
                for record in records:
                    print(f"  ID: {record[0]}")
                    print(f"  Title: {record[1]}")
                    print(f"  Company: {record[2]}")
                    print(f"  Status: {record[3]}")
                    print(f"  Created: {record[4]}")
                    print("-" * 80)

        return True

    except Exception as e:
        print(f"❌ Error verifying jobs table: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_schema_match():
    """Check if database schema matches the expected schema from models.py"""
    print("\n🔍 Schema Validation:")
    print("=" * 80)

    expected_columns = [
        'id', 'title', 'company', 'url', 'description', 'location',
        'country', 'city', 'salary', 'employment_type', 'provider',
        'status', 'match_score', 'created_at', 'updated_at'
    ]

    database_url = os.getenv("DATABASE_URL")

    try:
        engine = create_engine(database_url, echo=False)
        inspector = inspect(engine)

        if 'jobs' not in inspector.get_table_names():
            print("❌ jobs table does not exist")
            return False

        actual_columns = [col['name'] for col in inspector.get_columns('jobs')]

        # Check for missing columns
        missing = set(expected_columns) - set(actual_columns)
        if missing:
            print(f"❌ Missing columns: {', '.join(missing)}")

        # Check for extra columns
        extra = set(actual_columns) - set(expected_columns)
        if extra:
            print(f"⚠️  Extra columns: {', '.join(extra)}")

        if not missing and not extra:
            print(f"✅ Schema matches! All {len(expected_columns)} expected columns present")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ Error checking schema: {str(e)}")
        return False


def main():
    """Main test function."""
    print("\n" + "=" * 80)
    print("🔬 AWS RDS PostgreSQL Connection Test")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    results = {
        "connection": False,
        "tables": False,
        "jobs_table": False,
        "schema": False
    }

    # Test 1: Basic connection
    results["connection"] = test_connection()

    if not results["connection"]:
        print("\n❌ Connection test failed. Stopping here.")
        print("   Fix the connection issue before proceeding.")
        return 1

    # Test 2: List tables
    results["tables"] = list_tables()

    # Test 3: Verify jobs table
    results["jobs_table"] = verify_jobs_table()

    # Test 4: Check schema match
    results["schema"] = check_schema_match()

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name.replace('_', ' ').title()}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Database is ready to use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
