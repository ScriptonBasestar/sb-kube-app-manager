# SBKube Examples

SBKube의 다양한 사용 사례를 보여주는 실전 예제 모음입니다.

## 📁 디렉토리 구조

```
examples/
├── README.md                          # 이 파일
├── use-cases/                         # 실전 시나리오 예제 (11개)
│   ├── 01-dev-environment/            # 완전한 개발 환경 구축
│   ├── 02-wiki-stack/                 # MediaWiki + MySQL + Traefik
│   ├── 03-monitoring-stack/           # Prometheus + Grafana 모니터링
│   ├── 04-cicd-stack/                 # GitLab Runner + Docker Registry
│   ├── 05-logging-stack/              # Loki + Promtail + Grafana
│   ├── 06-ingress-controller/         # Traefik 고급 라우팅
│   ├── 07-cert-manager/               # TLS 인증서 자동화
│   ├── 08-service-mesh/               # Linkerd Service Mesh
│   ├── 09-backup-restore/             # Velero 백업/복구
│   ├── 10-database-cluster/           # PostgreSQL HA 클러스터
│   └── 11-message-queue/              # RabbitMQ 메시징
├── app-types/                         # 애플리케이션 타입별 예제 (8개)
│   ├── 01-helm/                       # Helm 차트 배포
│   ├── 02-yaml/                       # YAML 매니페스트 배포
│   ├── 03-git/                        # Git 리포지토리 연동
│   ├── 04-action/                     # Action 타입 (CRD 설치 등)
│   ├── 05-exec/                       # Exec 타입 (스크립트 실행)
│   ├── 06-http/                       # HTTP 다운로드
│   ├── 07-kustomize/                  # Kustomize (환경별 설정)
│   └── 08-noop/                       # Noop (수동 작업 표현)
├── advanced-features/                 # 고급 기능 예제 (6개)
│   ├── 01-enabled-flag/               # 조건부 배포 (enabled)
│   ├── 02-complex-dependencies/       # 복잡한 의존성 관리
│   ├── 03-helm-customization/         # Helm 고급 기능
│   ├── 04-multi-namespace/            # 멀티 네임스페이스 배포
│   ├── 05-helm-hooks/                 # Helm Hooks (pre/post install)
│   └── 06-progressive-delivery/       # Canary/Blue-Green 배포
├── security/                          # 보안 예제 (4개)
│   ├── 01-sealed-secrets/             # Secret 암호화 (GitOps)
│   ├── 02-rbac/                       # 권한 관리
│   ├── 03-network-policies/           # 네트워크 격리
│   └── 04-pod-security/               # Pod 보안 컨텍스트
├── integration/                       # 통합 예제 (3개)
│   ├── 01-full-stack-app/             # Full-Stack 애플리케이션
│   ├── 02-microservices/              # 마이크로서비스 아키텍처
│   └── 03-data-pipeline/              # 데이터 파이프라인 (Kafka+Spark)
└── patterns/                          # 운영 패턴 (4개)
    ├── 01-gitops/                     # GitOps (ArgoCD)
    ├── 02-disaster-recovery/          # 재해 복구 자동화
    ├── 03-multi-cluster/              # 멀티 클러스터 관리
    └── 04-cost-optimization/          # 비용 최적화 (HPA, VPA, PDB)
```

> **📚 학습 튜토리얼**: 단계별 학습 가이드는 **[docs/tutorials/](../docs/tutorials/README.md)** 를 참조하세요.

## 🚀 빠른 시작

### 처음 사용하시나요?

**[docs/tutorials/](../docs/tutorials/README.md)** 에서 단계별 학습 가이드를 확인하세요!

### 실전 프로젝트를 시작하시나요?

**Use Cases** 디렉토리에서 프로젝트와 유사한 예제를 찾아보세요:

- **개발 환경**: [01-dev-environment](use-cases/01-dev-environment/)
- **Wiki 시스템**: [02-wiki-stack](use-cases/02-wiki-stack/)
- **모니터링**: [03-monitoring-stack](use-cases/03-monitoring-stack/)
- **CI/CD**: [04-cicd-stack](use-cases/04-cicd-stack/)
- **로깅**: [05-logging-stack](use-cases/05-logging-stack/)

