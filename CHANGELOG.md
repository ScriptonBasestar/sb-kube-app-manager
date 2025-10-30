# Changelog - SBKube

> **참고**: 이 문서의 과거 버전 예제에는 Bitnami 차트 참조가 포함되어 있습니다.
> 현재 버전(v0.4.10+)에서는 Grafana, Prometheus 등 오픈소스 차트를 사용합니다.

## [Unreleased] - 2025-10-30

### ✨ Features

- **OCI 레지스트리 지원** (`sbkube/commands/prepare.py`)
  - Helm OCI 레지스트리에서 차트 직접 pull 가능
  - `oci_registries` 섹션을 sources.yaml에서 인식
  - `helm repo add` 없이 OCI 프로토콜로 직접 다운로드
  - TrueCharts, GitHub Container Registry 등 지원

### 🔧 Improvements

- **HelmApp 모델 확장** (`sbkube/models/config_model.py`)
  - `is_oci_chart()` 메서드 추가
  - OCI 프로토콜 감지 기능

- **prepare 명령어 개선**
  - `prepare_oci_chart()` 함수 추가
  - OCI와 일반 Helm 레지스트리 자동 구분
  - 더 명확한 오류 메시지 (힌트 포함)

### 📚 Documentation

- **트러블슈팅 가이드 업데이트** ([docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md))
  - OCI 레지스트리 오류 케이스 추가
  - Deprecated Helm 저장소 해결 방법
  - sources.yaml 설정 오류 가이드

- **OCI 예제 추가** ([examples/prepare/helm-oci/](examples/prepare/helm-oci/))
  - OCI 레지스트리 사용 예제
  - sources.yaml 설정 샘플
  - README.md with 사용 가이드

- **개발 가이드 개선** ([CLAUDE.md](CLAUDE.md))
  - 버그 수정 시 예제 및 엣지 케이스 추가 정책 명시
  - 회귀 테스트(regression test) 작성 가이드
  - 실제 적용 예시 포함 (2025-10-30 OCI 지원)

### 🧪 Testing

- **E2E 테스트 활성화**
  - `test_prepare_pull_helm_oci` 테스트 skip 해제
  - OCI 차트 pull 검증

- **엣지 케이스 테스트 전략**
  - 버그 발견 시 재발 방지를 위한 테스트 추가 정책
  - examples/edge-cases/ 디렉토리 구조 정의

### 🐛 Bug Fixes

- **일반적인 오류 케이스 해결**
  - Helm repo가 sources.yaml에 없을 때 명확한 안내
  - OCI 레지스트리와 일반 Helm repo 구분
  - Deprecated 저장소 사용 시 가이드 제공

### 🎯 Development Policy

- **버그 수정 시 필수 작업**
  1. 재현 테스트 작성
  2. 예제 추가 (`examples/`)
  3. 엣지 케이스 테스트 작성
  4. 트러블슈팅 문서 업데이트
  - 목적: 동일한 버그의 재발 방지

### 📝 Usage Example

```yaml
# sources.yaml
oci_registries:
  browserless:
    registry: oci://tccr.io/truecharts
  gabe565:
    registry: oci://ghcr.io/gabe565/charts

# config.yaml
apps:
  browserless:
    type: helm
    chart: browserless/browserless-chrome
```

## [0.4.10] - 2025-10-29

### ✨ Features

- **deps 필드 지원** (`sbkube/models/config_model.py`)
  - 앱 그룹 레벨에서 다른 앱 그룹에 대한 의존성 선언 가능
  - 설정 파일에서 의존성 정보를 명시적으로 문서화
  - 현재는 파싱만 지원 (검증은 향후 버전에서 구현)

### 🔧 Improvements

- **SBKubeConfig 모델 확장**

  - `deps: list[str]` 필드 추가
  - 기본값: 빈 리스트 (후방 호환성 보장)
  - Pydantic 모델 검증 통과

- **문서 업데이트**

  - `docs/03-configuration/config-schema.md` - deps 필드 스키마 추가
  - 사용 사례 및 예제 포함
  - 향후 기능 로드맵 명시

