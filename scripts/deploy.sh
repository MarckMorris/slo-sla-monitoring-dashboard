#!/bin/bash
set -e

ENV="${1:-production}"

echo "Deploying to ${ENV}..."

# Run tests
make test

# Build Docker image
docker build -t app:${ENV} .

# Apply Terraform changes
cd terraform
terraform workspace select ${ENV} || terraform workspace new ${ENV}
terraform apply -auto-approve

echo "Deployment to ${ENV} completed successfully"
