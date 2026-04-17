"""
session.py - Database Session Management

================================================================================
WHAT THIS FILE DOES:
================================================================================
This is the central configuration point for ALL database operations in the app.
It sets up the connection to your database and provides tools for talking to it.

Think of it like setting up a phone connection:
- Engine = The telephone line (connection infrastructure)
- SessionLocal = Phone session factory (makes new calls)
- Base = Template for all database tables (defines structure)
- get_db() = A phone call that automatically hangs up when done

================================================================================
HOW IT CONNECTS TO THE REST OF THE PROJECT:
================================================================================

1. app/config.py → Provides DATABASE_URL from .env file
   ↓
2. THIS FILE (session.py) → Creates engine and SessionLocal
   ↓
3. app/db/models.py → Defines tables (Job, Application, etc.) using Base
   ↓
4. app/api/routes_*.py → Uses get_db() to access database in API endpoints
   ↓
5. app/services/*.py → Uses database sessions to perform business logic

================================================================================
SQLAlchemy 2.0 ARCHITECTURE OVERVIEW:
================================================================================

Component          Purpose                           Real-World Analogy
-----------        --------------------------------  ----------------------
Engine             Physical connection to database   Telephone network
SessionLocal       Creates new sessions on demand    Phone session factory
Session            Active connection/transaction     Active phone call
Base               Parent class for all models       Blueprint/template
Model (Job, etc.)  Database table definition         Actual table schema

================================================================================
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

# SQLAlchemy core imports
from sqlalchemy import create_engine
# create_engine: Creates the "engine" - the core interface to the database
# Think of it as establishing the phone line to your database server

from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
# sessionmaker: Factory that creates database sessions (connections)
# DeclarativeBase: Base class for defining ORM models (tables)
# Session: Type hint for database sessions (for IDE autocomplete)

# Typing for better IDE support and type checking
from typing import Generator
# Generator: Type hint for functions that yield values (like get_db)

# Import settings from our configuration system
from app.config import settings
# settings: Loads DATABASE_URL from .env file
# This allows us to change databases without modifying code


# =============================================================================
# BASE CLASS FOR ALL DATABASE MODELS
# =============================================================================

class Base(DeclarativeBase):
    """
    Base class for all ORM (Object-Relational Mapping) models.

    WHAT IS THIS?
    -------------
    This is the parent class that all your database table classes inherit from.
    It provides the magic that converts Python classes into database tables.

    HOW IT WORKS:
    -------------
    When you define a model like this:

        class Job(Base):
            __tablename__ = "jobs"
            id = Column(Integer, primary_key=True)
            title = Column(String)

    SQLAlchemy automatically:
    1. Creates a "jobs" table in the database
    2. Adds "id" and "title" columns
    3. Provides methods to query, insert, update, delete rows

    WHERE IT'S USED:
    ----------------
    - app/db/models.py: All models (Job, Application, Account) inherit from Base
    - app/main.py: Base.metadata.create_all(engine) creates all tables on startup

    SQLALCHEMY 2.0 NOTES:
    ---------------------
    We use DeclarativeBase (new in SQLAlchemy 2.0) instead of the old
    declarative_base() function. This provides:
    - Better type hints
    - Better IDE autocomplete
    - More explicit and modern API
    """
    pass  # No implementation needed - DeclarativeBase provides everything


# =============================================================================
# DATABASE ENGINE - THE CORE CONNECTION
# =============================================================================

# Create the database engine using the URL from our configuration
# The engine is the "phone line" to your database

# Determine connect_args based on database type
# SQLite requires check_same_thread=False for FastAPI's multi-threading
# PostgreSQL doesn't need (and doesn't support) this parameter
connect_args = {}
if "sqlite" in settings.DATABASE_URL.lower():
    connect_args = {"check_same_thread": False}

engine = create_engine(
    # DATABASE_URL comes from .env file via app/config.py
    # Example: postgresql://user:password@localhost:5432/dbname
    settings.DATABASE_URL,

    # connect_args: Database-specific connection parameters
    # Only set for SQLite - PostgreSQL doesn't need extra config
    connect_args=connect_args,

    # Optional: Enable SQL query logging for debugging
    # Uncomment the line below to see all SQL queries in the console
    # This is very helpful when learning or debugging!
    # echo=True,  # Prints all SQL queries to console (verbose!)
)

"""
WHAT IS AN ENGINE?
==================
The engine is SQLAlchemy's core interface to the database. It:

