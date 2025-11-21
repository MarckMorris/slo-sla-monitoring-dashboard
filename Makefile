# Makefile for project automation

.PHONY: help install test lint format clean docker-build docker-run deploy

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make docker-build - Build Docker image"
	@echo "  make deploy       - Deploy application"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v --cov=src --cov-report=html

lint:
	flake8 src/ tests/ --max-line-length=100
	mypy src/ --ignore-missing-imports

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov

docker-build:
	docker build -t $(PROJECT_NAME):latest .

docker-run:
	docker-compose up -d

deploy:
	./scripts/deploy.sh

terraform-init:
	cd terraform && terraform init

terraform-plan:
	cd terraform && terraform plan

terraform-apply:
	cd terraform && terraform apply -auto-approve
