# Kustomize Example - 환경별 설정 관리

SBKube의 **kustomize 타입**을 사용하여 환경별 설정을 관리하는 예제입니다.

## 📋 목차

- [개요](#-개요)
- [kustomize 타입이란?](#-kustomize-타입이란)
- [디렉토리 구조](#-디렉토리-구조)
- [설정 상세](#-설정-상세)
- [배포 방법](#-배포-방법)
- [Kustomize vs Helm](#-kustomize-vs-helm)
- [고급 사용법](#-고급-사용법)

---

## 🎯 개요

이 예제는 **Kustomize**를 사용하여 동일한 애플리케이션을 개발/프로덕션 환경에 다른 설정으로 배포하는 방법을 보여줍니다.

**배포 환경**:
- **Development**: 2 replicas, debug 로그, 낮은 리소스
- **Production**: 5 replicas, info 로그, 높은 리소스

---

## 🔧 kustomize 타입이란?

**kustomize 타입**은 Kustomize를 사용하여 Kubernetes 매니페스트를 환경별로 커스터마이징하는 애플리케이션 타입입니다.

### 특징

| 특징 | 설명 |
|-----|------|
| **베이스 + 오버레이** | 공통 설정(base) + 환경별 변경(overlay) |
| **템플릿 없음** | YAML 패치 기반 (템플릿 엔진 불필요) |
| **선언적** | kustomization.yaml로 변경사항 선언 |
| **네이티브 지원** | kubectl kustomize 내장 |

### Kustomize 핵심 개념

```
base/                    # 공통 베이스 설정
├── kustomization.yaml
├── deployment.yaml
└── service.yaml

overlays/dev/            # 개발 환경 오버레이
└── kustomization.yaml   # base 참조 + dev 커스터마이징

overlays/prod/           # 프로덕션 환경 오버레이
├── kustomization.yaml   # base 참조 + prod 커스터마이징
└── resources-patch.yaml # 추가 패치
```

---

## 📁 디렉토리 구조

```
kustomize-example/
├── config.yaml                      # SBKube 설정
├── base/                            # 공통 베이스
│   ├── kustomization.yaml          # 베이스 Kustomize 설정
│   ├── deployment.yaml             # 공통 Deployment
│   └── service.yaml                # 공통 Service
├── overlays/
│   ├── dev/                        # 개발 환경
│   │   └── kustomization.yaml     # Dev 커스터마이징
│   └── prod/                       # 프로덕션 환경
│       ├── kustomization.yaml     # Prod 커스터마이징
│       └── resources-patch.yaml   # 리소스 패치
└── README.md
```

---

## 📝 설정 상세

### config.yaml

```yaml
namespace: kustomize-demo

apps:
  # Development 환경
  myapp-dev:
    type: kustomize
    path: overlays/dev      # Dev 오버레이 경로
    enabled: true

  # Production 환경 (기본 비활성화)
  myapp-prod:
    type: kustomize
    path: overlays/prod     # Prod 오버레이 경로
    enabled: false
```

**주요 필드**:
- `type`: `kustomize` 고정
- `path`: Kustomize 디렉토리 경로 (kustomization.yaml 포함)
- `enabled`: 활성화 여부

### base/kustomization.yaml

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml

commonLabels:
  app: myapp
```

**역할**: 모든 환경의 공통 설정

### base/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 1              # 기본값 (오버레이에서 변경)
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: nginx:1.21  # 기본 이미지 (오버레이에서 변경)
        ports:
        - containerPort: 80
        resources:
          limits:
            cpu: 100m
            memory: 128Mi
```

### base/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 80
  selector:
    app: myapp
```

### overlays/dev/kustomization.yaml

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: kustomize-demo

bases:
  - ../../base              # 베이스 참조

namePrefix: dev-            # 이름에 "dev-" 접두사 추가

commonLabels:
  environment: development  # 환경 레이블 추가

replicas:
  - name: myapp
    count: 2                # Dev: 2 replicas

images:
  - name: nginx
    newTag: 1.21            # Dev: nginx:1.21

configMapGenerator:
  - name: myapp-config
    literals:
      - ENV=development
      - LOG_LEVEL=debug     # Dev: debug 로그
```

**결과**:
- Deployment 이름: `dev-myapp`
- Replicas: 2
- Image: `nginx:1.21`
- ConfigMap: `myapp-config` (ENV=development, LOG_LEVEL=debug)

### overlays/prod/kustomization.yaml

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: kustomize-demo

bases:
  - ../../base              # 베이스 참조

namePrefix: prod-           # 이름에 "prod-" 접두사 추가

commonLabels:
  environment: production   # 환경 레이블 추가

replicas:
  - name: myapp
    count: 5                # Prod: 5 replicas

images:
  - name: nginx
    newTag: 1.25            # Prod: nginx:1.25 (최신)

configMapGenerator:
  - name: myapp-config
    literals:
      - ENV=production
      - LOG_LEVEL=info      # Prod: info 로그

patchesStrategicMerge:
  - resources-patch.yaml    # 추가 패치
```

### overlays/prod/resources-patch.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: myapp
        resources:
          limits:
            cpu: 500m       # Prod: 더 높은 CPU
            memory: 512Mi   # Prod: 더 높은 메모리
          requests:
            cpu: 250m
            memory: 256Mi
```

**결과**:
- Deployment 이름: `prod-myapp`
- Replicas: 5
- Image: `nginx:1.25`
- Resources: CPU 500m, Memory 512Mi
- ConfigMap: `myapp-config` (ENV=production, LOG_LEVEL=info)

---

## 🚀 배포 방법

### Development 환경 배포

```bash
cd examples/kustomize-example

# Dev 환경만 배포
sbkube apply
```

**실행 과정**:
```
✅ [prepare] Kustomize 빌드 (overlays/dev)
✅ [deploy] Dev 환경 배포 (kustomize-demo 네임스페이스)
```

**결과**:
```
NAME                       READY   STATUS    RESTARTS   AGE
dev-myapp-xxxx-yyyy        1/1     Running   0          1m
dev-myapp-xxxx-zzzz        1/1     Running   0          1m
```

### Production 환경 배포

```bash
# 1. config.yaml 수정
# myapp-dev: enabled: false
# myapp-prod: enabled: true

# 2. Prod 환경 배포
sbkube apply
```

**결과**:
```
NAME                       READY   STATUS    RESTARTS   AGE
prod-myapp-xxxx-aaaa       1/1     Running   0          1m
prod-myapp-xxxx-bbbb       1/1     Running   0          1m
prod-myapp-xxxx-cccc       1/1     Running   0          1m
prod-myapp-xxxx-dddd       1/1     Running   0          1m
prod-myapp-xxxx-eeee       1/1     Running   0          1m
```

### 로컬 Kustomize 빌드 확인

```bash
# Dev 환경 렌더링 결과 확인
kubectl kustomize overlays/dev/

# Prod 환경 렌더링 결과 확인
kubectl kustomize overlays/prod/

# 또는 SBKube template 사용
sbkube template --output-dir /tmp/rendered
cat /tmp/rendered/myapp-dev.yaml
```

---

## 🔍 배포 확인

### Dev 환경 확인

```bash
# Deployment 확인
kubectl get deployment -n kustomize-demo -l environment=development

# Pod 확인
kubectl get pods -n kustomize-demo -l environment=development

# ConfigMap 확인
kubectl get configmap -n kustomize-demo -l environment=development
kubectl describe configmap myapp-config-<hash> -n kustomize-demo
```

**예상 출력**:
```
Data
====
ENV:
----
development
LOG_LEVEL:
----
debug
```

### Prod 환경 확인

```bash
# Deployment 확인
kubectl get deployment -n kustomize-demo -l environment=production

# Pod 리소스 확인
kubectl describe pod -n kustomize-demo -l environment=production | grep -A 5 "Limits:"
```

**예상 출력**:
```
Limits:
  cpu:     500m
  memory:  512Mi
Requests:
  cpu:     250m
  memory:  256Mi
```

---

## 🆚 Kustomize vs Helm

### 비교표

| 비교 항목 | Kustomize | Helm |
|---------|----------|------|
| **접근 방식** | 패치 기반 (베이스 + 오버레이) | 템플릿 기반 (Go template) |
| **설정 관리** | YAML 패치 | values.yaml |
| **학습 곡선** | ⭐⭐ 낮음 | ⭐⭐⭐ 중간 |
| **환경 분리** | ✅ 매우 우수 (오버레이) | ⚠️ values 파일 분리 필요 |
| **패키징** | ❌ 없음 (Git 기반) | ✅ .tgz 차트 |
| **릴리스 관리** | ❌ 없음 | ✅ Helm 릴리스 |
| **롤백** | ❌ kubectl 수동 | ✅ helm rollback |
| **kubectl 통합** | ✅ 내장 (kubectl kustomize) | ❌ 별도 설치 필요 |
| **용도** | 간단한 앱, 환경별 설정 | 복잡한 앱, 버전 관리 |

### 언제 사용할까?

**Kustomize 권장**:
- ✅ 환경별 설정이 중요한 경우 (dev/staging/prod)
- ✅ 템플릿 없이 순수 YAML로 관리하고 싶은 경우
- ✅ GitOps 워크플로우 (ArgoCD, Flux)
- ✅ 간단한 애플리케이션

**Helm 권장**:
- ✅ 복잡한 애플리케이션 (의존성 많음)
- ✅ 버전 관리 및 롤백이 중요한 경우
- ✅ 패키징 및 배포 자동화
- ✅ 써드파티 애플리케이션 (Bitnami, 등)

**둘 다 사용** (Best Practice):
```yaml
# Helm으로 써드파티 앱 배포
apps:
  postgresql:
    type: helm
    chart: bitnami/postgresql

# Kustomize로 자체 앱 배포
  myapp-dev:
    type: kustomize
    path: overlays/dev
```

---

## 🛠️ 고급 사용법

### 1. 여러 환경 추가

```bash
# Staging 환경 추가
mkdir -p overlays/staging
```

**overlays/staging/kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: kustomize-demo

bases:
  - ../../base

namePrefix: staging-

commonLabels:
  environment: staging

replicas:
  - name: myapp
    count: 3

images:
  - name: nginx
    newTag: 1.23

configMapGenerator:
  - name: myapp-config
    literals:
      - ENV=staging
      - LOG_LEVEL=warn
```

**config.yaml**:
```yaml
apps:
  myapp-dev:
    type: kustomize
    path: overlays/dev

  myapp-staging:
    type: kustomize
    path: overlays/staging

  myapp-prod:
    type: kustomize
    path: overlays/prod
```

### 2. Secret 관리

**overlays/prod/secret.yaml**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: myapp-secret
type: Opaque
stringData:
  DATABASE_URL: postgresql://user:password@db:5432/myapp
  API_KEY: prod-api-key-xxxx
```

**overlays/prod/kustomization.yaml**:
```yaml
resources:
  - secret.yaml  # 추가

secretGenerator:
  - name: myapp-env
    envs:
      - .env.prod  # .env.prod 파일에서 Secret 생성
```

**⚠️ 주의**: Secret은 Git에 커밋하지 말 것! (`.gitignore` 추가)

### 3. 네임스페이스별 분리

```yaml
# config-dev.yaml
namespace: development

apps:
  myapp:
    type: kustomize
    path: overlays/dev

# config-prod.yaml
namespace: production

apps:
  myapp:
    type: kustomize
    path: overlays/prod
```

**배포**:
```bash
# Dev 네임스페이스
sbkube apply --config config-dev.yaml

# Prod 네임스페이스
sbkube apply --config config-prod.yaml
```

### 4. JSON Patch 사용

**overlays/prod/json-patch.yaml**:
```yaml
# patchesJson6902 사용 (더 세밀한 제어)
- target:
    group: apps
    version: v1
    kind: Deployment
    name: myapp
  patch: |-
    - op: replace
      path: /spec/template/spec/containers/0/image
      value: nginx:1.25
    - op: add
      path: /spec/template/spec/containers/0/env
      value:
        - name: CUSTOM_VAR
          value: custom-value
```

**overlays/prod/kustomization.yaml**:
```yaml
patchesJson6902:
  - path: json-patch.yaml
```

### 5. 여러 베이스 병합

```yaml
# overlays/prod/kustomization.yaml
bases:
  - ../../base              # 공통 베이스
  - ../../components/monitoring  # 모니터링 컴포넌트
  - ../../components/logging     # 로깅 컴포넌트
```

---

## 💡 실전 시나리오

### 시나리오 1: Blue-Green 배포

```yaml
# overlays/blue/kustomization.yaml
namePrefix: blue-
nameSuffix: -v1

# overlays/green/kustomization.yaml
namePrefix: green-
nameSuffix: -v2
images:
  - name: nginx
    newTag: 1.25  # 새 버전
```

**배포**:
```bash
# Blue 버전 유지하면서 Green 배포
sbkube apply --app myapp-blue
sbkube apply --app myapp-green

# 테스트 후 Blue 제거
sbkube delete --app myapp-blue
```

### 시나리오 2: GitOps (ArgoCD/Flux)

```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-dev
spec:
  source:
    repoURL: https://github.com/myorg/myrepo
    path: kustomize-example/overlays/dev
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: development
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

---

## ⚠️ 주의사항

### 1. kustomization.yaml 검증

```bash
# 문법 검증
kubectl kustomize overlays/dev/ > /dev/null
# 오류 없으면 정상
```

### 2. 베이스 경로 주의

```yaml
# ❌ 잘못된 경로
bases:
  - ../base  # 상대 경로가 잘못됨

# ✅ 올바른 경로
bases:
  - ../../base  # overlays/dev 기준
```

### 3. ConfigMap/Secret 해시

Kustomize는 ConfigMap/Secret 이름에 해시를 추가합니다:
```
myapp-config → myapp-config-k8tm4k9dk2
```

**이유**: 변경 감지 및 자동 Pod 재시작

### 4. namePrefix/nameSuffix 충돌

```yaml
# ❌ 중복 접두사
namePrefix: dev-
# base에도 namePrefix가 있으면 중복: dev-dev-myapp

# ✅ 베이스는 접두사 없이
```

---

## 🔄 삭제

```bash
# Dev 환경 삭제
sbkube delete --app myapp-dev --namespace kustomize-demo

# Prod 환경 삭제
sbkube delete --app myapp-prod --namespace kustomize-demo

# 전체 네임스페이스 삭제
kubectl delete namespace kustomize-demo
```

---

## 📚 참고 자료

- [SBKube 애플리케이션 타입 가이드](../../docs/02-features/application-types.md)
- [Kustomize 공식 문서](https://kustomize.io/)
- [Kubernetes Kustomize 가이드](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)
- [Kustomize vs Helm](https://blog.stack-labs.com/code/kustomize-101/)

---

## 🔗 관련 예제

- [deploy/yaml-example/](../deploy/yaml-example/) - 원시 YAML 배포
- [basic/](../basic/) - Helm 차트 배포
- [apply-workflow/](../apply-workflow/) - 통합 워크플로우

---

**💡 팁**: Kustomize는 환경별 설정 관리에 최적화되어 있습니다. Helm과 함께 사용하면 강력한 조합이 됩니다 (Helm으로 써드파티 앱, Kustomize로 자체 앱).
