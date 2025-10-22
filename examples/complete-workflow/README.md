# sbkube 전체 워크플로우 예시

이 예시는 sbkube를 사용한 완전한 애플리케이션 배포 워크플로우를 보여줍니다.

## 프로젝트 구조

```
my-k8s-project/
├── sources.yaml              # 외부 리소스 정의
├── config/                   # 메인 애플리케이션 설정
│   ├── config.yaml          # 앱 목록 및 구성
│   ├── values/              # Helm values 파일들
│   │   ├── redis-values.yaml
│   │   ├── postgres-values.yaml
│   │   └── webapp-values.yaml
│   └── overrides/           # 차트 커스터마이징
│       └── webapp/
│           └── templates/
│               └── ingress.yaml
├── environments/            # 환경별 설정 (옵션)
│   ├── dev/
│   │   └── config.yaml
│   ├── staging/
│   │   └── config.yaml
│   └── prod/
│       └── config.yaml
└── manifests/              # 추가 K8s 리소스
    ├── namespace.yaml
    └── secrets.yaml
```

## Step 1: sources.yaml 작성

```yaml
# sources.yaml
cluster: my-k8s-cluster
kubeconfig: ~/.kube/config

helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
  ingress-nginx: https://kubernetes.github.io/ingress-nginx
  prometheus: https://prometheus-community.github.io/helm-charts

git_repos:
  custom-charts:
    url: https://github.com/myorg/helm-charts.git
    branch: main
  
  k8s-configs:
    url: https://github.com/myorg/k8s-configs.git
    branch: v2.0.0
```

## Step 2: config.yaml 작성

```yaml
# config/config.yaml
namespace: myapp

apps:
  # 1. 네임스페이스 및 기본 리소스 생성
  - name: base-setup
    type: exec
    specs:
      commands:
        - "kubectl create namespace myapp || true"
        - "kubectl create namespace monitoring || true"
        - "kubectl label namespace myapp environment=production"

  # 2. 시크릿 및 설정 적용
  - name: configs
    type: yaml
    specs:
      actions:
        - type: apply
          path: manifests/secrets.yaml
        - type: apply
          path: manifests/configmap.yaml

  # 3. 데이터베이스 - PostgreSQL
  - name: database
    type: helm
    specs:
      repo: bitnami
      chart: postgresql
      chart_version: 12.5.8
      dest: postgres-db

  - name: database-deploy
    type: helm
    path: postgres-db
    namespace: myapp
    specs:
      values:
        - postgres-values.yaml

  # 4. 캐시 - Redis  
  - name: cache
    type: helm
    specs:
      repo: bitnami
      chart: redis
      chart_version: 17.11.3
      dest: redis-cache

  - name: cache-deploy
    type: helm
    path: redis-cache
    namespace: myapp
    specs:
      values:
        - redis-values.yaml

  # 5. 웹 애플리케이션
  - name: webapp
    type: pull-git
    specs:
      repo: custom-charts
      paths:
        - src: charts/webapp
          dest: webapp

  - name: webapp-build
    type: copy-app
    specs:
      paths:
        - src: ../../webapp-src
          dest: webapp-built

  - name: webapp-deploy
    type: helm
    path: webapp-built
    namespace: myapp
    specs:
      values:
        - webapp-values.yaml

  # 6. 모니터링
  - name: monitoring
    type: helm
    specs:
      repo: prometheus
      chart: kube-prometheus-stack
      dest: monitoring-stack

  - name: monitoring-deploy
    type: helm
    path: monitoring-stack
    namespace: monitoring
    specs:
      values:
        - monitoring-values.yaml

  # 7. 배포 후 검증
  - name: verify-deployment
    type: exec
    specs:
      commands:
        - "kubectl get pods -n myapp"
        - "kubectl get svc -n myapp"
        - "kubectl rollout status deployment/webapp -n myapp --timeout=300s"
```

## Step 3: Values 파일 작성

### postgres-values.yaml
```yaml
# config/values/postgres-values.yaml
global:
  postgresql:
    auth:
      postgresPassword: "changeme"
      database: "myapp"

primary:
  persistence:
    enabled: true
    size: 10Gi

metrics:
  enabled: true
```

