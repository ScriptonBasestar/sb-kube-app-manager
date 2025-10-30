# Multi-Source Configuration Example

여러 환경별로 다른 소스 설정을 사용하는 예제입니다.

이 예제는 다음을 보여줍니다:
- **환경별 sources.yaml**: dev, staging, prod 환경별 클러스터 설정
- **공통 config.yaml**: 모든 환경에서 동일한 앱 구성
- **환경별 values 오버라이드**: set_values를 통한 환경별 커스터마이징
- **다중 리포지토리**: Helm, OCI, Git 리포지토리 통합

## 📁 디렉토리 구조

```
multi-source/
├── sources.yaml              # 기본 (개발 환경)
├── sources-dev.yaml          # 개발 환경 (Minikube)
├── sources-staging.yaml      # 스테이징 환경
├── sources-prod.yaml         # 프로덕션 환경
├── config.yaml               # 앱 설정 (환경 독립적)
├── nginx-values.yaml         # Nginx 기본값
├── postgres-values.yaml      # PostgreSQL 기본값
├── redis-values.yaml         # Redis 기본값
└── README.md                 # 이 문서
```

## 🎯 환경별 설정

### Development (sources-dev.yaml)

**특징**:
- 로컬 클러스터 (Minikube/Kind)
- 낮은 리소스 할당
- 영속성 비활성화 (빠른 재배포)
- Public OCI 이미지

**kubeconfig**:
```yaml
cluster: dev-k3s
kubeconfig: ~/.kube/config
kubeconfig_context: minikube
```

### Staging (sources-staging.yaml)

**특징**:
- 전용 클러스터
- 프로덕션과 유사한 리소스
- 영속성 활성화
- 인증 필요 (OCI)

**kubeconfig**:
```yaml
cluster: staging-k3s
kubeconfig: ~/.kube/config-staging
kubeconfig_context: staging
```

### Production (sources-prod.yaml)

**특징**:
- 고가용성 클러스터
- 높은 리소스 할당
- 모든 모니터링 활성화
- 백업 활성화
- Git 리포지토리 추가

**kubeconfig**:
```yaml
cluster: production-k3s
kubeconfig: ~/.kube/config-prod
kubeconfig_context: production
```

## 🚀 실행 방법

### 시나리오 1: 환경별 배포

```bash
# 개발 환경 배포
sbkube apply --app-dir examples/multi-source --source sources-dev.yaml

# 스테이징 환경 배포
sbkube apply --app-dir examples/multi-source --source sources-staging.yaml

# 프로덕션 환경 배포
sbkube apply --app-dir examples/multi-source --source sources-prod.yaml
```

### 시나리오 2: 기본 sources.yaml 사용

```bash
# --source 미지정 시 sources.yaml 사용
sbkube apply --app-dir examples/multi-source
```

### 시나리오 3: 환경별 준비 및 검증

```bash
# 개발 환경
sbkube prepare --app-dir examples/multi-source --source sources-dev.yaml
sbkube template --app-dir examples/multi-source --source sources-dev.yaml --output-dir rendered-dev

# 스테이징 환경
sbkube prepare --app-dir examples/multi-source --source sources-staging.yaml
sbkube template --app-dir examples/multi-source --source sources-staging.yaml --output-dir rendered-staging

# 프로덕션 환경
sbkube prepare --app-dir examples/multi-source --source sources-prod.yaml
sbkube template --app-dir examples/multi-source --source sources-prod.yaml --output-dir rendered-prod
```

### 시나리오 4: CI/CD 파이프라인

```bash
#!/bin/bash
# deploy.sh - 환경별 배포 스크립트

ENV=${1:-dev}  # 기본값: dev
SOURCE_FILE="sources-${ENV}.yaml"

echo "Deploying to ${ENV} environment..."

# 검증
sbkube prepare --app-dir . --source ${SOURCE_FILE}

# 템플릿 생성 (dry-run)
sbkube template --app-dir . --source ${SOURCE_FILE} --output-dir rendered-${ENV}

# 배포
sbkube deploy --app-dir . --source ${SOURCE_FILE}

echo "Deployment to ${ENV} completed!"
```

**사용법**:
```bash
./deploy.sh dev      # 개발 환경
./deploy.sh staging  # 스테이징 환경
./deploy.sh prod     # 프로덕션 환경
```

## 🔍 환경별 차이점

