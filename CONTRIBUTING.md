# Contributing to SBKube

> **Quick Reference**: How to contribute to SBKube v0.9.1
>
> **For Complete Details**: See [Development Guide](docs/04-development/README.md) and [Coding Standards](docs/04-development/coding-standards.md)

Thank you for your interest in contributing to SBKube! This document provides essential guidelines for getting started.

---

## Quick Start

### Prerequisites
- **Python 3.14+** (required)
- **uv** package manager (recommended)
- **Git**
- **kubectl** (for testing)
- **helm** v3.x (for testing)

### Development Setup

```bash
# 1. Clone repository
git clone https://github.com/archmagece/sb-kube-app-manager.git
cd sb-kube-app-manager

# 2. Create virtual environment
uv venv
source .venv/bin/activate

# 3. Install development dependencies
uv sync --frozen
uv pip install -e .

# 4. Verify setup
sbkube version  # Should show: 0.9.1
make test-quick # Run quick tests
```

---

## Development Workflow

### 1. Making Changes

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make your changes
# ... edit code ...

# Format and lint
make lint-fix

# Run tests
make test-quick  # Fast unit tests
make test        # Full test suite

# Commit changes
git add .
git commit -m "feat(scope): add my feature"
```

### 2. Code Quality

**Before committing:**
```bash
# Quick validation
make check         # Fast syntax + type check

# Auto-fix issues
make lint-fix      # Format + fix linting

# Run tests
make test-quick    # Unit tests only
make test          # All tests (slower)
```

**Code quality tools:**
- **ruff**: Linting and formatting
- **mypy**: Static type checking
- **bandit**: Security scanning
- **pytest**: Test framework

### 3. Testing

**Test categories:**
```bash
# Unit tests (no external dependencies)
make test-unit

# Integration tests (require cluster)
make test-integration

# End-to-end tests (full workflow)
make test-e2e

# All tests
make test
```

**Writing tests:**
- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use pytest fixtures for common setup
- Mark slow/integration tests: `@pytest.mark.integration`

---

## Contribution Guidelines

### Code Style

**Follow existing patterns:**
- **Type hints**: All functions must have type annotations
- **Docstrings**: Public functions need clear docstrings
- **Error handling**: Use specific exceptions, not bare `except`
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes

**Example:**
```python
def deploy_helm_app(
    app_name: str,
    chart_path: Path,
    namespace: str,
    output: OutputManager,
) -> bool:
    """Deploy a Helm application to Kubernetes.

    Args:
        app_name: Name of the application
        chart_path: Path to Helm chart directory
        namespace: Target Kubernetes namespace
        output: Output manager for user feedback

    Returns:
        True if deployment succeeded, False otherwise

    Raises:
        HelmExecutionError: If Helm command fails
    """
    # Implementation...
```

### Commit Message Format

We follow Conventional Commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `chore`: Build process or auxiliary tool changes

**Example:**
```
feat(commands): add check-updates command for Helm chart version checking

Implements semantic version comparison and interactive config.yaml updates.
Supports --all flag to check all releases and --update-config for
interactive updates.

Closes #123
```

### Pull Request Process

1. **Fork the repository** on GitHub
2. **Create a feature branch** from `master`
3. **Make your changes** with clear commits
4. **Run tests**: `make test`
5. **Push to your fork**: `git push origin feature/my-feature`
6. **Create Pull Request** on GitHub

**PR Requirements:**
- ✅ All tests pass (`make test`)
- ✅ Code is linted (`make lint-fix`)
- ✅ Type checking passes (`make check`)
- ✅ Documentation updated if needed
- ✅ Changelog entry added (if user-facing)

---

## Project Structure

### Key Directories

```
sbkube/
├── cli.py              # CLI entry point
├── commands/           # Command implementations
├── models/             # Pydantic models
├── state/              # SQLAlchemy state management
├── utils/              # Utilities
└── validators/         # Validation logic

tests/
├── unit/               # Unit tests
├── integration/        # Integration tests
└── e2e/                # End-to-end tests

docs/
├── 00-product/         # Product documentation
├── 02-features/        # Feature guides
├── 04-development/     # Development guides
└── ...

