# SBKube 모듈 아키텍처

## 개요
이 문서는 SBKube 모듈의 상세한 아키텍처 설계를 다룹니다. 사용자용 개요는 [docs/02-features/architecture.md](../../02-features/architecture.md)를 참조하세요.

## 아키텍처 원칙

### 1. 단순성 (Simplicity)
- 모놀리식 구조로 복잡성 최소화
- 명확한 계층 분리
- 직관적인 명령어 체계

### 2. 확장성 (Extensibility)
- 플러그인 패턴 (BaseCommand)
- 새로운 앱 타입 쉽게 추가
- 새로운 명령어 독립적 구현

### 3. 안정성 (Reliability)
- 강타입 검증 (Pydantic)
- 명확한 에러 메시지
- 상태 관리 및 롤백

### 4. 사용자 경험 (User Experience)
- Rich 콘솔 UI
- 실시간 진행 상태 표시
- Dry-run 모드 지원

## 레이어 아키텍처

```
┌────────────────────────────────────────────────────────┐
│                   CLI Layer                            │
│  (Click Framework + SbkubeGroup)                       │
│  - 명령어 파싱 및 라우팅                                 │
│  - 전역 옵션 처리 (kubeconfig, context, namespace)    │
│  - 도구 검증 (kubectl, helm 설치 확인)                  │
└──────────────────┬─────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────┐
│                Command Layer                           │
│  (BaseCommand Pattern)                                 │
│  - 명령어별 비즈니스 로직 (prepare, build, etc.)        │
│  - 공통 설정 로딩 및 검증                                │
│  - 앱별 처리 로직 (app.type에 따른 분기)                 │
└──────────────────┬─────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────┐
│              Model & Validation Layer                  │
│  (Pydantic Models)                                     │
│  - 설정 파일 모델 (SBKubeConfig, AppInfoScheme)        │
│  - 런타임 타입 검증                                      │
│  - JSON 스키마 자동 생성                                 │
└──────────────────┬─────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────┐
│          Infrastructure Layer                          │
│  (Utils, State, Validators)                            │
│  - Helm/kubectl/Git 연동 (utils/)                      │
│  - 배포 상태 관리 (state/)                              │
│  - 사전/사후 검증 (validators/)                         │
│  - 로깅 및 UI (logger.py, Rich)                        │
└──────────────────┬─────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────┐
│           External Dependencies                        │
│  - Helm CLI v3.x                                       │
│  - kubectl                                             │
│  - Git                                                 │
│  - Kubernetes API (via Python client)                 │
└────────────────────────────────────────────────────────┘
```

## 핵심 컴포넌트

### 1. CLI 엔트리포인트 (cli.py)

#### SbkubeGroup 클래스
```python
class SbkubeGroup(click.Group):
    """사용자 정의 Click Group"""

    def invoke(self, ctx: click.Context):
        # 1. 명령어 실행 전 도구 검증
        if ctx.invoked_subcommand in ['deploy', 'upgrade']:
            check_kubectl_installed_or_exit()
            check_helm_installed_or_exit()

        # 2. 명령어 실행
        return super().invoke(ctx)
```

**책임**:
- 전역 옵션 파싱 (--kubeconfig, --context, --namespace, --verbose)
- 명령어별 필수 도구 검증 (kubectl, helm, git)
- 컨텍스트 전달 (ctx.obj)
- 명령어 없이 실행 시 kubeconfig 정보 표시

### 2. Command Layer (commands/)

#### BaseCommand 패턴
```python
class BaseCommand(ABC):
    """모든 명령어의 기본 클래스"""

    def __init__(self, base_dir, app_config_dir, target_app_name, config_file_name):
        self.base_dir = Path(base_dir).resolve()
        self.app_config_dir = self.base_dir / app_config_dir
        self.target_app_name = target_app_name
        self.config_file_name = config_file_name or 'config.yaml'

    def load_config(self) -> SBKubeConfig:
        """설정 파일 로딩 및 Pydantic 검증"""
        config_path = self.app_config_dir / self.config_file_name
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return SBKubeConfig.model_validate(data)

    def should_process_app(self, app: AppInfoScheme) -> bool:
        """앱 처리 여부 판단 (--app 옵션, enabled 플래그)"""
        if self.target_app_name and app.name != self.target_app_name:
            return False
        return app.enabled

    @abstractmethod
    def execute(self):
        """명령어 실행 로직 (서브클래스 구현)"""
        pass
```