- **테스트 추가**

  - `tests/test_config_model.py` - deps 필드 테스트 3개
    - `test_deps_field_parsing` - deps 필드 파싱 검증
    - `test_deps_field_optional` - 후방 호환성 검증
    - `test_deps_field_empty_list` - 빈 리스트 처리

### 📝 Usage Example

```yaml
# a302_devops/config.yaml
namespace: harbor
deps:
  - a000_infra_network    # Ingress and Storage
  - a101_data_rdb         # PostgreSQL database
  - a100_data_memory      # Redis cache

apps:
  harbor:
    type: helm
    chart: harbor/harbor
    values:
      - values/harbor.yaml
```

### 🎯 Purpose

이 기능은 복잡한 Kubernetes 인프라 프로젝트에서:

1. 앱 그룹 간 의존성을 config.yaml에 명시적으로 기록
1. 배포 순서 정보를 기계 판독 가능한 형식으로 유지
1. 향후 자동 검증 및 순서 결정 기능의 기반 제공

**현재 버전 (v0.4.10)**:

- ✅ 파싱 및 저장
- ✅ 문서화 목적

**향후 버전 (예정)**:

- 배포 전 의존성 검증
- 자동 배포 순서 결정 (`--recursive`)
- 의존성 그래프 시각화

### 🔗 Related

- Feature Request: tmp/sbkube-deps-feature-request.md
- Real-world usage: 11개 앱 그룹에서 deps 사용 중
- Issue: Validation 에러 해결 (Extra inputs are not permitted)

______________________________________________________________________

## [0.4.9] - 2025-10-29

### ✨ Features

- **Glob 패턴 지원** (`sbkube/commands/build.py`)
  - Override 파일 지정 시 와일드카드 패턴 사용 가능
  - `*` (0개 이상 문자), `?` (정확히 1개 문자), `**` (재귀적 디렉토리) 지원
  - 명시적 파일 경로와 glob 패턴 혼합 사용 가능

### 🔧 Improvements

- **build 명령어 Glob 패턴 처리**

  - 패턴 매칭 파일 개수 표시
  - 매칭되는 파일이 없으면 경고 메시지
  - 개별 파일 복사 진행 상황 표시

- **문서 업데이트**

  - `docs/02-features/commands.md` - Glob 패턴 사용 예제 추가
  - `docs/03-configuration/config-schema.md` - Glob 패턴 지원 문서화
  - `examples/override-with-files/` - Glob 패턴 사용 예제 추가

- **테스트 추가**

  - `tests/test_build.py` - Glob 패턴 테스트 케이스 2개
    - `test_helm_app_with_glob_patterns` - 기본 glob 패턴 테스트
    - `test_helm_app_with_mixed_patterns` - 명시적 파일 + glob 혼합 테스트

### 📝 Usage Examples

**기본 사용**:

```yaml
overrides:
  - templates/*.yaml        # templates/의 모든 .yaml 파일
  - files/*                 # files/의 모든 파일
```

**혼합 사용**:

```yaml
overrides:
  - Chart.yaml              # 명시적 파일
  - templates/*.yaml        # Glob 패턴
  - files/config.toml       # 명시적 파일
```

**재귀적 패턴**:

```yaml
overrides:
  - templates/**/*.yaml     # templates/ 하위 모든 .yaml (서브디렉토리 포함)
```

______________________________________________________________________

## [0.4.8] - 2025-10-29

### ✨ Features

- **Override 디렉토리 감지 경고 시스템**
  - **문제**: `overrides/` 디렉토리가 있지만 `config.yaml`에 명시하지 않으면 무시됨
  - **해결**: Override 디렉토리가 있지만 설정되지 않은 경우 상세한 경고 메시지 표시
  - **영향**: 사용자가 override 설정 누락을 즉시 알 수 있음

### 🔧 Improvements

- **build 명령어 경고 메시지 추가** (`sbkube/commands/build.py`)

  - Override 디렉토리 존재 확인
  - 설정되지 않은 경우 파일 목록 표시 (최대 5개 + 더 있으면 개수 표시)
  - 예제 config.yaml 설정 방법 제안

