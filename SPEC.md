---
type: Technical Specification
audience: Developer
topics: [architecture, requirements, implementation]
llm_priority: medium
last_updated: 2025-01-04
---

# SBKube 기술 명세서 (Technical Specification)

## 1. 프로젝트 개요

### 1.1 프로젝트 정보

- **프로젝트명**: SBKube
- **버전**: 0.1.10
- **라이선스**: MIT
- **개발자**: archmagece <archmagece@users.noreply.github.com>
- **저장소**: https://github.com/ScriptonBasestar/kube-app-manaer

### 1.2 프로젝트 목적

SBKube는 Kubernetes 애플리케이션의 코드화를 위한 CLI 도구입니다. yaml설정에 기반해 helm, yaml 을 순차적으로 설치합니다.

### 1.3 주요 사용 사례

k3s 홈서버, 호스팅k3s서버 애플리케이션 관리

### 1.4 핵심 가치

- **일관성**: 다양한 소스를 통합한 단일 배포 인터페이스
- **자동화**: 수동 작업 최소화를 통한 배포 효율성 향상
- **확장성**: 다양한 애플리케이션 타입 및 배포 방법 지원
- **안정성**: 차후 고려 예정

## 2. 핵심 기능 및 특징

### 2.1 다단계 워크플로우

```
prepare → build → template → deploy
```

**통합 실행**: `sbkube apply` 명령어로 4단계를 자동으로 실행할 수 있습니다.

#### 2.1.0 Apply (통합 워크플로우)

- 4단계를 자동으로 순차 실행
- 환경별 프로파일 지원 (development/staging/production)
- 실패 지점부터 재시작 가능 (`--resume`, `--continue-from`)
- 단계별 실행 제어 (`--from-step`, `--to-step`, `--only`)
- 실시간 진행 상황 표시

#### 2.1.1 Prepare (소스 준비)

- 외부 Helm 저장소에서 차트 다운로드
- Git 리포지토리 클론 및 소스 복사
- OCI 차트 풀링

#### 2.1.2 Build (앱 빌드)

- 다운로드된 소스를 배포 가능한 형태로 변환
- 로컬 파일 및 설정 복사
- 의존성 해결 및 패키지화

#### 2.1.3 Template (템플릿 렌더링)

- Helm 차트를 YAML 매니페스트로 렌더링
- 환경별 설정 값 적용
- 최종 배포 매니페스트 생성

#### 2.1.4 Deploy (배포 실행)

- Kubernetes 클러스터에 리소스 배포
- Helm 릴리스 설치/업그레이드
- 사용자 정의 스크립트 실행

### 2.2 강력한 설정 관리

- **Pydantic 기반 타입 검증**: 런타임 설정 검증 및 IDE 지원
- **JSON 스키마 지원**: 자동 스키마 생성 및 검증
- **계층적 설정 구조**: 전역 설정과 앱별 설정 분리
- **환경별 설정**: 개발/스테이징/프로덕션 환경 구분

### 2.3 상태 관리 시스템

- **SQLAlchemy 기반 데이터베이스**: 배포 상태 추적
- **히스토리 관리**: 시간순 배포 기록 보존
- **롤백 지원**: 이전 상태로 안전한 되돌리기
- **상태 쿼리**: 현재 배포 상태 및 히스토리 조회

### 2.4 사용자 친화적 인터페이스

- **Rich 라이브러리**: 색상별 로깅 및 테이블 형태 출력
- **상세 로깅**: --verbose 옵션을 통한 디버깅 정보 제공
- **진행 상태 표시**: 작업 진행도 및 결과 시각화
- **에러 메시지**: 명확한 오류 정보 및 해결 방법 제시

## 3. 아키텍처 설계

### 3.1 시스템 구조

