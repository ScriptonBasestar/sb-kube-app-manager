# App Type: Helm

Helm 차트를 사용한 애플리케이션 배포 예제입니다.

이 예제는 다음 Helm 기능들을 시연합니다:
- 기본 차트 배포 (values 파일)
- `set_values` - CLI 값 오버라이드
- `release_name` - 커스텀 릴리스 이름
- 다중 values 파일 병합
- 앱별 namespace 오버라이드 (optional)

## 📋 config.yaml 주요 기능

### 1. 기본 Helm 배포 (values 파일)

```yaml
apps:
  grafana:
    type: helm
    repo: grafana  # sources.yaml의 Helm 리포지토리 이름
    chart: grafana
    version: "10.1.2"
    values:
      - grafana-values.yaml  # values 파일 지정
```

### 2. set_values - CLI 값 오버라이드 (v0.4.0+)

values 파일보다 우선순위가 높은 개별 값 설정:

```yaml
apps:
  grafana:
    type: helm
    repo: grafana
    chart: grafana
    version: "10.1.2"
    values:
      - grafana-values.yaml
    # values 파일보다 우선순위 높음
    set_values:
      - adminPassword=admin123
      - service.type=LoadBalancer
      - persistence.enabled=false
```

**사용 사례**:
- 비밀번호, API 키 등 민감한 정보 (CI/CD에서 주입)
- 환경별 동적 값 (service.type, ingress.enabled 등)
- values 파일 수정 없이 빠른 테스트

### 3. release_name - 커스텀 릴리스 이름 (v0.4.0+)

기본 릴리스 이름 대신 사용자 지정 이름 사용:

```yaml
apps:
  grafana:
    type: helm
    repo: grafana
    chart: grafana
    version: "10.1.2"
    # 기본값: {namespace}-{app_name} → helm-demo-grafana
    release_name: my-custom-grafana  # 커스텀 이름 지정
```

**사용 사례**:
- 레거시 시스템과 호환성 (기존 릴리스 이름 유지)
- 동일 네임스페이스에 여러 인스턴스 배포
- 짧고 읽기 쉬운 이름 사용

### 4. 다중 values 파일 병합 (v0.4.0+)

여러 values 파일을 순서대로 병합 (나중 파일이 앞 파일 덮어씀):

```yaml
apps:
  prometheus:
    type: helm
    repo: prometheus-community
    chart: prometheus
    version: "25.28.0"
    values:
      - prometheus-values-base.yaml      # 기본 설정
      - prometheus-values-override.yaml  # 환경별 오버라이드
```

**사용 사례**:
- 공통 설정 + 환경별 오버라이드 (base + dev/prd)
- 기능별 설정 분리 (auth + monitoring + logging)
- 팀별 설정 관리 (infra-team + app-team)

### 5. 앱별 namespace 오버라이드 (v0.4.0+)

글로벌 namespace를 무시하고 독립적으로 배포:

```yaml
namespace: helm-demo  # 글로벌 namespace

apps:
  prometheus:
    type: helm
    repo: prometheus-community
    chart: prometheus
    namespace: monitoring  # 이 앱만 monitoring namespace에 배포
```

**사용 사례**:
- 시스템 컴포넌트를 별도 namespace에 배포
- 멀티 테넌시 환경
- 네임스페이스별 RBAC 분리

### 6. 최소 설정 (values 파일 없이 set_values만)

```yaml
apps:
  redis:
    type: helm
    repo: bitnami
    chart: redis
    version: "19.0.0"
    # values 파일 없이 set_values만 사용
    set_values:
      - architecture=standalone
      - auth.enabled=false
```

## 🚀 실행 방법

### 1. 전체 워크플로우 (apply)

```bash
# 현재 디렉토리의 config.yaml을 사용하여 배포
sbkube apply --app-dir examples/app-types/01-helm

# 또는 특정 앱만 배포
sbkube apply --app-dir examples/app-types/01-helm --app grafana
```

### 2. 단계별 실행

```bash
# Step 1: Helm 차트 다운로드
sbkube prepare --app-dir examples/app-types/01-helm

# Step 2: 빌드 (chart_patches, overrides, removes 적용)
sbkube build --app-dir examples/app-types/01-helm

# Step 3: 템플릿 생성 (dry-run)
sbkube template --app-dir examples/app-types/01-helm --output-dir rendered

# Step 4: 배포
sbkube deploy --app-dir examples/app-types/01-helm
```