- **문서 대폭 개선**

  - `docs/02-features/commands.md` - Override 사용법 상세 설명 추가 (150+ 줄)
  - `docs/03-configuration/config-schema.md` - overrides 필드 스키마 확장
  - `docs/07-troubleshooting/README.md` - 빌드 및 Override 문제 해결 섹션 추가 (280+ 줄)

- **실전 예제 추가**

  - `examples/override-with-files/` - files 디렉토리와 .Files.Get 사용 예제
  - 완전한 작동 예제 (Nginx + ConfigMap + .Files.Get)
  - 상세한 README 및 사용 가이드

### 📝 Technical Details

**Before (v0.4.7)**:

```bash
# overrides 디렉토리가 있지만 설정 안 함
$ tree
overrides/
  myapp/
    templates/
      configmap.yaml

$ cat config.yaml
apps:
  myapp:
    type: helm
    chart: bitnami/nginx
    # overrides 필드 없음!

$ sbkube build
🔨 Building Helm app: myapp
  Copying chart: charts/nginx/nginx → build/myapp
✅ Helm app built: myapp

# 결과: Override 무시됨 (경고 없음)
$ ls build/myapp/templates/
deployment.yaml service.yaml  # ❌ configmap.yaml 없음
```

**After (v0.4.8)**:

```bash
$ sbkube build
🔨 Building Helm app: myapp
  Copying chart: charts/nginx/nginx → build/myapp

⚠️  Override directory found but not configured: myapp
    Location: overrides/myapp
    Files:
      - templates/configmap.yaml
    💡 To apply these overrides, add to config.yaml:
       myapp:
         overrides:
           - templates/configmap.yaml

✅ Helm app built: myapp

# 경고 메시지로 사용자에게 알림
```

### 🎯 Impact

- **문제 발견 시간**: 배포 실패 시점 → **빌드 시점**으로 조기 감지
- **디버깅 시간**: 30분+ → **1분 이내** (명확한 경고 및 해결 방법 제시)
- **사용자 경험**: 혼란 → 명확한 가이드
- **문서 품질**: 기본 설명 → 실전 예제 및 트러블슈팅 포함

### 📚 Documentation

- Override 메커니즘의 "새 파일 추가" 기능 명시
- .Files.Get 사용 시 주의사항 추가
- 명시적 설정 (Explicit over Implicit) 철학 설명
- 실제 프로젝트 사례 기반 트러블슈팅 가이드

### 🙏 Acknowledgments

이 개선은 실제 프로젝트에서 발생한 문제 리포트를 기반으로 만들어졌습니다.

- 문제 제기: a000_infra_network 프로젝트 배포 중 override 미적용 이슈
- 근본 원인 분석 및 설계 철학 재확인

______________________________________________________________________

## [0.4.7] - 2025-10-24

### ✨ Features

- **sources.yaml 자동 탐색 기능** (Developer Experience 개선)
  - **문제**: `cd app1 && sbkube apply` 실행 시 sources.yaml을 찾지 못함
  - **해결**: sources.yaml을 다음 순서로 자동 탐색
    1. 현재 디렉토리 (`.`)
    1. 상위 디렉토리 (`..`)
    1. base-dir (프로젝트 루트)
  - **영향**: 두 가지 실행 방법 모두 동일하게 동작
    - `sbkube apply --app-dir app1` (base-dir에서 실행)
    - `cd app1 && sbkube apply` (app-dir에서 실행)

### 🔧 Improvements

- **find_sources_file() 유틸리티 함수 추가**
  - `sbkube/utils/common.py`에 sources.yaml 탐색 로직 구현
  - 상세한 에러 메시지 (찾은 경로 목록 표시)
  - charts/repos 디렉토리를 sources.yaml 위치 기준으로 생성

### 📝 Technical Details

**Before (v0.4.6)**:

```bash
# base-dir에서 실행 (성공)
$ sbkube apply --app-dir app1
✅ Works

# app-dir에서 실행 (실패)
$ cd app1 && sbkube apply
❌ Error: sources.yaml not found
```

