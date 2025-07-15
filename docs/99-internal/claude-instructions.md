# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test modules
pytest tests/test_prepare.py -v
pytest tests/test_build.py -v
pytest tests/test_template.py -v
pytest tests/test_deploy.py -v
```

### Building and Publishing
```bash
# Build package
uv build

# Publish to PyPI (using twine)
uv run -m twine upload dist/*

# Force reinstall local development version
uv pip install --force-reinstall --no-deps --upgrade .
```

### Development Workflow
```bash
# Basic sbkube workflow commands
sbkube prepare --base-dir . --app-dir config
sbkube build --base-dir . --app-dir config  
sbkube template --base-dir . --app-dir config --output-dir rendered/
sbkube deploy --base-dir . --app-dir config --namespace <namespace>
```

## Architecture

### Core Structure
- **sbkube/** - Main Python package containing CLI implementation
  - **cli.py** - Main entry point with Click-based command group
  - **commands/** - Individual command implementations (prepare, build, template, deploy, etc.)
  - **models/** - Pydantic data models for configuration validation
  - **utils/** - Common utilities (logging, file operations, command execution)

### Key Components
- **Configuration System**: Uses YAML/TOML config files with JSON schema validation
- **Multi-stage Workflow**: prepare → build → template → deploy pipeline
- **Kubernetes Integration**: Uses python-kubernetes library for cluster interaction
- **Helm Integration**: Wraps helm CLI commands for chart management
- **Source Management**: Supports Helm repos, OCI charts, Git repos, and local files

### Application Types
- `pull-helm` / `pull-helm-oci` / `pull-git` - Source preparation
- `copy-app` - Local file copying  
- `install-helm` / `install-kubectl` / `install-action` - Deployment methods

### Configuration Files
- **config.yaml** - Defines applications, their types, and deployment specs
- **sources.yaml** - Defines external sources (Helm repos, Git repos)
- **values/** - Directory containing Helm values files

### Directory Structure During Execution
- **charts/** - Downloaded Helm charts (from prepare step)
- **repos/** - Cloned Git repositories (from prepare step)
- **build/** - Built application artifacts (from build step)
- **rendered/** - Templated YAML outputs (from template step)

## Development Guidelines

### Package Management
- Use `uv` instead of pip for dependency management
- Add dependencies with `uv add <library>` (don't create requirements.txt)
- Run scripts with `uv run script.py`

### Code Style
- Follow existing patterns in the codebase
- Use Pydantic models for configuration validation
- Maintain consistent logging using the custom logger utility
- Handle errors gracefully with appropriate user feedback

### Testing
- Update tests when making source changes
- Use pytest for all testing
- Test both successful operations and error conditions
- Include integration tests for full workflows

### Kubernetes Testing
For manual testing with Kind:
```bash
# Create test cluster
kind create cluster --name sbkube-test
kubectl config use-context kind-sbkube-test

# Run sbkube commands against test cluster
uv run -m sbkube.cli deploy --base-dir examples/k3scode --app-dir memory --namespace data-memory
```

## Important Notes

- This is a Korean Kubernetes deployment automation tool (`k3s용 헬름+yaml+git 배포 자동화 CLI 도구`)
- Part of ScriptonBasestar's DevOps infrastructure tooling
- The tool supports dry-run operations and various deployment targets
- CLI provides comprehensive kubeconfig inspection when run without arguments