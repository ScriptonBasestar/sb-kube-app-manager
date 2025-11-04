---
type: Module Overview
audience: Developer
topics: [module, structure, organization]
llm_priority: medium
last_updated: 2025-01-04
---

# SBKube 모듈 정의

## 모듈 개요

- **이름**: sbkube
- **타입**: Python CLI Application (Monolithic)
- **역할**: Kubernetes 배포 자동화 CLI 도구
- **책임**: Helm, YAML, Git 소스 통합 및 k3s 클러스터 배포 관리

## 모듈 경계 및 책임

### 이 모듈이 하는 것 (Responsibilities)

- ✅ CLI 명령어 제공 (prepare, build, template, deploy 등)
- ✅ 설정 파일 파싱 및 검증 (Pydantic)
- ✅ 외부 소스 다운로드 (Helm, Git, OCI)
- ✅ Helm 차트 렌더링 및 배포
- ✅ YAML 매니페스트 적용
- ✅ 배포 상태 관리 (SQLAlchemy)
- ✅ 사용자 인터페이스 (Rich Console)
- ✅ 검증 시스템 (사전/사후 배포)

### 이 모듈이 하지 않는 것 (Boundaries)

- ❌ Kubernetes 클러스터 관리 (k3s 설치/업그레이드)
- ❌ 컨테이너 이미지 빌드
- ❌ CI/CD 파이프라인 오케스트레이션
- ❌ 모니터링/로깅 수집

### 외부 의존성 (External Dependencies)

- **Helm CLI v3.x**: 차트 관리 및 렌더링
- **kubectl**: Kubernetes API 접근
- **Git CLI**: 리포지토리 클론
- **Kubernetes API**: 클러스터 리소스 관리

## 내부 구조

### 디렉토리 구조

```
sbkube/
├── cli.py                    # CLI 진입점 (Click 프레임워크)
├── commands/                 # 명령어 구현
│   ├── prepare.py           # 소스 준비
│   ├── build.py             # 앱 빌드
│   ├── template.py          # 템플릿 렌더링
│   ├── deploy.py            # 배포 실행
│   ├── upgrade.py           # 릴리스 업그레이드
│   ├── delete.py            # 리소스 삭제
│   ├── validate.py          # 설정 검증
│   ├── version.py           # 버전 정보
│   ├── run.py               # 실행 명령
│   ├── init.py              # 초기화
│   └── doctor.py            # 시스템 진단
├── models/                  # Pydantic 데이터 모델
│   ├── config_model.py      # config.yaml 모델
│   └── sources_model.py     # sources.yaml 모델
├── state/                   # 상태 관리 시스템
│   ├── database.py          # SQLAlchemy 설정
│   ├── tracker.py           # 상태 추적
│   └── rollback.py          # 롤백 관리
├── utils/                   # 유틸리티
│   ├── base_command.py      # 명령어 기본 클래스
│   ├── logger.py            # Rich 기반 로깅
│   ├── cli_check.py         # CLI 도구 검증
│   ├── helm_util.py         # Helm 유틸리티
│   ├── file_loader.py       # 파일 로딩
│   ├── kubeconfig_info.py   # Kubeconfig 정보
│   ├── validation_system.py # 검증 시스템
│   ├── validation_report.py # 검증 리포트
│   ├── progress_manager.py  # 진행 상태 관리
│   ├── retry.py             # 재시도 로직
│   └── pattern_analyzer.py  # 패턴 분석
├── validators/              # 검증 시스템
│   ├── basic_validators.py  # 기본 검증
│   ├── configuration_validators.py # 설정 검증
│   ├── dependency_validators.py    # 의존성 검증
│   ├── environment_validators.py   # 환경 검증
│   └── pre_deployment_validators.py # 배포 전 검증
├── diagnostics/             # 시스템 진단
│   └── kubernetes_checks.py # Kubernetes 체크
├── fixes/                   # 자동 수정 도구
├── templates/               # 초기화 템플릿
│   └── basic/               # 기본 템플릿
└── exceptions.py            # 예외 정의
```

### 레이어 아키텍처

```
┌─────────────────────────────────────────┐
│         CLI Layer (cli.py)              │ ← Click Framework
├─────────────────────────────────────────┤
│      Commands Layer (commands/)         │ ← Business Logic
├─────────────────────────────────────────┤
│   Models & Validation (models/)         │ ← Pydantic
├─────────────────────────────────────────┤
│  Utils & State (utils/, state/)         │ ← Infrastructure
├─────────────────────────────────────────┤
│  External Tools (Helm, kubectl, Git)    │ ← Dependencies
└─────────────────────────────────────────┘
```

## 핵심 패턴

### 1. BaseCommand 패턴

모든 명령어는 `BaseCommand` 클래스를 상속:

