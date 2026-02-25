# SBKube 버전 마이그레이션 가이드

> **이 문서는 주요 버전 변경 시 마이그레이션 가이드를 제공합니다.**

## v0.7.x → v0.8.0 마이그레이션

> **소요 시간**: 5-10분 **난이도**: 쉬움 **필수 작업**: ✅ 필수 (Breaking Changes 포함)

______________________________________________________________________

## 🎯 TL;DR (빠른 마이그레이션)

```bash
# 1. 백업 (선택)
cp -r .sbkube/charts .sbkube/charts.backup

# 2. 구 charts 제거
rm -rf .sbkube/charts

# 3. 신 구조로 재다운로드
sbkube prepare --force

# 4. 배포
sbkube apply

# Done! ✅
```

______________________________________________________________________

## ⚠️ 주요 변경사항

### Chart 경로 구조 변경

**Before (v0.7.x)**:

```
.sbkube/charts/redis/              # ❌ repo/version 정보 없음
.sbkube/charts/grafana/            # ❌ 충돌 위험
```

**After (v0.8.0)**:

```
.sbkube/charts/grafana/loki-18.0.0/      # ✅ repo + version
.sbkube/charts/grafana/grafana-6.50.0/    # ✅ 명확한 식별
```

**왜 바뀌었나?**

- 같은 이름의 chart가 다른 repo에 있을 때 충돌 방지
- 같은 chart의 다른 버전 동시 사용 가능
- 명확한 버전 추적

______________________________________________________________________

## 📋 시나리오별 마이그레이션

### Case 1: 단순 Helm 차트만 사용 (90% 케이스)

**설정 파일 (config.yaml)**:

```yaml
apps:
  redis:
    type: helm
    chart: grafana/loki
    version: 18.0.0
```

**✅ 설정 파일은 변경 없음!**

**마이그레이션**:

```bash
# 1. 구 charts 제거
rm -rf .sbkube/charts

# 2. 재다운로드
sbkube prepare --force

# 3. 확인
ls .sbkube/charts/grafana/
# Expected: redis-18.0.0/

# 4. 배포
sbkube apply
```

______________________________________________________________________

### Case 2: Chart Overrides 사용하는 경우

**Before (v0.7.x)**:

```
project/
├── config/
│   └── config.yaml
├── overrides/
│   └── grafana/
│       └── values.yaml       # overrides 경로
└── .sbkube/
    └── charts/
        └── grafana/          # 구 chart 경로
```

**After (v0.8.0)**:

```
project/
├── config/
│   └── config.yaml
├── overrides/
│   └── grafana/
│       └── values.yaml       # ✅ overrides 경로는 동일!
└── .sbkube/
    └── charts/
        └── grafana/
            └── grafana-6.50.0/  # 신 chart 경로
```

**✅ overrides 디렉터리 경로는 변경 불필요!**

**config.yaml**:

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    overrides:
      - values.yaml           # ✅ 그대로 사용
      - templates/deployment.yaml
```

**마이그레이션**:

```bash
# overrides 디렉터리는 그대로 두고
rm -rf .sbkube/charts
sbkube prepare --force
sbkube apply
```

______________________________________________________________________

### Case 3: 여러 버전 공존 필요 (v0.8.0 신기능)

**시나리오**: redis 18.0.0과 19.0.0을 다른 앱에서 사용

**Before (v0.7.x)**: ❌ 불가능 - 하나만 선택 가능

**After (v0.8.0)**: ✅ 가능!

**config.yaml**:

```yaml
apps:
  cache:
    type: helm
    chart: grafana/loki
    version: 18.0.0
    release_name: redis-cache

  session:
    type: helm
    chart: grafana/loki
    version: 19.0.0
    release_name: redis-session
```

**결과**:

```
.sbkube/charts/grafana/
├── redis-18.0.0/
└── redis-19.0.0/
```

**마이그레이션**:

```bash
rm -rf .sbkube/charts
sbkube prepare --force

# 확인
ls .sbkube/charts/grafana/
# Expected: redis-18.0.0/ redis-19.0.0/

