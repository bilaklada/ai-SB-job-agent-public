"""
Job Lifecycle Orchestration - LangGraph State Machine with Parallel Processing

This module implements the job lifecycle state machine as described in the system architecture.
It processes jobs from State 0 (empty system) → State 1 (jobs available) → State 2 (completed).

Parallel Processing Architecture:
==================================
- Uses asyncio for concurrent job processing
- Processes multiple jobs simultaneously (configurable worker pool)
- Each job runs in its own isolated workflow
- Database updates are atomic per job

Database-Driven Architecture:
==============================
The orchestrator works in a webhook-style pattern:
- Monitors the jobs table for new records
- Processes records with status in ['new_url', 'new_api', 'new_webscraping']
- Updates job status as it progresses through the lifecycle
- Each state transition is persisted to the database

State Machine Architecture:
===========================

STATE 0: Sleepy System
- No unprocessed jobs (no rows with status='new_*')
- System is idle, waiting for new jobs

TRANSITION 0→1: Data Collection
- Path A: new_url (user provides URL list) → deterministic match_score=1.0
- Path B: new_api (Adzuna, JSearch) → AI match_score calculation
- Path C: new_webscraping (future) → AI match_score calculation

STATE 1: Jobs Available (Multiple Sub-States)

Match Score Logic:
------------------
new_url → det_match_score → match_score = 1.0 → approved_for_application

new_api → AI.match_score:
  - ≥0.7 → approved_for_application
  - 0.5-0.7 → low_priority
  - <0.5 → filtered_out (END)

new_webscraping → AI.match_score (same logic as new_api)

Account Workflow Check:
-----------------------
approved_for_application → existing_account_check:
  - YES → existing_workflow_check:
    * YES → application_init → application_in_progress
    * NO → missing_workflow → [HITL]
  - NO → missing_account → [HITL]

Application Progress:
---------------------
application_in_progress → [To be defined - RPA execution]

STATE 2: Completed (Terminal States)
- applied (success)
- application_failed (failure)
- requires_manual_check (HITL)
- filtered_out (rejected)
- low_priority (queued for later processing)

Author: SBAgent1 Team
Last Updated: 2025-12-14
"""

import os
import logging
import asyncio
from typing import TypedDict, Literal, Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pathlib import Path
import time
import httpx
import json
from urllib.parse import urlparse

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    from langchain_core.messages import HumanMessage
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None

# Database imports
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Job, Application, LogStatusChange, LogATSMatch, ATS, Company

# Gemini imports
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    ChatGoogleGenerativeAI = None

# Playwright imports
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    Browser = None
    BrowserContext = None
    Page = None

# ATS Detection v14 imports
try:
    from app.orchestration.ats_detection import (
        detect_ats_with_evidence,
        ATSDetectionResult,
        ATSDetectionEvidence,
        EvidenceLevel,
    )
    ATS_DETECTION_V14_AVAILABLE = True
except ImportError:
    ATS_DETECTION_V14_AVAILABLE = False
    detect_ats_with_evidence = None
    ATSDetectionResult = None
    ATSDetectionEvidence = None
    EvidenceLevel = None

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# JOB STATUS ENUMS (from README state machine specification)
# =============================================================================

class JobStatus(str, Enum):
    """
    Job status values matching the state machine specification.

    ENTRY POINTS (State 0 → State 1):
    - new_url: User provides URL list (manual input)
    - new_api: Job from API provider (Adzuna, JSearch)
    - new_webscraping: Job from webscraping (future)
    """

    # === State 0 → State 1 Transitions (Data Collection Entry Points) ===
    NEW_URL = "new_url"                          # User-provided URL (manual)
    NEW_API = "new_api"                          # API-sourced (Adzuna, JSearch)
    NEW_WEBSCRAPING = "new_webscraping"          # Webscraping-sourced (future)

    # === State 1 Sub-States (After Match Scoring) ===
    APPROVED_FOR_APPLICATION = "approved_for_application"  # Match ≥0.7 or new_url
    LOW_PRIORITY = "low_priority"                          # Match 0.5-0.7
    FILTERED_OUT = "filtered_out"                          # Match <0.5 (END)

    # === State 1 Sub-States (Account Workflow) ===
    MISSING_ACCOUNT = "missing_account"          # No account exists (HITL)
    MISSING_WORKFLOW = "missing_workflow"        # No automation workflow (HITL)
    APPLICATION_IN_PROGRESS = "application_in_progress"  # Application started

    # === State 2 Terminal States ===
    APPLIED = "applied"                          # Successfully submitted
    APPLICATION_FAILED = "application_failed"    # Submission failed
    REQUIRES_MANUAL_CHECK = "requires_manual_check"  # Manual intervention needed


# Entry point statuses that trigger orchestration
ENTRY_STATUSES = [
    JobStatus.NEW_URL,
    JobStatus.NEW_API,
    JobStatus.NEW_WEBSCRAPING
]


# =============================================================================
# STATE DEFINITION
# =============================================================================

class JobLifecycleState(TypedDict):
    """
    State object for the job lifecycle orchestration workflow.

    This state flows through the LangGraph nodes and tracks the job's progression
    through the lifecycle state machine.
    """
    # Job identification
    job_id: int
    job_url: str
    job_status: str
    profile_id: int  # Which candidate profile this job is for

    # Job details
    title: Optional[str]
    company: Optional[str]
    description: Optional[str]
    provider: str

    # Match scoring
    match_score: Optional[float]
    match_explanation: Optional[str]

    # Application tracking (State Machine v2)
    application_id: Optional[int]

    # Account and workflow checks
    has_existing_account: Optional[bool]
    account_id: Optional[int]
    has_workflow: Optional[bool]
    workflow_type: Optional[str]  # 'greenhouse', 'lever', etc.

    # Workflow tracking
    current_step: str
    logs: list[str]
    errors: list[str]

    # Timestamps
    processed_at: Optional[str]


# =============================================================================
# DETERMINISTIC OPERATIONS
# =============================================================================

def det_match_score_node(state: JobLifecycleState) -> JobLifecycleState:
    """
    Deterministic match score for user-provided jobs (new_url).

    For jobs added manually via URL, we automatically approve them with match_score=1.0
    since the user explicitly selected them.

    Flow:
        new_url → match_score = 1.0 → approved_for_application
    """
    logger.info(f"[det_match_score] Job {state['job_id']}: Applying deterministic match score")

    state['current_step'] = 'det_match_score'

    if state['job_status'] == JobStatus.NEW_URL:
        # User-provided URL → automatic approval
        state['match_score'] = 1.0
        state['match_explanation'] = "User-provided URL - automatically approved (match_score=1.0)"
        state['job_status'] = JobStatus.APPROVED_FOR_APPLICATION

        log_msg = f"Job {state['job_id']}: new_url → match_score=1.0 → {JobStatus.APPROVED_FOR_APPLICATION}"
        state['logs'].append(log_msg)
        logger.info(f"[det_match_score] {log_msg}")

        # Update database
        _update_job_in_db(
            state['job_id'],
            status=JobStatus.APPROVED_FOR_APPLICATION,
            match_score=1.0
        )

        # Note: state_change_history tracking temporarily disabled (table being rebuilt)
    else:
        # Should not reach here for non-manual jobs
        error_msg = f"det_match_score called for non-new_url job: {state['job_status']}"
        logger.warning(f"[det_match_score] {error_msg}")
        state['errors'].append(error_msg)

    return state


