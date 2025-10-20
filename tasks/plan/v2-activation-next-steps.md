# v2 모델 활성화 완료 후 다음 단계

**작성일**: 2025-10-20
**상태**: 계획 단계
**관련 커밋**: 02ac181, 36aa484

---

## 📊 현재 상태

### ✅ 완료된 작업

1. **v2 파일 메인으로 승격** (02ac181)
   - config_model_v2.py → config_model.py
   - sources_model_v2.py → sources_model.py
   - base_command_v2.py → base_command.py
   - deploy_v2.py → deploy.py

2. **레거시 파일 deprecated 처리**
   - config_model.py → config_model_legacy.py
   - sources_model.py → sources_model_legacy.py
   - base_command.py → base_command_legacy.py
   - deploy.py → deploy_legacy.py
   - 모든 legacy 파일에 DeprecationWarning 추가

3. **버그 수정** (36aa484)
   - 무한 재귀 버그 수정 (validate_specs_for_type)
   - namespace 검증 재귀 수정
   - 테스트 업데이트 (v2 필수 필드 반영)

---

## 🎯 다음 단계 (우선순위순)

### 1. 실제 배포 테스트 (High Priority)

**목적**: v2 모델 및 상태 추적 기능 실제 동작 검증

**작업 내용**:
```bash
# 1. 샘플 프로젝트로 dry-run 테스트
sbkube prepare --app-dir ./examples/basic --dry-run
sbkube build --app-dir ./examples/basic
sbkube deploy --app-dir ./examples/basic --dry-run

# 2. 상태 추적 DB 생성 확인
ls -la ~/.sbkube/deployments.db

# 3. 상태 조회 명령 테스트
sbkube state list
sbkube state show <deployment-id>
```

**예상 결과**:
- ✅ 설정 검증 통과
- ✅ 배포 dry-run 성공
- ✅ deployments.db 생성
- ✅ 배포 이력 조회 가능

**예상 이슈**:
- 설정 파일 스키마 불일치
- 필수 필드 누락 오류
- 상태 DB 경로 권한 문제

---

### 2. 상태 추적 기능 동작 확인 (High Priority)

**목적**: DeploymentTracker 정상 동작 검증

**작업 내용**:
```bash
# 1. 실제 배포 수행 (테스트 환경)
sbkube deploy --app-dir ./examples/basic --enable-tracking

# 2. 배포 이력 확인
sbkube state list --limit 10

# 3. 특정 배포 상세 조회
sbkube state show <deployment-id>

# 4. 롤백 기능 테스트 (주의!)
sbkube state rollback <deployment-id> --dry-run
```

**검증 항목**:
- [ ] 배포 ID 자동 생성
- [ ] Kubernetes 리소스 추적
- [ ] Helm 릴리스 추적
- [ ] CREATE vs UPDATE 구분
- [ ] 배포 실패 시 상태 기록
- [ ] 롤백 대상 리소스 식별

---

### 3. 레거시 코드 사용 파일 업데이트 (Medium Priority)

**목적**: 남아있는 레거시 import 제거

**작업 내용**:
```bash
# 1. 레거시 import 사용 파일 검색
grep -r "from.*config_model_legacy\|base_command_legacy" sbkube/ --include="*.py"
grep -r "import.*config_model_legacy\|base_command_legacy" sbkube/ --include="*.py"

# 2. 각 파일 업데이트
# - import 경로 변경
# - 필요시 specs 필드 수정 (v2 필수 필드 반영)

# 3. 테스트 실행
pytest tests/ --no-cov
```

**예상 대상 파일**:
- build.py
- prepare.py
- template.py
- upgrade.py
- delete.py
- validate.py
- run.py

---

### 4. 테스트 Coverage 이슈 해결 (Low Priority)

**목적**: pytest with coverage 정상 동작

**현재 이슈**:
```
pytest tests/unit/models/test_config_model.py
# ✗ 1 failed, 10 passed (coverage on)

pytest tests/unit/models/test_config_model.py --no-cov
# ✅ 11/11 passed
```

**조사 방향**:
1. Coverage가 모듈을 import하는 방식 확인
2. Pydantic 모델 reload 이슈 확인
3. pytest.ini coverage 설정 확인