**책임**:
- 설정 파일 로딩 및 검증
- 앱 필터링 로직 (--app 옵션)
- 공통 전처리 (execute_pre_hook)
- 에러 처리 템플릿

#### 명령어별 구현 예시 (PrepareCommand)
```python
class PrepareCommand(BaseCommand):
    def execute(self):
        logger.heading(f"Prepare - app-dir: {self.app_config_dir.name}")

        config = self.load_config()
        sources = self.load_sources()  # sources.yaml 로딩

        # Helm 저장소 추가
        for repo in sources.helm_repos:
            self.add_helm_repo(repo)

        # 앱별 소스 준비
        for app in config.apps:
            if not self.should_process_app(app):
                continue

            if app.type == 'helm':
                self.prepare_helm_chart(app, sources)
            elif app.type == 'pull-git':
                self.prepare_git_repo(app, sources)
            elif app.type == 'helm-oci':
                self.prepare_oci_chart(app)
```

### 3. Model Layer (models/)

#### 타입 계층 구조
```
BaseModel (Pydantic)
  ├─ SBKubeConfig
  │   ├─ namespace: str
  │   ├─ deps: List[str]
  │   └─ apps: List[AppInfoScheme]
  │
  ├─ AppInfoScheme
  │   ├─ name: str
  │   ├─ type: Literal[...]
  │   ├─ enabled: bool
  │   ├─ namespace: Optional[str]
  │   ├─ release_name: Optional[str]
  │   └─ specs: Union[AppSpecBase, dict]
  │
  ├─ AppSpecBase (추상)
  │   ├─ AppPullHelmSpec
  │   ├─ AppInstallHelmSpec
  │   ├─ AppInstallYamlSpec
  │   ├─ AppCopyAppSpec
  │   └─ AppExecSpec
  │
  └─ SourcesConfig
      ├─ helm_repos: List[HelmRepoInfo]
      └─ git_repos: List[GitRepoInfo]
```

**검증 흐름**:
1. YAML 파일 파싱 (PyYAML)
2. Pydantic 모델로 변환 (`model_validate()`)
3. 필드 타입 검증 (자동)
4. 커스텀 검증 로직 (`@field_validator`)
5. 검증 실패 시 명확한 오류 메시지

### 4. State Management (state/)

#### 데이터베이스 스키마
```sql
CREATE TABLE deployment_states (
    id TEXT PRIMARY KEY,
    app_name TEXT NOT NULL,
    cluster_name TEXT NOT NULL,
    namespace TEXT NOT NULL,
    release_name TEXT,
    status TEXT NOT NULL,  -- success, failed, rollback
    created_at DATETIME NOT NULL,
    metadata JSON
);

CREATE INDEX idx_app_cluster ON deployment_states(app_name, cluster_name);
CREATE INDEX idx_namespace ON deployment_states(namespace);
CREATE INDEX idx_created_at ON deployment_states(created_at DESC);
```

#### 상태 추적 흐름
```python
# 1. 배포 시작 전
state_tracker.begin_deployment(app_name, cluster, namespace)

# 2. 배포 실행
try:
    helm_install(...)
    state_tracker.mark_success(deployment_id, metadata={
        'chart_version': '1.2.3',
        'values_hash': 'abc123'
    })
except Exception as e:
    state_tracker.mark_failed(deployment_id, error=str(e))

# 3. 히스토리 조회
history = state_tracker.get_history(
    cluster=cluster,
    namespace=namespace,
    limit=10
)
```

### 5. Validation System (validators/)

#### 검증 계층
```
┌─────────────────────────────────────────┐
│     Pre-Deployment Validation           │
│  (pre_deployment_validators.py)         │
│  - Kubernetes 클러스터 연결 확인          │
│  - 네임스페이스 존재 여부                  │
│  - RBAC 권한 확인                        │
│  - 필수 도구 설치 확인 (helm, kubectl)    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    Configuration Validation             │
│  (configuration_validators.py)          │
│  - config.yaml 스키마 검증               │
│  - sources.yaml 검증                    │
│  - 앱 이름 중복 검사                      │
│  - 순환 의존성 검사                       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    Environment Validation               │
│  (environment_validators.py)            │
│  - 환경변수 확인                          │
│  - 디스크 공간 확인                       │
│  - 네트워크 접근성 확인                    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    Dependency Validation                │
│  (dependency_validators.py)             │
│  - Helm 차트 의존성 검증                  │
│  - Git 리포지토리 접근 확인                │
│  - OCI 레지스트리 인증 확인                │
└─────────────────────────────────────────┘
```

