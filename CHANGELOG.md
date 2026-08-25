______________________________________________________________________

## type: Historical Reference audience: Developer topics: [changelog, version-history, releases] llm_priority: low exclude_from_context: true last_updated: 2025-01-04

# Changelog - SBKube

> **참고**: 이 문서의 과거 버전 예제에는 grafana 차트 참조가 포함되어 있습니다. 현재 버전(v0.6.0+)에서는 Grafana, Prometheus 등 오픈소스 차트를 사용합니다.

## [Unreleased]

### 🚀 New Features

**marker 경계 기반 클러스터 설정 상속**

- `apply`, `prepare`, `deploy`는 `.sbkube-workspace` 내부에서만 공용
  클러스터·저장소 설정을 상속한다. 우선순위는 CLI > 앱 > phase > 루트다.
- marker 없는 중첩 앱은 임의의 상위 `sbkube.yaml`을 더 이상 흡수하지 않는다.
  의도한 루트에 `.sbkube-workspace`를 추가하고 공용 설정을 옮기거나,
  앱에 클러스터 설정을 직접 선언해 마이그레이션한다.

**설정 상속 `_parent`** (`sbkube/utils/config_inheritance.py`)

- ✅ **NEW**: 설정 문서가 `_parent:` 로 다른 설정을 상속한다. 부모를 먼저 적재해
  현재 문서를 그 위에 deep merge 한다(자식 우선, 리스트는 교체).
- ✅ **NEW**: 워크스페이스 앵커 `@lib/...` — 상위로 올라가며 찾은
  `.sbkube-workspace` 의 `anchors:` 표로 해석한다.
- ✅ `values:` 만은 교체가 아니라 **부모가 앞**에 붙는다(helm 이 뒤 파일을 나중에
  적용하므로 부모=base, 자식=overlay). 부모의 항목은 **절대경로로 재작성**된다 —
  소비자는 `values` 를 자식의 앱 디렉터리 기준으로 푸는데 부모 파일은 거기 없다.
- ⚠️ **fail closed**: 못 푸는 참조·순환·읽기 실패는 전부 `ParentResolutionError`.
  경고 후 진행하면 문서는 여전히 유효한 채(`values` 기본값이 빈 리스트다)
  차트가 **기본 설정으로** 렌더돼 아무것도 빨갛지 않다.
- ⚠️ 부모 앱에 `overrides`/`manifests` 등 다른 디렉터리 상대 경로 키가 있으면
  거부한다. `values` 만 절대경로화하므로 나머지는 자식 기준으로 잘못 풀린다.
- 발동 조건은 **문서의 종류**(`apiVersion: sbkube/...`)다. 같은 로더를 지나는
  helm values 파일이 우연히 `_parent` 키를 가져도 건드리지 않는다.


## [0.11.0] - 2026-02-25

### 💥 Breaking Changes

- Removed public `sbkube workspace ...` command group from CLI entrypoints.
- Unified workflow is now the official path:
  - `sbkube apply -f sbkube.yaml`
  - `sbkube validate -f sbkube.yaml`

### ✨ Improvements

- Added explicit migration shim command:
  - Running `sbkube workspace ...` now returns migration guidance instead of a generic "No such command".
- Updated core docs to reflect v0.11.0:
  - README version/stable badges
  - Unified config schema wording and priority notes

## [0.9.1] - 2025-12-01

### 🚀 New Features

**Update Management System** (v0.9.1)

- ✅ **NEW**: `sbkube check-updates` command - Check for available Helm chart updates
  - Compares deployed chart versions with latest available versions
  - Visual indicators: 🔴 major, 🟡 minor, 🟢 patch updates
  - Supports semantic version comparison with pre-release and build metadata
  - `--all` flag: Check all Helm releases (not just sbkube-managed apps)
  - `--update-config` flag: Interactive config.yaml update with confirmation
  - LLM-friendly output support via `--format llm`

