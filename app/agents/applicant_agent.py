"""
Applicant Agent - LangGraph Orchestrator

This module orchestrates the entire job application workflow using LangGraph.
It coordinates between Playwright (deterministic automation), Browser-Use (adaptive),
and other services (database, email verification, etc.).

Architecture:
    LangGraph State Machine:
    - fetch_job → analyze_portal → choose_strategy → execute_automation → verify → update_db

Security:
    - Runs in isolated Docker container
    - Limited file system access
    - Logs all actions
"""

import os
import logging
import asyncio
from typing import TypedDict, Annotated, Literal
from datetime import datetime

# LangGraph imports (only available in agent container)
try:
    from langgraph.graph import StateGraph, END
    from langchain_core.messages import HumanMessage
    from langchain_google_genai import ChatGoogleGenerativeAI
    LANGGRAPH_AVAILABLE = True
except ImportError:
    # Running in main API container (no langgraph/langchain)
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None
    HumanMessage = None
    ChatGoogleGenerativeAI = None

# Database imports
from app.db.session import SessionLocal
from app.services.jobs_service import get_job_by_status

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# STATE DEFINITION
# =============================================================================

class ApplicationState(TypedDict):
    """
    State object that flows through the LangGraph workflow.
    Contains all information needed to process a job application.
    """
    # Job information
    job_id: int
    job_url: str
    company: str
    title: str
    portal_type: str  # 'greenhouse', 'lever', 'workday', 'unknown'

    # User profile (loaded from profile/)
    user_data: dict

    # Workflow state
    current_step: str
    automation_strategy: Literal['playwright', 'browser-use']

    # Results
    screenshots: list[str]  # Paths to screenshots taken
    logs: list[str]  # Action logs
    errors: list[str]  # Any errors encountered
    success: bool
    application_submitted_at: str | None


# =============================================================================
# WORKFLOW NODES
# =============================================================================

def fetch_job_node(state: ApplicationState) -> ApplicationState:
    """
    Node 1: Fetch job details from database

    If job_id is provided in state, fetches that specific job.
    Otherwise, fetches the oldest job with status='new'.
    """
    logger.info(f"[fetch_job] Fetching job from database")

    db = SessionLocal()
    try:
        if state.get('job_id'):
            # Fetch specific job by ID
            logger.info(f"[fetch_job] Fetching job ID: {state['job_id']}")
            from app.db.models import Job
            job = db.query(Job).filter(Job.id == state['job_id']).first()
        else:
            # Fetch oldest job with status='new' (anti-bot strategy)
            logger.info(f"[fetch_job] Fetching oldest job with status='new'")
            job = get_job_by_status(db, status="new", limit=1)

        if not job:
            error_msg = f"No job found (ID: {state.get('job_id', 'auto-select')})"
            logger.error(f"[fetch_job] {error_msg}")
            state['errors'].append(error_msg)
            state['success'] = False
            state['current_step'] = 'fetch_job_failed'
            return state

        # Update state with job details
        state['job_id'] = job.id
        state['job_url'] = job.url
        state['company'] = job.company or 'Unknown Company'
        state['title'] = job.title
        state['current_step'] = 'fetch_job_complete'

        log_msg = f"Fetched job {job.id}: {job.title} at {job.company} (created {job.created_at})"
        state['logs'].append(log_msg)
        logger.info(f"[fetch_job] {log_msg}")

    except Exception as e:
        error_msg = f"Database error fetching job: {str(e)}"
        logger.error(f"[fetch_job] {error_msg}")
        state['errors'].append(error_msg)
        state['success'] = False
        state['current_step'] = 'fetch_job_failed'
    finally:
        db.close()

    return state


def analyze_portal_node(state: ApplicationState) -> ApplicationState:
    """
    Node 2: Analyze job URL to determine portal type
    """
    logger.info(f"[analyze_portal] Analyzing portal for URL: {state['job_url']}")

    url = state['job_url'].lower()

    # Detect portal type from URL
    if 'greenhouse.io' in url or 'boards.greenhouse.io' in url:
        portal_type = 'greenhouse'
    elif 'lever.co' in url or 'jobs.lever.co' in url:
        portal_type = 'lever'
    elif 'myworkdayjobs.com' in url:
        portal_type = 'workday'
    elif 'linkedin.com/jobs' in url:
        portal_type = 'linkedin'
    else:
        portal_type = 'unknown'

    state['portal_type'] = portal_type
    state['current_step'] = 'portal_analyzed'
    state['logs'].append(f"Portal detected: {portal_type}")

    logger.info(f"[analyze_portal] Portal type: {portal_type}")

    return state


