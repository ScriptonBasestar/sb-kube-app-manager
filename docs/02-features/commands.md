______________________________________________________________________

## type: API Reference audience: End User topics: [commands, cli, workflow, deployment, kubernetes] llm_priority: high last_updated: 2025-01-06

# 📋 SBKube 명령어 상세 가이드

> **주의**: 이 문서는 명령어 사용자 가이드입니다. 기술적 구현 상세는 [ARCHITECTURE.md](../../docs/10-modules/sbkube/ARCHITECTURE.md)를 우선
> 참조하세요.

## TL;DR

- **Purpose**: Complete reference for all SBKube CLI commands and their options
- **Version**: v0.7.0 (개발 중), v0.6.0 (안정)
- **Key Points**:
  - Main workflow: `sbkube apply` (runs prepare→build→template→deploy)
  - Quick start: `sbkube init` → `sbkube doctor` → `sbkube apply`
  - Validation: `sbkube validate` for config checks, `--dry-run` for safe testing
  - Troubleshooting: `sbkube doctor` for comprehensive system diagnostics
  - All commands support `--format` option for LLM-friendly output
- **Quick Reference**: See command table below
- **Related**:
  - ****상위 문서**: [ARCHITECTURE.md](../../ARCHITECTURE.md) - 아키텍처 (어떻게)
  - **제품 개요**: [PRODUCT.md](../../PRODUCT.md) - 제품 정의 (무엇을, 왜)
  - **설정 참조**: [config-schema.md](../03-configuration/config-schema.md)
  - **LLM 통합**: [llm-friendly-output.md](llm-friendly-output.md)

## 🚀 Quick Reference Table

| Command | Category | Purpose | Key Options | |---------|----------|---------|-------------| | **apply** ⭐ | 통합 |
Complete workflow (prepare→build→template→deploy) | --dry-run, --profile, --from-step, --resume | | **prepare** | 핵심 |
Download sources (Helm charts, Git repos) | --app, --force | | **build** | 핵심 | Build and customize applications |
--app, overrides support | | **template** | 핵심 | Render Kubernetes manifests | --app, --output-dir | | **deploy** | 핵심 |
Deploy to k3s cluster | --app, --dry-run | | **init** | 유틸리티 | Initialize project structure | --template, --force | |
**validate** | 유틸리티 | Validate configuration files | --strict, --app-dir | | **doctor** | 유틸리티 | System diagnostics |
--detailed, --check | | **status** ⭐ | 상태관리 | Check deployment status (v0.6.0+) | --by-group, --managed, --unhealthy | |
**history** | 상태관리 | View deployment history (v0.6.0+) | --show, --diff, --values-diff | | **rollback** | 상태관리 |
Rollback to previous revision (v0.6.0+) | --dry-run, --force | | **upgrade** | 관리 | Upgrade Helm releases | --app | |
**delete** | 관리 | Delete deployed resources | --app, --dry-run, --skip-not-found | | **check-updates** ⭐ | 관리 | Check for available chart updates (v0.9.1+) | --all, --update-config | | **version** | 유틸리티 | Show version
info | |

### 워크플로우별 명령어 조합

```bash
# 📦 처음 시작하기
sbkube init                    # 1. 프로젝트 초기화
sbkube doctor                  # 2. 환경 진단
sbkube apply --dry-run         # 3. 배포 계획 확인
sbkube apply                   # 4. 실제 배포

# 🔄 일상적인 배포
sbkube validate               # 1. 설정 검증
sbkube apply --profile production  # 2. 프로덕션 배포

# 🐛 문제 해결
sbkube doctor --detailed      # 상세 진단
sbkube status --unhealthy     # 문제 리소스 확인

# 🔄 업데이트 관리 (v0.9.1+)
sbkube check-updates          # 사용 가능한 차트 업데이트 확인
sbkube check-updates --update-config  # config.yaml 자동 업데이트
sbkube status --check-updates # 상태 확인과 동시에 업데이트 체크

# 🧹 정리 및 재배포
sbkube delete --dry-run       # 삭제 대상 확인
sbkube delete && sbkube apply # 재배포
```