### redis-values.yaml
```yaml
# config/values/redis-values.yaml
auth:
  enabled: true
  password: "changeme"

master:
  persistence:
    enabled: true
    size: 5Gi

replica:
  replicaCount: 2
  persistence:
    enabled: true
    size: 5Gi
```

### webapp-values.yaml
```yaml
# config/values/webapp-values.yaml
replicaCount: 3

image:
  repository: myorg/webapp
  tag: "1.0.0"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: app.example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"

env:
  - name: DATABASE_URL
    value: "postgresql://postgres:changeme@postgres-db:5432/myapp"
  - name: REDIS_URL
    value: "redis://:changeme@redis-cache-master:6379"
```

## Step 4: 실행 명령어

### 개발 환경
```bash
# 1. 외부 리소스 준비
sbkube prepare --sources sources.yaml

# 2. 빌드
sbkube build --app-dir config

# 3. 템플릿 확인 (선택사항)
sbkube template --app webapp-deploy

# 4. 배포
sbkube deploy --app-dir config --dry-run  # 먼저 dry-run으로 확인
sbkube deploy --app-dir config            # 실제 배포
```

### 프로덕션 환경
```bash
# 환경별 설정 사용
sbkube prepare --sources sources-prod.yaml
sbkube build --app-dir environments/prod
sbkube deploy --app-dir environments/prod --namespace production
```

## Step 5: 업그레이드 및 관리

### 애플리케이션 업그레이드
```bash
# values 파일 수정 후
vim config/values/webapp-values.yaml  # tag를 1.0.1로 변경

# 업그레이드 실행
sbkube upgrade --app webapp-deploy
```

### 롤백
```bash
# Helm 히스토리 확인
helm history webapp -n myapp

# 이전 버전으로 롤백
helm rollback webapp 1 -n myapp
```

### 삭제
```bash
# 특정 앱만 삭제
sbkube delete --app webapp-deploy

# 전체 삭제 (역순으로 진행)
sbkube delete --app-dir config
```

## 모범 사례

### 1. 환경 분리
```yaml
# environments/dev/config.yaml
namespace: myapp-dev
apps:
  - name: database
    type: helm
    specs:
      values:
        - postgres-values-dev.yaml  # 개발용 가벼운 설정

# environments/prod/config.yaml  
namespace: myapp-prod
apps:
  - name: database
    type: helm
    specs:
      values:
        - postgres-values-prod.yaml  # 프로덕션용 고가용성 설정
```

### 2. GitOps 통합
```yaml
# CI/CD 파이프라인에서 사용
steps:
  - name: Prepare
    run: sbkube prepare --sources sources.yaml
    
  - name: Build
    run: sbkube build --app-dir config
    
  - name: Deploy to Staging
    run: |
      sbkube deploy --app-dir config \
        --namespace staging \
        --kubeconfig $STAGING_KUBECONFIG
        
  - name: Run Tests
    run: ./run-integration-tests.sh
    
  - name: Deploy to Production
    run: |
      sbkube deploy --app-dir config \
        --namespace production \
        --kubeconfig $PROD_KUBECONFIG
```

### 3. 시크릿 관리
```yaml
# Sealed Secrets 또는 External Secrets 사용
apps:
  - name: secrets
    type: yaml
    specs:
      actions:
        - type: apply
          path: https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.18.0/controller.yaml
        
  - name: app-secrets
    type: exec
    specs:
      commands:
        - "kubeseal --format=yaml < secrets/app-secret.yaml | kubectl apply -f -"
```

## 트러블슈팅

### 1. 의존성 순서 문제
앱들을 의존성 순서대로 정의:
1. 네임스페이스/RBAC
2. 시크릿/ConfigMap
3. 데이터베이스
4. 캐시
5. 애플리케이션
6. 모니터링

### 2. 리소스 부족
```bash
# 노드 리소스 확인
kubectl top nodes
kubectl describe nodes

# Pod 리소스 사용량 확인
kubectl top pods -n myapp
```

### 3. 네트워크 정책
```yaml
# 필요한 경우 NetworkPolicy 추가
apps:
  - name: network-policies
    type: yaml
    specs:
      actions:
        - type: apply
          path: manifests/network-policies/
``` 