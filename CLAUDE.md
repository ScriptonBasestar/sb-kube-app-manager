# CLAUDE.md - SBKube AI 작업 가이드

> 이 문서는 AI 에이전트(Claude Code 등)가 SBKube 프로젝트를 효율적으로 이해하고 작업할 수 있도록 통합된 가이드를 제공합니다.

______________________________________________________________________

## 📋 목차

1. [프로젝트 개요](#1-%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8-%EA%B0%9C%EC%9A%94)
1. [AI 컨텍스트 네비게이션](#2-ai-%EC%BB%A8%ED%85%8D%EC%8A%A4%ED%8A%B8-%EB%84%A4%EB%B9%84%EA%B2%8C%EC%9D%B4%EC%85%98)
1. [개발 환경 및 워크플로우](#3-%EA%B0%9C%EB%B0%9C-%ED%99%98%EA%B2%BD-%EB%B0%8F-%EC%9B%8C%ED%81%AC%ED%94%8C%EB%A1%9C%EC%9A%B0)
1. [코드 스타일 및 규약](#4-%EC%BD%94%EB%93%9C-%EC%8A%A4%ED%83%80%EC%9D%BC-%EB%B0%8F-%EA%B7%9C%EC%95%BD)
1. [아키텍처 가이드](#5-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98-%EA%B0%80%EC%9D%B4%EB%93%9C)
1. [AI 에이전트 특화 지침](#6-ai-%EC%97%90%EC%9D%B4%EC%A0%84%ED%8A%B8-%ED%8A%B9%ED%99%94-%EC%A7%80%EC%B9%A8)
1. [테스트 및 품질 관리](#7-%ED%85%8C%EC%8A%A4%ED%8A%B8-%EB%B0%8F-%ED%92%88%EC%A7%88-%EA%B4%80%EB%A6%AC)
1. [트러블슈팅](#8-%ED%8A%B8%EB%9F%AC%EB%B8%94%EC%8A%88%ED%8C%85)
1. [참고 자료](#9-%EC%B0%B8%EA%B3%A0-%EC%9E%90%EB%A3%8C)

______________________________________________________________________

## 1. 프로젝트 개요

### 1.1 기본 정보

- **제품**: SBKube - k3s용 Kubernetes 배포 자동화 CLI 도구
- **아키텍처**: 모놀리식 Python CLI 애플리케이션
- **기술 스택**: Python 3.12+, Click, Pydantic, SQLAlchemy, Rich
- **개발 단계**: v0.6.0 (성숙기 - 기능 확장 중)
- **목적**: Helm, YAML, Git 소스를 통합하여 Kubernetes 배포 자동화

### 1.2 핵심 가치

- **통합성**: 다양한 배포 소스를 하나의 선언적 설정으로 통합
- **자동화**: 수동 작업 최소화 및 일관된 배포 절차
- **검증**: Pydantic 기반 강타입 검증 시스템
- **상태 관리**: SQLAlchemy 기반 배포 히스토리 추적

### 1.3 핵심 워크플로우

```
prepare → build → template → deploy
   ↓        ↓         ↓         ↓
소스준비  앱빌드   템플릿화   클러스터배포
```

또는 **통합 실행**: `sbkube apply` (4단계 자동 실행)

### 1.4 주요 디렉토리 구조

```
sbkube/
├── cli.py                    # CLI 진입점 (Click 프레임워크)
├── commands/                 # 명령어 구현 (prepare, build, template, deploy 등)
├── models/                   # Pydantic 데이터 모델 (설정 검증)
├── state/                    # SQLAlchemy 상태 관리
├── utils/                    # 유틸리티 (logger, helm_util, validation 등)
├── validators/               # 사전/사후 배포 검증
├── diagnostics/              # 시스템 진단 도구
└── templates/                # 초기화 템플릿

docs/
├── 00-product/               # 제품 정의 (최우선 참조)
├── 01-getting-started/       # 빠른 시작 가이드
├── 02-features/              # 기능 및 명령어 설명
├── 03-configuration/         # 설정 파일 가이드
├── 04-development/           # 개발자 가이드
├── 10-modules/               # 모듈별 상세 문서
│   └── sbkube/               # SBKube 모듈 문서
└── 99-internal/              # 내부 문서 (백로그, 계획)

tests/
├── commands/                 # 명령어 단위 테스트
├── models/                   # 모델 검증 테스트
├── integration/              # 통합 테스트
└── e2e/                      # E2E 테스트 (k3s)

.sbkube/                      # SBKube 작업 디렉토리 (프로젝트별, .gitignore)
├── charts/                   # Helm 차트 다운로드 (prepare)
├── repos/                    # Git 리포지토리 clone (prepare)
├── build/                    # 차트 빌드 결과 (build)
└── rendered/                 # 템플릿 렌더링 결과 (template)
```

______________________________________________________________________

## 2. AI 컨텍스트 네비게이션

### 2.1 컨텍스트 계층 구조

```
Level 0 (최우선): 제품 개요
  └─ PRODUCT.md (진입점)

Level 1 (제품 정의): 상세 제품 문서
  ├─ docs/00-product/product-definition.md
  ├─ docs/00-product/product-spec.md
  ├─ docs/00-product/vision-roadmap.md
  └─ docs/00-product/target-users.md

Level 2 (모듈 아키텍처): 구현 설계
  ├─ docs/10-modules/sbkube/MODULE.md
  ├─ docs/10-modules/sbkube/ARCHITECTURE.md
  └─ docs/10-modules/sbkube/API_CONTRACT.md

Level 3 (기능 문서): 사용자 가이드
  ├─ docs/02-features/commands.md
  ├─ docs/02-features/application-types.md
  └─ docs/03-configuration/config-schema.md

Level 4 (구현 코드): 소스 파일
  ├─ sbkube/commands/
  ├─ sbkube/models/
  └─ sbkube/utils/
```

### 2.2 질의 유형별 라우팅

#### 2.2.1 제품 관련 질의

**질의 패턴**:

- "SBKube가 뭔가요?"
- "이 프로젝트의 목적은?"
- "어떤 문제를 해결하나요?"
- "주요 기능은?"

**라우팅 경로**:

```
Primary: PRODUCT.md
Secondary: docs/00-product/product-definition.md
Fallback: docs/00-product/product-spec.md
```

**컨텍스트 로딩 순서**:

1. [PRODUCT.md](PRODUCT.md) (간결한 개요)
1. [docs/00-product/product-definition.md](docs/00-product/product-definition.md) (문제 정의, 솔루션)
1. [docs/00-product/target-users.md](docs/00-product/target-users.md) (사용자 페르소나)

#### 2.2.2 아키텍처 관련 질의

**질의 패턴**:

- "시스템 아키텍처는?"
- "모듈 구조는 어떻게 되나요?"
- "데이터 흐름은?"
- "설계 패턴은?"

**라우팅 경로**:

```
Primary: docs/10-modules/sbkube/ARCHITECTURE.md
Secondary: docs/02-features/architecture.md
Fallback: PRODUCT.md (Architecture 섹션)
```

**컨텍스트 로딩 순서**:

1. [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md) (전체 구조)
1. [docs/02-features/architecture.md](docs/02-features/architecture.md) (기능별 아키텍처)
1. 소스 코드 (sbkube/cli.py, sbkube/commands/)

#### 2.2.3 기능 및 사용법 질의

**질의 패턴**:

- "prepare 명령어는 어떻게 사용하나요?"
- "Helm 차트 배포 방법은?"
- "config.yaml 작성법은?"
- "어떤 앱 타입이 지원되나요?"

**라우팅 경로**:

```
Primary: docs/00-product/product-spec.md
Secondary: docs/02-features/commands.md
Fallback: docs/01-getting-started/README.md
```

**컨텍스트 로딩 순서**:

1. [docs/00-product/product-spec.md](docs/00-product/product-spec.md) (기능 명세)
1. [docs/02-features/commands.md](docs/02-features/commands.md) (명령어 상세)
1. [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md) (설정 예제)
1. [examples/](examples/) (실제 사용 예제)

#### 2.2.4 구현 및 개발 질의

**질의 패턴**:

- "새 명령어를 어떻게 추가하나요?"
- "Pydantic 모델은 어디 있나요?"
- "BaseCommand 패턴은?"
- "테스트는 어떻게 작성하나요?"

**라우팅 경로**:

```
Primary: docs/10-modules/sbkube/docs/20-implementation/
Secondary: docs/04-development/README.md
Fallback: 소스 코드 (sbkube/)
```

**컨텍스트 로딩 순서**:

1. 이 문서 (CLAUDE.md) - 개발 환경 및 규약
1. [docs/04-development/README.md](docs/04-development/README.md) (개발자 가이드)
1. [docs/10-modules/sbkube/MODULE.md](docs/10-modules/sbkube/MODULE.md) (모듈 구조)
1. 소스 코드 (관련 모듈)

#### 2.2.5 문제 해결 질의

**질의 패턴**:

- "{오류 메시지}"
- "배포가 실패했어요"
- "Helm 릴리스가 생성되지 않아요"
- "설정 검증 오류가 나요"

**라우팅 경로**:

```
Primary: docs/07-troubleshooting/README.md
Secondary: docs/10-modules/sbkube/docs/40-maintenance/troubleshooting.md
Fallback: GitHub Issues
```

**컨텍스트 로딩 순서**:

1. [docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md) (일반 문제)
1. 오류 메시지 기반 검색 (코드베이스)
1. 관련 명령어 구현 (sbkube/commands/)
1. 검증 로직 (sbkube/validators/)

### 2.3 컨텍스트 우선순위 규칙

#### Rule 1: 제품 우선 (Product-First)

모든 질의는 제품 컨텍스트부터 시작합니다.

```
질의 → PRODUCT.md → docs/00-product/ → 구체적 문서
```

#### Rule 2: 모듈 경계 준수

모듈별 질의는 해당 모듈 문서를 우선 참조합니다.

```
SBKube 구현 질의 → docs/10-modules/sbkube/ → sbkube/ 소스
```

#### Rule 3: 의미 단위 청킹

긴 문서는 섹션 단위로 로딩합니다.

```
product-spec.md → 섹션별 4000 토큰 이하로 분할
```

#### Rule 4: 크로스 레퍼런스 활용

관련 문서는 자동으로 연결합니다.

```
product-definition.md → product-spec.md (기능 상세)
ARCHITECTURE.md → commands/ (구현 코드)
```

### 2.4 토큰 효율성 가이드

#### 최소 컨텍스트 (< 10K 토큰)

**간단한 질의**: "SBKube가 뭔가요?"

```
- PRODUCT.md (전체)
- docs/00-product/product-definition.md (개요 섹션)
```

#### 중간 컨텍스트 (10K-50K 토큰)

**기능 질의**: "Helm 차트 배포 방법은?"

```
- PRODUCT.md
- docs/00-product/product-spec.md (섹션 1.1, 1.4, 2.1)
- docs/02-features/commands.md (prepare, deploy 섹션)
- examples/basic/config.yaml
```

#### 대규모 컨텍스트 (50K-100K 토큰)

**구현 작업**: "새 명령어 추가"

```
- CLAUDE.md
- docs/10-modules/sbkube/ARCHITECTURE.md
- sbkube/cli.py
- sbkube/commands/ (전체 또는 샘플)
- sbkube/utils/base_command.py
- tests/commands/ (샘플)
```

### 2.5 의미 기반 인덱스

#### 핵심 개념 → 문서 매핑

**제품 비전**

- 키워드: 제품, 비전, 목표, 가치, 문제 해결
- 문서: [docs/00-product/product-definition.md](docs/00-product/product-definition.md),
  [docs/00-product/vision-roadmap.md](docs/00-product/vision-roadmap.md)

**워크플로우**

- 키워드: prepare, build, template, deploy, 워크플로우, 배포
- 문서: [docs/00-product/product-spec.md](docs/00-product/product-spec.md) (섹션 1),
  [docs/02-features/commands.md](docs/02-features/commands.md)

**설정 관리**

- 키워드: config.yaml, sources.yaml, Pydantic, 검증
- 문서: [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md),
  [sbkube/models/config_model.py](sbkube/models/config_model.py)

**상태 관리**

- 키워드: history, rollback, SQLAlchemy, 배포 상태
- 문서: [docs/00-product/product-spec.md](docs/00-product/product-spec.md) (섹션 4), [sbkube/state/](sbkube/state/)

**앱 타입**

- 키워드: helm, yaml, action, http, exec
- 문서: [docs/02-features/application-types.md](docs/02-features/application-types.md)

______________________________________________________________________

## 3. 개발 환경 및 워크플로우

### 3.1 환경 설정

#### Python 환경 (uv 사용 필수)

```bash
# 가상환경 생성 및 의존성 설치
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync

# Editable 모드 설치
uv pip install -e .
```

#### 개발 환경 세부사항

- **Python 버전**: 3.12 (엄격한 요구사항)
- **패키지 매니저**: uv (pip 직접 사용 금지)
- **운영체제**: macOS, Linux (Manjaro 테스트 완료)
- **중요**: requirements.txt 생성 금지 - `uv add` 명령어만 사용

#### 필수 외부 도구

- **Helm v3.x**: `helm version` 확인
- **kubectl**: Kubernetes 클러스터 접근
- **Git**: Git 리포지토리 사용 시

### 3.2 개발 워크플로우 명령어

#### 빠른 참조 (Quick Reference)

**가장 자주 사용하는 명령어**:

```bash
# 1. 개발 설치 (dev + test 의존성 포함)
make install-all

# 2. 빠른 테스트 (E2E 제외, 빠른 피드백)
make test-quick

# 3. 코드 품질 검사 및 자동 수정
make lint-fix

# 4. 전체 CI 체크 (lint + test + coverage)
make ci

# 5. 특정 테스트만 실행
pytest tests/unit/commands/test_deploy.py -v
```

#### 코드 품질 검사

```bash
# 린팅 (읽기 전용, 변경사항 미리보기)
make lint-check

# 린팅 (자동 수정 포함)
make lint-fix

# 린팅 (위험한 자동 수정 포함)
make lint-fix UNSAFE_FIXES=1

# 엄격한 린팅 (모든 규칙 적용)
make lint-strict

# 개별 도구 실행
uv run ruff check sbkube/
uv run mypy sbkube/
```

#### 테스트 실행

```bash
# 모든 테스트 실행
uv run pytest tests/

# 특정 테스트 모듈
uv run pytest tests/test_prepare.py -v
uv run pytest tests/test_build.py -v

# 커버리지 측정
uv run pytest --cov=sbkube --cov-report=html

# Makefile 사용
make test
```

#### 빌드 및 배포

```bash
# 패키지 빌드
uv build

# PyPI 배포 (twine 사용)
uv run -m twine upload dist/*

# 로컬 재설치 (강제)
uv pip install --force-reinstall --no-deps --upgrade .
```

#### 문서 검증

```bash
# Markdown 포맷 확인
uv run mdformat --check docs/
```

#### 보안 검사

```bash
# 보안 취약점 스캔
uv run bandit -r sbkube/

# Makefile 사용
make security
```

### 3.3 SBKube CLI 사용 (개발 중)

#### 기본 워크플로우

```bash
# Editable 설치 후
uv pip install -e .

# 전체 워크플로우
sbkube prepare --app-dir examples/basic
sbkube build --app-dir examples/basic
sbkube template --app-dir examples/basic --output-dir /tmp/rendered
sbkube deploy --app-dir examples/basic --namespace test --dry-run

# 통합 실행 (v0.2.1+)
sbkube apply --app-dir examples/basic --namespace test
```

#### 상태 관리

```bash
sbkube state list
sbkube state history --namespace test
```

#### 설정 검증

```bash
sbkube validate --app-dir examples/basic
```

#### 도움말

```bash
sbkube --help
sbkube deploy --help
```

### 3.4 Kubernetes 테스트 환경

#### Kind 클러스터 사용

```bash
# 테스트 클러스터 생성
kind create cluster --name sbkube-test
kubectl config use-context kind-sbkube-test

# SBKube 명령어 실행
uv run -m sbkube.cli deploy --base-dir examples/k3scode --app-dir memory --namespace data-memory

# 클러스터 삭제
kind delete cluster --name sbkube-test
```

### 3.5 개발 효율성 가이드

#### 작업 시작 시

- **즉시 실행**: 변경사항 적용 후 바로 다음 단계 제안 (불필요한 확인 질문 지양)
- **Indentation 주의**: Python과 YAML 파일 작업 시 indent 오류 방지
- **최소 변경**: 필요한 라인만 수정하여 불필요한 변경 최소화

#### 오류 수정 시

- **테스트 동기화**: 오류 수정 시 관련 테스트도 함께 업데이트
- **근본 원인**: 증상이 아닌 원인을 수정
- **회귀 방지**: 버그가 발견된 시나리오를 예제와 테스트로 추가

______________________________________________________________________

## 4. 코드 스타일 및 규약

### 4.1 Python 스타일

- **언어**: Python 3.12+
- **포매터**: black (line-length: 120)
- **린터**: ruff (설정: ruff.toml)
- **타입 체커**: mypy (설정: mypy.ini)
- **컨벤션**: PEP 8
  - 함수/변수: `snake_case`
  - 클래스: `PascalCase`
  - 상수: `UPPER_SNAKE_CASE`

### 4.2 Import 순서

```python
# 1. 표준 라이브러리
import os
from pathlib import Path

# 2. 서드파티 라이브러리
import click
from pydantic import BaseModel

# 3. 로컬 모듈
from sbkube.utils.logger import console
from sbkube.models.config_model import SBKubeConfig
```

### 4.3 Docstring 규약

모든 public 함수/클래스에 docstring 필수:

```python
def deploy_application(app_name: str, namespace: str) -> bool:
    """애플리케이션을 Kubernetes 클러스터에 배포합니다.

    Args:
        app_name: 배포할 애플리케이션 이름
        namespace: 배포 대상 네임스페이스

    Returns:
        bool: 배포 성공 시 True, 실패 시 False

    Raises:
        DeploymentError: 배포 중 오류 발생 시
    """
```

### 4.4 에러 처리

```python
from sbkube.exceptions import SbkubeError

try:
    result = risky_operation()
except SbkubeError as e:
    console.print(f"[red]Error: {e}[/red]")
    raise
```

______________________________________________________________________

## 5. 아키텍처 가이드

### 5.1 고수준 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    SBKube CLI                           │
│  (Click Framework + Rich Console)                       │
└────────────┬────────────────────────────────────────────┘
             │
             ├─► Commands Layer (prepare/build/template/deploy)
             ├─► Models Layer (Pydantic validation)
             ├─► State Management (SQLAlchemy)
             └─► Utils & Validators
                      │
                      ▼
         ┌──────────────────────────┐
         │  External Dependencies   │
         ├──────────────────────────┤
         │ • Helm CLI               │
         │ • kubectl                │
         │ • Git                    │
         │ • Kubernetes API         │
         └──────────────────────────┘
```

### 5.2 레이어 아키텍처

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
│  - 명령어별 비즈니스 로직                                 │
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
└────────────────────────────────────────────────────────┘
```

### 5.3 핵심 패턴

#### BaseCommand 패턴

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

#### Pydantic 검증 패턴

설정 파일은 Pydantic 모델로 강타입 검증:

```python
# sbkube/models/config_model.py
class AppConfig(BaseModel):
    name: str
    type: str
    enabled: bool = True
    specs: dict

class SBKubeConfig(BaseModel):
    namespace: str
    apps: List[AppConfig]
```

#### Rich Console 패턴

모든 출력은 Rich를 통해 사용자 친화적으로:

```python
# sbkube/utils/logger.py
from rich.console import Console

console = Console()
console.print("[green]✅ Deployment successful[/green]")
console.print_table(data)
```

#### EnhancedBaseCommand 패턴 (v0.6.0+)

v0.6.0부터 `EnhancedBaseCommand`가 도입되어 더 나은 설정 관리를 제공:

```python
# sbkube/utils/base_command.py
class EnhancedBaseCommand:
    def __init__(
        self,
        base_dir: str = ".",
        app_config_dir: str = "config",
        cli_namespace: str | None = None,
        validate_on_load: bool = True,
        use_inheritance: bool = True,
    ):
        self.BASE_DIR = Path(base_dir).resolve()
        self.APP_CONFIG_DIR = self.BASE_DIR / app_config_dir
        self.SBKUBE_WORK_DIR = self._determine_sbkube_dir()

        # Configuration manager with inheritance support
        self.config_manager = ConfigManager(
            base_dir=self.BASE_DIR,
            schema_dir=self.SCHEMA_DIR if self.SCHEMA_DIR.exists() else None,
        )
```

**주요 기능**:
- 설정 상속 지원 (Configuration inheritance)
- 자동 검증 (Automatic validation)
- sources.yaml 위치 기반 작업 디렉토리 결정

### 5.4 데이터 흐름

```
설정 파일 → Pydantic 모델 → 검증 → 명령어 실행 → 상태 저장
```

### 5.5 App-Group 기반 관리 (v0.6.0+)

애플리케이션을 논리적 그룹으로 관리:

#### 네이밍 컨벤션

`app_{priority}_{category}_{name}` 형식 사용:

```yaml
apps:
  - name: app_000_infra_network  # priority: 000, category: infra
    type: helm
    chart: cilium/cilium

  - name: app_010_data_postgresql  # priority: 010, category: data
    type: helm
    chart: cloudnative-pg/cloudnative-pg
    deps:
      - app_000_infra_network

  - name: app_020_app_backend  # priority: 020, category: app
    type: helm
    chart: ./charts/backend
    deps:
      - app_010_data_postgresql
```

#### 새로운 상태 관리 명령어 (v0.6.0)

```bash
# 클러스터 상태 확인
sbkube status

# App-group별 그룹핑
sbkube status --by-group

# 특정 app-group 상세 조회
sbkube status app_000_infra_network

# 의존성 트리 시각화
sbkube status --deps

# 배포 히스토리
sbkube history

# 두 배포 비교
sbkube history --diff dep_123,dep_456

# 롤백
sbkube rollback dep_123
```

**상세 정보**: [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)

______________________________________________________________________

## 6. AI 에이전트 특화 지침

### 6.1 컨텍스트 우선순위

작업 시작 시 다음 순서로 문서를 참조:

1. **[PRODUCT.md](PRODUCT.md)** → 제품 개요 이해
1. **[docs/00-product/](docs/00-product/)** → 제품 정의 및 명세
1. **[docs/10-modules/sbkube/MODULE.md](docs/10-modules/sbkube/MODULE.md)** → 모듈 구조
1. **소스 코드** → 구체적 구현

**질의 유형별**:

- **기능 질의**: [docs/00-product/product-spec.md](docs/00-product/product-spec.md)
- **아키텍처 질의**: [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)
- **구현 질의**: [docs/02-features/](docs/02-features/) 및 소스 코드

### 6.2 코드 변경 시 체크리스트

#### 모든 코드 변경 시

1. **관련 테스트 실행**

   ```bash
   uv run pytest tests/
   ```

1. **문서 동기화 확인**

   - 특히 `product-spec.md`, `commands.md` 업데이트
   - 새 기능 추가 시 [docs/00-product/product-spec.md](docs/00-product/product-spec.md) 업데이트 필수

1. **타입 힌트 검증**

   ```bash
   uv run mypy sbkube/
   ```

1. **Pydantic 모델 변경 시**

   - JSON 스키마 재생성
   - 관련 검증 테스트 업데이트

### 6.3 새 기능 개발 시

1. **제품 스펙 확인**

   - [product-spec.md](docs/00-product/product-spec.md)와 일치성 확인
   - 제품 비전에 부합하는지 검토

1. **BaseCommand 패턴 준수**

   - `sbkube/utils/base_command.py` 상속
   - 공통 메서드 활용

1. **Rich Console 사용**

   - `sbkube/utils/logger.py` 임포트
   - 색상별 로깅 (`[green]`, `[red]`, `[yellow]` 등)

1. **Pydantic 모델 검증 추가**

   - `sbkube/models/` 디렉토리에 모델 정의
   - 런타임 검증 로직 구현

### 6.4 새 명령어 추가 시

1. **명령어 모듈 생성**

   - `sbkube/commands/` 디렉토리에 파일 생성
   - `EnhancedBaseCommand` 또는 `BaseCommand` 상속 클래스 작성

1. **CLI 등록**

   - `cli.py`에 Click 명령어 등록
   - `SbkubeGroup.COMMAND_CATEGORIES`에 카테고리 등록

#### 명령어 카테고리 시스템

새 명령어는 적절한 카테고리에 등록:

```python
# sbkube/cli.py
class SbkubeGroup(click.Group):
    COMMAND_CATEGORIES = {
        "핵심 워크플로우": ["prepare", "build", "template", "deploy"],
        "통합 명령어": ["apply"],
        "상태 관리": ["status", "history", "rollback"],
        "업그레이드/삭제": ["upgrade", "delete"],
        "유틸리티": ["init", "validate", "doctor", "version"],
    }
```

1. **문서화**

   - [docs/02-features/commands.md](docs/02-features/commands.md)에 명령어 추가
   - 사용 예제 포함

1. **테스트 작성**

   - `tests/commands/` 디렉토리에 테스트 케이스 작성
   - 성공 케이스 및 에러 케이스 모두 포함

### 6.5 버그 수정 시

1. **재현 테스트 작성**

   - 버그를 재현하는 테스트 케이스 먼저 작성

1. **근본 원인 분석**

   - 증상이 아닌 원인 수정

1. **최소한의 변경**

   - 필요한 부분만 수정
   - 관련 없는 리팩토링 지양

1. **예제 및 엣지 케이스 추가 (중요)**

   - 버그가 발견된 시나리오를 `examples/` 디렉토리에 예제로 추가
   - 엣지 케이스(edge case)에 대한 테스트 작성
   - 동일한 문제가 재발하지 않도록 회귀 테스트(regression test) 구성

   **예제 추가 위치**:
   ```
   examples/
   ├── edge-cases/           # 엣지 케이스 예제
   │   ├── oci-registry/     # OCI 레지스트리 관련
   │   ├── deprecated-repo/  # Deprecated 저장소
   │   └── typo-config/      # 설정 오타 케이스
   └── prepare/              # 명령어별 예제
       └── helm-oci/         # 실제 사용 예제
   ```

   **테스트 추가 위치**:
   ```
   tests/
   ├── e2e/                  # E2E 테스트
   │   └── test_edge_cases.py
   ├── integration/          # 통합 테스트
   └── unit/                 # 단위 테스트
   ```

   **실제 적용 예시** (2025-10-30):
   - **버그**: OCI 레지스트리 미지원, Deprecated 저장소, 레포 이름 오타
   - **추가된 예제**: `examples/prepare/helm-oci/`
   - **추가된 테스트**: `tests/e2e/test_prepare_examples.py::test_prepare_pull_helm_oci`
   - **문서화**: `docs/07-troubleshooting/README.md`에 3가지 케이스 추가

1. **문서 업데이트**

   - [docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md)에 해결 방법 추가 (필요 시)
   - 버그 유형별로 구체적인 오류 메시지와 해결 방법 명시
   - 실제 사용자가 마주칠 수 있는 시나리오 중심으로 작성

### 6.6 문서화 요구사항

#### 필수 업데이트 대상

- **새 기능**: [docs/00-product/product-spec.md](docs/00-product/product-spec.md)
- **명령어 변경**: [docs/02-features/commands.md](docs/02-features/commands.md)
- **아키텍처 변경**: [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)
- **설정 스키마 변경**: [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md)

#### Docstring 필수 대상

- 모든 public 함수
- 모든 클래스
- 복잡한 로직 블록

______________________________________________________________________

## 7. 테스트 및 품질 관리

### 7.1 테스트 전략

#### 단위 테스트 (Unit Tests)

- **도구**: pytest
- **위치**: `tests/commands/`, `tests/models/`, `tests/utils/`
- **실행**: `uv run pytest tests/`
- **목표**: 개별 함수/클래스 동작 검증

**예시**:

```python
# tests/models/test_config_model.py
def test_config_validation():
    config = SBKubeConfig(
        namespace="test",
        apps=[{"name": "app1", "type": "helm", "specs": {"repo": "grafana", "chart": "grafana"}}]
    )
    assert config.namespace == "test"
```

#### 통합 테스트 (Integration Tests)

- **도구**: pytest + testcontainers[k3s]
- **위치**: `tests/integration/`
- **실행**: `uv run pytest tests/integration/`
- **목표**: 여러 모듈 간 상호작용 검증

**예시**:

```python
# tests/integration/test_workflow.py
def test_full_workflow():
    prepare = PrepareCommand(app_dir="examples/basic")
    prepare.execute()

    build = BuildCommand(app_dir="examples/basic")
    build.execute()

    # 결과 검증
    assert Path("charts/redis").exists()
```

#### E2E 테스트 (End-to-End Tests)

- **도구**: pytest + 실제 k3s 클러스터
- **위치**: `tests/e2e/`
- **실행**: `uv run pytest tests/e2e/`
- **목표**: 실제 배포 시나리오 검증

**예시**:

```python
# tests/e2e/test_deploy.py
def test_deploy_to_k3s():
    deploy = DeployCommand(app_dir="examples/basic", namespace="test")
    result = deploy.execute()

    # Kubernetes 리소스 확인
    pods = kubectl_get_pods("test")
    assert len(pods) > 0
```

### 7.2 커버리지 목표

- **최소 커버리지**: 80%
- **측정 명령어**: `uv run pytest --cov=sbkube --cov-report=html`
- **리포트 위치**: `htmlcov/index.html`

### 7.3 코드 품질 도구

#### Ruff (린터)

```bash
# 체크
uv run ruff check sbkube/

# 자동 수정
uv run ruff check --fix sbkube/
```

#### Black (포매터)

```bash
# 체크
uv run black --check sbkube/

# 포맷팅
uv run black sbkube/
```

#### MyPy (타입 체커)

```bash
# 타입 검증
uv run mypy sbkube/

# 특정 파일만
uv run mypy sbkube/commands/deploy.py
```

#### Bandit (보안 스캔)

```bash
# 보안 취약점 검사
uv run bandit -r sbkube/
```

### 7.4 Pre-commit Hooks

```bash
# Pre-commit 설치 (프로젝트 설정 시)
pre-commit install

# 수동 실행
pre-commit run --all-files
```

______________________________________________________________________

## 8. 트러블슈팅

### 8.1 일반적인 문제

#### 1. 테스트 실패 (k3s 관련)

**증상**: testcontainers 관련 오류

**원인**: Docker가 설치되지 않았거나 실행 중이지 않음

**해결**:

```bash
# Docker Desktop 설치 확인
docker --version

# Docker 실행 확인
docker ps

# 환경변수 확인
echo $DOCKER_HOST
```

#### 2. 타입 오류 (mypy)

**증상**: mypy 검증 실패

**해결**:

```python
# reveal_type() 사용하여 타입 디버깅
from typing import reveal_type
reveal_type(my_variable)

# Pydantic 모델은 model_validate() 사용
config = SBKubeConfig.model_validate(data)

# Optional 타입 명시적 처리
from typing import Optional
def func(arg: Optional[str] = None) -> str:
    return arg or "default"
```

#### 3. Import 오류

**원인**: 패키지 구조 또는 PYTHONPATH 문제

**해결**:

```bash
# 상대 임포트 사용
from . import utils
from .models import SBKubeConfig

# __init__.py 파일 존재 확인
ls sbkube/__init__.py

# PYTHONPATH 확인
echo $PYTHONPATH

# Editable 모드 재설치
uv pip install -e .
```

#### 4. 배포 테스트 실패

**증상**: Kubernetes 리소스 생성 실패

**원인**: kubeconfig, 클러스터 접근 권한, Helm 버전 문제

**해결**:

```bash
# kubeconfig 파일 경로 확인
echo $KUBECONFIG
kubectl config view

# 클러스터 접근 확인
kubectl cluster-info
kubectl get nodes

# Helm 버전 확인 (v3.x 필요)
helm version
```

#### 5. uv 관련 문제

**증상**: 의존성 설치 실패

**해결**:

```bash
# uv 업데이트
pip install --upgrade uv

# 캐시 클리어
rm -rf ~/.cache/uv

# 가상환경 재생성
rm -rf .venv
uv venv
source .venv/bin/activate
uv sync
```

### 8.2 디버깅 팁

#### 상세 로깅 활성화

```bash
# --verbose 옵션 사용
sbkube --verbose prepare --app-dir config
```

#### Python 디버거 사용

```python
# breakpoint() 추가
def my_function():
    breakpoint()  # 여기서 멈춤
    result = some_operation()
    return result
```

#### Rich Console 디버깅

```python
from rich import print as rprint
from rich.traceback import install

install()  # 상세한 트레이스백

rprint(f"Debug: {my_variable}")  # 색상 출력
```

______________________________________________________________________

## 9. 참고 자료

### 9.1 내부 문서 (우선순위)

#### 제품 문서

- [PRODUCT.md](PRODUCT.md) - 제품 개요 (진입점)
- [SPEC.md](SPEC.md) - 기술 명세서
- [docs/00-product/product-definition.md](docs/00-product/product-definition.md) - 완전한 제품 정의
- [docs/00-product/product-spec.md](docs/00-product/product-spec.md) - 기능 명세서
- [docs/00-product/vision-roadmap.md](docs/00-product/vision-roadmap.md) - 비전과 로드맵
- [docs/00-product/target-users.md](docs/00-product/target-users.md) - 대상 사용자

#### 모듈 문서

- [docs/10-modules/sbkube/MODULE.md](docs/10-modules/sbkube/MODULE.md) - 모듈 정의
- [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md) - 상세 아키텍처
- [docs/10-modules/sbkube/API_CONTRACT.md](docs/10-modules/sbkube/API_CONTRACT.md) - API 계약

#### 기능 문서

- [docs/02-features/commands.md](docs/02-features/commands.md) - 명령어 참조
- [docs/02-features/application-types.md](docs/02-features/application-types.md) - 앱 타입
- [docs/02-features/architecture.md](docs/02-features/architecture.md) - 아키텍처 개요

#### 설정 문서

- [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md) - 설정 스키마
- [docs/03-configuration/migration.md](docs/03-configuration/migration.md) - 마이그레이션 가이드

#### 개발자 문서

- [docs/04-development/README.md](docs/04-development/README.md) - 개발자 가이드
- [docs/04-development/testing.md](docs/04-development/testing.md) - 테스트 가이드

#### 사용자 가이드

- [docs/01-getting-started/README.md](docs/01-getting-started/README.md) - 빠른 시작
- [docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md) - 트러블슈팅

#### 예제

- [examples/](examples/) - 사용 예제 디렉토리

### 9.2 외부 라이브러리 문서

#### Python 프레임워크

- [Click 문서](https://click.palletsprojects.com/) - CLI 프레임워크
- [Pydantic 문서](https://docs.pydantic.dev/) - 데이터 검증
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/) - ORM
- [Rich 문서](https://rich.readthedocs.io/) - 콘솔 UI

#### Kubernetes 도구

- [Helm v3 문서](https://helm.sh/docs/) - Helm 차트 관리
- [kubectl 문서](https://kubernetes.io/docs/reference/kubectl/) - Kubernetes CLI
- [Kubernetes Python Client](https://github.com/kubernetes-client/python) - K8s API

#### 테스트 도구

- [pytest 문서](https://docs.pytest.org/) - 테스트 프레임워크
- [testcontainers 문서](https://testcontainers-python.readthedocs.io/) - 통합 테스트

### 9.3 문서 간 관계 그래프

```
CLAUDE.md (이 문서)
  └─ AI 작업 진입점
      │
      ├─ PRODUCT.md (Level 0)
      │   ├─ docs/00-product/product-definition.md
      │   │   ├─ docs/00-product/product-spec.md
      │   │   └─ docs/00-product/target-users.md
      │   └─ docs/00-product/vision-roadmap.md
      │
      ├─ docs/10-modules/sbkube/ (Level 2)
      │   ├─ MODULE.md
      │   ├─ ARCHITECTURE.md
      │   └─ API_CONTRACT.md
      │
      ├─ docs/02-features/ (Level 3)
      │   ├─ commands.md
      │   ├─ application-types.md
      │   └─ architecture.md
      │
      └─ sbkube/ (Level 4)
          ├─ cli.py
          ├─ commands/
          ├─ models/
          └─ utils/
```

______________________________________________________________________

## 10. 버전 정보

- **문서 버전**: 1.1
- **마지막 업데이트**: 2025-10-31
- **대상 SBKube 버전**: v0.6.0+
- **작성자**: archmagece@users.noreply.github.com

### 변경 이력

- **v1.1 (2025-10-31)**:
  - v0.6.0 기능 반영 (app-group 기반 관리, 새로운 상태 관리 명령어)
  - EnhancedBaseCommand 패턴 추가
  - 개발 효율성 가이드 추가
  - 빠른 참조 명령어 추가
  - Cursor rules 반영 (uv 필수, Python 3.12 엄격 요구사항)
- **v1.0 (2025-10-20)**: 초기 버전

______________________________________________________________________

## 11. 문서 사용 가이드

### AI 에이전트를 위한 권장 사항

1. **첫 번째 작업 시**: 이 문서 전체를 읽고 프로젝트 구조 파악
1. **기능 질의 시**: 섹션 2 (AI 컨텍스트 네비게이션) 참조
1. **코드 작성 시**: 섹션 4 (코드 스타일), 섹션 6 (AI 특화 지침) 준수
1. **문제 해결 시**: 섹션 8 (트러블슈팅) 먼저 확인
1. **상세 정보 필요 시**: 섹션 9 (참고 자료)의 2급/3급 문서 참조

### 문서 업데이트 정책

- 주요 기능 추가 시 이 문서 업데이트
- 아키텍처 변경 시 섹션 5 수정
- 새로운 일반적인 문제 발견 시 섹션 8에 추가
- 버전 번호와 업데이트 날짜 갱신

______________________________________________________________________

**🎯 이 문서는 SBKube 프로젝트의 AI 작업을 위한 통합 가이드입니다.**

상세한 제품 정보는 [PRODUCT.md](PRODUCT.md)를, 기술 명세는 [SPEC.md](SPEC.md)를 참조하세요.
