# Hooks Phase 3 예제: Validation, Dependency, Rollback

이 예제는 sbkube Hooks Phase 3 기능을 시연합니다:

- **Validation**: Task 실행 후 리소스 상태 검증
- **Dependency**: Task 간 의존성 관리 (`depends_on`, `wait_for`)
- **Rollback**: 실패 시 자동 롤백 정책

## 시나리오

cert-manager를 배포하고, ClusterIssuers, Certificate를 순차적으로 생성하며, 각 단계에서 validation과 dependency를 적용합니다.

### 배포 단계

1. **cert-manager Helm 차트 배포** (메인 앱)
2. **ClusterIssuers 배포** (manifests task)
   - `letsencrypt-prd`: 프로덕션 환경
   - `letsencrypt-stg`: 스테이징 환경
   - **Validation**: ClusterIssuer가 Ready 상태가 될 때까지 대기 (120초)
   - **Rollback**: 실패 시 ClusterIssuers 자동 삭제
3. **Certificate 생성** (inline task)
   - wildcard certificate for `*.example.com`
   - **Dependency**: ClusterIssuers가 먼저 배포되어야 함 (`depends_on`)
   - **Validation**: Certificate가 Ready 상태가 될 때까지 대기 (300초)
   - **Rollback**: 실패 시 Certificate 및 Secret 자동 삭제
4. **DNS 검증** (command task)
   - ACME challenge DNS 레코드 확인
   - **Dependency**: Certificate가 먼저 생성되어야 함 + CertificateRequest Ready 대기 (`depends_on` + `wait_for`)
   - **Retry**: 최대 5번 시도, 10초 간격
   - **on_failure: warn**: 실패해도 경고만 출력 (배포는 계속)

## 사용 방법

### 1. 전체 워크플로우 실행

```bash
sbkube apply --app-dir examples/hooks-phase3 --namespace cert-manager
```

### 2. 단계별 실행 (디버깅용)

```bash
# Step 1: prepare (Helm 차트 다운로드)
sbkube prepare --app-dir examples/hooks-phase3

# Step 2: build (Helm 차트 빌드)
sbkube build --app-dir examples/hooks-phase3

# Step 3: template (템플릿 렌더링)
sbkube template --app-dir examples/hooks-phase3 --output-dir /tmp/rendered

# Step 4: deploy (배포 + hooks 실행)
sbkube deploy --app-dir examples/hooks-phase3 --namespace cert-manager
```

### 3. Dry-run 모드

```bash
sbkube deploy --app-dir examples/hooks-phase3 --namespace cert-manager --dry-run
```

## Phase 3 기능 상세

### Validation

```yaml
validation:
  kind: ClusterIssuer            # 검증할 리소스 Kind
  name: letsencrypt-prd          # 리소스 이름 (optional)
  namespace: cert-manager        # 네임스페이스 (optional)
  wait_for_ready: true           # Ready 상태 대기
  timeout: 120                   # 타임아웃 (초)
  conditions:                    # 검증할 Condition 리스트 (optional)
    - type: Ready
      status: "True"
```

**동작**:
- `wait_for_ready: true` → `kubectl wait --for=condition=Ready` 실행
- `conditions` 지정 → 각 condition을 개별적으로 검증
- 타임아웃 내에 조건이 만족되지 않으면 **실패**

### Dependency

#### `depends_on`: Task 간 순서 보장

```yaml
dependency:
  depends_on:
    - deploy-cluster-issuers  # 이 task가 먼저 완료되어야 함
```

**동작**:
- 같은 hook 내에서 task 간 의존성 정의
- `depends_on`에 명시된 task가 완료되지 않으면 **실행 불가**

#### `wait_for`: 외부 리소스 대기

```yaml
dependency:
  wait_for:
    - kind: CertificateRequest
      namespace: default
      label_selector: "acme.cert-manager.io/order-name"
      condition: Ready
      timeout: 300
```

