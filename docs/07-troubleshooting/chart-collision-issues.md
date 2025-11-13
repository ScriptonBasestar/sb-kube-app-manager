# Chart 충돌 문제 해결 가이드

> **대상**: v0.7.x 사용자가 v0.8.0으로 마이그레이션 시 발생하는 chart 충돌 문제 **난이도**: 쉬움 **소요 시간**: 5-15분

______________________________________________________________________

## 🎯 개요

v0.8.0 이전 버전에서는 chart 경로가 `charts/{chart-name}/`으로 단순했기 때문에, 다음과 같은 충돌 문제가 발생했습니다:

1. **동일 이름, 다른 Repo**: `bitnami/redis`와 `my-company/redis`
1. **동일 Chart, 다른 버전**: `redis:18.0.0`과 `redis:19.0.0`

v0.8.0부터는 `charts/{repo}/{chart-name}-{version}/` 구조로 변경되어 이러한 문제가 **자동으로 해결**됩니다.

______________________________________________________________________

## 🚨 증상별 트러블슈팅

### Symptom 1: "Chart already exists" 에러

#### 증상

```
❌ Error: Chart 'redis' already exists at .sbkube/charts/redis/
Cannot download from different repo 'my-company/redis'
```

#### 원인

- v0.7.x에서 같은 이름의 chart를 다른 repo에서 다운로드 시도
- 기존 chart 디렉토리가 덮어써지거나 충돌 발생

#### 해결 (v0.8.0+)

```bash
# 1. v0.8.0으로 업그레이드
uv add sbkube==0.8.0

# 2. 구 charts 제거
rm -rf .sbkube/charts

# 3. 신 구조로 재다운로드
sbkube prepare --force

# 4. 확인
ls -R .sbkube/charts/
# Expected:
# .sbkube/charts/bitnami/redis-18.0.0/
# .sbkube/charts/my-company/redis-1.0.0/
```

**결과**: 두 chart가 공존 가능!

______________________________________________________________________

### Symptom 2: 버전 충돌

#### 증상 (v0.7.x)

```yaml
# config.yaml
apps:
  cache:
    chart: bitnami/redis
    version: 18.0.0

  session:
    chart: bitnami/redis
    version: 19.0.0  # ❌ 18.0.0을 덮어쓰거나 충돌
```

```
❌ Error: Chart version mismatch
Expected: 18.0.0, Found: 19.0.0 at .sbkube/charts/redis/
```

#### 원인

- v0.7.x에서 같은 chart의 다른 버전을 동시에 사용 불가
- 마지막 다운로드한 버전만 남음

#### 해결 (v0.8.0+)

```bash
# v0.8.0으로 업그레이드 후
sbkube prepare --force

# 확인
ls .sbkube/charts/bitnami/
# Expected:
# redis-18.0.0/
# redis-19.0.0/
```

**결과**: 두 버전이 독립적으로 존재!

______________________________________________________________________

### Symptom 3: "Remote chart not found" 에러

#### 증상

```
❌ Error: Remote chart not found at .sbkube/charts/redis/
Expected structure: .sbkube/charts/{repo}/{chart-name}-{version}/
```

#### 원인

- v0.8.0으로 업그레이드 후 구 chart 경로가 남아있음
- SBKube가 신 경로에서 chart를 찾으려 하지만 구 경로에만 존재

#### 해결

```bash
# 1. 구 charts 완전 제거
rm -rf .sbkube/charts

# 2. 재다운로드
sbkube prepare --force

# 3. 경로 구조 확인
tree .sbkube/charts/
# Expected:
# charts/
# ├── bitnami/
# │   └── redis-18.0.0/
# └── grafana/
#     └── grafana-6.50.0/
```

______________________________________________________________________

### Symptom 4: "Chart found at legacy path" 경고

#### 증상

```
⚠️  Warning: Chart found at legacy path: .sbkube/charts/redis/
💡 Migration required to v0.8.0 structure
```

#### 의미

- v0.7.x 구조의 chart가 여전히 존재
- 현재는 동작하지만 신 구조로 마이그레이션 권장

#### 해결

```bash
# 옵션 1: 점진적 마이그레이션 (기존 유지하면서)
sbkube prepare --force --migrate-legacy

# 옵션 2: 완전 재다운로드 (권장)
rm -rf .sbkube/charts
sbkube prepare --force
```

______________________________________________________________________

### Symptom 5: Overrides가 적용 안됨

#### 증상

```yaml
# config.yaml
apps:
  grafana:
    chart: grafana/grafana
    version: 6.50.0
    overrides:
      - values.yaml  # ❌ 적용 안됨
```

```
⚠️  Warning: Override file not applied
Expected: overrides/grafana/values.yaml
```

#### 원인 (v0.8.0)

- **overrides 경로는 변경 없음!**
- 다른 문제일 가능성 높음 (파일 경로, YAML 문법 등)

#### 해결

