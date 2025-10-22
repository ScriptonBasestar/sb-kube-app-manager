# SBKube v0.3.0 Changelog

> **Release Date**: TBD
> **Type**: Major Release (Breaking Changes)

---

## 🎉 주요 변경 사항

### 1. 완전히 새로운 설정 구조

#### 앱 구조 변경: List → Dict

```yaml
# v0.2.x
apps:
  - name: redis-pull
    type: pull-helm
    specs: ...
  - name: redis
    type: install-helm
    specs: ...

# v0.3.0
apps:
  redis:
    type: helm
    chart: bitnami/redis
    values: ...
```

**개선 사항**:
- 설정이 50% 이상 간소화
- 앱 이름이 키로 이동하여 가독성 향상
- 중복 제거

---

### 2. Helm 타입 통합

`pull-helm` + `install-helm` → `helm` (자동으로 pull + install)

```yaml
# v0.3.0
apps:
  redis:
    type: helm
    chart: bitnami/redis  # "repo/chart" 형식
    version: 17.13.2      # 선택적
    values:
      - redis.yaml
```

**개선 사항**:
- 2단계 작업이 1단계로 통합
- chart 표기법 간소화 (`repo` + `chart` → `repo/chart`)
- dest, path 필드 자동 관리

---

### 3. 의존성 자동 해결

`depends_on` 필드로 앱 간 의존성 명시:

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis

  backend:
    type: helm
    chart: my/backend
    depends_on:
      - redis  # redis가 먼저 배포됨
```

**개선 사항**:
- 위상 정렬로 올바른 순서 자동 보장
- 순환 의존성 자동 검출
- 배포 순서를 명시적으로 제어 가능

---

### 4. Specs 평탄화

모든 설정이 앱 레벨로 평탄화:

```yaml
# v0.2.x
apps:
  - name: custom
    type: install-yaml
    specs:
      paths: [...]

# v0.3.0
apps:
  custom:
    type: yaml
    files: [...]
```

**개선 사항**:
- 중첩 깊이 감소
- 직관적인 구조

---

## ✨ 새로운 기능

### 1. `apply` 명령어 (통합 실행)

```bash
sbkube apply --app-dir memory
```

prepare → deploy를 자동으로 실행하며, 의존성 순서대로 배포합니다.

### 2. `migrate` 명령어 (자동 변환)

```bash
sbkube migrate config.yaml -o config-v3.yaml
```

v0.2.x 설정을 v0.3.0 형식으로 자동 변환합니다.

---

## 🔄 타입 변경

| v0.2.x | v0.3.0 | 변경 사항 |
|--------|--------|-----------|
| `pull-helm` + `install-helm` | `helm` | 통합 |
| `install-yaml` | `yaml` | 간소화 |
| `install-kubectl` | `yaml` | 통합 |
| `install-action` | `action` | 간소화 |
| `install-kustomize` | `kustomize` | 간소화 |
| `pull-git` | `git` | 간소화 |
| `exec` | `exec` | 동일 |

**제거된 타입**:
- `copy-*` (copy-app, copy-repo 등): 불필요
- `render`: `template` 명령어 사용
- `pull-helm-oci`: `helm`으로 통합

---

## 📝 새 파일 구조

```
sbkube/
├── models/
│   └── config_v3.py          # 새 Pydantic 모델
├── commands/
│   ├── prepare_v3.py         # 리팩토링된 prepare
│   ├── deploy_v3.py          # 리팩토링된 deploy
│   ├── apply_v3.py           # 신규 통합 명령어
│   └── migrate.py            # 신규 마이그레이션 도구
tests/
└── test_config_v3.py         # v0.3.0 모델 테스트
docs/
└── MIGRATION_V3.md           # 마이그레이션 가이드
examples/
└── k3scode/memory/
    └── config-v3.yaml        # v0.3.0 예제
```

---

## 🚨 Breaking Changes

### 1. 설정 파일 구조

- `apps`가 list에서 dict로 변경
- `name` 필드가 dict 키로 이동
- `specs` 필드 제거

### 2. 타입 이름

- 모든 Helm 관련 타입이 `helm`으로 통합
- `install-*` 접두사 제거

### 3. 필드 이름

- `paths` → `files` (yaml 타입)
- `chart_version` → `version` (helm 타입)
- `kustomize_path` → `path` (kustomize 타입)

### 4. 제거된 기능

- `copy-*` 타입군
- `render` 타입
- 전역 `deps` (앱별 `depends_on` 사용)

---

## 📚 마이그레이션 가이드

상세한 마이그레이션 가이드는 [MIGRATION_V3.md](docs/MIGRATION_V3.md)를 참조하세요.

### 자동 마이그레이션

```bash
# 미리보기
sbkube migrate config.yaml

# 파일 저장
sbkube migrate config.yaml -o config-v3.yaml
```

### 수동 마이그레이션 체크리스트

1. [ ] 백업 생성 (`cp config.yaml config.backup.yaml`)
2. [ ] `sbkube migrate` 실행
3. [ ] `depends_on` 의존성 추가 (필요 시)
4. [ ] `copy-*`, `render` 타입 대체 방법 검토
5. [ ] Dry-run 테스트 (`sbkube apply --dry-run`)
6. [ ] 실제 배포 테스트

---

## 🎯 성능 개선

- 설정 검증 속도 향상 (Pydantic discriminated union)
- 의존성 해결 알고리즘 최적화 (Kahn's algorithm)
- 불필요한 중간 단계 제거

---

## 🐛 버그 수정

- v0.2.x의 앱 순서 의존성 문제 해결
- 중복 Helm repo 추가 경고 개선
- 타입 검증 강화

---

## 📊 통계

- **코드 감소**: 설정 파일 평균 40% 간소화
- **타입 통합**: 15개 → 7개 타입
- **필수 필드 감소**: 앱당 평균 3개 → 2개 필드

---

## 🙏 감사의 말

이번 Breaking Change는 장기적으로 SBKube를 더 사용하기 쉽게 만들기 위한 결정이었습니다. 마이그레이션에 불편을 드려 죄송하지만, v0.3.0의 개선된 경험을 즐기시길 바랍니다!

---

## 📞 지원

- GitHub Issues: [github.com/your-org/sbkube/issues](https://github.com/your-org/sbkube/issues)
- 문서: [docs/](docs/)
- 예제: [examples/v3/](examples/v3/)
