# Development Roadmap

This document is the engineering roadmap and delivery history for the public repository. It is intended to show how the codebase was developed, what has already been implemented, how a two-developer team split work, and what remains before the system becomes a fuller autonomous job-search and application platform.

It is based on the current codebase plus the repository history. Where the history shows intent but the current tree does not fully implement that intent yet, this document treats the work as partial rather than complete.

## Purpose

The system is not just a browser bot and not just a CRUD app. The target architecture is a stateful autonomous workflow that combines:

- provider/API job ingestion
- database-backed orchestration
- LLM-assisted routing and evaluation
- ATS/portal detection
- browser automation in an isolated runtime
- operational visibility through an admin UI

The development path reflects that architecture: infrastructure first, then schema and APIs, then ingestion, then orchestration, then browser-agent and ATS intelligence, then admin tooling and hardening.

## Two-Developer Delivery Model

The project was built as a two-core-developer effort rather than a large team. The repository history shows a practical split into two moving workstreams.

### Workstream A: Platform, Data, API, And Infrastructure

Primary responsibilities in this stream:

- FastAPI service foundation
- configuration and environment handling
- SQLAlchemy models and Alembic migrations
- provider ingestion and normalization
- Docker and Terraform scaffolding
- database integration and operational bootstrapping
- repository-level documentation and architecture framing

### Workstream B: Automation, Intelligence, And Operator Tooling

Primary responsibilities in this stream:

- lifecycle orchestration
- ATS matching / ATS detection
- LLM provider configuration and observability
- browser-agent runtime scaffolding
- VNC-based visible browser automation
- frontend admin UI and operator workflows
- settings management and internal control surfaces

### Collaboration Pattern

The two workstreams were not strictly isolated. The pattern visible in the repository history is:

- one developer builds or stabilizes a subsystem boundary
- the other builds on top of it with a higher-layer capability
- documentation is updated after major slices land
- commits are kept subsystem-scoped rather than mixing unrelated edits

That is why the repository feels layered: data model work, orchestration work, UI work, and infra work were typically delivered as explicit slices.

## Commit And Branch Discipline

The Git history shows a consistent preference for structured prefixes:

- `feat`
- `fix`
- `refactor`
- `docs`
- `test`
- `chore`
- `infra`

This is worth preserving because it makes a complex repository readable. Good contributions to this project should continue to produce commits that are:

- subsystem-specific
- technically descriptive
- traceable to a single architectural concern

Representative examples from the repository history:

- `833b523` - full backend foundation
- `92a5eab` - Alembic migration setup
- `d1c963b` - Adzuna integration
- `4a174d1` - JSearch provider
- `1f98155` - state machine v2 with application creation and AI matching
- `1fea1e8` - multi-provider LLM support and ATS observability
- `59538ab` - LLM/settings CRUD surface
- `28f88c4` - editable admin table support
- `f5d2c17` - settings page
- `82e78e0` - DataTable edit-mode stabilization

## Roadmap Summary

| Phase | Area | Current State |
|------|------|---------------|
| 0 | Foundation and infrastructure scaffolding | Mostly complete |
| 1 | Core backend API and jobs schema | Complete for current scope |
| 2 | Provider ingestion and normalization | Implemented for Adzuna and JSearch |
| 3 | Expanded data model | Implemented and migrated |
| 4 | Lifecycle orchestration and execution state | Partially implemented |
| 5 | LLM and ATS intelligence | Partially implemented, strongest around ATS detection |
| 6 | Browser automation / applicant agent | Scaffolded, not complete |
| 7 | Admin UI and runtime control surfaces | Substantially implemented |
| 8 | Production hardening and autonomous completion path | Still open |

## Phase 0: Foundation And Infrastructure

### Objective

Create a stable engineering base for a non-trivial AI systems project:

- service bootstrapping
- environment/config management
- containerized local development
- database connectivity
- cloud deployment scaffolding

### Implemented

- FastAPI application entrypoint and health endpoint
- Pydantic settings-based configuration surface in `app/config.py`
- Docker Compose local stack
- backend production Dockerfile
- isolated browser-agent Dockerfile
- PostgreSQL/Alembic setup
- Terraform scaffolding for AWS resources
- remote-state-oriented Terraform structure
- repository-level ignore rules and env template patterns

### Evidence In Current Tree

- `app/main.py`
- `app/config.py`
- `docker-compose.yml`
- `Dockerfile`
- `Dockerfile.agent`
- `terraform/`
- `alembic/`

### Remaining

- verified ECS/ECR deployment from the public tree
- CI/CD activation rather than template-only presence
- public deployment runbook for a fresh account
- clean compatibility matrix for supported Python/Node versions

## Phase 1: Core Backend API And Jobs Schema

