# 🏭 프로덕션 배포 Best Practices

> **난이도**: ⭐⭐⭐ 고급 **소요 시간**: 30분 **사전 요구사항**: [02-multi-app-deployment.md](02-multi-app-deployment.md) 완료

______________________________________________________________________

## 📋 학습 목표

- ✅ 프로덕션 환경 설정 관리
- ✅ 안전한 배포 워크플로우
- ✅ 모니터링 및 롤백 전략
- ✅ 보안 Best Practices

______________________________________________________________________

## 시나리오: 프로덕션 웹 서비스 배포

**요구사항**:

- 고가용성 (HA) 구성
- 리소스 제한 및 요청 설정
- 시크릿 관리
- 롤백 가능한 배포

______________________________________________________________________

## Step 1: 환경별 설정 분리

### 디렉토리 구조

```
production-app/
├── config.yaml           # 공통 앱 정의
├── sources.yaml
├── values/
│   ├── common/          # 공통 설정
│   │   └── app.yaml
│   ├── dev/             # 개발 환경
│   │   └── app.yaml
│   └── prod/            # 프로덕션 환경
│       └── app.yaml
└── secrets/             # Git 제외 (.gitignore)
    └── prod-secrets.yaml
```

______________________________________________________________________

## Step 2: 프로덕션 설정 작성

### `config.yaml`

```yaml
namespace: production

apps:
  web-app:
    type: helm
    chart: ingress-nginx/ingress-nginx
    version: 4.0.0
    enabled: true
    values:
      - values/common/app.yaml
      - values/prod/app.yaml  # 환경별 오버라이드
```

### `values/common/app.yaml` (공통)

```yaml
nameOverride: "webapp"

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  hostname: app.example.com
```

### `values/prod/app.yaml` (프로덕션 전용)

```yaml
# 고가용성 구성
replicaCount: 3

podDisruptionBudget:
  enabled: true
  minAvailable: 2

# 리소스 제한
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi

# 헬스체크
livenessProbe:
  enabled: true
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  enabled: true
  initialDelaySeconds: 10
  periodSeconds: 5

# 롤링 업데이트 전략
updateStrategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0

# 보안 설정
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
```

______________________________________________________________________

## Step 3: 안전한 배포 워크플로우

### 3.1 배포 전 검증

```bash
# 1. 설정 검증
sbkube validate

# 2. Dry-run 실행
sbkube apply --dry-run

# 3. 클러스터 연결 확인
kubectl cluster-info
kubectl get nodes
```

### 3.2 단계별 배포

```bash
# Step 1: Prepare만 실행 (차트 다운로드)
sbkube prepare

# Step 2: Build (커스터마이징 있는 경우)
sbkube build

# Step 3: Template 확인 (실제 YAML 검토)
sbkube template --output-dir /tmp/rendered
cat /tmp/rendered/web-app/templates/deployment.yaml

# Step 4: 배포 실행
sbkube deploy
```

### 3.3 배포 후 검증

```bash
# Pod 상태 확인 (모든 Pod가 Running인지)
kubectl get pods -n production -w

# Rollout 상태 확인
kubectl rollout status deployment/webapp -n production

# Pod 이벤트 확인
kubectl describe deployment webapp -n production

# 로그 확인
kubectl logs -n production -l app=webapp --tail=50
```

______________________________________________________________________

## Step 4: 모니터링 및 롤백

### 4.1 배포 히스토리

```bash
# SBKube 히스토리
sbkube history --namespace production

# Helm 히스토리
helm history webapp -n production
```

### 4.2 문제 발생 시 롤백

```bash
# 방법 1: SBKube 롤백
sbkube rollback --revision 1 --namespace production

# 방법 2: Helm 직접 롤백
helm rollback webapp 1 -n production

# 롤백 확인
kubectl get pods -n production
sbkube history
```

______________________________________________________________________

## Step 5: 보안 Best Practices

### 5.1 시크릿 관리

**`.gitignore`에 추가**:

```
secrets/
*.secret.yaml
```

**Kubernetes Secret 생성**:

```bash
# 파일에서 시크릿 생성
kubectl create secret generic app-secrets \
  --from-file=api-key=secrets/api-key.txt \
  -n production

# 또는 값으로 직접 생성
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password='SuperSecret123!' \
  -n production
```

**Helm values에서 참조**:

```yaml
# values/prod/app.yaml
env:
  - name: API_KEY
    valueFrom:
      secretKeyRef:
        name: app-secrets
        key: api-key
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-credentials
        key: password
```

### 5.2 RBAC 설정

```yaml
# values/prod/app.yaml
serviceAccount:
  create: true
  name: webapp-sa

rbac:
  create: true
  rules:
    - apiGroups: [""]
      resources: ["configmaps"]
      verbs: ["get", "list"]
```

______________________________________________________________________

## Step 6: CI/CD 통합

### GitHub Actions 예제

```yaml
# .github/workflows/deploy-prod.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install SBKube
        run: pip install sbkube

      - name: Setup Kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG }}" > ~/.kube/config

      - name: Validate
        run: sbkube validate

      - name: Deploy
        run: sbkube apply

      - name: Verify
        run: |
          kubectl get pods -n production
          sbkube history
```

______________________________________________________________________

## 체크리스트

### 배포 전 ✅

- [ ] 설정 파일 검증 (`sbkube validate`)
- [ ] Dry-run 실행 (`--dry-run`)
- [ ] 리소스 제한 설정 확인
- [ ] 시크릿 생성 및 참조 확인
- [ ] 백업 및 롤백 계획 수립

### 배포 중 ✅

- [ ] Pod 상태 모니터링
- [ ] 로그 실시간 확인
- [ ] Rollout 진행 상태 확인

### 배포 후 ✅

- [ ] 모든 Pod가 Running 상태인지 확인
- [ ] Health check 응답 확인
- [ ] 애플리케이션 기능 테스트
- [ ] 배포 히스토리 기록

______________________________________________________________________

## 트러블슈팅

### 문제: Pod가 CrashLoopBackOff

**원인**: 잘못된 환경 변수, 시크릿 누락, 리소스 부족

**해결**:

```bash
# 로그 확인
kubectl logs -n production <pod-name>

# 이벤트 확인
kubectl describe pod -n production <pod-name>

# 시크릿 확인
kubectl get secrets -n production
```

### 문제: 배포가 멈춤 (Pending)

**원인**: 리소스 부족, PVC 마운트 실패

**해결**:

```bash
# 노드 리소스 확인
kubectl top nodes

# Pod 이벤트 확인
kubectl describe pod -n production <pod-name>
```

______________________________________________________________________

## 다음 단계

- **[04-customization.md](04-customization.md)** - 차트 커스터마이징
- **[05-troubleshooting.md](05-troubleshooting.md)** - 문제 해결 가이드

______________________________________________________________________

**작성자**: SBKube Documentation Team **버전**: v0.5.0 **최종 업데이트**: 2025-10-31
