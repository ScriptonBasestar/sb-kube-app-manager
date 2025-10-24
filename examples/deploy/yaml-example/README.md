# YAML Type Example - 원시 매니페스트 배포

SBKube의 **yaml 타입**을 사용하여 원시 Kubernetes YAML 매니페스트를 배포하는 예제입니다.

## 📋 목차

- [개요](#-개요)
- [yaml 타입이란?](#-yaml-타입이란)
- [사용 시나리오](#-사용-시나리오)
- [설정 구조](#-설정-구조)
- [실행 방법](#-실행-방법)
- [고급 사용법](#-고급-사용법)

---

## 🎯 개요

이 예제는 다음을 시연합니다:

1. **Deployment 배포**: Nginx Deployment를 YAML로 배포
2. **Service 배포**: ClusterIP 타입 Service 생성
3. **다중 파일 관리**: 여러 YAML 파일을 하나의 앱으로 관리
4. **간단한 애플리케이션**: Helm 없이 순수 YAML로 배포

---

## 🔧 yaml 타입이란?

**yaml 타입**은 원시 Kubernetes YAML 매니페스트를 배포하는 애플리케이션 타입입니다.

### 특징

| 특징 | 설명 |
|-----|------|
| **정적 매니페스트** | 미리 작성된 YAML 파일 사용 |
| **템플릿팅 없음** | 변수 치환이나 템플릿 처리 없음 |
| **다중 파일 지원** | 여러 YAML 파일을 순차적으로 배포 |
| **kubectl apply** | 내부적으로 `kubectl apply -f` 실행 |

### 다른 타입과 비교

| 비교 항목 | yaml | helm | action | exec |
|---------|------|------|--------|------|
| **매니페스트 형식** | YAML | Helm 차트 | YAML | - |
| **템플릿팅** | ❌ | ✅ | ❌ | - |
| **변수 치환** | ❌ | ✅ (values.yaml) | ❌ | - |
| **릴리스 관리** | ❌ | ✅ | ❌ | - |
| **롤백 지원** | ❌ | ✅ | ❌ | - |
| **사용 난이도** | ⭐ (가장 쉬움) | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **적합한 용도** | 간단한 앱 | 복잡한 앱 | CRD/Operator | 훅/스크립트 |

---

## 🚀 사용 시나리오

### 시나리오 1: 간단한 웹 서버 배포

**배경**: Helm 차트 없이 간단한 Nginx를 배포하고 싶습니다.

**해결**:
```yaml
apps:
  nginx:
    type: yaml
    files:
      - manifests/nginx-deployment.yaml
      - manifests/nginx-service.yaml
```

**장점**:
- Helm 차트 불필요
- 매니페스트 구조 명확
- 수정이 직관적

### 시나리오 2: ConfigMap + Secret 배포

**배경**: 애플리케이션 설정과 민감 정보를 먼저 배포해야 합니다.

**해결**:
```yaml
apps:
  configs:
    type: yaml
    files:
      - manifests/configmap.yaml
      - manifests/secret.yaml

  app:
    type: yaml
    files:
      - manifests/deployment.yaml
      - manifests/service.yaml
    depends_on:
      - configs  # ConfigMap/Secret 이후 배포
```

### 시나리오 3: 정적 사이트 배포

**배경**: HTML/CSS/JS 정적 파일을 서빙하는 간단한 웹사이트를 배포합니다.

**해결**:
```yaml
apps:
  static-site:
    type: yaml
    files:
      - manifests/nginx-configmap.yaml    # HTML 파일을 ConfigMap으로
      - manifests/nginx-deployment.yaml   # Nginx Deployment
      - manifests/nginx-service.yaml      # Service
      - manifests/nginx-ingress.yaml      # Ingress
```

### 시나리오 4: 마이크로서비스 단일 배포

**배경**: 여러 마이크로서비스를 개별적으로 관리하고 싶습니다.

**해결**:
```yaml
apps:
  frontend:
    type: yaml
    files:
      - services/frontend/deployment.yaml
      - services/frontend/service.yaml

  backend:
    type: yaml
    files:
      - services/backend/deployment.yaml
      - services/backend/service.yaml

  database:
    type: yaml
    files:
      - services/database/statefulset.yaml
      - services/database/service.yaml
      - services/database/pvc.yaml
```

---

## 📝 설정 구조

### config.yaml

```yaml
namespace: example-yaml

apps:
  nginx:
    type: yaml                           # 애플리케이션 타입
    files:                               # YAML 파일 목록 (순차 배포)
      - manifests/nginx-deployment.yaml  # Deployment
      - manifests/nginx-service.yaml     # Service
    namespace: example-yaml              # Optional: 네임스페이스 오버라이드
```

### manifests/nginx-deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
```

### manifests/nginx-service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
```

### 주요 필드

| 필드 | 타입 | 필수 | 설명 |
|-----|------|-----|------|
| `type` | string | ✅ | `yaml` 고정 |
| `files` | list[string] | ✅ | YAML 매니페스트 파일 경로 목록 |
| `namespace` | string | ❌ | 배포 대상 네임스페이스 (오버라이드) |
| `depends_on` | list[string] | ❌ | 의존하는 앱 목록 |
| `enabled` | boolean | ❌ | 활성화 여부 (기본: true) |

---

## ⚡ 실행 방법

### 1. 통합 배포 (권장)

```bash
cd examples/deploy/yaml-example

# 전체 워크플로우 실행
sbkube apply --app-dir . --namespace example-yaml
```

**실행 과정**:
1. `manifests/nginx-deployment.yaml` → kubectl apply
2. `manifests/nginx-service.yaml` → kubectl apply

**결과**:
```
✅ nginx-deployment (Deployment) 생성
✅ nginx-service (Service) 생성
```

### 2. 단계별 배포

```bash
# 1. 준비 (yaml 타입은 이 단계에서 아무 작업 안 함)
sbkube prepare --app-dir .

# 2. 빌드 (yaml 타입은 이 단계에서 아무 작업 안 함)
sbkube build --app-dir .

# 3. 템플릿 (매니페스트 복사)
sbkube template --app-dir . --output-dir /tmp/yaml-example

# 4. 배포 (kubectl apply)
sbkube deploy --app-dir . --namespace example-yaml
```

### 3. Dry-run 모드

```bash
# 실제 배포 없이 계획 확인
sbkube deploy --app-dir . --namespace example-yaml --dry-run
```

---

## 🔍 배포 확인

### Deployment 확인

```bash
# Deployment 상태
kubectl get deployment -n example-yaml

# Pod 상태
kubectl get pods -n example-yaml -l app=nginx
```

**예상 출력**:
```
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
nginx-deployment   2/2     2            2           1m

NAME                                READY   STATUS    RESTARTS   AGE
nginx-deployment-xxxx-yyyy          1/1     Running   0          1m
nginx-deployment-xxxx-zzzz          1/1     Running   0          1m
```

### Service 확인

```bash
# Service 정보
kubectl get service -n example-yaml

# Service 상세 정보
kubectl describe service nginx-service -n example-yaml
```

**예상 출력**:
```
NAME            TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
nginx-service   ClusterIP   10.43.123.45    <none>        80/TCP    1m
```

### 애플리케이션 테스트

```bash
# Pod에서 직접 테스트
kubectl exec -n example-yaml deploy/nginx-deployment -- curl http://localhost

# Service를 통한 테스트 (클러스터 내부)
kubectl run -i --tty --rm debug --image=busybox --restart=Never -n example-yaml -- wget -O- http://nginx-service
```

---

## 🛠️ 고급 사용법

### 1. 다중 리소스 타입

```yaml
apps:
  full-stack:
    type: yaml
    files:
      - manifests/namespace.yaml       # Namespace
      - manifests/configmap.yaml       # ConfigMap
      - manifests/secret.yaml          # Secret
      - manifests/pvc.yaml             # PersistentVolumeClaim
      - manifests/deployment.yaml      # Deployment
      - manifests/service.yaml         # Service
      - manifests/ingress.yaml         # Ingress
```

**실행 순서**: 파일 순서대로 순차 배포

### 2. 환경별 매니페스트 분리

```yaml
# config-dev.yaml
namespace: development
apps:
  nginx:
    type: yaml
    files:
      - manifests/dev/deployment.yaml
      - manifests/dev/service.yaml

# config-prod.yaml
namespace: production
apps:
  nginx:
    type: yaml
    files:
      - manifests/prod/deployment.yaml
      - manifests/prod/service.yaml
```

**배포**:
```bash
# Development
sbkube apply --config config-dev.yaml

# Production
sbkube apply --config config-prod.yaml
```

### 3. Kustomize와 결합

**kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - nginx-deployment.yaml
  - nginx-service.yaml
replicas:
  - name: nginx-deployment
    count: 3
```

**빌드 후 배포**:
```bash
# Kustomize 빌드
kustomize build manifests/ > manifests/output.yaml

# SBKube 배포
sbkube apply --app-dir .
```

**config.yaml**:
```yaml
apps:
  nginx:
    type: yaml
    files:
      - manifests/output.yaml  # Kustomize 빌드 결과
```

### 4. 조건부 리소스

```yaml
apps:
  nginx-basic:
    type: yaml
    files:
      - manifests/nginx-deployment.yaml
      - manifests/nginx-service.yaml

  nginx-ingress:
    type: yaml
    files:
      - manifests/nginx-ingress.yaml
    enabled: false               # 기본적으로 비활성화
    depends_on:
      - nginx-basic
```

**활성화**:
```yaml
# config.yaml 수정
nginx-ingress:
  enabled: true
```

### 5. 네임스페이스별 격리

```yaml
namespace: default  # 전역 네임스페이스

apps:
  frontend:
    type: yaml
    files:
      - services/frontend/deployment.yaml
    namespace: frontend  # frontend 네임스페이스로 오버라이드

  backend:
    type: yaml
    files:
      - services/backend/deployment.yaml
    namespace: backend   # backend 네임스페이스로 오버라이드
```

---

## ⚠️ 주의사항 및 제한사항

### 1. 템플릿팅 미지원

**제한**: 변수 치환이나 템플릿 처리가 없습니다.

```yaml
# ❌ 작동하지 않음 (Helm 템플릿 문법)
image: {{ .Values.image.repository }}:{{ .Values.image.tag }}

# ✅ 정적 값만 가능
image: nginx:1.21
```

**대안**:
- **Helm 타입 사용**: 템플릿팅이 필요한 경우
- **Jinja2 사전 렌더링**: Python 템플릿 엔진 사용
- **envsubst**: 환경변수 치환
  ```bash
  export IMAGE_TAG=1.21
  envsubst < template.yaml > manifests/deployment.yaml
  sbkube apply --app-dir .
  ```

### 2. 순서 보장 제한

**보장됨**: 동일 앱 내 파일들은 순차 배포
```yaml
files:
  - file-1.yaml  # 1번째
  - file-2.yaml  # 2번째
  - file-3.yaml  # 3번째
```

**보장 안 됨**: 다른 앱 간 순서
```yaml
apps:
  app-a:
    files: [...]  # app-a와 app-b 순서 불확실
  app-b:
    files: [...]
```

**해결**: `depends_on` 사용
```yaml
apps:
  app-a:
    files: [...]
  app-b:
    files: [...]
    depends_on:
      - app-a  # app-a 이후 실행
```

### 3. 롤백 미지원

**제한**: Helm처럼 자동 롤백이 없습니다.

**수동 롤백 방법**:
```bash
# 1. Git에서 이전 버전 체크아웃
git checkout <previous-commit> manifests/

# 2. 재배포
sbkube apply --app-dir .

# 또는 수동 kubectl 롤백
kubectl rollout undo deployment/nginx-deployment -n example-yaml
```

### 4. 파일 경로 주의

**상대 경로**: `app-dir` 기준
```yaml
files:
  - manifests/deployment.yaml  # ✅ 올바름
  - ../other-app/deployment.yaml  # ⚠️ 위험 (상위 디렉토리)
  - /abs/path/deployment.yaml  # ❌ 절대 경로 사용 금지
```

### 5. 대량 리소스 처리

**비효율적**: 파일이 너무 많으면 느려집니다.
```yaml
# ⚠️ 50개 파일 → 느림
files:
  - file-01.yaml
  - file-02.yaml
  ...
  - file-50.yaml
```

**효율적**: 통합 매니페스트 사용
```bash
# 여러 YAML을 하나로 통합
cat manifests/*.yaml > manifests/all-in-one.yaml
```

**config.yaml**:
```yaml
files:
  - manifests/all-in-one.yaml  # ✅ 빠름
```

---

## 🔄 삭제 (Uninstall)

### 방법 1: sbkube delete (권장)

```bash
sbkube delete --app-dir . --namespace example-yaml
```

**실행 내용**:
- `files` 목록의 모든 리소스 삭제
- 역순으로 삭제 (Service → Deployment)

### 방법 2: kubectl delete

```bash
# 개별 파일 삭제
kubectl delete -f manifests/nginx-service.yaml
kubectl delete -f manifests/nginx-deployment.yaml

# 디렉토리 전체 삭제
kubectl delete -f manifests/

# 네임스페이스 전체 삭제
kubectl delete namespace example-yaml
```

---

## 📚 참고 자료

- [SBKube 애플리케이션 타입 가이드](../../../docs/02-features/application-types.md)
- [Kubernetes 객체 관리](https://kubernetes.io/docs/concepts/overview/working-with-objects/)
- [kubectl apply 참조](https://kubernetes.io/docs/reference/kubectl/apply/)
- [Kustomize 가이드](https://kustomize.io/)

---

## 🆚 다른 타입과 비교

| 기능 | yaml | helm | action | git |
|-----|------|------|--------|-----|
| **정적 YAML** | ✅ 최적 | ❌ | ✅ | ⚠️ |
| **템플릿팅** | ❌ | ✅ 최적 | ❌ | ❌ |
| **릴리스 관리** | ❌ | ✅ | ❌ | ❌ |
| **롤백 지원** | ❌ | ✅ | ❌ | ❌ |
| **다중 파일** | ✅ | ✅ | ✅ | ✅ |
| **사용 난이도** | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **적합한 용도** | 간단한 앱 | 복잡한 앱 | CRD/Operator | Git 차트 |

**선택 가이드**:
- **간단한 매니페스트 배포**: yaml 타입 (이 예제)
- **템플릿팅 필요**: helm 타입
- **CRD/Operator**: action 타입
- **Git 리포지토리 차트**: git 타입

---

## 💡 실전 예제

### 예제 1: WordPress + MySQL

```yaml
namespace: wordpress

apps:
  mysql:
    type: yaml
    files:
      - mysql/secret.yaml       # MySQL 비밀번호
      - mysql/pvc.yaml          # 데이터 볼륨
      - mysql/deployment.yaml   # MySQL Deployment
      - mysql/service.yaml      # MySQL Service

  wordpress:
    type: yaml
    files:
      - wordpress/pvc.yaml      # 워드프레스 볼륨
      - wordpress/deployment.yaml
      - wordpress/service.yaml
      - wordpress/ingress.yaml  # 외부 접근
    depends_on:
      - mysql  # MySQL 먼저 배포
```

### 예제 2: 모니터링 스택 (Prometheus + Grafana)

```yaml
namespace: monitoring

apps:
  prometheus:
    type: yaml
    files:
      - prometheus/configmap.yaml       # Prometheus 설정
      - prometheus/deployment.yaml
      - prometheus/service.yaml

  grafana:
    type: yaml
    files:
      - grafana/secret.yaml             # Grafana admin 비밀번호
      - grafana/configmap.yaml          # 대시보드 설정
      - grafana/deployment.yaml
      - grafana/service.yaml
      - grafana/ingress.yaml
    depends_on:
      - prometheus
```

---

**💡 팁**: yaml 타입은 Helm 차트가 없거나 간단한 애플리케이션에 최적입니다. 복잡한 애플리케이션은 helm 타입을 사용하세요.