### Objective

Build the first reliable relational backbone around `jobs`, with a minimal but real API.

### Implemented

- SQLAlchemy base/session pattern
- full `jobs` ORM model
- Pydantic request/response schemas
- CRUD endpoints for jobs
- filtering and pagination
- health endpoint
- test coverage for the early API/model layer
- migration-based schema evolution

### Representative Artifacts

- `app/db/session.py`
- `app/db/models.py`
- `app/schemas/job.py`
- `app/api/routes_jobs.py`
- `tests/test_api_jobs.py`
- `tests/test_job_model.py`

### Current Assessment

This phase is effectively complete for the repository’s current public scope.

### Remaining

- tighten compatibility between current pinned dependencies and supported Python versions
- expand tests so the API layer stays stable while orchestration evolves

## Phase 2: Provider Ingestion And Normalization

### Objective

Bring external jobs into the system through reusable adapters and a normalized schema rather than manual-only inserts.

### Implemented

- provider abstraction via `BaseJobProvider`
- Adzuna adapter
- JSearch adapter
- service-layer ingestion functions
- API endpoints for provider-backed fetches
- remote-only filtering logic for JSearch
- normalization into the internal jobs schema

### Representative Artifacts

- `app/providers/base.py`
- `app/providers/adzuna.py`
- `app/providers/jsearch.py`
- `app/services/jobs_service.py`
- `app/api/routes_jobs.py`
- `tests/test_adzuna_provider.py`

### Current Assessment

This phase is implemented for two sources and is enough to demonstrate the ingestion architecture credibly.

### Remaining

- scheduler or queue-driven provider polling
- stronger dedup rules across provider identifiers
- provider-level quality controls before jobs enter downstream automation
- broader provider coverage if the project expands

## Phase 3: Expanded Data Layer

### Objective

Move from a single-table prototype to a persistent workflow model capable of storing profiles, applications, artifacts, and routing metadata.

### Implemented

- `applications`
- `accounts`
- `profiles`
- `documents`
- `ai_artifacts`
- `log_status_change`
- `log_ats_match`
- `atss`
- `workflows`
- `companies`
- `llm_providers`
- `llm_models`
- `settings`

### Why This Phase Matters

This is where the project stops being a toy job collector and becomes a stateful platform. The schema shows the intended system boundaries clearly:

- candidate state
- job state
- application state
- ATS routing state
- AI artifact caching
- runtime model/provider configuration

### Representative Commits

- `3d83f4a` - application table refactor
- `5400dd5` - companies table
- `1fea1e8` - multi-provider LLM support and observability
- `59538ab` - settings / management tables

### Current Assessment

This phase is materially implemented and is one of the strongest parts of the repository.

### Remaining

- enforce more production-grade constraints around credential handling in `accounts`
- add higher-confidence data migration verification tests
- continue cleanup of historical schema drift as the system stabilizes

## Phase 4: Lifecycle Orchestration

### Objective

Introduce a real job-processing flow instead of leaving jobs as static records.

### Implemented

- asynchronous lifecycle orchestration in `app/orchestration/job_lifecycle_graph.py`
- explicit entry-state handling for manually added and provider-sourced jobs
- deterministic approval path for manual URLs
- application creation from the orchestrator path
- database-backed status updates
- manual trigger endpoint for processing batches
- profile-aware manual URL submission flow in the admin API/frontend

### Representative Artifacts

- `app/orchestration/job_lifecycle_graph.py`
- `app/api/routes_admin.py`
- `frontend/app/new-task/page.tsx`

### Current Assessment

This phase is partially implemented. The state-machine backbone exists, but the downstream execution path is not yet fully closed.

### Remaining

- more complete workflow/account resolution logic
- stronger failure recovery / retry semantics
- tighter bridge from orchestration result to browser execution
- broader test coverage for transition correctness

## Phase 5: LLM And ATS Intelligence

### Objective

Add decision-making and routing intelligence where deterministic rules are not enough.

### Implemented

- multi-provider LLM client surface
- provider/model selection via env and DB-backed settings
- token and cost extraction logic
- ATS matching observability
- advanced ATS detection subsystem with progressive evidence levels
- settings-controlled model selection for ATS-related paths

### Strongest Implemented Subsystem

The most sophisticated intelligence slice in the repository today is `app/orchestration/ats_detection/`.

It includes:

- URL evidence
- DOM evidence
- apply-button evidence
- network evidence
- proof validation and route eligibility gating

This is the clearest example in the codebase of careful AI/system design rather than one-shot prompt wiring.

### Representative Commits

- `1fea1e8` - multi-provider LLM support and ATS observability
- `6e6e7a8` - log_ats_match simplification plus LLM reference tables
- `1244d0b` - DB-backed ATS model selection
- `51f092e` / `a15f2d2` / `c40e11f` - ATS detection planning and implementation arc

