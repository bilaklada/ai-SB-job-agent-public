"""
Admin/Debug Routes

Lightweight read-only endpoints for inspecting system state without direct SQL.
These endpoints are for debugging and admin purposes.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, text, inspect
import logging

from app.db.session import get_db
from app.db.models import Application, Account, LogStatusChange, AIArtifact, Job, Profile, LLMProvider, LLMModel, Setting
from app.schemas.admin import (
    ApplicationRead,
    AccountRead,
    AIArtifactRead,
    LLMProviderRead,
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMModelRead,
    LLMModelCreate,
    LLMModelUpdate,
    SettingRead,
    SettingCreate,
    SettingUpdate
)
from pydantic import BaseModel, HttpUrl

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


# ============================================================================
# Profile Endpoints
# ============================================================================

class ProfileListItem(BaseModel):
    """Lightweight profile info for dropdowns and lists."""
    profile_id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True


@router.get("/profiles", response_model=List[ProfileListItem])
def list_profiles(db: Session = Depends(get_db)):
    """
    Get all profiles for dropdown selection.

    Returns lightweight profile info (id, name, email) for UI components
    like the profile selector in the New Task page.
    """
    profiles = db.query(Profile).order_by(Profile.profile_id).all()
    return profiles


@router.get("/applications/{application_id}", response_model=ApplicationRead)
def get_application(
    application_id: int,
    db: Session = Depends(get_db)
):
    """Get single application by ID."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail=f"Application {application_id} not found")
    return application