sbkube apply
```

______________________________________________________________________

### Case 4: 다른 Repo의 동일 이름 Chart (v0.8.0 신기능)

**시나리오**: grafana/loki와 my-company/redis 동시 사용

**Before (v0.7.x)**: ❌ 불가능 - 충돌 발생

**After (v0.8.0)**: ✅ 가능!

**config.yaml**:

```yaml
apps:
  public-cache:
    type: helm
    chart: grafana/loki
    version: 18.0.0

  internal-cache:
    type: helm
    chart: my-company/redis
    version: 1.0.0
```

**결과**:

```
.sbkube/charts/
├── grafana/
│   └── redis-18.0.0/
└── my-company/
    └── redis-1.0.0/
```

______________________________________________________________________

## 🔍 마이그레이션 전 체크리스트

- [ ] 현재 버전 확인: `sbkube version` (v0.7.x인지 확인)
- [ ] 백업 생성: `cp -r .sbkube/charts .sbkube/charts.backup`
- [ ] 현재 배포 상태 확인: `kubectl get all -n <namespace>`
- [ ] Git에 변경사항 커밋 (롤백 대비)

______________________________________________________________________

## 🚀 단계별 마이그레이션

### Step 1: 백업 (선택사항, 권장)

```bash
# Charts 백업
cp -r .sbkube/charts .sbkube/charts.backup

# Config 백업
cp config.yaml config.yaml.backup
```

### Step 2: SBKube 업그레이드

```bash
# Using uv (권장)
uv add sbkube==0.8.0

# Or using pip
pip install --upgrade sbkube==0.8.0

# 버전 확인
sbkube version
# Expected: 0.8.0
```

### Step 3: 구 Charts 제거

```bash
# .sbkube/charts 제거
rm -rf .sbkube/charts

# 확인
ls .sbkube/
# charts/ 디렉터리가 없어야 함
```

### Step 4: 신 구조로 재다운로드

```bash
# 새 경로 구조로 다운로드
sbkube prepare --force

# 새 구조 확인
ls -R .sbkube/charts/
# Expected: charts/{repo}/{chart-name}-{version}/
```

**예상 출력**:

```
.sbkube/charts/:
grafana/  grafana/

.sbkube/charts/grafana:
redis-18.0.0/

.sbkube/charts/grafana:
grafana-6.50.0/
```

### Step 5: 검증 (v0.8.0 신기능!)

```bash
# 설정 검증 + PV/PVC 체크
sbkube validate

# 예상 출력:
# ✅ Configuration valid
# ✅ All dependencies resolved
# ✅ Storage validated (or warnings if PV missing)
```

### Step 6: 배포

```bash
# Dry-run으로 먼저 확인
sbkube apply --dry-run

# 실제 배포
sbkube apply

# 배포 상태 확인
sbkube status
kubectl get all -n <namespace>
```

______________________________________________________________________

## 🐛 트러블슈팅

### Issue 1: "Chart not found" 에러

**증상**:

```
❌ Chart not found at .sbkube/charts/redis/
```

**원인**: 구 경로 참조

**해결**:

```bash
# 1. Charts 완전 제거
rm -rf .sbkube/charts

# 2. 재다운로드
sbkube prepare --force

# 3. 확인
ls -R .sbkube/charts/
```

______________________________________________________________________

### Issue 2: Overrides가 적용 안됨

**증상**: 커스터마이징이 반영되지 않음

**원인**: overrides 경로는 변경 불필요 - 다른 문제

**해결**:

```bash
# 1. 검증으로 문제 확인
sbkube validate

# 2. overrides 경로 확인
ls overrides/grafana/
# values.yaml이 있어야 함

# 3. config.yaml 확인
# overrides: ["values.yaml"]  # 경로는 동일
```

______________________________________________________________________

### Issue 3: 여러 버전 충돌

**증상**: 같은 chart의 다른 버전 사용 시 에러

**원인**: v0.7.x로 다운받은 chart 잔재

**해결**:

```bash
# 완전 초기화
rm -rf .sbkube/charts
rm -rf .sbkube/repos

sbkube prepare --force
```

______________________________________________________________________

### Issue 4: "Legacy path detected" 경고

**증상**:

```
⚠️  Legacy path detected: .sbkube/charts/redis/
💡 Migration required (v0.8.0)
```

**의미**: v0.7.x 구조가 남아있음

**해결**: Step 3-4 반복 (charts 제거 → 재다운로드)

______________________________________________________________________

## 🔄 롤백 (필요 시)

v0.8.0으로 마이그레이션 후 문제 발생 시:

### Option 1: SBKube만 롤백

```bash
# 1. v0.7.2로 다운그레이드
uv add sbkube==0.7.2

