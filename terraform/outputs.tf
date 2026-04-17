# =============================================================================
# Terraform Outputs for AI Job Agent Infrastructure
# =============================================================================
#
# These outputs expose important information after terraform apply.
# Use them to:
# - Get connection strings for the database
# - Reference resource IDs in other configurations
# - Display important information to operators
#
# Access outputs with: terraform output <output_name>
# Example: terraform output db_endpoint
#
# =============================================================================

# -----------------------------------------------------------------------------
# RDS DATABASE OUTPUTS
# -----------------------------------------------------------------------------

output "db_instance_id" {
  description = "RDS instance identifier"
  value       = aws_db_instance.main.id
}

output "db_instance_arn" {
  description = "ARN of the RDS instance"
  value       = aws_db_instance.main.arn
}

output "db_endpoint" {
  description = "RDS instance endpoint (host:port)"
  value       = aws_db_instance.main.endpoint
}

output "db_address" {
  description = "RDS instance hostname"
  value       = aws_db_instance.main.address
}

output "db_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "db_name" {
  description = "Name of the created database"
  value       = aws_db_instance.main.db_name
}

output "db_username" {
  description = "Master username for the database"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_connection_string" {
  description = "PostgreSQL connection string (without password)"
  value       = "postgresql://${aws_db_instance.main.username}:****@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

output "db_resource_id" {
  description = "RDS resource ID (for CloudWatch metrics)"
  value       = aws_db_instance.main.resource_id
}

# -----------------------------------------------------------------------------
# SECURITY GROUP OUTPUTS
# -----------------------------------------------------------------------------

output "db_security_group_id" {
  description = "ID of the RDS security group"
  value       = aws_security_group.rds.id
}

output "db_security_group_name" {
  description = "Name of the RDS security group"
  value       = aws_security_group.rds.name
}

# -----------------------------------------------------------------------------
# SUBNET GROUP OUTPUT
# -----------------------------------------------------------------------------

output "db_subnet_group_name" {
  description = "Name of the DB subnet group"
  value       = aws_db_subnet_group.main.name
}

# -----------------------------------------------------------------------------
# CLOUDWATCH ALARMS OUTPUTS
# -----------------------------------------------------------------------------

output "high_cpu_alarm_arn" {
  description = "ARN of the high CPU utilization alarm"
  value       = var.enable_cloudwatch_alarms ? aws_cloudwatch_metric_alarm.high_cpu[0].arn : null
}

output "low_storage_alarm_arn" {
  description = "ARN of the low free storage alarm"
  value       = var.enable_cloudwatch_alarms ? aws_cloudwatch_metric_alarm.low_storage[0].arn : null
}

output "high_connections_alarm_arn" {
  description = "ARN of the high database connections alarm"
  value       = var.enable_cloudwatch_alarms ? aws_cloudwatch_metric_alarm.high_connections[0].arn : null
}

output "cloudwatch_dashboard_url" {
  description = "URL to the CloudWatch dashboard"
  value       = var.enable_cloudwatch_alarms ? "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.rds[0].dashboard_name}" : null
}

# -----------------------------------------------------------------------------
# APPLICATION CONFIGURATION OUTPUTS
# -----------------------------------------------------------------------------

output "database_url_template" {
  description = "DATABASE_URL template for application .env file"
  value       = "postgresql://${aws_db_instance.main.username}:YOUR_PASSWORD_HERE@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

output "environment_variables" {
  description = "Environment variables to set in application"
  value = {
    DATABASE_HOST = aws_db_instance.main.address
    DATABASE_PORT = tostring(aws_db_instance.main.port)
    DATABASE_NAME = aws_db_instance.main.db_name
    DATABASE_USER = aws_db_instance.main.username
  }
  sensitive   = true
}

# -----------------------------------------------------------------------------
# INFORMATIONAL OUTPUTS
# -----------------------------------------------------------------------------

output "infrastructure_summary" {
  description = "Summary of deployed infrastructure"
  value = {
    region              = var.aws_region
    environment         = var.environment
    instance_class      = aws_db_instance.main.instance_class
    engine_version      = aws_db_instance.main.engine_version
    storage_size_gb     = aws_db_instance.main.allocated_storage
    multi_az            = aws_db_instance.main.multi_az
    publicly_accessible = aws_db_instance.main.publicly_accessible
    backup_retention    = aws_db_instance.main.backup_retention_period
    encryption_enabled  = aws_db_instance.main.storage_encrypted
  }
}

# -----------------------------------------------------------------------------
# ECR OUTPUTS
# -----------------------------------------------------------------------------

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = try(aws_ecr_repository.app.repository_url, null)
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = try(aws_ecr_repository.app.name, null)
}

# -----------------------------------------------------------------------------
# ECS OUTPUTS
# -----------------------------------------------------------------------------

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = try(aws_ecs_cluster.main.name, null)
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = try(aws_ecs_service.app.name, null)
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = try(aws_lb.main.dns_name, null)
}

output "application_url" {
  description = "URL to access the application"
  value       = try("http://${aws_lb.main.dns_name}", null)
}

# -----------------------------------------------------------------------------
# USAGE INSTRUCTIONS
# -----------------------------------------------------------------------------

output "connection_instructions" {
  description = "How to connect to the database"
  value       = <<-EOT

    ========================================================================
    DATABASE CONNECTION INFORMATION
    ========================================================================

    Endpoint: ${aws_db_instance.main.endpoint}
    Database: ${aws_db_instance.main.db_name}
    Username: ${aws_db_instance.main.username}
    Password: (stored in AWS Secrets Manager or .env file)

    CONNECTION STRING (for .env file):
    DATABASE_URL=postgresql://${aws_db_instance.main.username}:YOUR_PASSWORD@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}

    TEST CONNECTION:
    docker-compose exec api python scripts/test_db_connection.py

    RUN MIGRATIONS:
    docker-compose exec api alembic upgrade head

    ========================================================================
  EOT
  sensitive   = true
}

output "deployment_instructions" {
  description = "How to deploy the application"
  value       = try(<<-EOT

    ========================================================================
    DEPLOYMENT INFORMATION
    ========================================================================

    ECR Repository: ${aws_ecr_repository.app.repository_url}
    ECS Cluster: ${aws_ecs_cluster.main.name}
    Application URL: http://${aws_lb.main.dns_name}

    DEPLOY NEW VERSION:
    1. Build Docker image:
       docker build -t ${aws_ecr_repository.app.repository_url}:latest .

    2. Login to ECR:
       aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.app.repository_url}

    3. Push image:
       docker push ${aws_ecr_repository.app.repository_url}:latest

    4. Update ECS service:
       aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.app.name} --force-new-deployment

    ========================================================================
  EOT
  , null)
}
