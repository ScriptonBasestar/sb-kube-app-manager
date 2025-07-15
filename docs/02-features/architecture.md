# 🏗️ SBKube 아키텍처 가이드

SBKube의 내부 구조와 설계 원칙에 대한 상세한 설명입니다.

---

## 📂 프로젝트 구조

```
sbkube/
├── cli.py                    # 🎯 메인 CLI 엔트리포인트
├── commands/                 # 📋 명령어 구현
│   ├── prepare.py           # 소스 준비
│   ├── build.py             # 앱 빌드 
│   ├── template.py          # 템플릿 렌더링
│   ├── deploy.py            # 배포 실행
│   ├── upgrade.py           # 릴리스 업그레이드
│   ├── delete.py            # 리소스 삭제
│   ├── validate.py          # 설정 검증
│   ├── version.py           # 버전 정보
│   └── state.py             # 상태 관리 (신규)
├── models/                  # 🎨 데이터 모델
│   ├── config_model.py      # 앱 설정 모델 (주력)
│   ├── config_model_v2.py   # v2 모델 (실험적)
│   ├── sources_model.py     # 소스 설정 모델
│   ├── deployment_state.py  # 배포 상태 모델
│   └── validators.py        # 검증 로직
├── state/                   # 📊 상태 관리 시스템
│   ├── database.py          # SQLAlchemy 데이터베이스
│   ├── tracker.py           # 상태 추적
│   └── rollback.py          # 롤백 관리
└── utils/                   # 🔧 유틸리티
    ├── base_command.py      # 명령어 기본 클래스
    ├── logger.py            # Rich 기반 로깅
    ├── cli_check.py         # CLI 도구 검증
    ├── common.py            # 공통 함수
    ├── helm_util.py         # Helm 유틸리티
    └── file_loader.py       # 파일 로딩
```

---

## 🎯 핵심 아키텍처 패턴

### 1. **BaseCommand 패턴**

모든 명령어는 `BaseCommand` 클래스를 상속하여 일관된 동작을 제공합니다.

```python
class BaseCommand:
    """모든 명령어의 기본 클래스"""
    
    def __init__(self, base_dir: str, app_config_dir: str, 
                 target_app_name: Optional[str], config_file_name: Optional[str]):
        self.base_dir = Path(base_dir).resolve()
        self.app_config_dir = self.base_dir / app_config_dir
        # 공통 초기화 로직
        
    def execute_pre_hook(self):
        """실행 전 공통 처리"""
        
    def execute(self):
        """명령어별 구현 (추상 메서드)"""
        raise NotImplementedError
```

#### 장점
- **일관된 설정 로딩**: 모든 명령어가 동일한 방식으로 설정 파일 처리
- **공통 에러 처리**: 표준화된 예외 처리 및 로깅
- **확장성**: 새로운 명령어 추가 시 기본 기능 자동 제공

---

### 2. **Pydantic 기반 모델 시스템**

강력한 타입 검증과 데이터 모델링을 위해 Pydantic을 활용합니다.

```python
class AppInfoScheme(BaseModel):
    """애플리케이션 정의 모델"""
    name: str
    type: Literal[
        'exec', 'install-helm', 'install-action', 'install-kustomize', 'install-yaml',
        'pull-helm', 'pull-helm-oci', 'pull-git', 'pull-http', 'copy-app'
    ]
    path: Optional[str] = None
    enabled: bool = True
    namespace: Optional[str] = None
    release_name: Optional[str] = None
    specs: Dict[str, Any] = Field(default_factory=dict)
```

#### 특징
- **런타임 검증**: 설정 파일 로딩 시 자동 타입 검증
- **JSON 스키마 생성**: 자동으로 JSON 스키마 생성 가능
- **IDE 지원**: 타입 힌트를 통한 자동완성 및 오류 검출

---

### 3. **Rich Console 시스템**

사용자 친화적인 콘솔 출력을 위해 Rich 라이브러리를 활용합니다.

```python
# 색상별 로깅 레벨
logger.heading("🚀 Build 시작")        # 제목
logger.info("✅ 앱 빌드 완료")          # 정보
logger.warning("⚠️ 설정 파일 누락")     # 경고  
logger.error("❌ 빌드 실패")           # 오류
logger.verbose("🔍 상세 디버그 정보")   # 상세 (--verbose 시에만)
```

#### 출력 예제
```
╭─────────────────────────────────────────────────────────╮
│                    🚀 Build 시작                         │
│                app-dir: config                         │
╰─────────────────────────────────────────────────────────╯

✅ nginx-app 빌드 완료
⚠️  database-app 설정 파일이 누락되었습니다
```

---

### 4. **상태 관리 시스템** *(신규)*

SQLAlchemy 기반의 배포 상태 추적 및 롤백 시스템입니다.

```python
class DeploymentState(Base):
    """배포 상태 모델"""
    __tablename__ = 'deployment_states'
    
    id = Column(String, primary_key=True)
    app_name = Column(String, nullable=False)
    cluster_name = Column(String, nullable=False)
    namespace = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)
```

#### 기능
- **자동 상태 추적**: 배포/업그레이드/삭제 시 자동으로 상태 기록
- **히스토리 관리**: 시간순 배포 히스토리 조회
- **롤백 지원**: 이전 상태로 안전한 롤백

---

## 🔄 명령어 실행 플로우

### 1. **CLI 엔트리포인트 (cli.py)**

