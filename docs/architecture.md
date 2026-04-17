# Architecture

## System Shape

The repository implements a database-backed autonomous workflow with five visible layers:

1. Integration
2. Intelligence
3. Execution
4. Control
5. Data

That split is reflected in the code layout rather than being purely conceptual.

## 1. Integration Layer

### Job intake

Code:

- `app/providers/base.py`
- `app/providers/adzuna.py`
- `app/providers/jsearch.py`
- `app/services/jobs_service.py`
- `app/api/routes_jobs.py`

Current intake paths:

- Adzuna API ingestion
- JSearch API ingestion
- manual URL submission through `/admin/db/jobs/bulk-create-urls`

The provider adapters normalize external payloads into the internal `jobs` schema before persistence.

### Email and external accounts

The config surface includes IMAP/email credentials and account-related schema, but the public repository is not a complete mail-driven application bot. The data model and configuration hooks exist; the surrounding integration remains partial.

## 2. Intelligence Layer

### Job lifecycle orchestration

Code:

- `app/orchestration/job_lifecycle_graph.py`

This module is the main state-machine implementation in the repository. It handles:

- entry statuses such as `new_url`, `new_api`, and `new_webscraping`
- deterministic approval for manually submitted URLs
- status transitions persisted back to the database
- application record creation
- workflow/account existence checks
- batch processing with async worker concurrency

### LLM access

Code:

- `app/orchestration/llm_client.py`
- `app/orchestration/llm_providers.py`
- `app/config.py`

The code supports multiple LLM providers through environment configuration and database-backed settings. The current public implementation is strongest around ATS matching/detection rather than generalized answer generation across the full stack.

### ATS detection subsystem

Code:

- `app/orchestration/ats_detection/`

This is the most technically developed orchestration submodule in the repository. It implements progressive evidence gathering:

- L1: URL-level heuristics
- L2: DOM inspection
- L3: apply-button and page interaction evidence
- L4: Playwright network capture with proof validation

The design goal visible in the code is to avoid false routing by requiring progressively stronger evidence before a route is considered eligible.

## 3. Execution Layer

### API-triggered execution

Execution is initiated either by:

- provider-backed job ingestion endpoints
- manual URL bulk creation
- explicit orchestrator trigger endpoints

The public code does not present a separate distributed worker system in normal local development. The orchestration path is invoked directly from the backend.

### Browser automation container

Code:

- `Dockerfile.agent`
- `scripts/vnc_entrypoint.sh`
- `app/agents/applicant_agent.py`

The repository contains an isolated worker image intended for browser automation experiments. It combines:

- Playwright-capable runtime dependencies
- a VNC-accessible virtual desktop
- non-root execution
- read-only mounts for application code where possible

Portal-specific automation remains incomplete in the public tree, but the isolation pattern is part of the architecture.

## 4. Control Layer

### Admin API

Code:

- `app/api/routes_admin.py`

The admin surface is intentionally pragmatic. It exposes:

- profile listings
- application/account/artifact inspection
- dynamic table/schema/data introspection
- bulk manual URL creation
- orchestrator trigger endpoint
- CRUD for LLM providers, LLM models, and runtime settings

### Frontend

Code:

- `frontend/app/`
- `frontend/components/`
- `frontend/lib/api.ts`

The frontend is an operational UI for the backend rather than a polished end-user product. It focuses on:

- database exploration
- admin editing for selected configuration tables
- manual task creation

## 5. Data Layer

Code:

- `app/db/models.py`
- `alembic/versions/`

The persistence layer is central to the system. Jobs, applications, profiles, accounts, documents, AI artifacts, ATS metadata, workflows, companies, LLM configuration, and runtime settings are all database-backed.

This is important to understanding the project: the system is not just a browser bot. It is designed as a stateful orchestration platform around a relational data model.

## Execution Flow

The current public flow looks like this:

1. Jobs arrive through provider adapters or manual URL submission.
2. Jobs are normalized into `jobs`.
3. The lifecycle graph reads eligible jobs from the database.
4. Matching / routing / ATS detection logic updates job status.
5. Application records are created and linked to profiles plus optional ATS/company/workflow/account data.
6. Browser automation can be invoked in an isolated environment for supported flows.
7. Admin endpoints and the frontend expose state for inspection and control.

## Important Boundaries

- The public repo contains real architectural depth but uneven product completeness.
- Some schema and config surfaces exist ahead of fully implemented workflows.
- Documentation should be read as "implemented structure plus visible in-progress direction", not as a claim that every autonomous path is production-ready today.
