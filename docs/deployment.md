# Deployment And Infrastructure

## Docker

The repository includes two main container targets:

- `Dockerfile` for the backend API
- `Dockerfile.agent` for isolated browser automation

`docker-compose.yml` is the main local orchestration entry point and wires together:

- FastAPI backend
- Next.js frontend
- optional browser agent profile

## Terraform

The `terraform/` directory contains AWS scaffolding for:

- RDS
- ECS
- ECR
- related networking/backend configuration

Treat it as a starting point, not a turnkey production deployment. Public release removed private operational context, so maintainers should review:

- region and account assumptions
- CIDR exposure
- state backend configuration
- secret handling
- environment separation

## Before Real Deployment

Review at minimum:

- `terraform.tfvars` handling
- remote state storage and locking
- database access controls
- container image hardening
- runtime secret delivery
- logging and artifact retention

## Recommended Release Posture

For a serious public deployment, prefer:

- a dedicated secrets manager
- private networking for the database
- explicit environment separation
- restricted IAM roles
- sanitized logging
- manual review before enabling live autonomous submission paths