@router.get("/applications", response_model=List[ApplicationRead])
def list_applications(
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """List applications with optional filters."""
    query = db.query(Application)

    if job_id is not None:
        query = query.filter(Application.job_id == job_id)
    if status:
        query = query.filter(Application.status == status)

    applications = query.order_by(desc(Application.created_at)).offset(offset).limit(limit).all()
    return applications


@router.get("/accounts/{account_id}", response_model=AccountRead)
def get_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    """Get single account by ID."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    return account


@router.get("/accounts", response_model=List[AccountRead])
def list_accounts(
    portal_name: Optional[str] = Query(None, description="Filter by portal name"),
    account_health: Optional[str] = Query(None, description="Filter by health status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """List accounts with optional filters."""
    query = db.query(Account)

    if portal_name:
        query = query.filter(Account.portal_name == portal_name)
    if account_health:
        query = query.filter(Account.account_health == account_health)
    if is_active is not None:
        query = query.filter(Account.is_active == is_active)

    accounts = query.order_by(desc(Account.created_at)).offset(offset).limit(limit).all()
    return accounts


class LogStatusChangeRead(BaseModel):
    """Schema for reading log_status_change records."""
    lsc_id: int
    lsc_table: str
    profile_id: int
    job_id: int
    application_id: Optional[int]
    initial_status: str
    final_status: str
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/log-status-changes", response_model=List[LogStatusChangeRead])
def list_log_status_changes(
    lsc_table: Optional[str] = Query(None, description="Filter by table: jobs or applications"),
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    application_id: Optional[int] = Query(None, description="Filter by application ID"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """List status change logs with optional filters."""
    query = db.query(LogStatusChange)

    if lsc_table:
        query = query.filter(LogStatusChange.lsc_table == lsc_table)
    if job_id is not None:
        query = query.filter(LogStatusChange.job_id == job_id)
    if application_id is not None:
        query = query.filter(LogStatusChange.application_id == application_id)

    logs = query.order_by(desc(LogStatusChange.updated_at)).offset(offset).limit(limit).all()
    return logs


@router.get("/ai-artifacts/{artifact_id}", response_model=AIArtifactRead)
def get_ai_artifact(
    artifact_id: int,
    db: Session = Depends(get_db)
):
    """Get single AI artifact by ID."""
    artifact = db.query(AIArtifact).filter(AIArtifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail=f"AI artifact {artifact_id} not found")
    return artifact


@router.get("/ai-artifacts", response_model=List[AIArtifactRead])
def list_ai_artifacts(
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    artifact_type: Optional[str] = Query(None, description="Filter by artifact type"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """List AI artifacts with optional filters."""
    query = db.query(AIArtifact)

    if job_id is not None:
        query = query.filter(AIArtifact.job_id == job_id)
    if artifact_type:
        query = query.filter(AIArtifact.artifact_type == artifact_type)

    artifacts = query.order_by(desc(AIArtifact.created_at)).offset(offset).limit(limit).all()
    return artifacts


# ============================================================================
# Dynamic Database Introspection Endpoints
# ============================================================================


@router.get("/db/tables", response_model=List[str])
def list_database_tables(db: Session = Depends(get_db)):
    """
    List all tables in the database dynamically.

    This endpoint introspects the database schema and returns all available tables.
    Perfect for building dynamic table selectors in the frontend.
    """
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()

    # Filter out Alembic version table
    tables = [t for t in tables if t != 'alembic_version']

    return sorted(tables)


@router.get("/db/tables/{table_name}/schema")
def get_table_schema(
    table_name: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the schema (columns, types, nullable) for a specific table.

    Returns column definitions that can be used to dynamically render table headers
    and understand data types.
    """
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()

    if table_name not in tables:
        raise HTTPException(
            status_code=404,
            detail=f"Table '{table_name}' not found in database"
        )

    columns = inspector.get_columns(table_name)
    primary_keys = inspector.get_pk_constraint(table_name)['constrained_columns']
    foreign_keys = inspector.get_foreign_keys(table_name)

    # Format column information
    column_info = []
    for col in columns:
        column_info.append({
            "name": col['name'],
            "type": str(col['type']),
            "nullable": col['nullable'],
            "default": str(col['default']) if col['default'] is not None else None,
            "primary_key": col['name'] in primary_keys
        })

    # Format foreign key information
    fk_info = []
    for fk in foreign_keys:
        fk_info.append({
            "constrained_columns": fk['constrained_columns'],
            "referred_table": fk['referred_table'],
            "referred_columns": fk['referred_columns']
        })

    return {
        "table_name": table_name,
        "columns": column_info,
        "primary_keys": primary_keys,
        "foreign_keys": fk_info
    }


@router.get("/db/tables/{table_name}/data")
def get_table_data(
    table_name: str,
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Fetch data from any table with pagination.

    Returns both the data rows and metadata about total count and pagination.
    This is a generic endpoint that works with any table in the database.
    """
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()

    if table_name not in tables:
        raise HTTPException(
            status_code=404,
            detail=f"Table '{table_name}' not found in database"
        )

    # Get total count
    count_query = text(f"SELECT COUNT(*) as total FROM {table_name}")
    count_result = db.execute(count_query).fetchone()
    total_count = count_result[0] if count_result else 0

    # Get data with pagination
    # Order by first column (usually id) descending to get newest first
    columns = inspector.get_columns(table_name)
    first_column = columns[0]['name'] if columns else 'id'

    data_query = text(
        f"SELECT * FROM {table_name} ORDER BY {first_column} DESC LIMIT :limit OFFSET :offset"
    )
    result = db.execute(data_query, {"limit": limit, "offset": offset})

    # Convert rows to dictionaries
    rows = []
    for row in result:
        row_dict = dict(row._mapping)
        # Convert any non-serializable types to strings
        for key, value in row_dict.items():
            if value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
                row_dict[key] = str(value)
        rows.append(row_dict)

    return {
        "table_name": table_name,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total_count,
        "data": rows
    }


# ============================================================================
# Bulk Job Creation Endpoints
# ============================================================================


class BulkJobsRequest(BaseModel):
    """Request schema for creating multiple jobs from URLs."""
    urls: List[str]
    profile_id: int


class JobCreatedResponse(BaseModel):
    """Response schema for a created job."""
    id: int
    url: str
    status: str


class BulkJobsResponse(BaseModel):
    """Response schema for bulk job creation."""
    created: List[JobCreatedResponse]
    failed: List[Dict[str, str]]
    summary: Dict[str, int]


@router.post("/db/jobs/bulk-create-urls", response_model=BulkJobsResponse)
async def bulk_create_jobs_from_urls(
    request: BulkJobsRequest,
    db: Session = Depends(get_db)
):
    """
    Create multiple job records from a list of URLs.

    This endpoint implements Data Collection Method 1 (URL) from the state machine:
    - Creates jobs with status='new_url'
    - Sets provider='manual' (user-provided)
    - Automatically triggers orchestrator to process jobs through state machine

    Args:
        request: BulkJobsRequest containing list of URLs and profile_id

    Returns:
        BulkJobsResponse with created jobs and any failures
    """
    from app.orchestration.job_lifecycle_graph import process_job_async
    import asyncio
    # Verify profile exists
    profile = db.query(Profile).filter(Profile.profile_id == request.profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Profile {request.profile_id} not found"
        )

    created_jobs = []
    failed_jobs = []

    for url in request.urls:
        try:
            # Strip whitespace
            url = url.strip()

            # Skip empty URLs
            if not url:
                continue

            # Check if job with this URL already exists
            existing = db.query(Job).filter(Job.url == url).first()
            if existing:
                failed_jobs.append({
                    "url": url,
                    "reason": f"Job already exists with ID {existing.job_id}"
                })
                continue

            # Create new job with status='new_url'
            # Following state machine spec: new_url → det_match_score → match_score=1.0
            job = Job(
                url=url,
                provider='manual',         # User-provided URL
                status='new_url',          # Entry point for det_match_score (state machine)
                match_score=1.0,           # Deterministic for new_url (user explicitly selected)
                profile_id=request.profile_id,  # Link to selected profile
                # Optional fields remain null initially:
                # - title, company, description (can be scraped later if needed)
                # - location_country, location_city
                # Timestamps set explicitly (database default not configured yet)
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.add(job)
            db.flush()  # Get the ID without committing yet

            created_jobs.append(JobCreatedResponse(
                id=job.job_id,          # Fixed: use job_id instead of id
                url=job.url,
                status=job.status
            ))

        except Exception as e:
            failed_jobs.append({
                "url": url,
                "reason": str(e)
            })

    # Commit all successful jobs
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to commit jobs to database: {str(e)}"
        )

    # Automatically trigger orchestrator for each created job (State Machine v2)
    # Process jobs through state machine in the background
    if created_jobs:
        logger.info(f"[bulk-create-urls] Triggering orchestrator for {len(created_jobs)} jobs")

        # Create background tasks to process each job
        for job_response in created_jobs:
            job_id = job_response.id
            # Get fresh job instance from DB
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                try:
                    # Process job through state machine
                    logger.info(f"[bulk-create-urls] Processing job {job_id} through state machine")
                    final_state = await process_job_async(job)
                    logger.info(f"[bulk-create-urls] Job {job_id} processed: status={final_state['job_status']}, application_id={final_state.get('application_id')}")
                except Exception as e:
                    logger.error(f"[bulk-create-urls] Failed to process job {job_id}: {e}")

    # Return summary
    return BulkJobsResponse(
        created=created_jobs,
        failed=failed_jobs,
        summary={
            "total_submitted": len(request.urls),
            "created": len(created_jobs),
            "failed": len(failed_jobs)
        }
    )


# ============================================================================
# Orchestrator Trigger Endpoint (State Machine v2)
# ============================================================================

@router.post("/orchestrator/process-jobs")
async def trigger_job_processing(
    limit: int = Query(10, ge=1, le=100, description="Max jobs to process"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger orchestrator to process new jobs.

    Processes jobs with status in ['new_url', 'new_api', 'new_webscraping']
    through the state machine workflow.

    Returns:
        Summary of processed jobs with results
    """
    from app.orchestration.job_lifecycle_graph import process_jobs_batch, ENTRY_STATUSES

    # Get jobs that need processing
    jobs = db.query(Job).filter(Job.status.in_([s.value for s in ENTRY_STATUSES])).limit(limit).all()

    if not jobs:
        return {
            "message": "No jobs to process",
            "processed": 0,
            "statuses": {}
        }

    # Process jobs through state machine
    results = await process_jobs_batch(jobs, max_workers=3)

    # Summarize results
    status_counts = {}
    for result in results:
        status = result.get('job_status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "message": f"Processed {len(results)} jobs",
        "processed": len(results),
        "statuses": status_counts,
        "results": [
            {
                "job_id": r['job_id'],
                "status": r['job_status'],
                "application_id": r.get('application_id'),
                "errors": len(r.get('errors', []))
            }
            for r in results
        ]
    }


# ============================================================================
# LLM Providers CRUD
# ============================================================================

@router.get("/llm-providers", response_model=List[LLMProviderRead])
def list_llm_providers(db: Session = Depends(get_db)):
    """List all LLM providers."""
    providers = db.query(LLMProvider).order_by(LLMProvider.llm_provider_id).all()
    return providers


@router.post("/llm-providers", response_model=LLMProviderRead, status_code=201)
def create_llm_provider(
    provider: LLMProviderCreate,
    db: Session = Depends(get_db)
):
    """Create a new LLM provider."""
    # Check for duplicate provider name
    existing = db.query(LLMProvider).filter(
        LLMProvider.llm_provider_name == provider.llm_provider_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider.llm_provider_name}' already exists"
        )

    db_provider = LLMProvider(**provider.model_dump())
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    return db_provider


@router.patch("/llm-providers/{provider_id}", response_model=LLMProviderRead)
def update_llm_provider(
    provider_id: int,
    provider_update: LLMProviderUpdate,
    db: Session = Depends(get_db)
):
    """Update an LLM provider."""
    db_provider = db.query(LLMProvider).filter(
        LLMProvider.llm_provider_id == provider_id
    ).first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Check for duplicate name if updating name
    if provider_update.llm_provider_name:
        existing = db.query(LLMProvider).filter(
            LLMProvider.llm_provider_name == provider_update.llm_provider_name,
            LLMProvider.llm_provider_id != provider_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{provider_update.llm_provider_name}' already exists"
            )
        db_provider.llm_provider_name = provider_update.llm_provider_name

    db.commit()
    db.refresh(db_provider)
    return db_provider


@router.delete("/llm-providers/{provider_id}", status_code=204)
def delete_llm_provider(
    provider_id: int,
    db: Session = Depends(get_db)
):
    """Delete an LLM provider."""
    db_provider = db.query(LLMProvider).filter(
        LLMProvider.llm_provider_id == provider_id
    ).first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Check if provider has models
    models_count = db.query(LLMModel).filter(
        LLMModel.llm_provider_id == provider_id
    ).count()
    if models_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete provider: {models_count} models are using it"
        )

    db.delete(db_provider)
    db.commit()