```
sbkube/
├── cli.py                    # 메인 CLI 엔트리포인트
├── commands/                 # 명령어 구현
│   ├── apply.py             # 통합 워크플로우 실행
│   ├── prepare.py           # 소스 준비
│   ├── build.py             # 앱 빌드
│   ├── template.py          # 템플릿 렌더링
│   ├── deploy.py            # 배포 실행
│   ├── upgrade.py           # 릴리스 업그레이드
│   ├── delete.py            # 리소스 삭제
│   ├── validate.py          # 설정 검증
│   ├── version.py           # 버전 정보
│   └── state.py             # 상태 관리
├── models/                  # 데이터 모델
│   ├── config_model.py      # 앱 설정 모델
│   ├── sources_model.py     # 소스 설정 모델
│   ├── deployment_state.py  # 배포 상태 모델
│   └── validators.py        # 검증 로직
├── state/                   # 상태 관리 시스템
│   ├── database.py          # SQLAlchemy 데이터베이스
│   ├── tracker.py           # 상태 추적
│   └── rollback.py          # 롤백 관리
└── utils/                   # 유틸리티
    ├── base_command.py      # 명령어 기본 클래스
    ├── logger.py            # Rich 기반 로깅
    ├── cli_check.py         # CLI 도구 검증
    ├── common.py            # 공통 함수
    ├── helm_util.py         # Helm 유틸리티
    └── file_loader.py       # 파일 로딩
```

### 3.2 핵심 아키텍처 패턴

#### 3.2.1 BaseCommand 패턴

모든 명령어는 `BaseCommand` 클래스를 상속하여 일관된 동작을 제공합니다:

- 공통 설정 로딩
- 표준화된 에러 처리
- 확장 가능한 구조

#### 3.2.2 Pydantic 모델 시스템

강력한 타입 검증과 데이터 모델링:

- 런타임 타입 검증
- JSON 스키마 자동 생성
- IDE 지원 및 자동완성

#### 3.2.3 Rich Console 시스템

사용자 친화적 콘솔 출력:

- 색상별 로깅 레벨
- 테이블 형태 정보 표시
- 진행 상태 시각화

### 3.3 데이터 흐름

```
설정 파일 → Pydantic 모델 → 검증 → 명령어 실행 → 상태 저장
```

## 4. 워크플로우 및 명령어 체계

### 4.1 전역 옵션

```bash
sbkube [전역옵션] <명령어> [명령어옵션]
```

- `--kubeconfig <경로>`: Kubernetes 설정 파일 경로
- `--context <이름>`: 사용할 Kubernetes 컨텍스트
- `--namespace <네임스페이스>`: 작업 수행할 기본 네임스페이스
- `-v, --verbose`: 상세 로깅 활성화

### 4.2 명령어 체계

#### 4.2.1 prepare - 소스 준비

```bash
sbkube prepare [옵션]
```

- 외부 소스 다운로드 및 준비
- Helm 저장소, Git 리포지토리, OCI 차트 지원
- 생성 디렉토리: `charts/`, `repos/`

#### 4.2.2 build - 앱 빌드

```bash
sbkube build [옵션]
```

- 준비된 소스를 배포 가능한 형태로 변환
- 로컬 파일 복사 및 의존성 해결
- 생성 디렉토리: `build/`

#### 4.2.3 template - 템플릿 렌더링

```bash
sbkube template [옵션]
```

- Helm 차트 및 YAML 파일 렌더링
- 환경별 설정 값 적용
- 생성 디렉토리: `rendered/`

#### 4.2.4 deploy - 배포 실행

```bash
sbkube deploy [옵션]
```

- Kubernetes 클러스터에 배포
- Helm 릴리스 설치 및 YAML 적용
- Dry-run 지원

#### 4.2.5 upgrade - 릴리스 업그레이드

```bash
sbkube upgrade [옵션]
```

- 기존 Helm 릴리스 업그레이드
- 존재하지 않을 경우 새로 설치

#### 4.2.6 delete - 리소스 삭제

```bash
sbkube delete [옵션]
```

- 배포된 리소스 제거
- Helm 릴리스 삭제 및 YAML 리소스 제거

#### 4.2.7 validate - 설정 검증

```bash
sbkube validate [TARGET_FILE] [옵션]
```

