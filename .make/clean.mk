# Clean and cleanup targets

.PHONY: clean clean-db clean-docker clean-all

# Clean build artifacts and caches
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

# Development database cleanup
clean-db:
	@echo "Cleaning development database..."
	rm -f ~/.sbkube/deployments.db

# Docker cleanup (for integration tests)
clean-docker:
	@echo "Cleaning test containers..."
	docker ps -a | grep test- | awk '{print $$1}' | xargs -r docker rm -f
	docker ps -a | grep k3s | awk '{print $$1}' | xargs -r docker rm -f

# Full cleanup
clean-all: clean clean-db clean-docker