## 📚 예제 카탈로그

**총 38개 예제** | 8개 앱 타입 100% 커버리지 | 프로덕션 준비 완료

| 카테고리 | 예제 수 | 설명 |
|----------|---------|------|
| **Use Cases** | 11 | 실전 시나리오 (인프라, 보안, 메시징) |
| **App Types** | 8 | 모든 앱 타입 (helm, yaml, git, action, exec, http, kustomize, noop) |
| **Advanced Features** | 6 | 고급 배포 기능 (멀티 NS, Hooks, Canary) |
| **Security** | 4 | 보안 베스트 프랙티스 |
| **Integration** | 3 | Full-Stack, 마이크로서비스, 데이터 파이프라인 |
| **Patterns** | 4 | 운영 패턴 (GitOps, DR, Multi-Cluster, Cost) |

---

### 💼 Use Cases (실전 시나리오)

| 예제 | 설명 | 포함된 기술 스택 |
|------|------|-----------------|
| [01-dev-environment](use-cases/01-dev-environment/) | 완전한 개발 환경 구축 | Redis, PostgreSQL, Mailhog, MinIO |
| [02-wiki-stack](use-cases/02-wiki-stack/) | 프로덕션급 Wiki 시스템 | MediaWiki, MySQL, Traefik Ingress |
| [03-monitoring-stack](use-cases/03-monitoring-stack/) | 완전한 모니터링 시스템 | Prometheus, Grafana, AlertManager |
| [04-cicd-stack](use-cases/04-cicd-stack/) | CI/CD 인프라 구축 | GitLab Runner, Docker Registry, MinIO |
| [05-logging-stack](use-cases/05-logging-stack/) | 로그 집계 및 시각화 | Loki, Promtail, Grafana |
| [06-ingress-controller](use-cases/06-ingress-controller/) | Traefik 고급 라우팅 | Traefik IngressRoute, Middlewares |
| [07-cert-manager](use-cases/07-cert-manager/) | TLS 인증서 자동화 | cert-manager, Let's Encrypt |
| [08-service-mesh](use-cases/08-service-mesh/) | Service Mesh 구현 | Linkerd, mTLS, Metrics |
| [09-backup-restore](use-cases/09-backup-restore/) | 백업/복구 자동화 | Velero, MinIO, Restic |
| [10-database-cluster](use-cases/10-database-cluster/) | 고가용성 데이터베이스 | PostgreSQL HA, Pgpool-II |
| [11-message-queue](use-cases/11-message-queue/) | 메시지 큐 클러스터 | RabbitMQ, Producer/Consumer |

### 🔧 App Types (타입별 예제)

| 예제 | 설명 | 타입 |
|------|------|------|
| [01-helm](app-types/01-helm/) | Helm 차트 배포 (원격/로컬, overrides/removes) | helm |
| [02-yaml](app-types/02-yaml/) | Kubernetes 매니페스트 배포 | yaml |
| [03-git](app-types/03-git/) | Git 리포지토리 연동 | git |
| [04-action](app-types/04-action/) | 커스텀 액션 (CRD 설치, 순차 배포) | action |
| [05-exec](app-types/05-exec/) | 명령어 실행 (초기화, 검증) | exec |
| [06-http](app-types/06-http/) | HTTP URL에서 파일 다운로드 | http |
| [07-kustomize](app-types/07-kustomize/) | Kustomize base/overlay 패턴 (환경별 설정) | kustomize |
| [08-noop](app-types/08-noop/) | 수동 작업을 의존성 체인에 표현 | noop |

### ⚡ Advanced Features (고급 기능)