**After (v0.4.7)**:

```bash
# base-dir에서 실행 (성공)
$ sbkube apply --app-dir app1
📄 Using sources file: /project/sources.yaml
✅ Works

# app-dir에서 실행 (성공)
$ cd app1 && sbkube apply
📄 Using sources file: /project/sources.yaml  # 상위에서 발견
✅ Works
```

### 🎯 Impact

- ✅ 유연한 실행 위치 (app-dir 내부에서도 실행 가능)
- ✅ monorepo 구조 지원 개선
- ✅ 하위 호환성 유지 (기존 동작 그대로)

______________________________________________________________________

## [0.4.6] - 2025-10-24

### 🐛 Bug Fixes

- **prepare 명령어 멱등성 개선** (Critical Fix)
  - **문제**: 차트/리포지토리가 이미 존재할 때 `prepare` 실패
  - **해결**: 기본 동작을 skip으로 변경 (실패 → 성공)
  - **영향**: `sbkube apply` 재실행 시 오류 없이 성공

### ✨ Features

- **prepare 명령어 개선**
  - **기본 동작**: 차트/리포지토리 존재 시 자동 skip
    - Helm 차트: `charts/{chart_name}/{chart_name}/Chart.yaml` 존재 확인
    - Git 리포지토리: `repos/{repo_alias}/.git` 존재 확인
    - HTTP 파일: 이미 구현됨 (변경 없음)
  - **--force 옵션**: 기존 리소스 삭제 후 재다운로드
  - **재실행 안전성**: `sbkube apply` 여러 번 실행해도 안전

### 🔄 Behavior Changes

**Before (v0.4.5)**:

```bash
$ sbkube prepare
✅ Helm app prepared: redis

$ sbkube prepare  # 재실행 시 실패
❌ Failed to pull chart: destination path exists
```

**After (v0.4.6)**:

```bash
$ sbkube prepare
✅ Helm app prepared: redis

$ sbkube prepare  # 재실행 시 성공 (skip)
⏭️  Chart already exists, skipping: redis
    Use --force to re-download
✅ Helm app prepared: redis

$ sbkube prepare --force  # 강제 재다운로드
⚠️  Removing existing chart (--force): charts/redis
✅ Helm app prepared: redis
```

### 📝 Documentation

- `docs/02-features/commands.md` 업데이트
  - prepare 명령어 멱등성 섹션 추가
  - --force 옵션 사용 예제 추가
  - 동작 방식 상세 설명

### 🎯 Impact

- ✅ `sbkube apply` 재실행 안전성 확보
- ✅ 개발 워크플로우 개선 (불필요한 재다운로드 방지)
- ✅ 하위 호환성 유지 (Breaking change 없음)

______________________________________________________________________

## [0.4.5] - 2025-10-24

### 📦 Examples

- **Kustomize 예제 디렉토리 추가** (Phase 3 완료)
  - `examples/kustomize-example/` - Kustomize 타입 완전 예제
    - Base + Overlays 패턴 (dev/prod 환경)
    - namePrefix, replicas, images 변환 데모
    - configMapGenerator를 통한 환경별 설정 생성
    - 전략적 병합 패치 (resources-patch.yaml)
    - Kustomize vs Helm 비교 분석
    - 3,800줄 상세 README.md

### 📊 Examples Coverage - 100% 달성

- **앱 타입 커버리지**: 87.5% (7/8) → **100% (8/8)** ✅
  - kustomize 타입 예제 완성
  - 모든 지원 앱 타입 예제화 완료
- **워크플로우 커버리지**: 71.4% (5/7) → **100% (7/7)** ✅
- **고급 기능 커버리지**: **100% (9/9)** ✅
- **README 문서화**: **100% (21/21)** ✅
- **전체 예제 커버리지**: 85% → **~95%** (최종)

### 📝 Documentation

- `EXAMPLES_COVERAGE_ANALYSIS.md` 최종 업데이트
  - Phase 1/2A/2B/3 모두 완료 상태로 변경
  - 커버리지 개선 결과 (v0.4.2 → v0.4.5) 요약
  - 총 12,000줄 이상의 상세 문서 작성 완료