def ai_match_score_node(state: JobLifecycleState) -> JobLifecycleState:
    """
    AI-powered match score calculation for API/webscraping jobs.

    For jobs from providers (new_api, new_webscraping), we use AI to calculate match_score
    by comparing the job description against the user profile.

    Flow:
        new_api/new_webscraping → AI.match_score:
            - ≥0.7 → approved_for_application
            - 0.5-0.7 → low_priority
            - <0.5 → filtered_out (END)

    TODO: Integrate actual LLM for match scoring (Phase 4)
    For now, using placeholder logic.
    """
    logger.info(f"[ai_match_score] Job {state['job_id']}: Calculating AI match score")

    state['current_step'] = 'ai_match_score'

    # TODO: Replace with actual LLM integration (Phase 4)
    # For now, using simple keyword matching as placeholder

    try:
        # Placeholder: Simple scoring based on title/description
        # In production, this would call OpenAI/Anthropic with profile comparison
        score = _calculate_placeholder_match_score(
            state['title'],
            state['description']
        )

        state['match_score'] = score
        state['match_explanation'] = f"AI match score calculated: {score:.2f} (placeholder logic)"

        # Apply thresholds from state machine spec
        if score >= 0.7:
            new_status = JobStatus.APPROVED_FOR_APPLICATION
        elif score >= 0.5:
            new_status = JobStatus.LOW_PRIORITY
        else:
            new_status = JobStatus.FILTERED_OUT

        state['job_status'] = new_status

        log_msg = f"Job {state['job_id']}: AI match_score={score:.2f} → {new_status}"
        state['logs'].append(log_msg)
        logger.info(f"[ai_match_score] {log_msg}")

        # Update database
        _update_job_in_db(
            state['job_id'],
            status=new_status,
            match_score=score
        )

    except Exception as e:
        error_msg = f"AI match score failed: {str(e)}"
        logger.error(f"[ai_match_score] {error_msg}")
        state['errors'].append(error_msg)
        state['job_status'] = JobStatus.APPLICATION_FAILED

        # Update database with failure
        _update_job_in_db(
            state['job_id'],
            status=JobStatus.APPLICATION_FAILED
        )

    return state


def existing_account_check_node(state: JobLifecycleState) -> JobLifecycleState:
    """
    Check if an account exists for the job portal.

    Flow:
        approved_for_application → existing_account_check:
            - YES (account exists) → continue to workflow check
            - NO (no account) → missing_account → [HITL]

    Checks the accounts table to see if we have credentials for this job's portal.
    """
    logger.info(f"[existing_account_check] Job {state['job_id']}: Checking for existing account")

    state['current_step'] = 'existing_account_check'

    # Extract domain from job URL to identify portal
    portal_domain = _extract_portal_domain(state['job_url'])

    # TODO: Query accounts table when it's created (Phase 3)
    # For now, using placeholder logic

    # Placeholder: Check if account exists
    has_account, account_id = _check_account_exists(portal_domain)

    state['has_existing_account'] = has_account
    state['account_id'] = account_id

    if has_account:
        log_msg = f"Job {state['job_id']}: Account found (account_id={account_id}) for {portal_domain}"
        state['logs'].append(log_msg)
        logger.info(f"[existing_account_check] {log_msg}")
    else:
        # No account → HITL required
        state['job_status'] = JobStatus.MISSING_ACCOUNT
        log_msg = f"Job {state['job_id']}: No account for {portal_domain} → {JobStatus.MISSING_ACCOUNT} (HITL)"
        state['logs'].append(log_msg)
        logger.warning(f"[existing_account_check] {log_msg}")

        # Update database
        _update_job_in_db(
            state['job_id'],
            status=JobStatus.MISSING_ACCOUNT
        )

    return state


def existing_workflow_check_node(state: JobLifecycleState) -> JobLifecycleState:
    """
    Check if an automation workflow exists for the job portal.

    Flow:
        (after account exists) → existing_workflow_check:
            - YES (workflow exists) → application_init → application_in_progress
            - NO (no workflow) → missing_workflow → [HITL]

    Checks if we have an RPA automation script for this portal type.
    """
    logger.info(f"[existing_workflow_check] Job {state['job_id']}: Checking for automation workflow")

    state['current_step'] = 'existing_workflow_check'

    # Detect portal type from URL
    portal_type = _detect_portal_type(state['job_url'])
    state['workflow_type'] = portal_type

    # Check if we have automation for this portal
    has_workflow = _check_workflow_exists(portal_type)
    state['has_workflow'] = has_workflow

    if has_workflow:
        # Workflow exists → can proceed to application
        state['job_status'] = JobStatus.APPLICATION_IN_PROGRESS
        log_msg = f"Job {state['job_id']}: Workflow '{portal_type}' exists → {JobStatus.APPLICATION_IN_PROGRESS}"
        state['logs'].append(log_msg)
        logger.info(f"[existing_workflow_check] {log_msg}")

        # Update database
        _update_job_in_db(
            state['job_id'],
            status=JobStatus.APPLICATION_IN_PROGRESS
        )
    else:
        # No workflow → HITL required
        state['job_status'] = JobStatus.MISSING_WORKFLOW
        log_msg = f"Job {state['job_id']}: No workflow for '{portal_type}' → {JobStatus.MISSING_WORKFLOW} (HITL)"
        state['logs'].append(log_msg)
        logger.warning(f"[existing_workflow_check] {log_msg}")

        # Update database
        _update_job_in_db(
            state['job_id'],
            status=JobStatus.MISSING_WORKFLOW
        )

    return state


def application_init_node(state: JobLifecycleState) -> JobLifecycleState:
    """
    Initialize the application process.

    This node prepares the application by:
    1. Creating an application record (when applications table exists)
    2. Loading user profile
    3. Queueing the job for RPA execution

    TODO: This is a placeholder for the full application workflow.
    The actual execution will be handled by the Applicant Agent (app/agents/applicant_agent.py).
    """
    logger.info(f"[application_init] Job {state['job_id']}: Initializing application")

    state['current_step'] = 'application_init'

    # TODO: Create application record in applications table (Phase 3)
    # TODO: Queue job for RPA agent execution (Phase 5)

    log_msg = f"Job {state['job_id']}: Application initialized (placeholder - RPA execution pending)"
    state['logs'].append(log_msg)
    logger.info(f"[application_init] {log_msg}")

    # For now, keep status as application_in_progress
    # The actual application execution will be handled separately

    return state


