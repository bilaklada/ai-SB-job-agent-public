# =============================================================================
# Terraform Main Configuration
# =============================================================================
#
# This file configures Terraform itself and the AWS provider.
#
# Usage:
#   terraform init       # Initialize and download providers
#   terraform plan       # Preview changes
#   terraform apply      # Apply changes
#   terraform destroy    # Destroy infrastructure (use with caution!)
#
# =============================================================================

# -----------------------------------------------------------------------------
# TERRAFORM CONFIGURATION
# -----------------------------------------------------------------------------

terraform {
  # Require Terraform 1.0 or higher
  required_version = ">= 1.0"

  # Required providers
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0" # Use AWS provider version 5.x
    }
  }

  # Backend configuration is in backend.tf
  # This allows easier switching between local and remote backends
}

# -----------------------------------------------------------------------------
# AWS PROVIDER CONFIGURATION
# -----------------------------------------------------------------------------

provider "aws" {
  region = var.aws_region

  # Default tags applied to ALL resources
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Repository  = "ai-job-agent"
    }
  }
}

# -----------------------------------------------------------------------------
# LOCALS
# -----------------------------------------------------------------------------

locals {
  # Common name prefix
  name_prefix = "${var.project_name}-${var.environment}"

  # Common tags
  common_tags = merge(
    var.tags,
    {
      Terraform   = "true"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# -----------------------------------------------------------------------------
# ADDITIONAL NOTES
# -----------------------------------------------------------------------------

# Cost Optimization Tips:
# - Use db.t4g.micro for development (cheapest ARM-based instance)
# - Set db_multi_az = false for dev (multi-AZ doubles cost)
# - Use gp2 storage instead of gp3 for < 200GB
# - Set backup_retention to 7 days minimum (more days = more cost)
# - Enable deletion_protection = true in production
# - Use Reserved Instances for 1-year commitment (40% savings)

# Security Best Practices:
# - Set db_publicly_accessible = false in production
# - Use specific CIDR blocks in allowed_cidr_blocks (not 0.0.0.0/0)
# - Store db_password in AWS Secrets Manager
# - Enable storage_encrypted = true (already default)
# - Use VPC with private subnets for RDS
# - Enable CloudWatch alarms for monitoring

# Backup & Recovery:
# - Automated backups retained for backup_retention_period days
# - Set skip_final_snapshot = false in production
# - Test restore procedure regularly
# - Consider cross-region backup replication for DR

# Monitoring:
# - CloudWatch alarms created for CPU, storage, connections
# - Enable Performance Insights for query analysis (additional cost)
# - Review CloudWatch Logs for PostgreSQL logs
# - Set up SNS topic for alarm notifications
