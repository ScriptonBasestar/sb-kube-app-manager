# 📋 SBKube 명령어 상세 가이드

SBKube의 모든 명령어에 대한 상세한 사용법과 옵션을 설명합니다.

______________________________________________________________________

## 🚀 빠른 참조 (Quick Reference)

### 상황별 명령어 가이드

- **🎬 새 프로젝트 시작** — `sbkube init` 설정 파일 및 디렉토리 구조 생성

- **⭐ 전체 배포** — `sbkube apply` 가장 많이 사용 (prepare→build→template→deploy)

- **🔍 배포 전 확인** — `sbkube apply --dry-run` 실제 배포 없이 계획만 확인

- **🏥 문제 진단** — `sbkube doctor` 시스템 종합 진단 및 문제 해결

- **✅ 설정 검증** — `sbkube validate` config.yaml 유효성 검사

- **🗑️ 리소스 삭제** — `sbkube delete --dry-run` 삭제 전 대상 확인

- **♻️ 릴리스 업그레이드** — `sbkube upgrade` Helm 릴리스 업그레이드

### 워크플로우별 명령어 조합

#### 📦 처음 시작하기

```bash
sbkube init                    # 1. 프로젝트 초기화
sbkube doctor                  # 2. 환경 진단
sbkube apply --dry-run         # 3. 배포 계획 확인
sbkube apply                   # 4. 실제 배포
```

#### 🔄 일상적인 배포

```bash
sbkube validate               # 1. 설정 검증
sbkube apply --profile production  # 2. 프로덕션 배포
```

#### 🐛 문제 해결

```bash
sbkube doctor --detailed      # 1. 상세 진단
```

#### 🧹 정리 및 재배포

```bash
sbkube delete --dry-run       # 1. 삭제 대상 확인
sbkube delete                 # 2. 리소스 삭제
sbkube apply                  # 3. 재배포
```

### 명령어 카테고리

SBKube는 명령어를 사용 목적에 따라 5가지 카테고리로 구분합니다. `sbkube --help` 실행 시 카테고리별로 그룹화되어 표시됩니다.

#### 🔄 핵심 워크플로우

배포 프로세스의 4단계를 개별적으로 실행할 수 있습니다:

- `prepare` - 소스 다운로드 (Helm 차트, Git 리포지토리 등)
- `build` - 애플리케이션 빌드 및 커스터마이징
- `template` - Kubernetes YAML 렌더링
- `deploy` - 클러스터 배포

#### ⚡ 통합 명령어

- `apply` ⭐ - 전체 워크플로우 자동 실행 (prepare → build → template → deploy)

#### 📊 상태 관리 (v0.6.0+)

배포 후 상태 확인 및 복구:

- `status` ⭐ - 클러스터 및 앱 상태 확인 (실시간 + 캐싱)
- `history` ⭐ - 배포 히스토리 조회 및 비교 (diff, values-diff)
- `rollback` - 이전 배포로 롤백

#### 🔧 업그레이드/삭제

- `upgrade` - Helm 릴리스 업그레이드
- `delete` - 리소스 삭제

#### 🛠️ 유틸리티

- `init` - 프로젝트 초기화 (최초 1회)
- `validate` - 설정 파일 검증 (config.yaml, sources.yaml)
- `doctor` - 시스템 종합 진단 (kubectl, helm, 네트워크 등)
- `version` - 버전 정보

### 명령어 관계 다이어그램

```
                          SBKube 워크플로우

┌──────────────────────────────────────────────────────────────┐
│                      🎬 시작                                  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │  init   │ ← 최초 1회 실행
                    └────┬────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
┌───▼───┐           ┌───▼───┐           ┌───▼───┐
│doctor │           │validate│          │ apply │ ⭐ 가장 많이 사용
└───┬───┘           └───┬───┘           └───┬───┘
    │                   │                   │
    │ 문제 발견?         │ 검증 성공?         │ 4단계 자동 실행:
    │                   │                   │
┌───▼───┐           ┌───▼───┐           ┌───▼──────────┐
│  fix  │           │ apply │           │ 1. prepare   │
└───────┘           └───────┘           │ 2. build     │
                                        │ 3. template  │
또는 수동 단계별 실행:                    │ 4. deploy    │
                                        └───┬──────────┘
┌─────────┐                                 │
│ prepare │──► 소스 다운로드                 │
└────┬────┘                                 │
     │                                      │
┌────▼────┐                                 │
│  build  │──► 차트 커스터마이징              │
└────┬────┘                                 │
     │                                      │
┌────▼────┐                                 │
│template │──► 매니페스트 렌더링              │
└────┬────┘                                 │
     │                                      │
┌────▼────┐                                 │
│ deploy  │──► 클러스터 배포                  │
└────┬────┘                                 │
     │                                      │
     └──────────────────┬───────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    ┌───▼───┐      ┌───▼────┐     ┌───▼────┐
    │upgrade│      │ delete │     │ state  │
    └───────┘      └────────┘     └───┬────┘
                                       │
                   ┌───────────────────┼─────────┐
                   │                   │         │
               ┌───▼────┐              │     ┌──▼────┐
               │history │              │     │rollback│
               └────────┘              │     └────────┘
                                       │

보조 도구:
  📖 history   - 실행 기록 확인
```

### 명령어 간 의존성