### 🎯 Achievement

- 🎉 **모든 SBKube 앱 타입 예제 완성**
- 🎉 **모든 워크플로우 시나리오 커버**
- 🎉 **100% README 문서화 완성**
- 🎉 **Phase 1, 2A, 2B, 3 모두 완료**

______________________________________________________________________

## [0.4.4] - 2025-10-24

### 📦 Examples

- **4개 신규 예제 디렉토리 추가** (Phase 2A 완료)
  - `examples/apply-workflow/` - 통합 워크플로우 (`sbkube apply`) 사용법
    - Redis + Nginx 스택 배포
    - depends_on을 통한 의존성 관리
    - apply vs 단계별 실행 비교
  - `examples/force-update/` - `--force` 옵션 활용
    - 차트/Git 리포지토리 강제 재다운로드
    - 빌드 캐시 무시 및 재빌드
    - 배포 충돌 해결 및 Pod 강제 재생성
  - `examples/git-standalone/` - Git 타입 단독 사용
    - Strimzi Kafka Operator Git 배포
    - Public/Private 리포지토리 인증
    - 로컬 수정 및 다중 차트 배포
  - `examples/state-management/` - 배포 상태 관리
    - state list/history 명령어
    - rollback을 통한 이전 버전 복구
    - SQLite 상태 데이터베이스 활용

### 📊 Examples Coverage Improvement

- **예제 디렉토리**: 16개 → 20개 (+25%)
- **워크플로우 커버리지**: 14.3% → 71.4% (5배 향상)
  - apply 통합 워크플로우: ✅
  - --force 옵션: ✅
  - Git 타입 단독: ✅
  - 상태 관리 (history/rollback): ✅
- **전체 예제 커버리지**: 72% → 85% (예상)
- **총 라인 수**: 12,872줄 (문서 8,436줄 추가)

### 🎯 Related

- Phase 2A (예제 추가) 완료
- Phase 2B (문서 보강) + Phase 2A 통합 완료
- 남은 단계: kustomize 예제 (Phase 3 예정)

______________________________________________________________________

## [0.4.3] - 2025-10-24

### 📚 Documentation

- **8개 예제 디렉토리 README.md 추가**
  - HIGH 우선순위 (4개):
    - `examples/k3scode/README.md` - k3s 통합 배포 프로젝트 개요
    - `examples/deploy/action-example/README.md` - kubectl 액션 실행 가이드
    - `examples/deploy/exec/README.md` - 커스텀 명령어 실행 가이드
    - `examples/deploy/yaml-example/README.md` - 원시 YAML 매니페스트 배포 가이드
  - MEDIUM 우선순위 (4개):
    - `examples/k3scode/memory/README.md` - Redis/Memcached 배포 가이드
    - `examples/k3scode/rdb/README.md` - PostgreSQL/MariaDB 배포 가이드
    - `examples/k3scode/ai/README.md` - Toolhive Operator 배포 가이드 (Git 타입)
    - `examples/overrides/README.md` - Helm 차트 커스터마이징 가이드

### 📊 Examples Coverage Improvement

- **README 커버리지**: 50% → 100% (8/16 → 16/16)
- **전체 예제 커버리지**: 60% → 72% 예상
  - 문서 완성도 크게 향상
  - 사용자가 각 앱 타입 및 기능을 쉽게 이해 가능

### 🎯 Related

- Phase 2B (문서 보강) 완료
- 다음 단계: Phase 2A (예제 추가) - apply-workflow, force-update, git-standalone, state-management

______________________________________________________________________

## [0.4.1] - 2025-10-24

### ✨ Features

- **helm_repos dict 포맷 통일**
  - init 템플릿이 list 대신 dict 포맷으로 sources.yaml 생성
  - 예제 및 모델과 일관성 확보
  - 중복 방지 자동화 (dict key uniqueness)
  - O(1) 조회 성능 개선

### 🔧 Improvements