def create_application_node(state: JobLifecycleState) -> JobLifecycleState:
    """
    Create application record in database (Det.Op: create_new_application).

    According to state-machine-spec-v2.md, this operation:
    1. Creates a new record in applications table
    2. Links to job_id and profile_id (from state - no DB fetch needed)
    3. Sets initial status = 'created'

    Flow:
        approved_for_application → create_application → applications.status='created'
    """
    logger.info(f"[create_application] START - Job {state['job_id']}, Profile {state['profile_id']}")

    state['current_step'] = 'create_application'

    db = SessionLocal()
    try:
        # Create application record using data from state (no DB fetch needed!)
        logger.info(f"[create_application] Creating Application record with job_id={state['job_id']}, profile_id={state['profile_id']}")

        application = Application(
            job_id=state['job_id'],
            profile_id=state['profile_id'],
            status='created',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(application)
        logger.info(f"[create_application] Application added to session, flushing to get ID...")
        db.flush()  # Get application_id without committing yet

        application_id = application.application_id
        logger.info(f"[create_application] Application ID assigned: {application_id}")

        # Log initial application creation (status change from null → 'created')
        _log_status_change(
            db=db,
            lsc_table='applications',
            profile_id=state['profile_id'],
            job_id=state['job_id'],
            application_id=application_id,
            initial_status='null',  # No previous status
            final_status='created'
        )

        # Commit the application
        logger.info(f"[create_application] Committing application {application_id} to database...")
        db.commit()
        logger.info(f"[create_application] ✅ Application {application_id} committed successfully")

        log_msg = f"Job {state['job_id']}: Application {application_id} created with status='created'"
        state['logs'].append(log_msg)
        logger.info(f"[create_application] {log_msg}")

        # Store application_id in state for next nodes
        state['application_id'] = application_id
        logger.info(f"[create_application] Application ID stored in state: {application_id}")

    except Exception as e:
        error_msg = f"Failed to create application: {str(e)}"
        logger.error(f"[create_application] ❌ EXCEPTION: {error_msg}", exc_info=True)
        state['errors'].append(error_msg)
        db.rollback()
        logger.error(f"[create_application] Transaction rolled back")
    finally:
        db.close()
        logger.info(f"[create_application] Database session closed")

    logger.info(f"[create_application] END - Application ID in state: {state.get('application_id')}")
    return state


def ats_match_node(state: JobLifecycleState) -> JobLifecycleState:
    """
    AI Operation: Identify ATS platform from job URL.

    According to state-machine-spec-v2.md, this operation:
    1. Fetches HTML/inspect code from the URL
    2. Calls Gemini LLM with: URL, HTML, list of available ATSs
    3. Updates application with ats_id, ats_name
    4. Sets application.status = 'ats_match' or 'ats_missing'
    5. Records state change

    Flow:
        application.status='created' → AI.ats_match → 'ats_match' or 'ats_missing'
    """
    logger.info(f"[ats_match] Job {state['job_id']}: Identifying ATS platform")

    state['current_step'] = 'ats_match'

    application_id = state.get('application_id')
    if not application_id:
        error_msg = "No application_id in state"
        logger.error(f"[ats_match] {error_msg}")
        state['errors'].append(error_msg)
        return state

    if not GEMINI_AVAILABLE:
        error_msg = "Gemini not available - cannot perform ATS matching"
        logger.warning(f"[ats_match] {error_msg}")
        state['errors'].append(error_msg)
        _update_application_status(application_id, 'ats_missing', 'Gemini not available')
        return state

    db = SessionLocal()
    try:
        # Fetch HTML from URL
        html_content = _fetch_html_from_url(state['job_url'])
        if not html_content:
            logger.warning(f"[ats_match] Could not fetch HTML from {state['job_url']}")
            html_content = "(HTML fetch failed)"

        # Get list of available ATSs from database
        atss = db.query(ATS).all()
        ats_list = [{"ats_id": ats.ats_id, "ats_name": ats.ats_name} for ats in atss]

        if not ats_list:
            logger.warning(f"[ats_match] No ATSs in database - cannot match")
            _update_application_status(application_id, 'ats_missing', 'No ATSs in database')
            return state

        # Call LLM to identify ATS (uses configured provider from settings)
        ats_result = _identify_ats_with_llm(state['job_url'], html_content, ats_list)

        # Log the ATS matching attempt for observability (with HTML snapshot)
        if ats_result:
            _log_ats_match_attempt(db, application_id, html_content, ats_result)

        # Update application based on result
        application = db.query(Application).filter(Application.application_id == application_id).first()
        if not application:
            error_msg = f"Application {application_id} not found"
            logger.error(f"[ats_match] {error_msg}")
            state['errors'].append(error_msg)
            return state

        old_status = application.status

        if ats_result and ats_result.get('matched'):
            # ATS matched
            application.ats_id = ats_result['ats_id']
            application.ats_name = ats_result['ats_name']
            application.status = 'ats_match'
            application.updated_at = datetime.utcnow()

            new_status = 'ats_match'
            reason = f"ATS identified: {ats_result['ats_name']}"

            log_msg = f"Job {state['job_id']}: ATS matched - {ats_result['ats_name']} (ats_id={ats_result['ats_id']})"
            state['logs'].append(log_msg)
            logger.info(f"[ats_match] {log_msg}")
        else:
            # ATS not matched
            application.status = 'ats_missing'
            application.updated_at = datetime.utcnow()

            new_status = 'ats_missing'
            reason = ats_result.get('reason', 'ATS could not be identified') if ats_result else 'AI matching failed'

            log_msg = f"Job {state['job_id']}: ATS not matched - {reason}"
            state['logs'].append(log_msg)
            logger.warning(f"[ats_match] {log_msg}")

        # Log status change
        _log_status_change(
            db=db,
            lsc_table='applications',
            profile_id=state['profile_id'],
            job_id=state['job_id'],
            application_id=application_id,
            initial_status=old_status,
            final_status=new_status
        )

        db.commit()
        logger.info(f"[ats_match] Status updated: {old_status} → {new_status}")

    except Exception as e:
        error_msg = f"ATS matching failed: {str(e)}"
        logger.error(f"[ats_match] {error_msg}")
        state['errors'].append(error_msg)
        db.rollback()
        _update_application_status(application_id, 'ats_missing', error_msg)
    finally:
        db.close()

    return state


def company_match_node(state: JobLifecycleState) -> JobLifecycleState:
    """
    AI Operation: Identify company from job URL.

    According to state-machine-spec-v2.md, this operation:
    1. Reuses URL and HTML from previous step
    2. Calls Gemini LLM with: URL, HTML, list of known companies
    3. If matched: Updates application with company_id, company_name, status='company_match'
    4. If not matched but identified: Creates new company, status='new_company'
    5. If not identified: status='missing_company'
    6. Records state change

    Flow:
        application.status='ats_match' or 'ats_missing' → AI.company_match →
        'company_match' or 'new_company' or 'missing_company'
    """
    logger.info(f"[company_match] Job {state['job_id']}: Identifying company")

    state['current_step'] = 'company_match'

    application_id = state.get('application_id')
    if not application_id:
        error_msg = "No application_id in state"
        logger.error(f"[company_match] {error_msg}")
        state['errors'].append(error_msg)
        return state

    if not GEMINI_AVAILABLE:
        error_msg = "Gemini not available - cannot perform company matching"
        logger.warning(f"[company_match] {error_msg}")
        state['errors'].append(error_msg)
        _update_application_status(application_id, 'missing_company', 'Gemini not available')
        return state

    db = SessionLocal()
    try:
        # Fetch HTML from URL (same as ATS match)
        html_content = _fetch_html_from_url(state['job_url'])
        if not html_content:
            logger.warning(f"[company_match] Could not fetch HTML from {state['job_url']}")
            html_content = "(HTML fetch failed)"

        # Get list of known companies from database
        companies = db.query(Company).all()
        company_list = [{"company_id": c.company_id, "company_name": c.company_name} for c in companies]

        # Call Gemini to identify company
        company_result = _identify_company_with_gemini(state['job_url'], html_content, company_list)

        # Update application based on result
        application = db.query(Application).filter(Application.application_id == application_id).first()
        if not application:
            error_msg = f"Application {application_id} not found"
            logger.error(f"[company_match] {error_msg}")
            state['errors'].append(error_msg)
            return state

        old_status = application.status

        if company_result and company_result.get('matched'):
            # Company exists in database
            application.company_id = company_result['company_id']
            application.company_name = company_result['company_name']
            application.status = 'company_match'
            application.updated_at = datetime.utcnow()

            new_status = 'company_match'
            reason = f"Company matched: {company_result['company_name']}"

            log_msg = f"Job {state['job_id']}: Company matched - {company_result['company_name']} (company_id={company_result['company_id']})"
            state['logs'].append(log_msg)
            logger.info(f"[company_match] {log_msg}")

        elif company_result and company_result.get('identified'):
            # Company identified but not in database - create new company
            company_name = company_result['company_name']

            # Get ATS info from application
            ats_id = application.ats_id
            ats_name = application.ats_name or 'unknown'

            # If no ATS, try to get a default one
            if not ats_id:
                default_ats = db.query(ATS).first()
                if default_ats:
                    ats_id = default_ats.ats_id
                    ats_name = default_ats.ats_name

            if ats_id:
                # Create new company
                new_company = Company(
                    company_name=company_name,
                    ats_id=ats_id,
                    ats_name=ats_name,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(new_company)
                db.flush()

                # Update application
                application.company_id = new_company.company_id
                application.company_name = company_name
                application.status = 'new_company'
                application.updated_at = datetime.utcnow()

                new_status = 'new_company'
                reason = f"New company created: {company_name}"

                log_msg = f"Job {state['job_id']}: New company created - {company_name} (company_id={new_company.company_id})"
                state['logs'].append(log_msg)
                logger.info(f"[company_match] {log_msg}")
            else:
                # Cannot create company without ATS
                application.status = 'missing_company'
                application.updated_at = datetime.utcnow()

                new_status = 'missing_company'
                reason = f"Company identified but cannot create (no ATS): {company_name}"

                log_msg = f"Job {state['job_id']}: {reason}"
                state['logs'].append(log_msg)
                logger.warning(f"[company_match] {log_msg}")
        else:
            # Company not identified
            application.status = 'missing_company'
            application.updated_at = datetime.utcnow()

            new_status = 'missing_company'
            reason = company_result.get('reason', 'Company could not be identified') if company_result else 'AI matching failed'

            log_msg = f"Job {state['job_id']}: Company not identified - {reason}"
            state['logs'].append(log_msg)
            logger.warning(f"[company_match] {log_msg}")

        # Log status change
        _log_status_change(
            db=db,
            lsc_table='applications',
            profile_id=state['profile_id'],
            job_id=state['job_id'],
            application_id=application_id,
            initial_status=old_status,
            final_status=new_status
        )

        db.commit()
        logger.info(f"[company_match] Status updated: {old_status} → {new_status}")

    except Exception as e:
        error_msg = f"Company matching failed: {str(e)}"
        logger.error(f"[company_match] {error_msg}")
        state['errors'].append(error_msg)
        db.rollback()
        _update_application_status(application_id, 'missing_company', error_msg)
    finally:
        db.close()

    return state


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_by_job_status(state: JobLifecycleState) -> str:
    """
    Router: Determine next node based on job status.

    This implements the state machine transitions from the specification.
    """
    status = state['job_status']

    # Route user-provided jobs to deterministic scoring
    if status == JobStatus.NEW_URL:
        return 'det_match_score'

    # Route API/webscraping jobs to AI scoring
    elif status in [JobStatus.NEW_API, JobStatus.NEW_WEBSCRAPING]:
        return 'ai_match_score'

    # Unexpected status
    else:
        logger.error(f"[route_by_job_status] Unexpected status: {status}")
        return END


def route_after_match_score(state: JobLifecycleState) -> str:
    """
    Router: Determine path after match scoring.

    State Machine v2 flow:
    approved_for_application → create_application (then ATS/company match)
    low_priority → END (queued for later)
    filtered_out → END (rejected)
    """
    status = state['job_status']

    if status == JobStatus.APPROVED_FOR_APPLICATION:
        return 'create_application'  # State Machine v2: create application first

    elif status in [JobStatus.LOW_PRIORITY, JobStatus.FILTERED_OUT]:
        # Terminal states for now
        return END

    else:
        logger.warning(f"[route_after_match_score] Unexpected status: {status}")
        return END


def route_after_account_check(state: JobLifecycleState) -> str:
    """
    Router: Determine path after account check.

    has_account=True → check workflow
    has_account=False (missing_account) → END (HITL)
    """
    if state.get('has_existing_account'):
        return 'existing_workflow_check'
    else:
        # missing_account → HITL required
        return END


def route_after_workflow_check(state: JobLifecycleState) -> str:
    """
    Router: Determine path after workflow check.

    has_workflow=True → initialize application
    has_workflow=False (missing_workflow) → END (HITL)
    """
    if state.get('has_workflow'):
        return 'application_init'
    else:
        # missing_workflow → HITL required
        return END


def route_after_ats_match(state: JobLifecycleState) -> str:
    """
    Router: Determine path after ATS matching (State Machine v2).

    According to state-machine-spec-v2.md:
    - ats_match → continue to company_match
    - ats_missing → END (terminal state - requires manual intervention)
    """
    application_id = state.get('application_id')
    if not application_id:
        logger.error("[route_after_ats_match] No application_id in state")
        return END

    # Query application to get current status
    db = SessionLocal()
    try:
        from app.db.models import Application
        application = db.query(Application).filter(Application.application_id == application_id).first()
        if not application:
            logger.error(f"[route_after_ats_match] Application {application_id} not found")
            return END

        if application.status == 'ats_match':
            logger.info(f"[route_after_ats_match] ATS matched - continuing to company_match")
            return 'company_match'
        else:
            # ats_missing or any other status → terminal state
            logger.warning(f"[route_after_ats_match] ATS not matched (status={application.status}) - workflow ends here")
            return END
    finally:
        db.close()


def route_after_company_match(state: JobLifecycleState) -> str:
    """
    Router: After company matching (State Machine v2).

    According to state-machine-spec-v2.md:
    All outcomes are terminal states (workflow ends):
    - company_match → END (success)
    - new_company → END (success - company created)
    - missing_company → END (terminal - requires manual intervention)
    """
    application_id = state.get('application_id')

    db = SessionLocal()
    try:
        from app.db.models import Application
        application = db.query(Application).filter(Application.application_id == application_id).first()
        if application:
            logger.info(f"[route_after_company_match] Company matching complete (status={application.status}) - workflow ends (STATE 2)")
        else:
            logger.warning(f"[route_after_company_match] Application {application_id} not found")
    finally:
        db.close()

    # All company_match outcomes are terminal states
    return END


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _update_job_in_db(
    job_id: int,
    status: Optional[str] = None,
    match_score: Optional[float] = None
) -> None:
    """Update job status and/or match_score in database."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if job:
            # Capture old status for logging
            old_status = job.status

            # Update fields
            if status:
                job.status = status
            if match_score is not None:
                job.match_score = match_score

            # Log status change if status was updated
            if status and old_status != status:
                _log_status_change(
                    db=db,
                    lsc_table='jobs',
                    profile_id=job.profile_id,
                    job_id=job.job_id,
                    application_id=None,  # Job-level change, no application yet
                    initial_status=old_status,
                    final_status=status
                )

            db.commit()
            logger.debug(f"[_update_job_in_db] Updated job {job_id}: status={status}, match_score={match_score}")
    except Exception as e:
        logger.error(f"[_update_job_in_db] Error updating job {job_id}: {e}")
        db.rollback()
    finally:
        db.close()


def _calculate_placeholder_match_score(title: Optional[str], description: Optional[str]) -> float:
    """
    Placeholder match score calculation.

    TODO: Replace with actual LLM integration in Phase 4.
    For now, uses simple keyword matching.
    """
    # Simple keyword-based scoring (placeholder)
    score = 0.5  # Default neutral score

    if title:
        title_lower = title.lower()
        # Increase score for relevant keywords
        if any(keyword in title_lower for keyword in ['python', 'engineer', 'developer', 'senior']):
            score += 0.2
        if 'remote' in title_lower:
            score += 0.1

    if description:
        desc_lower = description.lower()
        if any(keyword in desc_lower for keyword in ['python', 'fastapi', 'postgresql']):
            score += 0.1

    # Cap at 1.0
    return min(score, 1.0)


def _extract_portal_domain(url: str) -> str:
    """Extract portal domain from job URL."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc


def _detect_portal_type(url: str) -> str:
    """Detect portal type from URL."""
    url_lower = url.lower()

    if 'greenhouse.io' in url_lower:
        return 'greenhouse'
    elif 'lever.co' in url_lower:
        return 'lever'
    elif 'workday' in url_lower:
        return 'workday'
    elif 'linkedin.com' in url_lower:
        return 'linkedin'
    else:
        return 'unknown'


def _check_account_exists(portal_domain: str) -> tuple[bool, Optional[int]]:
    """
    Check if account exists for portal domain.

    TODO: Query accounts table when created (Phase 3).
    Returns: (has_account, account_id)
    """
    # Placeholder: No accounts exist yet
    # In Phase 3, this will query the accounts table
    return (False, None)


def _check_workflow_exists(portal_type: str) -> bool:
    """
    Check if automation workflow exists for portal type.

    Currently checks if RPA script file exists in app/rpa/{portal_type}.py
    """
    import os

    # Check for known portal types with implemented workflows
    known_portals = ['greenhouse']  # As per Phase 5, only greenhouse is implemented

    if portal_type in known_portals:
        # Check if RPA file exists
        rpa_file = Path(__file__).resolve().parents[1] / "rpa" / f"{portal_type}.py"
        return rpa_file.exists()

    return False


def _log_status_change(
    db: Session,
    lsc_table: str,
    profile_id: int,
    job_id: int,
    application_id: Optional[int],
    initial_status: str,
    final_status: str
) -> None:
    """
    Log a status change to the log_status_change table.

    Args:
        db: Database session
        lsc_table: 'jobs' or 'applications'
        profile_id: Profile ID
        job_id: Job ID
        application_id: Application ID (nullable)
        initial_status: Status before change
        final_status: Status after change
    """
    try:
        log_entry = LogStatusChange(
            lsc_table=lsc_table,
            profile_id=profile_id,
            job_id=job_id,
            application_id=application_id,
            initial_status=initial_status,
            final_status=final_status,
            updated_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.flush()  # Flush to DB but don't commit yet (let caller commit)
        logger.debug(
            f"[_log_status_change] Logged {lsc_table} status change: "
            f"job={job_id}, app={application_id}, '{initial_status}' → '{final_status}'"
        )
    except Exception as e:
        logger.error(f"[_log_status_change] Failed to log status change: {e}", exc_info=True)
        # Don't raise - logging failures shouldn't break the workflow


def _update_application_status(application_id: int, status: str, reason: str) -> None:
    """Update application status in database."""
    db = SessionLocal()
    try:
        application = db.query(Application).filter(Application.application_id == application_id).first()
        if application:
            application.status = status
            application.updated_at = datetime.utcnow()
            db.commit()
            logger.debug(f"[_update_application_status] Updated application {application_id}: status={status}")
    except Exception as e:
        logger.error(f"[_update_application_status] Error updating application {application_id}: {e}")
        db.rollback()
    finally:
        db.close()


def _fetch_html_from_url(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch HTML content from URL using httpx.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content as string, or None if fetch failed
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            response.raise_for_status()

            # Limit HTML size to avoid processing huge pages
            html = response.text[:50000]  # First 50KB should be enough for ATS/company detection

            logger.debug(f"[_fetch_html_from_url] Fetched {len(html)} characters from {url}")
            return html

    except httpx.RequestError as e:
        logger.warning(f"[_fetch_html_from_url] Request failed for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"[_fetch_html_from_url] Unexpected error fetching {url}: {e}")
        return None


def _log_ats_match_attempt(
    db: Session,
    application_id: int,
    html_content: str,
    ats_result: Dict[str, Any]
) -> None:
    """
    Log an ATS matching attempt to log_ats_match table (simplified schema).

    New Schema (8 columns, all mandatory):
    1. lam_id (PK, auto)
    2. application_id
    3. html_snapshot - HTML content passed to LLM
    4. llm_provider_name - LLM provider used
    5. extracted_ats_name - ATS name extracted by LLM
    6. best_match_ats_name - ATS name matched in database
    7. ats_match_status - 'ats_match' or 'ats_missing'
    8. updated_at (auto)

    Args:
        db: Database session
        application_id: Application ID being processed
        html_content: HTML snapshot passed to the LLM
        ats_result: Result dict from _identify_ats_with_llm containing:
                   - matched: bool
                   - ats_name: str (ATS name if matched, or extracted name if not)
                   - metadata: dict (provider, model)
    """
    metadata = ats_result.get('metadata', {})

    # Determine match status ('ats_match' or 'ats_missing')
    if ats_result.get('matched'):
        ats_match_status = 'ats_match'
        best_match_ats_name = ats_result.get('ats_name', 'unknown')
    else:
        ats_match_status = 'ats_missing'
        best_match_ats_name = 'N/A'  # Mandatory field, use N/A when no match

    # Extract ATS name from LLM (always required, even if empty)
    extracted_ats_name = ats_result.get('ats_name', 'unknown')

    # Get provider name (mandatory)
    llm_provider_name = metadata.get('llm_provider', 'unknown')

    # Create log entry with new simplified schema
    log_entry = LogATSMatch(
        application_id=application_id,
        html_snapshot=html_content[:50000],  # Store first 50KB to avoid huge text fields
        llm_provider_name=llm_provider_name,
        extracted_ats_name=extracted_ats_name,
        best_match_ats_name=best_match_ats_name,
        ats_match_status=ats_match_status
        # updated_at is auto-generated by server_default
    )

    db.add(log_entry)
    db.commit()

    logger.info(
        f"[_log_ats_match_attempt] Logged ATS match attempt: "
        f"app={application_id}, provider={llm_provider_name}, "
        f"extracted={extracted_ats_name}, matched={best_match_ats_name}, "
        f"status={ats_match_status}"
    )


def _identify_ats_with_llm(
    url: str,
    html_content: str,
    ats_list: List[Dict[str, Any]],
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Use LLM to identify which ATS platform is used by the job URL.

    Supports multiple providers: Gemini, OpenAI, Anthropic.

    Args:
        url: Job URL
        html_content: HTML content from the URL
        ats_list: List of available ATSs from database
        provider: LLM provider ('gemini', 'openai', 'anthropic')
                 If None, reads from database settings (ats_matching_model)
                 Falls back to env var ATS_MATCHING_LLM_PROVIDER
        model: Model name (e.g., 'gpt-4o-mini')
              If None, reads from database settings (ats_matching_model)
              Falls back to env var ATS_MATCHING_LLM_MODEL or provider default

    Returns:
        Dict with:
        - matched: bool (True if ATS identified)
        - ats_id: int (if matched)
        - ats_name: str (if matched)
        - confidence: str ('high', 'medium', 'low')
        - reason: str (explanation)
        - metadata: dict (tokens, cost, latency)
    """
    try:
        # If provider/model not specified, load from database settings
        if provider is None and model is None:
            from app.config import get_ats_matching_llm_config
            provider, model = get_ats_matching_llm_config()

        # Initialize multi-provider LLM client
        from app.orchestration.llm_client import LLMClient
        client = LLMClient(provider=provider, model=model)

        # Prepare ATS list for prompt
        ats_list_str = '\n'.join([f"- {ats['ats_name']} (ID: {ats['ats_id']})" for ats in ats_list])

        # Create prompt
        prompt = f"""Analyze the following job application URL and HTML content to identify which ATS (Applicant Tracking System) platform is being used.

URL: {url}

HTML Content (first 50KB):
{html_content[:10000]}

Available ATS platforms in our database:
{ats_list_str}

Instructions:
1. Look for ATS-specific identifiers in the URL and HTML:
   - Greenhouse: usually has 'greenhouse.io' or 'boards.greenhouse.io' in URL
   - Lever: usually has 'lever.co' or 'jobs.lever.co' in URL
   - Workday: usually has 'myworkdayjobs.com' in URL
   - Ashby: usually has 'ashbyhq.com' or 'jobs.ashbyhq.com' in URL
   - SmartRecruiters: usually has 'smartrecruiters.com' in URL
   - Other platforms: look for distinctive domain patterns or HTML metadata

2. Return your answer in **strict JSON format only** (no markdown, no additional text):
   {{
       "matched": true/false,
       "ats_name": "exact name from list" or null,
       "ats_id": integer or null,
       "confidence": "high/medium/low",
       "reason": "brief explanation"
   }}

3. Only set "matched": true if you can confidently identify the ATS from the available list.
4. Use the exact ats_name from the provided list.

IMPORTANT: Return ONLY the JSON object, with no markdown formatting or additional text."""

        # Call LLM (returns tuple: response_text, metadata)
        response_text, metadata = client.invoke(prompt)

        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()

        # Parse JSON response
        result = json.loads(response_text)

        if result.get('matched'):
            # Find the ats_id from the list
            matched_ats = next((ats for ats in ats_list if ats['ats_name'].lower() == result['ats_name'].lower()), None)
            if matched_ats:
                return {
                    'matched': True,
                    'ats_id': matched_ats['ats_id'],
                    'ats_name': matched_ats['ats_name'],
                    'confidence': result.get('confidence', 'unknown'),
                    'reason': result.get('reason', ''),
                    'metadata': metadata
                }

        return {
            'matched': False,
            'reason': result.get('reason', 'ATS not recognized or not in database'),
            'metadata': metadata
        }

    except json.JSONDecodeError as e:
        logger.error(f"[_identify_ats_with_llm] JSON parse error: {e}\nResponse: {response_text[:500]}")
        return {'matched': False, 'reason': f'JSON parse error: {str(e)}'}
    except Exception as e:
        logger.error(f"[_identify_ats_with_llm] Error: {e}")
        return {'matched': False, 'reason': f'Error: {str(e)}'}


def _identify_company_with_gemini(url: str, html_content: str, company_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Use Gemini to identify which company the job belongs to.

    Args:
        url: Job URL
        html_content: HTML content from the URL
        company_list: List of known companies from database

    Returns:
        Dict with:
        - matched: bool (True if company found in database)
        - identified: bool (True if company name identified even if not in DB)
        - company_id: int (if matched)
        - company_name: str (if matched or identified)
        - reason: str (if not matched/identified)
    """
    if not GEMINI_AVAILABLE:
        return {'matched': False, 'identified': False, 'reason': 'Gemini not available'}

    try:
        # Initialize Gemini
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            api_key=os.getenv('GEMINI_API_KEY'),
            temperature=0.0  # Deterministic output
        )

        # Prepare company list for prompt
        company_list_str = '\n'.join([f"- {c['company_name']} (ID: {c['company_id']})" for c in company_list])

        # Create prompt
        prompt = f"""Analyze the following job application URL and HTML content to identify which company is hiring.

URL: {url}

HTML Content (first 50KB):
{html_content[:10000]}

Known companies in our database:
{company_list_str if company_list else "(No companies in database yet)"}

Instructions:
1. Extract the company name from:
   - URL domain (e.g., 'acmecorp.greenhouse.io' → 'Acme Corp')
   - HTML title tag
   - Company branding in the page
   - Job posting content

2. Return your answer in **strict JSON format only** (no markdown, no additional text):
   {{
       "matched": true/false,
       "identified": true/false,
       "company_name": "Company Name" or null,
       "company_id": integer or null,
       "confidence": "high/medium/low",
       "reason": "brief explanation"
   }}

3. Set "matched": true ONLY if the company exists in our database list (case-insensitive match)
4. Set "identified": true if you can identify the company name from the URL/HTML, even if not in our database
5. If matched, use the exact company_name and company_id from the database
6. If only identified (not matched), provide the company name you extracted

IMPORTANT: Return ONLY the JSON object, with no markdown formatting or additional text."""

        # Call Gemini
        response = llm.invoke(prompt)
        response_text = response.content.strip()

        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()

        # Parse JSON response
        result = json.loads(response_text)

        if result.get('matched'):
            # Find the company_id from the list
            matched_company = next((c for c in company_list if c['company_name'].lower() == result['company_name'].lower()), None)
            if matched_company:
                return {
                    'matched': True,
                    'identified': True,
                    'company_id': matched_company['company_id'],
                    'company_name': matched_company['company_name'],
                    'confidence': result.get('confidence', 'unknown'),
                    'reason': result.get('reason', '')
                }

        if result.get('identified'):
            return {
                'matched': False,
                'identified': True,
                'company_name': result.get('company_name'),
                'confidence': result.get('confidence', 'unknown'),
                'reason': result.get('reason', 'Company identified but not in database')
            }

        return {
            'matched': False,
            'identified': False,
            'reason': result.get('reason', 'Company could not be identified')
        }

    except json.JSONDecodeError as e:
        logger.error(f"[_identify_company_with_gemini] JSON parse error: {e}\nResponse: {response_text[:500]}")
        return {'matched': False, 'identified': False, 'reason': f'JSON parse error: {str(e)}'}
    except Exception as e:
        logger.error(f"[_identify_company_with_gemini] Error: {e}")
        return {'matched': False, 'identified': False, 'reason': f'Error: {str(e)}'}


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_job_lifecycle_graph():
    """
    Create the LangGraph state machine for job lifecycle orchestration.

    State Machine Flow:
    ==================

    START → route_by_job_status
        ├→ det_match_score (new_url)
        │   └→ route_after_match_score
        │       ├→ existing_account_check (approved)
        │       │   └→ route_after_account_check
        │       │       ├→ existing_workflow_check (has_account)
        │       │       │   └→ route_after_workflow_check
        │       │       │       ├→ application_init (has_workflow)
        │       │       │       │   └→ END
        │       │       │       └→ END (missing_workflow)
        │       │       └→ END (missing_account)
        │       └→ END (low_priority, filtered_out)
        │
        └→ ai_match_score (new_api, new_webscraping)
            └→ route_after_match_score
                └→ (same flow as above)
    """
    if not LANGGRAPH_AVAILABLE:
        raise ImportError("LangGraph not available. Install with: pip install langgraph")

    workflow = StateGraph(JobLifecycleState)

    # Add nodes (State Machine v2 - only nodes from state-machine-spec-v2.md)
    workflow.add_node("det_match_score", det_match_score_node)
    workflow.add_node("ai_match_score", ai_match_score_node)
    workflow.add_node("create_application", create_application_node)
    workflow.add_node("ats_match", ats_match_node)
    workflow.add_node("company_match", company_match_node)
    # Note: Removed old nodes (existing_account_check, existing_workflow_check, application_init)
    # These are from state-machine-spec-v1 and not part of the new spec

    # Set conditional entry point (route based on job status)
    workflow.set_conditional_entry_point(
        route_by_job_status,
        {
            "det_match_score": "det_match_score",
            "ai_match_score": "ai_match_score",
        }
    )

    # After match scoring, route based on result
    # State Machine v2: approved_for_application → create_application (not existing_account_check)
    workflow.add_conditional_edges(
        "det_match_score",
        route_after_match_score,
        {
            "create_application": "create_application",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "ai_match_score",
        route_after_match_score,
        {
            "create_application": "create_application",
            END: END
        }
    )

    # State Machine v2: New workflow (strictly following state-machine-spec-v2.md)
    # create_application → ats_match → [conditional] → company_match → END
    workflow.add_edge("create_application", "ats_match")

    # After ats_match: route based on status
    # - ats_match → continue to company_match
    # - ats_missing → END (terminal state)
    workflow.add_conditional_edges(
        "ats_match",
        route_after_ats_match,
        {
            "company_match": "company_match",
            END: END
        }
    )

    # After company_match: all outcomes → END (STATE 2: Completed)
    # - company_match → END
    # - new_company → END
    # - missing_company → END (terminal state)
    workflow.add_conditional_edges(
        "company_match",
        route_after_company_match,
        {
            END: END
        }
    )

    return workflow.compile()


# =============================================================================
# PARALLEL PROCESSING
# =============================================================================

async def process_job_async(job: Job) -> JobLifecycleState:
    """
    Process a single job through the lifecycle orchestrator (async version).

    This function wraps the synchronous graph execution in asyncio to enable
    parallel processing of multiple jobs.

    Args:
        job: Job object from database

    Returns:
        Final state after processing
    """
    logger.info(f"[Worker] Processing Job {job.job_id}: {job.url} ({job.status})")

    # Initialize state
    # Note: Job model currently only has url, provider, status, match_score, profile_id
    # Fields like title, company, description are not in the model yet
    initial_state = JobLifecycleState(
        job_id=job.job_id,
        job_url=job.url,
        job_status=job.status,
        profile_id=job.profile_id,  # Carry profile_id in state
        title=None,  # Not in Job model yet
        company=None,  # Not in Job model yet
        description=None,  # Not in Job model yet
        provider=job.provider,
        match_score=job.match_score,
        match_explanation=None,
        application_id=None,  # State Machine v2
        has_existing_account=None,
        account_id=None,
        has_workflow=None,
        workflow_type=None,
        current_step='start',
        logs=[],
        errors=[],
        processed_at=None
    )

    # Create and run graph (in executor to avoid blocking)
    loop = asyncio.get_event_loop()
    graph = create_job_lifecycle_graph()

    # Run synchronous graph in executor
    final_state = await loop.run_in_executor(
        None,  # Use default executor
        graph.invoke,
        initial_state
    )

    # Set processed timestamp
    final_state['processed_at'] = datetime.utcnow().isoformat()

    # Log results
    logger.info(f"[Worker] Job {job.job_id} complete: {final_state['job_status']}")

    return final_state


async def process_jobs_parallel(jobs: List[Job], max_workers: int = 5) -> List[JobLifecycleState]:
    """
    Process multiple jobs in parallel using asyncio.

    Args:
        jobs: List of Job objects to process
        max_workers: Maximum number of concurrent workers (default: 5)

    Returns:
        List of final states for all processed jobs
    """
    logger.info(f"Processing {len(jobs)} jobs in parallel (max {max_workers} workers)")

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_workers)

    async def process_with_semaphore(job: Job) -> JobLifecycleState:
        """Process job with semaphore to limit concurrency"""
        async with semaphore:
            try:
                return await process_job_async(job)
            except Exception as e:
                logger.error(f"Error processing job {job.job_id}: {e}", exc_info=True)
                # Mark job as failed in database
                _update_job_in_db(job.job_id, status=JobStatus.APPLICATION_FAILED)
                # Return error state
                return JobLifecycleState(
                    job_id=job.job_id,
                    job_url=job.url,
                    job_status=JobStatus.APPLICATION_FAILED,
                    title=job.title,
                    company=job.company,
                    description=job.description,
                    provider=job.provider,
                    match_score=None,
                    match_explanation=None,
                    has_existing_account=None,
                    account_id=None,
                    has_workflow=None,
                    workflow_type=None,
                    current_step='error',
                    logs=[],
                    errors=[str(e)],
                    processed_at=datetime.utcnow().isoformat()
                )

    # Process all jobs in parallel
    tasks = [process_with_semaphore(job) for job in jobs]
    results = await asyncio.gather(*tasks)

    logger.info(f"Parallel processing complete: {len(results)} jobs processed")
    return results


# =============================================================================
# DATABASE LISTENER (Webhook-Style Processing with Parallel Execution)
# =============================================================================

def fetch_unprocessed_jobs(db: Session, limit: int = 100) -> List[Job]:
    """
    Fetch jobs that need processing from the database.

    Returns jobs with status in ['new_url', 'new_api', 'new_webscraping']
    ordered by created_at (oldest first) to avoid anti-bot detection.

    Args:
        db: Database session
        limit: Maximum number of jobs to fetch

    Returns:
        List of Job objects ready for processing
    """
    return db.query(Job).filter(
        Job.status.in_([
            JobStatus.NEW_URL,
            JobStatus.NEW_API,
            JobStatus.NEW_WEBSCRAPING
        ])
    ).order_by(
        Job.created_at.asc()  # Process oldest first
    ).limit(limit).all()


async def run_orchestrator_daemon_async(
    poll_interval: int = 30,
    batch_size: int = 100,
    max_workers: int = 10
):
    """
    Run the orchestrator as an async daemon that continuously monitors the database.

    This function implements parallel webhook-style processing:
    - Polls the database every poll_interval seconds
    - Fetches up to batch_size jobs with status in ['new_url', 'new_api', 'new_webscraping']
    - Processes up to max_workers jobs in parallel
    - Updates job status as they progress through the lifecycle

    Args:
        poll_interval: Seconds between database polls (default: 30)
        batch_size: Maximum jobs to fetch per batch (default: 100)
        max_workers: Maximum parallel workers (default: 10)

    Usage:
        >>> import asyncio
        >>> from app.orchestration import run_orchestrator_daemon_async
        >>> asyncio.run(run_orchestrator_daemon_async(poll_interval=30, max_workers=10))
    """
    logger.info("=== Starting Job Lifecycle Orchestrator Daemon (Async) ===")
    logger.info(f"Poll interval: {poll_interval} seconds")
    logger.info(f"Batch size: {batch_size} jobs")
    logger.info(f"Max parallel workers: {max_workers}")
    logger.info(f"Monitoring statuses: {[s.value for s in ENTRY_STATUSES]}")

    while True:
        try:
            db = SessionLocal()

            # Fetch unprocessed jobs
            jobs = fetch_unprocessed_jobs(db, limit=batch_size)

            if jobs:
                logger.info(f"Found {len(jobs)} unprocessed jobs - starting parallel processing")

                # Process jobs in parallel
                results = await process_jobs_parallel(jobs, max_workers=max_workers)

                # Log summary
                success_count = sum(1 for r in results if not r['errors'])
                error_count = len(results) - success_count
                logger.info(f"Batch complete: {success_count} success, {error_count} errors")

            else:
                logger.debug(f"No unprocessed jobs found (State 0: Sleepy System)")

            db.close()

            # Wait before next poll
            await asyncio.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Orchestrator daemon stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in orchestrator daemon: {e}", exc_info=True)
            await asyncio.sleep(poll_interval)


def run_orchestrator_daemon(
    poll_interval: int = 30,
    batch_size: int = 100,
    max_workers: int = 10
):
    """
    Synchronous wrapper for run_orchestrator_daemon_async.

    This is the main entry point for running the orchestrator as a daemon.

    Args:
        poll_interval: Seconds between database polls (default: 30)
        batch_size: Maximum jobs to fetch per batch (default: 100)
        max_workers: Maximum parallel workers (default: 10)

    Usage:
        >>> from app.orchestration import run_orchestrator_daemon
        >>> run_orchestrator_daemon(poll_interval=30, max_workers=10)
    """
    asyncio.run(run_orchestrator_daemon_async(poll_interval, batch_size, max_workers))


# =============================================================================
# SINGLE JOB PROCESSING (for manual testing)
# =============================================================================

def run_job_lifecycle_orchestrator(job_id: int) -> JobLifecycleState:
    """
    Main entry point to run the job lifecycle orchestrator for a specific job.

    This is useful for manual/one-time processing of a specific job.
    For continuous parallel processing, use run_orchestrator_daemon() instead.

    Args:
        job_id: Database ID of the job to process

    Returns:
        Final state after processing

    Usage:
        >>> from app.orchestration import run_job_lifecycle_orchestrator
        >>> result = run_job_lifecycle_orchestrator(job_id=123)
        >>> print(f"Final status: {result['job_status']}")
        >>> print(f"Match score: {result['match_score']}")
    """
    logger.info(f"=== Processing Single Job {job_id} ===")

    # Fetch job from database
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found in database")

        # Process the job using async version
        final_state = asyncio.run(process_job_async(job))

    finally:
        db.close()

    return final_state


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    """
    CLI entry point for testing/running the orchestrator.

    Usage:
        # Process a specific job
        python -m app.orchestration.job_lifecycle_graph --job-id 123

        # Run as daemon with parallel processing
        python -m app.orchestration.job_lifecycle_graph --daemon --poll-interval 30 --max-workers 10
    """
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Run job lifecycle orchestrator")
    parser.add_argument("--job-id", type=int, help="Process specific job ID")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon (continuous parallel processing)")
    parser.add_argument("--poll-interval", type=int, default=30, help="Daemon poll interval in seconds")
    parser.add_argument("--batch-size", type=int, default=100, help="Daemon batch size")
    parser.add_argument("--max-workers", type=int, default=10, help="Maximum parallel workers")
    args = parser.parse_args()

    try:
        if args.daemon:
            # Run as daemon with parallel processing
            run_orchestrator_daemon(
                poll_interval=args.poll_interval,
                batch_size=args.batch_size,
                max_workers=args.max_workers
            )
        elif args.job_id:
            # Process specific job
            result = run_job_lifecycle_orchestrator(args.job_id)
            print(f"\n✅ Success! Final status: {result['job_status']}")
            if result.get('match_score'):
                print(f"Match score: {result['match_score']:.2f}")
            sys.exit(0)
        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nStopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
