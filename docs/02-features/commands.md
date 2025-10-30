# 📋 SBKube 명령어 상세 가이드

SBKube의 모든 명령어에 대한 상세한 사용법과 옵션을 설명합니다.

---

## 🚀 빠른 참조 (Quick Reference)

### 상황별 명령어 가이드

| 상황 | 명령어 | 설명 | |------|--------|------| | 🎬 **새 프로젝트 시작** | `sbkube init` | 설정 파일 및 디렉토리 구조 생성 | | ⭐ **전체 배포** |
`sbkube apply` | 가장 많이 사용 (prepare→build→template→deploy) | | 🔍 **배포 전 확인** | `sbkube apply --dry-run` | 실제 배포 없이 계획만 확인
| | 🏥 **문제 진단** | `sbkube doctor` | 시스템 종합 진단 및 문제 해결 | | 🔧 **자동 수정** | `sbkube fix --dry-run` | 발견된 문제 자동 수정 | | ✅ **설정
검증** | `sbkube validate` | config.yaml 유효성 검사 | | 🗑️ **리소스 삭제** | `sbkube delete --dry-run` | 삭제 전 대상 확인 | | 📖 **배포
히스토리** | `sbkube history` | 최근 실행 기록 및 통계 | | 👤 **대화형 도움** | `sbkube assistant` | 문제 해결 대화형 도우미 | | ⬆️ **업그레이드** |
`sbkube upgrade` | Helm 릴리스 업그레이드 |

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
sbkube history --stats        # 3. 배포 결과 확인
```

#### 🐛 문제 해결

```bash
sbkube doctor --detailed      # 1. 상세 진단
sbkube assistant              # 2. 대화형 문제 해결
sbkube fix --dry-run          # 3. 수정 계획 확인
sbkube fix                    # 4. 자동 수정 실행
```

#### 🧹 정리 및 재배포

```bash
sbkube delete --dry-run       # 1. 삭제 대상 확인
sbkube delete                 # 2. 리소스 삭제
sbkube apply                  # 3. 재배포
```

### 명령어 카테고리

**🎯 핵심 워크플로우**

- `init` - 프로젝트 초기화
- `apply` ⭐ - 통합 배포 (가장 많이 사용)
- `prepare` / `build` / `template` / `deploy` - 단계별 실행

**🛠️ 관리 및 유지보수**

- `upgrade` - 릴리스 업그레이드
- `delete` - 리소스 삭제
- `validate` - 설정 검증

**📊 상태 및 이력**

- `state` - 배포 상태 관리
- `history` - 실행 히스토리
- `profiles` - 프로파일 관리

**🏥 문제 해결**

- `doctor` - 시스템 진단
- `fix` - 자동 수정
- `assistant` - 대화형 도우미

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
               ┌───▼────┐         ┌───▼───┐ ┌──▼────┐
               │history │         │profiles│ │rollback│
               └────────┘         └────────┘ └────────┘

보조 도구:
  👤 assistant - 언제든지 대화형 도움
  📖 history   - 실행 기록 확인
  🎛️ profiles  - 환경별 설정 관리
```

### 명령어 간 의존성

```
init
 ├─ 생성: config.yaml, sources.yaml
 └─ 사용: prepare, build, template, deploy, apply

doctor
 ├─ 체크: kubectl, helm, config files
 └─ 제안: fix

fix
 ├─ 읽기: config.yaml, 클러스터 상태
 └─ 수정: 네임스페이스, RBAC, 설정 파일

apply (통합 명령어)
 ├─ 실행: prepare → build → template → deploy
 ├─ 사용: profiles (환경 분리)
 └─ 기록: history, state

validate
 ├─ 검증: config.yaml, sources.yaml
 └─ 선행: apply, deploy

prepare
 ├─ 입력: sources.yaml, config.yaml
 └─ 출력: charts/, repos/

build
 ├─ 입력: charts/, config.yaml (overrides, removes)
 └─ 출력: build/

template
 ├─ 입력: build/, config.yaml (values)
 └─ 출력: rendered/

deploy
 ├─ 입력: build/, rendered/, config.yaml
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

profiles
 ├─ 관리: development, staging, production
 └─ 사용: apply --profile <환경>
```

---

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

---

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

---

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

