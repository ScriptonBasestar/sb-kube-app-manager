# End-to-End Tests

이 디렉토리는 SBKube 프로젝트의 E2E(End-to-End) 테스트를 포함합니다.

## 🎯 목적

**실제 examples/ 디렉토리의 설정 파일을 사용**하여 SBKube의 전체 워크플로우를 검증합니다.

> **핵심 원칙**: CLI 도구는 examples/ 기반 테스트가 우선입니다. Mock 데이터가 아닌 실제 예제 파일로 테스트합니다.

## 📁 디렉토리 구조

```
e2e/
├── conftest.py                    # E2E 테스트 전용 fixture 및 helper 함수
├── test_k3scode_workflows.py     # ✅ k3scode 실제 워크플로우 테스트
├── test_prepare_examples.py      # ✅ prepare 예제 테스트
├── test_deploy_examples.py       # ✅ deploy 예제 테스트
├── test_complete_workflow.py     # ✅ 전체 워크플로우 테스트
├── test_init_end_to_end.py       # init 명령어 테스트
├── test_run_end_to_end.py        # run 명령어 테스트
└── __init__.py                   # 패키지 마커
```

## ✅ 구현된 테스트 시나리오

### 1. k3scode 워크플로우 (test_k3scode_workflows.py)

**커버리지**: examples/k3scode/* 전체 시나리오

- `test_ai_prepare` - AI 앱 prepare 단계 (Git 저장소 클론)
- `test_ai_build` - AI 앱 build 단계
- `test_devops_prepare` - DevOps 앱 prepare 단계
- `test_devops_build` - DevOps 앱 build 단계
- `test_memory_prepare` - Memory 앱 prepare (Helm 차트 다운로드)
- `test_rdb_prepare` - RDB 앱 prepare

**실행 예시**:
```bash
pytest tests/e2e/test_k3scode_workflows.py -v
# 6 tests, 모두 실제 examples/k3scode/ 파일 사용
```

### 2. prepare 예제 (test_prepare_examples.py)

**커버리지**: examples/prepare/* 시나리오

- `test_prepare_pull_helm_oci` - OCI Helm 차트 pull 테스트

**실행 예시**:
```bash
pytest tests/e2e/test_prepare_examples.py -v
# 실제 OCI 저장소에서 차트 다운로드 테스트
```

### 3. deploy 예제 (test_deploy_examples.py)

**커버리지**: examples/deploy/* 시나리오 (dry-run)

- `test_deploy_install_yaml_dry_run` - YAML 매니페스트 배포
- `test_deploy_install_action_dry_run` - 커스텀 액션 배포
- `test_deploy_exec_dry_run` - exec 명령 실행

**실행 예시**:
```bash
pytest tests/e2e/test_deploy_examples.py -v
# --dry-run으로 K8s 클러스터 없이 테스트
```

### 4. 전체 워크플로우 (test_complete_workflow.py)

**커버리지**: examples/complete-workflow 전체 파이프라인

- `test_complete_workflow_prepare_phase` - prepare 단계
- `test_complete_workflow_build_phase` - prepare + build 단계
- `test_complete_workflow_deploy_phase_dry_run` - prepare + build + deploy 단계

**실행 예시**:
```bash
pytest tests/e2e/test_complete_workflow.py -v
# 전체 워크플로우 통합 테스트
```

## 🏃‍♂️ 실행 방법

```bash
# E2E 테스트 실행 (실제 클러스터 필요)
pytest tests/e2e/ -v

# 마커 기반 실행
pytest -m e2e -v

# 특정 시나리오 실행
pytest tests/e2e/ -k "ai_workflow" -v

# 긴 실행 시간 고려하여 타임아웃 설정
pytest tests/e2e/ -v --timeout=300
```

## 🔧 사전 요구사항

### Kubernetes 클러스터

```bash
# Kind 클러스터 생성
kind create cluster --name sbkube-e2e-test --config kind-config.yaml

# 클러스터 확인
kubectl cluster-info --context kind-sbkube-e2e-test

# 네임스페이스 준비
kubectl create namespace test-ai
kubectl create namespace test-data
```

### 외부 의존성

- **실제 Helm Charts**: Bitnami, 공식 차트
- **Git 저장소**: 실제 GitHub/GitLab 레포지토리
- **네트워크 접근**: 인터넷 연결 필요
- **스토리지**: PersistentVolume 지원

### 도구 설치

```bash
# 필수 CLI 도구
helm version
kubectl version
git --version

# 선택적 도구
k9s version          # 클러스터 모니터링
kubectx              # 컨텍스트 전환
```

## ⚙️ 테스트 환경 설정

### Kind 클러스터 설정

```yaml
# kind-config.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
  - containerPort: 443
    hostPort: 443
```

### 테스트 데이터

```bash
# 실제 설정 파일 사용
tests/e2e/fixtures/
├── ai-config.yaml           # AI 워크로드 설정
├── data-config.yaml         # 데이터 파이프라인 설정
└── monitoring-config.yaml   # 모니터링 스택 설정
```

## 📊 검증 항목

### 배포 성공 검증

```python
def test_ai_workflow_deployment():
    """AI 워크플로우 전체 배포 테스트"""
    
    # 1. Prepare 단계
    assert prepare_command_success()
    
    # 2. Build 단계  
    assert build_command_success()
    
    # 3. Template 단계
    assert template_command_success()
    
    # 4. Deploy 단계
    assert deploy_command_success()
    
    # 5. 배포 상태 확인
    assert pods_are_running(namespace="test-ai")
    assert services_are_accessible()
    
    # 6. 기능 테스트
    assert jupyter_is_accessible()
    assert mlflow_is_accessible()
```

### 성능 검증

- 배포 시간: 5분 이내
- 리소스 사용량: 적정 수준
- 재시작 없이 안정적 동작

### 정리 검증

```python
def test_cleanup_after_deployment():
    """배포 후 정리 테스트"""
    
    # sbkube delete 실행
    assert delete_command_success()
    
    # 모든 리소스 제거 확인
    assert no_pods_remaining()
    assert no_services_remaining() 
    assert namespace_is_empty()
```

## ⚠️ 주의사항

### 실행 시간

- E2E 테스트는 매우 오래 걸림 (10-30분)
- Chart 다운로드, 이미지 풀, 배포 대기 시간 포함
- CI에서는 별도 파이프라인으로 분리 권장

### 리소스 사용량

- Kubernetes 클러스터 리소스 소모
- 인터넷 대역폭 사용 (차트/이미지 다운로드)
- 로컬 디스크 공간 필요

### 테스트 격리

- 각 테스트는 별도 네임스페이스 사용
- 테스트 완료 후 반드시 정리
- 병렬 실행 금지 (리소스 충돌)

## 🔄 CI/CD 통합

### 별도 파이프라인

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests
on:
  schedule:
    - cron: '0 2 * * *'  # 매일 새벽 2시
  workflow_dispatch:     # 수동 실행

jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Kind Cluster
        run: |
          kind create cluster --name e2e-test
          kubectl wait --for=condition=Ready nodes --all --timeout=300s
      
      - name: Run E2E Tests
        run: |
          pytest tests/e2e/ -v --maxfail=1 --timeout=1800
      
      - name: Cleanup
        if: always()
        run: |
          kind delete cluster --name e2e-test
```

### 실패 시 디버깅

```bash
# 테스트 실패 시 로그 수집
kubectl logs -n test-ai --all-containers=true

# 이벤트 확인
kubectl get events -n test-ai --sort-by=.metadata.creationTimestamp

# 리소스 상태 확인
kubectl get all -n test-ai
```

## 📈 모니터링

### 테스트 메트릭

- 성공률 추적
- 실행 시간 추이
- 실패 원인 분석

### 알림 설정

- E2E 테스트 실패 시 즉시 알림
- 성능 저하 감지 시 경고
- 주간 E2E 테스트 리포트

### 시각화

```bash
# 테스트 결과 대시보드
# - 성공/실패 비율
# - 평균 실행 시간
# - 주요 실패 원인
```
