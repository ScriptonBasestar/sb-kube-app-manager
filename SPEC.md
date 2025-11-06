______________________________________________________________________

## type: Technical Specification audience: Developer, DevOps Engineer topics: [architecture, implementation, api, workflow, technical] llm_priority: high last_updated: 2025-01-06

# SBKube 기술 명세서 (Technical Specification)

> **어떻게 만들 것인가**: SBKube의 아키텍처, 워크플로우, API, 데이터 구조, 구현 상세 기술 사양

______________________________________________________________________

## 📌 목차

1. [문서 개요](#1-문서-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [워크플로우 상세](#3-워크플로우-상세)
4. [데이터 모델 및 스키마](#4-데이터-모델-및-스키마)
5. [API 및 명령어 명세](#5-api-및-명령어-명세)
6. [상태 관리 시스템](#6-상태-관리-시스템)
7. [Hooks 시스템 구현](#7-hooks-시스템-구현)
8. [검증 시스템](#8-검증-시스템)
9. [기술 스택 및 의존성](#9-기술-스택-및-의존성)
10. [에러 처리 및 예외](#10-에러-처리-및-예외)
11. [성능 및 확장성](#11-성능-및-확장성)
12. [보안 고려사항](#12-보안-고려사항)

______________________________________________________________________

## 1. 문서 개요

### 1.1 문서 목적

본 문서는 SBKube의 **기술적 구현 방법**을 정의합니다. 개발자가 기능을 구현하거나 시스템을 이해하기 위한 청사진 역할을 합니다.

### 1.2 독자

- **주 독자**: 개발자, DevOps 엔지니어
- **보조 독자**: QA 엔지니어, 아키텍트

### 1.3 관련 문서

| 문서 | 목적 | 링크 |
|------|------|------|
| **PRODUCT.md** | 제품 정의 (무엇을, 왜) | [PRODUCT.md](PRODUCT.md) |
| **ARCHITECTURE.md** | 상세 아키텍처 설계 | [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md) |
| **API_CONTRACT.md** | API 계약 및 인터페이스 | [docs/10-modules/sbkube/API_CONTRACT.md](docs/10-modules/sbkube/API_CONTRACT.md) |
| **config-schema.md** | 설정 파일 스키마 상세 | [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md) |

### 1.4 버전 정보

- **문서 버전**: 2.0
- **대상 SBKube 버전**: v0.7.0 (개발 중, 안정 버전: v0.6.0)
- **마지막 업데이트**: 2025-01-06
- **문서 상태**: v0.7.0 기능 포함 (일부 Unreleased)

______________________________________________________________________

## 2. 시스템 아키텍처

### 2.1 고수준 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      SBKube CLI                             │
│               (Click Framework)                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────────┐ ┌──────────────┐ ┌──────────────┐
│   Commands    │ │    Models    │ │    State     │
│    Layer      │ │    Layer     │ │  Management  │
├───────────────┤ ├──────────────┤ ├──────────────┤
│ • prepare     │ │ • ConfigModel│ │ • SQLAlchemy │
│ • build       │ │ • SourcesModel│ │ • Tracker   │
│ • template    │ │ • Pydantic   │ │ • History    │
│ • deploy      │ │   Validators │ │ • Rollback   │
│ • apply       │ │              │ │              │
│ • status      │ │              │ │              │
└───────┬───────┘ └──────┬───────┘ └──────┬───────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
              ┌──────────────────┐
              │  Utils & Helpers │
              ├──────────────────┤
              │ • helm_util      │
              │ • logger         │
              │ • file_loader    │
              │ • output_formatter│
              └─────────┬────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌─────────────┐ ┌──────────────┐
│   Helm CLI   │ │   kubectl   │ │   Git CLI    │
│   (v3.x)     │ │             │ │              │
└──────────────┘ └─────────────┘ └──────────────┘
        │               │               │
        └───────────────┼───────────────┘
                        ▼
               ┌────────────────┐
               │  Kubernetes    │
               │   Cluster      │
               └────────────────┘
```

### 2.2 모듈 구조

```
sbkube/
├── cli.py                    # CLI 엔트리포인트
├── commands/                 # 명령어 구현
│   ├── __init__.py
│   ├── apply.py             # 통합 워크플로우
│   ├── prepare.py           # 소스 준비
│   ├── build.py             # 앱 빌드
│   ├── template.py          # 템플릿 렌더링
│   ├── deploy.py            # 배포 실행
│   ├── status.py            # 상태 조회
│   ├── history.py           # 히스토리 조회
│   ├── rollback.py          # 롤백
│   └── validate.py          # 설정 검증
├── models/                  # 데이터 모델
│   ├── __init__.py
│   ├── config_model.py      # config.yaml 모델
│   ├── sources_model.py     # sources.yaml 모델
│   └── deployment_state.py  # 배포 상태 모델
├── state/                   # 상태 관리
│   ├── __init__.py
│   ├── database.py          # SQLAlchemy 설정
│   ├── tracker.py           # 배포 추적
│   └── rollback.py          # 롤백 관리
├── utils/                   # 유틸리티
│   ├── __init__.py
│   ├── base_command.py      # 명령어 베이스 클래스
│   ├── logger.py            # Rich 로깅
│   ├── helm_util.py         # Helm 연동
│   ├── file_loader.py       # 파일 로딩
│   └── output_formatter.py  # LLM 친화적 출력
└── validators/              # 검증 시스템
    ├── __init__.py
    ├── config_validator.py  # 설정 검증
    └── dependency_validator.py  # 의존성 검증
```

### 2.3 핵심 아키텍처 패턴

#### 2.3.1 Command Pattern (명령 패턴)

모든 명령어는 `BaseCommand` 또는 `EnhancedBaseCommand`를 상속:

```python
# sbkube/utils/base_command.py
class BaseCommand:
    def __init__(self, app_dir: str, base_dir: str, **kwargs):
        self.app_dir = app_dir
        self.base_dir = base_dir
        self.logger = get_logger()

    def execute(self):
        raise NotImplementedError

class EnhancedBaseCommand(BaseCommand):
    def __init__(self, *args, format: str = "human", **kwargs):
        super().__init__(*args, **kwargs)
        self.formatter = OutputFormatter(format=format)
```

#### 2.3.2 Strategy Pattern (전략 패턴)

앱 타입별로 다른 처리 전략 적용:

```python
# 앱 타입별 핸들러
APP_HANDLERS = {
    "helm": HelmHandler,
    "yaml": YAMLHandler,
    "git": GitHandler,
    "kustomize": KustomizeHandler,
    "action": ActionHandler,
}
```

#### 2.3.3 Repository Pattern (저장소 패턴)

상태 관리 데이터 접근 추상화:

```python
# sbkube/state/tracker.py
class DeploymentTracker:
    def __init__(self, db_path: str):
        self.db = Database(db_path)

    def save_deployment(self, deployment: DeploymentState):
        # SQLAlchemy ORM 사용

    def get_history(self, filters: dict):
        # 히스토리 조회
```

______________________________________________________________________

## 3. 워크플로우 상세

### 3.1 통합 워크플로우 (`apply`)

**명령어**: `sbkube apply [옵션]`

**실행 흐름**:
```
1. 설정 파일 로딩 (config.yaml, sources.yaml)
   ↓
2. Pydantic 검증
   ↓
3. 전역 pre-apply hooks 실행
   ↓
4. prepare 단계 실행
   ↓
5. build 단계 실행
   ↓
6. template 단계 실행
   ↓
7. deploy 단계 실행
   ↓
8. 전역 post-apply hooks 실행
   ↓
9. 상태 DB 저장
```

**시퀀스 다이어그램**:
```
User         ApplyCmd      PrepareCmd   BuildCmd   TemplateCmd  DeployCmd   StateDB
 │              │              │           │            │           │          │
 ├─ apply ─────>│              │           │            │           │          │
 │              ├─ validate ──>│           │            │           │          │
 │              │<─ OK ────────┤           │            │           │          │
 │              ├─ execute ───>│           │            │           │          │
 │              │              ├─ download charts       │           │          │
 │              │              ├─────────────────────────────────────────────>│
 │              │              │           │            │           │          │
 │              ├──────────────┼─ execute─>│            │           │          │
 │              │              │           ├─ customize charts      │          │
 │              │              │           ├───────────────────────────────────>│
 │              │              │           │            │           │          │
 │              ├──────────────┼───────────┼─ execute──>│           │          │
 │              │              │           │            ├─ render   │          │
 │              │              │           │            ├─────────────────────>│
 │              │              │           │            │           │          │
 │              ├──────────────┼───────────┼────────────┼─ execute─>│          │
 │              │              │           │            │           ├─ kubectl │
 │              │              │           │            │           ├─────────>│
 │              │              │           │            │           │<─ OK ────┤
 │              ├──────────────────────────────────────────────────────────────>│
 │<─ Done ──────┤              │           │            │           │          │
```

### 3.2 prepare - 소스 준비

**목적**: 외부 소스 다운로드 및 로컬화

**지원 앱 타입**:
- `helm`: Helm 차트 (remote repository)
- `git`: Git 리포지토리
- `http`: HTTP(S) URL 파일 다운로드

**구현 로직** (helm 타입):
```python
def prepare_helm_app(app: AppConfig, sources: SourcesConfig):
    """
    Helm 차트 다운로드 로직

    1. chart 필드 파싱 (repo/chart 형식)
    2. sources.yaml의 helm_repos에서 repository URL 조회
    3. helm repo add 실행
    4. helm pull 실행
    5. .sbkube/charts/<app-name>/ 에 저장
    """
    repo_name, chart_name = parse_chart_field(app.chart)
    repo_url = sources.helm_repos.get(repo_name)

    # helm repo add
    run_command(f"helm repo add {repo_name} {repo_url}")

    # helm pull
    version_flag = f"--version {app.version}" if app.version else ""
    run_command(f"helm pull {repo_name}/{chart_name} {version_flag} --untar -d .sbkube/charts/{app.name}")
```

**출력 디렉토리**:
```
.sbkube/
└── charts/
    ├── grafana/        # helm 타입 앱
    │   └── grafana/    # 실제 차트 디렉토리
    └── nginx/
        └── nginx/
```

### 3.3 build - 앱 빌드

**목적**: 배포 가능한 형태로 변환

**지원 앱 타입**:
- `helm`: Helm 차트 커스터마이징 (overrides, removes 적용)

**구현 로직** (차트 커스터마이징):
```python
def build_helm_app(app: AppConfig):
    """
    Helm 차트 커스터마이징

    1. .sbkube/charts/<app-name> → .sbkube/build/<app-name> 복사
    2. overrides 파일 덮어쓰기
    3. removes 패턴 파일 삭제
    """
    src = f".sbkube/charts/{app.name}"
    dest = f".sbkube/build/{app.name}"

    # 복사
    shutil.copytree(src, dest)

    # overrides 적용
    for override_path in app.overrides or []:
        dest_path = os.path.join(dest, os.path.basename(override_path))
        shutil.copy(override_path, dest_path)

    # removes 적용
    for remove_pattern in app.removes or []:
        for file in glob.glob(os.path.join(dest, remove_pattern)):
            os.remove(file)
```

**출력 디렉토리**:
```
.sbkube/
└── build/
    ├── grafana/        # 커스터마이징된 차트
    │   └── grafana/
    └── nginx/
        └── nginx/
```

### 3.4 template - 템플릿 렌더링

**목적**: 환경별 설정 적용 및 YAML 생성

**지원 앱 타입**:
- `helm`: Helm 차트 렌더링
- `yaml`: YAML 파일 템플릿화 (Jinja2, 향후 지원)

**구현 로직**:
```python
def template_helm_app(app: AppConfig, namespace: str):
    """
    Helm 차트 템플릿 렌더링

    1. helm template 명령어 실행
    2. values 파일 적용
    3. .sbkube/rendered/<app-name>.yaml 생성
    """
    chart_path = f".sbkube/build/{app.name}"
    release_name = app.release_name or app.name

    # values 파일 옵션 생성
    values_flags = " ".join([f"-f {v}" for v in app.values or []])

    # helm template 실행
    cmd = f"helm template {release_name} {chart_path} {values_flags} -n {namespace}"
    output = run_command(cmd, capture_output=True)

    # 파일 저장
    with open(f".sbkube/rendered/{app.name}.yaml", "w") as f:
        f.write(output)
```

**출력 디렉토리**:
```
.sbkube/
└── rendered/
    ├── grafana.yaml    # 렌더링된 매니페스트
    └── nginx.yaml
```

### 3.5 deploy - 배포 실행

**목적**: Kubernetes 클러스터에 배포

**지원 앱 타입**:
- `helm`: Helm 릴리스 설치/업그레이드
- `yaml`: kubectl apply 실행
- `action`: kubectl 액션 (apply, create, delete)
- `exec`: 임의 명령어 실행

**구현 로직** (helm 타입):
```python
def deploy_helm_app(app: AppConfig, namespace: str, dry_run: bool = False):
    """
    Helm 릴리스 배포

    1. helm install 또는 helm upgrade 실행
    2. --dry-run 지원
    3. 배포 상태 DB 저장
    """
    chart_path = f".sbkube/build/{app.name}"
    release_name = app.release_name or app.name
    values_flags = " ".join([f"-f {v}" for v in app.values or []])

    # 릴리스 존재 여부 확인
    exists = check_release_exists(release_name, namespace)

    # install vs upgrade
    action = "upgrade --install" if exists else "install"
    dry_run_flag = "--dry-run" if dry_run else ""

    cmd = f"helm {action} {release_name} {chart_path} {values_flags} -n {namespace} {dry_run_flag}"
    run_command(cmd)

    # 상태 저장
    if not dry_run:
        tracker.save_deployment(
            app_name=app.name,
            namespace=namespace,
            status="deployed",
            timestamp=datetime.now()
        )
```

______________________________________________________________________

## 4. 데이터 모델 및 스키마

### 4.1 config.yaml 스키마 (Pydantic)

**모델 정의**:
```python
# sbkube/models/config_model.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict

class HooksConfig(BaseModel):
    """Hooks 설정"""
    pre_deploy: Optional[List[str]] = None
    post_deploy: Optional[List[str]] = None
    on_deploy_failure: Optional[List[str]] = None

class AppConfig(BaseModel):
    """앱 설정"""
    type: str = Field(..., description="앱 타입 (helm, yaml, action, exec, git, http, kustomize)")
    enabled: bool = Field(default=True, description="활성화 여부")
    depends_on: Optional[List[str]] = Field(default=None, description="앱 의존성")
    deps: Optional[List[str]] = Field(default=None, description="앱 그룹 의존성")

    # helm 타입 필드
    chart: Optional[str] = Field(default=None, description="차트 경로 (repo/chart 또는 ./path)")
    version: Optional[str] = Field(default=None, description="차트 버전")
    values: Optional[List[str]] = Field(default=None, description="values 파일 목록")
    overrides: Optional[List[str]] = Field(default=None, description="덮어쓸 파일 목록")
    removes: Optional[List[str]] = Field(default=None, description="제거할 파일 패턴")
    namespace: Optional[str] = Field(default=None, description="네임스페이스 오버라이드")
    release_name: Optional[str] = Field(default=None, description="Helm 릴리스 이름")

    # hooks
    hooks: Optional[HooksConfig] = None

    @field_validator("type")
    def validate_type(cls, v):
        valid_types = ["helm", "yaml", "action", "exec", "git", "http", "kustomize"]
        if v not in valid_types:
            raise ValueError(f"Invalid type '{v}'. Must be one of {valid_types}")
        return v

class Config(BaseModel):
    """config.yaml 전체 모델"""
    namespace: str = Field(..., description="기본 네임스페이스")
    deps: Optional[List[str]] = Field(default=None, description="앱 그룹 의존성")
    apps: Dict[str, AppConfig] = Field(..., description="앱 정의 (dict 형식)")
    hooks: Optional[HooksConfig] = None  # 전역 hooks
```

**YAML 예시**:
```yaml
namespace: production
deps: ["a000_infra"]

apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: "18.0.0"
    values: ["values/production.yaml"]
    hooks:
      pre_deploy: ["./backup-db.sh"]
      post_deploy: ["./notify-slack.sh"]

  nginx:
    type: helm
    chart: ./charts/nginx-custom
    overrides: ["templates/deployment.yaml"]
    removes: ["templates/ingress.yaml"]
```

### 4.2 sources.yaml 스키마

**모델 정의**:
```python
# sbkube/models/sources_model.py
class SourcesConfig(BaseModel):
    """sources.yaml 전체 모델"""
    kubeconfig: str = Field(..., description="Kubeconfig 파일 경로")
    kubeconfig_context: str = Field(..., description="Kubectl context 이름")
    cluster: Optional[str] = Field(default=None, description="클러스터 이름 (문서화 목적)")

    helm_repos: Dict[str, str] = Field(default_factory=dict, description="Helm 저장소 (이름: URL)")
    git: Optional[Dict[str, GitRepoConfig]] = Field(default=None, description="Git 리포지토리")
```

**YAML 예시**:
```yaml
kubeconfig: ~/.kube/config
kubeconfig_context: production-cluster
cluster: production-k3s

helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
  grafana: https://grafana.github.io/helm-charts

git:
  my-manifests:
    url: https://github.com/example/k8s-manifests.git
    ref: v1.0.0
```

### 4.3 배포 상태 DB 스키마

**SQLAlchemy 모델**:
```python
# sbkube/state/database.py
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class DeploymentHistory(Base):
    __tablename__ = 'deployment_history'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    cluster_context = Column(String(255), nullable=False)
    namespace = Column(String(255), nullable=False)
    app_name = Column(String(255), nullable=False)
    release_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)  # deployed, failed, rolled_back
    metadata = Column(JSON, nullable=True)  # 추가 메타데이터 (버전, 해시 등)
```

**데이터베이스 위치**: `.sbkube/deployments.db` (SQLite)

______________________________________________________________________

## 5. API 및 명령어 명세

### 5.1 CLI 명령어 계약

#### 5.1.1 전역 옵션

```bash
sbkube [전역옵션] <명령어> [명령어옵션]

전역 옵션:
  --kubeconfig <경로>     # Kubernetes 설정 파일 (기본: ~/.kube/config)
  --context <이름>        # Kubernetes 컨텍스트 (sources.yaml 우선)
  --namespace <이름>      # 기본 네임스페이스 (config.yaml 우선)
  --format <형식>         # 출력 형식: human, llm, json, yaml (기본: human)
  -v, --verbose          # 상세 로깅
  --help                 # 도움말
```

#### 5.1.2 apply - 통합 워크플로우

```bash
sbkube apply [옵션]

옵션:
  --app-dir <경로>        # 설정 디렉토리 (기본: ./config)
  --base-dir <경로>       # 작업 디렉토리 (기본: .)
  --app <이름>            # 특정 앱만 처리
  --from-step <단계>      # 시작 단계 (prepare, build, template, deploy)
  --to-step <단계>        # 종료 단계
  --only <단계>           # 특정 단계만 실행
  --dry-run              # 시뮬레이션 모드
  --resume               # 실패 지점부터 재시작

예제:
  sbkube apply --app-dir config/production
  sbkube apply --from-step template --namespace staging
  sbkube apply --only deploy --dry-run
```

#### 5.1.3 status - 배포 상태 조회

```bash
sbkube status [옵션]

옵션:
  --namespace <이름>      # 네임스페이스 필터
  --app-group <경로>      # 앱 그룹 디렉토리 (config.yaml 위치)

출력:
  - 클러스터 정보 (context, server)
  - 노드 상태
  - Helm 릴리스 목록 (네임스페이스 또는 앱 그룹별)
  - 배포 상태 (최근 배포 기록)

예제:
  sbkube status --namespace production
  sbkube status --app-group a101_data_rdb
  sbkube --format llm status --namespace staging
```

#### 5.1.4 history - 배포 히스토리 조회

```bash
sbkube history [옵션]

옵션:
  --namespace <이름>      # 네임스페이스 필터
  --app <이름>            # 앱 이름 필터
  --limit <N>             # 최근 N개 (기본: 10)

출력:
  배포 히스토리 테이블 (timestamp, app, namespace, status)

예제:
  sbkube history --namespace production --limit 20
  sbkube history --app redis
```

#### 5.1.5 validate - 설정 검증

```bash
sbkube validate [TARGET_FILE] [옵션]

옵션:
  --app-dir <경로>        # 설정 디렉토리 (기본: ./config)
  --config-file <파일>    # 설정 파일 이름 (기본: config.yaml)
  --schema-type <타입>    # 파일 종류: config, sources

검증 항목:
  1. YAML 구문 검증
  2. Pydantic 모델 검증
  3. 앱 이름 중복 검사
  4. 순환 의존성 검사
  5. 앱 그룹 의존성 배포 상태 검증

예제:
  sbkube validate config.yaml
  sbkube validate --schema-type sources
```

### 5.2 Python API (프로그래밍 방식)

**명령어 직접 호출**:
```python
from sbkube.commands.apply import ApplyCommand

# Apply 명령어 실행
cmd = ApplyCommand(
    app_dir="config/production",
    base_dir=".",
    format="llm",
    dry_run=False
)
cmd.execute()
```

**설정 파일 로딩**:
```python
from sbkube.utils.file_loader import load_config

config = load_config("config/production/config.yaml")
print(config.namespace)  # 'production'
print(config.apps["redis"].chart)  # 'bitnami/redis'
```

______________________________________________________________________

## 6. 상태 관리 시스템

### 6.1 배포 상태 추적

**저장 정보**:
- 배포 시각 (timestamp)
- 클러스터 정보 (context, namespace)
- 앱 정보 (app_name, release_name)
- 배포 결과 (status: deployed, failed, rolled_back)
- 메타데이터 (JSON 필드: 차트 버전, 설정 해시 등)

**구현**:
```python
# sbkube/state/tracker.py
class DeploymentTracker:
    def __init__(self, db_path: str = ".sbkube/deployments.db"):
        self.db = Database(db_path)

    def save_deployment(self, **kwargs):
        """배포 기록 저장"""
        deployment = DeploymentHistory(
            timestamp=datetime.now(),
            cluster_context=kwargs["context"],
            namespace=kwargs["namespace"],
            app_name=kwargs["app_name"],
            release_name=kwargs.get("release_name"),
            status=kwargs["status"],
            metadata=kwargs.get("metadata", {})
        )
        self.db.session.add(deployment)
        self.db.session.commit()

    def get_history(self, filters: dict = None, limit: int = 10):
        """히스토리 조회"""
        query = self.db.session.query(DeploymentHistory)

        if filters:
            if "namespace" in filters:
                query = query.filter_by(namespace=filters["namespace"])
            if "app_name" in filters:
                query = query.filter_by(app_name=filters["app_name"])

        return query.order_by(DeploymentHistory.timestamp.desc()).limit(limit).all()
```

### 6.2 앱 그룹 의존성 검증

**목적**: `deps` 필드에 선언된 의존 앱 그룹이 배포되었는지 확인

**네임스페이스 자동 감지** (v0.6.0+):
```python
# sbkube/validators/dependency_validator.py
def validate_app_group_dependencies(config: Config, tracker: DeploymentTracker):
    """
    앱 그룹 의존성 검증

    1. config.deps 필드 확인
    2. 각 의존 앱 그룹의 배포 히스토리 조회
    3. 네임스페이스 자동 감지 (히스토리 DB에서)
    4. 배포 여부 확인
    """
    if not config.deps:
        return []

    warnings = []
    for dep_group in config.deps:
        # 의존 앱 그룹의 배포 기록 조회 (네임스페이스 무관)
        history = tracker.get_history(filters={"app_name": f"{dep_group}/*"}, limit=1)

        if not history:
            warnings.append(f"Dependency '{dep_group}' is not deployed")
        else:
            detected_namespace = history[0].namespace
            logger.info(f"Dependency '{dep_group}' found in namespace '{detected_namespace}'")

    return warnings
```

### 6.3 롤백 지원

**롤백 프로세스**:
```python
# sbkube/state/rollback.py
def rollback_deployment(deployment_id: int, tracker: DeploymentTracker):
    """
    배포 롤백

    1. 이전 배포 상태 조회 (deployment_id)
    2. Helm 릴리스 롤백 실행
    3. 새로운 배포 기록 생성 (status: rolled_back)
    """
    # 1. 이전 배포 조회
    prev_deployment = tracker.get_deployment_by_id(deployment_id)

    # 2. Helm 롤백
    cmd = f"helm rollback {prev_deployment.release_name} -n {prev_deployment.namespace}"
    run_command(cmd)

    # 3. 롤백 기록 저장
    tracker.save_deployment(
        context=prev_deployment.cluster_context,
        namespace=prev_deployment.namespace,
        app_name=prev_deployment.app_name,
        release_name=prev_deployment.release_name,
        status="rolled_back",
        metadata={"original_deployment_id": deployment_id}
    )
```

______________________________________________________________________

## 7. Hooks 시스템 구현

### 7.1 Hooks 실행 타이밍

**명령어 수준 Hooks** (전역):
```yaml
# config.yaml
hooks:
  deploy:
    pre: ["echo 'Starting deployment'"]
    post: ["./notify-slack.sh 'Deployment completed'"]
    on_failure: ["./rollback.sh"]
```

**앱 수준 Hooks**:
```yaml
# config.yaml
apps:
  database:
    type: helm
    chart: bitnami/postgresql
    hooks:
      pre_deploy: ["./backup-db.sh"]
      post_deploy: ["kubectl wait --for=condition=ready pod -l app=postgresql"]
      on_deploy_failure: ["./restore-backup.sh"]
```

### 7.2 실행 순서

**deploy 명령어 실행 시**:
```
1. 전역 hooks.deploy.pre 실행
2. 앱 A:
   2.1. 앱 A hooks.pre_deploy 실행
   2.2. 앱 A 배포
   2.3. 성공 → 앱 A hooks.post_deploy 실행
       실패 → 앱 A hooks.on_deploy_failure 실행
3. 앱 B:
   3.1. 앱 B hooks.pre_deploy 실행
   3.2. 앱 B 배포
   3.3. 성공/실패 hooks 실행
4. 모두 성공 → 전역 hooks.deploy.post 실행
   하나라도 실패 → 전역 hooks.deploy.on_failure 실행
```

### 7.3 환경변수 주입

**자동 주입 변수** (앱별 Hooks):
```python
# sbkube/commands/deploy.py
def execute_app_hooks(app: AppConfig, hook_type: str, namespace: str):
    """
    앱 Hooks 실행

    환경변수 주입:
    - SBKUBE_APP_NAME: 앱 이름
    - SBKUBE_NAMESPACE: 배포 네임스페이스
    - SBKUBE_RELEASE_NAME: Helm 릴리스 이름
    """
    env_vars = os.environ.copy()
    env_vars.update({
        "SBKUBE_APP_NAME": app.name,
        "SBKUBE_NAMESPACE": namespace,
        "SBKUBE_RELEASE_NAME": app.release_name or app.name,
    })

    hooks = app.hooks.get(hook_type, []) if app.hooks else []
    for cmd in hooks:
        subprocess.run(cmd, shell=True, env=env_vars, check=True)
```

### 7.4 에러 처리

- Hook 실패 시 배포 중단
- 명확한 오류 메시지 (종료 코드, stderr 출력)
- Dry-run 모드에서는 Hook 명령어만 표시 (실제 실행 X)

______________________________________________________________________

## 8. 검증 시스템

### 8.1 설정 파일 검증 (validate 명령어)

**검증 레이어**:
```
1. YAML 파싱 검증 (PyYAML)
   ↓
2. Pydantic 모델 검증 (타입, 필수 필드)
   ↓
3. 논리 검증 (앱 이름 중복, 순환 의존성)
   ↓
4. 앱 그룹 의존성 검증 (deps 필드)
   ↓
5. 리소스 존재 여부 검증 (선택, --strict 플래그)
```

**구현**:
```python
# sbkube/commands/validate.py
class ValidateCommand(EnhancedBaseCommand):
    def execute(self):
        # 1. YAML 파싱
        try:
            with open(self.config_file) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValidationError(f"YAML parsing error: {e}")

        # 2. Pydantic 검증
        try:
            config = Config(**data)
        except ValidationError as e:
            raise ValidationError(f"Schema validation error: {e}")

        # 3. 논리 검증
        validate_app_name_uniqueness(config)
        validate_circular_dependencies(config)

        # 4. 앱 그룹 의존성 검증
        warnings = validate_app_group_dependencies(config, tracker)
        for warning in warnings:
            logger.warning(warning)

        logger.success("✅ Validation passed")
```

### 8.2 배포 전 검증 (pre-deployment)

**자동 실행**: deploy 명령어 실행 시

**검증 항목**:
- Kubernetes 클러스터 연결 확인
- 대상 네임스페이스 존재 여부
- 의존성 도구 설치 확인 (helm, kubectl, git)

### 8.3 배포 후 검증 (post-deployment)

**선택적 실행**: `--verify` 플래그 (향후 지원)

**검증 항목**:
- Pod 상태 확인 (Running)
- Service 엔드포인트 확인
- Helm 릴리스 상태 (deployed)

______________________________________________________________________

## 9. 기술 스택 및 의존성

### 9.1 핵심 의존성

**Python 패키지** (`pyproject.toml`):
```toml
[project]
dependencies = [
    "click>=8.1",          # CLI 프레임워크
    "pyyaml>=6.0",         # YAML 파일 처리
    "pydantic>=2.7.1",     # 데이터 검증
    "sqlalchemy>=2.0.0",   # ORM (상태 관리)
    "rich>=13.0",          # 콘솔 출력
    "gitpython>=3.1",      # Git 연동
    "jinja2>=3.1",         # 템플릿 엔진
    "jsonschema>=4.23.0",  # JSON 스키마 검증
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.5",
    "pytest-cov>=4.0",
    "ruff>=0.4.0",
    "mypy>=1.10",
]
```

### 9.2 외부 도구 의존성

| 도구 | 버전 | 용도 | 필수 여부 |
|------|------|------|----------|
| **Helm** | v3.x | 차트 관리 및 배포 | ✅ 필수 |
| **kubectl** | v1.27+ | Kubernetes API 통신 | ✅ 필수 |
| **Git** | v2.x | Git 리포지토리 클론 | ⚠️ Git 타입 사용 시 |

### 9.3 런타임 요구사항

- **Python**: 3.12+ (엄격한 요구사항)
- **OS**: Linux, macOS, Windows WSL2
- **Kubernetes**: v1.24+ (k3s 권장)

### 9.4 빌드 및 배포

**빌드 시스템**: hatchling

**배포 플랫폼**:
- PyPI: `pip install sbkube`
- GitHub Releases: Binary 배포 (향후 계획)

______________________________________________________________________

## 10. 에러 처리 및 예외

### 10.1 에러 타입 계층

```python
# sbkube/exceptions.py
class SBKubeError(Exception):
    """Base exception"""

class ConfigurationError(SBKubeError):
    """설정 오류"""

class ValidationError(SBKubeError):
    """검증 오류"""

class DeploymentError(SBKubeError):
    """배포 오류"""

class CommandExecutionError(SBKubeError):
    """명령어 실행 오류"""
```

### 10.2 에러 메시지 형식

**예시**:
```
❌ ValidationError: config.yaml
  apps.redis.chart: field required
  apps.backend.type: invalid app type 'helmm' (did you mean 'helm'?)

Suggestions:
  - Check config.yaml syntax
  - Refer to docs/03-configuration/config-schema.md
```

### 10.3 복구 전략

- **네트워크 오류**: 자동 재시도 (최대 3회)
- **Pydantic 검증 오류**: 명확한 필드 위치 표시 + 수정 제안
- **Helm 배포 실패**: 롤백 옵션 제시

______________________________________________________________________

## 11. 성능 및 확장성

### 11.1 성능 목표

- **앱 100개 기준**: 전체 워크플로우 10분 이내
- **설정 파일 검증**: 1초 이내
- **상태 조회 쿼리**: 100ms 이내

### 11.2 병렬 처리

**현재**: 순차 실행 (앱 의존성 고려)

**향후 계획** (v0.8.x):
- DAG 기반 병렬 실행
- 독립적인 앱 동시 배포

### 11.3 캐싱 전략

- **Helm 차트**: 다운로드 캐시 (`.sbkube/charts/`)
- **Git 리포지토리**: 로컬 클론 재사용

______________________________________________________________________

## 12. 보안 고려사항

### 12.1 인증 및 권한

- **Kubernetes 인증**: kubeconfig 파일 의존 (표준 메커니즘)
- **Helm 저장소**: HTTPS 강제 (HTTP는 경고)
- **Git 리포지토리**: SSH 키 또는 토큰 인증

### 12.2 민감 정보 관리

- **Secrets**: Kubernetes Secrets 사용 (SBKube는 직접 관리 X)
- **설정 파일**: `.gitignore`에 values 파일 추가 권장
- **로그**: 민감 정보 마스킹 (비밀번호, 토큰 등)

### 12.3 RBAC 권한

**최소 권한 원칙**:
- 대상 네임스페이스에 대한 생성/수정/삭제 권한
- Helm 릴리스 설치 권한
- RBAC 리소스 관리 권한 (필요 시)

______________________________________________________________________

## 📚 관련 문서

### 기술 문서

- **[ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)** - 상세 아키텍처 설계
- **[API_CONTRACT.md](docs/10-modules/sbkube/API_CONTRACT.md)** - API 계약 및 인터페이스
- **[config-schema.md](docs/03-configuration/config-schema.md)** - 설정 파일 스키마 상세
- **[DEPENDENCIES.md](docs/10-modules/sbkube/DEPENDENCIES.md)** - 의존성 및 라이선스

### 제품 문서

- **[PRODUCT.md](PRODUCT.md)** - 제품 정의 (무엇을, 왜, 누구를 위해)
- **[product-spec.md](docs/00-product/product-spec.md)** - 기능 명세 및 사용자 시나리오

### 개발 가이드

- **[개발자 가이드](docs/04-development/README.md)** - 개발 환경 구성 및 기여 방법
- **[코딩 표준](docs/04-development/coding-standards.md)** - Python 코드 스타일 가이드
- **[테스팅](docs/04-development/testing.md)** - 테스트 작성 및 실행

______________________________________________________________________

**🎯 문서 유형**: 기술 명세서 (Technical Specification) **독자**: 개발자, QA, DevOps 엔지니어 **초점**: 기능의 기술적 구현 방법

**💡 제품 정의 및 사용자 가치는 [PRODUCT.md](PRODUCT.md)를 참조하세요**
