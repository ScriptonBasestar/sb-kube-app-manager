______________________________________________________________________

## type: Product Specification audience: Developer topics: [features, requirements, architecture, workflow, automation] llm_priority: high last_updated: 2025-01-06

# SBKube 기능 명세서

> **주의**: 이 문서는 [PRODUCT.md](../../PRODUCT.md) Section 6 (주요 기능)의 상세 버전입니다. 핵심 기능 요약은 PRODUCT.md를 우선 참조하세요.

## TL;DR

- **Purpose**: Detailed functional specifications for SBKube's deployment automation system
- **Current Version**: v0.7.0 (개발 중), v0.6.0 (안정)
- **Key Points**:
  - Core workflow: prepare→build→template→deploy pipeline
  - Multi-source integration: Helm charts, Git repos, HTTP URLs, Kustomize
  - Strong validation: Pydantic models for config validation
  - State management: SQLAlchemy-based deployment tracking
  - Extensible hooks system for deployment customization
  - LLM-friendly output: `--format llm/json/yaml` options
- **Quick Reference**: Section 1 covers workflow automation, Section 2-5 detail each component
- **Related**:
  - **상위 문서**: [PRODUCT.md](../../PRODUCT.md) - 제품 개요 (무엇을, 왜)
  - ****아키텍처**: [ARCHITECTURE.md](../../ARCHITECTURE.md) - 시스템 아키텍처 (어떻게)
  - **아키텍처**: [ARCHITECTURE.md](../10-modules/sbkube/ARCHITECTURE.md) - 시스템 설계
  - **설정 스키마**: [config-schema.md](../03-configuration/config-schema.md) - 설정 상세

## 기능 개요

### 핵심 기능 분류

1. **배포 워크플로우 자동화** (prepare-build-template-deploy)
1. **다중 소스 통합** (Helm, YAML, Git)
1. **설정 관리 시스템** (Pydantic 검증)
1. **상태 관리 시스템** (SQLAlchemy 기반)
1. **검증 시스템** (사전/사후 배포 검증)
1. **Hooks 시스템** (배포 자동화 및 커스터마이징)
1. **사용자 인터페이스** (Rich 콘솔)

## 1. 배포 워크플로우 자동화

### 1.1 prepare - 소스 준비

**목적**: 외부 소스(Helm 차트, Git 리포지토리, HTTP URL)를 로컬로 다운로드 및 준비

**지원 애플리케이션 타입**:

- `helm`: Helm 차트 배포 (remote repository 또는 local path)
- `git`: Git 리포지토리 클론
- `http`: HTTP(S) URL에서 파일 다운로드
- `kustomize`: Kustomize 디렉토리 처리

**사용자 시나리오**:

```
개발자 Alice는 Grafana 차트를 사용하려고 합니다.
1. sources.yaml에 Grafana Helm 저장소 추가
2. config.yaml에 helm 타입 앱 정의
3. sbkube prepare 실행
→ .sbkube/charts/grafana 디렉토리에 차트 다운로드 완료
```

**입력**:

- `--app-dir`: 설정 파일 디렉토리 (기본: ./config)
- `--base-dir`: 작업 디렉토리 (기본: .)
- `--app`: 특정 앱만 처리 (선택)

**출력**:

- `charts/`: Helm 차트 디렉토리
- `repos/`: Git 리포지토리 클론 디렉토리

**비기능 요구사항**:

- 네트워크 장애 시 재시도 (최대 3회)
- 진행 상태 실시간 표시
- 다운로드 캐시 지원 (중복 다운로드 방지)

### 1.2 build - 앱 빌드

**목적**: 준비된 소스를 배포 가능한 형태로 변환 및 패키징

**지원 애플리케이션 타입**:

- `helm`: Helm 차트 커스터마이징 (overrides, removes 적용)
- `git`: Git 리포지토리 특정 경로 추출
- `http`: 다운로드된 파일 정리
- `kustomize`: Kustomize 빌드 실행

**사용자 시나리오**:

```
개발자 Bob은 Helm 차트에 커스텀 values를 적용하려 합니다.
1. config.yaml에 helm 타입 앱 정의 및 values 파일 지정
2. sbkube build 실행
→ .sbkube/build/ 디렉토리에 커스터마이징된 차트 준비
```

