# =============================================================================
# Amazon ECR (Elastic Container Registry) for Docker Images
# =============================================================================
#
# This file defines the ECR repository where Docker images for the application
# will be stored and pulled by ECS tasks.
#
# =============================================================================

resource "aws_ecr_repository" "app" {
  name                 = "${var.project_name}-${var.environment}"
  image_tag_mutability = "MUTABLE" # Allow overwriting tags (IMMUTABLE for production)

  # Scan images for vulnerabilities
  image_scanning_configuration {
    scan_on_push = true
  }

  # Enable encryption at rest
  encryption_configuration {
    encryption_type = "AES256" # or "KMS" for customer-managed keys
  }

  tags = merge(
    var.tags,
    {
      Name      = "${var.project_name}-${var.environment}-ecr"
      Component = "container-registry"
    }
  )
}

# Lifecycle policy to keep only recent images (cost optimization)
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "latest"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Delete untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
