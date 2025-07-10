# sbkube Makefile

.PHONY: help install test test-unit test-integration test-performance test-coverage lint format clean

# Default target
help:
	@echo "sbkube Development Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install          Install sbkube in development mode"
	@echo "  make install-test     Install with test dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test            Run all tests"
	@echo "  make test-unit       Run unit tests (tests/unit/)"
	@echo "  make test-integration Run integration tests (tests/integration/)"
	@echo "  make test-performance Run performance tests (tests/performance/)"
	@echo "  make test-e2e        Run end-to-end tests (tests/e2e/)"
	@echo "  make test-legacy     Run legacy tests (tests/legacy/)"
	@echo "  make test-coverage   Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint            Run linters (ruff, mypy)"
	@echo "  make format          Format code with black and isort"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean           Clean build artifacts and caches"

# Installation
install:
	uv pip install -e .

install-test:
	uv pip install -e . --group test

# Testing
test:
	pytest -v

test-unit:
	pytest -v tests/unit/

test-integration:
	pytest -v tests/integration/

test-performance:
	pytest -v tests/performance/ --benchmark-only

test-e2e:
	pytest -v tests/e2e/

test-legacy:
	pytest -v tests/legacy/

test-coverage:
	pytest -v --cov=sbkube --cov-report=html --cov-report=term-missing

test-watch:
	ptw -- -v

# Specific test categories (by markers)
test-k8s:
	pytest -v -m requires_k8s

test-helm:
	pytest -v -m requires_helm

test-fast:
	pytest -v -m "not slow"

# Specific test directories
test-commands:
	pytest -v tests/unit/commands/

test-models:
	pytest -v tests/unit/models/

test-state:
	pytest -v tests/unit/state/

test-utils:
	pytest -v tests/unit/utils/

# Parallel testing
test-parallel:
	pytest -v -n auto

# Code Quality
lint:
	@echo "Running ruff..."
	ruff check sbkube tests
	@echo "Running mypy..."
	mypy sbkube --ignore-missing-imports

format:
	@echo "Running black..."
	black sbkube tests
	@echo "Running isort..."
	isort sbkube tests

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Build
build:
	uv build

# Clean
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Development database
clean-db:
	@echo "Cleaning development database..."
	rm -f ~/.sbkube/deployments.db

# Docker cleanup (for integration tests)
clean-docker:
	@echo "Cleaning test containers..."
	docker ps -a | grep test- | awk '{print $$1}' | xargs -r docker rm -f
	docker ps -a | grep k3s | awk '{print $$1}' | xargs -r docker rm -f

# Full clean
clean-all: clean clean-db clean-docker

# CI simulation
ci:
	@echo "Running CI checks..."
	make lint
	make test-coverage
	@echo "CI checks passed!"

# Performance report
perf-report:
	pytest -v -m performance --benchmark-only --benchmark-json=benchmark.json
	@echo "Performance report saved to benchmark.json"

# Generate test report
test-report:
	pytest -v --html=report.html --self-contained-html
	@echo "Test report saved to report.html"

# Update dependencies
update-deps:
	uv pip compile pyproject.toml -o requirements.txt
	uv pip sync requirements.txt

# Version management
version:
	@grep version pyproject.toml | head -1 | cut -d'"' -f2

bump-patch:
	@current=$$(make version); \
	new=$$(echo $$current | awk -F. '{print $$1"."$$2"."$$3+1}'); \
	sed -i "s/version = \"$$current\"/version = \"$$new\"/" pyproject.toml; \
	echo "Version bumped from $$current to $$new"

bump-minor:
	@current=$$(make version); \
	new=$$(echo $$current | awk -F. '{print $$1"."$$2+1".0"}'); \
	sed -i "s/version = \"$$current\"/version = \"$$new\"/" pyproject.toml; \
	echo "Version bumped from $$current to $$new"

# Documentation
docs:
	@echo "Generating documentation..."
	pdoc --html --output-dir docs sbkube

# Release
release: clean test build
	@echo "Ready for release!"
	@echo "Don't forget to:"
	@echo "  1. Update CHANGELOG.md"
	@echo "  2. Commit all changes"
	@echo "  3. Tag the release: git tag v$$(make version)"
	@echo "  4. Push tags: git push --tags"
	@echo "  5. Upload to PyPI: twine upload dist/*"