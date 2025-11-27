# Testing targets

.PHONY: test test-unit test-integration test-performance test-coverage test-watch test-k8s test-helm test-fast test-quick test-unit-only test-commands test-models test-state test-utils test-parallel test-e2e test-legacy

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