1. Manages the connection pool
   - Creates and reuses database connections efficiently
   - Like having multiple phone lines ready to use

2. Translates Python to SQL
   - Converts your Python code into SQL statements
   - Handles different SQL dialects (PostgreSQL, SQLite, MySQL, etc.)

3. Executes queries
   - Sends SQL to the database
   - Returns results back to Python

IMPORTANT: The engine itself doesn't hold connections!
It's more like a factory that creates connections when needed.

REAL-WORLD ANALOGY:
The engine is like a telephone exchange/switchboard:
- It knows how to connect to the database (has the phone number)
- It manages multiple simultaneous calls (connection pooling)
- It speaks the right language (SQL dialect)
- But it's not a phone call itself - you need a Session for that

ENGINE LIFECYCLE:
- Created once when the app starts (at module import)
- Reused throughout the app's lifetime
- Never needs to be closed (handles cleanup automatically)
"""


# =============================================================================
# SESSION FACTORY - CREATES DATABASE SESSIONS
# =============================================================================

SessionLocal = sessionmaker(
    # autocommit=False: Transactions must be explicitly committed
    # This means changes aren't saved until you call session.commit()
    # Why? Safety! You can rollback if something goes wrong
    autocommit=False,

    # autoflush=False: Don't automatically sync Python objects to database
    # This gives you more control over when data is sent to the database
    # You can flush manually with session.flush() if needed
    autoflush=False,

    # bind=engine: Connect this session factory to our database engine
    # This tells SessionLocal which database to talk to
    bind=engine,
)

"""
WHAT IS SESSIONLOCAL?
=====================
SessionLocal is a factory that creates database sessions (active connections).

IMPORTANT: SessionLocal is NOT a session itself!
It's a factory - call SessionLocal() to create a new session.

WHAT IS A SESSION?
==================
A session is an active connection/transaction with the database.
Think of it like an active phone call:
- You can talk (query the database)
- You can listen (receive results)
- You can hang up when done (close the session)

HOW SESSIONS WORK:
------------------
1. Create session: db = SessionLocal()
2. Use session: jobs = db.query(Job).all()
3. Make changes: db.add(new_job)
4. Save changes: db.commit()
5. Clean up: db.close()

SESSION LIFECYCLE (IMPORTANT):
------------------------------
ALWAYS close sessions when done! Otherwise you'll leak connections.
The database has a limited connection pool (typically 10-100 connections).

Bad example (connection leak!):
    db = SessionLocal()
    jobs = db.query(Job).all()
    # Forgot to close! ❌

Good example (manual cleanup):
    db = SessionLocal()
    try:
        jobs = db.query(Job).all()
    finally:
        db.close()  # ✅ Always closes, even if error occurs

Best example (using get_db() - see below):
    def my_route(db: Session = Depends(get_db)):
        jobs = db.query(Job).all()
        # get_db() automatically closes! ✅

TRANSACTION BEHAVIOR:
---------------------
autocommit=False means:
- db.add(job) → Stages the change (not yet saved)
- db.commit() → Saves all staged changes to database
- db.rollback() → Discards all staged changes

