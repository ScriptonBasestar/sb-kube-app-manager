# AGENTS.md - SBKube

## 프로젝트 개요
- **제품**: SBKube - k3s용 Kubernetes 배포 자동화 CLI 도구
- **아키텍처**: 모놀리식 Python CLI 애플리케이션
- **기술 스택**: Python 3.12+, Click, Pydantic, SQLAlchemy, Rich
- **개발 단계**: v0.2.1 (성숙기 - 기능 확장 중)

## 에이전트 작업 지침

### 개발 환경 설정
```bash
# Python 환경 (uv 사용 필수)
uv sync

# 개발 서버 (테스트 실행)
uv run pytest

# 빌드
uv build

# 설치 (editable mode)
uv pip install -e .
```

### 코드 스타일 및 규약
- **언어**: Python 3.12+
- **포매터**: black (line-length: 120)
- **린터**: ruff (설정: ruff.toml)
- **타입 체커**: mypy (설정: mypy.ini)
- **컨벤션**: PEP 8, snake_case (함수/변수), PascalCase (클래스)
- **Import 순서**:
  1. 표준 라이브러리
  2. 서드파티 라이브러리
  3. 로컬 모듈

### 테스트 전략
- **단위 테스트**: pytest
- **통합 테스트**: testcontainers[k3s]
- **E2E 테스트**: 실제 k3s 클러스터 사용
- **최소 커버리지**: 80%
- **테스트 실행**: `uv run pytest -v`
- **커버리지 측정**: `uv run pytest --cov=sbkube --cov-report=html`

### 문서화 요구사항
- 새 기능 추가 시 [docs/00-product/product-spec.md](docs/00-product/product-spec.md) 업데이트
- 명령어 변경 시 [docs/02-features/commands.md](docs/02-features/commands.md) 업데이트 필수
- 아키텍처 변경 시 [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md) 검토
- 모든 public 함수/클래스에 docstring 필수

### 보안 고려사항
- 민감 정보는 환경변수 사용 (KUBECONFIG, GIT_TOKEN 등)
- Kubernetes Secrets 직접 노출 금지
- 외부 API 키는 설정 파일에서 참조
- 의존성 보안 취약점 정기 검사: `uv run bandit -r sbkube/`

### 배포 및 운영
- **환경**: PyPI (공개 패키지)
- **배포 도구**: hatchling, twine
- **버전 관리**: pyproject.toml에서 수동 관리
- **릴리스 프로세스**:
  1. 버전 업데이트 (pyproject.toml)
  2. CHANGELOG 작성
  3. Git 태그 생성
  4. PyPI 배포 (`make publish`)

### AI 에이전트 특화 지침
1. **컨텍스트 우선순위**:
   - [PRODUCT.md](PRODUCT.md) → [docs/00-product/](docs/00-product/) → [docs/10-modules/sbkube/MODULE.md](docs/10-modules/sbkube/MODULE.md) 순서로 참조
   - 기능 질의: [docs/00-product/product-spec.md](docs/00-product/product-spec.md)
   - 아키텍처 질의: [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)
   - 구현 질의: [docs/02-features/](docs/02-features/) 및 소스 코드

2. **코드 변경 시**:
   - 관련 테스트 자동 실행 (`uv run pytest tests/`)
   - 문서 동기화 확인 (특히 product-spec.md, commands.md)
   - Pydantic 모델 변경 시 JSON 스키마 재생성
   - 타입 힌트 검증 (`uv run mypy sbkube/`)

3. **새 기능 개발 시**:
   - 제품 스펙과 일치성 확인 (product-spec.md 참조)
   - BaseCommand 패턴 준수 (sbkube/utils/base_command.py)
   - Rich Console 사용 (sbkube/utils/logger.py)
   - Pydantic 모델 검증 추가 (sbkube/models/)

4. **새 명령어 추가 시**:
   - sbkube/commands/ 디렉토리에 모듈 생성
   - cli.py에 Click 명령어 등록
   - docs/02-features/commands.md에 문서화
   - 테스트 케이스 작성 (tests/commands/)

5. **버그 수정 시**:
   - 재현 가능한 테스트 케이스 먼저 작성
   - 근본 원인 분석 후 최소한의 변경
   - 관련 문서 업데이트 (troubleshooting.md)

## 핵심 디렉토리 구조

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
```

## 자주 사용하는 명령어

### 개발 워크플로우
```bash
# 코드 품질 검사
uv run ruff check sbkube/
uv run mypy sbkube/
uv run black --check sbkube/

# 자동 포맷팅
uv run black sbkube/
uv run isort sbkube/

# 테스트 실행
uv run pytest -v
uv run pytest --cov=sbkube

# 문서 검증
uv run mdformat --check docs/

# 전체 품질 검사 (Makefile 사용)
make lint
make test
make security
```

### SBKube CLI 사용 (개발 중)
```bash
# Editable 설치 후
uv pip install -e .

# 기본 워크플로우
sbkube prepare --app-dir examples/basic
sbkube build --app-dir examples/basic
sbkube template --app-dir examples/basic --output-dir /tmp/rendered
sbkube deploy --app-dir examples/basic --namespace test --dry-run

# 상태 관리
sbkube state list
sbkube state history --namespace test

# 설정 검증
sbkube validate --app-dir examples/basic

# 도움말
sbkube --help
sbkube deploy --help
```

## 트러블슈팅

### 일반적인 문제

**1. 테스트 실패 (k3s 관련)**
- testcontainers가 Docker 필요
- 로컬에 Docker Desktop 설치 확인
- 환경변수 `DOCKER_HOST` 확인

**2. 타입 오류 (mypy)**
- `reveal_type()` 사용하여 타입 디버깅
- Pydantic 모델은 `model_validate()` 사용
- Optional 타입 명시적 처리

**3. Import 오류**
- 상대 임포트 사용 (`from . import ...`)
- `__init__.py` 파일 존재 확인
- PYTHONPATH 확인

**4. 배포 테스트 실패**
- kubeconfig 파일 경로 확인
- k3s 클러스터 접근 권한 확인
- Helm v3.x 설치 확인 (`helm version`)

## 참고 자료

### 내부 문서
- [PRODUCT.md](PRODUCT.md) - 제품 개요
- [CONTEXT_MAP.md](CONTEXT_MAP.md) - AI 컨텍스트 네비게이션
- [docs/00-product/product-definition.md](docs/00-product/product-definition.md) - 완전한 제품 정의
- [docs/04-development/README.md](docs/04-development/README.md) - 개발자 가이드

### 외부 자료
- [Click 문서](https://click.palletsprojects.com/)
- [Pydantic 문서](https://docs.pydantic.dev/)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)
- [Rich 문서](https://rich.readthedocs.io/)
- [Helm v3 문서](https://helm.sh/docs/)

---

**문서 버전**: 1.0
**마지막 업데이트**: 2025-10-20
**담당자**: archmagece@users.noreply.github.com
