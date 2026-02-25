# Advanced Feature: Helm Customization

Helm 차트의 고급 커스터마이징 기능 (set_values, release_name 등)을 시연하는 예제입니다.

## 📋 개요

**카테고리**: Advanced Features

**학습 목표**:
- `set_values`로 CLI 값 오버라이드
- `release_name`으로 릴리스 이름 커스터마이징
- Values 파일 병합 우선순위 이해
- 여러 인스턴스 배포 (같은 차트, 다른 릴리스)

## 🎯 사용 사례

### 1. CLI 값 오버라이드

Values 파일을 수정하지 않고 특정 값만 변경:
- 환경별 이미지 태그
- 동적으로 변경되는 설정
- CI/CD 파이프라인에서 주입

### 2. 릴리스 이름 관리

동일한 차트를 여러 번 배포:
- 개발/스테이징/프로덕션 분리
- 멀티테넌시 (고객별 인스턴스)
- A/B 테스트 (블루/그린 배포)

### 3. 복잡한 Values 병합

여러 Values 파일 + set_values 조합:
- 공통 설정 (base-values.yaml)
- 환경별 설정 (prod-values.yaml)
- 동적 오버라이드 (set_values)

## 🚀 빠른 시작

### 1. 기본 예제 배포

```bash
sbkube apply -f sbkube.yaml \
  --app-dir examples/advanced-features/03-helm-customization \
  --namespace helm-custom
```

### 2. 배포 확인

```bash
# 3개의 Grafana 인스턴스 확인
kubectl get pods -n helm-custom

# Helm 릴리스 이름 확인
helm list -n helm-custom

# 출력:
# grafana-dev       default   1  deployed  grafana-6.x.x  9.x.x
# grafana-staging   default   1  deployed  grafana-6.x.x  9.x.x
# grafana-prod      default   1  deployed  grafana-6.x.x  9.x.x
```

### 3. 설정 확인

```bash
# Dev Grafana (standalone)
kubectl get pods -n helm-custom -l app.kubernetes.io/instance=grafana-dev

# Prod Grafana (HA mode)
kubectl get pods -n helm-custom -l app.kubernetes.io/instance=grafana-prod
```

## 📖 설정 파일 설명

### sbkube.yaml

```yaml
namespace: helm-custom

apps:
  # 1. Release Name + Set Values (Dev)
  grafana-dev:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    release_name: grafana-dev  # Helm 릴리스 이름 커스터마이징
    values:
      - values/base-values.yaml
      - values/dev-values.yaml
    set_values:
      # CLI 값 오버라이드 (values 파일보다 우선)
      image.tag: "9.5.0"
      resources.limits.memory: "256Mi"

  # 2. 다른 릴리스 (Staging)
  grafana-staging:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    release_name: grafana-staging
    values:
      - values/base-values.yaml
      - values/staging-values.yaml
    set_values:
      image.tag: "9.5.0"
      replicas: "2"

  # 3. Production 릴리스 (HA Mode)
  grafana-prod:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    release_name: grafana-prod
    values:
      - values/base-values.yaml
      - values/prod-values.yaml
    set_values:
      image.tag: "9.5.0"
      replicas: "3"
      persistence.enabled: "true"
```

### Values 병합 우선순위

```
기본 차트 values (낮음)
    ↓
base-values.yaml
    ↓
{env}-values.yaml (dev/staging/prod)
    ↓
set_values (가장 높음, 최우선)
```

## 🔧 주요 기능

### 1. release_name 커스터마이징

**기본 동작** (release_name 없음):
```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    # release_name 미지정 → 앱 이름(grafana) 사용
```

**커스터마이징**:
```yaml
apps:
  grafana-prod:
    type: helm
    chart: grafana/grafana
    release_name: my-custom-grafana-name  # Helm 릴리스 이름
```

**확인**:
```bash
helm list -n <namespace>
# NAME                      NAMESPACE  ...
# my-custom-grafana-name    default    ...
```

### 2. set_values 사용법

**기본 형식**:
```yaml
apps:
  my-app:
    type: helm
    chart: grafana/grafana
    set_values:
      key1: value1
      nested.key2: value2
      array[0]: item1
```

**Helm 명령어 변환**:
```bash
# SBKube가 내부적으로 실행:
helm install <release> <chart> \
  --set key1=value1 \
  --set nested.key2=value2 \
  --set array[0]=item1
```

**고급 사용**:
```yaml
set_values:
  # 문자열
  image.tag: "7.0.11"

  # 숫자
  replica.replicaCount: "3"

  # Boolean
  auth.enabled: "true"

  # 배열
  extraEnvVars[0].name: "LOG_LEVEL"
  extraEnvVars[0].value: "debug"

  # 중첩 객체
  resources.limits.memory: "512Mi"
  resources.limits.cpu: "500m"
```

