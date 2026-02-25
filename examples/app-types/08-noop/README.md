# App Type: Noop (No Operation)

수동으로 설정된 리소스를 의존성 체인에 포함시키기 위한 특수 타입입니다.

## 📋 개요

**App Type**: `noop`

**학습 목표**:
- Noop 타입의 용도 이해
- 수동 설정과 자동 배포 연계
- 의존성 체인에서 수동 작업 표현

## 🎯 사용 사례

### 1. 수동으로 설치된 인프라

클러스터에 이미 설치되어 있는 리소스 (수동 또는 다른 도구로 설치):
- Traefik (k3s 기본 설치)
- cert-manager (수동 설치)
- Operators (Helm으로 직접 설치)

### 2. 외부 의존성

SBKube가 관리하지 않는 외부 시스템:
- 외부 데이터베이스 (RDS, Cloud SQL)
- 외부 메시징 시스템 (AWS SQS, GCP Pub/Sub)
- 수동으로 생성된 ConfigMap/Secret

### 3. 배포 순서 제어

수동 작업과 자동 배포를 순서대로 연결:
```
수동 네트워크 설정 (noop)
    ↓
네트워크 정책 배포 (yaml)
    ↓
애플리케이션 배포 (helm)
```

## 🚀 빠른 시작

### 1. 예제 배포

```bash
# Noop 타입은 실제로 아무것도 하지 않으므로
# 의존성이 있는 앱만 배포됩니다
sbkube apply --app-dir examples/app-types/08-noop --namespace noop-demo
```

### 2. 배포 확인

```bash
# Noop 앱은 실제 리소스가 없음
kubectl get all -n noop-demo

# nginx만 배포됨
kubectl get pods -n noop-demo
```

### 3. 의존성 체인 확인

```bash
# 상태 확인
sbkube state list

# manual-setup은 처리되었지만 실제 리소스는 없음
# nginx는 manual-setup 완료 후 배포됨
```

## 📖 설정 파일 설명

### sbkube.yaml

```yaml
namespace: noop-demo

apps:
  # 1단계: 수동으로 설정되었다고 가정하는 작업
  manual-setup:
    type: noop
    description: "수동으로 설정된 네트워크 정책 (이미 완료)"
    enabled: true

  # 2단계: manual-setup 후에 배포되는 앱
  nginx:
    type: yaml
    files:
      - manifests/nginx-deployment.yaml
    depends_on:
      - manual-setup  # noop 작업 완료 후 배포
```

### 실행 흐름

```
1. manual-setup (noop) → 즉시 완료 (아무것도 하지 않음)
2. nginx (yaml) → manual-setup 완료 후 배포
```

## 🔧 주요 기능

### 1. 기본 Noop 설정

```yaml
apps:
  base-infrastructure:
    type: noop
    description: "이미 설치된 Traefik 인그레스 컨트롤러"
```

**주요 필드**:
- `type: noop` (필수)
- `description` (권장): 수동 작업 설명
- `enabled` (선택): true/false (기본값: true)

### 2. 의존성 체인에서 사용

```yaml
apps:
  # Noop: k3s에 기본 설치된 Traefik
  traefik-ingress-controller:
    type: noop
    description: "k3s에 기본 설치된 Traefik (v2.x)"

  # Traefik이 있다고 가정하고 Ingress 생성
  app-ingress:
    type: yaml
    files:
      - ingress.yaml
    depends_on:
      - traefik-ingress-controller
```

### 3. 다단계 수동/자동 혼합

```yaml
apps:
  # 1단계: 수동 네트워크 설정 (noop)
  network-setup:
    type: noop
    description: "수동으로 생성된 NetworkPolicy"

  # 2단계: 수동 데이터베이스 (noop)
  external-database:
    type: noop
    description: "AWS RDS PostgreSQL (외부 관리)"
    depends_on:
      - network-setup

  # 3단계: 애플리케이션 배포 (helm)
  backend-service:
    type: helm
    chart: my/backend
    depends_on:
      - external-database
```

## 🎓 학습 포인트

### 1. Noop vs 실제 배포

| 비교 | Noop | 실제 배포 (helm/yaml) |
|------|------|----------------------|
| **목적** | 의존성 표현 | 실제 리소스 생성 |
| **동작** | 아무것도 하지 않음 | kubectl apply/helm install |
| **상태** | 기록만 남김 | Kubernetes 리소스 생성 |
| **사용** | 수동 작업, 외부 리소스 | 자동 배포 |

### 2. 언제 Noop을 사용하나?

**✅ 사용해야 할 때**:
- k3s 기본 설치 리소스 (Traefik, CoreDNS)
- 수동으로 설치한 Operator
- 외부 관리 시스템 (클라우드 DB, 메시징)
- 다른 팀이 관리하는 리소스

**❌ 사용하지 말아야 할 때**:
- SBKube가 배포할 수 있는 리소스
- 자동화 가능한 작업
- 반복적으로 생성/삭제되는 리소스

### 3. 의존성 체인의 역할

```yaml
# 잘못된 예: noop 없이 바로 배포
apps:
  app-ingress:
    type: yaml
    files: [ingress.yaml]
    # Traefik이 없으면 실패할 수 있음 (하지만 알 수 없음)

# 올바른 예: noop으로 명시적 의존성 표현
apps:
  traefik:
    type: noop
    description: "k3s 기본 Traefik"

  app-ingress:
    type: yaml
    files: [ingress.yaml]
    depends_on: [traefik]  # 명확한 의존성
```

