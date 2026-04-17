# =============================================================================
# Terraform Variables for AI Job Agent Infrastructure
# =============================================================================
#
# This file defines all input variables for the infrastructure.
# Values can be set via:
# - terraform.tfvars file (recommended for non-sensitive values)
# - Environment variables (TF_VAR_name)
# - Command line flags (-var="name=value")
# - AWS Systems Manager Parameter Store / Secrets Manager (for sensitive values)
#
# =============================================================================

# -----------------------------------------------------------------------------
# AWS CONFIGURATION
# -----------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "eu-west-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]{1}$", var.aws_region))
    error_message = "AWS region must be in format: us-east-1, eu-west-1, etc."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "ai-job-agent"
}

# -----------------------------------------------------------------------------
# RDS DATABASE CONFIGURATION
# -----------------------------------------------------------------------------

variable "db_instance_class" {
  description = "RDS instance type (e.g., db.t4g.micro for ARM-based, cost-optimized)"
  type        = string
  default     = "db.t4g.micro"

  validation {
    condition     = can(regex("^db\\.", var.db_instance_class))
    error_message = "Instance class must start with 'db.' (e.g., db.t4g.micro)."
  }
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB for RDS instance"
  type        = number
  default     = 20

  validation {
    condition     = var.db_allocated_storage >= 20 && var.db_allocated_storage <= 100
    error_message = "Allocated storage must be between 20 and 100 GB."
  }
}

variable "db_storage_type" {
  description = "Storage type for RDS (gp2, gp3, io1)"
  type        = string
  default     = "gp2"

  validation {
    condition     = contains(["gp2", "gp3", "io1"], var.db_storage_type)
    error_message = "Storage type must be one of: gp2, gp3, io1."
  }
}

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "17.6"
}

variable "db_name" {
  description = "Name of the database to create"
  type        = string
  default     = "jobagent_db"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]*$", var.db_name))
    error_message = "Database name must start with a letter and contain only lowercase letters, numbers, and underscores."
  }
}

variable "db_username" {
  description = "Master username for database"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "db_password" {
  description = "Master password for database (should use AWS Secrets Manager in production)"
  type        = string
  sensitive   = true

  # Note: Do NOT set a default for passwords!
  # Use AWS Secrets Manager or provide via terraform.tfvars (gitignored)
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment for high availability (doubles cost)"
  type        = bool
  default     = false
}

variable "db_publicly_accessible" {
  description = "Allow public access to database (set to false for production)"
  type        = bool
  default     = true # Only for development; should be false in production
}

variable "db_backup_retention_period" {
  description = "Number of days to retain automated backups (0-35)"
  type        = number
  default     = 7

  validation {
    condition     = var.db_backup_retention_period >= 0 && var.db_backup_retention_period <= 35
    error_message = "Backup retention period must be between 0 and 35 days."
  }
}

variable "db_backup_window" {
  description = "Preferred backup window (UTC)"
  type        = string
  default     = "03:00-04:00" # 3-4 AM UTC
}

variable "db_maintenance_window" {
  description = "Preferred maintenance window (UTC)"
  type        = string
  default     = "mon:04:00-mon:05:00" # Monday 4-5 AM UTC
}

variable "db_deletion_protection" {
  description = "Enable deletion protection (recommended for production)"
  type        = bool
  default     = false # false for dev, true for prod
}

variable "db_skip_final_snapshot" {
  description = "Skip final snapshot when destroying (set to false for production)"
  type        = bool
  default     = true # true for dev, false for prod
}

variable "db_storage_encrypted" {
  description = "Enable storage encryption at rest"
  type        = bool
  default     = true
}

variable "db_performance_insights_enabled" {
  description = "Enable Performance Insights"
  type        = bool
  default     = false # false for cost savings in dev
}

# -----------------------------------------------------------------------------
# NETWORKING CONFIGURATION
# -----------------------------------------------------------------------------

variable "vpc_id" {
  description = "VPC ID where RDS will be deployed (leave empty to use default VPC)"
  type        = string
  default     = "" # Will use default VPC if not specified
}

variable "db_subnet_ids" {
  description = "List of subnet IDs for RDS subnet group"
  type        = list(string)
  default     = [] # Will use default subnets if not specified
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to connect to RDS (use specific IPs in production)"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Open to all (dev only!)

  # Production should use specific IPs/ranges:
  # default = ["10.0.0.0/16", "YOUR_OFFICE_IP/32"]
}

# -----------------------------------------------------------------------------
# MONITORING & ALERTING
# -----------------------------------------------------------------------------

variable "enable_cloudwatch_alarms" {
  description = "Create CloudWatch alarms for RDS monitoring"
  type        = bool
  default     = true
}

variable "alarm_sns_topic_arn" {
  description = "SNS topic ARN for alarm notifications (optional)"
  type        = string
  default     = ""
}

variable "cpu_utilization_threshold" {
  description = "CPU utilization percentage threshold for alarms"
  type        = number
  default     = 80
}

variable "free_storage_threshold_mb" {
  description = "Free storage space threshold in MB for alarms"
  type        = number
  default     = 2000 # 2 GB
}

# -----------------------------------------------------------------------------
# ECS CONFIGURATION
# -----------------------------------------------------------------------------

variable "ecs_task_cpu" {
  description = "CPU units for ECS task (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 256 # 0.25 vCPU
}

variable "ecs_task_memory" {
  description = "Memory (MB) for ECS task"
  type        = number
  default     = 512 # 512 MB
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights for ECS"
  type        = bool
  default     = false # Enable in production
}

# -----------------------------------------------------------------------------
# TAGS
# -----------------------------------------------------------------------------

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "AI Job Agent"
    ManagedBy   = "Terraform"
    Environment = "dev"
  }
}