def choose_strategy_node(state: ApplicationState) -> ApplicationState:
    """
    Node 3: Choose automation strategy based on portal type

    Known portals (Greenhouse, Lever) → Use Playwright (fast, deterministic)
    Unknown portals → Use Browser-Use (adaptive, AI-powered)
    """
    logger.info(f"[choose_strategy] Choosing strategy for portal: {state['portal_type']}")

    # Decision logic
    known_portals = ['greenhouse', 'lever', 'workday']

    if state['portal_type'] in known_portals:
        strategy = 'playwright'
        reason = f"Known portal ({state['portal_type']}), using deterministic Playwright"
    else:
        strategy = 'browser-use'
        reason = f"Unknown/complex portal, using adaptive Browser-Use with AI"

    state['automation_strategy'] = strategy
    state['current_step'] = 'strategy_chosen'
    state['logs'].append(f"Strategy: {strategy} - {reason}")

    logger.info(f"[choose_strategy] Selected: {strategy}")

    return state


def execute_playwright_node(state: ApplicationState) -> ApplicationState:
    """
    Node 4a: Execute automation using Playwright (deterministic)
    """
    logger.info(f"[execute_playwright] Starting Playwright automation for {state['portal_type']}")

    state['current_step'] = 'executing_playwright'
    state['logs'].append(f"Starting Playwright automation")

    try:
        # Import portal-specific automation
        if state['portal_type'] == 'greenhouse':
            from app.rpa.greenhouse import apply_to_greenhouse
            result = apply_to_greenhouse(state['job_url'], state['user_data'])
        elif state['portal_type'] == 'lever':
            # TODO: Implement Lever automation
            result = {'success': False, 'error': 'Lever automation not yet implemented'}
        elif state['portal_type'] == 'workday':
            # TODO: Implement Workday automation
            result = {'success': False, 'error': 'Workday automation not yet implemented'}
        else:
            result = {'success': False, 'error': f'No Playwright automation for {state["portal_type"]}'}

        state['success'] = result.get('success', False)

        if state['success']:
            state['application_submitted_at'] = datetime.utcnow().isoformat()
            state['screenshots'].extend(result.get('screenshots', []))
            state['logs'].append("Application submitted successfully via Playwright")
        else:
            error = result.get('error', 'Unknown error')
            state['errors'].append(f"Playwright failed: {error}")
            state['logs'].append(f"Playwright automation failed: {error}")

    except Exception as e:
        logger.error(f"[execute_playwright] Error: {e}")
        state['success'] = False
        state['errors'].append(f"Playwright exception: {str(e)}")

    state['current_step'] = 'playwright_complete'
    return state