### Current Assessment

Partially implemented overall, but with serious depth in ATS intelligence.

### Remaining

- full rule-based vacancy filtering service
- stable AI match scoring path that is transparently tested
- vacancy parsing and company-info extraction pipelines
- reusable answer generation for form completion
- production-quality prompt and artifact lifecycle management

## Phase 6: Browser Automation / Applicant Agent

### Objective

Move from “the system knows what to do” to “the system can execute it on real portals.”

### Implemented

- isolated applicant-agent runtime
- LangGraph-based applicant-agent scaffold
- Playwright/browser-use oriented dependency split
- VNC-visible automation environment
- portal-type analysis and strategy selection
- basic agent test scripts and runtime hooks

### Representative Artifacts

- `app/agents/applicant_agent.py`
- `Dockerfile.agent`
- `scripts/vnc_entrypoint.sh`
- `scripts/test_applicant_agent.py`

### Current Assessment

This phase is scaffolded but not complete. The public repository shows the execution architecture clearly, but not a finished cross-portal application bot.

### Remaining

- robust portal-specific drivers, beginning with Greenhouse-class flows
- safe container-per-application management if that remains the design direction
- deterministic document upload path
- reusable profile loader for browser execution
- account creation / reuse logic
- no-submit / dry-run versus live-submit control plane
- end-to-end application tests

## Phase 7: Admin UI And Runtime Control Surfaces

### Objective

Give operators visibility into the database-backed workflow and enough control to inspect and steer the system without writing SQL.

### Implemented

- Next.js admin UI
- dynamic table discovery
- schema-driven universal table rendering
- manual URL submission page with profile selection
- settings page
- editable LLM provider and model management
- backend CRUD support for these admin flows

### Representative Commits

- `59538ab` - provider/model/settings CRUD
- `28f88c4` - editable data table
- `f5d2c17` - settings page
- `82e78e0` - edit-mode stabilization and UX fixes

### Current Assessment

This phase is substantially implemented and gives the repository a strong operational story. The frontend is not decorative; it directly reflects the backend’s administrative needs.

### Remaining

- better operator-level validation and error surfacing
- more intentional permissions model if the UI ever becomes multi-user
- cleaner read/write boundaries for sensitive tables
- richer application run inspection views

## Phase 8: Hardening Toward A Full Autonomous Agent

### Objective

Close the gap between a serious prototype and a safer end-to-end autonomous system.

### Still Open

- email verification / inbox integration
- stable full application form completion pipeline
- complete document retrieval and upload pipeline
- retry and incident handling for failed runs
- environment-compatible test matrix
- deployment validation from clean infrastructure
- security review of historical Git objects
- dependency and packaging cleanup

## Milestone Timeline

The delivery pattern visible in Git can be summarized like this:

1. Foundation and service bootstrap.
2. Jobs API and database model baseline.
3. Migration system and cloud/database scaffolding.
4. Adzuna ingestion.
5. JSearch ingestion and remote-only positioning.
6. Browser-agent architecture and visible VNC automation.
7. Expanded application/ATS/company/workflow schema.
8. Lifecycle state machine and audit logging.
9. Multi-provider LLM support and ATS observability.
10. Settings-backed model control and admin UI editing.
11. Deep ATS detection planning and implementation.

That sequence is coherent with the repository as it stands today: the team built the base system first, then the orchestration/data model, then the intelligence-heavy routing pieces, while simultaneously improving operator tooling.

## What Is Already Demonstrated Well In Public

The repository already demonstrates:

- serious relational modeling
- orchestration-first system thinking
- explicit ATS intelligence work
- clear separation between main app and isolated automation runtime
- evidence of iterative collaboration between two developers
- disciplined, subsystem-oriented commit history

## What Still Needs To Be Built To Reach The Full Vision

To fully realize the autonomous agent vision described by the project, the next major delivery steps are:

1. Complete the gap between lifecycle orchestration and browser execution.
2. Finish the deterministic/document/profile side of form filling.
3. Add email/account verification loops where portal flows require them.
4. Stabilize LLM-driven classification and answer-generation paths.
5. Build end-to-end tests around a dry-run applicant workflow.
6. Validate deployment and packaging on supported runtime versions.

## Guidance For New Contributors

If you want to contribute in a way that matches the project’s real trajectory, good starting slices are:

- test hardening around existing orchestration behavior
- provider/dedup cleanup
- safer account/document handling
- admin UI improvements tied directly to backend surfaces
- ATS detection tests and validation tooling
- browser-agent observability rather than feature sprawl

The best contributions to this repository are those that make the system more inspectable, more reliable, and more faithful to its existing architecture.