## Common Options

### 전역 옵션 (All commands)

- `--kubeconfig PATH`: Kubernetes config file (env: KUBECONFIG)
- `--context NAME`: Kubernetes context to use
- `--namespace NS`: Default namespace (env: KUBE_NAMESPACE)
- `-v, --verbose`: Enable verbose logging
- `--format {human|llm|json|yaml}`: Output format (default: human)
- `--help`: Show command help

### 공통 워크플로우 옵션

- `--app-dir PATH`: Configuration directory (default: current directory)
- `--base-dir PATH`: Working directory (default: .)
- `--app NAME`: Process specific app only
- `--config-file NAME`: Custom config filename

### 배포 관련 옵션

- `--dry-run`: Preview changes without applying
- `--profile NAME`: Use specific configuration profile (development/staging/production)
- `--quiet`: Minimal output (suppress progress, show only results)

## Detailed Command Reference

### 🔄 Core Workflow Commands

#### apply ⭐

**Purpose**: Execute complete deployment workflow (prepare → build → template → deploy)

**Usage**: `sbkube apply [OPTIONS]`

**Unique Options**:

- `--from-step {prepare|build|template|deploy}`: Start from specific step
- `--to-step {prepare|build|template|deploy}`: End at specific step
- `--only STEP`: Execute only specific step
- `--continue-from STEP`: Restart from specific step
- `--retry-failed`: Retry only failed apps
- `--resume`: Auto-resume from last failure point
- `--skip-deps-check`: Skip app group dependency validation

**Examples**:

```bash
# Standard deployment
sbkube apply

# Environment-specific
sbkube apply --profile production

# Step control
sbkube apply --from-step template  # Start from template
sbkube apply --only build          # Only run build

# Recovery
sbkube apply --resume              # Auto-resume from failure
sbkube apply --retry-failed        # Retry failed apps only
```

**Features**:

- Automatic 4-step execution
- Smart restart from failure point
- Profile-based environment management
- Real-time progress tracking
- State saved in `.sbkube/runs/`
- Auto dependency validation via `deps` field

**Error Handling** (v0.6.1+): Enhanced error messages with solutions for:

- DatabaseAuthenticationError
- DatabaseConnectionError
- HelmReleaseError
- KubernetesConnectionError
- NamespaceNotFoundError

**See Also**: prepare, build, template, deploy

______________________________________________________________________

#### prepare

**Purpose**: Download and prepare sources (Helm charts, Git repositories)

**Usage**: `sbkube prepare [OPTIONS]`

**Unique Options**:

- `--source FILE`: Source config file (default: sources.yaml)
- `--force`: Force re-download existing resources

**Idempotency** (v0.4.6+):

- Default: Skip existing charts/repos
- `--force`: Delete and re-download
- Safe for re-execution

**Examples**:

```bash
sbkube prepare               # Download all sources (idempotent)
sbkube prepare --app nginx   # Specific app
sbkube prepare --force       # Force re-download
```

**Creates**: `.sbkube/charts/`, `.sbkube/repos/`

______________________________________________________________________

#### build

**Purpose**: Build deployment-ready artifacts from prepared sources

**Usage**: `sbkube build [OPTIONS]`

**Override System**:

- Overrides must be explicitly listed in `config.yaml`
- Supports file replacement and additions
- Glob patterns supported (v0.4.9+)

**Examples**:

```bash
sbkube build                 # Build all apps
sbkube build --app database  # Specific app
```

**Important**: Override files in `overrides/` directory are NOT auto-discovered. Must be listed in `config.yaml`:

```yaml
apps:
  myapp:
    overrides:
      - templates/*.yaml     # Glob pattern
      - files/config.txt     # Explicit file
```

**Creates**: `.sbkube/build/`

**See Also**: [config-schema.md](../03-configuration/config-schema.md) for override details

______________________________________________________________________

#### template

**Purpose**: Render Helm charts and YAML to final manifests

**Usage**: `sbkube template [OPTIONS]`

