# =============================================================================
# Terraform Backend Configuration
# =============================================================================
#
# This file configures where Terraform stores its state file.
#
# IMPORTANT: State files contain sensitive information (passwords, connection
# strings, etc.). NEVER commit state files to git!
#
# REQUIREMENTS (Phase 0 - CONTRIBUTING.md):
# - S3 bucket for Terraform state storage
# - DynamoDB table for state locking
#
# =============================================================================

# -----------------------------------------------------------------------------
# OPTION 1: Local Backend (Current - Development Only)
# -----------------------------------------------------------------------------

# No configuration needed - Terraform uses local backend by default
# State will be stored in: terraform.tfstate (gitignored)

# Pros:
# - Simple, no AWS setup required
# - Works immediately
# - Good for local development and testing

# Cons:
# - State file only on your machine
# - No collaboration with team
# - Risk of losing state if file is deleted
# - No state locking (race conditions possible)

# -----------------------------------------------------------------------------
# OPTION 2: S3 Backend (Recommended for Production)
# -----------------------------------------------------------------------------

# S3 backend enabled - bucket and DynamoDB table created

terraform {
  backend "s3" {
    # S3 bucket to store state file
    bucket = "ai-job-agent-terraform-state"

    # Path within bucket (allows multiple environments)
    key    = "dev/terraform.tfstate"

    # AWS region where bucket is located
    region = "eu-west-1"

    # Enable encryption at rest
    encrypt = true

    # DynamoDB table for state locking (prevents concurrent modifications)
    dynamodb_table = "ai-job-agent-terraform-locks"
  }
}

# -----------------------------------------------------------------------------
# S3 BACKEND SETUP INSTRUCTIONS (Phase 0 Requirements)
# -----------------------------------------------------------------------------

# Step 1: Create S3 bucket for state
# aws s3api create-bucket \
#   --bucket ai-job-agent-terraform-state \
#   --region eu-west-1 \
#   --create-bucket-configuration LocationConstraint=eu-west-1

# Step 2: Enable versioning
# aws s3api put-bucket-versioning \
#   --bucket ai-job-agent-terraform-state \
#   --versioning-configuration Status=Enabled

# Step 3: Enable server-side encryption
# aws s3api put-bucket-encryption \
#   --bucket ai-job-agent-terraform-state \
#   --server-side-encryption-configuration '{
#     "Rules": [{
#       "ApplyServerSideEncryptionByDefault": {
#         "SSEAlgorithm": "AES256"
#       }
#     }]
#   }'

# Step 4: Block public access
# aws s3api put-public-access-block \
#   --bucket ai-job-agent-terraform-state \
#   --public-access-block-configuration \
#     BlockPublicAcls=true,\
#     IgnorePublicAcls=true,\
#     BlockPublicPolicy=true,\
#     RestrictPublicBuckets=true

# Step 5: Create DynamoDB table for locking
# aws dynamodb create-table \
#   --table-name ai-job-agent-terraform-locks \
#   --attribute-definitions AttributeName=LockID,AttributeType=S \
#   --key-schema AttributeName=LockID,KeyType=HASH \
#   --billing-mode PAY_PER_REQUEST \
#   --region eu-west-1

# Step 6: Uncomment the backend configuration above
# Step 7: Run: terraform init -migrate-state
# Step 8: Verify and delete local terraform.tfstate

# -----------------------------------------------------------------------------
# CURRENT STATUS
# -----------------------------------------------------------------------------

# Backend: S3 (ACTIVE)
# S3 Bucket: ai-job-agent-terraform-state (eu-west-1)
# DynamoDB Table: ai-job-agent-terraform-locks (eu-west-1)
# State file: s3://ai-job-agent-terraform-state/dev/terraform.tfstate
# Status: ✅ Migrated to remote backend (Session 6, 2025-11-29)
