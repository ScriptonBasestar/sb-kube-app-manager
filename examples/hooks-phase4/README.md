# Hooks Phase 4 예제: Hook as First-class App

Phase 4의 핵심 기능인 **HookApp** (Hook을 독립적인 앱으로 관리)을 시연하는 예제입니다.

## Phase 4 특징

### 1. **HookApp은 독립적인 App Type**

```yaml
apps:
  setup-issuers:
    type: hook  # 독립적인 app type
    depends_on:
      - cert-manager
    labels:
      app: cert-manager-setup
      component: issuers
      managed-by: sbkube
    annotations:
      description: "Let's Encrypt ClusterIssuers setup"
      version: "1.0.0"
    tasks:
      - type: manifests
        name: deploy-issuer
        files:
          - manifests/cluster-issuer.yaml
```

**Phase 2/3과의 차이**:
- Phase 2/3: 다른 앱의 `hooks.post_deploy_tasks` 필드에 포함
- Phase 4: `type: hook`으로 독립적인 앱으로 관리

### 2. **Lifecycle 분리**

HookApp은 다른 명령어에서 자동으로 건너뜁니다:

```bash
# prepare 단계: HookApp 건너뜀
sbkube prepare --app-dir examples/hooks-phase4
# ⏭️  HookApp does not require prepare: setup-issuers

# build 단계: HookApp 건너뜀
sbkube build --app-dir examples/hooks-phase4
# ⏭️  HookApp does not require build: setup-issuers

# template 단계: HookApp 건너뜀
sbkube template --app-dir examples/hooks-phase4
# ⏭️  HookApp does not support template: setup-issuers

# deploy 단계: HookApp 실행
sbkube deploy --app-dir examples/hooks-phase4 --namespace cert-manager
# 🪝 Deploying Hook app: setup-issuers
```

### 3. **Dependency Chain 지원**

HookApp 간, 또는 HookApp과 다른 앱 간 의존성 설정:

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager

  setup-issuers:
    type: hook
    depends_on:
      - cert-manager  # Helm 앱에 의존

  create-certificates:
    type: hook
    depends_on:
      - setup-issuers  # 다른 HookApp에 의존

  verify-deployment:
    type: hook
    depends_on:
      - create-certificates  # HookApp 체인
```

**배포 순서 (topological sort)**:
```
cert-manager → setup-issuers → create-certificates → verify-deployment
```

### 4. **Phase 2/3 기능 재사용**

HookApp은 Phase 2/3의 모든 기능을 재사용합니다:

- **HookTask Types** (Phase 2):
  - `manifests`: YAML 파일 배포
  - `inline`: 인라인 리소스 생성
  - `command`: 쉘 명령어 실행

- **Validation** (Phase 3):
  ```yaml
  validation:
    kind: ClusterIssuer
    wait_for_ready: true
    timeout: 120
  ```

- **Dependency** (Phase 3):
  ```yaml
  dependency:
    depends_on:
      - deploy-issuer
    wait_for:
      - kind: Pod
        condition: Ready
  ```

- **Rollback** (Phase 3):
  ```yaml
  rollback:
    enabled: true
    on_failure: always
    commands:
      - kubectl delete clusterissuer letsencrypt-prd
  ```

### 5. **앱 레벨 vs 태스크 레벨 설정**

HookApp은 앱 레벨과 태스크 레벨 모두에서 Phase 3 기능 지원:

```yaml
apps:
  setup-issuers:
    type: hook
    tasks:
      - type: manifests
        name: deploy-issuer
        # 태스크 레벨 validation
        validation:
          kind: ClusterIssuer
          name: letsencrypt-prd
          wait_for_ready: true

    # 앱 레벨 validation (모든 태스크 완료 후)
    validation:
      kind: ClusterIssuer
      wait_for_ready: true

    # 앱 레벨 rollback (모든 태스크 실패 시)
    rollback:
      enabled: true
      on_failure: always
      commands:
        - kubectl delete clusterissuers --all
```

## 예제 구조

```
examples/hooks-phase4/
├── config.yaml                              # 메인 설정 파일
├── manifests/
│   ├── cluster-issuer-letsencrypt-prd.yaml  # Production ClusterIssuer
│   └── cluster-issuer-letsencrypt-stg.yaml  # Staging ClusterIssuer
└── README.md                                # 이 파일
```

## 예제 시나리오

이 예제는 cert-manager를 배포하고 Let's Encrypt 인증서를 자동으로 설정하는 시나리오입니다:

1. **cert-manager 배포** (HelmApp)
   - Jetstack의 공식 Helm 차트 사용
   - CRD 자동 설치 (`installCRDs: true`)

2. **ClusterIssuer 설정** (HookApp: `setup-issuers`)
   - Production 및 Staging ClusterIssuer 배포
   - 각 Issuer가 Ready 상태가 될 때까지 대기 (validation)
   - 실패 시 자동 rollback

3. **Certificate 생성** (HookApp: `create-certificates`)
   - Wildcard certificate (`*.example.com`)
   - API certificate (`api.example.com`)
   - 각 Certificate가 Ready 상태가 될 때까지 대기

4. **배포 검증** (HookApp: `verify-deployment`)
   - Certificate 상태 확인
   - TLS Secret 존재 확인
   - ClusterIssuer 상태 확인

## 실행 방법

### Prerequisites

```bash
# Kubernetes 클러스터 필요 (k3s, kind, minikube 등)
# sources.yaml에 Helm 리포지토리 추가
cat > sources.yaml << EOF
helm_repos:
  jetstack: https://charts.jetstack.io
