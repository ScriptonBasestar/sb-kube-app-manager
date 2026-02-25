---
type: Technical Documentation
audience: Developer
topics: [architecture, design, patterns, modules, implementation]
llm_priority: medium
last_updated: 2026-02-25
---

# SBKube 모듈 아키텍처

> **주의**: 이 문서는 SBKube 모듈의 상세 아키텍처 설계를 다룹니다.
> 전체 아키텍처 개요는 [ARCHITECTURE.md](../../../ARCHITECTURE.md)를 우선 참조하세요.

## TL;DR
- **Purpose**: Technical architecture and design patterns for SBKube module implementation
- **Version**: v0.11.0
- **Key Points**:
  - Monolithic architecture with clear layer separation (CLI→Command→Model→State→External)
  - EnhancedBaseCommand pattern for command extensibility
  - Pydantic 2.7.1+ with `extra="forbid"` for strong typing and validation
  - 9 app types via discriminated union (helm, yaml, action, exec, git, kustomize, http, noop, hook)
  - Unified config format (`sbkube.yaml`, apiVersion: sbkube/v1) + legacy backward compatibility
  - SQLAlchemy for state persistence (deployments, resources, Helm releases, workspaces)
  - OutputManager + OutputFormatter for dual-layer output (human, llm, json, yaml)
  - Comprehensive exception hierarchy (20+ exception types)
  - Retry pattern with exponential backoff for external tool calls
- **Quick Reference**: Layer architecture diagram shows CLI→Command→Model→State flow
- **Related**: [ARCHITECTURE.md](../../../ARCHITECTURE.md), [MODULE.md](MODULE.md), [API_CONTRACT.md](API_CONTRACT.md)

## 개요

이 문서는 SBKube 모듈의 상세한 아키텍처 설계를 다룹니다. 전체 시스템 아키텍처 요약은 [ARCHITECTURE.md](../../../ARCHITECTURE.md)를, 

## 아키텍처 원칙

### 1. 단순성 (Simplicity)

- 모놀리식 구조로 복잡성 최소화
- 명확한 계층 분리
- 직관적인 명령어 체계

### 2. 확장성 (Extensibility)

- EnhancedBaseCommand 패턴으로 새 명령어 독립적 구현
- Discriminated Union으로 새 앱 타입 쉽게 추가
- Hook 시스템으로 워크플로우 커스터마이징

### 3. 안정성 (Reliability)

- 강타입 검증 (Pydantic `extra="forbid"`)
- 포괄적 예외 계층 (20+ exception types)
- 재시도 로직 (exponential backoff + jitter)
- 상태 관리 및 롤백

### 4. 사용자 경험 (User Experience)

- Rich 콘솔 UI
- 실시간 진행 상태 표시
- Dry-run 모드 지원
- Multi-format output (human, llm, json, yaml)
- 자동 에러 수정 프롬프트

## 레이어 아키텍처

```
┌────────────────────────────────────────────────────────┐
│                   CLI Layer                            │
│  (Click Framework + SbkubeGroup)                       │
│  - 명령어 파싱 및 라우팅                                 │
│  - 전역 옵션 처리 (kubeconfig, context, namespace)    │
│  - 도구 검증 (kubectl, helm 설치 확인)                  │
│  - 전역 예외 처리 + 자동 수정 프롬프트                   │
└──────────────────┬─────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────┐
│                Command Layer (16 commands)              │
│  (EnhancedBaseCommand Pattern)                         │
│  - 명령어별 비즈니스 로직 (prepare, build, etc.)        │
│  - Unified + Legacy 설정 로딩 및 검증                   │
│  - 앱별 처리 로직 (AppConfig 타입별 분기)               │
│  - Hook 실행 (command-level + app-level)                │
└──────────────────┬─────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────┐
│              Model & Validation Layer                  │
│  (Pydantic 2.7.1+ Models)                              │
│  - UnifiedConfig (sbkube.yaml) - 통합 설정              │
│  - SBKubeConfig + SourceScheme - 레거시 설정            │
│  - AppConfig: 9종 Discriminated Union                  │
│  - Hook System: ManifestsHookTask, InlineHookTask, ... │
│  - ConfigBaseModel + InheritableConfigModel            │
└──────────────────┬─────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────┐
│          Infrastructure Layer                          │
│  (Utils 45개, State 5개, Validators 7개)               │
│  - Helm/kubectl/Git 연동 + retry (utils/)              │
│  - 배포 상태 관리 (state/ - SQLAlchemy)                 │
│  - 사전/사후 검증 (validators/)                         │
│  - 출력 관리 (OutputManager + OutputFormatter)          │
│  - 에러 분류/제안 (error_classifier, error_suggestions)│
│  - 성능 프로파일링 (perf.py - SBKUBE_PERF=1)           │
└──────────────────┬─────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────┐
│           External Dependencies                        │
│  - Helm CLI v3.x (with retry)                          │
│  - kubectl (with retry)                                │
│  - Git (with retry)                                    │
│  - Kubernetes API (via Python client)                 │
└────────────────────────────────────────────────────────┘
```