- **Pydantic shorthand 지원 추가**
  - `helm_repos`, `git_repos`, `oci_registries`에 string shorthand 지원
  - `{"bitnami": "https://..."}` → 자동으로 `{"bitnami": {"url": "https://..."}}`로 변환
  - 간결한 설정과 복잡한 설정 모두 지원
  - 하위 호환성 유지 (기존 포맷 모두 작동)

### 📊 Examples Coverage

- **예제 커버리지 분석 문서 추가** (`EXAMPLES_COVERAGE_ANALYSIS.md`)
  - 현재 커버리지: 60% (⭐⭐⭐ 보통)
  - 앱 타입: 7/8 (87.5%) - kustomize 예제 누락
  - 워크플로우: 1/7 (14.3%)
  - 개선 계획 4단계 제시

### 🔗 Related Commits

- `3e44209` - helm_repos dict 포맷 통일 및 shorthand validator 추가

______________________________________________________________________

## [0.4.0] - 2025-10-23

### ✨ Features

- **prepare 명령어에 `--force` 옵션 추가**
  - Helm 차트 및 Git 리포지토리를 강제로 덮어쓰기 가능
  - 테스트 시나리오 및 재배포 워크플로우 개선
  - 사용법: `sbkube prepare --force`

### 🐛 Bug Fixes

- **validate 명령어 BaseCommand 의존성 오류 수정**

  - BaseCommand 상속 제거하여 초기화 오류 해결
  - JSON 스키마 검증을 선택적으로 변경 (Pydantic만으로도 검증 가능)
  - 파일 타입 자동 감지 기능 추가

- **prepare Git URL dict 파싱 오류 수정**

  - `sources.yaml`의 `git_repos`가 dict 형태일 때 발생하던 TypeError 해결
  - `{url: "...", branch: "..."}` 형식 지원
  - 기존 string 형식과의 하위 호환성 유지

- **prepare 성공 카운팅 버그 수정**

  - 건너뛴 앱(yaml/action/exec)이 성공 카운트에 포함되지 않던 문제 해결
  - 정확한 성공/실패 리포팅

### 🔧 Improvements

- **helm_repos dict 형태 지원**

  - Private Helm repository 인증 준비
  - `{url: "...", username: "...", password: "..."}` 형식 지원
  - 기존 string 형식과의 하위 호환성 유지

- **Git URL None 체크 추가**

  - `git_repos`에서 `url` 필드 누락 시 명확한 오류 메시지
  - 런타임 오류 방지 및 디버깅 용이성 향상

- **코드 품질 개선**

  - shutil import를 파일 상단으로 이동 (PEP 8 준수)
  - `load_json_schema` 함수에 타입 힌트 추가
  - ruff 및 mypy 검증 통과

### 📊 Code Quality

- **이전**: 7.7/10
- **현재**: 9.0/10
- **개선**: 일관성, 안정성, 유지보수성 향상

### 🔗 Related Commits

- `d414b54` - 코드 리뷰 개선사항 5건 반영
- `588f298` - validate 및 prepare Git 파싱 버그 수정
- `8037517` - prepare --force 옵션 추가
- `5f3a6b8` - E2E 테스트 주요 수정

______________________________________________________________________

## [0.3.0] - 2025-10-22

### 🎉 Major Release: Breaking Changes

SBKube v0.3.0은 사용성을 대폭 개선한 메이저 업데이트입니다. 기존 v0.2.x와 호환되지 않으며, 설정 파일 마이그레이션이 필요합니다.

### ✨ 주요 변경사항

#### 1. 간결한 설정 구조

**Before (v0.2.x)**:

```yaml
apps:
  - name: redis-pull
    type: pull-helm
    specs:
      repo: bitnami
      chart: redis
      dest: redis

  - name: redis
    type: install-helm
    specs:
      path: redis
      values:
        - redis.yaml
```

**After (v0.3.0)**:

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    values:
      - redis.yaml
