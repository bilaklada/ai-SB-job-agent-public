# Terraform

This directory contains AWS infrastructure scaffolding for the project.

## What Is Here

- provider and backend configuration
- RDS resources
- ECS/ECR resources
- outputs and variable definitions
- a public-safe `terraform.tfvars.example`

## Quick Start

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt
terraform validate
terraform plan
```

## Security Notes

- Do not commit `terraform.tfvars`, state files, or `.terraform/`.
- Review public exposure carefully before applying changes.
- Replace all placeholder secrets with real values through secure local files or a secret manager.

## Public Repository Caveat

The original private project included environment-specific deployment context that is not part of this public tree. Review every variable and resource assumption before using this configuration outside a sandbox or personal development account.