## 핵심 컴포넌트

### 1. CLI 엔트리포인트 (cli.py)

#### SbkubeGroup 클래스

```python
class SbkubeGroup(click.Group):
    """SBKube CLI 그룹 with categorized help display."""

    COMMAND_CATEGORIES = {
        "핵심 워크플로우": ["prepare", "build", "template", "deploy"],
        "통합 명령어": ["apply"],
        "상태 관리": ["status", "history", "rollback"],
        "업그레이드/삭제": ["upgrade", "delete", "check-updates"],
        "유틸리티": ["init", "validate", "doctor", "version"],
    }

    def invoke(self, ctx: click.Context):
        if ctx.invoked_subcommand:
            # kubectl/helm 필요한 명령어에 대해 사전 검증
            if ctx.invoked_subcommand in commands_requiring_kubectl_connection:
                check_kubectl_installed_or_exit(...)
            if ctx.invoked_subcommand in commands_requiring_helm:
                check_helm_installed_or_exit()
        super().invoke(ctx)
```

**책임**:

- 전역 옵션 파싱 (--kubeconfig, --context, --namespace, --format, --verbose, --profile)
- 카테고리별 명령어 도움말 표시 (5개 카테고리, 이모지 라벨)
- 명령어별 필수 도구 검증 (kubectl, helm)
- `main_with_exception_handling()`: 전역 예외 처리 + 자동 수정 프롬프트

### 2. Command Layer (commands/ — 16 commands)

#### EnhancedBaseCommand 패턴

```python
class EnhancedBaseCommand:
    """Enhanced base class for all commands with validation support."""

    def __init__(
        self,
        base_dir: str = ".",
        app_config_dir: str = "config",
        cli_namespace: str | None = None,
        config_file_name: str | None = None,
        sources_file: str = "sources.yaml",
        validate_on_load: bool = True,
        use_inheritance: bool = True,
        output_format: str = "human",
    ):
        self.formatter = OutputFormatter(output_format)
        self.config_manager = ConfigManager(...)
        self.hook_executor = HookExecutor(...)
```

**핵심 메서드**:

| Method | Description |
|--------|-------------|
| `load_config()` | config.yaml 로딩 + Pydantic 검증 |
| `load_sources()` | sources.yaml 로딩 + 검증 |
| `parse_apps()` | 앱 필터링 (타입별, 이름별) |
| `get_namespace()` | 네임스페이스 결정 (CLI > App > Global) |
| `process_apps_with_stats()` | 앱 목록 처리 + 통계 출력 |
| `execute_command_hook()` | 명령어 수준 전역 훅 실행 |
| `execute_app_hook()` | 앱별 훅 실행 |
| `resolve_cluster_configuration()` | kubeconfig/context 해석 + 연결 확인 |
| `get_cluster_global_values()` | sources.yaml의 클러스터 전역 values 추출 |
| `load_and_validate_config_file()` | 설정 파일 로딩 유틸리티 |
| `load_and_validate_sources_file()` | sources 파일 로딩 유틸리티 |

#### 전체 명령어 목록