```bash
# 1. overrides 경로 확인
ls overrides/grafana/
# Expected: values.yaml

# 2. 파일 내용 검증
sbkube validate

# 3. YAML 문법 확인
python -c "import yaml; yaml.safe_load(open('overrides/grafana/values.yaml'))"

# 4. 상세 로그로 확인
sbkube apply --log-level DEBUG
```

**중요**: overrides 디렉토리 구조는 v0.8.0에서도 **동일**합니다!

```
overrides/
└── grafana/          # ✅ 변경 없음
    └── values.yaml
```

______________________________________________________________________

## 📋 마이그레이션 체크리스트

### 마이그레이션 전

- [ ] 현재 버전 확인: `sbkube version`
- [ ] 백업 생성: `cp -r .sbkube/charts .sbkube/charts.backup`
- [ ] 현재 배포 상태 확인: `kubectl get all -n <namespace>`
- [ ] Git 커밋 (롤백 대비)

### 마이그레이션 중

- [ ] v0.8.0으로 업그레이드: `uv add sbkube==0.8.0`
- [ ] 구 charts 제거: `rm -rf .sbkube/charts`
- [ ] 신 구조로 다운로드: `sbkube prepare --force`
- [ ] 경로 확인: `ls -R .sbkube/charts/`

### 마이그레이션 후

- [ ] 설정 검증: `sbkube validate`
- [ ] Dry-run 테스트: `sbkube apply --dry-run`
- [ ] 실제 배포: `sbkube apply`
- [ ] 배포 상태 확인: `sbkube status`

______________________________________________________________________

## 🔄 롤백 방법

### v0.7.x로 완전 롤백

```bash
# 1. SBKube 다운그레이드
uv add sbkube==0.7.2

# 2. Charts 재다운로드
rm -rf .sbkube/charts
sbkube prepare

# 3. 배포
sbkube apply
```

### 백업 복원 (빠른 롤백)

```bash
# 1. 백업 복원
rm -rf .sbkube/charts
mv .sbkube/charts.backup .sbkube/charts

# 2. SBKube 롤백
uv add sbkube==0.7.2

# 3. 배포
sbkube apply
```

______________________________________________________________________

## 💡 v0.8.0 장점 요약

### Before (v0.7.x)

```
.sbkube/charts/
├── redis/              # ❌ repo 구분 없음
├── grafana/            # ❌ 버전 구분 없음
└── postgresql/         # ❌ 충돌 위험
```

**문제점**:

- 같은 이름, 다른 repo: 충돌
- 같은 chart, 다른 버전: 덮어쓰기

### After (v0.8.0)

```
.sbkube/charts/
├── bitnami/
│   ├── redis-18.0.0/      # ✅ repo + version
│   ├── redis-19.0.0/      # ✅ 다른 버전 공존
│   └── postgresql-12.0.0/
├── grafana/
│   └── grafana-6.50.0/
└── my-company/
    └── redis-1.0.0/       # ✅ 다른 repo 공존
```

**장점**:

- ✅ 같은 이름, 다른 repo: 공존 가능
- ✅ 같은 chart, 다른 버전: 독립 사용
- ✅ 명확한 버전 추적
- ✅ 캐시 효율성 증가

______________________________________________________________________

## 🔍 디버깅 팁

### Chart 경로 확인

```bash
# 현재 chart 구조 확인
tree .sbkube/charts/ -L 3

# 특정 chart 검색
find .sbkube/charts/ -name "redis*" -type d

# Chart.yaml 내용 확인
cat .sbkube/charts/bitnami/redis-18.0.0/Chart.yaml
```

### 로그 레벨 높이기

```bash
# 상세 로그로 실행
sbkube prepare --log-level DEBUG

# 출력을 파일로 저장
sbkube prepare --log-level DEBUG 2>&1 | tee prepare.log
```

### 검증 명령어 활용

```bash
# 설정 및 chart 구조 검증
sbkube validate

# 예상 출력:
# ✅ Configuration valid
# ✅ All charts found at correct paths
# ✅ Chart versions match config
```

______________________________________________________________________

## 📚 관련 문서

- [v0.8.0 마이그레이션 가이드](../08-tutorials/05-migrating-to-v080.md) - 전체 마이그레이션 절차
- [RELEASE_v0.8.0.md](../RELEASE_v0.8.0.md) - 릴리스 노트
- [Chart Path Refactoring](../10-modules/sbkube/CHART_PATH_REFACTORING_v080.md) - 기술 세부사항
- [CHANGELOG.md](../../CHANGELOG.md) - 변경 이력

______________________________________________________________________

## 🆘 추가 도움이 필요한 경우

1. **일반 트러블슈팅**: [docs/07-troubleshooting/README.md](./README.md)
1. **FAQ**: [docs/07-troubleshooting/faq.md](./faq.md)
1. **GitHub Issues**: [sb-kube-app-manager/issues](https://github.com/your-org/sb-kube-app-manager/issues)

______________________________________________________________________

**마지막 업데이트**: 2025-11-13 **적용 버전**: v0.8.0+