- ✅ **NEW**: `sbkube status --check-updates` integration
  - Combined status and update checking in single command
  - Displays current deployment status alongside available updates
  - Streamlined workflow for regular maintenance checks

- ✅ **NEW**: Version comparison utilities (`sbkube/utils/version_compare.py`)
  - Semantic version comparison with OUTDATED/SAME/NEWER states
  - Update type detection: major/minor/patch/pre-release
  - Pre-release and build metadata handling
  - Comprehensive test coverage (100%)

- ✅ **NEW**: Enhanced Helm utilities (`sbkube/utils/helm_util.py`)
  - `get_all_helm_releases()`: List all releases across namespaces
  - `search_helm_chart()`: Query Helm repositories for charts
  - `get_latest_chart_version()`: Fetch latest available version
  - Error handling for repository queries

**Usage Examples**:

```bash
# Check updates for sbkube-managed apps
sbkube check-updates

# Check all Helm releases in cluster
sbkube check-updates --all

# Interactive config.yaml update
sbkube check-updates --update-config

# Combined status and update check
sbkube status --check-updates

# LLM-friendly output
sbkube --format llm check-updates
```

**Update Workflow**:

```bash
# 1. Check for updates
sbkube check-updates

# 2. Review changes and update config.yaml
sbkube check-updates --update-config

# 3. Apply updates
sbkube apply
```

**Files Added**:

- `sbkube/commands/check_updates.py` - Update checking command
- `sbkube/utils/version_compare.py` - Version comparison utilities
- `tests/unit/utils/test_version_compare.py` - Version comparison tests
- `tests/unit/utils/test_helm_util.py` - Helm utilities tests

**Files Modified**:

- `sbkube/cli.py` - Registered check-updates command
- `sbkube/commands/status.py` - Added --check-updates flag
- `sbkube/utils/helm_util.py` - Enhanced with release and chart query functions
- `pyproject.toml` - Added `packaging>=25.0` dependency
- `docs/02-features/commands.md` - Documented check-updates command

**Dependencies**:

- Added `packaging>=25.0` for semantic version parsing

**See Also**:

- [commands.md](docs/02-features/commands.md) - Complete command reference

## [0.9.0] - 2025-01-25

### 🎉 Major Feature: Workspace Multi-Phase Deployment

**Workspace** enables orchestrating multi-phase deployments with dependency ordering across different configurations.

### Added

- **Workspace CLI Commands**:
  - `sbkube workspace validate`: Validate workspace.yaml configuration
  - `sbkube workspace graph`: Visualize phase dependency graph
  - `sbkube workspace deploy`: Execute multi-phase deployments
    - Supports `--dry-run`, `--phase <name>`, `--force`, `--skip-validation` options
    - Handles `on_failure` modes: stop, continue, rollback
    - Parallel execution support for independent phases
  - `sbkube workspace status`: Display workspace configuration overview
  - `sbkube workspace history`: View deployment history for workspace phases

- **Phase Dependency Resolution**:
  - Uses Kahn's algorithm for topological sorting
  - Detects circular dependencies
  - Supports parallel execution of independent phases

- **Workspace Configuration**:
  - Full Pydantic model validation for workspace.yaml
  - WorkspaceConfig, PhaseConfig models with strict validation
  - Phase-level sources override support
  - Repository priority: App > Phase > Workspace

- **State Management**:
  - Workspace-level state tracking
  - Deployment history per phase
  - Rollback support at phase level

- **Documentation**:
  - Multi-phase examples: `examples/workspace-multi-phase/`
  - 40+ unit tests for multi-phase commands

## [0.8.1] - 2025-11-25

### Added

- **Documentation as Code**: Added optional `notes` field to all app types for documenting design decisions, deployment order, and operational information
  - Supports multiline YAML with `|` syntax
  - Available in all 9 app types: helm, yaml, action, exec, git, kustomize, http, noop, hook
  - CLI: `sbkube status --show-notes` flag added (foundation for future UI enhancement)
  - Example: `examples/documentation-as-code/`
  - Fully backward compatible (optional field)