**입력**:

- `--app-dir`, `--base-dir`, `--app` (prepare와 동일)

**출력**:

- `build/`: 빌드된 애플리케이션 아티팩트

**비기능 요구사항**:

- 파일 권한 보존
- 심볼릭 링크 처리
- 대용량 파일 스트리밍 복사

### 1.3 template - 템플릿 렌더링

**목적**: Helm 차트 및 YAML 파일에 환경별 설정 적용 및 최종 매니페스트 생성

**지원 애플리케이션 타입**:

- `helm`: Helm 차트 렌더링
- `yaml`: YAML 파일 템플릿화 (Jinja2)

**사용자 시나리오**:

```
운영자 Carol은 프로덕션 환경에 맞는 매니페스트를 생성하려 합니다.
1. values/production.yaml 준비
2. config.yaml의 helm 앱에 values 파일 지정
3. sbkube template --output-dir rendered/
→ rendered/ 디렉토리에 프로덕션용 YAML 생성
```

**입력**:

- `--output-dir`: 렌더링된 매니페스트 출력 디렉토리
- `--namespace`: 대상 네임스페이스
- `--app-dir`, `--app` (공통)

**출력**:

- `rendered/`: 렌더링된 YAML 매니페스트 파일

**비기능 요구사항**:

- Helm 템플릿 엔진 호환성
- Jinja2 템플릿 확장 지원
- 렌더링 오류 명확한 위치 표시

### 1.4 deploy - 배포 실행

**목적**: Kubernetes 클러스터에 렌더링된 매니페스트 또는 Helm 릴리스 배포

**지원 애플리케이션 타입**:

- `helm`: Helm 릴리스 설치/업그레이드
- `yaml`: YAML 매니페스트 적용 (kubectl apply)
- `action`: 사용자 정의 스크립트 실행
- `exec`: 임의 명령어 실행

**사용자 시나리오**:

```
DevOps 엔지니어 Dave는 전체 스택을 배포하려 합니다.
1. sbkube prepare && sbkube build && sbkube template
2. sbkube deploy --namespace production
→ 모든 앱이 순서대로 배포되고, 상태가 DB에 기록됨
```

**입력**:

- `--namespace`: 배포 대상 네임스페이스
- `--dry-run`: 실제 배포 없이 시뮬레이션
- `--app`, `--app-dir` (공통)
- `--kubeconfig`, `--context`: Kubernetes 클러스터 지정

**출력**:

- Kubernetes 리소스 생성/업데이트
- 배포 상태 DB 기록

**비기능 요구사항**:

- 배포 순서 보장 (의존성 그래프)
- 배포 실패 시 롤백 옵션
- Dry-run 모드 정확성
- 배포 진행률 실시간 표시

## 2. 다중 소스 통합

### 2.1 Helm 저장소 통합

**기능**: Helm 저장소에서 차트 다운로드 및 설치

**설정 예시**:

**지원 기능**:

- Helm 저장소 자동 추가 (`helm repo add`)
- 차트 버전 고정 및 업데이트
- Remote 및 Local 차트 모두 지원
- Values override 및 파일 제거 기능

### 2.2 Git 리포지토리 통합

**기능**: Git 리포지토리를 클론하여 YAML 매니페스트 또는 Helm 차트 사용

**설정 예시**:

```yaml
# sources.yaml
git_repos:
  - name: my-app
    url: https://github.com/example/k8s-manifests.git
    ref: v1.2.3

# config.yaml
apps:
  - name: app-manifests
    type: git
    specs:
      repo: my-app
      dest: manifests
```

**지원 기능**:

- 브랜치, 태그, 커밋 해시 지정
- Private 리포지토리 (SSH 키, 토큰 인증)
- 서브디렉토리 추출

### 2.3 YAML 매니페스트 직접 관리

**기능**: 로컬 YAML 파일을 직접 배포

**설정 예시**:

```yaml
apps:
  custom-resources:
    type: yaml
    files:
      - manifests/namespace.yaml
      - manifests/deployment.yaml
      - manifests/service.yaml
```

**지원 기능**:

- 여러 YAML 파일 순차 적용
- kubectl apply를 통한 배포
- 네임스페이스 오버라이드

## 3. 설정 관리 시스템

