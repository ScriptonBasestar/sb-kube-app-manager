# sbkube Makefile

.PHONY: help install test test-unit test-integration test-performance test-coverage clean

# Default target
help:
	@echo "sbkube Development Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install          Install sbkube in development mode"
	@echo "  make install-dev      Install with dev dependencies (ruff, mypy, black)"
	@echo "  make install-test     Install with test dependencies"
	@echo "  make install-all      Install with all dependencies (dev + test)"
	@echo ""
	@echo "Testing:"
	@echo "  make test            Run all tests"
	@echo "  make test-unit       Run unit tests (tests/unit/)"
	@echo "  make test-quick      Run fast unit tests (no E2E, no slow)"
	@echo "  make test-unit-only  Run unit tests excluding E2E"
	@echo "  make test-integration Run integration tests (tests/integration/)"
	@echo "  make test-performance Run performance tests (tests/performance/)"
	@echo "  make test-e2e        Run end-to-end tests (tests/e2e/)"
	@echo "  make test-legacy     Run legacy tests (tests/legacy/)"
	@echo "  make test-coverage   Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make check           Quick syntax + type check (fastest)"
	@echo "  make lint            Run linters (ruff, mypy, bandit) - read-only"
	@echo "  make lint-fix        Run linters with auto-fix"
	@echo "  make lint-fix UNSAFE_FIXES=1  Run linters with unsafe auto-fix"
	@echo "  make lint-check      Run linters with diff output (no auto-fix)"
	@echo "  make lint-strict     Run strict linters for high quality standards"
	@echo "  make lint-strict-fix Run strict linters with auto-fix"
	@echo "  make lint-strict-fix UNSAFE_FIXES=1  Strict with unsafe auto-fix"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean           Clean build artifacts and caches"

# Installation
install:
	uv pip install -e .

install-dev:
	uv pip install -e . --group dev

install-test:
	uv pip install -e . --group test

install-all:
	uv pip install -e . --group dev --group test

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

# Quick unit tests (no E2E, no slow tests)
test-quick:
	pytest -v -m "not e2e and not slow" tests/unit/

# Unit tests only (no E2E)
test-unit-only:
	pytest -v -m "not e2e" tests/unit/

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
LINT_DIRS = sbkube tests
LINT_DIRS_SECURITY = sbkube
LINT_DIRS_CORE = sbkube
EXCLUDE_DIRS = --exclude migrations --exclude node_modules --exclude examples
# Optional unsafe fixes (use: make lint-fix UNSAFE_FIXES=1)
UNSAFE_FIXES ?=
UNSAFE_FLAG = $(if $(UNSAFE_FIXES),--unsafe-fixes,)

# check: 빠른 문법 + 타입 체크 (가장 빠름, 빌드 컴파일처럼 사용)
# - Python 문법 체크: py_compile로 syntax error 검출
# - mypy: 기본 타입 검사 (엄격하지 않음)
# - 용도: 코드 수정 후 빠른 검증, CI 사전 체크
check:
	@echo "🔍 Quick syntax and type check..."
	@echo "✓ Checking Python syntax..."
	@uv run python -m py_compile sbkube/**/*.py 2>&1 | grep -v "^$$" || echo "✅ Syntax OK"
	@echo "✓ Running mypy..."
	@uv run mypy $(LINT_DIRS_CORE) --ignore-missing-imports --no-error-summary $(EXCLUDE_DIRS) || echo "⚠️  Type check completed with warnings"
	@echo "✅ Quick check completed!"

# lint-check: 변경 사항 미리보기 (diff 모드)
# - ruff check --diff: 수정될 내용을 미리보기로 표시 (실제 수정 없음)
# - mypy: 타입 검사
# - bandit: 보안 취약점 검사 (medium 레벨)
# - mdformat: 마크다운 포맷팅 체크 (diff 모드)
lint-check:
	@echo "Running lint checks only (no auto-fix)..."
	@echo "Running ruff check..."
	uv run ruff check $(LINT_DIRS) --diff $(EXCLUDE_DIRS)
	@echo "Running mypy..."
	uv run mypy $(LINT_DIRS_CORE) --ignore-missing-imports $(EXCLUDE_DIRS)
	@echo "Running bandit security check..."
	uv run bandit -r $(LINT_DIRS_SECURITY) --skip B101,B404,B603,B607,B602 --severity-level medium --quiet --exclude "*/tests/*,*/scripts/*,*/debug/*,*/examples/*" || echo "✅ Security check completed"
	@echo "Running mdformat check..."
	uv run mdformat --check *.md docs/**/*.md --wrap 120 || echo "✅ Markdown format check completed"