## 🧪 테스트 시나리오

### 시나리오 1: 기본 Noop 사용

```bash
# 배포
sbkube apply --app-dir examples/app-types/08-noop --namespace noop-demo

# 확인 (nginx만 실제로 배포됨)
kubectl get all -n noop-demo

# 상태 확인 (manual-setup도 기록됨)
sbkube state list
```

### 시나리오 2: 의존성 체인 테스트

```yaml
# sbkube.yaml 수정
apps:
  step1:
    type: noop
    description: "1단계 수동 작업"

  step2:
    type: noop
    description: "2단계 수동 작업"
    depends_on: [step1]

  app:
    type: yaml
    files: [manifests/nginx-deployment.yaml]
    depends_on: [step1, step2]
```

```bash
# 배포 (step1 → step2 → app 순서)
sbkube apply -f sbkube.yaml --namespace noop-demo

# 상태 확인 (모든 단계 기록됨)
sbkube state list
```

### 시나리오 3: enabled=false 테스트

```yaml
apps:
  optional-setup:
    type: noop
    description: "선택적 설정"
    enabled: false  # 비활성화

  app:
    type: yaml
    files: [manifests/nginx-deployment.yaml]
    depends_on: [optional-setup]  # 의존성 무시됨
```

## 🔍 트러블슈팅

### 문제 1: "Noop 앱이 실제로 배포되지 않아요"

**원인**: 정상 동작입니다! Noop은 실제로 배포하지 않습니다.

**확인**:
```bash
# Noop은 상태만 기록됨
sbkube state list

# 실제 Kubernetes 리소스는 없음
kubectl get all -n <namespace> -l app=<noop-app-name>
```

### 문제 2: "의존성 앱이 배포되지 않아요"

**원인**: Noop의 enabled=false이거나 다른 문제

**해결**:
```bash
# Noop 앱이 활성화되어 있는지 확인
grep -A 3 "type: noop" sbkube.yaml

# 의존성 체인 확인
grep -A 5 "depends_on" sbkube.yaml
```

### 문제 3: "순서가 보장되지 않아요"

**원인**: depends_on 설정 누락

**해결**:
```yaml
# 명시적 의존성 추가
apps:
  noop-task:
    type: noop

  real-task:
    type: helm
    chart: my/app
    depends_on:
      - noop-task  # 필수!
```

## 💡 실전 패턴

### 패턴 1: k3s 기본 리소스

```yaml
# k3s에 이미 설치된 리소스들
apps:
  traefik:
    type: noop
    description: "k3s 기본 Traefik IngressController"

  coredns:
    type: noop
    description: "k3s 기본 CoreDNS"

  local-path-provisioner:
    type: noop
    description: "k3s 기본 StorageClass"

  # 위 리소스들을 사용하는 앱
  my-app:
    type: helm
    chart: my/app
    depends_on:
      - traefik
      - local-path-provisioner
```

### 패턴 2: 외부 관리 시스템

```yaml
apps:
  aws-rds-postgres:
    type: noop
    description: "AWS RDS PostgreSQL 12.x (외부 관리)"

  redis-elasticache:
    type: noop
    description: "AWS ElastiCache Redis (외부 관리)"

  backend-api:
    type: helm
    chart: my/backend
    depends_on:
      - aws-rds-postgres
      - redis-elasticache
    values:
      - backend-values.yaml  # DB 연결 정보 포함
```

### 패턴 3: 단계별 수동/자동 혼합

```yaml
apps:
  # Phase 1: 수동 인프라 (noop)
  manual-network:
    type: noop
    description: "수동 생성 NetworkPolicy 및 Security Groups"

  manual-secrets:
    type: noop
    description: "Sealed Secrets로 암호화된 시크릿 (수동 적용)"
    depends_on: [manual-network]

  # Phase 2: 자동 데이터베이스
  postgres:
    type: helm
    chart: cloudnative-pg/cloudnative-pg
    depends_on: [manual-network, manual-secrets]

  # Phase 3: 자동 애플리케이션
  app:
    type: helm
    chart: my/app
    depends_on: [postgres, manual-secrets]
```

## 📚 추가 학습 자료

### SBKube 관련 문서
- [Application Types](../../docs/02-features/application-types.md)
- [Dependency Management](../../docs/02-features/commands.md#의존성-관리)
- [State Management](../../docs/02-features/commands.md#상태-관리)

### 관련 예제
- [Complex Dependencies](../../advanced-features/02-complex-dependencies/) - 복잡한 의존성 체인
- [Enabled Flag](../../advanced-features/01-enabled-flag/) - 조건부 배포

## 🎯 다음 단계

1. **의존성 체인 설계**: Noop을 활용해 수동/자동 작업 혼합
2. **외부 시스템 통합**: 클라우드 서비스와 k8s 앱 연계
3. **단계별 배포**: Phase 기반 배포 전략 수립

## 🧹 정리

```bash
# 네임스페이스 삭제 (Noop은 실제 리소스가 없으므로 nginx만 삭제됨)
kubectl delete namespace noop-demo
```

---

**Noop으로 수동 작업과 자동 배포를 명확히 연결하세요! 🔗**