| Command | File | Description |
|---------|------|-------------|
| `prepare` | `prepare.py` (42KB) | 소스 준비 (Helm chart pull, Git clone) |
| `build` | `build.py` (22KB) | 앱 빌드 (values merge, chart packaging) |
| `template` | `template.py` (30KB) | 매니페스트 렌더링 (helm template, jinja2) |
| `deploy` | `deploy.py` (58KB) | 배포 실행 (helm install, kubectl apply) |
| `apply` | `apply.py` (54KB) | 통합 워크플로우 (prepare→build→template→deploy) |
| `status` | `status.py` (36KB) | 클러스터 상태 조회 |
| `history` | `history.py` (23KB) | 배포 히스토리 조회 |
| `rollback` | `rollback.py` (11KB) | 롤백 실행 |
| `upgrade` | `upgrade.py` (14KB) | 인플레이스 업그레이드 |
| `delete` | `delete.py` (22KB) | 리소스 삭제 |
| `check_updates` | `check_updates.py` (14KB) | 차트 업데이트 확인 |
| `validate` | `validate.py` (19KB) | 설정 파일 검증 |
| `init` | `init.py` (19KB) | 프로젝트 초기화 |
| `doctor` | `doctor.py` (3KB) | 환경 진단 |
| `version` | `version.py` (<1KB) | 버전 표시 |
| `workspace` | `workspace.py` (89KB) | 워크스페이스 멀티 페이즈 명령어 |

### 3. Model Layer (models/ — 10 files)

#### 타입 계층 구조

```
ConfigBaseModel (base_model.py - Pydantic 확장)
  ├─ InheritableConfigModel (상속 지원)
  │
  ├─ SBKubeConfig (config_model.py)
  │   ├─ namespace: str
  │   ├─ apps: dict[str, AppConfig]  # key = app name
  │   ├─ hooks: dict[str, CommandHooks]
  │   └─ labels/annotations: dict[str, str]
  │
  ├─ AppConfig = Discriminated Union (config_model.py)
  │   ├─ HelmApp (type="helm")
  │   ├─ YamlApp (type="yaml")
  │   ├─ ActionApp (type="action")
  │   ├─ ExecApp (type="exec")
  │   ├─ GitApp (type="git")
  │   ├─ KustomizeApp (type="kustomize")
  │   ├─ HttpApp (type="http")
  │   ├─ NoopApp (type="noop")
  │   └─ HookApp (type="hook")
  │
  ├─ Hook System (config_model.py)
  │   ├─ HookTask = ManifestsHookTask | InlineHookTask | CommandHookTask
  │   ├─ AppHooks (per-app hooks)
  │   ├─ CommandHooks (per-command hooks)
  │   ├─ ValidationRule
  │   ├─ DependencyConfig
  │   └─ RollbackPolicy
  │
  ├─ SourceScheme (sources_model.py)
  │   ├─ HelmRepoScheme
  │   ├─ GitRepoScheme
  │   └─ OciRepoScheme
  │
  └─ UnifiedConfig (unified_config_model.py)
      ├─ apiVersion: "sbkube/v1"
      ├─ metadata: dict
      ├─ settings: UnifiedSettings
      ├─ apps: dict[str, AppConfig]
      └─ phases: dict[str, PhaseReference]

State Models (deployment_state.py, workspace_state.py)
  ├─ Deployment → AppDeployment → DeployedResource / HelmRelease
  ├─ WorkspaceDeployment → PhaseDeployment
  └─ ExecutionState → StepExecution (dataclass)
```

**검증 흐름**:

1. YAML 파일 파싱 (PyYAML)
1. Pydantic 모델로 변환 (`model_validate()`)
1. 필드 타입 검증 (자동, `extra="forbid"`)
1. Discriminated Union으로 타입별 모델 자동 선택
1. 커스텀 검증 로직 (`@field_validator`, `@model_validator`)
1. 검증 실패 시 명확한 오류 메시지

### 4. State Management (state/ — 5 files)

#### SQLAlchemy 모델 (deployment_state.py)

```
Deployment (배포 기록)
  ├─ deployment_id (unique)
  ├─ cluster, namespace
  ├─ status (pending/in_progress/success/failed/rolled_back/partially_failed)
  ├─ config_snapshot (JSON)
  └─ AppDeployment[] (앱별 배포)
       ├─ app_name, app_type, app_group
       ├─ DeployedResource[] (K8s 리소스)
       │   ├─ api_version, kind, name, namespace
       │   ├─ action (create/update/delete/apply/rollback)
       │   └─ previous_state, current_state, checksum
       └─ HelmRelease[] (Helm 릴리스)
           ├─ release_name, chart, chart_version
           ├─ revision, values
           └─ status
```

#### Workspace 모델 (workspace_state.py)

```
WorkspaceDeployment (워크스페이스 배포)
  ├─ workspace_name, workspace_file
  ├─ environment, target_phase
  ├─ total/completed/failed/skipped_phases
  └─ PhaseDeployment[] (페이즈별 배포)
       ├─ phase_name, execution_order
       ├─ depends_on, app_groups
       ├─ on_failure_action (stop/continue/rollback)
       └─ status, duration_seconds
```

