# =============================================================================
# RDS PostgreSQL Database Infrastructure
# =============================================================================
#
# This file defines the RDS instance, security groups, subnet groups, and
# CloudWatch monitoring for the AI Job Agent application.
#
# Resources created:
# - RDS PostgreSQL instance
# - Security group for RDS access
# - DB subnet group
# - CloudWatch alarms for monitoring
#
# =============================================================================

# -----------------------------------------------------------------------------
# DATA SOURCES
# -----------------------------------------------------------------------------

# Get default VPC if vpc_id not specified
data "aws_vpc" "default" {
  count   = var.vpc_id == "" ? 1 : 0
  default = true
}

# Get all subnets in the VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [var.vpc_id != "" ? var.vpc_id : data.aws_vpc.default[0].id]
  }
}

# -----------------------------------------------------------------------------
# SECURITY GROUP
# -----------------------------------------------------------------------------

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-db-sg" # Matches existing: ai-job-agent-db-sg
  description = "Created by RDS management console" # Matches existing description
  vpc_id      = var.vpc_id != "" ? var.vpc_id : data.aws_vpc.default[0].id

  # Inbound rule: Allow PostgreSQL connections from specified CIDR blocks
  ingress {
    description = "" # Match existing (empty description)
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Outbound rule: Allow all outbound traffic
  egress {
    description = "" # Match existing (empty description)
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-rds-sg"
      Description = "RDS Security Group"
    }
  )
}

# -----------------------------------------------------------------------------
# DB SUBNET GROUP
# -----------------------------------------------------------------------------

resource "aws_db_subnet_group" "main" {
  name       = "default-vpc-02248d51e4b12d54e" # Matches existing default subnet group
  subnet_ids = length(var.db_subnet_ids) > 0 ? var.db_subnet_ids : data.aws_subnets.default.ids

  description = "DB subnet group for ${var.project_name} ${var.environment}"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-db-subnet-group"
    }
  )
}

# -----------------------------------------------------------------------------
# RDS INSTANCE
# -----------------------------------------------------------------------------

resource "aws_db_instance" "main" {
  # Instance identification
  identifier = "${var.project_name}-db" # Matches existing: ai-job-agent-db

  # Engine configuration
  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  # Storage configuration
  allocated_storage = var.db_allocated_storage
  storage_type      = var.db_storage_type
  storage_encrypted = var.db_storage_encrypted

  # Database configuration
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = var.db_publicly_accessible
  multi_az               = var.db_multi_az

  # Backup configuration
  backup_retention_period = var.db_backup_retention_period
  backup_window           = var.db_backup_window
  maintenance_window      = var.db_maintenance_window

  # Deletion protection
  deletion_protection       = var.db_deletion_protection
  skip_final_snapshot       = var.db_skip_final_snapshot
  final_snapshot_identifier = var.db_skip_final_snapshot ? null : "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  performance_insights_enabled    = var.db_performance_insights_enabled

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  # Parameter group (using default for now)
  # Custom parameter group can be created if needed
  # parameter_group_name = aws_db_parameter_group.main.name

  tags = merge(
    var.tags,
    {
      Name      = "${var.project_name}-${var.environment}-db"
      Component = "database"
      ManagedBy = "Terraform"
    }
  )

  # Prevent accidental replacement
  lifecycle {
    prevent_destroy = false # Set to true in production
  }
}

# -----------------------------------------------------------------------------
# CLOUDWATCH ALARMS
# -----------------------------------------------------------------------------

# High CPU Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-rds-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = var.cpu_utilization_threshold
  alarm_description   = "This metric monitors RDS CPU utilization"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-rds-high-cpu-alarm"
    }
  )
}

# Low Free Storage Space Alarm
resource "aws_cloudwatch_metric_alarm" "low_storage" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-rds-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = var.free_storage_threshold_mb * 1024 * 1024 # Convert MB to bytes
  alarm_description   = "This metric monitors RDS free storage space"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-rds-low-storage-alarm"
    }
  )
}