**Unique Options**:

- `--output-dir DIR`: Output directory (default: .sbkube/rendered)

**Examples**:

```bash
sbkube template                         # Render all
sbkube template --namespace production  # With namespace
sbkube template --output-dir /tmp/out  # Custom output
```

**Creates**: `.sbkube/rendered/`

**Automatic Manifest Cleanup** (v0.7.0+):

Template command automatically removes server-managed metadata fields that may cause deployment failures.

**Applies to**:

- Helm apps (all rendered manifests)
- YAML apps (all manifest files)
- HTTP apps (YAML files only, non-YAML files unchanged)

**Removed fields**:

- `metadata.managedFields` (Server-Side Apply tracking)
- `metadata.creationTimestamp` (auto-generated timestamp)
- `metadata.resourceVersion` (cluster resource version)
- `metadata.uid` (unique identifier)
- `metadata.generation` (modification counter)
- `metadata.selfLink` (deprecated API link)
- `status` (entire section, managed by controllers)

This prevents common errors like:

```text
Error: admission webhook denied the request: metadata.managedFields is not allowed
```

______________________________________________________________________

#### deploy

**Purpose**: Deploy applications to Kubernetes cluster

**Usage**: `sbkube deploy [OPTIONS]`

**Supports**:

- `helm`: Helm chart installation
- `yaml`: kubectl apply
- `action`: Custom scripts
- `exec`: Arbitrary commands

**Examples**:

```bash
sbkube deploy             # Deploy all
sbkube deploy --dry-run   # Preview only
sbkube deploy --app web   # Specific app
```

### 📊 State Management Commands (v0.6.0+)

#### status ⭐

**Purpose**: Comprehensive cluster and deployment status

**Usage**: `sbkube status [APP_GROUP] [OPTIONS]`

**Unique Options**:

- `--by-group`: Group by app-groups
- `--managed`: Show only sbkube-managed apps
- `--unhealthy`: Show only problematic resources
- `--deps`: Visualize dependency tree (Phase 6)
- `--health-check`: Detailed pod health (Phase 7)
- `--check-updates`: Check for available chart updates (v0.9.1+)
- `--refresh`: Force cache refresh
- `--watch`: Auto-refresh every 10s

**Cache Files** (v0.6.2+):

Single shared base cache file for all views:

```
.sbkube/cluster_status/
└── {context}_{cluster}.yaml
    ├── helm_releases: [with labels for app-group classification]
    ├── nodes: [cluster node status]
    ├── namespaces: [list of namespaces]
    └── ...
```

**App-group Classification** (v0.6.2+):

Releases are classified by app-group using priority:

1. **Label** (recommended): `sbkube.io/app-group=app_000_infra_network`

   - Set at Helm release install time
   - Most reliable and explicit

1. **State DB**: Previous deployment records from sbkube

   - Falls back if label not present

1. **Name pattern**: Release name like `app_000_...`

   - Auto-extracted from name

1. **Namespace pattern**: Namespace like `app_000_...`

   - Last resort fallback

**Example**: Deploy with label

```bash
helm install myapp chart/ \
  --set-string='podAnnotations.sbkube\.io/app-group=app_000_infra_network'
```

Cache expires in 5 minutes (TTL-based). Use `--refresh` to force update.

**Examples**:

```bash
sbkube status                           # Overall status
sbkube status --by-group                # Grouped view
sbkube status --unhealthy               # Problems only
sbkube status app_000_infra_network     # Specific group
sbkube status --deps                    # Dependency tree

# Force refresh and create new cache
sbkube status --by-group --refresh
```

**Replaces**: `sbkube cluster status` (deprecated)

______________________________________________________________________

#### history

**Purpose**: View and compare deployment history

**Usage**: `sbkube history [APP_GROUP] [OPTIONS]`

**Unique Options**:

- `--show ID`: Show deployment details
- `--diff ID1,ID2`: Compare deployments (Phase 5)
- `--values-diff ID1,ID2`: Compare Helm values (Phase 5)
- `--cluster NAME`: Filter by cluster
- `--limit N`: Limit results (default: 50)

