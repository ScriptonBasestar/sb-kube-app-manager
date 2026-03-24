# Installation targets

.PHONY: install install-global install-system install-dev install-test install-all bump-version

## bump-version: Bump patch version if there are changes or new commit
bump-version:
	@LAST_COMMIT=$$(cat .last_built_commit 2>/dev/null || echo ""); \
	CURRENT_COMMIT=$$(git rev-parse HEAD 2>/dev/null || echo "none"); \
	DIRTY=$$(git status --porcelain | grep -v 'pyproject.toml'); \
	if [ "$$CURRENT_COMMIT" != "$$LAST_COMMIT" ] || [ -n "$$DIRTY" ]; then \
		echo "Changes or new commit detected, bumping version..."; \
		CURRENT_VERSION=$$(grep '^version = ' pyproject.toml | head -1 | cut -d'"' -f2); \
		MAJOR=$$(echo $$CURRENT_VERSION | cut -d. -f1); \
		MINOR=$$(echo $$CURRENT_VERSION | cut -d. -f2); \
		PATCH=$$(echo $$CURRENT_VERSION | cut -d. -f3); \
		NEW_PATCH=$$(($$PATCH + 1)); \
		NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
		sed -i "s/^version = \"$$CURRENT_VERSION\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
		echo "$$CURRENT_COMMIT" > .last_built_commit; \
		echo "Version bumped: $$CURRENT_VERSION → $$NEW_VERSION"; \
	else \
		echo "No changes detected, skipping version bump."; \
	fi

install: bump-version
	uv pip install -e .

install-global: bump-version
	uv cache clean sbkube --force 2>/dev/null || true
	uv tool install . --force --reinstall

install-system:
	uv pip install -e . --system

install-dev: bump-version
	uv pip install -e . --group dev

install-test: bump-version
	uv pip install -e . --group test

install-all: bump-version
	uv pip install -e . --group dev --group test