### 3.1 config.yaml 스키마

**기본 구조**:

```yaml
namespace: <string>  # 기본 네임스페이스

apps:  # 앱 정의 (dict 형식, key = 앱 이름)
  <app-name>:
    type: <string>   # 앱 타입 (helm, yaml, action, exec, git, http, kustomize)
    enabled: <bool>  # 활성화 여부 (기본: true)
    depends_on: [<string>]  # 의존성 (다른 앱 이름 목록)
    deps: [<string>]        # 앱 그룹 의존성 (v0.4.9+)
                            # - 다른 앱 그룹 디렉토리 이름 목록 (예: ["a000_infra"])
                            # - validate/apply 명령어 실행 시 배포 상태 검증
                            # - 네임스페이스 자동 감지 (v0.6.0+)
    # ... 타입별 추가 필드 (평탄화됨, specs 래퍼 없음)
```

**앱 타입별 필드**:

**`helm` 타입**:

```yaml
apps:
  redis:
    type: helm
    chart: <string>          # "repo/chart" or "./path" or "/path"
    version: <string>        # 차트 버전 (선택, remote chart만)
    values: [<string>]       # values 파일 목록
    overrides: [<string>]    # 덮어쓸 파일 목록
    removes: [<string>]      # 제거할 파일 패턴
    namespace: <string>      # 네임스페이스 오버라이드
    release_name: <string>   # Helm 릴리스 이름
```

**`yaml` 타입**:

```yaml
apps:
  manifests:
    type: yaml
    files: [<string>]        # YAML 파일 목록
    namespace: <string>
```

**`action` 타입**:

```yaml
apps:
  setup:
    type: action
    actions:                 # kubectl 액션 목록
      - type: apply          # apply, create, delete
        path: <string>
```

**`exec` 타입**:

```yaml
apps:
  post-install:
    type: exec
    commands: [<string>]     # 실행할 명령어 목록
```

**`git` 타입**:

```yaml
apps:
  manifests-repo:
    type: git
    repo: <string>           # Git repository URL
    path: <string>           # 리포지토리 내 경로 (선택)
    branch: <string>         # 브랜치 (기본: main)
    ref: <string>            # 특정 commit/tag (선택)
```

**`http` 타입**:

```yaml
apps:
  external-manifest:
    type: http
    url: <string>            # HTTP(S) URL
    dest: <string>           # 저장할 파일 경로
    headers: {<key>: <value>}  # HTTP 헤더 (선택)
```

**`kustomize` 타입**:

```yaml
apps:
  kustomize-app:
    type: kustomize
    path: <string>           # kustomization.yaml이 있는 디렉토리
```

### 3.2 sources.yaml 스키마

```yaml
# 클러스터 설정 (필수, v0.4.10+)
kubeconfig: <string>           # Kubeconfig 파일 경로 (필수)
kubeconfig_context: <string>   # Kubectl context 이름 (필수)
cluster: <string>              # 클러스터 이름 (선택, 문서화 목적)

# Helm 차트 리포지토리 (dict 형식)
helm_repos:
  <repo-name>: <string>  # 저장소 이름: URL 매핑
  # 예:
  # grafana: https://grafana.github.io/helm-charts
  # stable: https://charts.helm.sh/stable

# Git 리포지토리 (향후 지원 예정)
git:
  <repo-name>:
    url: <string>      # Git URL
    ref: <string>      # 브랜치/태그/커밋 (선택)
```

### 3.3 Pydantic 검증

**검증 항목**:

- 필수 필드 누락 검사
- 타입 불일치 검사 (예: namespace는 문자열)
- 값 범위 검사 (예: enabled는 true/false만)
- 커스텀 검증 (예: Helm 차트 버전 형식)

**오류 메시지 예시**:

```
ValidationError: config.yaml
  apps.redis.chart: field required
  apps.backend.type: invalid app type 'helmm' (did you mean 'helm'?)
  apps.database.version: version requires remote chart (repo/chart format)
```

## 4. 상태 관리 시스템

### 4.1 배포 상태 추적

**저장 정보**:

- 배포 시각 (타임스탬프)
- 클러스터 정보 (컨텍스트, 네임스페이스)
- 앱 이름 및 릴리스 이름
- 배포 결과 (성공/실패)
- Helm 차트 버전 (해당 시)
- 설정 파일 해시 (변경 추적)