examples/               # Example configurations
```

### Important Files

- `pyproject.toml`: Project metadata and dependencies
- `ruff.toml`: Linting configuration
- `Makefile`: Development commands
- `.pre-commit-config.yaml`: Pre-commit hooks

---

## Making Specific Contributions

### Adding a New Command

1. Create command file in `sbkube/commands/`
2. Inherit from `EnhancedBaseCommand`
3. Register in `sbkube/cli.py`
4. Add to command categories in `SbkubeGroup`
5. Document in `docs/02-features/commands.md`
6. Write tests in `tests/unit/commands/`

**Example skeleton:**
```python
from sbkube.utils.base_command import EnhancedBaseCommand

class MyCommand(EnhancedBaseCommand):
    def __init__(self, base_dir=".", app_config_dir="config"):
        super().__init__(
            base_dir=base_dir,
            app_config_dir=app_config_dir,
            output_format="human",
        )

    def execute(self) -> int:
        """Execute the command logic."""
        # Implementation...
        return 0
```

### Adding a New App Type

1. Create Pydantic model in `sbkube/models/config_model.py`
2. Add deployer function in `sbkube/commands/deploy.py`
3. Update `deploy_app()` dispatcher
4. Document in `docs/02-features/application-types.md`
5. Add examples in `examples/app-types/`
6. Write comprehensive tests

### Improving Documentation

Documentation is highly valued! Areas to improve:
- Typo fixes and clarifications
- Usage examples
- Troubleshooting guides
- Architecture explanations
- Tutorial additions

**Documentation structure:**
- Root documents (PRODUCT.md, USAGE.md, etc.): High-level overviews
- `docs/` directory: Detailed documentation
- Code comments: Implementation details

---

## Development Commands Reference

```bash
# Setup
make setup          # Complete environment setup

# Code Quality (fast → strict)
make check          # Quick syntax + type check
make lint-fix       # Auto-fix issues
make lint-strict    # Strict linting

# Testing (fast → comprehensive)
make test-quick     # Fast unit tests only
make test-unit      # All unit tests
make test           # Full test suite
make test-coverage  # With coverage report

# CI Simulation
make ci             # Run full CI checks
make ci-fix         # CI with auto-fix

# Build
make build          # Build package
make clean          # Clean build artifacts
```

---

## Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and ideas
- **Pull Requests**: Code contributions

### Reporting Bugs

When reporting bugs, please include:
- SBKube version (`sbkube version`)
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (use `--verbose`)

**Template:**
```markdown
## Bug Description
[Clear description of the issue]

## Environment
- SBKube version: 0.9.1
- Python version: 3.12.1
- OS: Ubuntu 22.04
- Kubernetes: k3s v1.28.0

## Steps to Reproduce
1. Run `sbkube apply`
2. ...

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happened]

## Logs
```bash
$ sbkube --verbose apply
[Paste logs here]
```
```

### Requesting Features

Feature requests should include:
- **Use case**: Why is this needed?
- **Proposed solution**: How should it work?
- **Alternatives considered**: Other approaches?
- **Additional context**: Examples, screenshots, etc.

---

## Code of Conduct

### Our Standards

- **Be respectful** and inclusive
- **Provide constructive feedback**
- **Focus on the best for the community**
- **Show empathy** towards others

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information

---

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with release notes
3. Create git tag: `git tag v0.X.Y`
4. Build package: `uv build`
5. Upload to PyPI: `twine upload dist/*`
6. Create GitHub release with notes

---

## Recognition

Contributors will be acknowledged in:
- CHANGELOG.md release notes
- GitHub contributors page
- Project README (for significant contributions)

---

## License

By contributing to SBKube, you agree that your contributions will be licensed under the MIT License.

---

## Related Documentation

- **Development Guide**: [docs/04-development/README.md](docs/04-development/README.md)
- **Coding Standards**: [docs/04-development/coding-standards.md](docs/04-development/coding-standards.md)
- **Testing Guide**: [docs/04-development/testing.md](docs/04-development/testing.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Technical Spec**: [SPEC.md](SPEC.md)

---

**Thank you for contributing to SBKube!** 🎉

Your contributions help make Kubernetes deployment automation better for everyone.

---

**Document Version**: 1.0
**Last Updated**: 2025-12-01
**SBKube Version**: 0.9.1