EOF
```

### 전체 워크플로우 실행

```bash
# 모든 단계 자동 실행 (prepare → build → template → deploy)
sbkube apply --app-dir examples/hooks-phase4 --namespace cert-manager

# 또는 단계별 실행
sbkube prepare --app-dir examples/hooks-phase4
sbkube build --app-dir examples/hooks-phase4
sbkube template --app-dir examples/hooks-phase4
sbkube deploy --app-dir examples/hooks-phase4 --namespace cert-manager
```

### 예상 출력

```
✨ SBKube `deploy` 시작 ✨
📦 Deploying Helm app: cert-manager
  ✅ Helm release deployed: cert-manager

🪝 Deploying Hook app: setup-issuers
  Executing 2 tasks...
  ✅ Task: deploy-production-issuer
  ✅ Task: deploy-staging-issuer
✅ Hook app deployed: setup-issuers

🪝 Deploying Hook app: create-certificates
  Executing 2 tasks...
  ✅ Task: create-wildcard-cert
  ✅ Task: create-api-cert
✅ Hook app deployed: create-certificates

🪝 Deploying Hook app: verify-deployment
  Executing 3 tasks...
  ✅ Task: check-certificates
  ✅ Task: verify-secrets
  ✅ Task: verify-issuers
✅ Hook app deployed: verify-deployment

🎉 All apps deployed successfully!
```

### 배포 확인

```bash
# ClusterIssuer 확인
kubectl get clusterissuers
# NAME               READY   AGE
# letsencrypt-prd    True    1m
# letsencrypt-stg    True    1m

# Certificate 확인
kubectl get certificates -n default
# NAME            READY   SECRET              AGE
# wildcard-cert   True    wildcard-cert-tls   1m
# api-cert        True    api-cert-tls        1m

# Secret 확인
kubectl get secrets -n default | grep -E "(wildcard|api)-cert-tls"
# wildcard-cert-tls   kubernetes.io/tls   2      1m
# api-cert-tls        kubernetes.io/tls   2      1m
```

## Phase 2/3/4 비교

### Phase 2: Type System (2025-10-24)

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager
    hooks:
      post_deploy_tasks:  # Helm 앱에 종속
        - type: manifests
          name: deploy-issuer
          files:
            - issuer.yaml
```

**특징**:
- Hook은 다른 앱의 일부
- Helm/Yaml 앱에만 post_deploy_tasks 사용 가능

### Phase 3: Validation, Dependency, Rollback (2025-10-31)

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager
    hooks:
      post_deploy_tasks:
        - type: manifests
          name: deploy-issuer
          files:
            - issuer.yaml
          validation:        # Phase 3 추가
            kind: ClusterIssuer
            wait_for_ready: true
          dependency:        # Phase 3 추가
            depends_on:
              - other-task
          rollback:          # Phase 3 추가
            enabled: true
```

**특징**:
- Phase 2 + Validation, Dependency, Rollback 기능
- 여전히 다른 앱에 종속

### Phase 4: Hook as First-class App (2025-10-31)

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager

  setup-issuers:
    type: hook              # 독립적인 앱
    depends_on:
      - cert-manager
    tasks:                  # hooks 대신 tasks
      - type: manifests
        name: deploy-issuer
        files:
          - issuer.yaml
        validation:         # Phase 3 기능 재사용
          kind: ClusterIssuer
          wait_for_ready: true
    validation:             # 앱 레벨 validation
      kind: ClusterIssuer
      wait_for_ready: true
    rollback:               # 앱 레벨 rollback
      enabled: true
```

**특징**:
- Hook이 독립적인 앱 타입 (`type: hook`)
- 다른 앱과 동등한 관계 (depends_on으로 연결)
- Phase 2/3의 모든 기능 재사용
- 앱 레벨 lifecycle 관리 (prepare/build/template 건너뜀)
- 앱 레벨 + 태스크 레벨 Phase 3 기능 지원

## 장점

1. **명확한 분리**: Hook 로직이 독립적인 앱으로 분리되어 관리 용이
2. **재사용성**: HookApp을 여러 config에서 재사용 가능
3. **의존성 관리**: 다른 앱과 동등한 수준의 의존성 관리
4. **Lifecycle 최적화**: prepare/build/template 단계를 건너뛰어 실행 시간 단축
5. **Phase 2/3 호환**: 기존 Phase 2/3 코드를 완전히 재사용

## 주의사항

1. **HookApp은 hooks 필드를 가질 수 없음**
   - 무한 재귀 방지를 위해 HookApp에는 hooks 필드가 없음
   - 대신 tasks 필드 사용

2. **배포 순서 중요**
   - HookApp의 depends_on을 정확히 설정해야 함
   - Topological sort로 자동 정렬되지만, 순환 의존성 주의

3. **Dry-run 모드**
   - HookApp도 dry-run 모드 지원
   - 실제 리소스 생성 없이 실행 계획 확인 가능

## 다음 단계

- E2E 테스트 작성
- 문서 업데이트 (product-spec.md, commands.md)
- 실제 클러스터에서 테스트 (k3s, kind 등)

## 관련 문서

- [Phase 2 문서](../hooks/README.md)
- [Phase 3 문서](../hooks-phase3/README.md)
- [Hooks 아키텍처](../../docs/02-features/hooks-architecture.md)