# 2. Charts 재다운로드
rm -rf .sbkube/charts
sbkube prepare

# 3. 배포
sbkube apply
```

### Option 2: 백업 복원

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

## ✅ 마이그레이션 성공 확인

```bash
# 1. 버전 확인
sbkube version
# Expected: 0.8.0

# 2. Chart 경로 확인
ls -R .sbkube/charts/
# Expected: {repo}/{chart-name}-{version}/ 구조

# 3. 배포 상태 확인
sbkube status
# 모든 앱이 정상 작동해야 함

# 4. 검증
sbkube validate
# ✅ All checks passed
```

______________________________________________________________________

## 💡 FAQ

### Q: 설정 파일(config.yaml)을 변경해야 하나요?

**A**: ❌ 아니요! 설정 파일은 **변경 불필요**합니다.

- `chart: grafana/loki` → 그대로
- `version: 18.0.0` → 그대로
- `overrides: [...]` → 그대로

**변경되는 것**: `.sbkube/charts/` 디렉터리 내부 구조만!

______________________________________________________________________

### Q: overrides 디렉터리도 변경해야 하나요?

**A**: ❌ 아니요! overrides 경로는 **변경 불필요**입니다.

```
overrides/
└── grafana/
    └── values.yaml    # ✅ 그대로 사용
```

______________________________________________________________________

### Q: 마이그레이션 중 서비스 다운타임이 있나요?

**A**: ❌ 없습니다!

- `.sbkube/charts/`는 로컬 캐시일 뿐
- Kubernetes 클러스터의 실행 중인 앱은 영향 없음
- 재배포 전까지 기존 앱은 계속 작동

______________________________________________________________________

### Q: 부분 마이그레이션 가능한가요?

**A**: ❌ 권장하지 않습니다.

- v0.8.0은 모든 charts를 새 구조로 다운로드
- 일부만 마이그레이션하면 혼란 발생
- **전체 마이그레이션 권장** (5분이면 완료)

______________________________________________________________________

### Q: Git에 .sbkube/charts를 커밋했는데?

**A**: ⚠️ `.sbkube/`는 Git에 **절대 커밋하지 않아야** 합니다!

```bash
# .gitignore에 추가
echo ".sbkube/" >> .gitignore

# Git에서 제거
git rm -r --cached .sbkube/
git commit -m "Remove .sbkube/ from git"
```

**이유**:

- `.sbkube/`는 로컬 캐시 (node_modules처럼)
- `sbkube prepare`로 언제든 재생성 가능
- 용량 낭비 및 충돌 위험

______________________________________________________________________

### Q: 여러 환경(dev/staging/prod)을 사용하는데?

**A**: 각 환경에서 독립적으로 마이그레이션:

```bash
# Dev 환경
cd dev-config/
rm -rf .sbkube/charts
sbkube prepare --force

# Staging 환경
cd ../staging-config/
rm -rf .sbkube/charts
sbkube prepare --force

# Production 환경 (가장 나중에)
cd ../prod-config/
rm -rf .sbkube/charts
sbkube prepare --force
```

______________________________________________________________________

## 📚 참고 자료

- [CHANGELOG.md](../../CHANGELOG.md) - 전체 릴리스 노트
- [Migration Guide](../03-configuration/migration-guide.md) - 공식 마이그레이션 가이드
- [CHANGELOG.md](../../CHANGELOG.md) - 변경 이력
- [Chart Path Refactoring](../10-modules/sbkube/CHART_PATH_REFACTORING_v080.md) - 기술 세부사항

______________________________________________________________________

## 🎯 다음 단계

마이그레이션 완료 후:

1. **새 기능 활용**:

   - `sbkube validate` - PV/PVC 검증
   - 여러 버전 chart 동시 사용
   - 다른 repo의 동일 이름 chart 사용

1. **문서 확인**:

   - [Storage Management](../05-best-practices/storage-management.md)
   - [Configuration Guide](../03-configuration/config-schema.md)

1. **팀 공유**:

   - 팀원들에게 마이그레이션 가이드 공유
   - CI/CD 파이프라인 업데이트

______________________________________________________________________

**마이그레이션 완료!** 🎉

문제가 발생하면 [Troubleshooting Guide](../07-troubleshooting/)를 참고하세요.
