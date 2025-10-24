# App Type: Helm

Helm 차트를 사용한 배포 예제입니다.

## 지원 형식

1. **원격 Helm 차트** - Helm 리포지토리에서 차트 다운로드
2. **로컬 Helm 차트** - 로컬 디렉토리의 차트 사용

## 예제 1: 원격 Helm 차트 (Bitnami Redis)

### config.yaml
```yaml
namespace: helm-demo

apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: "17.13.2"
    values:
      - redis-values.yaml
```

### sources.yaml
```yaml
helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami
```

### 실행
```bash
sbkube apply --app-dir .
```

## 예제 2: 로컬 Helm 차트

### 디렉토리 구조
```
.
├── config.yaml
├── charts/
│   └── my-app/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           └── service.yaml
└── values/
    └── my-app-values.yaml
```

### config.yaml
```yaml
namespace: helm-demo

apps:
  my-app:
    type: helm
    chart: ./charts/my-app
    values:
      - values/my-app-values.yaml
```

### 실행
```bash
sbkube apply --app-dir .
```

## 예제 3: 차트 커스터마이징 (Overrides & Removes)

### config.yaml
```yaml
namespace: helm-demo

apps:
  postgresql:
    type: helm
    chart: bitnami/postgresql
    version: "12.12.10"
    values:
      - postgresql-values.yaml

    # 차트 파일 교체
    overrides:
      templates/secrets.yaml: custom-secrets.yaml
      templates/configmap.yaml: custom-configmap.yaml

    # 차트 파일 삭제
    removes:
      - templates/serviceaccount.yaml
      - templates/tests/
```

### 사용 시나리오

**Overrides**:
- 보안 정책에 맞게 Secret 템플릿 수정
- 조직 표준 ConfigMap 적용
- Ingress 설정 커스터마이징

**Removes**:
- 불필요한 ServiceAccount 제거
- 테스트 리소스 제거
- 사용하지 않는 기능 제거

## 배포 확인

```bash
# Helm 릴리스 확인
helm list -n helm-demo

# Pod 상태 확인
kubectl get pods -n helm-demo

# 전체 리소스 확인
kubectl get all -n helm-demo
```

## 정리

```bash
sbkube delete --app-dir .
```
