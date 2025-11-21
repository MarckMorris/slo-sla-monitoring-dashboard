#!/bin/bash
set -e

echo "Starting application..."

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Start services
docker-compose up -d

echo "Application started successfully"
echo "Access Grafana at http://localhost:3000"
echo "Access Prometheus at http://localhost:9090"
echo "API available at http://localhost:8000"