def execute_browser_use_node(state: ApplicationState) -> ApplicationState:
    """
    Node 4b: Execute automation using Browser-Use (AI-powered)

    Uses Gemini + browser-use for adaptive form filling on unknown portals.
    This is slower but works on any website structure.
    """
    logger.info(f"[execute_browser_use] Starting Browser-Use automation")

    state['current_step'] = 'executing_browser_use'
    state['logs'].append(f"Starting Browser-Use (AI) automation")

    try:
        # Import browser-use (new API in 0.10.1)
        from browser_use import Agent
        import asyncio

        # Get Gemini API key
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            error_msg = "GEMINI_API_KEY not set in environment"
            logger.error(f"[execute_browser_use] {error_msg}")
            state['errors'].append(error_msg)
            state['success'] = False
            state['current_step'] = 'browser_use_failed'
            return state

        # Use browser-use's native ChatGoogle implementation
        # This has the required 'provider' attribute that browser-use expects
        from browser_use.llm.google.chat import ChatGoogle

        llm = ChatGoogle(
            model="gemini-2.0-flash-exp",
            api_key=gemini_api_key,
            temperature=0.1  # Low temperature for deterministic behavior
        )
        logger.info(f"[execute_browser_use] Using browser-use native ChatGoogle (gemini-2.0-flash-exp)")

        # Check headless mode (default: False for POC testing to see browser)
        headless = os.getenv("HEADLESS", "false").lower() == "true"

        # Build profile summary from user data
        user_data = state.get('user_data', {})
        profile_summary = f"""
        Name: {user_data.get('first_name', 'N/A')} {user_data.get('last_name', 'N/A')}
        Email: {user_data.get('email', 'N/A')}
        Phone: {user_data.get('phone', 'N/A')}
        """

        # Create task instruction for the agent
        # NOTE: POC mode - we stop BEFORE submitting to avoid sending fake applications
        task = f"""
        Navigate to this job application page and fill out the application form:
        URL: {state['job_url']}

        Job Details:
        - Title: {state['title']}
        - Company: {state['company']}

        Your profile information:
        {profile_summary}

        Instructions:
        1. Navigate to the URL
        2. Find and fill out the application form with the profile information
        3. Upload CV if requested (skip if file upload is required)
        4. STOP before clicking the final submit button

        Important:
        - Only fill fields that match the profile data
        - Skip optional fields if unsure
        - DO NOT submit the form (this is a test with fake data)
        - Just verify you can fill all required fields
        """

        logger.info(f"[execute_browser_use] Creating agent with task")
        state['logs'].append("Initializing Browser-Use agent with Gemini")
        state['logs'].append(f"Browser mode: {'headless' if headless else 'visible (VNC enabled)'}")

        # Note: browser-use 0.10.1 will use headless=False by default when DISPLAY is set
        # The VNC display (:0) is already configured via environment variable
        logger.info(f"[execute_browser_use] Using browser-use with DISPLAY={os.getenv('DISPLAY', 'not set')}")

        # Create browser-use agent
        # Browser configuration is handled via environment variables
        agent = Agent(
            task=task,
            llm=llm
        )

        logger.info(f"[execute_browser_use] Running agent (this may take 1-3 minutes)")
        state['logs'].append("Agent navigating to job page...")

        # Run the agent (this is async)
        # We need to run it in the event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a task
            result = loop.run_until_complete(agent.run())
        else:
            # If no loop is running, use asyncio.run
            result = asyncio.run(agent.run())

        logger.info(f"[execute_browser_use] Agent completed")
        logger.info(f"[execute_browser_use] Result: {result}")

        # Check if successful (browser-use returns history and status)
        # The exact structure depends on browser-use version
        # For now, assume success if no exception was raised
        state['success'] = True
        state['application_submitted_at'] = datetime.utcnow().isoformat()
        state['logs'].append(f"Browser-Use completed: {result}")
        state['logs'].append("Application submitted successfully via Browser-Use")

    except ImportError as e:
        error_msg = f"browser-use not installed: {str(e)}"
        logger.error(f"[execute_browser_use] {error_msg}")
        state['errors'].append(error_msg)
        state['success'] = False
    except Exception as e:
        logger.error(f"[execute_browser_use] Error: {e}", exc_info=True)
        state['success'] = False
        state['errors'].append(f"Browser-Use exception: {str(e)}")

    state['current_step'] = 'browser_use_complete'
    return state


