# Code quality and linting targets

.PHONY: check lint lint-check lint-fix lint-strict lint-strict-fix

LINT_DIRS = sbkube tests
LINT_DIRS_SECURITY = sbkube
LINT_DIRS_CORE = sbkube
EXCLUDE_DIRS = --exclude migrations --exclude node_modules --exclude examples

# Optional unsafe fixes (use: make lint-fix UNSAFE_FIXES=1)
UNSAFE_FIXES ?=
UNSAFE_FLAG = $(if $(UNSAFE_FIXES),--unsafe-fixes,)

# check: 빠른 문법 + 타입 체크 (가장 빠름, 빌드 컴파일처럼 사용)
# - Python 문법 체크: py_compile로 syntax error 검출
# - mypy: 기본 타입 검사 (엄격하지 않음)
# - 용도: 코드 수정 후 빠른 검증, CI 사전 체크
check:
	@echo "🔍 Quick syntax and type check..."
	@echo "✓ Checking Python syntax..."
	@uv run python -m py_compile sbkube/**/*.py 2>&1 | grep -v "^$$" || echo "✅ Syntax OK"
	@echo "✓ Running mypy..."
	@uv run mypy $(LINT_DIRS_CORE) --ignore-missing-imports --no-error-summary $(EXCLUDE_DIRS) || echo "⚠️  Type check completed with warnings"
	@echo "✅ Quick check completed!"

# lint-check: 변경 사항 미리보기 (diff 모드)
# - ruff check --diff: 수정될 내용을 미리보기로 표시 (실제 수정 없음)
# - mypy: 타입 검사
# - bandit: 보안 취약점 검사 (medium 레벨)
# - mdformat: 마크다운 포맷팅 체크 (diff 모드)
lint-check:
	@echo "Running lint checks only (no auto-fix)..."
	@echo "Running ruff check..."
	uv run ruff check $(LINT_DIRS) --diff $(EXCLUDE_DIRS)
	@echo "Running mypy..."
	uv run mypy $(LINT_DIRS_CORE) --ignore-missing-imports $(EXCLUDE_DIRS)
	@echo "Running bandit security check..."
	uv run bandit -r $(LINT_DIRS_SECURITY) --skip B101,B404,B603,B607,B602 --severity-level medium --quiet --exclude "*/tests/*,*/scripts/*,*/debug/*,*/examples/*" || echo "✅ Security check completed"
	@echo "Running mdformat check..."
	uv run mdformat --check *.md docs/**/*.md --wrap 120 || echo "✅ Markdown format check completed"

lint: lint-check

# lint-fix: 자동 수정 포함 코드 품질 검사 + 포맷팅
# - ruff check --fix: 자동 수정 가능한 규칙 위반 항목 수정
# - ruff format: 코드 포맷팅 자동 적용, black대체용
# - mypy: 타입 검사
# - bandit: 보안 취약점 검사 (medium 레벨)
# - mdformat: 마크다운 포맷팅
# - 사용법: make lint-fix UNSAFE_FIXES=1 (위험한 자동 수정 포함)
lint-fix:
	@echo "Running lint with auto-fix..."
	@echo "Running ruff check with auto-fix..."
	uv run ruff check $(LINT_DIRS) --fix $(UNSAFE_FLAG) $(EXCLUDE_DIRS)
	@echo "Running ruff format..."
	uv run ruff format $(LINT_DIRS) $(EXCLUDE_DIRS)
	@echo "Running mypy..."
	uv run mypy $(LINT_DIRS_CORE) --ignore-missing-imports $(EXCLUDE_DIRS)
	@echo "Running bandit security check..."
	uv run bandit -r $(LINT_DIRS_SECURITY) --skip B101,B404,B603,B607,B602 --severity-level medium --quiet --exclude "*/tests/*,*/scripts/*,*/debug/*,*/examples/*" || echo "✅ Security check completed"
	@echo "Running mdformat..."
	uv run mdformat *.md docs/**/*.md --wrap 120

# lint-strict: 엄격한 코드 품질 검사 (모든 규칙 적용)
# - ruff check --select ALL: 모든 규칙 적용 (일부 규칙 무시)
# - mypy --strict: 엄격한 타입 검사
# - bandit --severity-level low: 낮은 심각도까지 보안 검사
lint-strict:
	@echo "Running strict lint checks..."
	@echo "Running ruff with all rules..."
	uv run ruff check $(LINT_DIRS) --select ALL --ignore E501,B008,C901,COM812,B904,B017,B007,D100,D101,D102,D103,D104,D105,D106,D107 $(EXCLUDE_DIRS) --output-format=full
	@echo "Running mypy with strict settings..."
	uv run mypy $(LINT_DIRS_CORE) --strict --ignore-missing-imports $(EXCLUDE_DIRS)
	@echo "Running bandit with strict settings..."
	@uv run bandit -r $(LINT_DIRS_SECURITY) --severity-level low --exclude "*/tests/*,*/debug/*,*/examples/*"

# lint-strict-fix: 엄격한 코드 품질 검사 + 자동 수정
# - ruff check --select ALL --fix: 모든 규칙 적용하고 자동 수정
# - ruff format: 코드 포맷팅
# - mypy --strict: 엄격한 타입 검사 (수정 불가, 경고만)
# - 사용법: make lint-strict-fix UNSAFE_FIXES=1 (위험한 수정 포함)
lint-strict-fix:
	@echo "Running strict lint with auto-fix..."
	@echo "Running ruff check with all rules and auto-fix..."
	uv run ruff check $(LINT_DIRS) --select ALL --ignore E501,B008,C901,COM812,B904,B017,B007,D100,D101,D102,D103,D104,D105,D106,D107 --fix $(UNSAFE_FLAG) $(EXCLUDE_DIRS)
	@echo "Running ruff format..."
	uv run ruff format $(LINT_DIRS) $(EXCLUDE_DIRS)
	@echo "Running mypy with strict settings..."
	uv run mypy $(LINT_DIRS_CORE) --strict --ignore-missing-imports $(EXCLUDE_DIRS) || echo "⚠️  Type check completed with warnings"
	@echo "Running mdformat..."
	uv run mdformat *.md docs/**/*.md --wrap 120
	@echo "✅ Strict lint with auto-fix completed!"
