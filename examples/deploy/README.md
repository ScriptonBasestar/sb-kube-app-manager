# sbkube deploy 명령 예시

`deploy` 명령은 Helm chart, YAML 매니페스트, 실행 명령 등을 Kubernetes 클러스터에 적용합니다.

## 기본 사용법

```bash
sbkube deploy --app-dir config
```

## 옵션

- `--app-dir`: 앱 구성 디렉토리 (기본값: config)
- `--base-dir`: 프로젝트 루트 디렉토리 (기본값: 현재 디렉토리)
- `--namespace`: 설치할 기본 네임스페이스 (없으면 앱별로 따름)
- `--dry-run`: 실제로 적용하지 않고 dry-run
- `--app`: 배포할 특정 앱 이름 (지정하지 않으면 모든 앱 배포)
- `--config-file`: 사용할 설정 파일 이름

## 설정 파일 예시

### 1. Helm 차트 배포

```yaml
namespace: production

apps:
  - name: webapp
    type: install-helm
    path: webapp-nginx     # build 디렉토리 내 경로
    namespace: web         # 앱별 네임스페이스 (선택사항)
    specs:
      values:
        - values-prod.yaml       # values 디렉토리 내 파일
        - values-common.yaml
```

### 2. YAML 매니페스트 배포

```yaml
apps:
  - name: configs
    type: install-yaml
    namespace: default
    specs:
      actions:
        - type: apply
          path: manifests/configmap.yaml
        - type: create
          path: manifests/secret.yaml
        - type: apply
          path: https://raw.githubusercontent.com/example/repo/main/rbac.yaml
```

### 3. 실행 명령

```yaml
apps:
  - name: db-init
    type: exec
    specs:
      commands:
        - "kubectl create namespace database"
        - "kubectl label namespace database env=production"
        - "helm repo add bitnami https://charts.bitnami.com/bitnami"
```

## 실행 예시

### 1. 전체 앱 배포

```bash
# 모든 앱 배포
sbkube deploy --app-dir config

# 실행 결과:
# ✅ 클러스터 접속 확인됨
# 
# ➡️ 앱 'webapp' (타입: install-helm, 네임스페이스: web) 배포 시작
# ✅ values: config/values/values-prod.yaml
# ✅ values: config/values/values-common.yaml
# $ helm install webapp config/build/webapp-nginx --namespace web --create-namespace --values config/values/values-prod.yaml --values config/values/values-common.yaml
# ✅ 앱 'webapp': Helm 릴리스 'webapp' 배포 완료 (네임스페이스: web)
```

### 2. 특정 네임스페이스에 배포

```bash
# CLI로 네임스페이스 지정 (최우선)
sbkube deploy --namespace staging

# dry-run으로 확인
sbkube deploy --dry-run --app webapp
```

### 3. 특정 앱만 배포

```bash
# 단일 앱 배포
sbkube deploy --app webapp

# 여러 앱을 순차적으로 배포
sbkube deploy --app database
sbkube deploy --app backend
sbkube deploy --app frontend
```

## 네임스페이스 우선순위

네임스페이스는 다음 우선순위로 결정됩니다:

1. CLI `--namespace` 옵션
2. 앱별 `namespace` 필드
3. 전역 `namespace` 필드
4. 없으면 default 네임스페이스

특수 값으로 네임스페이스 무시:
- `!ignore`
- `!none`  
- `!false`
- `""` (빈 문자열)

## 배포 타입별 상세

### 1. install-helm 타입

```yaml
apps:
  - name: redis
    type: install-helm
    path: redis-cache       # 차트 경로 (build/redis-cache)
    release_name: my-redis  # Helm 릴리스 이름 (선택사항)
    specs:
      values:
        - values.yaml
        - values-override.yaml
```

Values 파일 우선순위:
- 나중에 지정된 파일이 앞의 파일을 오버라이드
- 절대 경로 또는 values 디렉토리 상대 경로 사용 가능

### 2. install-yaml 타입

```yaml
apps:
  - name: base-resources
    type: install-yaml
    specs:
      actions:
        # 로컬 파일
        - type: apply
          path: ./manifests/namespace.yaml
        
        # 절대 경로
        - type: apply
          path: /opt/k8s/configs/rbac.yaml
        
        # URL
        - type: apply
          path: https://example.com/manifests/ingress.yaml
        
        # 삭제 작업
        - type: delete
          path: ./manifests/old-config.yaml
```

### 3. exec 타입

```yaml
apps:
  - name: post-deploy
    type: exec
    specs:
      commands:
        # 데이터베이스 마이그레이션
        - "kubectl exec -n db deploy/postgres -- psql -c 'CREATE DATABASE myapp'"
        
        # 시크릿 생성
        - "kubectl create secret generic api-key --from-literal=key=abc123 -n backend"
        
        # 상태 확인
        - "kubectl rollout status deployment/webapp -n web"
```

## 문제 해결

### 1. 클러스터 접속 실패

```bash
# 현재 컨텍스트 확인
kubectl config current-context

# 사용 가능한 컨텍스트 목록
kubectl config get-contexts

# 컨텍스트 변경
kubectl config use-context my-cluster

# kubeconfig 파일 지정
export KUBECONFIG=~/.kube/my-cluster-config
```

### 2. Helm 릴리스 이미 존재

```bash
# 기존 릴리스 확인
helm list -n web

# 업그레이드가 필요한 경우
sbkube upgrade --app webapp

# 또는 삭제 후 재배포
sbkube delete --app webapp
sbkube deploy --app webapp
```

### 3. YAML 적용 실패

```bash
# 문법 검증
kubectl apply --dry-run=client -f manifests/app.yaml

# 상세 오류 확인
kubectl apply -f manifests/app.yaml --v=8

# 권한 확인
kubectl auth can-i create deployments -n web
```

## 모범 사례

### 1. 환경별 Values 파일 분리

```
config/
└── values/
    ├── values-common.yaml    # 공통 설정
    ├── values-dev.yaml       # 개발 환경
    ├── values-staging.yaml   # 스테이징 환경
    └── values-prod.yaml      # 프로덕션 환경
```

### 2. 배포 순서 관리

```yaml
# 1. 기반 리소스
apps:
  - name: namespaces
    type: exec
    specs:
      commands:
        - "kubectl create namespace web || true"
        - "kubectl create namespace db || true"

# 2. 데이터베이스
  - name: postgres
    type: install-helm
    namespace: db
    # ...

# 3. 애플리케이션
  - name: webapp
    type: install-helm
    namespace: web
    # ...
```

### 3. 헬스체크 포함

```yaml
apps:
  - name: deploy-and-verify
    type: exec
    specs:
      commands:
        # 배포
        - "helm install myapp ./charts/myapp -n production"
        # 대기
        - "kubectl wait --for=condition=ready pod -l app=myapp -n production --timeout=300s"
        # 확인
        - "kubectl get pods -n production -l app=myapp"
``` 