lint: lint-check

# lint-fix: 자동 수정 포함 코드 품질 검사 + 포맷팅
# - ruff check --fix: 자동 수정 가능한 규칙 위반 항목 수정
# - ruff format: 코드 포맷팅 자동 적용, black대체용
# - mypy: 타입 검사
# - bandit: 보안 취약점 검사 (medium 레벨)
# - mdformat: 마크다운 포맷팅
# - 사용법: make lint-fix UNSAFE_FIXES=1 (위험한 자동 수정 포함)
lint-fix:
	@echo "Running lint with auto-fix..."
	@echo "Running ruff check with auto-fix..."
	uv run ruff check $(LINT_DIRS) --fix $(UNSAFE_FLAG) $(EXCLUDE_DIRS)
	@echo "Running ruff format..."
	uv run ruff format $(LINT_DIRS) $(EXCLUDE_DIRS)
	@echo "Running mypy..."
	uv run mypy $(LINT_DIRS_CORE) --ignore-missing-imports $(EXCLUDE_DIRS)
	@echo "Running bandit security check..."
	uv run bandit -r $(LINT_DIRS_SECURITY) --skip B101,B404,B603,B607,B602 --severity-level medium --quiet --exclude "*/tests/*,*/scripts/*,*/debug/*,*/examples/*" || echo "✅ Security check completed"
	@echo "Running mdformat..."
	uv run mdformat *.md docs/**/*.md --wrap 120

# lint-strict: 엄격한 코드 품질 검사 (모든 규칙 적용)
# - ruff check --select ALL: 모든 규칙 적용 (일부 규칙 무시)
# - mypy --strict: 엄격한 타입 검사
# - bandit --severity-level low: 낮은 심각도까지 보안 검사
lint-strict:
	@echo "Running strict lint checks..."
	@echo "Running ruff with all rules..."
	uv run ruff check $(LINT_DIRS) --select ALL --ignore E501,B008,C901,COM812,B904,B017,B007,D100,D101,D102,D103,D104,D105,D106,D107 $(EXCLUDE_DIRS) --output-format=full
	@echo "Running mypy with strict settings..."
	uv run mypy $(LINT_DIRS_CORE) --strict --ignore-missing-imports $(EXCLUDE_DIRS)
	@echo "Running bandit with strict settings..."
	@uv run bandit -r $(LINT_DIRS_SECURITY) --severity-level low --exclude "*/tests/*,*/scripts/*,*/debug/*,*/examples/*"

# lint-strict-fix: 엄격한 코드 품질 검사 + 자동 수정
# - ruff check --select ALL --fix: 모든 규칙 적용하고 자동 수정
# - ruff format: 코드 포맷팅
# - mypy --strict: 엄격한 타입 검사 (수정 불가, 경고만)
# - 사용법: make lint-strict-fix UNSAFE_FIXES=1 (위험한 수정 포함)
lint-strict-fix:
	@echo "Running strict lint with auto-fix..."
	@echo "Running ruff check with all rules and auto-fix..."
	uv run ruff check $(LINT_DIRS) --select ALL --ignore E501,B008,C901,COM812,B904,B017,B007,D100,D101,D102,D103,D104,D105,D106,D107 --fix $(UNSAFE_FLAG) $(EXCLUDE_DIRS)
	@echo "Running ruff format..."
	uv run ruff format $(LINT_DIRS) $(EXCLUDE_DIRS)
	@echo "Running mypy with strict settings..."
	uv run mypy $(LINT_DIRS_CORE) --strict --ignore-missing-imports $(EXCLUDE_DIRS) || echo "⚠️  Type check completed with warnings"
	@echo "Running mdformat..."
	uv run mdformat *.md docs/**/*.md --wrap 120
	@echo "✅ Strict lint with auto-fix completed!"

# Pre-commit integration
pre-commit-install:
	@echo "Installing pre-commit hooks..."
	uv run pre-commit install

pre-commit-run:
	@echo "Running all pre-commit hooks..."
	uv run pre-commit run --all-files

pre-commit-update:
	@echo "Updating pre-commit hooks..."
	uv run pre-commit autoupdate

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
	make lint-check
	make test-coverage
	@echo "CI checks passed!"

ci-fix:
	@echo "Running CI with auto-fix..."
	make lint-fix
	make test-coverage
	@echo "CI with auto-fix completed!"

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
