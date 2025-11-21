#!/bin/bash
set -e

# Check application health
echo "Checking application health..."

APP_URL="${APP_URL:-http://localhost:8000}"
HEALTH_ENDPOINT="${APP_URL}/health"

response=$(curl -s -o /dev/null -w "%{http_code}" ${HEALTH_ENDPOINT})

if [ $response -eq 200 ]; then
    echo "✓ Application is healthy"
    exit 0
else
    echo "✗ Application is unhealthy (HTTP ${response})"
    exit 1
fi