## 데이터 흐름

### 워크플로우: prepare → build → template → deploy

```
┌───────────────────┐
│  config.yaml      │
│  sources.yaml     │
└────────┬──────────┘
         │
         ▼
    ┌────────────┐
    │  prepare   │
    │  (소스준비) │
    └────┬───────┘
         │ ✓ Helm 차트 다운로드 → charts/
         │ ✓ Git 리포지토리 클론 → repos/
         ▼
    ┌────────────┐
    │   build    │
    │  (앱빌드)   │
    └────┬───────┘
         │ ✓ 소스 정리 및 복사 → build/
         ▼
    ┌────────────┐
    │  template  │
    │ (템플릿화)  │
    └────┬───────┘
         │ ✓ Helm 차트 렌더링 → rendered/
         │ ✓ YAML 템플릿 처리
         ▼
    ┌────────────┐
    │   deploy   │
    │  (배포)     │
    └────┬───────┘
         │ ✓ kubectl apply / helm install
         │ ✓ 상태 DB 기록
         ▼
    ┌────────────┐
    │ Kubernetes │
    │  Cluster   │
    └────────────┘
```

### 설정 파일 처리 흐름
```
config.yaml (YAML)
    │
    ├─► PyYAML 파싱
    │       │
    │       ▼
    │   Python Dict
    │       │
    │       ▼
    ├─► Pydantic 검증
    │       │
    │       ▼
    │   SBKubeConfig 객체
    │       │
    │       ├─► namespace: str
    │       ├─► deps: List[str]
    │       └─► apps: List[AppInfoScheme]
    │               │
    │               ├─► name: str
    │               ├─► type: str
    │               └─► specs: AppSpecBase
    │
    └─► 명령어 실행
            │
            ├─► 앱 필터링 (--app 옵션)
            ├─► enabled 체크
            └─► 타입별 처리
```

## 확장 메커니즘

### 1. 새 앱 타입 추가 가이드

**단계 1: Spec 모델 정의**
```python
# models/config_model.py
class AppMyNewTypeSpec(AppSpecBase):
    """새 앱 타입의 Spec 모델"""
    source_url: str  # 필수 필드
    target_path: Optional[str] = None  # 선택 필드
    options: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('source_url')
    def validate_url(cls, v):
        if not v.startswith('http'):
            raise ValueError('source_url must be HTTP(S) URL')
        return v
```

**단계 2: AppInfoScheme 업데이트**
```python
class AppInfoScheme(BaseModel):
    type: Literal[
        'exec', 'helm', 'yaml',
        'helm', 'pull-git', 'copy-app',
        'my-new-type'  # 추가
    ]
```

**단계 3: get_spec_model 매핑 추가**
```python
def get_spec_model(app_type: str):
    mapping = {
        'my-new-type': AppMyNewTypeSpec,
        # ...
    }
    return mapping.get(app_type, dict)
```

**단계 4: 각 명령어에서 처리 로직 구현**
```python
# commands/prepare.py
class PrepareCommand(BaseCommand):
    def execute(self):
        for app in config.apps:
            if app.type == 'my-new-type':
                self.handle_my_new_type(app)

    def handle_my_new_type(self, app: AppInfoScheme):
        spec = cast(AppMyNewTypeSpec, app.specs)
        # 새 타입 처리 로직
        download_from_url(spec.source_url, spec.target_path)
```

### 2. 새 명령어 추가 가이드

**단계 1: 명령어 클래스 작성**
```python
# commands/my_command.py
from sbkube.utils.base_command import BaseCommand

class MyCommand(BaseCommand):
    def __init__(self, base_dir, app_dir, app_name,
                 my_option: str):
        super().__init__(base_dir, app_dir, app_name, None)
        self.my_option = my_option

    def execute(self):
        logger.heading(f"My Command - {self.my_option}")
        config = self.load_config()

        for app in config.apps:
            if self.should_process_app(app):
                self.process_app(app)
```