- 설정 파일 유효성 검증 (config.yaml, sources.yaml)
- JSON 스키마 및 Pydantic 모델 검증
- 앱 그룹 의존성 검증 (config 파일만)
- 지원 옵션:
  - `--app-dir <디렉토리>`: 앱 설정 디렉토리
  - `--config-file <파일>`: 설정 파일 이름 (기본: config.yaml)
  - `--schema-type <타입>`: 파일 종류 (config 또는 sources)

#### 4.2.8 state - 상태 관리

```bash
sbkube state <하위명령어> [옵션]
```

- `list`: 배포 상태 목록 조회
- `rollback`: 특정 배포로 롤백
- `history`: 배포 히스토리 조회

#### 4.2.9 version - 버전 정보

```bash
sbkube version
```

- 현재 CLI 버전 표시

### 4.3 일반적인 워크플로우

#### 기본 배포 워크플로우

```bash
sbkube prepare
sbkube build
sbkube template --output-dir ./manifests
sbkube deploy
```

#### 부분 배포 워크플로우

```bash
sbkube prepare --app database
sbkube build --app database
sbkube deploy --app database
```

#### 검증 및 Dry-run 워크플로우

```bash
sbkube validate
sbkube deploy --dry-run
sbkube deploy
```

## 5. 설정 파일 구조

### 5.1 config.yaml 스키마

```yaml
namespace: <기본 네임스페이스>
deps: []

apps:
  - name: <앱 이름>
    type: <앱 타입>
    enabled: true
    namespace: <앱별 네임스페이스>
    release_name: <Helm 릴리스 이름>
    specs:
      # 앱 타입별 설정
```

### 5.2 sources.yaml 스키마

```yaml
helm_repos:
  - name: <저장소 이름>
    url: <저장소 URL>

git_repos:
  - name: <저장소 이름>
    url: <Git URL>
    ref: <브랜치/태그>
```

### 5.3 앱 타입별 설정

#### 5.3.1 pull-helm

```yaml
specs:
  repo: <Helm 저장소 이름>
  chart: <차트 이름>
  version: <차트 버전>
  dest: <저장 경로>
```

#### 5.3.2 install-helm

```yaml
specs:
  path: <차트 경로>
  values:
    - <값 파일 경로>
```

#### 5.3.3 install-yaml

```yaml
specs:
  actions:
    - type: apply
      path: <YAML 파일 경로>
```

#### 5.3.4 copy-app

```yaml
specs:
  paths:
    - src: <소스 경로>
      dest: <대상 경로>
```

#### 5.3.5 exec

```yaml
specs:
  commands:
    - <실행할 명령어>
```

## 6. 지원하는 애플리케이션 타입

### 6.1 소스 준비 타입

- **pull-helm**: Helm 저장소에서 차트 다운로드
- **pull-helm-oci**: OCI 레지스트리에서 차트 다운로드
- **pull-git**: Git 리포지토리 클론
- **copy-app**: 로컬 파일 복사

### 6.2 배포 타입

- **install-helm**: Helm 차트 설치
- **install-yaml**: YAML 매니페스트 적용
- **install-action**: 사용자 정의 스크립트 실행
- **exec**: 임의 명령어 실행

### 6.3 타입별 지원 명령어

| 앱 타입 | prepare | build | template | deploy | upgrade | delete |
|---------|---------|-------|----------|--------|---------|---------| | pull-helm | ✓ | ✓ | - | - | - | - | |
pull-helm-oci | ✓ | ✓ | - | - | - | - | | pull-git | ✓ | ✓ | - | - | - | - | | copy-app | - | ✓ | - | - | - | - | |
install-helm | - | - | ✓ | ✓ | ✓ | ✓ | | install-yaml | - | - | ✓ | ✓ | - | ✓ | | install-action | - | - | - | ✓ | - | ✓
| | exec | - | - | - | ✓ | - | - |

## 7. 사용 사례 및 예제

### 7.1 완전한 워크플로우 예제

#### 설정 파일 (config.yaml)