This is like a draft email:
- You write changes (add, update, delete)
- commit() = Press "Send" (saves to database)
- rollback() = Press "Discard Draft" (undo changes)
"""


# =============================================================================
# DEPENDENCY INJECTION FUNCTION FOR FASTAPI
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI routes.

    WHAT THIS FUNCTION DOES:
    ------------------------
    This is a "dependency" that FastAPI can inject into your route functions.
    It automatically:
    1. Creates a new database session
    2. Provides it to your route function
    3. Closes it when the route finishes (even if an error occurs)

    HOW TO USE IT IN ROUTES:
    ------------------------
    Simply add it as a parameter with Depends():

    Example 1: List all jobs
    -------------------------
    from fastapi import Depends
    from sqlalchemy.orm import Session
    from app.db.session import get_db
    from app.db.models import Job

    @router.get("/jobs")
    def list_jobs(db: Session = Depends(get_db)):
        # 'db' is automatically created by get_db()
        jobs = db.query(Job).all()
        return {"jobs": jobs}
        # After this function returns, get_db() automatically closes 'db'


    Example 2: Create a new job
    ----------------------------
    @router.post("/jobs")
    def create_job(job_data: JobCreate, db: Session = Depends(get_db)):
        new_job = Job(**job_data.dict())
        db.add(new_job)
        db.commit()
        db.refresh(new_job)  # Get the ID from database
        return new_job
        # Session automatically closed after this


    Example 3: Multiple dependencies
    ---------------------------------
    @router.get("/jobs/{job_id}")
    def get_job(
        job_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404)
        return job

    WHY USE DEPENDENCY INJECTION?
    ------------------------------
    1. Automatic cleanup: Session always closed, no leaks
    2. Clean code: No try/finally blocks in every route
    3. Testable: Can override get_db() with a test database
    4. Consistent: Same pattern across all routes

    HOW FASTAPI USES THIS:
    -----------------------
    When a request comes in:
    1. FastAPI sees: db: Session = Depends(get_db)
    2. FastAPI calls: get_db()
    3. get_db() yields: db session
    4. FastAPI injects: db into your route function
    5. Your route runs: uses db to query database
    6. Route finishes: returns response
    7. get_db() continues: closes db session in finally block

    GENERATOR EXPLANATION:
    ----------------------
    This function uses 'yield' instead of 'return', making it a generator.

    Without yield (normal function):
        def get_db():
            db = SessionLocal()
            return db  # Returns and exits immediately
            # Problem: Who closes db? ❌

    With yield (generator function):
        def get_db():
            db = SessionLocal()
            yield db  # Pauses here, gives db to FastAPI
            # Route uses db...
            # Route finishes...
            db.close()  # Resumes here, cleans up ✅

    The 'yield' keyword makes the function pause and resume, allowing
    cleanup code to run AFTER the route finishes.

    RETURN TYPE EXPLANATION:
    ------------------------
    Generator[Session, None, None] means:
    - Generator: This function yields values (not returns)
    - Session: The type of value yielded (a database session)
    - None: We don't send anything back to the generator
    - None: We don't raise any special exceptions

    This type hint helps your IDE provide autocomplete for 'db'.

    ERROR HANDLING:
    ---------------
    The 'finally' block ALWAYS runs, even if:
    - Your route raises an exception
    - Database query fails
    - User cancels the request
    - Server crashes

    This guarantees that sessions are always closed and connections
    are returned to the pool.

    TESTING EXAMPLE:
    ----------------
    You can override this dependency in tests:

    def override_get_db():
        # Use test database instead
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Now all routes use test database!
    """

    # Step 1: Create a new database session
    # This opens a connection from the connection pool
    db = SessionLocal()

    try:
        # Step 2: Yield the session to the route function
        # The route function receives 'db' and can use it
        # Execution pauses here until the route finishes
        yield db

        # Note: If the route raises an exception, we jump to 'finally'
        # We DON'T commit here - routes should commit explicitly if needed

    finally:
        # Step 3: Clean up - close the session
        # This ALWAYS runs, even if an exception occurred
        # Closing returns the connection to the pool for reuse
        db.close()

        # Important: close() does NOT commit!
        # If you made changes but didn't commit, they're lost (rolled back)
        # This is a safety feature - explicit commits prevent accidental changes


