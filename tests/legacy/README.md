# Legacy Tests

이 디렉토리는 리팩토링 이전의 기존 테스트 파일들을 포함합니다.

## ⚠️ 상태: 리팩토링 대상

이 디렉토리의 파일들은 Phase 1 리팩토링에서 분할되지 않은 대용량 테스트 파일들입니다.

## 📁 파일 목록

```
legacy/
├── test_config_validation.py    # 477 라인 - 설정 검증 테스트
├── test_deployment_state.py     # 504 라인 - 배포 상태 테스트  
└── test_full_pipeline.py        # 전체 파이프라인 테스트
```

## 🔄 리팩토링 계획

### test_config_validation.py → 분할 완료 예정
- `unit/models/test_config_model.py` (기본 모델 검증)
- `unit/models/test_validation_errors.py` (오류 처리)
- `integration/test_config_integration.py` (통합 검증)

### test_deployment_state.py → 분할 완료 예정  
- `unit/state/test_deployment_database.py` ✅ 생성됨
- `unit/state/test_deployment_tracker.py` ✅ 생성됨
- `unit/state/test_rollback_manager.py` ✅ 생성됨

### test_full_pipeline.py → 이동 예정
- `integration/test_full_workflow.py` (통합 테스트로 이동)
- `e2e/test_end_to_end.py` (E2E 테스트로 승격)

## 📊 리팩토링 진행률

```
Phase 1 리팩토링 상태:
├── test_deployment_state.py     ✅ 분할 완료 (100%)
├── test_config_validation.py    🔄 진행 중 (60%)  
└── test_full_pipeline.py        ⏳ 대기 중 (0%)

총 진행률: 53% 완료
```

## 🚨 중요 사항

### 임시 보존 이유
1. **하위 호환성**: 기존 테스트가 여전히 작동해야 함
2. **점진적 마이그레이션**: 새 구조로 단계적 이동
3. **안전성**: 리팩토링 중 테스트 커버리지 유지

### 사용 지침
- **새 테스트**: legacy 디렉토리에 추가 금지
- **기존 테스트**: 가능한 한 빨리 리팩토링된 구조로 이동
- **실행**: CI에서는 legacy 테스트도 계속 실행

## 🏃‍♂️ 실행 방법

```bash
# Legacy 테스트만 실행
pytest tests/legacy/ -v

# 특정 파일 실행  
pytest tests/legacy/test_config_validation.py -v

# 전체 테스트 (legacy 포함)
pytest tests/ -v
```

## 📋 마이그레이션 체크리스트

### test_config_validation.py
- [ ] 기본 모델 검증 테스트 분리
- [ ] 오류 처리 테스트 분리
- [ ] 통합 테스트 분리
- [ ] 원본 파일 제거

### test_deployment_state.py  
- [x] Database 테스트 분리 ✅
- [x] Tracker 테스트 분리 ✅
- [x] Rollback 테스트 분리 ✅
- [ ] 원본 파일 제거 (검증 후)

### test_full_pipeline.py
- [ ] 통합 테스트 부분 분리
- [ ] E2E 테스트 부분 분리
- [ ] 중복 제거 및 최적화
- [ ] 원본 파일 제거

## 🔧 리팩토링 가이드

### 분할 원칙
1. **단일 책임**: 각 테스트 파일은 하나의 컴포넌트만 테스트
2. **적절한 크기**: 100-200 라인 내외 권장
3. **명확한 이름**: 파일명에서 테스트 대상 명확히 표현

### 코드 마이그레이션
```python
# Legacy 스타일 (지양)
class TestEverything:
    def test_config_and_deployment_and_more(self):
        # 여러 기능을 한 번에 테스트
        pass

# 새 스타일 (권장)
class TestConfigValidation:
    def test_valid_config_parsing(self):
        # 단일 기능에 집중
        pass
    
    def test_invalid_config_error_handling(self):
        # 예외 케이스 별도 테스트
        pass
```

## 📅 마이그레이션 일정

### Phase 3 (현재 진행 중)
- [ ] test_config_validation.py 분할 완료
- [ ] test_full_pipeline.py 분할 계획 수립

### Phase 4 (검증 및 정리)
- [ ] Legacy 파일 제거
- [ ] 중복 테스트 정리
- [ ] 최종 검증

## 🎯 최종 목표

**Legacy 디렉토리 완전 제거**: 모든 테스트가 적절한 디렉토리(`unit/`, `integration/`, `e2e/`)로 이동하여 깔끔한 테스트 구조 완성