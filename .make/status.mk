# Status and version management targets

.PHONY: version bump-patch bump-minor perf-report test-report

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

# Performance report
perf-report:
	pytest -v -m performance --benchmark-only --benchmark-json=benchmark.json
	@echo "Performance report saved to benchmark.json"

# Generate test report
test-report:
	pytest -v --html=report.html --self-contained-html
	@echo "Test report saved to report.html"
