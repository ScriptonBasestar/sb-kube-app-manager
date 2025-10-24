# App Type: Kustomize

Kustomize를 사용하여 환경별로 다른 설정을 적용하는 예제입니다.

## 📋 개요

**App Type**: `kustomize`

**학습 목표**:
- Kustomize base/overlay 패턴 이해
- SBKube에서 Kustomize 사용법
- 환경별 설정 관리 (dev/prod)

## 📁 디렉토리 구조

```
07-kustomize/
├── config.yaml           # SBKube 설정
├── base/                 # 기본 매니페스트
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   └── service.yaml
└── overlays/             # 환경별 오버레이
    ├── dev/
    │   ├── kustomization.yaml
    │   └── replica-patch.yaml
    └── prod/
        ├── kustomization.yaml
        └── replica-patch.yaml
```

## 🎯 사용 사례

### 1. 환경별 설정 관리
- **Dev**: 낮은 리소스, 1개 replicas
- **Prod**: 높은 리소스, 3개 replicas

### 2. Kustomize 장점
- YAML 템플릿 없이 base 재사용
- 환경별 패치 적용
- 네이티브 Kubernetes 도구

## 🚀 빠른 시작

### 1. Dev 환경 배포

```bash
sbkube apply --app-dir examples/app-types/07-kustomize --namespace kustomize-dev
```

### 2. Prod 환경 배포

```bash
# config.yaml에서 overlay_path를 'overlays/prod'로 변경 후
sbkube apply --app-dir examples/app-types/07-kustomize --namespace kustomize-prod
```

### 3. 배포 확인

```bash
# Dev 환경
kubectl get pods -n kustomize-dev
kubectl get svc -n kustomize-dev

# Prod 환경
kubectl get pods -n kustomize-prod
kubectl get svc -n kustomize-prod
```

## 📖 설정 파일 설명

### config.yaml

```yaml
namespace: kustomize-dev

apps:
  nginx-app:
    type: kustomize
    overlay_path: overlays/dev  # 또는 overlays/prod
    build_options:
      enable_alpha_plugins: false
```

### base/kustomization.yaml

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml

commonLabels:
  app: nginx
  managed-by: sbkube
```

### overlays/dev/kustomization.yaml

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

patchesStrategicMerge:
  - replica-patch.yaml

namespace: kustomize-dev
```

### overlays/prod/kustomization.yaml

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

patchesStrategicMerge:
  - replica-patch.yaml

namespace: kustomize-prod
```

## 🔧 주요 기능

### 1. Overlay Path 지정

```yaml
apps:
  my-app:
    type: kustomize
    overlay_path: overlays/prod  # 오버레이 경로
```

### 2. Build Options

```yaml
apps:
  my-app:
    type: kustomize
    overlay_path: overlays/dev
    build_options:
      enable_alpha_plugins: false  # 알파 플러그인 활성화
      enable_helm: false            # Helm 차트 지원
```

### 3. 환경별 패치

**Dev 환경** (`overlays/dev/replica-patch.yaml`):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 1  # Dev: 1개
```

**Prod 환경** (`overlays/prod/replica-patch.yaml`):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 3  # Prod: 3개
```

## 🎓 학습 포인트

### 1. Base vs Overlay

- **Base**: 모든 환경에서 공통으로 사용하는 기본 매니페스트
- **Overlay**: 환경별로 다른 설정 (패치 적용)

### 2. Kustomization 파일

```yaml
# 리소스 포함
resources:
  - deployment.yaml

# 공통 라벨 추가
commonLabels:
  app: myapp

# 패치 적용
patchesStrategicMerge:
  - patch.yaml
```

### 3. SBKube 워크플로우

```
kustomize build overlays/dev → kubectl apply
```

SBKube가 자동으로 처리합니다.

## 🧪 테스트 시나리오

### 시나리오 1: Dev 환경 배포

```bash
# Dev 환경 배포
sbkube apply --app-dir . --namespace kustomize-dev

# 확인 (replicas: 1)
kubectl get pods -n kustomize-dev
```

### 시나리오 2: Prod 환경 배포

```bash
# config.yaml 수정: overlay_path: overlays/prod
# Prod 환경 배포
sbkube apply --app-dir . --namespace kustomize-prod

# 확인 (replicas: 3)
kubectl get pods -n kustomize-prod
```

### 시나리오 3: 템플릿만 렌더링

```bash
sbkube template --app-dir . --output-dir /tmp/kustomize-rendered

# 렌더링 결과 확인
cat /tmp/kustomize-rendered/nginx-app.yaml
```

## 🔍 트러블슈팅

### 문제 1: "Error: accumulating resources"

**원인**: kustomization.yaml 경로 오류

**해결**:
```bash
# base/kustomization.yaml 확인
cat base/kustomization.yaml

# overlay_path 확인
grep overlay_path config.yaml
```

### 문제 2: Patch가 적용되지 않음

**원인**: 리소스 이름 불일치

**해결**:
```yaml
# deployment.yaml의 name과 patch의 name이 일치해야 함
metadata:
  name: nginx  # 두 파일에서 동일해야 함
```

### 문제 3: Namespace 충돌

**원인**: overlay와 config.yaml의 namespace 불일치

**해결**:
```yaml
# config.yaml
namespace: kustomize-dev

# overlays/dev/kustomization.yaml
namespace: kustomize-dev  # 일치시키기
```

## 📚 추가 학습 자료

### Kustomize 공식 문서
- [Kustomize 가이드](https://kustomize.io/)
- [Kubernetes Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)

### SBKube 관련 문서
- [Application Types](../../docs/02-features/application-types.md)
- [Configuration Schema](../../docs/03-configuration/config-schema.md)

## 🎯 다음 단계

1. **다른 패치 타입 시도**: JSON 6902 패치
2. **ConfigMap 생성**: Kustomize로 ConfigMap 자동 생성
3. **Secret 관리**: Kustomize Secret Generator 사용

## 💡 프로덕션 팁

### 1. Git 기반 관리

```bash
git/
├── base/
└── overlays/
    ├── dev/
    ├── staging/
    └── prod/
```

### 2. CI/CD 통합

```yaml
# GitLab CI 예시
deploy:dev:
  script:
    - sbkube apply --app-dir kustomize --namespace dev
  only:
    - develop

deploy:prod:
  script:
    - sbkube apply --app-dir kustomize --namespace prod
  only:
    - master
```

### 3. 버전 관리

```yaml
# kustomization.yaml
images:
  - name: nginx
    newTag: "1.21.6"  # 버전 명시
```

## 🧹 정리

```bash
# Dev 환경 삭제
kubectl delete namespace kustomize-dev

# Prod 환경 삭제
kubectl delete namespace kustomize-prod
```

---

**Kustomize로 환경별 설정을 깔끔하게 관리하세요! 🎨**
