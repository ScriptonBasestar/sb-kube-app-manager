# Advanced Feature: enabled Flag

조건부 배포를 위한 `enabled` 플래그 사용 예제입니다.

## 사용 시나리오

- 환경별 선택적 배포 (dev/staging/prod)
- 옵션 기능 활성화/비활성화
- A/B 테스트
- Feature Toggle

## 기본 사용법

```yaml
namespace: advanced-demo

apps:
  # 항상 배포
  redis:
    type: helm
    chart: bitnami/redis
    enabled: true  # 기본값

  # 비활성화 (배포하지 않음)
  memcached:
    type: helm
    chart: bitnami/memcached
    enabled: false

  # enabled 생략 (기본값은 true)
  postgresql:
    type: helm
    chart: bitnami/postgresql
```

## 실전 예제

### 환경별 배포

**개발 환경** (dev-config.yaml):
```yaml
namespace: dev

apps:
  app:
    type: helm
    chart: my/app
    enabled: true

  debug-tools:
    type: helm
    chart: my/debug-tools
    enabled: true  # 개발 환경에서만 활성화

  monitoring:
    type: helm
    chart: prometheus-community/prometheus
    enabled: false  # 개발 환경에서는 비활성화
```

**프로덕션 환경** (prod-config.yaml):
```yaml
namespace: prod

apps:
  app:
    type: helm
    chart: my/app
    enabled: true

  debug-tools:
    type: helm
    chart: my/debug-tools
    enabled: false  # 프로덕션에서는 비활성화

  monitoring:
    type: helm
    chart: prometheus-community/prometheus
    enabled: true  # 프로덕션에서만 활성화
```

### Feature Toggle

```yaml
namespace: app

apps:
  # 메인 애플리케이션
  main-app:
    type: helm
    chart: my/app
    enabled: true

  # 실험적 기능 (Feature Flag)
  experimental-feature-a:
    type: helm
    chart: my/feature-a
    enabled: false  # 실험 중

  experimental-feature-b:
    type: helm
    chart: my/feature-b
    enabled: true   # 베타 테스트 중

  # 레거시 기능 (단계적 폐기)
  legacy-service:
    type: helm
    chart: my/legacy
    enabled: false  # 더 이상 사용 안함
```

## 배포

### 기본 배포 (enabled: true만)
```bash
sbkube apply --app-dir .
```

### 모든 앱 강제 배포 (enabled 무시)
현재 SBKube는 `enabled: false` 앱을 자동으로 건너뜁니다.
강제로 배포하려면 설정을 변경해야 합니다.

### 특정 앱만 배포
```bash
# enabled 여부와 관계없이 특정 앱만
sbkube apply --app-dir . --apps redis
```

## depends_on과 함께 사용

```yaml
apps:
  database:
    type: helm
    chart: bitnami/postgresql
    enabled: true

  cache:
    type: helm
    chart: bitnami/redis
    enabled: true

  # database와 cache에 의존하지만 비활성화
  app:
    type: helm
    chart: my/app
    enabled: false
    depends_on:
      - database
      - cache

  # app이 비활성화되어 있어도 독립적으로 배포 가능
  monitoring:
    type: helm
    chart: prometheus-community/prometheus
    enabled: true
```

**동작**:
- `database`와 `cache`는 배포됨
- `app`은 `enabled: false`이므로 건너뜀
- `monitoring`은 독립적이므로 배포됨

## 실전 팁

### 1. 환경 변수로 제어 (템플릿 사용 시)

현재 SBKube는 환경 변수를 직접 지원하지 않지만,
여러 설정 파일을 사용할 수 있습니다:

```bash
# 개발 환경
cp config.dev.yaml config.yaml
sbkube apply --app-dir .

# 프로덕션 환경
cp config.prod.yaml config.yaml
sbkube apply --app-dir .
```

### 2. 주석 활용

```yaml
apps:
  # 🚧 TODO: 프로덕션 배포 전 활성화 필요
  new-feature:
    type: helm
    chart: my/new-feature
    enabled: false

  # ⚠️ WARNING: 리소스 사용량 높음, 필요시에만 활성화
  heavy-analytics:
    type: helm
    chart: my/analytics
    enabled: false
```

### 3. 그룹화

```yaml
apps:
  # === 핵심 서비스 ===
  api:
    type: helm
    chart: my/api
    enabled: true

  database:
    type: helm
    chart: bitnami/postgresql
    enabled: true

  # === 선택적 기능 ===
  metrics:
    type: helm
    chart: prometheus-community/prometheus
    enabled: false

  logging:
    type: helm
    chart: grafana/loki
    enabled: false
```

## 정리

```bash
sbkube delete --app-dir .
```

## 주의사항

1. **enabled: false는 완전히 건너뜀**
   - prepare, build, template, deploy 모든 단계에서 무시됨

2. **depends_on과 독립적**
   - A가 B에 의존하고 A가 enabled: false이면 B는 여전히 배포될 수 있음

3. **상태 관리**
   - `sbkube state list`에는 enabled: true 앱만 표시됨

## 관련 예제

- [Advanced Feature: Complex Dependencies](../02-complex-dependencies/)
- [Advanced Feature: Set Values](../03-set-values/)
