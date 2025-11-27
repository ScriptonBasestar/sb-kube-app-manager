# Build targets

.PHONY: build release

build:
	uv build

# Release preparation (runs clean, test, build)
release: clean test build
	@echo "Ready for release!"
	@echo "Don't forget to:"
	@echo "  1. Update CHANGELOG.md"
	@echo "  2. Commit all changes"
	@echo "  3. Tag the release: git tag v$$(make version)"
	@echo "  4. Push tags: git push --tags"
	@echo "  5. Upload to PyPI: twine upload dist/*"