```
init
 ├─ 생성: config.yaml, sources.yaml
 └─ 사용: prepare, build, template, deploy, apply

doctor
 └─ 체크: kubectl, helm, config files

apply (통합 명령어)
 ├─ 실행: prepare → build → template → deploy
 └─ 기록: history, state

validate
 ├─ 검증: config.yaml, sources.yaml
 └─ 선행: apply, deploy

prepare
 ├─ 입력: sources.yaml, config.yaml
 └─ 출력: .sbkube/charts/, .sbkube/repos/

build
 ├─ 입력: .sbkube/charts/, config.yaml (overrides, removes)
 └─ 출력: .sbkube/build/

template
 ├─ 입력: .sbkube/build/, config.yaml (values)
 └─ 출력: .sbkube/rendered/

deploy
 ├─ 입력: .sbkube/build/, .sbkube/rendered/, config.yaml
 ├─ 실행: helm install, kubectl apply
 └─ 기록: state (배포 상태)

upgrade
 ├─ 대상: Helm 릴리스만
 └─ 실행: helm upgrade --install

delete
 ├─ 대상: helm 릴리스, yaml 리소스, action 스크립트
 └─ 옵션: --dry-run (미리보기)

state
 ├─ 조회: list, history, show
 └─ 실행: rollback

history
 └─ 조회: .sbkube/runs/ (apply 실행 기록)
```

______________________________________________________________________

## 🌐 전역 옵션

모든 명령어에서 사용할 수 있는 전역 옵션:

```bash
sbkube [전역옵션] <명령어> [명령어옵션]
```

### 전역 옵션

- `--kubeconfig <경로>` - Kubernetes 설정 파일 경로 (환경변수: `KUBECONFIG`)
- `--context <이름>` - 사용할 Kubernetes 컨텍스트 이름
- `--namespace <네임스페이스>` - 작업을 수행할 기본 네임스페이스 (환경변수: `KUBE_NAMESPACE`)
- `-v, --verbose` - 상세 로깅 활성화

### 기본 실행

```bash
# Kubernetes 설정 정보 표시
sbkube

# 특정 컨텍스트로 명령어 실행
sbkube --context prod-cluster --namespace monitoring deploy
```

______________________________________________________________________

## 🎬 init - 프로젝트 초기화

새 SBKube 프로젝트를 초기화하고 기본 설정 파일 구조를 생성합니다.

### 📋 사용법

```bash
sbkube init [옵션]
```

### 🎛️ 옵션

- `--template [basic|web-app|microservice]` - 사용할 템플릿 (기본값: `basic`)
- `--name <이름>` - 프로젝트 이름 (기본값: 현재 디렉토리명)
- `--non-interactive` - 대화형 입력 없이 기본값으로 생성
- `--force` - 기존 파일이 있어도 덮어쓰기

### 📁 생성되는 파일

- `config.yaml` - 애플리케이션 설정 파일
- `sources.yaml` - Helm 저장소 및 소스 설정
- `.sbkube/` - SBKube 작업 디렉토리

### 🎯 템플릿 종류

- **`basic`** - 기본 구조 (Helm 차트 1개)
- **`web-app`** - 웹 애플리케이션 (프론트엔드 + 백엔드)
- **`microservice`** - 마이크로서비스 아키텍처 (여러 서비스)

### 💡 사용 예제

```bash
# 기본 템플릿으로 대화형 초기화
sbkube init

# 특정 템플릿 사용
sbkube init --template web-app

# 프로젝트명 지정
sbkube init --name my-project --template microservice

# 비대화형 모드 (CI/CD)
sbkube init --non-interactive --force
```

### 💡 팁

- **최초 실행**: 프로젝트 시작 시 가장 먼저 실행하는 명령어
- **기존 프로젝트**: `--force` 옵션 사용 시 기존 파일 백업 권장
- **템플릿 커스터마이징**: 생성된 파일을 수정하여 프로젝트에 맞게 조정

______________________________________________________________________

## 🔄 apply - 통합 워크플로우 실행 ⭐

prepare → build → template → deploy 4단계를 한 번에 자동 실행합니다.

> **💡 가장 많이 사용하는 명령어**: 일반적인 배포 시나리오에서 가장 자주 사용됩니다.

### 📋 사용법

```bash
sbkube apply [옵션]
```

### 🎛️ 주요 옵션

**단계 제어:**

- `--from-step <단계>` - 시작할 단계 지정 (prepare/build/template/deploy)
- `--to-step <단계>` - 종료할 단계 지정 (prepare/build/template/deploy)
- `--only <단계>` - 특정 단계만 실행

**환경 설정:**

- `--profile <환경>` - 환경 프로파일 (development/staging/production)
- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `.`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 사용할 설정 파일 이름
- `--app <앱이름>` - 대상 앱 이름 (미지정시 전체)

**재시작 및 복구:**

- `--continue-from <단계>` - 지정한 단계부터 재시작
- `--retry-failed` - 실패한 앱만 재시도
- `--resume` - 마지막 실패 지점부터 자동 재개

**의존성 관리:**

- `--skip-deps-check` - 앱 그룹 의존성 검증 건너뛰기 (강제 배포 시)

**기타:**

- `--dry-run` - 실행 계획만 표시 (실제 실행 안 함)
- `--no-progress` - 진행률 표시 비활성화

### 💡 사용 예제

```bash
# 전체 워크플로우 실행 (가장 일반적)
sbkube apply

# 특정 앱만 실행
sbkube apply --app web-frontend

# 환경별 배포
sbkube apply --profile production
sbkube apply --profile development

# 단계별 실행 제어
sbkube apply --from-step template              # template부터 실행
sbkube apply --to-step build                   # build까지만 실행
sbkube apply --only template                   # template만 실행
sbkube apply --from-step build --to-step template  # build와 template만

# 실패 후 재시작
sbkube apply --continue-from template          # template 단계부터 재시작
sbkube apply --retry-failed                    # 실패한 앱만 다시 시도
sbkube apply --resume                          # 자동으로 재시작 지점 탐지

# Dry-run으로 확인
sbkube apply --dry-run                         # 실행 계획만 확인
```