### Fixed

- **Test Infrastructure**: Fixed pytest module name collision by renaming duplicate test files in `tests/commands/` to use `_cli` suffix
- **Test Mocking**: Fixed `test_prepare_helm_app_success` test to properly simulate helm chart extraction

## [0.8.0] - 2025-11-13

### 🚨 Breaking Changes

**New Chart Path Structure to Prevent Collisions** (v0.8.0)

- ⚠️ **BREAKING**: Chart path structure changed from `.sbkube/charts/{chart-name}/` to
  `.sbkube/charts/{repo}/{chart-name}-{version}/`
- ✅ **FIXED**: Charts from different repos with same name no longer collide (e.g., `grafana/loki` vs
  `my-company/redis`)
- ✅ **FIXED**: Same chart with different versions can now coexist (e.g., `redis:18.0.0` and `redis:19.0.0`)
- ✅ **NEW**: Automatic legacy path detection with migration guide

**Migration Required**:

```bash
# Remove old charts and re-download
rm -rf .sbkube/charts
sbkube prepare --force
```

**New Path Examples**:

```
Before (v0.7.x):
.sbkube/charts/redis/           # ❌ Collision risk
.sbkube/charts/grafana/         # ❌ No version tracking

After (v0.8.0):
.sbkube/charts/grafana/loki-18.0.0/         # ✅ No collision
.sbkube/charts/my-company/redis-1.0.0/       # ✅ Different repo
.sbkube/charts/grafana/loki-19.0.0/         # ✅ Different version
.sbkube/charts/grafana/grafana-latest/       # ✅ Version tracked
```

**What Changed**:

- `HelmApp.get_chart_path()`: New method to generate versioned paths
- `HelmApp.get_version_or_default()`: Returns version or "latest"
- `prepare_helm_app()`: Saves charts to `{repo}/{chart-name}-{version}/`
- `prepare_oci_chart()`: Same path structure for OCI registries
- `build_helm_app()`: Reads from new path structure
- Legacy path detection: Automatic warning for v0.7.x charts

**Files Modified**:

- [sbkube/models/config_model.py](sbkube/models/config_model.py:746-784) - Added `get_chart_path()`,
  `get_version_or_default()`
- [sbkube/commands/prepare.py](sbkube/commands/prepare.py:110-192) - New path structure for OCI charts
- [sbkube/commands/prepare.py](sbkube/commands/prepare.py:302-384) - New path structure for Helm charts
- [sbkube/commands/build.py](sbkube/commands/build.py:50-98) - Legacy path detection
- [tests/unit/test_chart_path_v080.py](tests/unit/test_chart_path_v080.py) - Comprehensive collision prevention tests

**See Also**:

- [docs/05-best-practices/directory-structure.md](docs/05-best-practices/directory-structure.md) - Migration guide

### ✨ New Features

**PV/PVC Validation for Manual Provisioning** (v0.8.0)

- ✅ **NEW**: `sbkube validate` now checks PV requirements for apps using `kubernetes.io/no-provisioner` StorageClass
- ✅ **NEW**: Automatic detection of missing PVs before deployment
- ✅ **NEW**: `--skip-storage-check` option to bypass PV validation
- ✅ **NEW**: `--strict-storage-check` option to fail on missing PVs (default: warning only)
- ✅ **NEW**: Comprehensive storage management documentation and examples

**Problem Solved**:

```bash
# Before v0.8.0: PVC stays Pending, hard to diagnose
$ sbkube apply
# ... deployment succeeds but PVC stuck in Pending
$ kubectl get pvc
NAME              STATUS    VOLUME   CAPACITY
postgresql-data   Pending            # ❌ No guidance on why

# After v0.8.0: Early validation catches missing PVs
$ sbkube validate
❌ 스토리지 검증 실패:
  ✗ postgresql: postgresql-hostpath (8Gi)

💡 PV 생성 방법:
  1. 수동 생성: kubectl apply -f pv.yaml
  2. Dynamic Provisioner 설치: local-path-provisioner
  3. 검증 건너뛰기: sbkube validate --skip-storage-check
```