# High Database Connections Alarm
resource "aws_cloudwatch_metric_alarm" "high_connections" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-rds-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 80 # Adjust based on instance class
  alarm_description   = "This metric monitors number of database connections"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-rds-high-connections-alarm"
    }
  )
}

# -----------------------------------------------------------------------------
# CLOUDWATCH DASHBOARD
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_dashboard" "rds" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  dashboard_name = "${var.project_name}-${var.environment}-rds-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # CPU Utilization
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", { stat = "Average", label = "CPU Avg" }],
            ["...", { stat = "Maximum", label = "CPU Max" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "CPU Utilization (%)"
          period  = 300
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
          annotations = {
            horizontal = [
              {
                value = var.cpu_utilization_threshold
                label = "Alarm Threshold"
                fill  = "above"
                color = "#d13212"
              }
            ]
          }
        }
        width  = 12
        height = 6
        x      = 0
        y      = 0
      },
      # Database Connections
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "DatabaseConnections", { stat = "Average", label = "Connections Avg" }],
            ["...", { stat = "Maximum", label = "Connections Max" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Database Connections"
          period  = 300
          annotations = {
            horizontal = [
              {
                value = 80
                label = "Alarm Threshold"
                fill  = "above"
                color = "#ff7f0e"
              }
            ]
          }
        }
        width  = 12
        height = 6
        x      = 12
        y      = 0
      },
      # Free Storage Space
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "FreeStorageSpace", { stat = "Average" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Free Storage Space (Bytes)"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
          annotations = {
            horizontal = [
              {
                value = var.free_storage_threshold_mb * 1024 * 1024
                label = "Alarm Threshold"
                fill  = "below"
                color = "#d13212"
              }
            ]
          }
        }
        width  = 12
        height = 6
        x      = 0
        y      = 6
      },
      # Read/Write IOPS
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "ReadIOPS", { stat = "Average", label = "Read IOPS" }],
            [".", "WriteIOPS", { stat = "Average", label = "Write IOPS" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Read/Write IOPS"
          period  = 300
        }
        width  = 12
        height = 6
        x      = 12
        y      = 6
      },
      # Read/Write Latency
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "ReadLatency", { stat = "Average", label = "Read Latency" }],
            [".", "WriteLatency", { stat = "Average", label = "Write Latency" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Read/Write Latency (seconds)"
          period  = 300
        }
        width  = 12
        height = 6
        x      = 0
        y      = 12
      },
      # Network Throughput
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "NetworkReceiveThroughput", { stat = "Average", label = "Network In" }],
            [".", "NetworkTransmitThroughput", { stat = "Average", label = "Network Out" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Network Throughput (Bytes/sec)"
          period  = 300
        }
        width  = 12
        height = 6
        x      = 12
        y      = 12
      },
      # Freeable Memory
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "FreeableMemory", { stat = "Average" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Freeable Memory (Bytes)"
          period  = 300
        }
        width  = 12
        height = 6
        x      = 0
        y      = 18
      },
      # Swap Usage
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "SwapUsage", { stat = "Average" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Swap Usage (Bytes)"
          period  = 300
        }
        width  = 12
        height = 6
        x      = 12
        y      = 18
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# OPTIONAL: CUSTOM PARAMETER GROUP
# -----------------------------------------------------------------------------

# Uncomment if you need custom PostgreSQL parameters

/*
resource "aws_db_parameter_group" "main" {
  name   = "${var.project_name}-${var.environment}-pg-params"
  family = "postgres17"

  description = "Custom parameter group for ${var.project_name}"

  # Example parameters (uncomment and adjust as needed)
  # parameter {
  #   name  = "max_connections"
  #   value = "100"
  # }

  # parameter {
  #   name  = "shared_buffers"
  #   value = "{DBInstanceClassMemory/32768}"  # 1/4 of instance memory
  # }

  # parameter {
  #   name  = "log_statement"
  #   value = "all"  # Log all SQL statements (for debugging)
  # }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-pg-params"
    }
  )
}
*/