### 🎯 특징

- **자동화**: 4단계를 수동으로 실행할 필요 없음
- **스마트 재시작**: 실패 지점부터 재개 가능
- **환경별 관리**: 프로파일 시스템으로 환경별 설정 분리
- **진행 상황 표시**: 실시간 단계별 진행률 표시
- **상태 추적**: `.sbkube/runs/`에 실행 상태 저장
- **의존성 자동 검증**: `config.yaml`의 `deps` 필드에 명시된 앱 그룹 배포 상태를 자동으로 확인하여 미배포된 의존성이 있으면 배포 중단

### ⚠️ 참고

- Kubernetes 클러스터 연결 및 Helm 설치 필요
- 각 단계의 상세 옵션은 개별 명령어 참조 (prepare, build, template, deploy)
- 실패 시 `.sbkube/runs/`에서 실행 기록 확인 가능

______________________________________________________________________

## 🔧 prepare - 소스 준비

외부 소스(Helm 저장소, Git 저장소, OCI 차트)를 로컬 환경에 다운로드하고 준비합니다.

### 📋 사용법

```bash
sbkube prepare [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `.`)
- `--source <파일>` - 소스 설정 파일 (기본값: `sources.yaml`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 사용할 설정 파일 이름 (app-dir 내부)
- `--app <앱이름>` - 준비할 특정 앱 이름 (미지정시 모든 앱)
- `--force` - 기존 리소스 덮어쓰기 (차트/리포지토리 재다운로드)

### 📁 생성되는 디렉토리

- `.sbkube/charts/` - 다운로드된 Helm 차트
- `.sbkube/repos/` - 클론된 Git 저장소

### 🔄 멱등성 (Idempotency)

**v0.4.6부터**: `prepare` 명령어는 **멱등성**을 보장합니다.

- **기본 동작**: 차트/리포지토리가 이미 존재하면 **skip** (다운로드하지 않음)
- **강제 재다운로드**: `--force` 옵션 사용 시 기존 리소스 삭제 후 재다운로드
- **재실행 안전성**: `sbkube apply` 또는 `prepare` 재실행 시 오류 없이 성공

**동작 방식**:

```bash
# 첫 실행: 차트 다운로드
$ sbkube prepare
📦 Preparing Helm app: grafana
  Pulling chart: grafana/grafana → .sbkube/charts/grafana
✅ Helm app prepared: grafana

# 재실행: 기존 차트 skip
$ sbkube prepare
📦 Preparing Helm app: grafana
⏭️  Chart already exists, skipping: grafana
    Use --force to re-download
✅ Helm app prepared: grafana

# 강제 재다운로드
$ sbkube prepare --force
📦 Preparing Helm app: grafana
⚠️  Removing existing chart (--force): .sbkube/charts/grafana
  Pulling chart: grafana/grafana → .sbkube/charts/grafana
✅ Helm app prepared: grafana
```

### 💡 사용 예제

```bash
# 기본 소스 준비 (멱등성 보장)
sbkube prepare

# 특정 앱만 준비
sbkube prepare --app nginx-app

# 커스텀 설정으로 준비
sbkube prepare --app-dir my-config --source my-sources.yaml

# 기존 차트/리포지토리 강제 재다운로드
sbkube prepare --force