**Features**:

- **Validation**: Detects apps requiring manual PVs by checking for `kubernetes.io/no-provisioner` StorageClass
- **Cluster Check**: Queries cluster for available PVs matching requirements (StorageClass, size, status)
- **Flexible Patterns**: Supports common Helm chart patterns (persistence, primary.persistence)
- **Size Comparison**: Intelligent size matching (Gi, G, Mi, M units)
- **Graceful Degradation**: Skips validation if cluster unavailable (with warning)

**New CLI Options**:

```bash
# Skip storage validation
sbkube validate --skip-storage-check

# Strict mode (fail on missing PVs)
sbkube validate --strict-storage-check

# Custom kubeconfig
sbkube validate --kubeconfig ~/.kube/dev-cluster
```

**Files Added**:

- [sbkube/validators/storage_validators.py](sbkube/validators/storage_validators.py) - PV validation logic
- [tests/unit/validators/test_storage_validators.py](tests/unit/validators/test_storage_validators.py) - Comprehensive
  tests
- [docs/05-best-practices/storage-management.md](docs/05-best-practices/storage-management.md) - Storage management
  guide
- [docs/07-troubleshooting/storage-issues.md](docs/07-troubleshooting/storage-issues.md) - Troubleshooting guide
- [examples/storage-management/manual-pv-hostpath/](examples/storage-management/manual-pv-hostpath/) - Working example

**Files Modified**:

- [sbkube/commands/validate.py](sbkube/commands/validate.py) - Integrated storage validation

**See Also**:

- [docs/05-best-practices/storage-management.md](docs/05-best-practices/storage-management.md) - Best practices
- [docs/07-troubleshooting/storage-issues.md](docs/07-troubleshooting/storage-issues.md) - Common issues

______________________________________________________________________

## [0.7.2] - 2025-01-10

### 🐛 Bug Fixes

**Base Directory Consistency Across Commands** (2025-01-10)

- ✅ **FIXED**: Base directory mismatch between prepare and build/deploy/template commands
- ✅ **FIXED**: Commands now consistently use sources.yaml location for `.sbkube` directory
- ✅ **IMPROVED**: Running from project root with `--app-dir` subdirectory now works correctly
- ✅ **NEW**: Automatic sources.yaml discovery by searching upward from app config directory
- ✅ **NEW**: Fallback to base_dir if sources.yaml not found (backward compatibility)

**Problem Fixed**:

```bash
# Before: Commands looked in different locations
prepare: ph2_data/.sbkube/charts/memcached  ✅ (sources.yaml location)
build:   .sbkube/charts/memcached           ❌ (base_dir)

# After: All commands use same location
prepare: ph2_data/.sbkube/charts/memcached  ✅
build:   ph2_data/.sbkube/charts/memcached  ✅
deploy:  ph2_data/.sbkube/charts/memcached  ✅
```

**Technical Details**:

- Added `--source` option to build.py, deploy.py, template.py (default: "sources.yaml")
- Implemented sources.yaml discovery logic matching prepare.py behavior
- All commands now resolve `.sbkube` location based on sources.yaml parent directory
- Supports multi-environment setups with sources.yaml in subdirectories

**Files Modified**:

- [sbkube/commands/build.py](sbkube/commands/build.py) - Added sources.yaml discovery
- [sbkube/commands/deploy.py](sbkube/commands/deploy.py) - Added sources.yaml discovery
- [sbkube/commands/template.py](sbkube/commands/template.py) - Added sources.yaml discovery

**Testing**:

```bash
cd /project_root
sbkube apply --app-dir ph2_data/app_100_data_memory
# ✅ All commands now use ph2_data/.sbkube/
```

