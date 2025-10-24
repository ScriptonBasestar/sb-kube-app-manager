# Security: Sealed Secrets

Sealed Secrets를 사용하여 민감한 정보를 안전하게 Git에 저장하고 배포하는 예제입니다.

## 📋 개요

**카테고리**: Security

**구성 요소**:
- **Sealed Secrets Controller**: Secret 암호화/복호화 컨트롤러
- **암호화된 Secret**: Git에 안전하게 저장 가능한 SealedSecret 리소스
- **애플리케이션**: 복호화된 Secret을 사용하는 예제 앱

**학습 목표**:
- GitOps 워크플로우에서 Secret 관리
- Public/Private Key 기반 암호화
- Secret 암호화 및 복호화 프로세스
- 프로덕션 환경 Secret 관리 베스트 프랙티스

## 🎯 문제점 및 해결책

### ❌ 기존 문제점

**Plain Secret을 Git에 커밋하면**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-password
data:
  password: cGFzc3dvcmQxMjM=  # Base64 인코딩 (암호화 아님!)
```

- ❌ Base64는 **인코딩**일 뿐, **암호화가 아님**
- ❌ Git 히스토리에 평문 노출
- ❌ 공개 저장소에 절대 불가능

### ✅ Sealed Secrets 해결책

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: db-password
spec:
  encryptedData:
    password: AgBj8F...  # RSA 암호화된 데이터
```

- ✅ **공개키로 암호화**: 누구나 암호화 가능
- ✅ **비공개키로 복호화**: 클러스터만 복호화 가능
- ✅ **Git 안전**: 암호화된 상태로 저장
- ✅ **GitOps 가능**: ArgoCD, Flux 등과 통합

## 🚀 빠른 시작

### 1. 전체 스택 배포

```bash
sbkube apply \
  --app-dir examples/security/01-sealed-secrets \
  --namespace sealed-secrets
```

### 2. 배포 확인

```bash
# Sealed Secrets Controller 확인
kubectl get pods -n sealed-secrets

# SealedSecret 리소스 확인
kubectl get sealedsecrets -n sealed-secrets

# 복호화된 Secret 확인 (자동 생성됨)
kubectl get secrets -n sealed-secrets
```

### 3. 애플리케이션 확인

```bash
# Secret을 사용하는 앱 Pod 확인
kubectl get pods -n sealed-secrets -l app=demo-app

# 환경 변수 확인 (Secret이 정상 주입됨)
kubectl exec -n sealed-secrets -it <pod-name> -- env | grep DATABASE
```

## 📖 설정 파일 설명

### config.yaml

```yaml
namespace: sealed-secrets

apps:
  # 1단계: Sealed Secrets Controller 설치
  sealed-secrets-controller:
    type: helm
    chart: sealed-secrets/sealed-secrets
    values:
      - values/sealed-secrets-values.yaml
    enabled: true

  # 2단계: SealedSecret 리소스 생성 (Controller 의존)
  demo-sealed-secrets:
    type: yaml
    files:
      - manifests/sealed-secret.yaml
    depends_on:
      - sealed-secrets-controller

  # 3단계: Secret을 사용하는 애플리케이션 (SealedSecret 의존)
  demo-app:
    type: yaml
    files:
      - manifests/demo-app.yaml
    depends_on:
      - demo-sealed-secrets
```

### 의존성 체인

```
Sealed Secrets Controller (암호화/복호화 엔진)
    ↓
SealedSecret (암호화된 Secret)
    ↓  (자동 복호화)
Secret (평문 Secret, 클러스터 내에서만 존재)
    ↓
Application (Secret 사용)
```

## 🔧 주요 구성 요소

### 1. Sealed Secrets Controller

**역할**: SealedSecret 리소스를 감지하고 Secret으로 복호화

**주요 설정** (`values/sealed-secrets-values.yaml`):
```yaml
fullnameOverride: sealed-secrets-controller

# 컨트롤러 설정
commandArgs:
  - --update-status

# 리소스
resources:
  requests:
    memory: 128Mi
    cpu: 50m
  limits:
    memory: 256Mi
    cpu: 100m

# RBAC
rbac:
  create: true
  pspEnabled: false
```

