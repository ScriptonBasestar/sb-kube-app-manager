# SBKube 의존성 명세

## 개요

이 문서는 SBKube 모듈의 모든 외부 의존성을 명시합니다.

## 런타임 환경 요구사항

### Python 버전

- **필수**: Python 3.12 이상
- **권장**: Python 3.12.1
- **호환성 테스트**: 3.12.x

#### 이유

- Pydantic 2.7.1+가 Python 3.12 기능 사용
- 타입 힌팅 개선 (PEP 695)
- 성능 향상

### 운영체제

- **지원**: Linux, macOS
- **제한적 지원**: Windows (WSL2)
- **미지원**: Windows native

## 외부 CLI 도구 의존성

### 1. kubectl

**버전**: v1.28.0 이상 권장 **필수 여부**: 예 (deploy, upgrade, delete 명령어) **용도**: Kubernetes API 접근, YAML 리소스 적용

#### 설치 방법

```bash
# macOS
brew install kubectl

# Linux (최신 안정 버전)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# 버전 확인
kubectl version --client
```

#### 호환성 매트릭스

| kubectl 버전 | Kubernetes 1.27 | Kubernetes 1.28 | Kubernetes 1.29 |
|-------------|-----------------|-----------------|-----------------|
| v1.27.x | ✅ | ✅ | ⚠️ |
| v1.28.x | ✅ | ✅ | ✅ |
| v1.29.x | ⚠️ | ✅ | ✅ |

### 2. Helm

**버전**: v3.13.0 이상 권장 **필수 여부**: 예 (prepare, build, template, deploy 명령어) **용도**: Helm 차트 다운로드, 템플릿 렌더링, 릴리스 관리

#### 설치 방법

```bash
# macOS
brew install helm

# Linux
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 버전 확인
helm version
```

#### 호환성 매트릭스

| Helm 버전 | Kubernetes 1.27 | Kubernetes 1.28 | Kubernetes 1.29 |
|-----------|-----------------|-----------------|-----------------|
| v3.12.x | ✅ | ✅ | ⚠️ |
| v3.13.x | ✅ | ✅ | ✅ |
| v3.14.x | ⚠️ | ✅ | ✅ |

**중요**: Helm v2.x는 지원하지 않습니다.

### 3. Git

**버전**: 2.30.0 이상 **필수 여부**: 조건부 (pull-git 앱 타입 사용 시) **용도**: Git 리포지토리 클론

#### 설치 방법

```bash
# macOS
brew install git

# Linux (Debian/Ubuntu)
sudo apt-get install git

# Linux (RHEL/CentOS)
sudo yum install git

# 버전 확인
git --version
```

## Python 패키지 의존성

### 핵심 의존성 (pyproject.toml)

```toml
dependencies = [
  "click>=8.1",           # CLI 프레임워크
  "pyyaml",               # YAML 파일 파싱
  "gitpython",            # Git 리포지토리 조작
  "jinja2",               # 템플릿 엔진
  "rich",                 # 콘솔 UI
  "pytest>=8.3.5",        # 테스트 프레임워크
  "toml>=0.10.2",         # TOML 파일 처리
  "jsonschema>=4.23.0",   # JSON 스키마 검증
  "pydantic>=2.7.1",      # 데이터 모델링 및 검증
  "sqlalchemy>=2.0.0",    # ORM 및 데이터베이스
  "requests>=2.31.0",     # HTTP 클라이언트
  "kubernetes>=28.1.0",   # Kubernetes Python API
]
```

### 상세 의존성 분석

#### 1. click (CLI 프레임워크)

- **버전**: 8.1.0 이상
- **용도**: CLI 명령어 파싱 및 라우팅
- **라이선스**: BSD-3-Clause
- **대안**: argparse (표준 라이브러리, 기능 제한)

#### 2. pyyaml (YAML 파서)

- **버전**: 6.0 이상 권장
- **용도**: config.yaml, sources.yaml 파싱
- **라이선스**: MIT
- **보안**: C 확장 사용 (안전하지 않은 로드 금지)

