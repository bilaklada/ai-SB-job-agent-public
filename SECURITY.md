# Security Policy

## Scope

This repository contains code and documentation for an AI-assisted job-search and application system. Public release requires strict handling of secrets, personal data, and automation artifacts.

## What Must Never Be Committed

Do not commit:

- `.env` files or real credentials
- API keys, tokens, passwords, webhook URLs, or cookies
- browser session state, auth files, HAR captures, or screenshots from real runs
- real candidate profiles, resumes, diplomas, or application answers
- production database dumps, logs, or generated artifacts containing user data
- local machine paths or internal infrastructure details that are not needed publicly

## Secret Handling

- Use `.env.example` as the public template.
- Keep real values in untracked local env files or a dedicated secret manager.
- Rotate credentials immediately if a secret was ever committed, even temporarily.
- Treat browser automation outputs as sensitive by default.

## Vulnerability Reporting

If you discover a security issue:

1. Do not open a public issue with exploit details or leaked data.
2. Prefer GitHub private vulnerability reporting if enabled for the repository.
3. If that is unavailable, contact the repository maintainer privately through the project's configured contact channel.
4. Include reproduction steps, impact, and any relevant file paths.

## Public Repository Limitations

This repository has been sanitized for public release, but sanitization cannot guarantee that:

- historical Git objects are free of every previously committed secret
- every experimental script is production-safe
- every browser automation path has been hardened for hostile environments

Before any public launch or production use, maintainers should manually review:

- Git history for historical secrets or personal data
- Docker and Terraform defaults
- browser automation logging and artifact retention
- database contents used during local testing

## Operational Recommendations

- run browser automation with dedicated low-privilege accounts
- isolate storage for candidate documents and generated artifacts
- keep humans in the loop for live submission workflows
- avoid logging raw prompts, responses, or URLs if they may contain private data
- review dependencies and container images regularly