### 3. 여러 Values 파일 병합

```yaml
apps:
  my-app:
    type: helm
    chart: my/chart
    values:
      - values/base.yaml        # 1순위 (낮음)
      - values/common.yaml      # 2순위
      - values/prod.yaml        # 3순위
    set_values:                 # 4순위 (가장 높음)
      image.tag: "v1.2.3"
```

**병합 예시**:

`base.yaml`:
```yaml
image:
  repository: nginx
  tag: "1.21"
replicas: 1
```

`prod.yaml`:
```yaml
replicas: 3  # base.yaml의 1을 오버라이드
resources:
  limits:
    memory: 512Mi
```

`set_values`:
```yaml
set_values:
  image.tag: "1.22"  # prod.yaml의 tag를 오버라이드
```

**최종 결과**:
```yaml
image:
  repository: nginx
  tag: "1.22"      # set_values로 오버라이드
replicas: 3        # prod.yaml로 오버라이드
resources:
  limits:
    memory: 512Mi  # prod.yaml에서 추가
```

## 🎓 학습 포인트

### 1. 언제 release_name을 사용하나?

**✅ 사용해야 할 때**:
- 동일 차트를 여러 번 배포
- 환경별 릴리스 분리 (dev/staging/prod)
- 멀티테넌트 배포 (고객별 인스턴스)
- Helm 릴리스 이름과 앱 이름을 다르게

**❌ 사용하지 않아도 될 때**:
- 단일 인스턴스 배포
- 앱 이름 = 릴리스 이름이어도 무방

### 2. 언제 set_values를 사용하나?

**✅ 사용해야 할 때**:
- CI/CD에서 동적 값 주입 (이미지 태그, 빌드 번호)
- 환경 변수로 전달받은 값
- Values 파일을 수정하지 않고 특정 값만 변경
- 빠른 테스트 및 디버깅

**❌ Values 파일을 사용해야 할 때**:
- 정적이고 반복적인 설정
- 복잡한 구조화된 데이터
- 버전 관리가 필요한 설정

### 3. Values 우선순위 이해

```
낮음 → 높음
───────────────────────────────────────
차트 기본값 < values[0] < values[1] < ... < set_values
```

**실전 패턴**:
```yaml
values:
  - base-values.yaml       # 모든 환경 공통
  - secrets-values.yaml    # 시크릿 (Sealed Secrets)
  - prod-values.yaml       # 환경별 설정
set_values:
  image.tag: "${CI_COMMIT_SHA}"  # CI/CD 동적 주입
```

## 🧪 테스트 시나리오

### 시나리오 1: 릴리스 이름 확인

```bash
# 배포
sbkube apply -f sbkube.yaml --namespace helm-custom

# Helm 릴리스 확인
helm list -n helm-custom

# 예상 출력:
# NAME              NAMESPACE    REVISION  ...
# grafana-dev       helm-custom  1         ...
# grafana-staging   helm-custom  1         ...
# grafana-prod      helm-custom  1         ...
```

### 시나리오 2: Set Values 적용 확인

```bash
# grafana-dev의 메모리 제한 확인 (set_values로 256Mi 설정)
kubectl get pod -n helm-custom -l app.kubernetes.io/instance=grafana-dev -o yaml | grep -A 2 "limits:"

# 예상 출력:
#   limits:
#     memory: 256Mi
```

### 시나리오 3: Values 병합 확인

```bash
# grafana-prod의 HA 모드 확인 (set_values로 활성화)
kubectl get pods -n helm-custom -l app.kubernetes.io/instance=grafana-prod

# 예상 출력: 3개의 Pod (replicas=3)
```

### 시나리오 4: 동적 값 변경

```yaml
# sbkube.yaml 수정
apps:
  grafana-dev:
    set_values:
      image.tag: "10.0.0"  # 버전 변경
```

```bash
# 재배포
sbkube apply -f sbkube.yaml --namespace helm-custom

# 이미지 태그 확인
kubectl get pod -n helm-custom -l app.kubernetes.io/instance=grafana-dev \
  -o jsonpath='{.items[0].spec.containers[0].image}'

# 예상 출력: grafana/grafana:10.0.0
```

## 🔍 트러블슈팅

### 문제 1: "릴리스 이름 충돌"

**증상**:
```
Error: cannot re-use a name that is still in use
```

**원인**: 동일한 네임스페이스에 같은 release_name

**해결**:
```yaml
# 각 앱마다 고유한 release_name 사용
apps:
  grafana-1:
    release_name: grafana-instance-1  # 고유

  grafana-2:
    release_name: grafana-instance-2  # 고유
```

### 문제 2: "set_values가 적용되지 않음"

**원인**: 잘못된 키 경로 또는 타입

**해결**:
```bash
# 차트의 기본 values 확인
helm show values grafana/grafana > default-values.yaml

# 올바른 키 경로 찾기
cat default-values.yaml | grep -A 5 "image:"
```