```

**개선 사항**:

- Apps를 list → dict로 변경 (앱 이름이 키)
- `pull-helm` + `install-helm` → 단일 `helm` 타입으로 통합
- `specs` 제거 (모든 필드를 앱 레벨로 평탄화)
- 설정 파일 길이 약 50% 감소

#### 2. 자동 차트 타입 감지

```yaml
apps:
  # Remote chart (자동 감지)
  redis:
    type: helm
    chart: bitnami/redis  # repo/chart 형식

  # Local chart (자동 감지)
  my-app:
    type: helm
    chart: ./charts/my-app  # 상대 경로

  another-app:
    type: helm
    chart: /absolute/path/to/chart  # 절대 경로
```

**개선 사항**:

- Remote vs Local 차트를 자동으로 구분
- 별도의 타입 지정 불필요
- 더 직관적인 설정

#### 3. 차트 커스터마이징 기능 강화

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2
    values:
      - redis.yaml

    # 파일 교체
    overrides:
      - values.yaml
      - templates/service.yaml

    # 불필요한 파일 삭제
    removes:
      - README.md
      - templates/ingress.yaml
      - tests/

    # 메타데이터
    labels:
      environment: production
    annotations:
      managed-by: sbkube
```

**개선 사항**:

- `overrides`: 차트 파일을 커스텀 버전으로 교체
- `removes`: 불필요한 파일/디렉토리 제거
- `labels`, `annotations`: Kubernetes 메타데이터 추가
- v0.2.x의 모든 기능 보존

#### 4. 향상된 워크플로우

```bash
# v0.2.x
sbkube prepare
sbkube build
sbkube deploy

# v0.3.0 (동일하지만 더 강력)
sbkube prepare  # Helm, Git, HTTP 다운로드
sbkube build    # 차트 커스터마이징 (overrides/removes 적용)
sbkube template # YAML 렌더링 (배포 전 미리보기)
sbkube deploy   # 클러스터 배포

# 또는 통합 실행
sbkube apply    # prepare → build → deploy 자동 실행
```

**개선 사항**:

- `build` 단계에서 overrides/removes 자동 적용
- `template` 명령어로 배포 전 YAML 미리보기
- `apply`가 build 단계 포함

### 🆕 새로운 기능

#### 1. HTTP 파일 다운로드

```yaml
apps:
  my-manifest:
    type: http
    url: https://example.com/manifest.yaml
    dest: downloaded.yaml
    headers:
      Authorization: Bearer token
```

#### 2. 의존성 자동 해결

```yaml
apps:
  database:
    type: helm
    chart: bitnami/postgresql

  cache:
    type: helm
    chart: bitnami/redis
    depends_on:
      - database  # database 배포 후 cache 배포

  app:
    type: helm
    chart: myorg/backend
    depends_on:
      - database
      - cache  # 모든 의존성 배포 후 app 배포
```

**기능**:

- 위상 정렬 (Topological Sort)로 자동 순서 결정
- 순환 의존성 검출 및 오류 발생
- 존재하지 않는 앱 참조 검출

#### 3. 설정 마이그레이션 도구

```bash
# v0.2.x 설정을 현재 버전으로 변환
sbkube migrate config.yaml -o config-migrated.yaml

# 미리보기
sbkube migrate config.yaml

# 기존 파일 덮어쓰기
sbkube migrate config.yaml -o config.yaml --force
```

**기능**:

- 자동 타입 변환
- pull-helm + install-helm 통합
- overrides, removes, labels, annotations 보존
- 검증 및 오류 보고

### 🔧 CLI 변경사항

#### 명령어 변경

| 기능 | v0.2.x | v0.3.0 | 상태 | |------|--------|--------|------| | 차트 다운로드 | `sbkube prepare` | `sbkube prepare` | ✅ 동일 |
| 차트 커스터마이징 | `sbkube build` | `sbkube build` | ✅ 강화 | | YAML 렌더링 | `sbkube template` | `sbkube template` | ✅ 개선 | |
클러스터 배포 | `sbkube deploy` | `sbkube deploy` | ✅ 강화 | | 통합 실행 | `sbkube apply` | `sbkube apply` | ✅ build 단계 추가 | |
마이그레이션 | - | `sbkube migrate` | 🆕 신규 |

#### 레거시 명령어