### 리소스 할당

| 환경 | Nginx CPU | Nginx Memory | PostgreSQL CPU | PostgreSQL Memory |
|------|-----------|--------------|----------------|-------------------|
| **Dev** | 100m | 128Mi | 250m | 256Mi |
| **Staging** | 200m | 256Mi | 500m | 512Mi |
| **Prod** | 500m | 512Mi | 1000m | 1Gi |

**구현 방법** (config.yaml에서 환경 감지 후 set_values):
```yaml
# 프로덕션 배포 시
sbkube deploy --source sources-prod.yaml
```

실제로는 config.yaml 자체는 환경 독립적이고, values 파일에서 환경별 차이를 관리합니다.

### 영속성 (Persistence)

| 환경 | PostgreSQL PVC | Redis PVC | StorageClass |
|------|----------------|-----------|--------------|
| **Dev** | ❌ 비활성화 | ❌ 비활성화 | - |
| **Staging** | ✅ 5Gi | ✅ 2Gi | standard |
| **Prod** | ✅ 20Gi | ✅ 10Gi | fast-ssd |

### 서비스 타입

| 환경 | Nginx Service | 외부 접근 |
|------|---------------|-----------|
| **Dev** | ClusterIP | ❌ Port-forward 사용 |
| **Staging** | LoadBalancer | ✅ Internal LB |
| **Prod** | LoadBalancer | ✅ Public LB + TLS |

## 💡 환경별 커스터마이징 패턴

### 패턴 1: sources.yaml만 변경

**장점**: 앱 설정(config.yaml)은 환경 독립적

```
config.yaml (공통)
  +
sources-dev.yaml (개발 클러스터)
  = 개발 환경 배포

config.yaml (공통)
  +
sources-prod.yaml (프로덕션 클러스터)
  = 프로덕션 환경 배포
```

### 패턴 2: values 파일 분리

**config.yaml** (환경별 values 파일 참조):
```yaml
apps:
  web-app:
    type: helm
    values:
      - nginx-values-${ENV}.yaml  # ENV 변수로 파일 선택
```

**디렉토리 구조**:
```
nginx-values-dev.yaml      # 개발 환경
nginx-values-staging.yaml  # 스테이징 환경
nginx-values-prod.yaml     # 프로덕션 환경
```

### 패턴 3: set_values 오버라이드

**config.yaml** (환경별 set_values 섹션):
```yaml
# CI/CD에서 환경변수로 주입
apps:
  database:
    set_values:
      - primary.resources.requests.cpu=${DB_CPU:-250m}
      - primary.resources.requests.memory=${DB_MEMORY:-256Mi}
```

### 패턴 4: 앱별 enabled 제어

**개발 환경** (모니터링 비활성화):
```yaml
apps:
  prometheus:
    enabled: false  # 개발 환경에서는 불필요
```

**프로덕션 환경** (모니터링 활성화):
```yaml
apps:
  prometheus:
    enabled: true   # 프로덕션에서는 필수
```

## 🔐 보안 고려사항

### 1. kubeconfig 분리

```bash
# 개발
~/.kube/config              # 모든 개발자 접근 가능

# 스테이징
~/.kube/config-staging      # 제한된 접근

# 프로덕션
~/.kube/config-prod         # 매우 제한된 접근 (CI/CD만)
```

### 2. Secret 관리

```yaml
# 개발: values 파일에 하드코딩 (편의성)
auth:
  password: dev123

# 프로덕션: Kubernetes Secret 참조
auth:
  existingSecret: postgres-secret
  secretKeys:
    adminPasswordKey: postgres-password
```

### 3. OCI 인증

```yaml
# 개발: Public 이미지
oci_repos:
  ghcr:
    registry: ghcr.io
    # auth_required: false

# 프로덕션: Private 이미지 (인증 필요)
oci_repos:
  ghcr:
    registry: ghcr.io
    # auth_required: true
    # credentials: ${REGISTRY_TOKEN}  # CI/CD 변수
```

## 📊 환경별 비교표

