# Development tools and utilities

.PHONY: dev-setup pre-commit-install pre-commit-run pre-commit-update update-deps docs

dev-setup:
	@echo "Creating Python virtual environment in .venv (if missing)..."
	uv venv
	@echo "Syncing project dependencies..."
	uv sync
	@echo "Installing sbkube in editable mode with dev + test dependencies..."
	uv pip install -e . --group dev --group test
	@echo ""
	@echo "✅ Local development environment is ready."
	@echo "To use 'sbkube', activate the virtual environment:"
	@echo "  source .venv/bin/activate"
	@echo "Then run:"
	@echo "  sbkube version"

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

# Update dependencies
update-deps:
	uv pip compile pyproject.toml -o requirements.txt
	uv pip sync requirements.txt

# Documentation
docs:
	@echo "Generating documentation..."
	pdoc --html --output-dir docs sbkube
