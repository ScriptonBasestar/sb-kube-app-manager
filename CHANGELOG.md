______________________________________________________________________

## type: Historical Reference audience: Developer topics: [changelog, version-history, releases] llm_priority: low exclude_from_context: true last_updated: 2025-01-04

# Changelog - SBKube

> **참고**: 이 문서의 과거 버전 예제에는 Bitnami 차트 참조가 포함되어 있습니다. 현재 버전(v0.6.0+)에서는 Grafana, Prometheus 등 오픈소스 차트를 사용합니다.

## [Unreleased]

### ✨ New Features

_(No unreleased features yet)_

---

## [0.7.1] - 2025-01-06

### 🚀 New Features

**Cluster Global Values** (2025-01-06)

- ✅ **NEW**: `cluster_values_file` in sources.yaml - Load cluster-level values from external file
- ✅ **NEW**: `global_values` in sources.yaml - Inline cluster-level values
- ✅ **NEW**: Deep merge utility for hierarchical values inheritance
- ✅ **NEW**: Automatic values priority: cluster_values_file < global_values < app values
- ✅ **NEW**: Cluster-level values applied to all Helm apps in template/deploy
- ✅ **NEW**: Example configuration and documentation

**Usage Example**:

```yaml
# sources.yaml
cluster_values_file: cluster-values.yaml  # External file
global_values:  # Inline values (higher priority)
  global:
    environment: production
    monitoring:
      enabled: true
```

**Files Added**:
- `sbkube/utils/dict_merge.py` - Deep merge utility
- `tests/unit/utils/test_dict_merge.py` - Test suite
- `docs/03-configuration/sources-schema.md` - Complete sources.yaml documentation
- `examples/cluster-global-values/` - Working examples

**See:** [sources-schema.md](docs/03-configuration/sources-schema.md)

**helm_label_injection Control** (2025-01-06)

- ✅ **NEW**: `helm_label_injection` option per app (default: true)
- ✅ **FIX**: Disable automatic label injection for strict Helm charts (e.g., Authelia)
- ✅ **IMPROVED**: Fallback to state DB and name pattern tracking when disabled

**Usage Example**:

```yaml
# config.yaml
apps:
  authelia:
    type: helm
    chart: authelia/authelia
    helm_label_injection: false  # Disable for strict validation charts
```

### 🐛 Bug Fixes

**Enhanced Error Handling for Deployment Interruptions** (2025-01-06)

- ✅ **FIX**: KeyboardInterrupt (Ctrl+C) now exits immediately with clear message
- ✅ **FIX**: Helm deployment timeout shows detailed troubleshooting guide
- ✅ **IMPROVED**: Timeout detection with actionable next steps
- ✅ **IMPROVED**: Deployment interruption handling with status check commands

**Error Messages**:

```
⚠️  Deployment interrupted by user (Ctrl+C)
ℹ️  App 'keycloak' deployment may be incomplete.
Check deployment status: kubectl get pods -n auth
```

```
❌ Helm deployment timed out after 300 seconds (5 minutes).

Possible causes:
  - Pod image pull is slow or failing
  - Pod is failing health checks
  - Insufficient cluster resources

Troubleshooting:
  1. Check pod status: kubectl get pods -n {namespace}
  2. Check pod logs: kubectl logs -n {namespace} <pod-name>
  3. Describe pod: kubectl describe pod -n {namespace} <pod-name>
  4. Increase timeout: add 'timeout: 10m' to app config
```

### 📚 Documentation

- ✅ **NEW**: [sources-schema.md](docs/03-configuration/sources-schema.md) - Complete sources.yaml reference
- ✅ **UPDATED**: [PRODUCT.md](PRODUCT.md) and [SPEC.md](SPEC.md) as comprehensive root documents (SSOT)
- ✅ **UPDATED**: [CLAUDE.md](CLAUDE.md) with architecture patterns and development commands
- ✅ **SYNCED**: All documentation layers aligned with PRODUCT.md and SPEC.md

---

## [0.7.0] - 2025-01-03

### ✨ New Features

**LLM-Friendly Output System** (2025-01-03)

**Phase 1: Infrastructure** (2025-01-03)

- ✅ **NEW**: Multiple output formats for LLM agents and automation
  - `human` - Rich Console output (default)
  - `llm` - LLM-optimized compact text (80-90% token savings)
  - `json` - Structured JSON for machine parsing
  - `yaml` - YAML format output
