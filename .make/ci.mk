# CI targets

.PHONY: ci ci-fix

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