**컨트롤러 역할**:
1. 클러스터 시작 시 RSA 키 페어 생성 (없으면)
2. SealedSecret 리소스 감시
3. 비공개키로 복호화하여 Secret 생성
4. Secret 자동 갱신 및 관리

### 2. SealedSecret 생성

**방법 1: kubeseal CLI 사용 (권장)**

```bash
# kubeseal 설치
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/kubeseal-0.24.0-linux-amd64.tar.gz
tar -xzf kubeseal-0.24.0-linux-amd64.tar.gz
sudo install -m 755 kubeseal /usr/local/bin/kubeseal

# 공개키 가져오기
kubeseal --fetch-cert \
  --controller-name=sealed-secrets-controller \
  --controller-namespace=sealed-secrets \
  > pub-cert.pem

# Secret을 SealedSecret으로 암호화
kubectl create secret generic db-credentials \
  --dry-run=client \
  --from-literal=username=admin \
  --from-literal=password=super-secret-password \
  -o yaml | \
kubeseal \
  --cert=pub-cert.pem \
  --format=yaml \
  > sealed-secret.yaml

# 암호화된 파일을 Git에 커밋
git add sealed-secret.yaml
git commit -m "Add encrypted database credentials"
```

**방법 2: 온라인 도구 (개발/테스트용)**

```bash
# 공개키 URL로 직접 암호화
echo -n "super-secret-password" | kubeseal \
  --raw \
  --from-file=/dev/stdin \
  --namespace sealed-secrets \
  --name db-credentials \
  --controller-name sealed-secrets-controller \
  --controller-namespace sealed-secrets
```

### 3. 애플리케이션에서 Secret 사용

**Deployment 예시** (`manifests/demo-app.yaml`):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-app
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: app
        image: nginx:alpine
        env:
        # Secret에서 환경 변수 주입
        - name: DATABASE_USERNAME
          valueFrom:
            secretKeyRef:
              name: db-credentials  # SealedSecret이 생성한 Secret
              key: username
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: password
```

**볼륨 마운트 예시**:
```yaml
spec:
  template:
    spec:
      containers:
      - name: app
        volumeMounts:
        - name: secret-volume
          mountPath: /etc/secrets
          readOnly: true
      volumes:
      - name: secret-volume
        secret:
          secretName: db-credentials
```

## 🎓 학습 포인트

### 1. 암호화 방식 이해

**Public/Private Key 암호화**:
```
개발자 (공개키 사용)
    ↓ 암호화
SealedSecret (Git에 안전 저장)
    ↓ 배포
Kubernetes 클러스터
    ↓ 복호화 (비공개키 사용)
Secret (클러스터 내에서만)
    ↓
Application
```

**보안 원칙**:
- ✅ 공개키는 공유 가능 (암호화만 가능)
- ⚠️ 비공개키는 클러스터에만 존재 (복호화 가능)
- ✅ SealedSecret은 Git 공개 가능
- ❌ 복호화된 Secret은 절대 Git에 넣지 않음

### 2. Scope (범위) 개념

SealedSecret은 3가지 범위 지원:

**strict (기본값)**:
```yaml
# 네임스페이스 + 이름 일치해야 복호화 가능
metadata:
  name: my-secret
  namespace: production
  annotations:
    sealedsecrets.bitnami.com/scope: strict
```

**namespace-wide**:
```yaml
# 같은 네임스페이스면 이름 달라도 복호화 가능
metadata:
  annotations:
    sealedsecrets.bitnami.com/scope: namespace-wide
```

**cluster-wide**:
```yaml
# 클러스터 어디서든 복호화 가능
metadata:
  annotations:
    sealedsecrets.bitnami.com/scope: cluster-wide
