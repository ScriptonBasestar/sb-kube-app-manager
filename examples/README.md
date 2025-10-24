# SBKube Examples

SBKube의 다양한 사용 사례를 보여주는 **실행 가능한 예제 설정 파일** 모음입니다.

> **📚 학습이 필요하신가요?**
> 단계별 튜토리얼과 학습 가이드는 **[docs/tutorials/](../docs/tutorials/README.md)** 를 참조하세요.

---

## 📁 디렉토리 구조

```
examples/
├── README.md                 # 이 파일 (예제 카탈로그)
├── basic/                    # 기본 예제 (Redis 단일 앱)
├── k3scode/                  # K3s 코드 서버 예제
├── advanced-example/         # 고급 예제 (멀티 앱, 커스터마이징)
├── use-cases/                # 실전 시나리오 예제 (계획)
│   ├── 01-dev-environment/   # 완전한 개발 환경 구축
│   ├── 02-wiki-stack/        # MediaWiki + MySQL + Traefik
│   └── 03-monitoring-stack/  # Prometheus + Grafana 모니터링
└── app-types/                # 애플리케이션 타입별 예제 (계획)
    ├── 01-helm/              # Helm 차트 배포
    ├── 02-yaml/              # YAML 매니페스트 배포
    └── 03-git/               # Git 리포지토리 연동
```

---

## 🚀 빠른 시작

### 처음 사용하시나요?

**학습 경로**: [docs/tutorials/](../docs/tutorials/README.md)
1. [01-getting-started.md](../docs/tutorials/01-getting-started.md) - 첫 배포 (10-15분)
2. 이후 실전 예제로 진행

### 실전 프로젝트를 바로 시작하시나요?

아래 예제 중 프로젝트와 유사한 것을 찾아 복사하여 수정하세요:
- **단일 앱**: [basic/](basic/)
- **멀티 앱**: [advanced-example/](advanced-example/)
- **k3s 특화**: [k3scode/](k3scode/)

---

## 📚 예제 카탈로그

### 현재 사용 가능한 예제

| 예제 | 설명 | 파일 |
|------|------|------|
| **[basic/](basic/)** | 단일 Helm 차트 배포 (Redis) | config.yaml, sources.yaml, redis-values.yaml |
| **[k3scode/](k3scode/)** | K3s 환경에서 다중 앱 배포 | config.yaml, sources.yaml, values/ |
| **[advanced-example/](advanced-example/)** | 고급 기능 (overrides, removes, depends_on) | config.yaml, sources.yaml |

### 계획된 예제 (v0.5.0+)

#### 💼 Use Cases (실전 시나리오)

| 예제 | 설명 | 포함된 기술 스택 | 상태 |
|------|------|-----------------|------|
| 01-dev-environment | 완전한 개발 환경 구축 | Redis, PostgreSQL, Mailhog, MinIO | 🔜 계획 |
| 02-wiki-stack | 프로덕션급 Wiki 시스템 | MediaWiki, MySQL, Traefik Ingress | 🔜 계획 |
| 03-monitoring-stack | 완전한 모니터링 시스템 | Prometheus, Grafana, AlertManager | 🔜 계획 |

#### 🔧 App Types (타입별 예제)

| 예제 | 설명 | 타입 | 상태 |
|------|------|------|------|
| 01-helm | Helm 차트 배포 (원격/로컬) | helm | 🔜 계획 |
| 02-yaml | Kubernetes 매니페스트 배포 | yaml | 🔜 계획 |
| 03-git | Git 리포지토리 연동 | git | 🔜 계획 |

---

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

---

## 🔄 예제 실행 방법

### 1. 기본 실행 (권장)
```bash
cd examples/basic
sbkube apply
```

또는 외부에서:
```bash
sbkube apply --app-dir examples/basic
```

### 2. 단계별 실행 (디버깅용)
```bash
cd examples/basic

# 1. 소스 준비 (Helm 차트 다운로드, Git 클론)
sbkube prepare

# 2. 앱 빌드 (차트 커스터마이징)
sbkube build

# 3. 템플릿 렌더링 (최종 YAML 확인)
sbkube template --output-dir /tmp/rendered

# 4. 배포
sbkube deploy
```

### 3. 특정 앱만 배포 (멀티 앱 예제)
```bash
cd examples/advanced-example

# 하나만 배포
sbkube apply --app redis

# 여러 개 배포
sbkube apply --app redis,postgresql
```

### 4. 다른 네임스페이스에 배포
```bash
sbkube apply --namespace custom-namespace
```

### 5. Dry-run (실제 배포 없이 확인)
```bash
sbkube apply --dry-run
```

---

## 🧪 예제 테스트

### 배포 확인
```bash
# Pod 상태 확인
kubectl get pods -n <namespace>

# 서비스 확인
kubectl get svc -n <namespace>

# Helm 릴리스 확인
helm list -n <namespace>

# SBKube 상태 확인
sbkube state list
sbkube state history --namespace <namespace>

# 전체 리소스
kubectl get all -n <namespace>
```

### 애플리케이션 접근
```bash
# Port-forward로 로컬 접근 (예: Redis)
kubectl port-forward svc/redis-master 6379:6379 -n <namespace>

# 다른 터미널에서
redis-cli -h localhost -p 6379 ping
```

### 정리
```bash
# SBKube로 삭제 (권장)
sbkube delete

# 또는 네임스페이스 전체 삭제
kubectl delete namespace <namespace>
```