# 특정 앱만 강제 재다운로드
sbkube prepare --app redis --force
```

______________________________________________________________________

## 🔨 build - 앱 빌드

준비된 소스를 기반으로 배포 가능한 형태로 빌드합니다.

### 📋 사용법

```bash
sbkube build [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `.`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 사용할 설정 파일 이름
- `--app <앱이름>` - 빌드할 특정 앱 이름

### 📁 생성되는 디렉토리

- `.sbkube/build/` - 빌드된 애플리케이션 아티팩트

### 🎯 지원 앱 타입

- **`helm`** - Helm 차트 준비
- **`git`** - Git 소스 준비
- **`http`** - 로컬 파일 복사
- **`yaml`** - YAML 매니페스트 준비

### 💡 사용 예제

```bash
# 모든 앱 빌드
sbkube build

# 특정 앱만 빌드
sbkube build --app database

# 커스텀 설정으로 빌드
sbkube build --app-dir production --config-file prod-config.yaml
```

### ⚠️ Override 디렉토리 사용 시 주의사항

**중요**: Override 파일은 `config.yaml`에 **명시적으로** 나열해야 적용됩니다.

#### ❌ 잘못된 사용법 (Override 무시됨)

```yaml
# config.yaml
apps:
  myapp:
    type: helm
    chart: ingress-nginx/ingress-nginx
    # overrides 필드 없음! ← 문제
```

```
# 디렉토리 구조
overrides/
  myapp/
    templates/
      configmap.yaml  # ❌ config.yaml에 명시 안 되어 무시됨
```

**빌드 결과**: overrides/ 디렉토리가 있어도 경고 메시지만 표시되고 적용되지 않음

```
⚠️  Override directory found but not configured: myapp
    Location: overrides/myapp
    Files:
      - templates/configmap.yaml
    💡 To apply these overrides, add to config.yaml:
       myapp:
         overrides:
           - templates/configmap.yaml
```

#### ✅ 올바른 사용법 (Override 적용됨)

```yaml
# config.yaml
apps:
  myapp:
    type: helm
    chart: ingress-nginx/ingress-nginx
    overrides:
      - templates/configmap.yaml     # ✅ 명시적으로 나열
      - files/custom-config.txt      # ✅ files 디렉토리도 포함
```

**빌드 결과**: overrides가 .sbkube/build/ 디렉토리에 적용됨

```
🔨 Building Helm app: myapp
  Copying chart: .sbkube/charts/nginx/nginx → .sbkube/build/myapp
  Applying 2 overrides...
    ✓ Override: templates/configmap.yaml
    ✓ Override: files/custom-config.txt
✅ Helm app built: myapp
```

#### 📌 Override의 역할: 덮어쓰기 + 새 파일 추가

Override는 두 가지 용도로 사용됩니다:

**1. 기존 파일 덮어쓰기**

```yaml
overrides:
  - templates/deployment.yaml    # 차트의 기존 파일 교체
  - values.yaml                  # 기본 values.yaml 교체
```

**2. 새 파일 추가**

```yaml
overrides:
  - templates/new-configmap.yaml      # 차트에 없던 새 템플릿
  - templates/custom-service.yaml     # 차트에 없던 새 서비스
  - files/additional-config.txt       # 차트에 없던 새 파일
```

#### 🔍 .Files.Get 사용 시 주의사항

Helm 템플릿에서 `{{ .Files.Get "files/..." }}`를 사용하는 경우:

**1. files 디렉토리도 override에 포함 필수**

```yaml
# overrides/myapp/templates/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  config.toml: |-
{{ .Files.Get "files/config.toml" | indent 4 }}  # ← files/ 참조
```

```yaml
# config.yaml에 files도 명시!
apps:
  myapp:
    type: helm
    chart: my-chart
    overrides:
      - templates/configmap.yaml
      - files/config.toml          # ← 필수! 없으면 .Files.Get 실패
```

**2. 경로는 차트 루트 기준**

```
.sbkube/build/myapp/            # 차트 루트
  ├── Chart.yaml
  ├── templates/
  │   └── configmap.yaml        # .Files.Get을 사용하는 템플릿
  └── files/
      └── config.toml           # ← .Files.Get "files/config.toml"
```

#### 🎯 디렉토리 구조 예제

```
app-dir/
├── config.yaml                 # overrides 필드에 명시
├── overrides/
│   └── myapp/                  # 앱 이름과 일치해야 함
│       ├── templates/
│       │   ├── deployment.yaml      # 기존 파일 덮어쓰기
│       │   └── new-config.yaml      # 새 파일 추가
│       └── files/
│           └── custom-config.txt    # .Files.Get에서 참조
└── .sbkube/                    # sbkube 작업 디렉토리
    └── build/                  # sbkube build 실행 후 생성
        └── myapp/
            ├── templates/
            │   ├── deployment.yaml      # ✅ Override됨
            │   ├── service.yaml         # (차트 원본 유지)
            │   └── new-config.yaml      # ✅ 추가됨
            └── files/
                └── custom-config.txt    # ✅ 추가됨
```

#### 🚫 자동 발견 없음

sbkube는 `overrides/` 디렉토리를 **자동으로 감지하지 않습니다**.

- **명시적 설정 필요**: config.yaml의 `overrides` 필드에 모든 파일 나열
- **경고 메시지**: v0.4.8+에서는 override 디렉토리가 있지만 설정되지 않으면 경고 표시
- **설계 철학**: Explicit over Implicit (명시적 > 암묵적)

#### 🎯 Glob 패턴 지원 (v0.4.9+)

여러 파일을 한 번에 지정할 때 **Glob 패턴**을 사용할 수 있습니다.

**지원 와일드카드**: `*` (다중 문자), `?` (단일 문자), `**` (재귀 디렉토리)

**예제:**

```yaml
# config.yaml
apps:
  myapp:
    type: helm
    chart: my-chart
    overrides:
      - Chart.yaml              # 명시적 파일
      - templates/*.yaml        # Glob: templates/의 모든 .yaml
      - templates/**/*.yaml     # Glob: 서브디렉토리 포함 모든 .yaml
      - files/*.txt             # Glob: files/의 모든 .txt
```

**주의사항:**

- 매칭되는 파일 없으면 경고 표시
- 정확한 파일명을 아는 경우 명시적 경로 권장

#### 📚 관련 문서

- [config-schema.md](../03-configuration/config-schema.md) - overrides 필드 상세
- [troubleshooting.md](../07-troubleshooting/README.md) - Override 문제 해결
- [examples/override-with-files/](../../examples/override-with-files/) - 실전 예제

______________________________________________________________________

## 📄 template - 템플릿 렌더링

빌드된 Helm 차트 및 YAML 파일들을 최종 매니페스트로 렌더링합니다.

### 📋 사용법

```bash
sbkube template [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `.`)
- `--output-dir <디렉토리>` - 렌더링된 YAML 저장 디렉토리 (기본값: `.sbkube/rendered`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--namespace <네임스페이스>` - 템플릿 생성 시 적용할 기본 네임스페이스
- `--config-file <파일>` - 사용할 설정 파일 이름
- `--app <앱이름>` - 템플릿을 생성할 특정 앱 이름

### 📁 생성되는 디렉토리

- `.sbkube/rendered/` - 렌더링된 YAML 매니페스트 파일

### 🎯 지원 앱 타입

- **`helm`** - Helm 차트 템플릿
- **`yaml`** - YAML 매니페스트 템플릿
- **`http`** - HTTP 소스 매니페스트 템플릿

### 💡 사용 예제

```bash
# 모든 앱 템플릿 생성
sbkube template

# 특정 네임스페이스로 템플릿 생성
sbkube template --namespace production

# 커스텀 출력 디렉토리
sbkube template --output-dir /tmp/manifests
```

______________________________________________________________________

## 🚀 deploy - 애플리케이션 배포

Kubernetes 클러스터에 애플리케이션을 배포합니다.

### 📋 사용법

```bash
sbkube deploy [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `.`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--dry-run` - 실제로 적용하지 않고 dry-run 실행
- `--app <앱이름>` - 배포할 특정 앱 이름
- `--config-file <파일>` - 사용할 설정 파일 이름

### 🎯 지원 앱 타입

- **`helm`** - Helm 차트 설치
- **`yaml`** - YAML 매니페스트 적용
- **`action`** - 사용자 정의 스크립트 실행
- **`exec`** - 임의 명령어 실행

### 💡 사용 예제

```bash
# 모든 앱 배포
sbkube deploy

# Dry-run으로 확인
sbkube deploy --dry-run

# 특정 앱만 배포
sbkube deploy --app web-frontend

# 특정 네임스페이스에 배포
sbkube --namespace staging deploy
```

______________________________________________________________________

## ⬆️ upgrade - 릴리스 업그레이드

이미 배포된 Helm 릴리스를 업그레이드하거나 존재하지 않을 경우 새로 설치합니다.

### 📋 사용법

```bash
sbkube upgrade [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `.`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 사용할 설정 파일 이름
- `--app <앱이름>` - 업그레이드할 특정 앱 이름

### 🎯 지원 앱 타입

- **`helm`** - Helm 릴리스 업그레이드

### 💡 사용 예제

```bash
# 모든 Helm 릴리스 업그레이드
sbkube upgrade

# 특정 앱 업그레이드
sbkube upgrade --app database
```

______________________________________________________________________

## 🗑️ delete - 리소스 삭제

배포된 애플리케이션 및 리소스를 클러스터에서 삭제합니다.

### 📋 사용법

```bash
sbkube delete [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `.`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 사용할 설정 파일 이름
- `--app <앱이름>` - 삭제할 특정 앱 이름
- `--skip-not-found` - 삭제 대상 리소스가 없을 경우 오류 대신 건너뜁니다
- `--dry-run` - 실제로 삭제하지 않고 삭제될 리소스를 미리 확인합니다

### 🎯 지원 앱 타입

- **`helm`** - Helm 릴리스 삭제 (`helm uninstall`)
- **`yaml`** - YAML 리소스 삭제 (`kubectl delete -f`)
- **`action`** - 사용자 정의 삭제 스크립트 실행 (`uninstall.script`)

### 💡 사용 예제

```bash
# 모든 앱 삭제
sbkube delete

# 특정 앱만 삭제
sbkube delete --app nginx-app

# Dry-run으로 삭제 대상 미리 확인
sbkube delete --dry-run

# 리소스가 없어도 오류 없이 진행
sbkube delete --skip-not-found

# 특정 앱을 dry-run으로 확인
sbkube delete --app redis --dry-run --skip-not-found
```

### ⚠️ 주의사항

- **Helm 앱**: `helm uninstall --dry-run`으로 삭제 대상 확인
- **YAML 앱**: `kubectl delete --dry-run=client`로 삭제 대상 확인
- **Action 앱**: Dry-run 모드에서는 스크립트가 실행되지 않으며 경고 메시지만 표시됩니다

______________________________________________________________________

## ✅ validate - 설정 파일 검증

설정 파일의 유효성을 JSON 스키마 및 Pydantic 데이터 모델을 기반으로 검증합니다.

### 📋 사용법

```bash
sbkube validate [TARGET_FILE] [옵션]
```

### 🎛️ 옵션

| 옵션 | 설명 | 기본값 | |------|------|--------| | `TARGET_FILE` | 검증할 파일 경로 (선택) | - | | `--app-dir <디렉토리>` | 앱 설정 디렉토리
(config.yaml 자동 검색) | - | | `--config-file <파일>` | 설정 파일 이름 (app-dir 내부) | `config.yaml` | | `--base-dir <경로>` | 프로젝트 루트
디렉토리 | `.` | | `--schema-type <타입>` | 파일 종류 (config 또는 sources) | 자동 유추 | | `--schema-path <경로>` | 사용자 정의 JSON 스키마 파일 경로
| - |

### 🔍 검증 항목

- **JSON 스키마** 준수 여부 (선택적)
- **Pydantic 모델** 유효성 검증
- **필수 필드** 존재 여부
- **타입 검증** 및 제약사항
- **앱 그룹 의존성** 검증 (config 파일만 해당)

### 📂 파일 해석 우선순위

1. **명시적 파일 경로**: `TARGET_FILE` 인자가 제공된 경우
1. **--app-dir 옵션**: `--app-dir` + `--config-file` 조합
1. **현재 디렉토리**: 인자 없이 실행 시 `./config.yaml` 사용

### 💡 사용 예제

```bash
# 1. 명시적 파일 경로로 검증 (기존 방식, 여전히 지원)
sbkube validate config.yaml
sbkube validate /path/to/config.yaml
sbkube validate examples/basic/config.yaml

# 2. --app-dir로 앱 그룹별 검증 (신규 기능)
sbkube validate --app-dir redis
sbkube validate --app-dir app_000_infra_network

# 3. --app-dir + --config-file 조합 (커스텀 파일명)
sbkube validate --app-dir redis --config-file staging.yaml

# 4. 현재 디렉토리 검증 (인자 없이 실행)
cd examples/basic
sbkube validate

# 5. sources.yaml 검증
sbkube validate sources.yaml
sbkube validate --app-dir . --config-file sources.yaml

# 6. 스키마 타입 명시적 지정
sbkube validate config.yaml --schema-type config
sbkube validate sources.yaml --schema-type sources
```

### 🚨 에러 처리

**App directory not found:**

```bash
$ sbkube validate --app-dir nonexistent
❌ App directory not found: /path/to/nonexistent
💡 Check directory path or use explicit file path
```

**Config file not found:**

```bash
$ sbkube validate --app-dir redis --config-file custom.yaml
❌ Config file not found: /path/to/redis/custom.yaml
💡 Use --config-file to specify different name
```

**No arguments and no config in current directory:**

```bash
$ sbkube validate
❌ Config file not found: ./config.yaml
💡 Solutions:
   1. Provide explicit path: sbkube validate path/to/config.yaml
   2. Use --app-dir: sbkube validate --app-dir <directory>
   3. Ensure config.yaml exists in current directory
```

### 🎯 실전 사용 시나리오

#### 시나리오 1: 프로젝트 초기 검증

```bash
# 프로젝트 루트에서 전체 설정 검증
cd myproject
sbkube validate  # 현재 디렉토리의 config.yaml 검증
```

#### 시나리오 2: 앱 그룹별 검증

```bash
# 특정 앱 그룹만 검증 (권장 방식)
sbkube validate --app-dir app_000_infra_network
sbkube validate --app-dir app_010_data_postgresql
sbkube validate --app-dir app_020_app_backend

# 커스텀 설정 파일 검증
sbkube validate --app-dir redis --config-file staging.yaml
```

#### 시나리오 3: CI/CD 파이프라인

```bash
# 배포 전 모든 앱 그룹 자동 검증
#!/bin/bash
for dir in app_*/; do
  echo "Validating $dir..."
  sbkube validate --app-dir "$dir" || exit 1
done
echo "✅ All app groups validated successfully"
```

#### 시나리오 4: Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
# 변경된 config.yaml 파일만 검증
changed_configs=$(git diff --cached --name-only | grep 'config.yaml$')

for config in $changed_configs; do
  dir=$(dirname "$config")
  echo "Validating $config..."
  sbkube validate --app-dir "$dir" || {
    echo "❌ Validation failed for $config"
    echo "Fix errors before committing"
    exit 1
  }
done
```

#### 시나리오 5: 다중 환경 설정 검증

```bash
# 개발/스테이징/프로덕션 환경별 검증
sbkube validate --app-dir redis --config-file config.dev.yaml
sbkube validate --app-dir redis --config-file config.staging.yaml
sbkube validate --app-dir redis --config-file config.prod.yaml
```

______________________________________________________________________

## 🏥 doctor - 시스템 종합 진단

Kubernetes 클러스터 연결, Helm 설치, 설정 파일 유효성 등을 종합적으로 진단하고 문제점을 찾아 해결 방안을 제시합니다.

### 📋 사용법

```bash
sbkube doctor [옵션]
```

### 🎛️ 옵션

- `--detailed` - 상세한 진단 결과 표시
- `--check <검사명>` - 특정 검사만 실행 (예: `k8s_connectivity`)
- `--config-dir <디렉토리>` - 설정 파일 디렉토리

### 🔍 진단 항목

1. **Kubernetes 연결**

   - `kubectl` 설치 확인
   - 클러스터 접근 가능 여부
   - 네임스페이스 존재 확인

1. **Helm 환경**

   - Helm v3 설치 확인
   - Helm 저장소 목록
   - 차트 다운로드 가능 여부

1. **설정 파일**

   - `config.yaml` 유효성
   - `sources.yaml` 유효성
   - 필수 필드 존재 확인
   - `deps` 필드에 명시된 앱 그룹 디렉토리 존재 확인

1. **권한 및 리소스**

   - 네임스페이스 생성 권한
   - 리소스 할당량 확인
   - 스토리지 클래스 존재

### 💡 사용 예제

```bash
# 기본 진단 실행
sbkube doctor

# 상세 결과 표시
sbkube doctor --detailed

# 특정 검사만 실행
sbkube doctor --check k8s_connectivity
sbkube doctor --check helm_installation
```

### 🎯 진단 결과 해석

- ✅ **통과** - 정상 동작
- ⚠️ **경고** - 동작은 하지만 권장 설정 아님
- ❌ **실패** - 즉시 수정 필요

### 💡 팁

- **배포 전 실행**: `apply` 명령 실행 전 진단으로 사전 점검
- **트러블슈팅**: 문제 발생 시 가장 먼저 실행할 명령어
- **CI/CD 통합**: `--detailed` 옵션으로 빌드 로그에 상세 정보 기록

______________________________________________________________________

## ℹ️ version - 버전 정보

SBKube CLI의 현재 버전을 표시합니다.

### 📋 사용법

```bash
sbkube version
```

### 💡 출력 예제

```
SBKube CLI v0.1.10
```

______________________________________________________________________

## 🔄 일반적인 워크플로우

### 통합 워크플로우 (권장)

4단계를 자동으로 실행하는 `apply` 명령어를 사용하면 가장 간편합니다:

```bash
# 전체 워크플로우 자동 실행
sbkube apply

# 환경별 배포
sbkube apply --profile production
sbkube apply --profile staging

# 특정 앱만 배포
sbkube apply --app database

# Dry-run으로 먼저 확인
sbkube apply --dry-run
```

### 단계별 워크플로우 (개별 실행)

각 단계를 수동으로 제어하고 싶다면 개별 명령어를 사용할 수 있습니다:

```bash
# 1. 소스 준비
sbkube prepare

# 2. 앱 빌드
sbkube build

# 3. 템플릿 렌더링 (선택사항)
sbkube template --output-dir ./manifests

# 4. 배포 실행
sbkube deploy
```

### 부분 배포 워크플로우

```bash
# apply 사용 (권장)
sbkube apply --app database

# 또는 단계별 실행
sbkube prepare --app database
sbkube build --app database
sbkube deploy --app database
```

### 검증 및 Dry-run 워크플로우

```bash
# 설정 파일 검증
sbkube validate

# Dry-run으로 확인
sbkube apply --dry-run

# 실제 배포
sbkube apply
```

### 실패 후 재시작 워크플로우

```bash
# 실패한 단계부터 자동 재개
sbkube apply --resume

# 특정 단계부터 재시작
sbkube apply --continue-from template

# 실패한 앱만 재시도
sbkube apply --retry-failed
```

______________________________________________________________________

## 📊 `sbkube status` - 클러스터 상태 확인

### 개요

클러스터의 현재 상태를 확인하는 통합 명령어입니다. (v0.6.0+)

**기존 `sbkube cluster status` 대체** - 더 직관적이고 강력한 기능 제공

### 기본 사용법

```bash
# 전체 상태 요약
sbkube status

# App-group별 그룹핑
sbkube status --by-group

# 특정 app-group 상세 조회
sbkube status app_000_infra_network

# sbkube 관리 앱만 표시
sbkube status --managed

# 문제있는 리소스만 표시
sbkube status --unhealthy
```

### 고급 기능 (Phase 4-7)

```bash
# 의존성 트리 시각화 (Phase 6)
sbkube status --deps
sbkube status app_000_infra_network --deps

# Pod 헬스체크 상세 정보 (Phase 7)
sbkube status --health-check

# 옵션 조합
sbkube status --by-group --health-check
sbkube status --managed --unhealthy --health-check
```

### 옵션 상세

| 옵션 | 설명 | 예제 | |------|------|------| | `--by-group` | App-group별로 그룹핑하여 표시 | `sbkube status --by-group` | |
`--managed` | sbkube가 관리하는 앱만 표시 | `sbkube status --managed` | | `--unhealthy` | 문제있는 리소스만 표시 |
`sbkube status --unhealthy` | | `--deps` | 의존성 트리 시각화 (Phase 6) | `sbkube status --deps` | | `--health-check` | Pod 헬스체크
상세 (Phase 7) | `sbkube status --health-check` | | `--refresh` | 캐시 강제 갱신 | `sbkube status --refresh` | | `--watch` |
10초마다 자동 갱신 | `sbkube status --watch` |

### App-Group 기반 관리

**App-group 네이밍 컨벤션**: `app_{priority}_{category}_{name}`

```yaml
apps:
  - name: app_000_infra_network     # Priority: 000, Category: infra
  - name: app_010_data_postgresql   # Priority: 010, Category: data
  - name: app_020_app_backend       # Priority: 020, Category: app
```

**그룹핑 우선순위**:

1. Kubernetes Labels (`sbkube.io/app-group`)
1. State DB 기록
1. 이름 패턴 매칭

### 출력 예시

**기본 상태**:

```
Status: my-cluster (context: k3s-prod)

Resource            Status
─────────────────────────────────────────────
API Server          https://10.0.0.1:6443
Kubernetes Version  v1.28.0
Nodes               3 nodes (3 Ready)
Namespaces          12 namespaces
Pods                42 (40 Running, 2 Pending)
Deployments         15 (15 Ready)
StatefulSets        3 (3 Ready)
Services            20
Helm Releases       8 (7 deployed, 1 failed)
```

**App-Group별 그룹핑** (`--by-group`):

```
Managed App-Groups

  app_000_infra_network (1 app)
    ✅ cilium (deployed, rev: 3)

  app_010_data_postgresql (1 app)
    ✅ cloudnative-pg (deployed, rev: 2)

  app_020_app_backend (1 app)
    ⚠️ backend (failed, rev: 1)
```

**의존성 트리** (`--deps`):

```
🔗 Dependency Tree

📦 Applications
├── app_000_infra_network (no deps)
├── app_010_data_postgresql → 1 deps
│   └── app_000_infra_network (already shown)
└── app_020_app_backend → 2 deps
    ├── app_010_data_postgresql (already shown)
    └── app_000_infra_network (already shown)

Total: 3 apps, 2 with dependencies
```

**헬스체크** (`--health-check`):

```
💊 Health Check Details

Namespace: default
┌───────────────┬─────────┬───────┬──────────┬──────────────────┐
│ Pod           │ Phase   │ Ready │ Restarts │ Health           │
├───────────────┼─────────┼───────┼──────────┼──────────────────┤
│ redis-0       │ Running │ 1/1   │ 0        │ ✅ Healthy       │
│ postgres-0    │ Running │ 1/1   │ 2        │ 🔄 Restarted 2   │
│ backend-abc   │ Pending │ 0/1   │ 0        │ ⏳ Waiting       │
└───────────────┴─────────┴───────┴──────────┴──────────────────┘
```

### 실전 사용 시나리오

**시나리오 1: 배포 후 전체 상태 확인**

```bash
sbkube apply
sbkube status --by-group
```

**시나리오 2: 특정 그룹 문제 해결**

```bash
sbkube status --unhealthy
sbkube status app_020_app_backend --health-check
```

**시나리오 3: 의존성 검증**

```bash
sbkube status --deps
# 순환 의존성 있으면 빨간색으로 표시
```

**시나리오 4: 실시간 모니터링**

```bash
sbkube status --watch --unhealthy
# 문제있는 리소스만 10초마다 갱신
```

______________________________________________________________________

## 📜 `sbkube history` - 배포 히스토리 및 비교

### 개요

배포 히스토리를 조회하고 비교하는 명령어입니다. (v0.6.0+)

**기존 `sbkube state list/show` 대체** - 더 직관적이고 강력한 비교 기능 제공

### 기본 사용법

```bash
# 최근 배포 목록
sbkube history

# 특정 배포 상세 조회
sbkube history --show dep_20250131_143022

# App-group별 필터링 (Phase 5)
sbkube history app_000_infra_network
```

### 비교 기능 (Phase 5)

```bash
# 두 배포 비교
sbkube history --diff dep_123,dep_456

# Helm values 비교
sbkube history --values-diff dep_123,dep_456

# JSON 형식으로 출력
sbkube history --diff dep_123,dep_456 --format json
```

### 옵션 상세

| 옵션 | 설명 | 예제 | |------|------|------| | `--show <id>` | 특정 배포 상세 조회 | `sbkube history --show dep_123` | |
`--diff <id1>,<id2>` | 두 배포 비교 (Phase 5) | `sbkube history --diff dep_123,dep_456` | | `--values-diff <id1>,<id2>` |
Helm values 비교 (Phase 5) | `sbkube history --values-diff dep_123,dep_456` | | `--cluster <name>` | 클러스터별 필터링 |
`sbkube history --cluster prod` | | `--namespace <ns>` | 네임스페이스별 필터링 | `sbkube history -n default` | | `--limit <n>` |
최대 개수 제한 | `sbkube history --limit 50` | | `--format <type>` | 출력 형식 (table/json/yaml) | `sbkube history --format json`
|

### 출력 예시

**배포 목록**:

```
Deployment History

ID                    Timestamp             Status     Apps  Namespace
──────────────────────────────────────────────────────────────────────
dep_20250131_150000   2025-01-31 15:00:00   success    5     prod
dep_20250131_143022   2025-01-31 14:30:22   success    5     prod
dep_20250130_120000   2025-01-30 12:00:00   failed     5     prod
```

**배포 비교** (`--diff`):

```
Deployment Comparison

Field                Deployment 1            Deployment 2
─────────────────────────────────────────────────────────────────
ID                   dep_123                 dep_456
Timestamp            2025-01-31 14:30:22     2025-01-31 15:00:00
Status               success                 success
App Count            5                       6

📦 Application Changes:
  ➕ Added (1):
     • app_030_monitoring_grafana

  ➖ Removed (0):

  📝 Modified (2):
     • app_010_data_postgresql
     • app_020_app_backend

📄 Configuration Changes:
--- dep_123 config
+++ dep_456 config
@@ -10,7 +10,7 @@
   - name: app_010_data_postgresql
     type: helm
-    version: 1.0.0
+    version: 1.1.0
```

**Helm Values 비교** (`--values-diff`):

```
Helm Values Comparison

Deployment 1: dep_123 (2025-01-31 14:30:22)
Deployment 2: dep_456 (2025-01-31 15:00:00)

📊 Summary:
  ➕ Added: 1
  ➖ Removed: 0
  📝 Modified: 1
  ✅ Unchanged: 3

📝 cloudnative-pg (MODIFIED)
  --- dep_123
  +++ dep_456
  @@ -1,5 +1,5 @@
   replicas: 2
  -storage: 10Gi
  +storage: 20Gi
   backup:
     enabled: true
```

### 실전 사용 시나리오

**시나리오 1: 최근 배포 확인**

```bash
sbkube history --limit 10
```

**시나리오 2: 배포 실패 원인 분석**

```bash
sbkube history --show dep_failed_123
sbkube history --diff dep_success_122,dep_failed_123
```

**시나리오 3: 설정 변경 추적**

```bash
sbkube history --diff dep_prod_old,dep_prod_new
# 무엇이 변경되었는지 확인
```

**시나리오 4: Helm values 변경 검토**

```bash
sbkube history --values-diff dep_old,dep_new
# 각 릴리스의 values 차이 확인
```

______________________________________________________________________

## ♻️ `sbkube rollback` - 배포 롤백

### 개요

이전 배포 상태로 롤백하는 명령어입니다. (v0.6.0+)

**기존 `sbkube state rollback` 대체**

### 기본 사용법

```bash
# 특정 배포로 롤백
sbkube rollback dep_20250131_143022

# Dry-run (실제 롤백 없이 계획만 확인)
sbkube rollback dep_20250131_143022 --dry-run

# 강제 롤백 (확인 없이)
sbkube rollback dep_20250131_143022 --force
```

### 옵션 상세

| 옵션 | 설명 | 예제 | |------|------|------| | `--dry-run` | 실제 롤백 없이 계획만 표시 | `sbkube rollback dep_123 --dry-run` | |
`--force` | 확인 없이 강제 롤백 | `sbkube rollback dep_123 --force` | | `--list` | 롤백 가능한 배포 목록 | `sbkube rollback --list` |

### 실전 사용 시나리오

**시나리오 1: 안전한 롤백**

```bash
# 1. 롤백 가능한 배포 확인
sbkube rollback --list

# 2. 롤백 계획 확인
sbkube rollback dep_success_old --dry-run

# 3. 실제 롤백
sbkube rollback dep_success_old
```

**시나리오 2: 긴급 롤백**

```bash
sbkube rollback dep_last_good --force
```

______________________________________________________________________

## 🚨 Deprecated 명령어

다음 명령어는 v1.0.0에서 제거될 예정입니다:

### `sbkube cluster status` → `sbkube status`

```bash
# 이전 (deprecated)
sbkube cluster status

# 새로운 (권장)
sbkube status
```

### `sbkube state` → `sbkube history` / `sbkube rollback`

```bash
# 이전 (deprecated)          # 새로운 (권장)
sbkube state list          → sbkube history
sbkube state show <id>     → sbkube history --show <id>
sbkube state rollback <id> → sbkube rollback <id>
```

______________________________________________________________________