### ⚠️ 참고

- Kubernetes 클러스터 연결 및 Helm 설치 필요
- 각 단계의 상세 옵션은 개별 명령어 참조 (prepare, build, template, deploy)
- 실패 시 `.sbkube/runs/`에서 실행 기록 확인 가능

---

## 🔧 prepare - 소스 준비

외부 소스(Helm 저장소, Git 저장소, OCI 차트)를 로컬 환경에 다운로드하고 준비합니다.

### 📋 사용법

```bash
sbkube prepare [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `.`)
- `--sources <파일>` - 소스 설정 파일 (기본값: `sources.yaml`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 사용할 설정 파일 이름 (app-dir 내부)
- `--sources-file <경로>` - 소스 설정 파일 경로 (--sources와 동일)
- `--app <앱이름>` - 준비할 특정 앱 이름 (미지정시 모든 앱)
- `--force` - 기존 리소스 덮어쓰기 (차트/리포지토리 재다운로드)

### 📁 생성되는 디렉토리

- `charts/` - 다운로드된 Helm 차트
- `repos/` - 클론된 Git 저장소

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
  Pulling chart: grafana/grafana → charts/grafana
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
⚠️  Removing existing chart (--force): charts/grafana
  Pulling chart: grafana/grafana → charts/grafana
✅ Helm app prepared: grafana
```

### 💡 사용 예제

```bash
# 기본 소스 준비 (멱등성 보장)
sbkube prepare

# 특정 앱만 준비
sbkube prepare --app nginx-app

# 커스텀 설정으로 준비
sbkube prepare --app-dir my-config --sources my-sources.yaml

# 기존 차트/리포지토리 강제 재다운로드
sbkube prepare --force

# 특정 앱만 강제 재다운로드
sbkube prepare --app redis --force
```

---

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

- `build/` - 빌드된 애플리케이션 아티팩트

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

**빌드 결과**: overrides가 build/ 디렉토리에 적용됨