**Examples**:

```bash
sbkube history                          # Recent deployments
sbkube history --show dep_123           # Deployment details
sbkube history --diff dep_123,dep_456   # Compare deployments
sbkube history --values-diff old,new    # Compare Helm values
```

**Replaces**: `sbkube state list/show` (deprecated)

______________________________________________________________________

#### rollback

**Purpose**: Rollback to previous deployment

**Usage**: `sbkube rollback <DEPLOYMENT_ID> [OPTIONS]`

**Unique Options**:

- `--list`: Show rollback candidates
- `--scope {app|phase|all}`: Rollback scope (v0.11.0+)
  - `app`: Rollback specific app(s) only (default)
  - `phase`: Rollback all apps deployed in a specific phase
  - `all`: Rollback entire deployment (all apps)
- `--phase/-p`: Phase name to rollback (requires `--scope=phase`)
- `--app/-a`: Specific app(s) to rollback (can be specified multiple times)
- `--target`: Specific deployment ID to rollback to

**Examples**:

```bash
# List rollback candidates
sbkube rollback --list --cluster prod --namespace kube-system

# Rollback specific app only (scope=app, default)
sbkube rollback dep_123 --app traefik --dry-run

# Rollback entire phase (scope=phase)
sbkube rollback dep_123 --scope phase --phase p1-infra

# Rollback entire deployment (scope=all)
sbkube rollback dep_123 --scope all

# Force rollback (ignore warnings)
sbkube rollback dep_123 --force
```

**Replaces**: `sbkube state rollback` (deprecated)

### 🛠️ Utility Commands

#### init

**Purpose**: Initialize new SBKube project

**Usage**: `sbkube init [OPTIONS]`

**Unique Options**:

- `--template {basic|web-app|microservice}`: Project template (default: basic)
- `--name NAME`: Project name (default: directory name)
- `--non-interactive`: Skip prompts

**Creates**: `config.yaml`, `sources.yaml`, `.sbkube/`

______________________________________________________________________

#### validate

**Purpose**: Validate configuration files

**Usage**: `sbkube validate [FILE] [OPTIONS]`

**Unique Options**:

- `--schema-type {config|sources}`: Schema type (auto-detected)
- `--schema-path PATH`: Custom schema file

**Examples**:

```bash
sbkube validate                         # Current directory
sbkube validate config.yaml             # Specific file
sbkube validate --app-dir redis         # App directory
```

**Validates**:

- JSON schema compliance
- Pydantic model validation
- Required fields
- App group dependencies

______________________________________________________________________

#### doctor

**Purpose**: Comprehensive system diagnostics

**Usage**: `sbkube doctor [OPTIONS]`

**Unique Options**:

- `--detailed`: Verbose diagnostics
- `--check NAME`: Run specific check only

**Checks**:

- Kubernetes connectivity
- Helm installation
- Configuration validity
- Permissions and resources

**Examples**:

```bash
sbkube doctor                           # Basic diagnostics
sbkube doctor --detailed                # Verbose output
sbkube doctor --check k8s_connectivity  # Specific check
```

______________________________________________________________________

#### version

**Purpose**: Show SBKube version

**Usage**: `sbkube version`

### 🔧 Management Commands

#### upgrade

**Purpose**: Upgrade Helm releases

**Usage**: `sbkube upgrade [OPTIONS]`

**Supports**: Helm releases only

**Examples**:

```bash
sbkube upgrade                # Upgrade all
sbkube upgrade --app database # Specific app
```

______________________________________________________________________

#### delete

**Purpose**: Delete deployed resources

**Usage**: `sbkube delete [OPTIONS]`

**Unique Options**:

- `--skip-not-found`: Ignore missing resources

**Supports**:

- `helm`: helm uninstall
- `yaml`: kubectl delete
- `action`: Custom uninstall scripts

**Examples**:

```bash
sbkube delete --dry-run        # Preview deletion
sbkube delete --app nginx      # Delete specific app
sbkube delete --skip-not-found # Ignore if not found
```