```python
@click.group(cls=SbkubeGroup, invoke_without_command=True)
@click.option('--kubeconfig', help='Kubernetes 설정 파일 경로')
@click.option('--context', help='사용할 Kubernetes 컨텍스트')
@click.option('--namespace', help='기본 네임스페이스')
@click.option('-v', '--verbose', help='상세 로깅')
def main(ctx, kubeconfig, context, namespace, verbose):
    """SBKube 메인 CLI"""
    
    # 전역 설정 저장
    ctx.obj = {
        'kubeconfig': kubeconfig,
        'context': context, 
        'namespace': namespace,
        'verbose': verbose
    }
    
    # 명령어 없이 실행 시 kubeconfig 정보 표시
    if ctx.invoked_subcommand is None:
        display_kubeconfig_info(kubeconfig, context)
```

### 2. **명령어별 전처리 (SbkubeGroup)**

```python
class SbkubeGroup(click.Group):
    def invoke(self, ctx: click.Context):
        """명령어 실행 전 공통 검증"""
        
        if ctx.invoked_subcommand:
            # kubectl이 필요한 명령어들
            kubectl_commands = ['deploy', 'upgrade', 'delete', 'prepare']
            # helm이 필요한 명령어들  
            helm_commands = ['template', 'deploy', 'upgrade', 'delete', 'prepare', 'build']
            
            if ctx.invoked_subcommand in kubectl_commands:
                check_kubectl_installed_or_exit()
                
            if ctx.invoked_subcommand in helm_commands:
                check_helm_installed_or_exit()
```

### 3. **개별 명령어 실행**

각 명령어는 독립적으로 실행되며, BaseCommand 패턴을 따릅니다:

```python
# build.py 예제
class BuildCommand(BaseCommand):
    def execute(self):
        self.execute_pre_hook()  # 공통 전처리
        logger.heading(f"Build 시작 - app-dir: {self.app_config_dir.name}")
        
        # 설정 파일 로딩
        config_data = self.load_config()
        
        # 앱별 빌드 처리
        for app in config_data.apps:
            if self.should_process_app(app):
                self.build_app(app)
```

---

## 🎨 확장 가능한 설계

### 1. **새로운 앱 타입 추가**

새로운 앱 타입을 추가하는 과정:

```python
# 1. models/config_model.py에 새 Spec 클래스 추가
class AppMyNewTypeSpec(AppSpecBase):
    my_field: str
    my_optional_field: Optional[int] = None

# 2. AppInfoScheme의 type Literal에 추가
type: Literal[
    'exec', 'install-helm', ..., 'my-new-type'  # 새 타입 추가
]

# 3. get_spec_model 함수에 매핑 추가
def get_spec_model(app_type: str):
    spec_model_mapping = {
        'my-new-type': AppMyNewTypeSpec,  # 새 매핑 추가
        # ...
    }

# 4. 각 명령어에서 새 타입 처리 로직 추가
def build_app(self, app: AppInfoScheme):
    if app.type == 'my-new-type':
        self.handle_my_new_type(app)
```

### 2. **새로운 명령어 추가**

새로운 명령어를 추가하는 과정:

```python
# 1. commands/my_command.py 생성
from sbkube.utils.base_command import BaseCommand

class MyCommand(BaseCommand):
    def execute(self):
        # 새 명령어 로직 구현
        pass

@click.command(name="my-command")
@click.option("--my-option", help="내 옵션")
def cmd(my_option):
    """새로운 명령어"""
    command = MyCommand(...)
    command.execute()

# 2. cli.py에 명령어 등록
from sbkube.commands import my_command
main.add_command(my_command.cmd)
```

---

## 🔧 에러 처리 시스템

### 1. **계층화된 예외 구조**

```python
class SbkubeError(Exception):
    """SBKube 기본 예외"""
    def __init__(self, message: str, exit_code: int = 1):
        self.message = message
        self.exit_code = exit_code

class CliToolNotFoundError(SbkubeError):
    """CLI 도구 미발견 예외"""
    pass

class ConfigValidationError(SbkubeError):
    """설정 검증 오류 예외"""
    pass
```

### 2. **전역 예외 처리**

```python
def main_with_exception_handling():
    """전역 예외 처리가 포함된 메인 함수"""
    try:
        main()
    except SbkubeError as e:
        logger.error(format_error_with_suggestions(e))
        sys.exit(e.exit_code)
    except KeyboardInterrupt:
        logger.info("사용자에 의해 취소됨")
        sys.exit(130)
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        sys.exit(1)
```

---

## 📊 성능 최적화

### 1. **지연 로딩 (Lazy Loading)**

- 큰 파일이나 외부 리소스는 필요할 때만 로딩
- Kubernetes 클라이언트는 사용 시점에 초기화

### 2. **병렬 처리**

- 여러 앱의 prepare/build 작업을 병렬로 처리 가능
- Helm 차트 다운로드 동시 실행

### 3. **캐싱**

- 다운로드된 Helm 차트 로컬 캐싱
- 설정 파일 파싱 결과 캐싱

---

## 🔮 미래 확장 계획

### 1. **플러그인 시스템**
- 외부 플러그인을 통한 기능 확장
- 커스텀 앱 타입 동적 로딩

### 2. **웹 UI**
- 상태 관리를 위한 웹 대시보드
- 배포 히스토리 시각화

### 3. **고급 상태 관리**
- 분산 잠금을 통한 동시 배포 방지
- 클러스터 간 상태 동기화

---

*이 아키텍처는 확장성, 유지보수성, 사용자 경험을 중시하여 설계되었습니다.*