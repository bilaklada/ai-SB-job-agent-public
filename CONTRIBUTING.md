# Contributing

This repository is a sanitized public version of an internal project. Contributions should improve the public codebase without rewriting its core product direction or flattening the system into something simpler than it is.

For the detailed project roadmap, delivery phases, and two-developer collaboration model, see [docs/development-roadmap.md](docs/development-roadmap.md).

## Contribution Priorities

The highest-value contributions are:

- documentation accuracy and architectural clarity
- test coverage for existing behavior
- bug fixes that preserve intended workflows
- security hardening and secret-handling improvements
- container, deployment, and developer-experience improvements
- cleanup of public-facing comments, naming, and structure

Changes that alter product logic, workflow semantics, ranking behavior, or automation strategy should be treated as a separate design discussion.

## Ground Rules

- Keep behavior changes scoped and explicit.
- Do not commit secrets, personal data, browser state, or generated artifacts.
- Prefer small, reviewable pull requests.
- If docs and code disagree, fix the docs or clearly call out the mismatch.
- Preserve technically important complexity; do not oversimplify the architecture for presentation.

## Local Setup

1. Copy `.env.example` to `.env`.
2. Set the minimum values required for your workflow.
3. Start services with `docker-compose up --build`, or run components directly if you prefer.
4. For backend tests, install the Python dependencies from `requirements.txt`.
5. For frontend work, use the `frontend/` workspace.

Reference docs:

- [docs/setup.md](docs/setup.md)
- [docs/deployment.md](docs/deployment.md)
- [frontend/README.md](frontend/README.md)
- [terraform/README.md](terraform/README.md)

## Development Workflow

### Backend

- FastAPI entry point: `app/main.py`
- API routes: `app/api/`
- ORM models: `app/db/models.py`
- Orchestration modules: `app/orchestration/`
- Provider adapters: `app/providers/`

### Frontend

- Next.js app: `frontend/app/`
- reusable components: `frontend/components/`
- backend client: `frontend/lib/api.ts`

### Infrastructure

- local containers: `docker-compose.yml`, `Dockerfile`, `Dockerfile.agent`
- AWS Terraform: `terraform/`

## Testing

Run the checks relevant to your change before opening a PR.

Backend:

```bash
pytest
```

Frontend:

```bash
cd frontend
npm install
npm run lint
```

Terraform:

```bash
cd terraform
terraform fmt
terraform validate
```

If you cannot run a check, say so clearly in the PR description.

## Documentation Expectations

This repository relies heavily on documentation to explain architecture and current maturity. Documentation changes should:

- reflect the code that exists today
- distinguish implemented behavior from planned behavior
- avoid internal-only process notes
- avoid personal examples unless they are clearly genericized

## Pull Requests

Please include:

- what changed
- whether behavior changed
- what you tested
- any remaining risks or follow-up work

If the change touches security, credentials, browser automation, or candidate data handling, call that out explicitly.