| 항목 | Development | Staging | Production |
|------|-------------|---------|------------|
| **클러스터** | Minikube | 전용 k3s | HA k3s |
| **Nodes** | 1 | 3 | 5+ |
| **CPU 할당** | 낮음 | 중간 | 높음 |
| **메모리 할당** | 낮음 | 중간 | 높음 |
| **영속성** | ❌ | ✅ | ✅ |
| **모니터링** | ❌ | ✅ | ✅ |
| **로깅** | ❌ | ✅ | ✅ |
| **백업** | ❌ | ⚠️ (선택) | ✅ |
| **자동 스케일링** | ❌ | ❌ | ✅ |
| **네트워크 정책** | ❌ | ⚠️ (일부) | ✅ |

## 🎯 사용 사례

### Use Case 1: 개발 → 스테이징 → 프로덕션 파이프라인

```bash
# Step 1: 개발 환경에서 테스트
sbkube apply --source sources-dev.yaml
# 개발자가 기능 검증

# Step 2: 스테이징 환경 배포
sbkube apply --source sources-staging.yaml
# QA 팀 테스트

# Step 3: 프로덕션 배포
sbkube apply --source sources-prod.yaml
# 실제 서비스 배포
```

### Use Case 2: 멀티 클러스터 배포

**리전별 클러스터**:
```bash
# Asia Pacific
sbkube apply --source sources-ap.yaml

# Europe
sbkube apply --source sources-eu.yaml

# US East
sbkube apply --source sources-us-east.yaml
```

### Use Case 3: Feature Branch 배포

```bash
# 기능 브랜치용 임시 환경
cp sources-dev.yaml sources-feature-branch.yaml

# kubeconfig_context만 변경
# kubeconfig_context: feature-xyz

sbkube apply --source sources-feature-branch.yaml
```

## 🐛 Troubleshooting

### 문제 1: 잘못된 클러스터에 배포

**증상**: 개발 환경에 배포하려 했는데 프로덕션에 배포됨

**원인**: `--source` 옵션 누락

**해결**:
```bash
# 잘못된 예
sbkube apply --app-dir .
# ← sources.yaml (기본) 사용, 의도하지 않은 클러스터

# 올바른 예
sbkube apply --app-dir . --source sources-dev.yaml
```

### 문제 2: kubeconfig 파일 없음

**증상**: `Error: kubeconfig file not found: ~/.kube/config-prod`

**해결**:
```bash
# kubeconfig 경로 확인
ls -la ~/.kube/

# 파일이 없으면 생성
# 1. 클러스터 관리자에게 요청
# 2. 또는 기존 config에서 컨텍스트 추출
kubectl config view --flatten > ~/.kube/config-prod
```

### 문제 3: 컨텍스트 이름 불일치

**증상**: `Error: context "production" not found in kubeconfig`

**원인**: kubeconfig 파일의 컨텍스트 이름과 sources.yaml의 설정 불일치

**해결**:
```bash
# 사용 가능한 컨텍스트 확인
kubectl config get-contexts

# sources.yaml 수정
kubeconfig_context: <실제_컨텍스트_이름>
```

### 문제 4: 환경별 values 차이 확인

**방법**:
```bash
# 템플릿 생성 후 비교
sbkube template --source sources-dev.yaml --output-dir rendered-dev
sbkube template --source sources-prod.yaml --output-dir rendered-prod

# diff로 차이 확인
diff -r rendered-dev/ rendered-prod/
```

## 📚 관련 예제

- [app-dirs-explicit](../app-dirs-explicit/) - `app_dirs`로 앱 선택
- [multi-app-groups](../multi-app-groups/) - 멀티 그룹 배포
- [advanced-features/04-multi-namespace](../advanced-features/04-multi-namespace/) - 멀티 네임스페이스

## 🔑 핵심 정리

1. **sources.yaml 역할**
   - 클러스터 연결 정보 (kubeconfig, context)
   - Helm/OCI/Git 리포지토리 설정
   - 환경별로 분리 관리

2. **config.yaml 역할**
   - 앱 구성 (어떤 앱을 배포할지)
   - 앱 타입 및 버전
   - 환경 독립적 (가능한 한)

3. **환경 분리 전략**
   - sources.yaml 파일로 클러스터 분리
   - values 파일로 리소스 차별화
   - set_values로 동적 오버라이드

4. **배포 안전성**
   - 명시적 `--source` 옵션 사용
   - 템플릿 생성으로 사전 검증
   - 환경별 kubeconfig 분리

5. **CI/CD 통합**
   - 환경 변수로 sources 파일 선택
   - 환경별 파이프라인 구성
   - 자동 배포 + 수동 승인 (프로덕션)
