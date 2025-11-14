# Chart Path Structure Refactoring (v0.8.0)

## Overview

**Date**: 2025-01-11
**Version**: v0.8.0
**Type**: Breaking Change
**Issue**: Chart name collisions when using multiple repos or versions

---

## Problem Statement

### Issue Discovery

사용자가 Helm chart prepare 과정에서 중복 문제를 발견:

```yaml
# 문제 시나리오 1: 다른 repo, 같은 chart 이름
apps:
  redis-grafana:
    chart: grafana/loki
    version: 18.0.0

  redis-custom:
    chart: my-company/redis  # ❌ 충돌!
    version: 1.0.0

# 문제 시나리오 2: 같은 chart, 다른 버전
apps:
  redis-old:
    chart: grafana/loki
    version: 18.0.0           # ❌ 덮어쓰기!

  redis-new:
    chart: grafana/loki
    version: 19.0.0
```

### Root Cause

**v0.7.x 경로 구조**:
```
.sbkube/charts/
├── redis/           # ❌ repo 정보 없음
├── grafana/         # ❌ 버전 정보 없음
└── postgresql/
```

**문제점**:
1. `chart_name`만으로 경로 결정 → repo 구분 불가
2. 버전 정보 없음 → 다른 버전 동시 사용 불가
3. `helm pull` → `.sbkube/charts/` → 마지막 다운로드만 남음

---

## Solution Design

### Selected Approach: Option 2 (repo + version)

**새 경로 구조**:
```
.sbkube/charts/
├── grafana/
│   ├── redis-18.0.0/          # ✅ repo + 버전 명시
│   ├── redis-19.0.0/          # ✅ 다른 버전 공존
│   └── postgresql-15.0.0/
├── my-company/
│   └── redis-1.0.0/           # ✅ 다른 repo의 redis
└── grafana/
    └── grafana-latest/        # ✅ 버전 없으면 'latest'
```

**장점**:
- ✅ 모든 충돌 해결 (다른 repo + 다른 버전)
- ✅ 명시적 버전 관리
- ✅ 수동 디버깅 용이

**단점**:
- ⚠️ Breaking Change (마이그레이션 필요)
- ⚠️ 경로가 길어짐

---

## Implementation

### 1. Data Model Changes

**File**: [sbkube/models/config_model.py](sbkube/models/config_model.py)

```python
class HelmApp(ConfigBaseModel):
    # 기존 메서드...

    def get_version_or_default(self) -> str:
        """버전 없으면 'latest' 반환"""
        return self.version if self.version else "latest"

    def get_chart_path(self, charts_dir: Path | str) -> Path | None:
        """repo/chart-version 경로 생성

        Returns:
            Path(".sbkube/charts/grafana/loki-18.0.0")
            또는 None (로컬 차트)
        """
        if not self.is_remote_chart():
            return None

        repo_name = self.get_repo_name()
        chart_name = self.get_chart_name()
        version = self.get_version_or_default()

        return Path(charts_dir) / repo_name / f"{chart_name}-{version}"
```

### 2. Prepare Command Updates

**Files**:
- [sbkube/commands/prepare.py:302-384](sbkube/commands/prepare.py) - `prepare_helm_app()`
- [sbkube/commands/prepare.py:110-192](sbkube/commands/prepare.py) - `prepare_oci_chart()`

**Key Changes**:
```python
# Before (v0.7.x)
chart_dir = charts_dir / chart_name  # .sbkube/charts/redis/

# After (v0.8.0+)
chart_dir = app.get_chart_path(charts_dir)  # .sbkube/charts/grafana/loki-18.0.0/

# Atomic move pattern with UUID-based temp directory
import uuid
# UUID suffix prevents conflicts when multiple sbkube prepare commands run concurrently
temp_extract_dir = chart_dir.parent / f"_temp_{chart_name}_{uuid.uuid4().hex[:8]}"
helm pull ... --untardir str(temp_extract_dir)
extracted_chart_path.rename(chart_dir)
shutil.rmtree(temp_extract_dir)
```

**Safety Features**:
- **UUID-based temp directories**: Prevents concurrent execution conflicts when multiple `sbkube prepare` commands run simultaneously
- **Atomic rename operation**: Final chart directory appears only when fully extracted
- **Automatic cleanup**: Temp directories removed on both success and failure

### 3. Build Command Updates

**File**: [sbkube/commands/build.py:50-98](sbkube/commands/build.py)

```python
# Use new path structure
source_path = app.get_chart_path(charts_dir)

# Legacy path detection
if not source_path or not source_path.exists():
    chart_name = app.get_chart_name()

    # v0.7.1: charts/{chart-name}/
    legacy_v071_path = charts_dir / chart_name

    # v0.7.0: charts/{chart-name}/{chart-name}/
    legacy_v070_path = charts_dir / chart_name / chart_name

    if legacy_v071_path.exists():
        # Show migration guide...
```

### 4. Template Command Updates

**File**: [sbkube/commands/template.py:60-65](sbkube/commands/template.py)

```python
# v0.8.0+ path structure
elif app.is_remote_chart():
    source_path = app.get_chart_path(charts_dir)
    if source_path and source_path.exists():
        chart_path = source_path
```

### 5. Deploy Command Updates