---

## 🎯 시나리오별 추천 예제

### "처음 사용해봅니다"
1. **[docs/tutorials/01-getting-started.md](../docs/tutorials/01-getting-started.md)** - 단계별 학습
2. **[basic/](basic/)** - 가장 간단한 예제로 실습
3. **[docs/tutorials/02-multi-app-deployment.md](../docs/tutorials/02-multi-app-deployment.md)** - 다중 앱 학습

### "k3s에 간단한 앱을 배포하고 싶어요"
→ **[basic/](basic/)** - Redis 단일 앱 배포

**실행**:
```bash
cd examples/basic
sbkube apply
kubectl get pods -n basic
```

### "여러 앱을 한번에 관리하고 싶어요"
→ **[advanced-example/](advanced-example/)** - 멀티 앱 + 의존성 관리

**실행**:
```bash
cd examples/advanced-example
sbkube apply
```

### "k3s 코드 서버 환경을 구축하고 싶어요"
→ **[k3scode/](k3scode/)** - 실제 프로덕션 예제

**실행**:
```bash
cd examples/k3scode
sbkube apply --app-dir memory --namespace data-memory
```

### "Helm 차트를 커스터마이징하고 싶어요"
→ **[docs/tutorials/04-customization.md](../docs/tutorials/04-customization.md)** - overrides/removes 학습

---

## 💡 예제 활용 팁

### 예제를 내 프로젝트에 적용하기

1. **예제 복사**
   ```bash
   cp -r examples/basic my-project
   cd my-project
   ```

2. **설정 수정**
   ```bash
   # config.yaml 수정
   vim config.yaml

   # namespace, app 이름, chart 버전 등 변경
   ```

3. **Values 조정**
   ```bash
   # values 파일 수정
   vim values/my-app.yaml

   # 리소스 제한, 비밀번호, 환경 변수 등 조정
   ```

4. **배포**
   ```bash
   sbkube apply
   ```

### 프로덕션 사용 시 주의사항

예제는 대부분 **개발/테스트 환경용**입니다. 프로덕션에서는:

- ✅ **Persistence 활성화**: 데이터 손실 방지
- ✅ **강력한 비밀번호**: 기본값 절대 사용 금지
- ✅ **리소스 제한 조정**: CPU/메모리 requests/limits 설정
- ✅ **백업 정책 수립**: 정기 백업 스케줄
- ✅ **모니터링 설정**: Prometheus/Grafana 통합
- ✅ **고가용성 구성**: replicaCount: 3 이상
- ✅ **보안 설정**: RBAC, NetworkPolicy, PodSecurityPolicy

각 예제의 README.md에 **"프로덕션 체크리스트"**가 포함되어 있습니다.

---

## 🔍 트러블슈팅

### 예제가 작동하지 않을 때

1. **Helm 리포지토리 업데이트**
   ```bash
   helm repo update
   ```

2. **kubectl 연결 확인**
   ```bash
   kubectl cluster-info
   kubectl get nodes
   ```

3. **SBKube 버전 확인**
   ```bash
   sbkube --version
   # sbkube, version 0.4.7
   ```

4. **상세 로그 확인**
   ```bash
   sbkube --verbose apply
   ```

5. **설정 검증**
   ```bash
   sbkube validate
   ```

### 자주 발생하는 문제

| 문제 | 원인 | 해결 방법 |
|------|------|----------|
| Chart not found | Helm 리포지토리 미등록 | `helm repo add bitnami https://charts.bitnami.com/bitnami` |
| Namespace not found | 네임스페이스 없음 | `kubectl create namespace <name>` |
| ImagePullBackOff | 이미지 없음/권한 | 이미지 이름, 태그, registry 확인 |
| Pending Pod | 리소스 부족 | `kubectl describe pod <pod>` 확인 |

더 자세한 내용은 **[docs/tutorials/05-troubleshooting.md](../docs/tutorials/05-troubleshooting.md)** 참조

---

## 📖 추가 자료

### 문서
- **[튜토리얼](../docs/tutorials/README.md)** - 단계별 학습 가이드
- **[설정 스키마](../docs/03-configuration/config-schema.md)** - config.yaml 상세 설명
- **[애플리케이션 타입](../docs/02-features/application-types.md)** - helm, yaml, git 타입 가이드
- **[차트 커스터마이징](../docs/03-configuration/chart-customization.md)** - overrides, removes 사용법

### 외부 자료
- [Helm 문서](https://helm.sh/docs/)
- [Kubernetes 문서](https://kubernetes.io/docs/)
- [K3s 문서](https://docs.k3s.io/)

---

## 🤝 기여하기

새로운 예제를 제안하거나 개선사항이 있으시면:

1. [GitHub Issues](https://github.com/ScriptonBasestar/sb-kube-app-manager/issues)에 제안해주세요
2. Pull Request를 보내주세요

### 예제 작성 가이드라인

- ✅ README.md 포함 (목적, 사용법, 주의사항)
- ✅ 실행 가능한 완전한 설정 파일
- ✅ 명확한 주석 (특히 중요한 설정)
- ✅ 프로덕션 체크리스트 포함
- ✅ 테스트 완료 (Kind/k3s)

---

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](../LICENSE) 파일을 참조하세요.

---

**Happy deploying with SBKube! 🚀**

*k3s 환경에 특화된 Kubernetes 배포 자동화 도구*
