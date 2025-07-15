# Makefile for air pollution prediction project
# Run 'make help' to see available commands

.PHONY: help install install-dev test lint format type-check security clean pre-commit setup-hooks run-hooks

# Default target
help:
	@echo "Available commands:"
	@echo "  setup-dev     - Set up development environment with all tools"
	@echo "  install       - Install production dependencies"
	@echo "  install-dev   - Install development dependencies"
	@echo "  setup-hooks   - Install pre-commit hooks"
	@echo "  run-hooks     - Run pre-commit hooks on all files"
	@echo "  test          - Run all tests"
	@echo "  test-fast     - Run tests without slow tests"
	@echo "  test-cov      - Run tests with coverage report"
	@echo "  lint          - Run all linting checks"
	@echo "  format        - Format code with black and isort"
	@echo "  type-check    - Run type checking with mypy"
	@echo "  security      - Run security checks with bandit"
	@echo "  clean         - Clean up cache files"
	@echo "  prefect-start - Start Prefect server"
	@echo "  api-start     - Start FastAPI server"

# Development environment setup
setup-dev: install-dev setup-hooks
	@echo "Development environment ready!"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pip install -r requirements.txt

# Pre-commit hooks
setup-hooks:
	pre-commit install
	pre-commit install --hook-type commit-msg

run-hooks:
	pre-commit run --all-files

# Testing
test:
	python -m pytest tests/ -v

test-fast:
	python -m pytest tests/ -v -m "not slow"

test-cov:
	python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-flows:
	python -m pytest tests/test_flows.py -v

test-api:
	python -m pytest tests/test_api.py -v

test-predictor:
	python -m pytest tests/test_predictor.py -v

# Code quality
lint: format type-check security
	flake8 src/ tests/ flows/
	@echo "All linting checks passed!"

format:
	black src/ tests/ flows/ scripts/
	isort src/ tests/ flows/ scripts/

type-check:
	mypy src/

security:
	bandit -r src/ -f json -o bandit-report.json
	@echo "Security check completed. Check bandit-report.json for details."

# Cleaning
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -f .coverage
	rm -rf htmlcov/
	rm -f bandit-report.json

# Services
prefect-start:
	prefect server start

api-start:
	python -m src.api.app

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# MLflow
mlflow-ui:
	mlflow ui --backend-store-uri sqlite:///mlflow.db

# Utility commands
requirements-update:
	pip-compile requirements.in
	pip-compile requirements-dev.in

sort-requirements:
	sort-requirements requirements.txt
	sort-requirements requirements-dev.txt

check-deps:
	pip check

# CI/CD simulation
ci-check: install-dev run-hooks test-cov lint
	@echo "CI checks completed successfully!"