| 예제 | 설명 | 주요 기능 |
|------|------|----------|
| [01-enabled-flag](advanced-features/01-enabled-flag/) | 조건부 배포 | enabled: true/false |
| [02-complex-dependencies](advanced-features/02-complex-dependencies/) | 복잡한 의존성 체인 | depends_on 체인, 마이크로서비스 |
| [03-helm-customization](advanced-features/03-helm-customization/) | Helm 고급 커스터마이징 | set_values, release_name, Values 병합 |
| [04-multi-namespace](advanced-features/04-multi-namespace/) | 멀티 네임스페이스 배포 | Cross-namespace 통신, FQDN |
| [05-helm-hooks](advanced-features/05-helm-hooks/) | Helm Hooks 활용 | pre/post install/delete hooks |
| [06-progressive-delivery](advanced-features/06-progressive-delivery/) | 점진적 배포 전략 | Canary, Blue-Green, Traffic Split |

### 🔐 Security (보안)

| 예제 | 설명 | 주요 기능 |
|------|------|----------|
| [01-sealed-secrets](security/01-sealed-secrets/) | Secret 암호화 관리 | GitOps, Public/Private Key 암호화 |
| [02-rbac](security/02-rbac/) | 권한 기반 접근 제어 | ServiceAccount, Role, RoleBinding |
| [03-network-policies](security/03-network-policies/) | 네트워크 트래픽 격리 | Pod 간 통신 제한, Zero Trust |
| [04-pod-security](security/04-pod-security/) | Pod 보안 강화 | SecurityContext, Non-root, 읽기전용 FS |

### 🔗 Integration (통합 예제)

| 예제 | 설명 | 주요 기능 |
|------|------|----------|
| [01-full-stack-app](integration/01-full-stack-app/) | Full-Stack 애플리케이션 | Frontend + Backend + DB + Cache + Ingress |
| [02-microservices](integration/02-microservices/) | 마이크로서비스 아키텍처 | 5개 서비스 + API Gateway + Service Discovery |
| [03-data-pipeline](integration/03-data-pipeline/) | 데이터 파이프라인 | Kafka + Spark + MinIO |

### 🏗️ Patterns (운영 패턴)

| 예제 | 설명 | 주요 기능 |
|------|------|----------|
| [01-gitops](patterns/01-gitops/) | GitOps 패턴 | ArgoCD, 자동 동기화, Self-Healing |
| [02-disaster-recovery](patterns/02-disaster-recovery/) | 재해 복구 자동화 | Velero Schedule, 복구 절차 |
| [03-multi-cluster](patterns/03-multi-cluster/) | 멀티 클러스터 관리 | KubeFed, 클러스터 연합 |
| [04-cost-optimization](patterns/04-cost-optimization/) | 비용 최적화 | HPA, VPA, PDB, Resource Quotas |

## 🎯 시나리오별 추천 예제

### "처음 사용해봅니다"
1. **[docs/tutorials/](../docs/tutorials/README.md)** 에서 단계별 학습 시작
2. [App Type: Helm](app-types/01-helm/) - Helm 차트 배포 방법
3. [App Type: YAML](app-types/02-yaml/) - 간단한 YAML 배포
4. [Use Case: Dev Environment](use-cases/01-dev-environment/) - 실전 예제

### "k3s에 개발 환경을 구축하고 싶어요"
→ [Use Case 01: Development Environment](use-cases/01-dev-environment/)

**포함 내용**:
- Redis (세션 스토어)
- PostgreSQL (데이터베이스)
- Mailhog (이메일 테스트)
- MinIO (S3 호환 스토리지)

### "Wiki 시스템을 구축하고 싶어요"
→ [Use Case 02: Wiki Stack](use-cases/02-wiki-stack/)

**포함 내용**:
- MediaWiki (Wiki 애플리케이션)
- MySQL (데이터베이스)
- Traefik Ingress (외부 접근)
- Persistence 설정
- 프로덕션 체크리스트

### "클러스터 모니터링을 하고 싶어요"
→ [Use Case 03: Monitoring Stack](use-cases/03-monitoring-stack/)

**포함 내용**:
- Prometheus (메트릭 수집)
- Grafana (시각화 대시보드)
- AlertManager (알림)
- 사전 구성된 대시보드
- 알림 규칙 예제

### "YAML 매니페스트를 직접 배포하고 싶어요"
→ [App Type: YAML](app-types/02-yaml/)