# =============================================================================
# USAGE EXAMPLES IN OTHER FILES
# =============================================================================

"""
EXAMPLE 1: Simple query in a route
-----------------------------------
File: app/api/routes_jobs.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Job

router = APIRouter()

@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    # Query all jobs from database
    jobs = db.query(Job).all()
    return {"jobs": jobs}


EXAMPLE 2: Create a record
---------------------------
File: app/api/routes_jobs.py

@router.post("/jobs")
def create_job(title: str, company: str, db: Session = Depends(get_db)):
    # Create new job object
    new_job = Job(title=title, company=company)

    # Add to session (stages the change)
    db.add(new_job)

    # Commit to database (saves permanently)
    db.commit()

    # Refresh to get the generated ID
    db.refresh(new_job)

    return {"job": new_job}
    # Session automatically closed after return


EXAMPLE 3: Update a record
---------------------------
@router.put("/jobs/{job_id}")
def update_job(job_id: int, title: str, db: Session = Depends(get_db)):
    # Find the job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update the job
    job.title = title

    # Commit the changes
    db.commit()

    return {"job": job}


EXAMPLE 4: Delete a record
---------------------------
@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    # Find the job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Delete the job
    db.delete(job)
    db.commit()

    return {"message": "Job deleted successfully"}


EXAMPLE 5: Using in a service layer
------------------------------------
File: app/services/jobs_service.py

from sqlalchemy.orm import Session
from app.db.models import Job

class JobsService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_jobs(self):
        return self.db.query(Job).all()

    def create_job(self, title: str, company: str):
        job = Job(title=title, company=company)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

# In route:
@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    service = JobsService(db)
    return service.get_all_jobs()


EXAMPLE 6: Transaction with rollback
-------------------------------------
@router.post("/apply-to-jobs")
def apply_to_multiple_jobs(job_ids: List[int], db: Session = Depends(get_db)):
    try:
        for job_id in job_ids:
            application = Application(job_id=job_id, status="submitted")
            db.add(application)

        # Commit all at once (atomic transaction)
        db.commit()
        return {"message": "Applied to all jobs"}

    except Exception as e:
        # If anything fails, undo all changes
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
"""


# =============================================================================
# INITIALIZATION & TABLE CREATION
# =============================================================================

"""
HOW TABLES ARE CREATED:
-----------------------
Tables are NOT created in this file.
They're created in app/main.py using:

    from app.db.session import engine, Base
    Base.metadata.create_all(bind=engine)

This command:
1. Looks at all classes that inherit from Base
2. Reads their __tablename__ and Column definitions
3. Generates CREATE TABLE SQL statements
4. Executes them on the database

This happens automatically when the FastAPI app starts.

MIGRATION NOTE:
---------------
In production, you should use Alembic for database migrations instead of
create_all(). Alembic provides:
- Version control for database schema
- Safe rollbacks
- Automatic migration generation
- History of all schema changes

We'll add Alembic in Phase 1 of the roadmap.
"""


# =============================================================================
# DATABASE CONNECTION TESTING
# =============================================================================

if __name__ == "__main__":
    """
    Test database connection by running: python -m app.db.session

    This will:
    1. Load settings from .env
    2. Create engine
    3. Test connection
    4. Show database info
    """
    print("Testing database connection...")
    print(f"Database URL: {settings.DATABASE_URL}")

    try:
        # Try to connect
        with engine.connect() as connection:
            print("✅ Database connection successful!")
            print(f"Database dialect: {engine.dialect.name}")
            print(f"Database driver: {engine.driver}")

            # Show tables (if any exist)
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            if tables:
                print(f"\nExisting tables: {', '.join(tables)}")
            else:
                print("\nNo tables found. Run the app to create them!")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check DATABASE_URL in .env file")
        print("2. Ensure PostgreSQL is running (if using PostgreSQL)")
        print("3. Verify database credentials")
        print("4. Check network connectivity")
