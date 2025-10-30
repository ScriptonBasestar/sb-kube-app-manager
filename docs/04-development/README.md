# 👨‍💻 개발자 가이드

SBKube 프로젝트 개발을 위한 환경 설정 및 개발 워크플로우 가이드입니다.

---

## 🚀 개발 환경 설정

### 사전 요구사항

- Python 3.12 이상
- `uv` 패키지 매니저
- Git

### 환경 구성

```bash
# 1. 저장소 클론
git clone https://github.com/ScriptonBasestar/kube-app-manaer.git
cd sb-kube-app-manager

# 2. 가상환경 생성 및 활성화
uv venv
source .venv/bin/activate

# 3. 개발 의존성 설치
uv pip install -e .
```

### 기본 개발 워크플로우

```bash
# SBKube CLI 기본 명령어 순서
sbkube prepare --base-dir . --app-dir config
sbkube build --base-dir . --app-dir config  
sbkube template --base-dir . --app-dir config --output-dir rendered/
sbkube deploy --base-dir . --app-dir config --namespace <namespace>
```

---

## 📦 빌드 및 배포

### 패키지 빌드

```bash
# 배포용 패키지 빌드
uv build
```

### PyPI 배포

```bash
# 1. 기존 빌드 파일 정리
rm -rf dist

# 2. 새 패키지 빌드
uv build

# 3. PyPI 업로드 (twine 사용)
uv run -m twine upload dist/*
```

### 로컬 개발 설치

```bash
# 개발 버전 설치
uv build
uv pip install -e .

# 강제 재설치 (변경사항 즉시 반영)
uv pip install --force-reinstall --no-deps --upgrade .
```

### 시스템 레벨 설치

```bash
# 시스템 Python에 설치
uv build
pip install -e .
```

---

## 🧪 테스트

테스트 실행에 대한 자세한 내용은 [testing.md](testing.md)를 참조하세요.

### 기본 테스트 실행

```bash
# 전체 테스트 실행
pytest tests/

# 특정 모듈 테스트
pytest tests/test_prepare.py -v
pytest tests/test_build.py -v
pytest tests/test_template.py -v
pytest tests/test_deploy.py -v
```

---

## 🏗️ 프로젝트 구조

### 핵심 디렉토리

- **sbkube/** - 메인 Python 패키지
  - **cli.py** - CLI 엔트리포인트
  - **commands/** - 개별 명령어 구현
  - **models/** - Pydantic 데이터 모델
  - **utils/** - 공통 유틸리티
- **tests/** - 테스트 코드
- **examples/** - 사용 예제
- **docs/** - 프로젝트 문서

### 아키텍처 특징

- **다단계 워크플로우**: prepare → build → template → deploy
- **설정 기반**: YAML/TOML 설정 파일 사용
- **다양한 소스 지원**: Helm repos, OCI charts, Git repos, 로컬 파일

---

## 🔧 개발 도구

### 패키지 관리

- `uv` 사용 (pip 대신)
- 의존성 추가: `uv add <library>`
- 스크립트 실행: `uv run script.py`

### 코드 스타일

- 기존 코드 패턴 준수
- Pydantic 모델 활용한 설정 검증
- 일관된 로깅 사용
- 적절한 에러 처리

### 코드 품질 도구

프로젝트에서 사용하는 코드 품질 도구들:

```bash
# 개발 의존성 설치
make install-dev

# 코드 포맷팅
make format

# 린팅 및 타입 검사
make lint
```

#### 보안 검사 (Bandit)

bandit 보안 검사에서 다음 룰들이 skip됩니다:

- **B101**: assert 사용 - 테스트 코드에서 필수
- **B404**: subprocess 모듈 import - CLI 도구 특성상 필수
- **B603**: subprocess 호출 - kubectl, helm 등 외부 도구 실행 필수
- **B607**: partial 함수 시작 (부분 경로) - 상대 경로 사용 필요
- **B602**: shell=True 사용 - 동적 명령 실행을 위해 필요

이러한 보안 룰들은 CLI 도구의 특성상 필수적이며, 실제 보안 위험보다는 도구의 기능적 요구사항입니다.

#### Pre-commit 훅

```bash
# pre-commit 설치
uv run pre-commit install

# 모든 파일에 대해 실행
uv run pre-commit run --all-files
```

pre-commit 훅은 다음 도구들을 자동으로 실행합니다:

- ruff (린팅 및 포맷팅)
- isort (import 정렬)
- mypy (타입 검사)
- mdformat (마크다운 포맷팅)
- bandit (보안 검사)
- 기본 파일 검사 (trailing-whitespace, end-of-file-fixer 등)

---

## 🐳 Kubernetes 테스트

### Kind를 사용한 로컬 테스트

```bash
# 테스트 클러스터 생성
kind create cluster --name sbkube-test
kubectl config use-context kind-sbkube-test

# SBKube 명령어 테스트
uv run -m sbkube.cli deploy --base-dir examples/k3scode --app-dir memory --namespace data-memory
```

---

## 📝 기여 방법

1. **포크 및 브랜치 생성**

   ```bash
   git checkout -b feature/새로운-기능
   ```

1. **변경사항 구현**

   - 기존 코드 스타일 준수
   - 테스트 코드 작성
   - 문서 업데이트

1. **테스트 실행**

   ```bash
   pytest tests/
   ```

1. **풀 리퀘스트 생성**

   - 변경사항 명확히 설명
   - 테스트 결과 포함

---

## 🚨 중요 참고사항

- 한국 k3s 환경에 특화된 도구
- ScriptonBasestar DevOps 인프라의 일부
- MIT 라이선스 오픈소스 프로젝트
- 한국어 문서 및 코멘트 권장

---

*📋 원본 통합: Developer.md + Deploy.md → 한국어 통합 버전*
