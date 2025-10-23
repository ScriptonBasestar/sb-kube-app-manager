# SBKube API 계약 명세

## 개요
이 문서는 SBKube 모듈의 내부 API 인터페이스 계약을 정의합니다. 새로운 명령어나 앱 타입을 추가할 때 이 계약을 준수해야 합니다.

## BaseCommand 인터페이스

### 클래스 시그니처
```python
class BaseCommand(ABC):
    """모든 명령어의 기본 클래스

    이 클래스를 상속하여 새 명령어를 구현합니다.
    """

    def __init__(
        self,
        base_dir: str | Path,
        app_config_dir: str | Path,
        target_app_name: Optional[str] = None,
        config_file_name: Optional[str] = None
    ):
        """
        Args:
            base_dir: 작업 디렉토리 (일반적으로 프로젝트 루트)
            app_config_dir: 설정 파일 디렉토리 (config/ 등)
            target_app_name: 특정 앱만 처리 (--app 옵션)
            config_file_name: 설정 파일 이름 (기본: config.yaml)
        """
```

### 필수 구현 메서드

#### execute()
```python
@abstractmethod
def execute(self) -> None:
    """명령어 실행 로직

    이 메서드를 반드시 구현해야 합니다.

    Raises:
        SbkubeError: 명령어 실행 중 오류 발생 시
    """
    pass
```

### 제공되는 유틸리티 메서드

#### load_config()
```python
def load_config(self) -> SBKubeConfig:
    """config.yaml 로딩 및 검증

    Returns:
        SBKubeConfig: Pydantic으로 검증된 설정 객체

    Raises:
        ConfigValidationError: 설정 파일 검증 실패 시
        FileNotFoundError: 설정 파일 없을 시
    """
```

#### load_sources()
```python
def load_sources(self) -> SourcesConfig:
    """sources.yaml 로딩 및 검증

    Returns:
        SourcesConfig: Helm 저장소 및 Git 리포지토리 설정

    Raises:
        ConfigValidationError: 검증 실패 시
    """
```

#### should_process_app()
```python
def should_process_app(self, app: AppInfoScheme) -> bool:
    """앱 처리 여부 판단

    Args:
        app: 앱 정의 객체

    Returns:
        bool: True면 처리, False면 스킵

    로직:
        1. --app 옵션 지정 시 해당 앱만 처리
        2. app.enabled가 False면 스킵
    """
```

### 사용 예시
```python
# commands/my_command.py
from sbkube.utils.base_command import BaseCommand

class MyCommand(BaseCommand):
    def execute(self):
        # 1. 설정 로딩
        config = self.load_config()

        # 2. 앱별 처리
        for app in config.apps:
            if not self.should_process_app(app):
                continue

            # 3. 타입별 로직
            if app.type == 'helm':
                self.process_helm(app)
            elif app.type == 'yaml':
                self.process_yaml(app)

    def process_helm(self, app: AppInfoScheme):
        # Helm 처리 로직
        pass
```

## Pydantic 모델 계약

### SBKubeConfig
```python
class SBKubeConfig(ConfigBaseModel):
    """config.yaml 루트 모델

    Breaking Changes:
    - apps: List → Dict[str, AppConfig] (apps는 dict, key = app name)
    - 평탄화된 구조 (specs 래퍼 제거)
    """

    namespace: str  # 기본 네임스페이스
    apps: Dict[str, AppConfig]  # 앱 정의 (dict, key = 앱 이름)

    @field_validator('namespace')
    def validate_namespace(cls, v: str) -> str:
        """네임스페이스 유효성 검증"""
        if not v or not v.strip():
            raise ValueError('namespace must not be empty')
        return v

    def get_deployment_order(self) -> List[str]:
        """의존성 기반 배포 순서 계산 (위상 정렬)"""
        # ... 구현 생략
```

### AppConfig (Discriminated Union)
```python
# 타입별 App 모델 (Discriminated Union)
AppConfig = Annotated[
    Union[HelmApp, YamlApp, ActionApp, ExecApp, GitApp, KustomizeApp, HttpApp],
    Field(discriminator="type"),
]
```

### 타입별 App 모델

#### HelmApp
```python
class HelmApp(ConfigBaseModel):
    """Helm 차트 배포 앱

    통합 타입: remote chart 및 local chart 모두 지원
    - "repo/chart" 형식 → remote (자동 pull + install)
    - "./path" or "/path" → local (install only)
    """

    type: Literal["helm"] = "helm"
    chart: str  # "repo/chart", "./path", "/path"
    version: str | None = None  # 차트 버전 (remote chart만)
    values: list[str] = Field(default_factory=list)  # values 파일 목록
    overrides: list[str] = Field(default_factory=list)  # 덮어쓸 파일
    removes: list[str] = Field(default_factory=list)  # 제거할 파일 패턴

    # Helm 옵션
    release_name: str | None = None
    namespace: str | None = None
    create_namespace: bool = False
    wait: bool = True
    timeout: str = "5m"

    # 공통 필드
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
```