#### 상태 추적 흐름

```python
# 1. 배포 시작
db = DeploymentDatabase()
deployment = db.create_deployment(DeploymentCreate(...))

# 2. 앱별 배포
app_deploy = db.add_app_deployment(deployment.id, AppDeploymentCreate(...))
db.add_deployed_resource(app_deploy.id, ResourceInfo(...))
db.add_helm_release(app_deploy.id, HelmReleaseInfo(...))

# 3. 상태 업데이트
db.update_deployment_status(deployment_id, DeploymentStatus.SUCCESS)

# 4. 히스토리 조회
history = db.list_deployments(cluster="...", namespace="...", limit=10)
```

### 5. Validation System (validators/ — 7 files)

#### 검증 계층

```
┌─────────────────────────────────────────┐
│     Pre-Deployment Validation (55KB)    │
│  (pre_deployment_validators.py)         │
│  - Kubernetes 클러스터 연결 확인          │
│  - 네임스페이스 존재 여부                  │
│  - RBAC 권한 확인                        │
│  - 필수 도구 설치 확인 (helm, kubectl)    │
│  - 리소스 충돌 검사                       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    Configuration Validation (34KB)      │
│  (configuration_validators.py)          │
│  - config.yaml / sbkube.yaml 스키마 검증 │
│  - sources.yaml 검증                    │
│  - 앱 이름 Kubernetes 네이밍 규칙 검사     │
│  - 순환 의존성 검사                       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    Environment Validation (36KB)        │
│  (environment_validators.py)            │
│  - 환경변수 확인                          │
│  - 디스크 공간 확인                       │
│  - 네트워크 접근성 확인                    │
│  - CLI 도구 버전 확인                     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    Dependency Validation (49KB)         │
│  (dependency_validators.py)             │
│  - Helm 차트 의존성 검증                  │
│  - Git 리포지토리 접근 확인                │
│  - OCI 레지스트리 인증 확인                │
│  - 의존성 그래프 사이클 검출               │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    Storage Validation (14KB)            │
│  (storage_validators.py)                │
│  - PV/PVC 유효성 검증                    │
│  - StorageClass 확인                     │
└─────────────────────────────────────────┘
```

### 6. Exception Hierarchy (exceptions.py — 520 lines)

```
SbkubeError (base, with details dict + exit_code)
├── ConfigurationError
│   ├── ConfigFileNotFoundError
│   ├── ConfigValidationError
│   └── SchemaValidationError
├── ToolError
│   ├── CliToolNotFoundError
│   ├── CliToolExecutionError
│   └── CliToolVersionError
├── KubernetesError
│   ├── KubernetesConnectionError
│   └── KubernetesResourceError
├── HelmError
│   ├── HelmChartNotFoundError
│   └── HelmInstallationError
├── GitError
│   └── GitRepositoryError
├── FileSystemError
│   ├── FileOperationError
│   └── DirectoryNotFoundError
├── SecurityError
│   └── PathTraversalError
├── ValidationError
│   └── InputValidationError
├── NetworkError
│   ├── DownloadError
│   └── RepositoryConnectionError
├── StateError
│   └── StateCorruptionError
├── DeploymentError
└── RollbackError
```

**에러 처리 플로우**:
```
Exception 발생 → error_classifier.py (분류)
  → error_suggestions.py (수정 제안 생성)
  → error_formatter.py (포맷팅)
  → format_error_with_suggestions() (통합 출력)
  → is_auto_recoverable() → auto-fix 프롬프트 (interactive terminal)
```

## 데이터 흐름

### 설정 로딩 (Unified vs Legacy)

```
┌─────────────────────────────────────────┐
│  Unified: sbkube.yaml (apiVersion: sbkube/v1)
│    ↓                                     │
│  ConfigManager → UnifiedConfig           │
│    ├── settings (kubeconfig, namespace, repos)
│    ├── apps (dict[str, AppConfig])       │
│    └── phases (dict[str, PhaseReference])│
├─────────────────────────────────────────┤
│  Legacy: sources.yaml + config.yaml     │
│    ↓                                     │
│  ConfigManager → SourceScheme + SBKubeConfig
│    ├── helm_repos, git_repos, oci_registries
│    └── apps (dict[str, AppConfig])       │
└─────────────────────────────────────────┘
```