# ============================================================================
# LLM Models CRUD
# ============================================================================

@router.get("/llm-models", response_model=List[LLMModelRead])
def list_llm_models(db: Session = Depends(get_db)):
    """List all LLM models with provider information."""
    models = db.query(LLMModel).order_by(
        LLMModel.llm_provider_id,
        LLMModel.llm_model_id
    ).all()
    return models


@router.post("/llm-models", response_model=LLMModelRead, status_code=201)
def create_llm_model(
    model: LLMModelCreate,
    db: Session = Depends(get_db)
):
    """Create a new LLM model."""
    # Verify provider exists
    provider = db.query(LLMProvider).filter(
        LLMProvider.llm_provider_id == model.llm_provider_id
    ).first()
    if not provider:
        raise HTTPException(
            status_code=400,
            detail=f"Provider ID {model.llm_provider_id} not found"
        )

    # Check for duplicate model name
    existing = db.query(LLMModel).filter(
        LLMModel.llm_model_name == model.llm_model_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model.llm_model_name}' already exists"
        )

    # Create model with provider name (denormalized)
    db_model = LLMModel(
        llm_model_name=model.llm_model_name,
        llm_provider_id=model.llm_provider_id,
        llm_provider_name=provider.llm_provider_name
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


@router.patch("/llm-models/{model_id}", response_model=LLMModelRead)
def update_llm_model(
    model_id: int,
    model_update: LLMModelUpdate,
    db: Session = Depends(get_db)
):
    """Update an LLM model."""
    db_model = db.query(LLMModel).filter(
        LLMModel.llm_model_id == model_id
    ).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Update model name if provided
    if model_update.llm_model_name:
        # Check for duplicate
        existing = db.query(LLMModel).filter(
            LLMModel.llm_model_name == model_update.llm_model_name,
            LLMModel.llm_model_id != model_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_update.llm_model_name}' already exists"
            )
        db_model.llm_model_name = model_update.llm_model_name

    # Update provider if provided
    if model_update.llm_provider_id:
        provider = db.query(LLMProvider).filter(
            LLMProvider.llm_provider_id == model_update.llm_provider_id
        ).first()
        if not provider:
            raise HTTPException(
                status_code=400,
                detail=f"Provider ID {model_update.llm_provider_id} not found"
            )
        db_model.llm_provider_id = model_update.llm_provider_id
        db_model.llm_provider_name = provider.llm_provider_name

    db.commit()
    db.refresh(db_model)
    return db_model