**단계 2: Click 명령어 정의**
```python
@click.command(name="my-command")
@click.option('--app-dir', default='config', help='설정 디렉토리')
@click.option('--app', help='특정 앱만 처리')
@click.option('--my-option', required=True, help='나만의 옵션')
@click.pass_context
def cmd(ctx, app_dir, app, my_option):
    """나만의 커스텀 명령어"""
    command = MyCommand(
        base_dir='.',
        app_dir=app_dir,
        app_name=app,
        my_option=my_option
    )
    command.execute()
```

**단계 3: cli.py에 등록**
```python
# cli.py
from sbkube.commands import my_command

main.add_command(my_command.cmd)
```

## 성능 고려사항

### 병렬 처리 전략 (향후 구현)
```python
from concurrent.futures import ThreadPoolExecutor

def prepare_apps_parallel(apps: List[AppInfoScheme]):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for app in apps:
            if app.type in ['helm', 'pull-git']:
                future = executor.submit(download_app, app)
                futures.append(future)

        for future in futures:
            future.result()  # 에러 처리
```

### 캐싱 전략
- **Helm 차트**: `charts/` 디렉토리에 버전별 캐시
- **Git 리포지토리**: `repos/` 디렉토리에 클론 유지
- **설정 파일**: 파싱 결과 메모리 캐시 (동일 파일 재로딩 방지)

### 메모리 관리
- 대규모 YAML 파일: 스트리밍 파싱 (향후)
- Helm 템플릿 출력: 파일로 바로 저장 (메모리 적재 최소화)

## 보안 고려사항

### 1. Secrets 관리
- Kubernetes Secrets는 kubectl/Helm에 위임
- 설정 파일에 민감 정보 직접 저장 금지
- 환경변수 또는 외부 Secrets 관리 도구 사용 권장

### 2. 권한 최소화
- kubeconfig 파일 권한 확인 (600)
- 대상 네임스페이스에만 접근
- RBAC 권한 사전 검증

### 3. 입력 검증
- 모든 외부 입력 Pydantic으로 검증
- Shell injection 방지 (subprocess 안전 사용)
- 경로 탐색 공격 방지 (Path().resolve() 사용)

## 에러 복구 전략

### 1. 부분 배포 실패 처리
```python
deployed_apps = []
try:
    for app in apps:
        deploy_app(app)
        deployed_apps.append(app)
except Exception as e:
    logger.error(f"Deployment failed: {e}")
    logger.info(f"Successfully deployed: {[a.name for a in deployed_apps]}")
    # 실패한 앱부터 다시 시도 가능
```

### 2. 롤백 메커니즘
- 배포 전 현재 상태 스냅샷
- 실패 시 이전 Helm 릴리스로 자동 롤백 (옵션)
- 상태 DB에 롤백 이벤트 기록

### 3. 재시도 로직 (utils/retry.py)
```python
@retry(max_attempts=3, backoff_seconds=5)
def download_helm_chart(repo, chart, version):
    # 네트워크 장애 시 재시도
    pass
```

## 테스트 전략

### 1. 단위 테스트
- 각 명령어 클래스별 테스트
- Pydantic 모델 검증 테스트
- 유틸리티 함수 테스트 (helm_util, file_loader)

### 2. 통합 테스트
- 전체 워크플로우 테스트 (prepare → deploy)
- Helm/kubectl 연동 테스트 (mock 사용)
- 상태 관리 시스템 테스트 (SQLite in-memory)

### 3. E2E 테스트
- testcontainers[k3s]를 사용한 실제 클러스터 테스트
- 실제 Helm 차트 배포 시나리오
- 롤백 및 상태 조회 테스트

## 향후 개선 계획

### 단기 (v0.3.x)
- 병렬 처리 구현
- 플러그인 시스템 베타
- 웹 UI 프로토타입

### 중기 (v0.4.x - v0.6.x)
- 멀티 클러스터 지원
- 분산 잠금 (동시 배포 방지)
- GitOps 통합 (Flux, ArgoCD)

### 장기 (v1.0.x)
- Kubernetes Operator 개발
- API 서버 모드
- 엔터프라이즈 기능 (HA, Multi-tenancy)

---

**문서 버전**: 1.0
**마지막 업데이트**: 2025-10-20
**관련 문서**:
- [MODULE.md](MODULE.md) - 모듈 정의 및 경계
- [API_CONTRACT.md](API_CONTRACT.md) - API 계약 명세
- [docs/02-features/architecture.md](../../02-features/architecture.md) - 사용자용 아키텍처 개요