**데이터베이스 스키마**:

```sql
CREATE TABLE deployment_history (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME,
  cluster_context TEXT,
  namespace TEXT,
  app_name TEXT,
  release_name TEXT,
  status TEXT,  -- success, failed, rollback
  metadata JSON
);
```

### 4.2 히스토리 조회

**명령어**: `sbkube history`

**필터링 옵션**:

- `--cluster <context>`: 특정 클러스터
- `--namespace <name>`: 특정 네임스페이스
- `--app <name>`: 특정 앱
- `--limit <N>`: 최근 N개

**출력 형식**:

```
┌─────────────────────┬──────────────┬───────────┬────────┐
│ Timestamp           │ App          │ Namespace │ Status │
├─────────────────────┼──────────────┼───────────┼────────┤
│ 2025-10-20 10:30:00 │ redis-deploy │ prod      │ ✅     │
│ 2025-10-19 15:20:00 │ redis-deploy │ prod      │ ✅     │
└─────────────────────┴──────────────┴───────────┴────────┘
```

### 4.3 롤백 지원

**명령어**: `sbkube rollback --deployment-id <ID>`

**롤백 프로세스**:

1. 이전 배포 상태 조회 (설정 해시)
1. 해당 시점의 설정 파일 복원 (선택)
1. Helm 릴리스 롤백 또는 YAML 재적용
1. 새로운 배포 기록 생성 (타입: rollback)

## 5. 검증 시스템

### 5.1 설정 파일 검증 (validate 명령어)

**검증 항목**:

- **구문 검증**: YAML 파싱 오류
- **스키마 검증**: Pydantic 모델 일치성
- **논리 검증**: 앱 이름 중복, 순환 의존성
- **리소스 검증**: Helm 저장소/차트 존재 여부 (선택)
- **앱 그룹 의존성 검증**: deps 필드에 선언된 의존 앱 그룹 배포 상태 확인 (v0.6.0+)

**앱 그룹 의존성 검증**:

`deps` 필드에 선언된 의존 앱 그룹이 실제로 배포되었는지 확인합니다. 이 검증은 배포 히스토리 데이터베이스(`.sbkube/deployments.db`)를 조회하여 수행됩니다.

**네임스페이스 자동 감지** (v0.6.0+):

- 의존 앱 그룹이 어떤 네임스페이스에 배포되었는지 자동으로 감지
- 현재 앱과 다른 네임스페이스에 배포된 의존성도 올바르게 감지
- 예: 인프라 앱(`a000_infra`)은 `infra` 네임스페이스에, 데이터베이스 앱(`a101_data_rdb`)은 `postgresql` 네임스페이스에 배포된 경우에도 정상 작동

**검증 동작**:

- `validate` 명령어: 경고 출력 (non-blocking, 배포는 차단하지 않음)
- `apply` 명령어: 오류 출력 및 배포 차단 (blocking)

**사용자 시나리오**:

```
개발자 Eve는 설정 파일을 수정한 후 배포 전 검증하려 합니다.
1. sbkube validate --app-dir config
→ 오류 발견: apps[2].type: 'helmm' (오타)
2. 수정 후 재검증
→ ✅ All configurations are valid
→ ⚠️ Dependency check: a000_infra is not deployed

# 의존성이 다른 네임스페이스에 배포된 경우 (v0.6.0+):
3. sbkube validate --app-dir a101_data_rdb
→ ✅ Pydantic validation passed
→ ✅ Dependency check: a000_infra deployed at 2025-10-30T10:00:00 in namespace 'infra'
```

### 5.2 배포 전 검증 (pre-deployment)

**자동 실행**: deploy 명령어 실행 시 자동

**검증 항목**:

- Kubernetes 클러스터 연결 확인
- 대상 네임스페이스 존재 여부
- RBAC 권한 확인 (가능 시)
- 의존성 도구 설치 확인 (helm, kubectl, git)
- 디스크 공간 확인

**실패 시 동작**: 배포 중단 및 명확한 오류 메시지

### 5.3 배포 후 검증 (post-deployment)

**자동 실행**: deploy 성공 후 (선택적)

**검증 항목**:

- Pod 상태 확인 (Running)
- Service 엔드포인트 확인
- Helm 릴리스 상태 (deployed)
- 커스텀 헬스체크 (사용자 정의 스크립트)

## 6. Hooks 시스템

### 6.1 개요

**목적**: 명령어 실행 전후 및 앱 배포 전후에 커스텀 스크립트를 실행하여 배포 워크플로우를 자동화하고 커스터마이징

**핵심 가치**:

- 배포 자동화 확장
- 외부 시스템 통합
- 검증 및 알림
- 데이터베이스 백업 및 마이그레이션

### 6.2 명령어 수준 Hooks (Command-level)

**정의**: 전역 훅으로 모든 앱 배포에 적용

**지원 명령어**:

- `prepare`: 소스 준비 전후
- `build`: 빌드 전후
- `deploy`: 배포 전후

**지원 단계**:

- `pre`: 명령어 실행 전
- `post`: 명령어 실행 후 (성공 시)
- `on_failure`: 명령어 실패 시

**설정 예시**:

```yaml
namespace: production

hooks:
  deploy:
    pre:
      - echo "=== Deployment started at $(date) ==="
      - kubectl cluster-info
    post:
      - echo "=== Deployment completed at $(date) ==="
      - ./scripts/notify-slack.sh "Deployment completed"
    on_failure:
      - echo "=== Deployment failed at $(date) ==="
      - ./scripts/rollback.sh
```

**사용자 시나리오**:

```
DevOps 엔지니어 Frank는 모든 배포 전에 클러스터 상태를 확인하고,
배포 완료 후 Slack으로 알림을 받고 싶습니다.

1. config.yaml에 전역 hooks 설정
2. sbkube deploy --app-dir production
   → Pre-deploy hook: 클러스터 상태 확인
   → 앱 배포 진행
   → Post-deploy hook: Slack 알림 발송
3. 팀원들이 Slack에서 배포 완료 확인
```

### 6.3 앱 수준 Hooks (App-level)

**정의**: 개별 앱에 특화된 훅

**지원 타입**:

- `pre_prepare`: 앱 준비 전
- `post_prepare`: 앱 준비 후
- `pre_build`: 앱 빌드 전
- `post_build`: 앱 빌드 후
- `pre_deploy`: 앱 배포 전
- `post_deploy`: 앱 배포 후 (성공 시)
- `on_deploy_failure`: 앱 배포 실패 시

**설정 예시**:

```yaml
apps:
  database:
    type: helm
    chart: prometheus-community/kube-state-metrics
    hooks:
      pre_deploy:
        - echo "Creating database backup..."
        - ./scripts/backup-db.sh
      post_deploy:
        - echo "Waiting for database to be ready..."
        - kubectl wait --for=condition=ready pod -l app=postgresql --timeout=300s
        - echo "Running database migrations..."
        - ./scripts/migrate.sh
      on_deploy_failure:
        - echo "Database deployment failed, restoring backup..."
        - ./scripts/restore-backup.sh
```

**사용자 시나리오**:

```
개발자 Grace는 PostgreSQL 배포 시 자동으로 백업을 생성하고,
배포 후 마이그레이션을 실행하고 싶습니다.

1. database 앱에 hooks 설정
2. sbkube deploy --app-dir production --app database
   → Pre-deploy hook: DB 백업 생성
   → PostgreSQL Helm 차트 배포
   → Post-deploy hook: Pod 준비 대기 → 마이그레이션 실행
3. 데이터베이스가 새 스키마로 업데이트됨
```

### 6.4 환경변수 주입

**자동 주입 변수** (앱별 훅):

- `SBKUBE_APP_NAME`: 현재 앱 이름
- `SBKUBE_NAMESPACE`: 배포 네임스페이스
- `SBKUBE_RELEASE_NAME`: Helm 릴리스 이름

**사용 예시**:

```yaml
apps:
  backend:
    type: helm
    chart: ./charts/backend
    hooks:
      post_deploy:
        - echo "Deployed $SBKUBE_APP_NAME to $SBKUBE_NAMESPACE"
        - kubectl get pods -l release=$SBKUBE_RELEASE_NAME
```

### 6.5 실행 순서

**deploy 명령어 실행 시**:

```
1. 전역 pre-deploy 훅 실행
2. 앱 A:
   2.1. 앱 A pre_deploy 훅 실행
   2.2. 앱 A 배포
   2.3. 앱 A post_deploy 훅 실행 (성공) 또는 on_deploy_failure (실패)
3. 앱 B:
   3.1. 앱 B pre_deploy 훅 실행
   3.2. 앱 B 배포
   3.3. 앱 B post_deploy 훅 실행 (성공) 또는 on_deploy_failure (실패)
4. 전역 post-deploy 훅 실행 (모두 성공) 또는 on_failure (하나라도 실패)
```

### 6.6 주요 기능

**타임아웃 관리**:

- 기본 타임아웃: 300초 (5분)
- 훅이 타임아웃되면 실패로 처리

**Dry-run 지원**:

- `--dry-run` 모드에서는 훅 실행 명령어만 표시
- 실제 실행하지 않음

**에러 처리**:

- 훅 실패 시 배포 중단
- 명확한 오류 메시지 및 종료 코드 표시

**Rich 콘솔 출력**:

```
🪝 Executing pre-deploy hook for app 'database'...
  ▶ Running: ./scripts/backup-db.sh
    Database backup created: /backups/db-20251030-143022.sql
✅ pre-deploy hook for 'database' completed successfully
```

### 6.7 고급 기능 (Phase 1-4)

**Phase 1: Manifests** (v0.7.0+):

- `pre_deploy_manifests`, `post_deploy_manifests`
- SBKube가 자동으로 YAML 파일 배포
- `kubectl apply` 명령어 불필요

**Phase 2: Tasks** (v0.8.0+):

- `pre_deploy_tasks`, `post_deploy_tasks`
- 타입 시스템: `manifests`, `inline`, `command`
- Inline YAML 지원

**Phase 3: Validation/Dependency/Rollback** (v0.8.0+):

- 실행 결과 자동 검증
- Task 간 의존성 관리
- 실패 시 자동 롤백

**Phase 4: HookApp** (v0.8.0+):

- Hook을 First-class App으로 관리 (`type: hook`)
- 독립적이고 재사용 가능한 Hook
- 다른 앱과 동일한 lifecycle 관리

**참고 문서**:

- [Hooks 레퍼런스](../02-features/hooks-reference.md) - 전체 Hook 타입 및 환경 변수
- [Hooks 상세 가이드](../02-features/hooks.md) - 실전 예제 및 Best Practices
- [Hooks 마이그레이션 가이드](../02-features/hooks-migration-guide.md) - Phase 간 전환 방법

### 6.8 Helm Hooks와의 차이

| 특성 | SBKube Hooks | Helm Hooks | |------|--------------|------------| | **실행 위치** | 로컬 머신 | Kubernetes 클러스터 | | **실행
주체** | SBKube CLI | Helm/Kubernetes | | **목적** | 배포 자동화, 외부 시스템 통합 | 클러스터 내 작업 | | **사용 예시** | 백업, 알림, GitOps 통합 | DB
마이그레이션 Job |

**함께 사용하기**:

- SBKube hooks: 로컬 작업 (백업, 알림)
- Helm hooks: 클러스터 내 작업 (초기화 Job)

## 7. 사용자 인터페이스

### 7.1 Rich 콘솔 출력

**로그 레벨별 색상**:

- 🔵 INFO: 일반 정보 (파란색)
- 🟡 WARNING: 경고 (노란색)
- 🔴 ERROR: 오류 (빨간색)
- 🟢 SUCCESS: 성공 (초록색)
- 🟣 DEBUG: 디버깅 정보 (보라색, --verbose 시)

**테이블 형태 출력**:

- 배포 상태 목록
- 앱 목록 및 타입
- 히스토리 조회 결과

**진행 상태 표시**:

```
[prepare] Processing apps... ━━━━━━━━━━━━━━━━━━━━━━ 3/5 (60%)
  ✅ redis-pull
  ✅ postgres-pull
  ⏳ nginx-pull (downloading...)
```

### 6.2 명령어 옵션

**전역 옵션** (모든 명령어에 적용):

```bash
sbkube [전역옵션] <명령어> [명령어옵션]

전역 옵션:
  --kubeconfig <경로>     # Kubernetes 설정 파일
  --context <이름>        # Kubernetes 컨텍스트
  --namespace <이름>      # 기본 네임스페이스
  -v, --verbose          # 상세 로깅
```

