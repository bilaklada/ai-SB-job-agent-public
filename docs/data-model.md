# Data Model

The database schema is defined in `app/db/models.py` and evolved through Alembic migrations in `alembic/versions/`.

## Core Workflow Tables

### `jobs`

Primary unit of work for the system.

Key roles:

- stores normalized job postings
- tracks lifecycle status
- links each job to a target candidate profile
- holds match score and provider metadata

Typical entry statuses visible in code:

- `new_url`
- `new_api`
- `new_webscraping`

Typical downstream statuses:

- `approved_for_application`
- `low_priority`
- `filtered_out`
- `application_in_progress`
- `applied`
- `application_failed`
- `requires_manual_check`

### `applications`

Represents an application attempt for a specific job/profile pair.

Links may include:

- ATS
- company
- account
- workflow

This table is where the system records application-level progress independently of job discovery.

### `profiles`

Structured candidate data used by the system.

The current schema mixes relational fields with flexible JSONB columns:

- personal/contact data
- work authorization and availability
- `experience_json`
- `skills_json`
- `prefs_json`
- profile links such as LinkedIn or GitHub

### `documents`

Metadata for files associated with a profile.

The table stores descriptors and storage keys, not binary blobs. It is designed around object storage-backed document retrieval during automation.

## Operational Metadata Tables

### `accounts`

Portal login/account records associated with companies or application flows.

The schema assumes credentials will be stored securely outside the public repository. Any live deployment should encrypt or externalize secrets appropriately.

### `ai_artifacts`

Cache table for structured or generated AI outputs such as:

- parsed vacancy data
- company context
- motivations
- cover letters
- match explanations

### `log_status_change`

Tracks state transitions for jobs and applications.

### `log_ats_match`

Stores ATS matching / provider inference evidence and metadata.

## Reference And Routing Tables

### `atss`

Normalized ATS registry.

### `workflows`

Registry of automation workflow identifiers.

### `companies`

Connects companies to ATS, account, and workflow metadata.

### `llm_providers` and `llm_models`

Runtime-configurable registry tables for selectable LLM providers and models.

### `settings`

JSON-backed application settings table used for runtime-tunable configuration, including LLM-related choices.

## Design Characteristics

The schema shows several architectural choices clearly:

- relational persistence is the system backbone
- flexible JSONB columns are used where profile and artifact shapes are expected to evolve
- denormalized fields are used selectively for convenience and operational querying
- orchestration is expected to be resumable and inspectable through persisted state

## Sample Data

A sanitized example profile payload is available at [examples/profile.example.json](../examples/profile.example.json).
