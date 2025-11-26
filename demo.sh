#!/bin/bash
echo "Starting SLO/SLA Monitoring Dashboard..."
docker-compose up -d
sleep 10
python src/slo_monitor.py