**명령어별 옵션**:

- prepare/build/template/deploy:
  - `--app-dir <경로>`: 설정 디렉토리
  - `--base-dir <경로>`: 작업 디렉토리
  - `--app <이름>`: 특정 앱만 처리
- deploy:
  - `--dry-run`: 시뮬레이션 모드
- template:
  - `--output-dir <경로>`: 출력 디렉토리

## 8. 비기능 요구사항

### 8.1 성능

- 앱 100개 기준 전체 워크플로우 10분 이내 (네트워크 속도 의존)
- 설정 파일 검증 1초 이내
- 상태 조회 쿼리 100ms 이내

### 7.2 안정성

- 네트워크 장애 시 자동 재시도
- 부분 배포 실패 시 명확한 오류 보고
- 상태 DB 손상 시 복구 메커니즘

### 7.3 사용성

- 명확한 오류 메시지 (원인 및 해결 방법 포함)
- 진행 상태 실시간 피드백
- 도움말 및 예제 제공

### 7.4 확장성

- 새로운 앱 타입 추가 용이
- 플러그인 시스템 (향후 지원)
- 커스텀 검증 로직 추가 가능

## 9. 사용자 스토리

### 스토리 1: 빠른 Helm 차트 배포

**As a** DevOps 엔지니어, **I want to** Helm 차트를 설정 파일로 정의하고 한 번에 배포 **So that** 수동 helm install 명령어 반복을 피할 수 있다.

**Acceptance Criteria**:

- [ ] sources.yaml에 Helm 저장소 추가
- [ ] config.yaml에 helm 및 helm 정의
- [ ] sbkube prepare && sbkube deploy 실행으로 배포 완료
- [ ] Helm 릴리스가 클러스터에 생성됨

### 스토리 2: Git 리포지토리 기반 배포

**As a** 개발자, **I want to** Git 리포지토리의 YAML 매니페스트를 자동으로 배포 **So that** 수동 git clone 및 kubectl apply를 반복하지 않는다.

**Acceptance Criteria**:

- [ ] sources.yaml에 Git 리포지토리 추가
- [ ] config.yaml에 pull-git 및 yaml 정의
- [ ] 특정 브랜치/태그 지정 가능
- [ ] sbkube 워크플로우로 자동 배포

### 스토리 3: 환경별 설정 관리

**As a** SRE, **I want to** 동일한 설정 파일로 개발/스테이징/프로덕션 환경 배포 **So that** 환경별 일관성을 보장할 수 있다.

**Acceptance Criteria**:

- [ ] 환경별 values 파일 작성 (values/dev.yaml, values/prod.yaml)
- [ ] config.yaml에서 values 파일 참조
- [ ] --namespace 옵션으로 환경 구분
- [ ] 배포 히스토리에서 환경별 조회 가능

### 스토리 4: 배포 히스토리 및 롤백

**As a** 운영자, **I want to** 배포 히스토리를 조회하고 이전 버전으로 롤백 **So that** 배포 실패 시 빠르게 복구할 수 있다.

**Acceptance Criteria**:

- [ ] sbkube history로 배포 기록 조회
- [ ] 클러스터, 네임스페이스, 앱별 필터링
- [ ] sbkube rollback으로 이전 배포로 복원
- [ ] 롤백도 히스토리에 기록됨

______________________________________________________________________

## 관련 문서

- **상위 문서**: [PRODUCT.md](../../PRODUCT.md) - 제품 개요 (무엇을, 왜)
- ****아키텍처**: [ARCHITECTURE.md](../../ARCHITECTURE.md) - 시스템 아키텍처 (어떻게)
- **제품 정의**: [PRODUCT.md](../../PRODUCT.md) - 제품 개요 (무엇을, 왜)
- **아키텍처**: [../10-modules/sbkube/ARCHITECTURE.md](../10-modules/sbkube/ARCHITECTURE.md) - 시스템 설계
- **명령어 참조**: [../02-features/commands.md](../02-features/commands.md) - 전체 명령어

______________________________________________________________________

**문서 버전**: 1.1 **마지막 업데이트**: 2025-01-06 **담당자**: archmagece@users.noreply.github.com