#### YamlApp
```python
class YamlApp(ConfigBaseModel):
    """YAML 매니페스트 직접 배포 앱"""

    type: Literal["yaml"] = "yaml"
    files: list[str]  # YAML 파일 목록
    namespace: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
```

#### ActionApp
```python
class ActionApp(ConfigBaseModel):
    """커스텀 액션 실행 앱 (apply/create/delete)"""

    type: Literal["action"] = "action"
    actions: list[dict[str, Any]]  # kubectl 액션 목록
    namespace: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
```

#### ExecApp
```python
class ExecApp(ConfigBaseModel):
    """커스텀 명령어 실행 앱"""

    type: Literal["exec"] = "exec"
    commands: list[str]  # 실행할 명령어 목록
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
```

#### GitApp
```python
class GitApp(ConfigBaseModel):
    """Git 리포지토리에서 매니페스트 가져오기"""

    type: Literal["git"] = "git"
    repo: str  # Git repository URL
    path: str | None = None  # 리포지토리 내 경로
    branch: str = "main"
    ref: str | None = None  # 특정 commit/tag
    namespace: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
```

#### HttpApp
```python
class HttpApp(ConfigBaseModel):
    """HTTP URL에서 파일 다운로드"""

    type: Literal["http"] = "http"
    url: str  # HTTP(S) URL
    dest: str  # 저장할 파일 경로
    headers: dict[str, str] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
```

#### KustomizeApp
```python
class KustomizeApp(ConfigBaseModel):
    """Kustomize 기반 배포"""

    type: Literal["kustomize"] = "kustomize"
    path: str  # kustomization.yaml 경로
    namespace: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
```

## 새 앱 타입 추가 계약

### 1단계: App 모델 정의 (Discriminated Union 패턴)
```python
# sbkube/models/config_model.py에 추가

class MyNewApp(ConfigBaseModel):
    """새 앱 타입 모델

    ConfigBaseModel을 상속하여 새 앱 타입을 정의합니다.
    """

    type: Literal["my-new-type"] = "my-new-type"  # 필수: type 필드

    # 앱 타입별 필수 필드
    source_url: str  # 예: S3 URL
    target_path: str | None = None

    # 공통 필드 (옵션)
    namespace: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True

    # 검증 로직
    @field_validator('source_url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """URL 검증"""
        if not v.startswith(('s3://', 'gs://')):
            raise ValueError('source_url must be S3 or GCS URL')
        return v
```

### 2단계: AppConfig Union 업데이트
```python
# sbkube/models/config_model.py

AppConfig = Annotated[
    Union[
        HelmApp, YamlApp, ActionApp, ExecApp,
        GitApp, KustomizeApp, HttpApp,
        MyNewApp,  # 새 타입 추가
    ],
    Field(discriminator="type"),  # type 필드로 자동 구분
]
```

### 3단계: BaseCommand에서 타입 처리
```python
# commands/prepare.py

from sbkube.models.config_model import MyNewApp

class PrepareCommand(BaseCommand):
    def execute(self):
        config = self.load_config()

        for app_name, app in config.apps.items():  # Dict 순회
            if not self.should_process_app(app):
                continue

            # 타입별 분기 (isinstance 사용)
            if isinstance(app, MyNewApp):
                self.prepare_my_new_type(app_name, app)
            elif isinstance(app, HelmApp):
                self.prepare_helm(app_name, app)
            # ...

    def prepare_my_new_type(self, app_name: str, app: MyNewApp):
        """MyNewApp 타입 처리"""
        console.print(f"[cyan]Downloading from {app.source_url}...[/cyan]")
        download_from_cloud(app.source_url, app.target_path)
```

### 4단계: 모든 명령어에서 처리 로직 구현
```python
# commands/build.py
def build_my_new_type(app_name: str, app: MyNewApp):
    """Build 단계 처리"""
    pass

# commands/template.py
def template_my_new_type(app_name: str, app: MyNewApp):
    """Template 단계 처리"""
    pass

# commands/deploy.py
def deploy_my_new_type(app_name: str, app: MyNewApp):
    """Deploy 단계 처리"""
    kubectl_apply(app.target_path)
```

### 새 타입 추가 체크리스트
- [ ] `ConfigBaseModel` 상속한 `<NewType>App` 클래스 정의
- [ ] `type: Literal["new-type"]` 필드 필수
- [ ] `AppConfig` Union에 추가
- [ ] `prepare`, `build`, `template`, `deploy` 명령어에서 처리 로직 구현
- [ ] 테스트 케이스 작성 (`tests/test_<new_type>.py`)
- [ ] 문서 업데이트 (`docs/02-features/application-types.md`)
- [ ] 예제 추가 (`examples/deploy/<new-type>-example/`)

