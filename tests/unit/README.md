# Unit Tests

이 디렉토리는 SBKube 프로젝트의 단위 테스트를 포함합니다.

## 📁 디렉토리 구조

```
unit/
├── commands/          # CLI 명령어 테스트
├── models/           # 데이터 모델 검증 테스트  
├── state/            # 상태 관리 (DB, 추적, 롤백) 테스트
└── utils/            # 유틸리티 함수 테스트
```

## 🧪 테스트 분류

### Commands Tests (`commands/`)
- **build**: 앱 빌드 로직 테스트
- **delete**: 리소스 삭제 테스트
- **deploy**: 배포 프로세스 테스트
- **prepare**: 소스 준비 작업 테스트
- **template**: 템플릿 생성 테스트
- **upgrade**: 업그레이드 프로세스 테스트

### Models Tests (`models/`)
- **config_model**: 설정 데이터 모델 검증
- **validation_errors**: 유효성 검사 오류 처리

### State Tests (`state/`)
- **deployment_database**: 배포 상태 DB 연산
- **deployment_tracker**: 배포 추적 로직
- **rollback_manager**: 롤백 메커니즘

### Utils Tests (`utils/`)
- **common_patterns**: 공통 패턴 및 헬퍼
- **exceptions**: 예외 처리 로직
- **network_errors**: 네트워크 오류 시나리오 (18개 케이스)
- **resource_limits**: 리소스 제약 및 엣지 케이스 (9개 케이스)
- **retry**: 재시도 메커니즘

## 🏃‍♂️ 실행 방법

```bash
# 전체 단위 테스트 실행
pytest tests/unit/ -v

# 특정 모듈 실행
pytest tests/unit/commands/ -v
pytest tests/unit/state/test_deployment_database.py -v

# 마커 기반 실행
pytest -m unit -v
```

## ✅ 테스트 상태

- **총 테스트 파일**: 14개
- **pytest 마커**: `@pytest.mark.unit` 적용
- **예외 처리**: 27개 시나리오 커버
- **SQLAlchemy 세션**: Database 테스트 정상 동작

## 📊 품질 지표

- **예외 처리 커버리지**: 25%+
- **네트워크 오류 시나리오**: 9개
- **리소스 제약 테스트**: 9개  
- **동시성 테스트**: 2개
- **엣지 케이스**: 7개

## 🔧 개발 가이드

### 새 테스트 추가 시
1. 적절한 하위 디렉토리 선택
2. `pytestmark = pytest.mark.unit` 추가
3. 의미 있는 테스트 이름 사용
4. 예외 케이스 포함 권장

### 권장 패턴
```python
import pytest

pytestmark = pytest.mark.unit

class TestFeatureName:
    """Feature description."""
    
    def test_normal_case(self):
        """Test normal operation."""
        pass
        
    def test_exception_case(self):
        """Test error handling."""
        with pytest.raises(ExpectedError):
            # test code
            pass
```