#### 3. gitpython (Git 연동)

- **버전**: 3.1.0 이상
- **용도**: pull-git 타입 리포지토리 클론
- **라이선스**: BSD-3-Clause
- **주의**: Git CLI 필요 (래퍼)

#### 4. jinja2 (템플릿 엔진)

- **버전**: 3.1.0 이상
- **용도**: YAML 파일 템플릿 처리
- **라이선스**: BSD-3-Clause
- **보안**: 자동 이스케이핑 활성화

#### 5. rich (콘솔 UI)

- **버전**: 13.0.0 이상 권장
- **용도**: 색상 로깅, 테이블, 진행 표시
- **라이선스**: MIT
- **특징**: 터미널 감지 자동

#### 6. pydantic (데이터 검증)

- **버전**: 2.7.1 이상 (v2 필수)
- **용도**: 설정 파일 모델 및 검증
- **라이선스**: MIT
- **주의**: v1과 호환 불가

#### 7. sqlalchemy (ORM)

- **버전**: 2.0.0 이상
- **용도**: 배포 상태 관리 DB
- **라이선스**: MIT
- **데이터베이스**: SQLite (기본), PostgreSQL/MySQL 가능

#### 8. requests (HTTP 클라이언트)

- **버전**: 2.31.0 이상
- **용도**: OCI 레지스트리 접근 (향후)
- **라이선스**: Apache-2.0
- **보안**: 인증서 검증 필수

#### 9. kubernetes (Python 클라이언트)

- **버전**: 28.1.0 이상
- **용도**: Kubernetes API 직접 접근 (향후 확장)
- **라이선스**: Apache-2.0
- **현재**: kubectl 래퍼 우선 사용

### 개발 의존성 (dev)

```toml
[dependency-groups]
dev = [
    "twine>=6.1.0",      # PyPI 배포
    "ruff>=0.7.0",       # 린터
    "mypy>=1.13.0",      # 타입 체커
    "black>=24.0.0",     # 코드 포매터
    "isort>=5.13.0",     # Import 정렬
    "pre-commit>=4.0.0", # Pre-commit 훅
    "types-PyYAML>=6.0.0",  # PyYAML 타입 스텁
    "bandit>=1.8.6",     # 보안 검사
    "mdformat>=0.7.22",  # 마크다운 포매터
    "types-toml>=0.10.8",   # TOML 타입 스텁
    "types-requests>=2.31.0",  # Requests 타입 스텁
]
```

### 테스트 의존성 (test)

```toml
test = [
    "pytest>=8.3.5",         # 테스트 프레임워크
    "pytest-cov>=4.1.0",     # 커버리지
    "pytest-xdist>=3.5.0",   # 병렬 테스트
    "pytest-timeout>=2.2.0", # 타임아웃 관리
    "pytest-mock>=3.12.0",   # Mocking
    "pytest-benchmark>=4.0.0",  # 벤치마크
    "pytest-asyncio>=0.23.0",   # 비동기 테스트
    "testcontainers[k3s]>=4.0.0",  # k3s 컨테이너
    "kubernetes>=28.1.0",    # K8s API (테스트용)
    "faker>=22.0.0",         # 테스트 데이터 생성
]
```

## Kubernetes 클러스터 요구사항

### 최소 요구사항

- **Kubernetes 버전**: 1.27 이상
- **RBAC**: 대상 네임스페이스에 대한 read/write 권한
- **리소스**: 배포할 앱에 따라 다름

### 권장 환경

- **k3s**: v1.28.0 이상 (경량 테스트 환경)
- **minikube**: v1.32.0 이상 (로컬 개발)
- **kind**: v0.20.0 이상 (CI/CD)

### 필수 RBAC 권한

```yaml
# 최소 권한 예시
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: my-app
  name: sbkube-deployer
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["*"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
```

## 네트워크 요구사항

### 외부 접근