- ✅ **NEW**: `--format` CLI option for all commands
- ✅ **NEW**: `SBKUBE_OUTPUT_FORMAT` environment variable support
- ✅ **NEW**: `OutputFormatter` utility class for consistent formatting
- ✅ **ENHANCED**: `EnhancedBaseCommand` with built-in formatter support

**Phase 2: Command Integration** (2025-01-03)

- ✅ **INTEGRATED**: `prepare` command - LLM-friendly output for chart/repo downloads
- ✅ **INTEGRATED**: `build` command - LLM-friendly output for chart customization
- ✅ **INTEGRATED**: `deploy` command - LLM-friendly output for deployments
- ✅ **INTEGRATED**: `apply` command - Full workflow LLM output support
- ✅ **INTEGRATED**: `template` command - LLM-friendly output for YAML rendering

**Phase 3: Operational Commands** (2025-01-03)

- ✅ **INTEGRATED**: `status` command - LLM-friendly cluster status output
  - Cluster and node information
  - Helm release status by app-group or namespace
  - Structured deployment list with status
  - 80-85% token savings for status queries

**Usage Example**:

```bash
# LLM-optimized output (note: --format before subcommand)
sbkube --format llm apply
sbkube --format llm prepare
sbkube --format llm build
sbkube --format llm template
sbkube --format llm deploy
sbkube --format llm status

# JSON output
sbkube --format json status
sbkube --format json status --by-group

# Environment variable (recommended for LLM agents)
export SBKUBE_OUTPUT_FORMAT=llm
sbkube apply  # All commands use LLM format
sbkube status --managed  # Show only managed apps in LLM format
```

**Token Efficiency**:

- Simple deployment (3 apps): 500-1000 tokens → 80-100 tokens (80-90% savings)
- Complex deployment (10 apps): 2000-3000 tokens → 200-300 tokens (85-90% savings)
- Full workflow (prepare+build+template+deploy): 1500-2000 tokens → 150-200 tokens (85-90% savings)
- Template rendering: 300-500 tokens → 50-80 tokens (80-85% savings)
- Status queries: 800-1200 tokens → 120-180 tokens (80-85% savings)

**New Files**:

- `sbkube/utils/output_formatter.py` - Output formatting utilities
- `docs/02-features/llm-friendly-output.md` - Complete usage guide
- `tests/unit/utils/test_output_formatter.py` - Test suite (17 tests, 84% coverage)

**Modified Files**:

- `sbkube/commands/prepare.py` - LLM output support
- `sbkube/commands/build.py` - LLM output support
- `sbkube/commands/deploy.py` - LLM output support
- `sbkube/commands/apply.py` - LLM output support
- `sbkube/commands/template.py` - LLM output support
- `sbkube/commands/status.py` - Full LLM output support with structured status data
- `tests/commands/test_status.py` - Added LLM output tests

**See:** [LLM-Friendly Output Guide](docs/02-features/llm-friendly-output.md)

### ✨ Improved

**Enhanced Error Handling for Deployment Failures** (2025-01-04)

- ✅ **NEW**: Automatic error classification system for deployment failures
- ✅ **NEW**: Rich formatted error messages with contextual information
- ✅ **NEW**: Step-by-step error tracking (prepare/build/deploy phase identification)
- ✅ **NEW**: Automatic extraction of database connection details (PostgreSQL/MySQL)
- ✅ **NEW**: Automatic extraction of Helm release details
- ✅ **NEW**: Context-aware error suggestions and quick-fix commands
- ✅ **EXPANDED**: ERROR_GUIDE database with new error types:
  - `DatabaseAuthenticationError` - Database authentication failures
  - `DatabaseConnectionError` - Database connection issues
  - `HelmReleaseError` - Helm release deployment failures
  - `UnknownError` - Fallback for unclassified errors

**New Error Display Format**:

```
❌ 배포 실패: airflow
(3/3 단계에서 실패)

📍 실패 단계: 🚀 Deploy
🔍 에러 타입: DatabaseAuthenticationError
💬 상세 내용: password authentication failed for user "airflow_user"

🗄️ 데이터베이스 정보:
  • DB 종류: postgresql
  • 사용자: airflow_user
  • 호스트: postgresql.data.svc.cluster.local
  • 포트: 5432

💡 해결 방법:
  • DB 사용자/비밀번호 확인 → kubectl get secret -n <namespace>
  ...

⚡ 빠른 해결: kubectl get secret -n <namespace>
```

**New Files**:

- `sbkube/utils/error_classifier.py` - Pattern-based error classification
- `sbkube/utils/error_formatter.py` - Rich error formatting utilities
- `docs/07-troubleshooting/deployment-failures.md` - Comprehensive troubleshooting guide
- `tests/unit/utils/test_error_classifier.py` - Test suite (9 tests, 92% coverage)

**Updated Files**:

- `sbkube/commands/apply.py` - Integrated step-by-step error formatting
- `sbkube/utils/error_suggestions.py` - Extended ERROR_GUIDE database
- `docs/02-features/commands.md` - Added error handling documentation

**Technical Details**:

- Pattern-based classification using regex for common error types
- Severity levels: critical, high, medium, low, unknown
- Phase tracking: load_config, prepare, build, deploy
- Auto-recoverable flag for each error type
- Database detail extraction (db_type, user, host, port)
- Helm detail extraction (release_name, namespace, chart)

**User Impact**:

- Faster problem diagnosis with categorized errors
- Clear step identification reduces debugging time
- Automatic suggestions guide users to resolution
- Database and Helm errors provide extracted context
- Better UX for deployment failures

**Reference**: Issue - Airflow deployment failure with PostgreSQL authentication error

______________________________________________________________________

**Real-time Progress Tracking for Deployments** (2025-01-04)

- ✅ **NEW**: Rich Progress 바 기반 실시간 진행 상황 표시
- ✅ **NEW**: `ProgressTracker` 유틸리티 클래스
- ✅ **NEW**: `--no-progress` 옵션으로 기존 모드 사용 가능
- ✅ **ENHANCED**: apply 명령어에 progress 바 완전 통합
- ✅ **ENHANCED**: deploy_helm_app에 progress 지원 추가

**Progress 바 표시**:

```
━━━ myapp (helm) ━━━
⠋ Deploying myapp ━━━━━━━━━━ 1/3 • 0:00:05
📦 Prepare myapp
```

**Features**:

- 각 앱 배포 시 prepare/build/deploy 단계별 진행 상황
- 스피너 애니메이션으로 작업 진행 표시
- 경과 시간 표시 (TimeElapsedColumn)
- M/N 진행률 표시 (1/3, 2/3, 3/3)
- dry-run 시 자동 비활성화

**New CLI Options**:

- `sbkube apply --no-progress`: Progress 바 비활성화 (기존 모드)

**New Files**:

- `sbkube/utils/progress_tracker.py` - Progress tracking utilities

**Updated Files**:

- `sbkube/commands/apply.py` - Progress 바 통합 + --no-progress 옵션
- `sbkube/commands/deploy.py` - deploy_helm_app에 progress_tracker 파라미터

**Technical Details**:

- Rich Progress 라이브러리 활용
- SpinnerColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn
- disable 플래그로 CI/CD 환경 지원
- console_print() 메서드로 progress 중 출력 지원
- 컨텍스트 매니저 패턴 (track_task)

**User Impact**:

- 실시간 진행 상황 확인으로 더 나은 UX
- 여러 앱 배포 시 특히 유용
- 각 단계 소요 시간 파악 가능
- 하위 호환성 유지 (--no-progress)

**Reference**: Phase 2 - Real-time deployment progress tracking

### 🐛 Fixed

**Namespace Inheritance Bug** (2025-11-04)

- ✅ **CRITICAL**: Fixed YAML/Action/Kustomize apps not respecting `config.namespace`
- ✅ Resources were being deployed to `default` namespace instead of the configured global namespace when `app.namespace`
  was not explicitly set
- ✅ All app types now consistently inherit from `config.namespace` when `app.namespace` is None
- ✅ Backward compatible: Apps with explicit `app.namespace` continue to work identically
- ✅ Affected users: All deployments using YAML/Action/Kustomize apps without explicit app-level namespace

**Technical Details**:

- Modified `deploy_yaml_app()`, `deploy_action_app()`, `deploy_kustomize_app()` to accept `config_namespace` parameter
- Added namespace fallback logic: `namespace = app.namespace or config_namespace`
- Updated all deployer call sites to pass `config.namespace`
- Added comprehensive test suite: `tests/unit/commands/test_deploy_namespace.py` (9 test cases)
- Enhanced documentation in `application-types.md` and `config-schema.md`

**Migration**: No action required - fix is backward compatible

**Reference**: `tasks/issue/namespace-not-applied-to-yaml-manifests.md`

### ✨ New Features

**Multi-Cluster Context Support** (2025-11-03)