### 워크플로우: prepare → build → template → deploy

```
┌───────────────────┐
│  sbkube.yaml      │
│  (or sources.yaml │
│   + config.yaml)  │
└────────┬──────────┘
         │
         ▼
    ┌────────────┐
    │  prepare   │
    │  (소스준비) │
    └────┬───────┘
         │ ✓ Helm 차트 다운로드 → .sbkube/charts/
         │ ✓ Git 리포지토리 클론 → .sbkube/repos/
         │ ✓ HTTP 파일 다운로드
         ▼
    ┌────────────┐
    │   build    │
    │  (앱빌드)   │
    └────┬───────┘
         │ ✓ 소스 정리 및 복사 → .sbkube/build/
         │ ✓ Values 파일 병합
         ▼
    ┌────────────┐
    │  template  │
    │ (템플릿화)  │
    └────┬───────┘
         │ ✓ Helm 차트 렌더링 → .sbkube/rendered/
         │ ✓ YAML/Jinja2 템플릿 처리
         ▼
    ┌────────────┐
    │   deploy   │
    │  (배포)     │
    └────┬───────┘
         │ ✓ kubectl apply / helm install (with retry)
         │ ✓ DeploymentDatabase 기록
         │ ✓ Hook 실행 (pre/post_deploy)
         ▼
    ┌────────────┐
    │ Kubernetes │
    │  Cluster   │
    └────────────┘
```

## 확장 메커니즘

### 1. 새 앱 타입 추가 가이드

**단계 1: App 모델 정의** (config_model.py)

```python
class MyNewApp(ConfigBaseModel):
    """새 앱 타입 모델."""
    type: Literal["my-new-type"] = "my-new-type"
    source_url: str
    target_path: str | None = None
    namespace: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
    hooks: AppHooks | None = None
    notes: str | None = Field(default=None)

    @field_validator('source_url')
    def validate_url(cls, v: str) -> str:
        if not v.startswith('http'):
            raise ValueError('source_url must be HTTP(S) URL')
        return v
```

**단계 2: Discriminated Union에 추가**

```python
AppConfig = Annotated[
    HelmApp | YamlApp | ActionApp | ExecApp | GitApp
    | KustomizeApp | HttpApp | NoopApp | HookApp
    | MyNewApp,  # 추가
    Field(discriminator="type"),
]
```

**단계 3: 각 명령어에서 처리 로직 구현**

```python
# commands/prepare.py, deploy.py 등에서
if app_info.type == 'my-new-type':
    self.handle_my_new_type(app_info)
```

### 2. 새 명령어 추가 가이드

**단계 1: 명령어 클래스 작성**

```python
# commands/my_command.py
from sbkube.utils.base_command import EnhancedBaseCommand
from sbkube.utils.output_manager import OutputManager

class MyCommand(EnhancedBaseCommand):
    def execute(self, output: OutputManager):
        output.print_section("My Command")
        config = self.load_config()

        for app_name, app_info in config.apps.items():
            if app_info.enabled:
                output.print(f"Processing: {app_name}")
                # 처리 로직
        output.finalize(status="success")
```

**단계 2: Click 명령어 정의**

```python
@click.command(name="my-command")
@click.option('--app-dir', default='config', help='설정 디렉토리')
@click.option('--app', help='특정 앱만 처리')
@click.pass_context
def cmd(ctx, app_dir, app):
    """나만의 커스텀 명령어"""
    command = MyCommand(
        base_dir='.', app_config_dir=app_dir,
        output_format=ctx.obj.get("format", "human")
    )
    output = OutputManager(format_type=ctx.obj.get("format", "human"))
    command.execute(output)
```

**단계 3: cli.py에 등록 + SbkubeGroup.COMMAND_CATEGORIES에 추가**

```python
# cli.py
from sbkube.commands import my_command
main.add_command(my_command.cmd)

# SbkubeGroup.COMMAND_CATEGORIES에 카테고리 등록
```

## 성능 고려사항

### 프로파일링 (perf.py)

`SBKUBE_PERF=1`로 활성화:
- `subprocess.run` 자동 계측 (monkey-patch)
- `perf_timer()` context manager로 코드 블록 계측
- JSONL 이벤트 로그 (`tmp/perf/`)
- 프로세스 종료 시 자동 요약 출력

### 재시도 로직 (retry.py)

