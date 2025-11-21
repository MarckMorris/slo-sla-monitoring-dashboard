terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "terraform-state-bucket"
    key    = "project/terraform.tfstate"
    region = "us-west-2"
  }
}

# Variables
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "region" {
  description = "Cloud region"
  type        = string
  default     = "us-west-2"
}

# Database instance
resource "aws_db_instance" "main" {
  identifier           = "main-db-${var.environment}"
  engine              = "postgres"
  engine_version      = "14.9"
  instance_class      = "db.t3.large"
  allocated_storage   = 100
  storage_encrypted   = true
  
  db_name  = "appdb"
  username = "admin"
  password = random_password.db_password.result
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  multi_az               = true
  publicly_accessible    = false
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Random password generation
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store password in Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name = "db-password-${var.environment}"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

# Outputs
output "db_endpoint" {
  description = "Database endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "db_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}