```

### 3. 키 로테이션

**자동 키 로테이션**:
- Sealed Secrets는 기본적으로 30일마다 새 키 생성
- 이전 키도 보관하여 기존 SealedSecret 복호화 가능
- 새 SealedSecret은 최신 키로 암호화

**수동 키 백업**:
```bash
# 비공개키 백업 (안전한 장소에 보관!)
kubectl get secret -n sealed-secrets \
  -l sealedsecrets.bitnami.com/sealed-secrets-key=active \
  -o yaml > sealed-secrets-key-backup.yaml
```

### 4. 재암호화 (Re-encryption)

**네임스페이스 변경 시**:
```bash
# 기존 Secret을 새 네임스페이스용으로 재암호화
kubeseal --re-encrypt \
  --namespace=new-namespace \
  < old-sealed-secret.yaml \
  > new-sealed-secret.yaml
```

## 🧪 테스트 시나리오

### 시나리오 1: Secret 암호화 및 배포

```bash
# 1. Plain Secret 생성 (dry-run)
kubectl create secret generic test-secret \
  --dry-run=client \
  --from-literal=api-key=my-api-key-12345 \
  -o yaml > plain-secret.yaml

# 2. 암호화
kubeseal --cert=pub-cert.pem -f plain-secret.yaml -o yaml > sealed-secret.yaml

# 3. SealedSecret 배포
kubectl apply -f sealed-secret.yaml -n sealed-secrets

# 4. Secret 자동 생성 확인
kubectl get secret test-secret -n sealed-secrets
```

### 시나리오 2: 복호화 확인

```bash
# SealedSecret이 생성한 Secret 내용 확인
kubectl get secret db-credentials -n sealed-secrets -o jsonpath='{.data.password}' | base64 -d
# 출력: super-secret-password
```

### 시나리오 3: 애플리케이션 통합

```bash
# 앱 Pod에서 Secret 확인
kubectl exec -n sealed-secrets -it <demo-app-pod> -- sh

# 환경 변수 확인
echo $DATABASE_PASSWORD
# 출력: super-secret-password

# 파일로 마운트된 경우
cat /etc/secrets/password
# 출력: super-secret-password
```

### 시나리오 4: GitOps 워크플로우

```bash
# 1. SealedSecret 생성 및 커밋
kubectl create secret generic prod-db \
  --dry-run=client \
  --from-literal=password=prod-password \
  -o yaml | kubeseal --cert=pub-cert.pem -o yaml > prod-sealed-secret.yaml

git add prod-sealed-secret.yaml
git commit -m "Add production database secret"
git push

# 2. GitOps 도구가 자동 배포 (ArgoCD, Flux)
# 3. Sealed Secrets Controller가 자동 복호화
# 4. 애플리케이션이 Secret 사용
```

## 🔍 트러블슈팅

### 문제 1: "SealedSecret이 복호화되지 않음"

**증상**:
```bash
kubectl get sealedsecrets -n sealed-secrets
# SealedSecret 존재하지만 Secret 미생성
```

**원인**: Controller가 실행 중이지 않음

**해결**:
```bash
# Controller 상태 확인
kubectl get pods -n sealed-secrets

# Controller 로그 확인
kubectl logs -n sealed-secrets -l app.kubernetes.io/name=sealed-secrets
```

### 문제 2: "암호화 실패 (unable to fetch certificate)"

**증상**:
```bash
kubeseal --fetch-cert
# error: cannot fetch certificate
```

**원인**: Controller가 아직 준비되지 않음

**해결**:
```bash
# Controller 준비 대기
kubectl wait --for=condition=ready pod \
  -n sealed-secrets \
  -l app.kubernetes.io/name=sealed-secrets \
  --timeout=300s

