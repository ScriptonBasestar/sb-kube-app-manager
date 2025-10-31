# Hooks Manifests 예제

**Phase 1 기능 시연**: `post_deploy_manifests` 훅을 사용하여 cert-manager 배포 후 자동으로 ClusterIssuers를 생성합니다.

## 개요

이 예제는 SBKube v0.7.0+ 의 **Phase 1: Manifests 지원** 기능을 시연합니다.

### 시나리오

1. **cert-manager** Helm 차트 배포
2. 배포 후 자동으로 **ClusterIssuer** 리소스 생성 (Let's Encrypt)

### 기존 방식 vs 개선된 방식

#### ❌ 기존 방식 (kubectl 직접 호출)

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager
    hooks:
      post_deploy:
        - kubectl apply -f manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
        - kubectl apply -f manifests/issuers/cluster-issuer-letsencrypt-stg.yaml
```

**문제점**:
- kubectl 직접 실행 → sbkube가 상태 추적 불가
- 검증 및 롤백 불가
- 실패 시 디버깅 어려움

#### ✅ 개선된 방식 (Phase 1: Manifests 지원)

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager
    hooks:
      post_deploy_manifests:
        - manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
        - manifests/issuers/cluster-issuer-letsencrypt-stg.yaml
```

**장점**:
- sbkube가 직접 처리 → 상태 추적 가능
- YamlApp처럼 검증 및 롤백 지원
- 디버깅 용이 (상세 로그)
- namespace 자동 적용

## 사용 방법

### 1. 준비

```bash
cd examples/hooks-manifests
sbkube prepare
```

### 2. 배포

```bash
# Dry-run으로 확인
sbkube deploy --dry-run

# 실제 배포
sbkube deploy
```

### 3. 결과 확인

```bash
# cert-manager 배포 확인
kubectl get pods -n cert-manager

# ClusterIssuers 확인
kubectl get clusterissuers

# 상세 정보
kubectl describe clusterissuer letsencrypt-prd
kubectl describe clusterissuer letsencrypt-stg
```

### 4. 정리

```bash
sbkube delete
```

## 파일 구조

```
examples/hooks-manifests/
├── config.yaml                             # SBKube 설정 (hooks 포함)
├── sources.yaml                            # Helm 리포지토리 설정
├── manifests/
│   └── issuers/
│       ├── cluster-issuer-letsencrypt-prd.yaml  # Production ClusterIssuer
│       └── cluster-issuer-letsencrypt-stg.yaml  # Staging ClusterIssuer
└── README.md                               # 이 파일
```

## 예상 출력

```
✨ SBKube `deploy` 시작 ✨
🚀 Deploying Helm app: cert-manager
  ✅ Helm release 'cert-manager' installed
🪝 Deploying post_deploy_manifests manifests for app 'cert-manager'...
  Applying manifest: manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
    clusterissuer.cert-manager.io/letsencrypt-prd created
  Applying manifest: manifests/issuers/cluster-issuer-letsencrypt-stg.yaml
    clusterissuer.cert-manager.io/letsencrypt-stg created
✅ post_deploy_manifests manifests deployed for 'cert-manager'
✅ Helm app deployed: cert-manager
```

## 추가 정보

- **Phase 1**: `pre_deploy_manifests`, `post_deploy_manifests` 지원
- **Phase 2** (예정): type system (manifests, inline, command)
- **Phase 3** (예정): Validation & Dependency 통합
- **Phase 4** (예정): Hook as First-class App

자세한 내용은 [docs/hooks-improvement.md](../../docs/hooks-improvement.md) 참조하세요.