@router.delete("/llm-models/{model_id}", status_code=204)
def delete_llm_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """Delete an LLM model."""
    db_model = db.query(LLMModel).filter(
        LLMModel.llm_model_id == model_id
    ).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")

    db.delete(db_model)
    db.commit()


# ============================================================================
# Settings CRUD
# ============================================================================

@router.get("/settings", response_model=List[SettingRead])
def list_settings(db: Session = Depends(get_db)):
    """List all settings."""
    settings = db.query(Setting).order_by(Setting.setting_name).all()
    return settings


@router.get("/settings/{setting_name}", response_model=SettingRead)
def get_setting(
    setting_name: str,
    db: Session = Depends(get_db)
):
    """Get a specific setting by name."""
    setting = db.query(Setting).filter(
        Setting.setting_name == setting_name
    ).first()
    if not setting:
        raise HTTPException(
            status_code=404,
            detail=f"Setting '{setting_name}' not found"
        )
    return setting


@router.put("/settings/{setting_name}", response_model=SettingRead)
def upsert_setting(
    setting_name: str,
    setting_update: SettingUpdate,
    db: Session = Depends(get_db)
):
    """Create or update a setting."""
    setting = db.query(Setting).filter(
        Setting.setting_name == setting_name
    ).first()

    if setting:
        # Update existing
        setting.setting_value = setting_update.setting_value
        db.commit()
        db.refresh(setting)
    else:
        # Create new
        setting = Setting(
            setting_name=setting_name,
            setting_value=setting_update.setting_value
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)

    return setting


@router.delete("/settings/{setting_name}", status_code=204)
def delete_setting(
    setting_name: str,
    db: Session = Depends(get_db)
):
    """Delete a setting."""
    setting = db.query(Setting).filter(
        Setting.setting_name == setting_name
    ).first()
    if not setting:
        raise HTTPException(
            status_code=404,
            detail=f"Setting '{setting_name}' not found"
        )

    db.delete(setting)
    db.commit()
