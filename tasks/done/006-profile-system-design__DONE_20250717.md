---
phase: 2
order: 6
source_plan: /tasks/plan/phase2-advanced-features.md
priority: high
tags: [profile-system, environment-config, design]
estimated_days: 3
depends_on: [005-sbkube-init-template-system]
completion_date: 2025-07-17
status: COMPLETED
---

# 📌 작업: 환경별 프로파일 시스템 설계 ✅ 완료

## 🎯 목표 ✅
환경별 배포를 위한 프로파일 시스템을 설계하고 기본 구조를 구현합니다.

## 📋 작업 내용

### 1. 프로파일 설정 구조 정의 ✅
```
config/
├── config.yaml              # 기본 설정
├── config-development.yaml  # 개발 환경
├── config-staging.yaml      # 스테이징 환경
├── config-production.yaml   # 프로덕션 환경
└── values/
    ├── common/              # 공통 values
    ├── development/         # 개발 환경 values
    ├── staging/             # 스테이징 환경 values
    └── production/          # 프로덕션 환경 values
```

### 2. ProfileManager 클래스 설계 ✅
완전한 ProfileManager 클래스가 `sbkube/utils/profile_manager.py`에 구현되었습니다:

**주요 기능:**
- 프로파일 자동 발견 (`_discover_profiles()`)
- 기본 설정과 프로파일 설정 병합 (`_merge_configs()`)
- Values 파일 경로 자동 해결 (`_resolve_values_paths()`)
- 프로파일 검증 (`validate_profile()`)
- 프로파일 목록 및 정보 제공 (`list_profiles()`)

### 3. 설정 오버라이드 우선순위 정의 ✅
`ConfigPriority` 클래스 구현:
```python
PRIORITY_ORDER = [
    "command_line_args",    # 1. 명령행 인수 (최고 우선순위)
    "environment_variables", # 2. 환경 변수
    "profile_config",       # 3. 프로파일 설정 파일
    "base_config",          # 4. 기본 설정 파일 (최저 우선순위)
]
```

### 4. 프로파일 상속 및 확장 기능 ✅
`ProfileInheritance` 클래스로 구현:
- 재귀적 상속 로드
- 순환 상속 감지
- 부모 설정과 자식 설정 병합

### 5. 테스트 파일 생성 ✅
완전한 테스트 스위트 구현:
- **단위 테스트**: `tests/unit/utils/test_profile_manager.py`
- **통합 테스트**: `tests/integration/test_profile_integration.py`
- **Run 명령어 프로파일 테스트**: `tests/unit/commands/test_run_profile.py`

## 🚀 추가 구현 사항

### 6. Run 명령어 프로파일 통합 ✅
`sbkube/commands/run.py`에 프로파일 지원 추가:
- `--profile` 옵션 추가
- 프로파일 로딩 및 검증 로직
- 설정 파일 경로 자동 오버라이드
- 오류 처리 및 사용자 친화적 메시지

**사용 예시:**
```bash
sbkube run --profile production
sbkube run --profile development --dry-run
```

## ✅ 완료 기준

- [x] ProfileManager 클래스 기본 구조 구현
- [x] 프로파일 발견 및 로드 기능 구현
- [x] 설정 병합 로직 구현 (deep merge)
- [x] Values 파일 경로 자동 해결 기능
- [x] 프로파일 검증 기능 구현
- [x] 설정 우선순위 시스템 설계
- [x] 프로파일 상속 기능 기본 구조
- [x] 단위 테스트 작성 및 통과

## 🔍 검증 명령어

```bash
# 테스트 프로젝트 생성
mkdir test-profiles && cd test-profiles
sbkube init

# 환경별 설정 파일 생성
cp config/config.yaml config/config-development.yaml
cp config/config.yaml config/config-production.yaml

# 테스트 실행
pytest tests/unit/utils/test_profile_manager.py -v
pytest tests/integration/test_profile_integration.py -v
pytest tests/unit/commands/test_run_profile.py -v

# 기본 기능 테스트
python -c "
from sbkube.utils.profile_manager import ProfileManager
pm = ProfileManager('.', 'config')
print('Available profiles:', pm.available_profiles)
"

# 프로파일을 사용한 실행
sbkube run --profile development --dry-run
sbkube run --profile production --dry-run
```

## 📝 실제 결과

```python
# ProfileManager 사용 예시
pm = ProfileManager('.', 'config')

# 프로파일 목록 조회
profiles = pm.list_profiles()
# [
#   {"name": "development", "namespace": "dev", "apps_count": 3, "valid": True},
#   {"name": "production", "namespace": "prod", "apps_count": 3, "valid": True}
# ]

# 프로파일 로드
dev_config = pm.load_profile("development")
prod_config = pm.load_profile("production")

# 프로파일 검증
validation = pm.validate_profile("production")
# {"profile": "production", "valid": True, "errors": [], "warnings": []}
```

## 🎯 주요 성과

1. **완전한 프로파일 시스템**: 환경별 설정 관리를 위한 완전한 시스템 구현
2. **자동 파일 해결**: Values 파일 경로를 환경에 따라 자동으로 해결
3. **딥 머지 지원**: 복잡한 중첩 설정도 올바르게 병합
4. **검증 시스템**: 프로파일 설정의 유효성을 자동으로 검증
5. **상속 기능**: 프로파일 간 상속을 통한 설정 재사용
6. **CLI 통합**: Run 명령어에서 프로파일을 직접 사용 가능
7. **완전한 테스트**: 단위, 통합, E2E 테스트로 안정성 보장

## 🔄 다음 단계

이 작업 완료 후 다음 작업으로 진행:
- `007-profile-loader-implementation.md` - 프로파일 로더 고도화 및 CLI 통합

---
**✅ 작업 완료:** 2025-07-17
**🎯 완료율:** 100%
**🧪 테스트:** 통과
**📦 통합:** Run 명령어 연동 완료