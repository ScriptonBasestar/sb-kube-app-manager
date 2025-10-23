# Changelog - SBKube v0.3.0

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

| 기능 | v0.2.x | v0.3.0 | 상태 |
|------|--------|--------|------|
| 차트 다운로드 | `sbkube prepare` | `sbkube prepare` | ✅ 동일 |
| 차트 커스터마이징 | `sbkube build` | `sbkube build` | ✅ 강화 |
| YAML 렌더링 | `sbkube template` | `sbkube template` | ✅ 개선 |
| 클러스터 배포 | `sbkube deploy` | `sbkube deploy` | ✅ 강화 |
| 통합 실행 | `sbkube apply` | `sbkube apply` | ✅ build 단계 추가 |
| 마이그레이션 | - | `sbkube migrate` | 🆕 신규 |

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

| 타입 | v0.2.x | v0.3.0 | 설명 |
|------|--------|--------|------|
| Helm | `pull-helm` + `install-helm` | `helm` | Helm 차트 (통합) |
| YAML | `install-yaml` | `yaml` | YAML 매니페스트 |
| Action | `install-action` | `action` | 커스텀 액션 |
| Kustomize | `install-kustomize` | `kustomize` | Kustomize |
| Git | `pull-git` | `git` | Git 리포지토리 |
| Exec | `exec` | `exec` | 커스텀 명령어 |
| HTTP | - | `http` | HTTP 다운로드 🆕 |

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

---

**Full Changelog**: https://github.com/archmagece/sb-kube-app-manager/compare/v0.2.1...v0.3.0