______________________________________________________________________

#### check-updates ⭐

**Purpose**: Check for available Helm chart updates

**Usage**: `sbkube check-updates [OPTIONS]`

**Version**: Added in v0.9.1

**Unique Options**:

- `--all`: Check all Helm releases in cluster (not just sbkube-managed apps)
- `--update-config`: Update config.yaml with latest versions (prompts for confirmation)

**Features**:

- Compares currently deployed chart versions with latest available in repositories
- Semantic version comparison (identifies major/minor/patch updates)
- Shows upgrade commands for easy updating
- Can automatically update config.yaml with latest versions
- Supports both sbkube-managed apps and all cluster Helm releases

**Output Information**:

- Current version → Latest version
- Update type (Major 🔴 / Minor 🟡 / Patch 🟢)
- Upgrade command suggestion
- Summary of updates available

**Examples**:

```bash
# Check sbkube-managed apps for updates
sbkube check-updates

# Check all Helm releases in cluster
sbkube check-updates --all

# Update config.yaml with latest versions (interactive)
sbkube check-updates --update-config

# Integrate with status command
sbkube status --check-updates

# LLM-friendly output
sbkube check-updates --format llm
```

**Integration**:

The `check-updates` functionality is also available as part of the `status` command:

```bash
# Check status and available updates in one command
sbkube status --check-updates
```

**Version Comparison Logic**:

- **Major update** (🔴): Breaking changes expected (e.g., 1.x.x → 2.x.x)
- **Minor update** (🟡): New features, backward compatible (e.g., 1.0.x → 1.1.x)
- **Patch update** (🟢): Bug fixes only (e.g., 1.0.0 → 1.0.1)

## Advanced Usage Patterns

### Environment Management

```bash
# Development → Staging → Production
sbkube apply --profile development
sbkube apply --profile staging
sbkube apply --profile production
```

### Failure Recovery

```bash
# Auto-resume from failure
sbkube apply --resume

# Retry only failed apps
sbkube apply --retry-failed

# Start from specific step
sbkube apply --continue-from template
```

### Dependency Management

Apps can declare dependencies via `deps` field:

```yaml
apps:
  - name: app_020_backend
    deps:
      - app_000_network
      - app_010_database
```

Apply automatically validates dependencies are deployed.

## Command Output Formats

All commands support multiple output formats via `--format`:

- `human` (default): Rich formatted output for terminals
- `llm`: Structured text optimized for AI parsing
- `json`: Machine-readable JSON
- `yaml`: YAML format

Example:

```bash
sbkube status --format llm
sbkube history --format json
```

See [llm-friendly-output.md](llm-friendly-output.md) for details.

## Deprecated Commands

The following will be removed in v1.0.0:

| Old (Deprecated) | New (Recommended) | |-----------------|-------------------| | `sbkube cluster status` |
`sbkube status` | | `sbkube state list` | `sbkube history` | | `sbkube state show <id>` | `sbkube history --show <id>` |
| `sbkube state rollback <id>` | `sbkube rollback <id>` |

______________________________________________________________________

## Related Documentation

- ****상위 문서**: [ARCHITECTURE.md](../../ARCHITECTURE.md) - 아키텍처 (어떻게)
- **제품 개요**: [PRODUCT.md](../../PRODUCT.md) - 제품 정의 (무엇을, 왜)
- **기능 명세**: [../00-product/product-spec.md](../00-product/product-spec.md) - 전체 기능 상세
- **설정 참조**: [config-schema.md](../03-configuration/config-schema.md) - 설정 파일 스키마
- **LLM 통합**: [llm-friendly-output.md](llm-friendly-output.md) - LLM 친화적 출력
- **문제 해결**: [../07-troubleshooting/deployment-failures.md](../07-troubleshooting/deployment-failures.md) - 배포 문제 해결

______________________________________________________________________

**문서 버전**: 1.1 **마지막 업데이트**: 2025-01-06 **담당자**: archmagece@users.noreply.github.com
