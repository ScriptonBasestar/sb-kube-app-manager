# sbkube Test Suite

This directory contains the comprehensive test suite for sbkube, including unit tests, integration tests, and performance benchmarks.

## Test Structure

```
tests/
├── unit/                    # Unit tests - isolated component testing
│   ├── commands/           # CLI command tests (build, deploy, etc.)
│   ├── models/            # Data model validation tests
│   ├── state/             # State management (DB, tracking, rollback)
│   ├── utils/             # Utility function tests (27 exception scenarios)
│   └── conftest.py        # Unit test fixtures
├── integration/            # Integration tests - component interaction
│   ├── test_full_workflow.py     # Complete pipeline testing
│   ├── test_helm_integration.py  # Helm CLI integration
│   ├── test_k8s_integration.py   # Kubernetes API integration
│   └── conftest.py              # Integration test fixtures
├── performance/           # Performance tests - benchmarks & resource monitoring
│   ├── test_performance_benchmarks.py  # Execution time & resource usage
│   └── conftest.py                     # Performance test fixtures
├── e2e/                   # End-to-end tests - full user scenarios
│   └── conftest.py        # E2E test fixtures
├── legacy/                # Legacy tests - being refactored
│   ├── test_config_validation.py  # 477 lines - being split
│   ├── test_deployment_state.py   # 504 lines - already split
│   └── test_full_pipeline.py      # To be moved to integration/e2e
└── conftest.py           # Shared fixtures and configuration
```

## Test Categories

### Unit Tests

Unit tests verify individual components in isolation:
- Configuration validation
- Exception handling
- Retry mechanisms
- Command logic
- Utility functions

### Integration Tests

Integration tests verify interactions between components and with external systems:
- Complete workflow tests (prepare → build → template → deploy)
- Helm integration
- Kubernetes integration
- Git repository operations
- State tracking and rollback

### Performance Tests

Performance tests measure execution time and resource usage:
- Configuration loading benchmarks
- Command execution performance
- Template rendering performance
- Scalability tests
- Resource usage monitoring

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
uv add --group test pytest pytest-cov pytest-xdist pytest-benchmark pytest-mock testcontainers kubernetes faker
```

2. For integration tests, ensure you have:
- Docker (for testcontainers)
- Helm CLI installed
- kubectl CLI installed

### Running All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sbkube --cov-report=html

# Run in parallel
pytest -n auto
```

### Running Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Performance tests only
pytest -m performance

# Tests requiring Kubernetes
pytest -m requires_k8s

# Tests requiring Helm
pytest -m requires_helm
```

### Running Individual Test Files

```bash
# Run specific test file
pytest tests/test_deploy.py

# Run specific test class
pytest tests/integration/test_helm_integration.py::TestHelmIntegration

# Run specific test method
pytest tests/test_deploy.py::TestDeployCommand::test_deploy_helm_success
```

## Test Markers

The following pytest markers are available:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.e2e`: End-to-end tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.slow`: Tests that take more than 5 seconds
- `@pytest.mark.requires_k8s`: Tests requiring Kubernetes cluster
- `@pytest.mark.requires_helm`: Tests requiring Helm
- `@pytest.mark.requires_network`: Tests requiring network access
- `@pytest.mark.benchmark`: Performance benchmark tests

## Writing Tests

### Unit Test Example

```python
import pytest
from sbkube.commands.deploy import DeployCommand

@pytest.mark.unit
def test_deploy_validation(mock_runner):
    """Test deployment validation logic."""
    command = DeployCommand(
        base_dir=".",
        app_config_dir="config",
        cli_namespace="test",
        dry_run=True
    )
    # Test implementation
    assert command.dry_run is True
```

### Integration Test Example

```python
@pytest.mark.integration
@pytest.mark.requires_helm
def test_helm_workflow(sbkube_project, helm_binary):
    """Test complete Helm workflow."""
    runner = CliRunner()
    result = runner.invoke(main, [
        'deploy', 
        '--base-dir', str(sbkube_project),
        '--app-dir', 'config'
    ])
    assert result.exit_code == 0
```

### Performance Test Example

```python
@pytest.mark.performance
def test_config_loading_performance(benchmark, large_config):
    """Benchmark configuration loading."""
    result = benchmark(load_config, large_config)
    assert result is not None
```

## CI/CD Integration

### GitHub Actions

See `.github/workflows/test.yml` for the complete CI configuration.

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[test]"
      - name: Run tests
        run: |
          pytest --cov=sbkube --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Local Development

For local development, use the provided Makefile targets:

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests
make test-integration

# Run with coverage
make test-coverage

# Run performance tests
make test-performance
```

## Test Configuration

Test configuration is defined in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
addopts = [
    "-ra",
    "--strict-markers",
    "--cov=sbkube",
    "--cov-branch",
    "--cov-report=term-missing:skip-covered",
]
```

## Fixtures

### Common Fixtures

Located in `tests/conftest.py`:
- `runner`: Click test runner
- `base_dir`: Temporary base directory
- `app_dir`: Application configuration directory
- `sample_config`: Sample configuration data
- `sample_sources`: Sample sources configuration

### Integration Test Fixtures

Located in `tests/integration/conftest.py`:
- `k8s_cluster`: K3s Kubernetes cluster (using testcontainers)
- `k8s_namespace`: Isolated namespace for tests
- `helm_binary`: Validated Helm binary path
- `helm_repo_server`: Local Helm repository server
- `git_repo`: Temporary Git repository
- `sbkube_project`: Complete project structure

### Performance Test Fixtures

Located in `tests/performance/conftest.py`:
- `performance_benchmark`: Performance metrics collector
- `large_project_generator`: Generate large test projects
- `stress_test_data`: Generate stress test data
- `measure_performance`: Context manager for performance measurement

## Coverage Goals

We aim to maintain:
- Overall coverage: ≥ 90%
- Unit test coverage: ≥ 95%
- Integration test coverage: ≥ 80%
- No uncovered critical paths

Current coverage can be viewed by running:
```bash
pytest --cov=sbkube --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

### Common Issues

1. **Docker not available**: Integration tests using testcontainers require Docker
   ```bash
   # Check Docker is running
   docker ps
   ```

2. **Helm/kubectl not found**: Some tests require these tools
   ```bash
   # Install Helm
   curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
   
   # Install kubectl
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/
   ```

3. **Slow tests**: Run tests in parallel
   ```bash
   pytest -n auto
   ```

4. **Resource cleanup**: If tests fail to clean up resources
   ```bash
   # Clean up test namespaces
   kubectl delete ns -l test=sbkube
   
   # Clean up Helm releases
   helm list --all-namespaces | grep test- | awk '{print $1}' | xargs -I {} helm delete {}
   ```

## Contributing

When adding new features:
1. Write unit tests for new functions/classes
2. Add integration tests for user-facing features
3. Include performance tests for critical paths
4. Update this documentation if adding new test categories or fixtures
5. Ensure all tests pass and coverage remains above 90%