### 3. 환경별 배포 (sources.yaml 변경)

```bash
# 개발 환경
sbkube apply --app-dir examples/app-types/01-helm --source sources-dev.yaml

# 프로덕션 환경
sbkube apply --app-dir examples/app-types/01-helm --source sources-prd.yaml
```

## 🎯 우선순위 규칙

Helm 값 적용 순서 (낮음 → 높음):

1. 차트 기본값 (`Chart.yaml`의 values)
2. `values:` 첫 번째 파일
3. `values:` 두 번째 파일 (첫 번째 파일 덮어씀)
4. ...
5. `set_values:` (모든 values 파일 덮어씀) ← 최우선

**예시**:

```yaml
values:
  - base.yaml           # adminPassword: "default"
  - override.yaml       # adminPassword: "override123"
set_values:
  - adminPassword=cli456  # ← 최종 값: "cli456"
```

## 📁 파일 구조

```
app-types/01-helm/
├── config.yaml                         # SBKube 설정
├── sources.yaml                        # 기본 환경 (프로덕션)
├── sources-dev.yaml                    # 개발 환경
├── sources-prd.yaml                    # 프로덕션 환경
├── grafana-values.yaml                 # Grafana values
├── prometheus-values-base.yaml         # Prometheus 기본 설정
├── prometheus-values-override.yaml     # Prometheus 오버라이드
└── README.md                           # 이 문서
```

## 🔍 검증

### 배포 확인

```bash
# Helm 릴리스 확인
helm list -n helm-demo

# Pod 상태 확인
kubectl get pods -n helm-demo

# Grafana 릴리스 이름 확인
helm list -n helm-demo | grep grafana
# 출력: my-custom-grafana  (release_name 적용됨)
```

### 값 적용 확인

```bash
# 실제 적용된 values 확인
helm get values my-custom-grafana -n helm-demo

# set_values 적용 확인
kubectl get svc -n helm-demo my-custom-grafana -o yaml | grep type
# 출력: type: LoadBalancer  (set_values로 오버라이드됨)
```

## 💡 Tips

### 1. values 파일 vs set_values

**values 파일 사용**:
- 복잡한 구조 (nested objects)
- 버전 관리 필요
- 팀 공유 설정

**set_values 사용**:
- 간단한 단일 값
- 동적 값 (CI/CD에서 주입)
- 빠른 테스트/디버깅

### 2. 다중 values 파일 전략

```yaml
values:
  - values-common.yaml      # 모든 환경 공통
  - values-${ENV}.yaml      # 환경별 (dev/stg/prd)
  - values-${REGION}.yaml   # 리전별 (us-east-1, ap-northeast-2)
```

### 3. 버전 관리

```yaml
# 권장: 정확한 버전 지정
version: "10.1.2"

# 비권장: 범위 지정 (재현성 낮음)
# version: "~10.1.0"
# version: "^10.0.0"
```

## 📚 관련 문서

- [SBKube Commands](../../02-features/commands.md)
- [Helm Customization](../../advanced-features/03-helm-customization/)
- [Override with Files](../../override-with-files/)
- [Multi-Namespace](../../advanced-features/04-multi-namespace/)

## 🐛 Troubleshooting

### helm repo not found

**증상**: `Error: repo "grafana" not found`

**해결**:
```bash
# sources.yaml에 리포지토리 추가 확인
yq '.helm_repos' sources.yaml

# prepare 단계 실행
sbkube prepare --app-dir examples/app-types/01-helm
```

### release already exists

**증상**: `Error: release "grafana" already exists`

**해결**:
```bash
# 기존 릴리스 삭제
helm uninstall grafana -n helm-demo

# 또는 release_name 변경
# config.yaml:
#   release_name: grafana-v2
```

### values merge 이슈

**증상**: 나중 values 파일이 앞 파일을 완전히 덮어써버림

**해결**:
- Helm의 values 병합은 shallow merge입니다
- Deep merge가 필요한 경우 `set_values`로 개별 값 지정
- 또는 Kustomize patches 사용