**File**: [sbkube/commands/deploy.py:157-201](sbkube/commands/deploy.py)

```python
# v0.8.0+ path structure with legacy detection
elif app.is_remote_chart():
    source_path = app.get_chart_path(charts_dir)

    if not source_path or not source_path.exists():
        # Legacy path detection + migration guide
        ...
```

---

## Testing

### Test Coverage

**File**: [tests/unit/test_chart_path_v080.py](tests/unit/test_chart_path_v080.py)

**Test Cases**:
1. ✅ `test_get_chart_path_with_version` - 버전 있는 경로
2. ✅ `test_get_chart_path_without_version` - 버전 없으면 'latest'
3. ✅ `test_get_chart_path_different_repos_same_chart` - 다른 repo 충돌 방지
4. ✅ `test_get_chart_path_same_chart_different_versions` - 다른 버전 공존
5. ✅ `test_get_chart_path_local_chart_returns_none` - 로컬 차트는 None
6. ✅ `test_get_version_or_default_with_version` - 버전 추출
7. ✅ `test_get_version_or_default_without_version` - 기본값 'latest'
8. ✅ `test_build_with_new_path_structure` - 새 구조로 빌드
9. ✅ `test_build_detects_legacy_v071_path` - Legacy 경로 감지
10. ✅ `test_build_multiple_charts_same_name_different_repos` - 충돌 시나리오 검증

**Result**: All 10 tests passed ✅

### Legacy Test Updates

**File**: [tests/test_build.py](tests/test_build.py)

기존 테스트를 새 경로 구조에 맞게 업데이트:
```python
# Before (v0.7.x)
charts_dir = tmp_path / "charts" / "grafana"

# After (v0.8.0+)
charts_dir = tmp_path / "charts" / "grafana" / "grafana-6.50.0"
```

---

## Migration Guide

### For End Users

**Step 1: Detect Legacy Path**

```bash
$ sbkube build

❌ Chart found at legacy path (v0.7.1): .sbkube/charts/redis
💡 Migration required (v0.8.0 path structure):
   1. Remove old charts: rm -rf .sbkube/charts
   2. Re-download charts: sbkube prepare --force
```

**Step 2: Execute Migration**

```bash
# Remove old charts
rm -rf .sbkube/charts

# Re-download with new structure
sbkube prepare --force
```

**Step 3: Verify**

```bash
# Check new structure
ls -R .sbkube/charts/

# Expected output:
# .sbkube/charts/grafana/loki-18.0.0/
# .sbkube/charts/grafana/grafana-7.0.6/
```

### For Developers

**Updating Custom Scripts**:

```python
# Before (v0.7.x)
chart_path = charts_dir / app.get_chart_name()

# After (v0.8.0+)
chart_path = app.get_chart_path(charts_dir)
if chart_path:  # None for local charts
    # Use chart_path
```

---

## Documentation Updates

### 1. CHANGELOG.md

Added comprehensive breaking change notice with:
- Problem description
- Migration steps
- Before/After examples
- File changes reference

### 2. directory-structure.md

Added "v0.8.0 Chart Path Structure Migration" section with:
- Visual comparison (before/after)
- Why the change was needed
- Step-by-step migration
- Technical details
- Rollback procedure

---

## Rollback Plan

If issues occur, users can rollback to v0.7.x:

```bash
# Downgrade to v0.7.2
uv add sbkube==0.7.2

# Remove new structure charts
rm -rf .sbkube/charts

# Re-download with old structure
sbkube prepare
```

---

## Lessons Learned

### What Went Well

1. ✅ **Early Detection**: User reported issue before widespread adoption
2. ✅ **Comprehensive Testing**: 10 test cases covering all collision scenarios
3. ✅ **Legacy Detection**: Automatic detection with helpful migration guide
4. ✅ **Clear Documentation**: Migration guide in multiple locations
5. ✅ **Concurrent Execution Safety**: UUID-based temp directories prevent race conditions

### What Could Be Improved

1. ⚠️ **Earlier Design Review**: Path structure should have considered collisions from the start
2. ⚠️ **Breaking Change Impact**: Could have been caught in design phase
3. ⚠️ **Migration Tool**: Could provide automated migration script

### Future Considerations

1. 🔮 **Path Structure Versioning**: Consider version suffix in `.sbkube/` directory
2. 🔮 **Migration Tool**: Automated `sbkube migrate` command
3. 🔮 **Design Reviews**: More thorough collision analysis in future features

---

## Related Issues

- User Report: "helm을 prepare로 pull하는경우에 helmname, chartname이 경로로 잡혀야 중복이 없지 않나?"
- Impact: All users using multiple repos or versions
- Severity: High (data loss risk)

---

## Approval & Sign-off

**Implemented By**: Claude Code (Sonnet 4.5)
**Reviewed By**: Project Maintainer
**Status**: ✅ Completed
**Release Target**: v0.8.0

---

## References

- [CHANGELOG.md](CHANGELOG.md) - Breaking changes section
- [directory-structure.md](docs/05-best-practices/directory-structure.md) - Migration guide
- [config_model.py](sbkube/models/config_model.py) - HelmApp implementation
- [test_chart_path_v080.py](tests/unit/test_chart_path_v080.py) - Test suite