- **Helm 저장소**: HTTPS 접근 (예: charts.bitnami.com)
- **Git 리포지토리**: HTTPS 또는 SSH
- **OCI 레지스트리**: HTTPS (Docker Hub, GitHub Container Registry 등)
- **Kubernetes API**: kubeconfig에 지정된 주소

### 프록시 환경

환경변수를 통한 프록시 설정 지원:

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1,.cluster.local
```

## 버전 호환성 매트릭스

### SBKube x Python x Kubernetes

| SBKube | Python | Kubernetes | Helm | kubectl |
|--------|--------|------------|------|---------|
| v0.3.0 | 3.12+ | 1.27-1.29 | 3.13+ | 1.28+ |
| v0.3.x | 3.12+ | 1.28-1.30 | 3.14+ | 1.29+ |
| v0.4.x | 3.12+ | 1.29-1.31 | 3.15+ | 1.30+ |

### 패키지 버전 고정 (호환성 테스트 완료)

```toml
# 프로덕션 권장 버전 (pyproject.toml 예시)
click = "8.1.7"
pyyaml = "6.0.1"
pydantic = "2.7.1"
sqlalchemy = "2.0.29"
rich = "13.7.1"
```

## 보안 고려사항

### CVE 모니터링

정기적으로 의존성 취약점 검사:

```bash
# Bandit (Python 코드 보안)
uv run bandit -r sbkube/

# Safety (의존성 취약점)
uv run safety check

# 또는 GitHub Dependabot 활용
```

### 최소 권한 원칙

- kubeconfig 파일 권한: 600
- Kubernetes RBAC: 필요한 최소 권한만 할당
- Secrets 직접 노출 금지

## 의존성 업데이트 정책

### Patch 버전

- **주기**: 월간
- **방법**: 자동 (Dependabot)
- **검증**: CI 통과 후 머지

### Minor 버전

- **주기**: 분기별
- **방법**: 수동 검토
- **검증**: Full 테스트 스위트 + 수동 테스트

### Major 버전

- **주기**: 연간 또는 필요 시
- **방법**: 철저한 검토 및 마이그레이션 계획
- **검증**: 베타 테스트 후 점진적 롤아웃

## 라이선스 요약

### 주요 의존성 라이선스

| 패키지 | 라이선스 | 상업적 사용 |
|--------|----------|-------------|
| click | BSD-3-Clause | ✅ |
| pyyaml | MIT | ✅ |
| pydantic | MIT | ✅ |
| rich | MIT | ✅ |
| sqlalchemy | MIT | ✅ |
| kubernetes | Apache-2.0 | ✅ |

**SBKube 라이선스**: MIT (모든 의존성과 호환)

## 문제 해결

### 일반적인 의존성 문제

#### Pydantic v1/v2 충돌

**증상**: `ImportError: cannot import name 'BaseModel' from 'pydantic'`

**해결**:

```bash
# Pydantic v2로 강제 업그레이드
uv pip install "pydantic>=2.7.1"
```

#### SQLAlchemy 버전 불일치

**증상**: `AttributeError: 'Engine' object has no attribute 'execute'`

**해결**:

```bash
# SQLAlchemy 2.0으로 업그레이드
uv pip install "sqlalchemy>=2.0.0"
```

### 환경별 이슈

#### macOS ARM64 (M1/M2)

일부 패키지는 ARM64 네이티브 빌드 필요:

```bash
# Rosetta 사용하지 않고 네이티브 설치
arch -arm64 uv pip install sbkube
```

#### Linux (Alpine)

musl libc 환경에서는 일부 바이너리 의존성 빌드 필요:

```bash
# 빌드 도구 설치
apk add gcc musl-dev python3-dev libffi-dev openssl-dev
```

---

**문서 버전**: 1.0 **마지막 업데이트**: 2025-10-20 **관련 문서**:

- [MODULE.md](MODULE.md) - 모듈 정의
- [ARCHITECTURE.md](ARCHITECTURE.md) - 아키텍처
- [API_CONTRACT.md](API_CONTRACT.md) - API 계약