**학습 내용**:
- Kubernetes YAML 직접 작성
- Deployment, Service, ConfigMap
- kubectl apply 방식

### "Private Git 리포지토리의 차트를 사용하고 싶어요"
→ [App Type: Git](app-types/03-git/)

**학습 내용**:
- Git 리포지토리 클론
- SSH/Token 인증
- depends_on 활용

### "HTTP URL에서 매니페스트를 다운로드하고 싶어요"
→ [App Type: HTTP](app-types/06-http/)

**학습 내용**:
- GitHub Raw URL에서 다운로드
- HTTP 헤더 인증
- CRD 다운로드 패턴

### "배포 전후에 스크립트를 실행하고 싶어요"
→ [App Type: Exec](app-types/05-exec/)

**학습 내용**:
- 헬스 체크 스크립트
- DB 마이그레이션
- 배포 전후 검증

### "CRD를 먼저 설치하고 Operator를 배포하고 싶어요"
→ [App Type: Action](app-types/04-action/)

**학습 내용**:
- 순차적 리소스 배포
- CRD 설치 패턴
- apply/delete 액션

### "환경별로 다른 설정을 관리하고 싶어요"
→ [App Type: Kustomize](app-types/07-kustomize/)

**학습 내용**:
- Kustomize base/overlay 패턴
- 환경별 패치 (dev/prod)
- 설정 재사용 및 오버라이드

### "수동 작업과 자동 배포를 함께 관리하고 싶어요"
→ [App Type: Noop](app-types/08-noop/)

**학습 내용**:
- 수동 설정을 의존성으로 표현
- k3s 기본 리소스 활용 (Traefik, CoreDNS)
- 외부 관리 시스템 통합

### "CI/CD 파이프라인을 구축하고 싶어요"
→ [Use Case: CI/CD Stack](use-cases/04-cicd-stack/)

**학습 내용**:
- GitLab Runner 설정
- 프라이빗 Docker Registry
- MinIO S3 백엔드

### "로그를 중앙에서 관리하고 싶어요"
→ [Use Case: Logging Stack](use-cases/05-logging-stack/)

**학습 내용**:
- Loki + Promtail 연동
- LogQL 쿼리
- Grafana 로그 시각화

### "Helm 차트를 더 세밀하게 제어하고 싶어요"
→ [Advanced Feature: Helm Customization](advanced-features/03-helm-customization/)

**학습 내용**:
- set_values로 CLI 값 오버라이드
- release_name 커스터마이징
- Values 파일 병합 우선순위

### "Secret을 안전하게 관리하고 싶어요"
→ [Security: Sealed Secrets](security/01-sealed-secrets/)

**학습 내용**:
- GitOps 워크플로우에서 Secret 관리
- Public/Private Key 암호화
- kubeseal CLI 사용법

### "권한을 세밀하게 제어하고 싶어요"
→ [Security: RBAC](security/02-rbac/)

**학습 내용**:
- ServiceAccount 생성
- Role/RoleBinding 설정
- 최소 권한 원칙

### "Pod 간 통신을 제한하고 싶어요"
→ [Security: Network Policies](security/03-network-policies/)

**학습 내용**:
- NetworkPolicy로 트래픽 격리
- 3-Tier 아키텍처 보안
- Zero Trust 네트워크

### "Pod 보안을 강화하고 싶어요"
→ [Security: Pod Security](security/04-pod-security/)

**학습 내용**:
- SecurityContext 설정
- Non-root 실행
- 읽기 전용 파일시스템

### "고급 기능을 사용하고 싶어요"
→ [Advanced Features](advanced-features/) 디렉토리

**주요 기능**:
- **조건부 배포**: [enabled-flag](advanced-features/01-enabled-flag/)
- **복잡한 의존성**: [complex-dependencies](advanced-features/02-complex-dependencies/)
- **Helm 커스터마이징**: [helm-customization](advanced-features/03-helm-customization/)

## 🏗️ 예제 구조 이해하기

모든 예제는 다음 구조를 따릅니다:

```
example-dir/
├── README.md           # 예제 설명 및 사용법
├── config.yaml         # SBKube 설정 (앱 정의)
├── sources.yaml        # 외부 소스 정의 (Helm repos, Git repos)
└── values/             # Helm values 파일들
    └── app-values.yaml
```

### 핵심 파일 설명

#### config.yaml
```yaml
namespace: my-namespace

apps:
  app-name:
    type: helm
    chart: bitnami/redis
    version: "17.13.2"
    values:
      - redis-values.yaml
```

#### sources.yaml
```yaml
helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami

git_repos:
  my-charts:
    url: https://github.com/org/charts.git
    branch: main
```

## 🔄 예제 실행 방법

### 1. 기본 실행 (권장)
```bash
cd examples/use-cases/01-dev-environment
sbkube apply --app-dir .
```

### 2. 단계별 실행
```bash
# 소스 준비 (Helm 차트 다운로드, Git 클론 등)
sbkube prepare --app-dir .

# 앱 빌드 (차트 커스터마이징 등)
sbkube build --app-dir .

# 템플릿 렌더링
sbkube template --app-dir . --output-dir rendered/

# 배포
sbkube deploy --app-dir .
```

### 3. 특정 앱만 배포
```bash
# 하나만 배포
sbkube apply --app-dir . --apps redis

# 여러 개 배포
sbkube apply --app-dir . --apps redis,postgresql
```

### 4. 다른 네임스페이스에 배포
```bash
sbkube apply --app-dir . --namespace custom-namespace
```

## 🧪 예제 테스트

### 배포 확인
```bash
# Pod 상태
kubectl get pods -n <namespace>

# 서비스 확인
kubectl get svc -n <namespace>

# Helm 릴리스
helm list -n <namespace>

# 전체 리소스
kubectl get all -n <namespace>
```

### 정리
```bash
# SBKube로 삭제
sbkube delete --app-dir .

# 또는 네임스페이스 삭제
kubectl delete namespace <namespace>
```

## 💡 자주 묻는 질문

### Q: 예제를 내 프로젝트에 적용하려면?

1. 예제 디렉토리를 복사합니다
2. `config.yaml`을 프로젝트에 맞게 수정합니다
3. Values 파일을 환경에 맞게 조정합니다
4. `sbkube apply`로 배포합니다

### Q: 프로덕션 환경에서 사용할 때 주의사항은?

예제는 대부분 **개발/테스트 환경용**입니다. 프로덕션에서는:

- ✅ Persistence를 활성화하세요
- ✅ 강력한 비밀번호를 사용하세요
- ✅ 리소스 제한을 적절히 조정하세요
- ✅ 백업 정책을 수립하세요
- ✅ 모니터링을 설정하세요

각 예제의 README.md에 **"프로덕션 체크리스트"**가 있습니다.

### Q: 예제가 작동하지 않아요

1. **Helm 리포지토리 확인**
   ```bash
   helm repo update
   ```

2. **kubectl 연결 확인**
   ```bash
   kubectl cluster-info
   ```

3. **SBKube 버전 확인**
   ```bash
   sbkube --version
   ```

4. **상세 로그 확인**
   ```bash
   sbkube apply --app-dir . --verbose
   ```

### Q: 다른 Helm 리포지토리를 사용하고 싶어요

`sources.yaml`에 추가하세요:
```yaml
helm_repos:
  my-repo:
    url: https://my-repo.example.com/charts
```

## 📖 추가 자료

- [SBKube Documentation](../docs/)
- [Chart Customization Guide](../docs/03-configuration/chart-customization.md)
- [Configuration Schema](../docs/03-configuration/config-schema.md)
- [Troubleshooting](../docs/07-troubleshooting/)

## 🤝 기여하기

새로운 예제를 제안하거나 개선사항이 있으시면:

1. [GitHub Issues](https://github.com/ScriptonBasestar/sb-kube-app-manager/issues)에 제안해주세요
2. Pull Request를 보내주세요

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](../LICENSE) 파일을 참조하세요.

---

**Happy deploying with SBKube! 🚀**

*k3s 환경에 특화된 Kubernetes 배포 자동화 도구*
