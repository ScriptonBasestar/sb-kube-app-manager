# Integration Tests

이 디렉토리는 SBKube 프로젝트의 통합 테스트를 포함합니다.

## 🎯 목적

여러 컴포넌트 간의 상호작용과 외부 시스템과의 통합을 검증합니다.

## 📁 테스트 파일

```
integration/
├── test_full_workflow.py    # 전체 워크플로우 통합 테스트
├── test_helm_integration.py # Helm CLI와의 통합 테스트  
└── test_k8s_integration.py  # Kubernetes API 통합 테스트
```

## 🧪 테스트 범위

### Full Workflow (`test_full_workflow.py`)
- **prepare → build → template → deploy** 전체 파이프라인
- 다중 앱 배포 시나리오
- 설정 파일 검증 및 처리

### Helm Integration (`test_helm_integration.py`)
- Helm CLI 명령어 실행
- Chart 다운로드 및 템플릿 생성
- Repository 관리

### Kubernetes Integration (`test_k8s_integration.py`)
- Kubernetes API 연결
- 리소스 생성/조회/삭제
- 네임스페이스 관리

## 🏃‍♂️ 실행 방법

```bash
# 전체 통합 테스트 실행
pytest tests/integration/ -v

# 특정 테스트 실행
pytest tests/integration/test_full_workflow.py -v

# 마커 기반 실행
pytest -m integration -v

# 외부 종속성이 있는 테스트 (Kind 클러스터 필요)
pytest tests/integration/ -v --k8s-cluster=kind-sbkube-test
```

## 🔧 사전 요구사항

### 로컬 개발 환경
```bash
# Helm 설치 필요
helm version

# kubectl 설치 필요  
kubectl version --client

# Kind 클러스터 (선택사항)
kind create cluster --name sbkube-test
kubectl config use-context kind-sbkube-test
```

### CI/CD 환경
- Docker 컨테이너 내에서 실행
- Mock 서비스 또는 테스트 클러스터 사용
- 네트워크 접근 권한 필요

## ⚠️ 주의사항

### 실행 시간
- 통합 테스트는 단위 테스트보다 오래 걸림
- 네트워크 I/O 및 외부 CLI 호출 포함
- CI에서는 타임아웃 설정 권장

### 환경 의존성
- 실제 Helm/kubectl 바이너리 필요
- 인터넷 연결 (Chart 다운로드)
- Kubernetes 클러스터 (일부 테스트)

### 테스트 격리
- 각 테스트는 독립적 네임스페이스 사용
- 테스트 후 리소스 정리 필요
- 병렬 실행 시 충돌 방지

## 🎛️ 설정

### pytest 설정
```python
# conftest.py에서 제공하는 fixture들
@pytest.fixture
def k8s_cluster():
    """Kubernetes 클러스터 연결"""
    
@pytest.fixture  
def helm_binary():
    """Helm 바이너리 경로"""
```

### 환경 변수
```bash
# 선택적 환경 변수
export KUBECONFIG=/path/to/kubeconfig
export HELM_CACHE_HOME=/tmp/helm
export SBKUBE_LOG_LEVEL=DEBUG
```

## 📊 품질 지표

- **외부 시스템 연동**: Helm, Kubernetes, Git
- **실제 네트워크 I/O**: Repository 접근, API 호출
- **End-to-End 검증**: 전체 워크플로우 동작 확인

## 🔄 CI/CD 통합

```yaml
# GitHub Actions 예시
- name: Run Integration Tests
  run: |
    # 테스트 클러스터 준비
    kind create cluster --name test
    
    # 통합 테스트 실행
    pytest tests/integration/ -v --maxfail=1
    
    # 정리
    kind delete cluster --name test
```