______________________________________________________________________

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
- `docs/03-configuration/config-schema.md` - Complete sources.yaml documentation
- `examples/cluster-global-values/` - Working examples

**See:** [config-schema.md](docs/03-configuration/config-schema.md)

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

### 🔧 Improvements

**Chart Directory Structure Simplification** (2025-01-10)

- ✅ **IMPROVED**: Simplified chart directory structure from `.sbkube/charts/{name}/{name}/` to `.sbkube/charts/{name}/`
- ✅ **IMPROVED**: More accurate output messages showing actual chart destination paths
- ✅ **IMPROVED**: Clearer directory structure aligning with user expectations
- ✅ **NEW**: Legacy path detection with helpful migration guidance
  - Automatically detects charts from v0.7.0 or earlier
  - Provides step-by-step migration instructions when legacy paths are found
  - Shows clear error messages with documentation links
  - Available in `build` and `deploy` commands

**Migration**:

```bash
# After upgrading to v0.7.1+
rm -rf .sbkube/charts/
sbkube prepare
```

**Technical Details**:

- Changed `helm pull --untardir` target from `charts_dir / chart_name` to `charts_dir`
- Helm automatically creates `{chart_name}/` subdirectory, resulting in single-level structure
- Updated [sbkube/commands/prepare.py](sbkube/commands/prepare.py), [build.py](sbkube/commands/build.py),
  [template.py](sbkube/commands/template.py), [deploy.py](sbkube/commands/deploy.py)

**See:** [directory-structure.md](docs/05-best-practices/directory-structure.md) - Technical background section

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

- ✅ **NEW**: [config-schema.md](docs/03-configuration/config-schema.md) - Complete sources.yaml reference
- ✅ **UPDATED**: [PRODUCT.md](PRODUCT.md) as comprehensive root documents (SSOT)
- ✅ **UPDATED**: [CLAUDE.md](CLAUDE.md) with architecture patterns and development commands
- ✅ **SYNCED**: All documentation layers aligned with PRODUCT.md and ARCHITECTURE.md

______________________________________________________________________

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

## 과거 버전 요약

<details>
<summary>📦 v0.6.x (2025-10-31) — App-Group Dependencies, State Management, Code Quality</summary>

**v0.6.1**: Linting/formatting cleanup (63 import fixes, ruff/mypy/bandit passes), help 화면 카테고리 그룹화

**v0.6.0**: App-Group dependency validation (`deps` field), deployment checker enhancement with namespace auto-detection, validate command `--app-dir` option, doctor command safety improvements, removed deprecated `sbkube cluster` and `sbkube state` commands

</details>

<details>
<summary>📦 v0.5.x (2025-10-31) — Breaking Changes, Hooks System, OCI Support</summary>

**v0.5.1**: Redis → OpsTree Redis Operator 예제 전환

**v0.5.0** (**Breaking**): Helm `repo`+`chart` → 단일 `chart` 필드, `--env`→`--profile`, Hooks 시스템, OCI Registry 지원, 고급 차트 커스터마이징, 의존성 관리, 38개 예제, `shell=True` 제거

</details>

<details>
<summary>📦 v0.4.x — Examples, DX Improvements</summary>

v0.4.10: deps 필드, v0.4.9: Glob 패턴, v0.4.8: Override 자동 감지, v0.4.7: sources.yaml 자동 탐색, v0.4.6: prepare 멱등성, v0.4.5: Kustomize 예제 100%, v0.4.4: 워크플로우 예제, v0.4.3: README 커버리지 100%, v0.4.1: helm_repos dict 통일, v0.4.0: --force 옵션

</details>

<details>
<summary>📦 v0.3.0 (2025-10-22) — Major Refactoring (Breaking)</summary>

Apps list→dict, `pull-helm`+`install-helm`→단일 `helm`, `specs` 제거, HTTP 다운로드, 의존성 자동 해결, `sbkube migrate`, `copy-*` 제거, `render`→`template`, 설정 길이 50% 감소

</details>

---