**동작**:
- `kubectl wait` 명령어로 외부 리소스가 특정 조건을 만족할 때까지 대기
- `label_selector` 또는 `name`으로 리소스 지정 가능

### Rollback

```yaml
rollback:
  enabled: true                  # 롤백 활성화
  on_failure: always             # 실패 시 롤백 실행 (always, manual, never)
  manifests:                     # 롤백 시 적용할 manifest 파일들 (optional)
    - manifests/cleanup.yaml
  commands:                      # 롤백 시 실행할 shell 명령어들
    - kubectl delete clusterissuer letsencrypt-prd --ignore-not-found=true
    - kubectl delete certificate wildcard-cert -n default
```

**동작**:
- **Task 실행 실패** 또는 **Validation 실패** 시 자동으로 rollback 실행
- `on_failure: always` → 자동 롤백
- `on_failure: manual` → 수동 확인 후 롤백 (현재는 스킵)
- `on_failure: never` → 롤백 비활성화

## 예상 출력

```
🪝 Executing 3 post_deploy tasks for app 'cert-manager'...

[Task 1] deploy-cluster-issuers (manifests)
  Applying manifest: manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
    clusterissuer.cert-manager.io/letsencrypt-prd created
  Applying manifest: manifests/issuers/cluster-issuer-letsencrypt-stg.yaml
    clusterissuer.cert-manager.io/letsencrypt-stg created
  🔍 Validating task result...
    Waiting for ClusterIssuer to be ready (timeout: 120s)...
✅ Validation passed: ClusterIssuer is ready

[Task 2] create-wildcard-certificate (inline)
  ⏳ Waiting for external resources...
    Task 'deploy-cluster-issuers' completed
  Applying inline content...
    certificate.cert-manager.io/wildcard-cert created
  🔍 Validating task result...
    Waiting for Certificate to be ready (timeout: 300s)...
✅ Validation passed: Certificate is ready

[Task 3] verify-dns-records (command)
  ⏳ Waiting for external resources...
    Task 'create-wildcard-certificate' completed
    Waiting for CertificateRequest to satisfy condition 'Ready' (timeout: 300s)...
✅ CertificateRequest condition 'Ready' satisfied
  Executing command: dig +short _acme-challenge.example.com TXT @8.8.8.8...
    Attempt 1/5...
⚠️  Command failed but on_failure=warn, continuing...

✅ All post_deploy tasks completed for 'cert-manager'
```

## 실패 시나리오 테스트

### Validation 실패 시

```bash
# ClusterIssuer가 120초 내에 Ready 상태가 되지 않으면
❌ Validation failed: ClusterIssuer not ready within 120s
🔄 Executing rollback for task 'deploy-cluster-issuers'...
  Executing rollback commands...
    kubectl delete clusterissuer letsencrypt-prd --ignore-not-found=true
    kubectl delete clusterissuer letsencrypt-stg --ignore-not-found=true
✅ Rollback completed
```

### Dependency 실패 시

```bash
# Task 'deploy-cluster-issuers'가 완료되지 않았는데
# Task 'create-wildcard-certificate'를 실행하려고 하면
❌ Dependency not satisfied: task 'deploy-cluster-issuers' must complete first
🔄 Executing rollback for task 'create-wildcard-certificate'...
```

## 참고 사항

- **Phase 1, 2와 호환**: Phase 3 필드 없이도 기존 hooks 동작
- **점진적 적용**: validation, dependency, rollback을 필요에 따라 선택적으로 사용 가능
- **Dry-run 지원**: `--dry-run` 플래그로 실제 배포 없이 로직 검증

## 관련 문서

- [docs/hooks/hooks-improvement.md](../../docs/hooks/hooks-improvement.md): Hooks 개선 계획 전체 문서
- Phase 1: Manifests 지원 → [examples/hooks-manifests/](../hooks-manifests/)
- Phase 2: Type System → 이 예제에서 함께 시연
- Phase 3: Validation, Dependency, Rollback → 이 예제
- Phase 4: Hook as First-class App (v1.0.0 계획)