```yaml
namespace: complete-example

apps:
  # 소스 준비
  - name: grafana-chart-pull
    type: pull-helm
    specs:
      repo: grafana
      chart: grafana
      version: "6.50.0"
      dest: grafana

  # 로컬 리소스 복사
  - name: config-copy
    type: copy-app
    specs:
      paths:
        - src: local-configs
          dest: configs

  # 애플리케이션 배포
  - name: redis-deployment
    type: install-helm
    specs:
      path: redis
      values:
        - redis-values.yaml

  # 모니터링 설정
  - name: monitoring-setup
    type: install-yaml
    specs:
      actions:
        - type: apply
          path: manifests/monitoring.yaml

  # 배포 후 확인
  - name: post-install-check
    type: exec
    specs:
      commands:
        - echo "Checking deployment status..."
        - kubectl get pods -n complete-example
```

#### 소스 설정 (sources.yaml)

```yaml
helm_repos:
  - name: grafana
    url: https://grafana.github.io/helm-charts

git_repos:
  - name: example-app
    url: https://github.com/example/app.git
    ref: main
```

### 7.2 실행 예제

```bash
# 전체 워크플로우
sbkube prepare --app-dir config
sbkube build --app-dir config
sbkube template --app-dir config --output-dir rendered/
sbkube deploy --app-dir config --namespace complete-example

# 특정 앱만 처리
sbkube prepare --app redis-chart-pull
sbkube build --app redis-chart-pull
sbkube deploy --app redis-deployment

# 상태 확인
sbkube state list
sbkube state history --cluster production
```

## 8. 기술 스택 및 의존성

### 8.1 기본 요구사항

- **Python**: 3.12+
- **Kubernetes**: kubectl 설치 필수
- **Helm**: v3.x 설치 필수

### 8.2 주요 의존성

```python
dependencies = [
    "click>=8.1",          # CLI 프레임워크
    "pyyaml",              # YAML 파일 처리
    "gitpython",           # Git 리포지토리 조작
    "jinja2",              # 템플릿 엔진
    "rich",                # 콘솔 출력 개선
    "pytest>=8.3.5",      # 테스트 프레임워크
    "toml>=0.10.2",        # TOML 파일 처리
    "jsonschema>=4.23.0",  # JSON 스키마 검증
    "pydantic>=2.7.1",     # 데이터 모델링
    "sqlalchemy>=2.0.0",   # 데이터베이스 ORM
]
```

### 8.3 개발 도구

- **Code Quality**: ruff, black, isort, mypy
- **Testing**: pytest, pytest-cov, testcontainers
- **Security**: bandit
- **Pre-commit**: pre-commit hooks

### 8.4 배포 및 패키징

- **Build System**: hatchling
- **Distribution**: PyPI (pip install sbkube)
- **Entry Point**: sbkube 명령어

## 9. 확장성 및 향후 계획

### 9.1 현재 확장 가능한 설계

- **새로운 앱 타입 추가**: 모델 및 핸들러 확장
- **새로운 명령어 추가**: BaseCommand 패턴 활용
- **커스텀 검증 로직**: validators 모듈 확장

### 9.2 단기 계획

- **성능 최적화**: 병렬 처리 및 캐싱 개선
- **에러 처리 강화**: 더 상세한 오류 정보 제공
- **테스트 커버리지 향상**: E2E 테스트 확장

### 9.3 중장기 계획

- **플러그인 시스템**: 외부 플러그인을 통한 기능 확장
- **웹 UI**: 상태 관리를 위한 웹 대시보드
- **고급 상태 관리**: 분산 잠금, 클러스터 간 동기화
- **멀티 클러스터 지원**: 여러 클러스터 동시 관리

### 9.4 확장 로드맵

```
v0.2.x: 플러그인 시스템 도입
v0.3.x: 웹 UI 베타 버전
v0.4.x: 멀티 클러스터 지원
v0.5.x: 고급 상태 관리
v1.0.x: 안정 버전 릴리스
```

______________________________________________________________________

*이 문서는 SBKube v0.1.10 기준으로 작성되었으며, 향후 업데이트에 따라 변경될 수 있습니다.*