```
🔨 Building Helm app: myapp
  Copying chart: charts/nginx/nginx → build/myapp
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
build/myapp/                    # 차트 루트
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
└── build/                      # sbkube build 실행 후 생성
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

---

## 📄 template - 템플릿 렌더링

빌드된 Helm 차트 및 YAML 파일들을 최종 매니페스트로 렌더링합니다.

### 📋 사용법

```bash
sbkube template [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `.`)
- `--output-dir <디렉토리>` - 렌더링된 YAML 저장 디렉토리 (기본값: `rendered`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--namespace <네임스페이스>` - 템플릿 생성 시 적용할 기본 네임스페이스
- `--config-file <파일>` - 사용할 설정 파일 이름
- `--app <앱이름>` - 템플릿을 생성할 특정 앱 이름

### 📁 생성되는 디렉토리

- `rendered/` - 렌더링된 YAML 매니페스트 파일

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

---

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

---

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

---

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

---

## ✅ validate - 설정 파일 검증

설정 파일의 유효성을 JSON 스키마 및 Pydantic 데이터 모델을 기반으로 검증합니다.

### 📋 사용법

```bash
sbkube validate [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `.`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 검증할 설정 파일 이름

### 🔍 검증 항목

- **JSON 스키마** 준수 여부
- **Pydantic 모델** 유효성
- **필수 필드** 존재 여부
- **타입 검증** 및 제약사항

### 💡 사용 예제

```bash
# 기본 설정 파일 검증
sbkube validate

# 특정 설정 파일 검증
sbkube validate --config-file staging-config.yaml
```

---

## 🏥 doctor - 시스템 종합 진단

Kubernetes 클러스터 연결, Helm 설치, 설정 파일 유효성 등을 종합적으로 진단하고 문제점을 찾아 해결 방안을 제시합니다.

### 📋 사용법

```bash
sbkube doctor [옵션]
```

### 🎛️ 옵션

- `--detailed` - 상세한 진단 결과 표시
- `--fix` - 자동 수정 가능한 문제들을 수정
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

# 자동 수정 포함
sbkube doctor --fix

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

---

## 🔧 fix - 자동 수정 시스템

발견된 문제를 자동으로 수정하고 백업/롤백 기능을 제공합니다.

### 📋 사용법

```bash
sbkube fix [옵션]
```

### 🎛️ 옵션

- `--dry-run` - 실제 적용하지 않고 수정 계획만 표시
- `--force` - 대화형 확인 없이 자동 실행
- `--rollback <N>` - 최근 N개 수정 롤백
- `--backup-cleanup` - 오래된 백업 파일 정리
- `--history` - 수정 히스토리 표시
- `--config-dir <디렉토리>` - 설정 파일 디렉토리

### 🔧 자동 수정 가능 항목

- **네임스페이스 문제** - 누락된 네임스페이스 자동 생성
- **설정 파일 오류** - 구문 오류 자동 수정
- **권한 문제** - RBAC 규칙 자동 생성 (가능한 경우)
- **리소스 제한** - 권장 값으로 자동 조정

### 💡 사용 예제

```bash
# Dry-run으로 수정 계획 확인
sbkube fix --dry-run

# 자동 수정 실행
sbkube fix

# 강제 실행 (확인 없이)
sbkube fix --force

# 최근 3개 수정 롤백
sbkube fix --rollback 3

# 수정 히스토리 조회
sbkube fix --history

# 오래된 백업 정리
sbkube fix --backup-cleanup
```

### ⚠️ 주의사항

- **백업 생성**: 모든 수정 전 자동 백업 생성
- **롤백 가능**: 최대 10개 수정까지 롤백 가능
- **권한 필요**: 일부 수정은 관리자 권한 필요

---

## 👤 assistant - 대화형 문제 해결

대화형으로 문제를 진단하고 해결 방안을 제시합니다.

### 📋 사용법

```bash
sbkube assistant [옵션]
sbkube assistant-history  # 지원 세션 히스토리
```

### 🎛️ 옵션

- `--context <컨텍스트>` - 문제 컨텍스트 (예: 'network', 'config', 'permissions')
- `--error <오류메시지>` - 발생한 오류 메시지
- `--quick` - 빠른 제안만 표시 (대화형 없음)

### 💡 사용 예제

```bash
# 대화형 문제 해결
sbkube assistant

# 네트워크 문제로 시작
sbkube assistant --context network

# 특정 오류 분석
sbkube assistant --error "connection refused"

# 빠른 제안만
sbkube assistant --quick

# 지원 세션 히스토리
sbkube assistant-history
```

---

## 🎛️ profiles - 프로파일 관리

환경별 프로파일을 관리합니다.

### 📋 사용법

```bash
sbkube profiles <하위명령어> [옵션]
```

### 🎛️ 하위 명령어

- `list` - 사용 가능한 프로파일 목록 조회
- `show <프로파일>` - 프로파일 설정 내용 표시
- `validate <프로파일>` - 프로파일 설정 검증

### 💡 사용 예제

```bash
# 프로파일 목록
sbkube profiles list

# 특정 프로파일 내용 표시
sbkube profiles show production

# 프로파일 검증
sbkube profiles validate staging
```

---

## 📖 history - 실행 히스토리

최근 실행 기록을 조회하고 성공/실패 통계를 확인합니다.

### 📋 사용법

```bash
sbkube history [옵션]
sbkube diagnose  # 진단 실행
```

### 🎛️ 옵션

- `--limit <N>` - 표시할 히스토리 개수 (기본값: 10)
- `--detailed` - 상세 정보 표시
- `--failures` - 실패한 실행만 표시
- `--profile <프로파일>` - 특정 프로파일의 히스토리만 표시
- `--clean` - 오래된 히스토리 정리
- `--stats` - 통계 정보 표시

### 💡 사용 예제

```bash
# 최근 10개 실행 기록
sbkube history

# 최근 20개 상세 정보
sbkube history --limit 20 --detailed

# 실패한 실행만
sbkube history --failures

# 통계 정보
sbkube history --stats

# 오래된 기록 정리
sbkube history --clean

# 진단 실행
sbkube diagnose
```

---

## 📊 state - 배포 상태 관리

배포 상태를 추적하고 롤백 기능을 제공합니다. *(신규 기능)*

### 📋 사용법

```bash
sbkube state <하위명령어> [옵션]
```

### 🎛️ 하위 명령어

- `list` - 배포 상태 목록 조회
- `rollback` - 특정 배포로 롤백
- `history` - 배포 히스토리 조회

### 🎛️ 옵션

- `--cluster <이름>` - 클러스터별 필터링
- `--deployment-id <ID>` - 특정 배포 ID 지정

### 💡 사용 예제

```bash
# 배포 상태 목록 확인
sbkube state list

# 특정 클러스터 상태 확인
sbkube state list --cluster production

# 롤백 실행
sbkube state rollback --deployment-id <id>
```

---

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

---

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

---

## 10. `cluster` - 클러스터 상태 관리

**카테고리**: 유틸리티

Kubernetes 클러스터의 전체 상태를 수집하고 로컬에 캐싱합니다.

### 주요 기능

- 클러스터 정보 수집 (API 서버, 버전)
- 노드 상태 및 역할 조회
- 네임스페이스 목록 수집
- Helm 릴리스 상태 조회
- YAML 형식으로 로컬 캐싱 (TTL: 5분)

### 사용법

```bash
# 캐시된 상태 표시 (TTL 만료 시 자동 갱신)
sbkube cluster status

# 특정 디렉토리의 sources.yaml 사용
sbkube cluster status --base-dir /path/to/config

# 강제 갱신 (캐시 무시하고 실시간 수집)
sbkube cluster status --refresh

# 10초마다 자동 갱신 (Ctrl+C로 종료)
sbkube cluster status --watch
```

### 캐시 파일 위치

캐시 파일은 `sources.yaml`이 있는 디렉토리 아래에 저장됩니다:

```
{base-dir}/.sbkube/cluster_status/{context}_{cluster}.yaml
```

**예시:**
- `sources.yaml` 위치: `/home/user/project/config/sources.yaml`
- `kubeconfig_context`: `default`
- `cluster`: `production-k3s`
- 캐시 파일: `/home/user/project/config/.sbkube/cluster_status/default_production-k3s.yaml`

### 캐시 파일 형식

```yaml
# 메타데이터
context: default
cluster_name: production-k3s
timestamp: "2025-10-30T10:30:00Z"
ttl_seconds: 300

# 클러스터 정보
cluster_info:
  api_server: https://127.0.0.1:6443
  version: v1.27.3

# 노드 목록
nodes:
  - name: node1
    status: Ready
    roles:
      - control-plane
    version: v1.27.3

# 네임스페이스 목록
namespaces:
  - default
  - kube-system
  - my-app

# Helm 릴리스 목록
helm_releases:
  - name: redis
    namespace: data
    status: deployed
    chart: redis-18.0.0
    app_version: 7.2.0
    revision: 1
```

### 출력 예시

```bash
$ sbkube cluster status

Using cached data (collected 1m 23s ago)

Cluster Status: production-k3s (context: default)
┌─────────────────┬────────────────────────────────┐
│ Resource        │ Status                         │
├─────────────────┼────────────────────────────────┤
│ API Server      │ https://127.0.0.1:6443         │
│ Kubernetes      │ v1.27.3                        │
│ Nodes           │ 3 Ready / 3 Total              │
│ Namespaces      │ 12                             │
│ Helm Releases   │ 5 (4 deployed, 1 pending)      │
└─────────────────┴────────────────────────────────┘

Cache file: .sbkube/cluster_status/default_production-k3s.yaml
Last updated: 1 minute ago
Cache expires in: 3m 37s
```

### 옵션

- `--base-dir PATH`: sources.yaml이 있는 디렉토리 (기본값: 현재 디렉토리)
- `--refresh`: 캐시를 무시하고 강제로 새로 수집
- `--watch`: 10초마다 자동 갱신 (백그라운드)

### 에러 처리

- `sources.yaml` 파일이 없으면 에러 종료
- kubectl/helm 명령어 실행 실패 시:
  - 기존 캐시 파일이 있으면 유지
  - 경고 메시지 출력 후 기존 캐시 사용
  - 캐시가 없으면 에러 종료

### 권장 사항

**`.gitignore` 설정:**

캐시 디렉토리는 Git에 포함하지 않는 것을 권장합니다:

```gitignore
# SBKube cache directory
.sbkube/
```

`sbkube init` 명령어를 사용하면 자동으로 추가됩니다.

---

*각 명령어의 더 자세한 사용법은 `sbkube <명령어> --help`를 통해 확인할 수 있습니다.*