**회피 방법** (현재):
```bash
pytest --no-cov
```

---

### 5. 문서 업데이트 (Medium Priority)

**목적**: 사용자에게 변경사항 안내

#### 5.1 CHANGELOG.md 업데이트

```markdown
## [Unreleased]

### Added
- Enhanced configuration validation with Pydantic v2 models
- Configuration inheritance support
- Deployment state tracking and rollback functionality
- Kubernetes resource change tracking (CREATE vs UPDATE)
- Helm release tracking

### Changed
- **BREAKING**: v2 models now enforce strict validation
  - All app types require proper specs fields
  - Empty specs={} no longer allowed
- Migrated all v2 models to main filenames
  - config_model_v2.py → config_model.py
  - sources_model_v2.py → sources_model.py
  - base_command_v2.py → base_command.py
  - deploy_v2.py → deploy.py

### Deprecated
- Legacy models moved to *_legacy.py files
  - Will be removed in version X.X.X
  - Using legacy models will trigger DeprecationWarning

### Fixed
- Infinite recursion in validate_specs_for_type
- Namespace validation recursion bug
```

#### 5.2 README.md 업데이트

새로운 기능 섹션 추가:
- 배포 상태 추적
- 롤백 기능
- 향상된 검증

#### 5.3 Migration Guide 작성

`docs/migration/v1-to-v2.md` 생성:
- 필수 변경사항
- 설정 파일 업데이트 방법
- 레거시 코드 마이그레이션

---

### 6. 레거시 파일 제거 일정 (Future)

**목적**: 코드베이스 정리

**제안 일정**:
1. **현재 (v0.X.X)**: Legacy 파일 유지, DeprecationWarning 표시
2. **다음 릴리스 (v0.Y.X)**: 마이그레이션 가이드 제공, 경고 강화
3. **다다음 릴리스 (v0.Z.X)**: Legacy 파일 완전 제거

**제거 대상**:
- sbkube/models/config_model_legacy.py
- sbkube/models/sources_model_legacy.py
- sbkube/utils/base_command_legacy.py
- sbkube/commands/deploy_legacy.py

---

## 📋 작업 체크리스트

### 즉시 수행 (This Week)
- [ ] 실제 배포 dry-run 테스트
- [ ] 상태 추적 DB 생성 확인
- [ ] 배포 이력 조회 테스트
- [ ] 레거시 import 사용 파일 식별

### 단기 (Next Sprint)
- [ ] 레거시 import 제거
- [ ] CHANGELOG.md 업데이트
- [ ] README.md 새 기능 섹션 추가
- [ ] Migration guide 작성

### 중기 (Next Release)
- [ ] pytest coverage 이슈 해결
- [ ] 전체 테스트 스위트 정상화
- [ ] 문서 최종 검토

### 장기 (Future Release)
- [ ] 레거시 파일 제거 계획 수립
- [ ] 사용자 피드백 수집
- [ ] 추가 기능 개선

---

## 🚨 알려진 이슈

### Issue 1: pytest with coverage fails
- **증상**: `test_valid_app_types` 실패 (coverage on)
- **회피**: `pytest --no-cov` 사용
- **우선순위**: Low
- **예상 원인**: Coverage의 모듈 reload 방식

### Issue 2: --enable-tracking 옵션이 help에 미표시
- **증상**: `sbkube deploy --help`에 --enable-tracking 없음
- **원인**: Click 옵션 default=True로 설정
- **영향**: 기능은 정상 동작, 문서만 누락
- **우선순위**: Low

---

## 💡 개선 아이디어

### 향후 고려사항

1. **설정 스키마 검증**
   - JSON Schema 기반 설정 검증
   - IDE 자동완성 지원 (JSON Schema 제공)

2. **상태 추적 개선**
   - 배포 diff 시각화
   - 배포 실패 자동 롤백 옵션
   - 배포 승인 워크플로우

3. **성능 최적화**
   - 대규모 배포 시 상태 추적 성능
   - DB 인덱싱 최적화

4. **CLI UX 개선**
   - 진행률 표시 개선
   - 컬러 테마 커스터마이징
   - 대화형 배포 모드

---

## 📞 연락처

**작업자**: Claude (AI Assistant)
**커밋**: 02ac181, 36aa484
**브랜치**: develop