# 재시도
kubeseal --fetch-cert > pub-cert.pem
```

### 문제 3: "복호화 에러 (no key could decrypt)"

**증상**:
```
Error: no key could decrypt secret
```

**원인**: 다른 클러스터의 키로 암호화됨

**해결**:
```bash
# 현재 클러스터의 공개키로 재암호화
kubeseal --cert=pub-cert.pem -f plain-secret.yaml -o yaml > new-sealed-secret.yaml
```

### 문제 4: "키 분실"

**원인**: Controller 재설치로 키 분실

**예방**:
```bash
# 정기적 키 백업
kubectl get secret -n sealed-secrets \
  -l sealedsecrets.bitnami.com/sealed-secrets-key \
  -o yaml > sealed-secrets-keys-backup-$(date +%Y%m%d).yaml
```

**복구**:
```bash
# 백업한 키 복원
kubectl apply -f sealed-secrets-keys-backup-20250124.yaml

# Controller 재시작
kubectl rollout restart deployment -n sealed-secrets sealed-secrets-controller
```

## 💡 실전 패턴

### 패턴 1: 환경별 Secret 관리

```
environments/
├── dev/
│   └── sealed-secrets/
│       ├── db-password.yaml
│       └── api-keys.yaml
├── staging/
│   └── sealed-secrets/
│       ├── db-password.yaml
│       └── api-keys.yaml
└── prod/
    └── sealed-secrets/
        ├── db-password.yaml
        └── api-keys.yaml
```

**각 환경마다 다른 클러스터, 다른 암호화 키**

### 패턴 2: CI/CD 통합

```yaml
# GitLab CI 예시
stages:
  - encrypt
  - deploy

encrypt-secrets:
  stage: encrypt
  script:
    # 공개키 가져오기
    - kubeseal --fetch-cert --controller-namespace=sealed-secrets > pub-cert.pem
    # Secret 암호화
    - kubectl create secret generic app-config \
        --dry-run=client \
        --from-env-file=.env.production \
        -o yaml | \
      kubeseal --cert=pub-cert.pem -o yaml > sealed-secret.yaml
    # Git에 커밋
    - git add sealed-secret.yaml
    - git commit -m "Update encrypted secrets"
    - git push

deploy:
  stage: deploy
  script:
    - kubectl apply -f sealed-secret.yaml
```

### 패턴 3: Helm Values와 통합

```yaml
# values-prod.yaml (Git 안전)
sealedSecrets:
  db:
    username: AgBh8F...  # 암호화된 값
    password: AgCk3L...  # 암호화된 값
```

```yaml
# Helm template
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: db-credentials
spec:
  encryptedData:
    username: {{ .Values.sealedSecrets.db.username }}
    password: {{ .Values.sealedSecrets.db.password }}
```

### 패턴 4: 다중 Secret 관리

```bash
# 여러 Secret을 한 번에 암호화
for secret in db-creds api-keys tls-cert; do
  kubectl create secret generic $secret \
    --dry-run=client \
    --from-env-file=secrets/$secret.env \
    -o yaml | \
  kubeseal --cert=pub-cert.pem -o yaml > sealed-secrets/$secret.yaml
done
```

## 📚 추가 학습 자료

### 공식 문서
- [Sealed Secrets GitHub](https://github.com/bitnami-labs/sealed-secrets)
- [Bitnami Sealed Secrets Docs](https://docs.bitnami.com/tutorials/sealed-secrets/)

### SBKube 관련
- [Application Types - YAML](../../docs/02-features/application-types.md#2-yaml)
- [Security Best Practices](../../docs/07-troubleshooting/README.md)

### 관련 예제
- [RBAC](../02-rbac/) - 권한 관리
- [Network Policies](../03-network-policies/) - 네트워크 보안

## 🎯 다음 단계

1. **ArgoCD 통합**: GitOps 워크플로우 구축
2. **External Secrets**: AWS Secrets Manager, Vault 연동
3. **자동화**: CI/CD 파이프라인에 Secret 암호화 통합

## 🧹 정리

```bash
# 네임스페이스 삭제
kubectl delete namespace sealed-secrets

# 또는 개별 리소스 삭제
helm uninstall sealed-secrets-controller -n sealed-secrets
kubectl delete sealedsecrets --all -n sealed-secrets
```

---

**Secret을 안전하게 Git에 저장하고 자동으로 배포하세요! 🔐**