- ✅ Added `context` field to HelmApp, YamlApp, and ActionApp models
- ✅ `delete` command now reads sources.yaml for cluster configuration (consistent with deploy)
- ✅ App-level context override: config.yaml context > sources.yaml context > current kubectl context
- ✅ Enhanced `get_installed_charts()` to support kubeconfig parameter
- ✅ Full support for multi-cluster deployments in a single config.yaml

**Context Priority**:

1. **app.context** (highest): Per-app context in config.yaml
1. **sources.yaml context**: Project-level default (kubeconfig_context)
1. **current context** (lowest): System kubectl context

**Example**:

```yaml
apps:
  prod-app:
    type: helm
    chart: myapp/app
    context: prod-cluster      # Deploy to prod-cluster
    namespace: production

  staging-app:
    type: helm
    chart: myapp/app
    context: staging-cluster   # Deploy to staging-cluster
    namespace: staging
```

## [0.6.1] - 2025-10-31

### 🎨 Code Quality

**Linting and Formatting**

- ✅ Fixed 63 import formatting errors with ruff auto-fix
- ✅ Standardized multi-line import syntax across codebase
- ✅ Organized import order (stdlib → third-party → local)
- ✅ Removed unused imports
- ✅ Reformatted 16 files (88 files already compliant)
- ✅ Applied mdformat to markdown documentation

**Verification**

- ✅ ruff check: 0 errors remaining
- ✅ mypy: Type checking passed on 61 source files
- ✅ bandit: Security checks passed
- ✅ All critical module imports tested successfully

### ✨ Improved

**Help 화면 개선**

- ✅ 명령어를 카테고리별로 그룹화하여 가독성 향상
  - 🔄 핵심 워크플로우: prepare, build, template, deploy
  - ⚡ 통합 명령어: apply
  - 📊 상태 관리: status, history, rollback
  - 🔧 업그레이드/삭제: upgrade, delete
  - 🛠️ 유틸리티: init, validate, doctor, version
- ✅ 카테고리별 이모지 추가로 시각적 구분 강화
- ✅ 명령어 발견성 및 학습 곡선 개선

## [0.6.0] - 2025-10-31

### 🎯 New Features

**App-Group Dependency Validation**

- ✅ Automatic namespace detection for `deps` field validation
- ✅ Cross-namespace dependency checking (e.g., infra apps in `infra` namespace, data apps in `postgresql` namespace)
- ✅ Integration with `validate` command (non-blocking warnings)
- ✅ Integration with `apply` command (blocking errors)
- ✅ State-first approach using `.sbkube/deployments.db` for reliable dependency tracking
- ✅ New database method: `get_latest_deployment_any_namespace()` for namespace-agnostic queries

**Deployment Checker Enhancement**

- ✅ Automatic namespace detection in `DeploymentChecker.check_app_group_deployed()`
- ✅ Graceful fallback: namespace-specific query → any-namespace query
- ✅ Deployment status messages now include actual deployed namespace

**Validate Command Enhancement** (2025-10-31)

- ✅ Added `--app-dir` option for directory-based validation
- ✅ Added `--config-file` option (default: config.yaml)
- ✅ 3-level file resolution priority:
  1. Explicit file path (backward compatible)
  1. `--app-dir` + `--config-file` combination
  1. Current directory fallback (./config.yaml)
- ✅ Clear error messages with actionable solutions
- ✅ Comprehensive test suite added (15 test cases)

**Doctor Command Safety Improvements** (2025-10-31)

- ✅ Improved kubectl/helm detection using `shutil.which()` (fixes false negatives)
- ✅ Changed messaging from "자동 수정 가능" to "권장 해결 방법"
- ✅ Links to official documentation instead of shell commands
- ✅ Added safety warnings: "위 명령어는 참고용입니다. 실행 전 반드시 확인하세요"

### 🗑️ Breaking Changes

**Doctor Command** (2025-10-31):

- ❌ `--fix` option removed (security improvement)
  - **Reason**: Automatic system modifications can damage user environments
  - **Alternative**: Follow suggested commands manually after verification

### 🐛 Bug Fixes

- ✅ Fixed `pyproject.toml`: Moved `dependencies` from `[project.urls]` to `[project]` section
- ✅ Fixed kubectl detection false negative (kubectl exists but reported as missing)

### 🗑️ Breaking Changes (Previous)

**Removed Deprecated Commands**:

- ❌ `sbkube cluster` command removed → Use `sbkube status` instead
- ❌ `sbkube state` command removed → Use `sbkube history` and `sbkube rollback` instead