```python
# Predefined configs
NETWORK_RETRY_CONFIG = RetryConfig(max_attempts=3, base_delay=2.0, max_delay=30.0)
HELM_RETRY_CONFIG = RetryConfig(max_attempts=3, base_delay=1.0, max_delay=15.0)
GIT_RETRY_CONFIG = RetryConfig(max_attempts=3, base_delay=2.0, max_delay=20.0)

# Usage
@retry_helm_operation
def download_helm_chart(repo, chart, version): ...

# Or with context manager
result = run_helm_command_with_retry(["helm", "pull", chart])
```

### 캐싱 전략

- **Helm 차트**: `.sbkube/charts/` 디렉토리에 `repo/chart-version` 구조로 캐시
- **Git 리포지토리**: `.sbkube/repos/` 디렉토리에 클론 유지
- **설정 파일**: `ConfigLoader`의 메모리 캐시 (동일 파일 재로딩 방지)
- **클러스터 정보**: `cluster_cache.py`로 캐시

## 보안 고려사항

### 1. Secrets 관리

- Kubernetes Secrets는 kubectl/Helm에 위임
- 설정 파일에 민감 정보 직접 저장 금지
- 환경변수 또는 외부 Secrets 관리 도구 사용 권장

### 2. 입력 검증

- 모든 외부 입력 Pydantic으로 검증 (`extra="forbid"`)
- `PathTraversalError` 예외로 경로 탐색 공격 방지
- Shell injection 방지 (subprocess에서 `shell=True` 사용 금지)
- `security.py` 유틸리티 모듈

### 3. 에러 정보 보안

- `format_error_with_suggestions()`로 안전한 에러 출력
- 자동 수정 시 placeholder 검사 후 실행
- 인터랙티브 터미널에서만 자동 수정 프롬프트

## 에러 복구 전략

### 1. 부분 배포 실패 처리

- `process_apps_with_stats()`: 앱별 성공/실패 통계 추적
- `PARTIALLY_FAILED` 상태로 부분 성공 기록
- 실패한 앱만 재시도 가능

### 2. 롤백 메커니즘

- `state/rollback.py`: 배포 전 스냅샷 기반 롤백
- Helm 릴리스: 이전 revision 자동 롤백
- kubectl 리소스: previous_state 기반 복원
- 상태 DB에 롤백 이벤트 기록

### 3. Workspace 실패 정책

- `on_failure: stop` — 즉시 중단 (기본값)
- `on_failure: continue` — 다음 페이즈 계속
- `on_failure: rollback` — 현재 페이즈 롤백 후 중단

## 테스트 전략

### 1. 단위 테스트 (tests/unit/)

- 각 명령어 클래스별 테스트
- Pydantic 모델 검증 테스트 (모든 앱 타입)
- 유틸리티 함수 테스트
- `OutputManager` mocking: `MagicMock(spec=OutputManager)`

### 2. 통합 테스트 (tests/integration/)

- 전체 워크플로우 테스트 (prepare → deploy)
- Helm/kubectl 연동 테스트 (mock 사용)
- 상태 관리 시스템 테스트 (SQLite in-memory)
- `@pytest.mark.integration` 마커 필수

### 3. E2E 테스트 (tests/e2e/)

- testcontainers[k3s]를 사용한 실제 클러스터 테스트
- 실제 Helm 차트 배포 시나리오
- 롤백 및 상태 조회 테스트

### 4. 성능 테스트 (tests/performance/)

- pytest-benchmark를 사용한 벤치마크
- 모델 파싱 성능 측정
- 대규모 앱 목록 처리 성능

---

## 관련 문서

- **아키텍처 요약**: [ARCHITECTURE.md](../../../ARCHITECTURE.md) — 프로젝트 전체 아키텍처 요약
- **
- **제품 정의**: [PRODUCT.md](../../../PRODUCT.md) — 제품 개요 (무엇을, 왜)
- **기술 스택**: [TECH_STACK.md](../../../TECH_STACK.md) — 기술 스택 상세
- **모듈 개요**: [MODULE.md](MODULE.md) — 모듈 정의 및 경계
- **API 계약**: [API_CONTRACT.md](API_CONTRACT.md) — API 계약 명세
- ****의존성**: [TECH_STACK.md](../../../TECH_STACK.md) — 기술 스택 및 의존성

---

**문서 버전**: 2.0
**마지막 업데이트**: 2026-02-25
**SBKube Version**: 0.11.0
**담당자**: archmagece@users.noreply.github.com