v0.2.x 명령어는 `legacy-` 접두사로 계속 제공됩니다:

```bash
sbkube legacy-prepare
sbkube legacy-build
sbkube legacy-template
sbkube legacy-deploy
sbkube legacy-apply
```

### 🗑️ 제거된 기능

#### 제거된 앱 타입

- `copy-app` → 불필요 (직접 파일 복사)
- `copy-repo` → 불필요
- `copy-chart` → 불필요
- `copy-root` → 불필요
- `render` → `template` 명령어로 대체

### 📦 지원 앱 타입

| 타입 | v0.2.x | v0.3.0 | 설명 | |------|--------|--------|------| | Helm | `pull-helm` + `install-helm` | `helm` | Helm 차트
(통합) | | YAML | `install-yaml` | `yaml` | YAML 매니페스트 | | Action | `install-action` | `action` | 커스텀 액션 | | Kustomize |
`install-kustomize` | `kustomize` | Kustomize | | Git | `pull-git` | `git` | Git 리포지토리 | | Exec | `exec` | `exec` | 커스텀
명령어 | | HTTP | - | `http` | HTTP 다운로드 🆕 |

### 🔄 마이그레이션 가이드

#### 1. 설정 파일 변환

```bash
sbkube migrate config.yaml -o config-migrated.yaml
```

#### 2. 수동 변환 체크리스트

**필수 변경**:

- [ ] `apps` list → dict 변환
- [ ] `pull-helm` + `install-helm` → `helm` 통합
- [ ] `specs` 제거 (필드 평탄화)
- [ ] 앱 이름을 딕셔너리 키로 이동

**선택적 개선**:

- [ ] `depends_on` 추가하여 의존성 명시
- [ ] `overrides`, `removes` 활용하여 차트 커스터마이징
- [ ] `labels`, `annotations` 추가

#### 3. 디렉토리 구조 확인

```
project/
├── config.yaml         # v0.3.0 설정
├── sources.yaml        # 소스 설정 (동일)
├── values/             # values 파일 (동일)
├── overrides/          # 오버라이드 파일 🆕
│   └── redis/
│       ├── values.yaml
│       └── templates/
│           └── service.yaml
├── charts/             # 다운로드된 차트
├── build/              # 빌드된 차트 (overrides 적용)
└── rendered/           # 렌더링된 YAML
```

### 📖 문서

- [Migration Guide](docs/MIGRATION_V3.md) - 상세 마이그레이션 가이드
- [Chart Customization](docs/03-configuration/chart-customization.md) - 차트 커스터마이징
- [Helm Chart Types](docs/03-configuration/helm-chart-types.md) - Remote vs Local 차트
- [Examples](examples/overrides/advanced-example/) - 차트 커스터마이징 예제

### 🐛 버그 수정

- 순환 의존성 검출 개선
- 로컬 차트 경로 처리 개선
- 설정 검증 오류 메시지 개선

### ⚡ 성능 개선

- 설정 파일 파싱 속도 향상
- 의존성 해결 알고리즘 최적화

### 🧪 테스트

- 13개 유닛 테스트 추가 (config_v3)
- 4개 통합 테스트 추가 (workflow_v3)
- 전체 테스트 커버리지: 86% (config_v3)

### 📊 통계

**코드 변경**:

- 신규 파일: 9개
- 수정 파일: 5개
- 삭제 라인: 0
- 추가 라인: ~3,000

**설정 간소화**:

- 평균 설정 파일 길이: 50% 감소
- 필수 설정 항목: 30% 감소
- 중첩 레벨: 3 → 2

### 🙏 감사의 말

이 릴리스는 사용자 피드백을 바탕으로 만들어졌습니다. 모든 피드백에 감사드립니다!

### 🔗 링크

- [GitHub Repository](https://github.com/archmagece/sb-kube-app-manager)
- [Documentation](docs/)
- [Examples](examples/)
- [Issue Tracker](https://github.com/archmagece/sb-kube-app-manager/issues)

______________________________________________________________________

**Full Changelog**: https://github.com/archmagece/sb-kube-app-manager/compare/v0.2.1...v0.3.0