**Migration Guide**:

```bash
# Old commands (REMOVED in v0.6.0)
sbkube cluster status              # ❌ No longer available
sbkube state list                  # ❌ No longer available
sbkube state show dep_123          # ❌ No longer available
sbkube state rollback dep_123      # ❌ No longer available

# New commands (use these instead)
sbkube status                      # ✅ Cluster and app status
sbkube history                     # ✅ Deployment history
sbkube history --show dep_123      # ✅ Show specific deployment
sbkube rollback dep_123            # ✅ Rollback to deployment
```

### 📝 Documentation

- ✅ Updated `product-spec.md` with namespace auto-detection feature
- ✅ Added comprehensive validation examples in documentation
- ✅ Updated all command references from deprecated to new commands

### 🧪 Testing

- ✅ Added 3 new unit tests for namespace auto-detection
- ✅ Fixed 6 existing tests for new mock patterns
- ✅ All 19 tests passing in `test_deployment_checker.py`

______________________________________________________________________

______________________________________________________________________

## 과거 버전 요약 (v0.3.0 ~ v0.5.1)

<details>
<summary>📦 v0.5.1 (2025-10-31) - 예제 개선 및 Redis Operator 전환</summary>

- Bitnami Redis → OpsTree Redis Operator로 예제 교체 (17개 파일)
- 벤더 중립적 오픈소스 차트 사용, Kubernetes Operator 패턴 적용
- 기존 코드와 완전 호환
</details>

<details>
<summary>🚀 v0.5.0 (2025-10-31) - Breaking Changes 및 주요 기능 추가</summary>

**Breaking Changes**:
- Helm Chart 설정: `repo` + `chart` → 단일 `chart` 필드 (`grafana/grafana`)
- CLI 옵션: `--env` → `--profile`, `--sources` → `--source`

**새로운 기능**:
- Hooks 시스템 (pre/post/on_failure 지원)
- OCI Registry 지원 (TrueCharts, GHCR 등)
- 고급 차트 커스터마이징 (`overrides`, `removes`)
- 의존성 관리 (`depends_on`, 토폴로지 정렬)

**문서 및 예제**:
- 38개 실전 예제, 5개 튜토리얼 완성
- API 계약 명세 추가
- 마이그레이션 가이드 제공

**보안 및 성능**:
- `shell=True` 제거 (보안 개선)
- Pydantic 2.7+ 업그레이드
- Python 3.12+ 지원
</details>

<details>
<summary>📊 v0.4.x 시리즈 - 예제 및 개발자 경험 개선</summary>

**v0.4.10**: deps 필드 지원 (앱 그룹 간 의존성 선언)
**v0.4.9**: Glob 패턴 지원 (overrides에 `*.yaml` 등 사용 가능)
**v0.4.8**: Override 디렉토리 자동 감지 및 경고 시스템
**v0.4.7**: sources.yaml 자동 탐색 기능 (monorepo 지원 개선)
**v0.4.6**: prepare 명령어 멱등성 개선 (재실행 안전성)
**v0.4.5**: Kustomize 예제 완성, 예제 커버리지 100% 달성
**v0.4.4**: 워크플로우 예제 4개 추가 (apply, force-update, git, state-management)
**v0.4.3**: 8개 예제 디렉토리 README 추가 (문서 커버리지 100%)
**v0.4.1**: helm_repos dict 포맷 통일, Pydantic shorthand 지원
**v0.4.0**: `--force` 옵션, validate/prepare 버그 수정
</details>

<details>
<summary>🎉 v0.3.0 (2025-10-22) - 메이저 리팩토링 (Breaking Changes)</summary>

**설정 파일 간소화**:
- Apps list → dict 변경 (앱 이름이 키)
- `pull-helm` + `install-helm` → 단일 `helm` 타입 통합
- `specs` 제거 (필드 평탄화)
- 설정 파일 길이 50% 감소

**새로운 기능**:
- HTTP 파일 다운로드 지원
- 의존성 자동 해결 (토폴로지 정렬, 순환 의존성 검출)
- `sbkube migrate` 명령어 (자동 마이그레이션)

**제거된 기능**:
- `copy-*` 타입들 (copy-app, copy-repo, copy-chart, copy-root)
- `render` → `template` 명령어로 대체

**통계**:
- 신규 파일 9개, 추가 라인 ~3,000
- 설정 간소화: 필수 항목 30% 감소, 중첩 레벨 3→2
- 테스트 커버리지 86%
</details>

______________________________________________________________________