```yaml
# 올바른 형식
set_values:
  image.tag: "7.0.11"  # ✅ 문자열로
  replica.replicaCount: "3"  # ✅ 숫자도 문자열로
```

### 문제 3: "Values 파일 우선순위 혼란"

**원인**: 병합 순서 이해 부족

**테스트**:
```yaml
# 각 파일에 다른 값 설정하여 테스트
# base-values.yaml
replicas: 1

# prod-values.yaml
replicas: 3

# set_values
set_values:
  replica.replicaCount: "5"

# 최종 결과: 5 (set_values가 최우선)
```

### 문제 4: "특수 문자가 포함된 값"

**원인**: YAML 파싱 오류

**해결**:
```yaml
# 따옴표로 감싸기
set_values:
  password: "my-p@ssw0rd!"  # ✅ 특수문자는 따옴표
  image.tag: "v1.2.3"       # ✅ 버전도 문자열로
  tolerations[0].key: "node.kubernetes.io/not-ready"  # ✅ 슬래시 포함
```

## 💡 실전 패턴

### 패턴 1: 환경별 배포

```yaml
namespace: production

apps:
  # Dev 환경
  app-dev:
    type: helm
    chart: my/app
    release_name: app-dev
    values:
      - values/base.yaml
      - values/dev.yaml
    set_values:
      env: "development"
      replicas: "1"

  # Staging 환경
  app-staging:
    type: helm
    chart: my/app
    release_name: app-staging
    values:
      - values/base.yaml
      - values/staging.yaml
    set_values:
      env: "staging"
      replicas: "2"

  # Production 환경
  app-prod:
    type: helm
    chart: my/app
    release_name: app-prod
    values:
      - values/base.yaml
      - values/prod.yaml
    set_values:
      env: "production"
      replicas: "5"
```

### 패턴 2: CI/CD 통합

```yaml
# GitLab CI/CD 예시
apps:
  backend:
    type: helm
    chart: my/backend
    release_name: backend-${CI_ENVIRONMENT_NAME}
    values:
      - values/base.yaml
    set_values:
      # 동적 값 (CI/CD 변수)
      image.tag: "${CI_COMMIT_SHA}"
      ingress.hosts[0].host: "${APP_DOMAIN}"
      env.BUILD_NUMBER: "${CI_PIPELINE_ID}"
```

### 패턴 3: 멀티테넌트

```yaml
# 고객별 인스턴스 배포
apps:
  customer-a:
    type: helm
    chart: saas/app
    release_name: app-customer-a
    values:
      - values/saas-base.yaml
    set_values:
      tenant.id: "customer-a"
      tenant.name: "Customer A Inc."
      resources.limits.memory: "512Mi"

  customer-b:
    type: helm
    chart: saas/app
    release_name: app-customer-b
    values:
      - values/saas-base.yaml
    set_values:
      tenant.id: "customer-b"
      tenant.name: "Customer B Corp."
      resources.limits.memory: "1Gi"  # Premium 고객
```

### 패턴 4: A/B 테스트

```yaml
apps:
  # 기존 버전 (Blue)
  app-blue:
    type: helm
    chart: my/app
    release_name: app-v1
    values:
      - values/prod.yaml
    set_values:
      image.tag: "v1.5.0"
      service.name: "app-blue"

  # 신규 버전 (Green)
  app-green:
    type: helm
    chart: my/app
    release_name: app-v2
    values:
      - values/prod.yaml
    set_values:
      image.tag: "v2.0.0"
      service.name: "app-green"
```

## 📚 추가 학습 자료

### SBKube 관련 문서
- [Application Types - Helm](../../docs/02-features/application-types.md#1-helm---helm-차트)
- [Configuration Schema](../../docs/03-configuration/config-schema.md)

### Helm 공식 문서
- [Helm Values Files](https://helm.sh/docs/chart_template_guide/values_files/)
- [Helm --set Usage](https://helm.sh/docs/intro/using_helm/#customizing-the-chart-before-installing)

### 관련 예제
- [Helm App Type](../../app-types/01-helm/) - 기본 Helm 사용법
- [Enabled Flag](../01-enabled-flag/) - 조건부 배포

## 🎯 다음 단계

1. **CI/CD 통합**: 파이프라인에서 동적 값 주입
2. **Secrets 관리**: Sealed Secrets + set_values 조합
3. **멀티 클러스터**: 클러스터별 릴리스 관리

## 🧹 정리

```bash
# 네임스페이스 삭제 (모든 릴리스 함께 삭제됨)
kubectl delete namespace helm-custom

# 또는 개별 릴리스 삭제
helm uninstall grafana-dev grafana-staging grafana-prod -n helm-custom
```

---

**Helm의 모든 커스터마이징 옵션을 활용하세요! ⚙️**
