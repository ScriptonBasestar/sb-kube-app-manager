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

2. **변경사항 구현**
   - 기존 코드 스타일 준수
   - 테스트 코드 작성
   - 문서 업데이트

3. **테스트 실행**
   ```bash
   pytest tests/
   ```

4. **풀 리퀘스트 생성**
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