## 로깅 인터페이스

### logger 모듈 사용
```python
from sbkube.utils.logger import logger

# 레벨별 로깅
logger.heading("📋 Build 시작")  # 제목 (큰 박스)
logger.info("✅ 앱 빌드 완료")   # 일반 정보 (파란색)
logger.warning("⚠️ 설정 누락")  # 경고 (노란색)
logger.error("❌ 빌드 실패")    # 오류 (빨간색)
logger.verbose("🔍 디버그 정보")  # 디버깅 (--verbose 시만)
```

### 로깅 규칙
1. **heading()**: 명령어 시작 시 한 번만
2. **info()**: 주요 진행 상황 표시
3. **warning()**: 문제는 아니지만 주의 필요한 경우
4. **error()**: 오류 발생 시 (배포는 계속)
5. **verbose()**: 디버깅 정보 (기본은 숨김)

## 에러 처리 계약

### 예외 클래스 계층
```python
class SbkubeError(Exception):
    """SBKube 기본 예외

    모든 SBKube 예외의 부모 클래스
    """
    def __init__(self, message: str, exit_code: int = 1):
        self.message = message
        self.exit_code = exit_code

class CliToolNotFoundError(SbkubeError):
    """외부 CLI 도구 미발견"""
    pass

class ConfigValidationError(SbkubeError):
    """설정 검증 오류"""
    pass

class DeploymentError(SbkubeError):
    """배포 실행 오류"""
    pass
```

### 에러 처리 가이드라인
```python
def execute(self):
    try:
        # 명령어 로직
        self.process_apps()
    except CliToolNotFoundError as e:
        logger.error(f"Required tool not found: {e.message}")
        sys.exit(e.exit_code)
    except ConfigValidationError as e:
        logger.error(f"Configuration error: {e.message}")
        logger.info("Please check your config.yaml")
        sys.exit(e.exit_code)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
```

## 상태 관리 인터페이스

### DeploymentState 모델
```python
class DeploymentState(Base):
    """배포 상태 ORM 모델"""

    __tablename__ = 'deployment_states'

    id: str  # UUID
    app_name: str
    cluster_name: str
    namespace: str
    release_name: Optional[str]
    status: str  # 'success', 'failed', 'rollback'
    created_at: datetime
    metadata: dict  # JSON 필드
```

### StateTracker 인터페이스
```python
class StateTracker:
    """배포 상태 추적 클래스"""

    def begin_deployment(
        self,
        app_name: str,
        cluster: str,
        namespace: str
    ) -> str:
        """배포 시작 기록

        Returns:
            str: deployment_id (UUID)
        """

    def mark_success(
        self,
        deployment_id: str,
        metadata: Optional[dict] = None
    ) -> None:
        """배포 성공 기록"""

    def mark_failed(
        self,
        deployment_id: str,
        error: str
    ) -> None:
        """배포 실패 기록"""

    def get_history(
        self,
        cluster: Optional[str] = None,
        namespace: Optional[str] = None,
        app_name: Optional[str] = None,
        limit: int = 10
    ) -> List[DeploymentState]:
        """배포 히스토리 조회"""
```

## Click 명령어 계약

### 명령어 데코레이터 패턴
```python
@click.command(name="my-command")
@click.option('--base-dir', default='.', help='작업 디렉토리')
@click.option('--app-dir', default='config', help='설정 디렉토리')
@click.option('--app', help='특정 앱만 처리')
@click.option('--my-option', help='커스텀 옵션')
@click.pass_context
def cmd(ctx, base_dir, app_dir, app, my_option):
    """명령어 설명

    상세 설명...
    """
    command = MyCommand(base_dir, app_dir, app, my_option)
    command.execute()
```

### 전역 컨텍스트 접근
```python
@click.pass_context
def cmd(ctx, ...):
    # 전역 옵션 접근
    kubeconfig = ctx.obj.get('kubeconfig')
    context = ctx.obj.get('context')
    namespace = ctx.obj.get('namespace')
    verbose = ctx.obj.get('verbose')
```

## 버전 호환성

### API 변경 정책
- **Major 버전 변경**: 호환 불가능한 API 변경
- **Minor 버전 변경**: 하위 호환 API 추가
- **Patch 버전 변경**: 버그 수정 (API 변경 없음)

### 현재 버전 (v0.2.1)
- BaseCommand 인터페이스: 안정
- Pydantic 모델: 실험적 (v2 마이그레이션 중)
- 상태 관리 API: 베타

---

**문서 버전**: 1.0
**마지막 업데이트**: 2025-10-20
**관련 문서**:
- [MODULE.md](MODULE.md) - 모듈 정의
- [ARCHITECTURE.md](ARCHITECTURE.md) - 아키텍처
- [DEPENDENCIES.md](DEPENDENCIES.md) - 의존성 명세