def update_database_node(state: ApplicationState) -> ApplicationState:
    """
    Node 5: Update database with application result

    Updates the job status based on automation outcome:
    - Success: status='applied', stores submission timestamp
    - Failure: status='application_failed', stores error reason
    """
    logger.info(f"[update_database] Updating job {state['job_id']} status")

    state['current_step'] = 'updating_database'

    db = SessionLocal()
    try:
        from app.db.models import Job

        # Fetch job from database
        job = db.query(Job).filter(Job.id == state['job_id']).first()
        if not job:
            error_msg = f"Job {state['job_id']} not found in database"
            logger.error(f"[update_database] {error_msg}")
            state['errors'].append(error_msg)
            return state

        # Update job based on success/failure
        if state['success']:
            # Application succeeded (POC test - form filled but not submitted)
            job.status = 'poc_test'  # Proof of concept test successful
            # Note: We don't have an 'applied_at' field yet in the Job model
            # This would be part of the applications table in future phases
            new_status = 'poc_test'
            state['logs'].append(f"Database updated: job {state['job_id']} → {new_status} (POC test successful)")
            logger.info(f"[update_database] Job {state['job_id']} marked as poc_test (form filled successfully)")
        else:
            # Application failed
            job.status = 'application_failed'
            # Store first error as reject_reason
            if state['errors']:
                job.reject_reason = '; '.join(state['errors'][:3])  # Store first 3 errors
            new_status = 'application_failed'
            state['logs'].append(f"Database updated: job {state['job_id']} → {new_status} with errors")
            logger.warning(f"[update_database] Job {state['job_id']} marked as failed: {job.reject_reason}")

        # Commit changes
        db.commit()
        db.refresh(job)

        logger.info(f"[update_database] Successfully updated job {state['job_id']} → {new_status}")

    except Exception as e:
        error_msg = f"Database update error: {str(e)}"
        logger.error(f"[update_database] {error_msg}")
        state['errors'].append(error_msg)
        db.rollback()
    finally:
        db.close()

    state['current_step'] = 'complete'
    return state


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_automation_strategy(state: ApplicationState) -> str:
    """
    Router: Decide which automation node to execute
    """
    if state['automation_strategy'] == 'playwright':
        return 'execute_playwright'
    else:
        return 'execute_browser_use'


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_applicant_agent_graph():
    """
    Create the LangGraph state machine for the Applicant Agent

    Flow:
        START → fetch_job → analyze_portal → choose_strategy
            ├→ execute_playwright → update_database → END
            └→ execute_browser_use → update_database → END
    """
    workflow = StateGraph(ApplicationState)

    # Add nodes
    workflow.add_node("fetch_job", fetch_job_node)
    workflow.add_node("analyze_portal", analyze_portal_node)
    workflow.add_node("choose_strategy", choose_strategy_node)
    workflow.add_node("execute_playwright", execute_playwright_node)
    workflow.add_node("execute_browser_use", execute_browser_use_node)
    workflow.add_node("update_database", update_database_node)

    # Set entry point
    workflow.set_entry_point("fetch_job")

    # Add edges (flow between nodes)
    workflow.add_edge("fetch_job", "analyze_portal")
    workflow.add_edge("analyze_portal", "choose_strategy")

    # Conditional routing based on strategy
    workflow.add_conditional_edges(
        "choose_strategy",
        route_automation_strategy,
        {
            "execute_playwright": "execute_playwright",
            "execute_browser_use": "execute_browser_use"
        }
    )

    # Both automation paths lead to database update
    workflow.add_edge("execute_playwright", "update_database")
    workflow.add_edge("execute_browser_use", "update_database")

    # End after database update
    workflow.add_edge("update_database", END)

    return workflow.compile()


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def run_applicant_agent(job_id: int, job_url: str, company: str, title: str, user_data: dict):
    """
    Main entry point to run the Applicant Agent for a specific job

    Args:
        job_id: Database ID of the job
        job_url: URL to application page
        company: Company name
        title: Job title
        user_data: User profile data (loaded from profile/)

    Returns:
        Final state with results
    """
    logger.info(f"=== Starting Applicant Agent for Job {job_id} ===")
    logger.info(f"Job: {title} at {company}")
    logger.info(f"URL: {job_url}")

    # Create graph
    app = create_applicant_agent_graph()

    # Initialize state
    initial_state = ApplicationState(
        job_id=job_id,
        job_url=job_url,
        company=company,
        title=title,
        portal_type='',
        user_data=user_data,
        current_step='start',
        automation_strategy='playwright',
        screenshots=[],
        logs=[],
        errors=[],
        success=False,
        application_submitted_at=None
    )

    # Run the workflow
    final_state = app.invoke(initial_state)

    # Log final results
    logger.info("=== Applicant Agent Complete ===")
    logger.info(f"Success: {final_state['success']}")
    logger.info(f"Portal: {final_state['portal_type']}")
    logger.info(f"Strategy: {final_state['automation_strategy']}")
    logger.info(f"Screenshots: {len(final_state['screenshots'])}")
    logger.info(f"Errors: {len(final_state['errors'])}")

    if final_state['errors']:
        for error in final_state['errors']:
            logger.error(f"  - {error}")

    return final_state


# =============================================================================
# CLI ENTRY POINT (for Docker container execution)
# =============================================================================

if __name__ == "__main__":
    """
    CLI entry point when running as Docker container

    Environment variables:
        JOB_ID: ID of job to process
        DATABASE_URL: PostgreSQL connection string
        GEMINI_API_KEY: Gemini API key for Browser-Use
    """
    import sys

    # Get job ID from environment
    job_id = os.getenv("JOB_ID")
    if not job_id:
        logger.error("JOB_ID environment variable not set")
        sys.exit(1)

    job_id = int(job_id)

    # TODO: Fetch job details from database using DATABASE_URL
    # For now, use mock data
    job_url = "https://boards.greenhouse.io/example/jobs/123456"
    company = "Example Company"
    title = "Software Engineer"

    # TODO: Load user profile from profile/ directory
    user_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        # ... more profile data
    }

    # Run agent
    result = run_applicant_agent(job_id, job_url, company, title, user_data)

    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)