```python
# sbkube/utils/base_command.py
class BaseCommand:
    def __init__(self, app_dir, base_dir, ...):
        self.config = self.load_config(app_dir)
        self.logger = Logger()

    def load_config(self, app_dir):
        # 설정 파일 로딩 및 Pydantic 검증
        pass

    def execute(self):
        # 명령어 실행 로직 (서브클래스에서 구현)
        raise NotImplementedError
```

### 2. Pydantic 검증 패턴

설정 파일은 Pydantic 모델로 강타입 검증:

```python
# sbkube/models/config_model.py
class AppConfig(BaseModel):
    name: str
    type: str
    enabled: bool = True

class SBKubeConfig(BaseModel):
    namespace: str
    apps: List[AppConfig]
```

### 3. Rich Console 패턴

모든 출력은 Rich를 통해 사용자 친화적으로:

```python
# sbkube/utils/logger.py
from rich.console import Console

console = Console()
console.print("[green]✅ Deployment successful[/green]")
console.print_table(data)
```

## API 계약 (Internal)

### 공통 인터페이스

모든 명령어 클래스는 다음 메서드 제공:

- `load_config()`: 설정 로딩
- `execute()`: 명령어 실행
- `handle_error()`: 오류 처리

### 데이터 모델

- `SBKubeConfig`: config.yaml 전체 모델
- `SourcesConfig`: sources.yaml 전체 모델
- `AppConfig`: 개별 앱 설정
- `DeploymentState`: 배포 상태 (SQLAlchemy ORM)

## 의존성 명세

### Python 패키지 의존성

```toml
dependencies = [
  "click>=8.1",          # CLI 프레임워크
  "pyyaml",              # YAML 파싱
  "gitpython",           # Git 연동
  "jinja2",              # 템플릿 엔진
  "rich",                # 콘솔 UI
  "pytest>=8.3.5",       # 테스트
  "toml>=0.10.2",        # TOML 파싱
  "jsonschema>=4.23.0",  # JSON 스키마
  "pydantic>=2.7.1",     # 데이터 검증
  "sqlalchemy>=2.0.0",   # ORM
  "requests>=2.31.0",    # HTTP 클라이언트
  "kubernetes>=28.1.0",  # Kubernetes API
]
```

### 외부 CLI 도구

- **Helm v3.x** (필수): `helm version` 확인
- **kubectl** (필수): Kubernetes API 접근
- **Git** (선택): Git 리포지토리 사용 시

### 런타임 환경

- Python 3.12+
- Linux/macOS (Windows WSL2)

## 확장 포인트

### 1. 새 명령어 추가

1. `sbkube/commands/` 디렉토리에 모듈 생성
1. `BaseCommand` 상속 클래스 작성
1. `cli.py`에 Click 명령어 등록

### 2. 새 앱 타입 추가

1. `models/config_model.py`에 타입 정의
1. 각 명령어에서 타입별 로직 추가
1. `docs/02-features/application-types.md` 문서화

### 3. 새 검증 로직 추가

1. `validators/` 디렉토리에 검증 클래스 작성
1. `validation_system.py`에 등록
1. 명령어에서 호출

## 테스트 전략

### 단위 테스트

- 각 명령어 클래스별 테스트
- Pydantic 모델 검증 테스트
- 유틸리티 함수 테스트

### 통합 테스트

- 전체 워크플로우 테스트
- 외부 도구 연동 테스트 (Helm, kubectl)
- 상태 관리 시스템 테스트

### E2E 테스트

- testcontainers[k3s] 사용
- 실제 배포 시나리오 테스트
- 롤백 시나리오 테스트

## 성능 고려사항

### 최적화 전략

- 병렬 처리: 여러 앱 동시 다운로드 (향후 구현)
- 캐싱: 다운로드된 차트 재사용
- 지연 로딩: 필요한 모듈만 임포트

### 리소스 사용

- 메모리: 대규모 차트 렌더링 시 증가
- 디스크: 다운로드된 소스 보관 (charts/, repos/)
- 네트워크: 외부 소스 다운로드 시 대역폭

## 모니터링 및 로깅

### 로그 레벨

- **DEBUG**: --verbose 옵션 시 상세 로그
- **INFO**: 일반 작업 진행 상황
- **WARNING**: 경고 메시지
- **ERROR**: 오류 발생 (배포 계속)
- **CRITICAL**: 치명적 오류 (배포 중단)

### 메트릭 (향후 구현)

- 배포 성공률
- 평균 배포 시간
- 오류 빈도

---

**문서 버전**: 1.0 **마지막 업데이트**: 2025-10-20 **관련 문서**:

- [ARCHITECTURE.md](ARCHITECTURE.md) - 상세 아키텍처
- [API_CONTRACT.md](API_CONTRACT.md) - API 계약 (향후 작성)
- [DEPENDENCIES.md](DEPENDENCIES.md) - 의존성 명세 (향후 작성)
