# SBKube 사용성 개선 테스트 전략

## 🎯 테스트 목표

1. **기능 정확성**: 모든 새 기능이 설계된 대로 정확히 동작
2. **하위 호환성**: 기존 기능이 완전히 보존되고 정상 작동
3. **성능 유지**: 새 기능 추가로 인한 성능 저하 최소화
4. **사용자 경험**: 실제 사용 시나리오에서의 편의성 검증
5. **안정성**: 다양한 환경과 조건에서 안정적 동작

## 📊 테스트 피라미드

```
        /\
       /  \
      /    \
     /  E2E  \    (5%) - 사용자 시나리오, 전체 워크플로우
    /        \
   /          \
  / Integration \  (25%) - 명령어 간 상호작용, 외부 도구 연동
 /              \
/   Unit Tests   \  (70%) - 개별 함수, 클래스, 모듈
\                /
 \______________/
```

## 🧪 테스트 레벨별 전략

### 1. 단위 테스트 (Unit Tests) - 70%

#### 목표
- 개별 함수와 클래스의 정확한 동작 검증
- 빠른 피드백 루프 제공
- 코드 변경 시 회귀 버그 조기 발견

#### 커버리지 목표
- **전체 코드 커버리지**: 85% 이상
- **새로운 코드 커버리지**: 95% 이상
- **핵심 로직 커버리지**: 100%

#### 테스트 대상

**Phase 1 단위 테스트**:
```python
# tests/unit/commands/test_run.py
class TestRunCommand:
    def test_determine_steps_full_workflow(self):
        """전체 워크플로우 단계 결정"""
        
    def test_determine_steps_with_from_step(self):
        """특정 단계부터 시작"""
        
    def test_determine_steps_with_to_step(self):
        """특정 단계까지만 실행"""
        
    def test_execute_step_success(self):
        """단계 실행 성공 시나리오"""
        
    def test_execute_step_failure(self):
        """단계 실행 실패 시나리오"""

# tests/unit/commands/test_init.py
class TestInitCommand:
    def test_template_rendering(self):
        """템플릿 렌더링 정확성"""
        
    def test_interactive_input_validation(self):
        """대화형 입력 검증"""
        
    def test_file_generation(self):
        """설정 파일 생성"""

# tests/unit/utils/test_config_loader.py
class TestConfigLoader:
    def test_load_sbkuberc(self):
        """.sbkuberc 파일 로딩"""
        
    def test_profile_override(self):
        """프로파일 설정 오버라이드"""
        
    def test_environment_variable_override(self):
        """환경변수 오버라이드"""
```

**Phase 2 단위 테스트**:
```python
# tests/unit/utils/test_profile_manager.py
class TestProfileManager:
    def test_load_profile(self):
        """프로파일 로딩"""
        
    def test_merge_configs(self):
        """설정 병합"""
        
    def test_validate_profile(self):
        """프로파일 검증"""

# tests/unit/utils/test_execution_tracker.py
class TestExecutionTracker:
    def test_save_state(self):
        """실행 상태 저장"""
        
    def test_load_state(self):
        """실행 상태 로드"""
        
    def test_determine_restart_point(self):
        """재시작 지점 결정"""

# tests/unit/utils/test_progress_manager.py
class TestProgressManager:
    def test_update_progress(self):
        """진행률 업데이트"""
        
    def test_estimate_completion_time(self):
        """완료 시간 예측"""
```

**Phase 3 단위 테스트**:
```python
# tests/unit/commands/test_doctor.py
class TestDoctorCommand:
    def test_check_kubernetes_connectivity(self):
        """Kubernetes 연결 확인"""
        
    def test_check_config_validity(self):
        """설정 유효성 검사"""
        
    def test_generate_recommendations(self):
        """개선 권장사항 생성"""

# tests/unit/utils/test_workflow_engine.py
class TestWorkflowEngine:
    def test_parse_workflow(self):
        """워크플로우 파싱"""
        
    def test_execute_conditional_step(self):
        """조건부 단계 실행"""
        
    def test_parallel_execution(self):
        """병렬 실행"""
```

#### 테스트 작성 가이드라인

1. **AAA 패턴**: Arrange, Act, Assert
2. **독립성**: 각 테스트는 독립적으로 실행 가능
3. **결정성**: 동일한 입력에 항상 동일한 결과
4. **빠른 실행**: 단위 테스트는 1초 이내 완료
5. **명확한 이름**: 테스트 목적이 명확히 드러나는 이름

### 2. 통합 테스트 (Integration Tests) - 25%

#### 목표
- 여러 컴포넌트 간의 상호작용 검증
- 외부 시스템과의 연동 테스트
- 실제 환경에 가까운 조건에서 테스트

#### 테스트 환경 구성

**로컬 테스트 환경**:
```yaml
# tests/integration/docker-compose.yml
version: '3.8'
services:
  k3s:
    image: rancher/k3s:latest
    command: server --disable traefik
    environment:
      - K3S_KUBECONFIG_OUTPUT=/output/kubeconfig.yaml
    volumes:
      - k3s-data:/var/lib/rancher/k3s
      - ./kubeconfig:/output
    ports:
      - "6443:6443"
      
  helm:
    image: alpine/helm:latest
    depends_on:
      - k3s
    volumes:
      - ./kubeconfig:/root/.kube
```

#### 통합 테스트 시나리오

**Phase 1 통합 테스트**:
```python
# tests/integration/test_run_workflow.py
class TestRunWorkflow:
    def test_full_workflow_execution(self):
        """전체 워크플로우 실행"""
        # Given: 완전한 프로젝트 설정
        # When: sbkube run 실행
        # Then: 모든 단계가 순차적으로 성공
        
    def test_partial_workflow_execution(self):
        """부분 워크플로우 실행"""
        # Given: 일부 단계가 이미 완료된 상태
        # When: --from-step으로 중간부터 실행
        # Then: 지정된 단계부터 정상 실행
        
    def test_workflow_failure_handling(self):
        """워크플로우 실패 처리"""
        # Given: 실패하도록 설정된 환경
        # When: sbkube run 실행
        # Then: 적절한 오류 메시지와 상태 저장

# tests/integration/test_init_workflow.py
class TestInitWorkflow:
    def test_project_initialization(self):
        """프로젝트 초기화"""
        # Given: 빈 디렉토리
        # When: sbkube init 실행
        # Then: 완전한 프로젝트 구조 생성
        
    def test_generated_project_validation(self):
        """생성된 프로젝트 검증"""
        # Given: init으로 생성된 프로젝트
        # When: sbkube validate 실행
        # Then: 모든 검증 통과
```

**Phase 2 통합 테스트**:
```python
# tests/integration/test_profile_workflow.py
class TestProfileWorkflow:
    def test_profile_based_deployment(self):
        """프로파일 기반 배포"""
        # Given: 다양한 환경 설정
        # When: --profile로 특정 환경 배포
        # Then: 해당 환경 설정이 정확히 적용
        
    def test_profile_switching(self):
        """프로파일 전환"""
        # Given: production으로 배포된 상태
        # When: staging 프로파일로 재배포
        # Then: 설정이 staging으로 변경

# tests/integration/test_restart_workflow.py
class TestRestartWorkflow:
    def test_restart_from_failure_point(self):
        """실패 지점부터 재시작"""
        # Given: build 단계에서 실패한 상태
        # When: --continue-from build 실행
        # Then: build부터 정상 재시작
        
    def test_state_persistence(self):
        """상태 지속성"""
        # Given: 실행 중 중단된 상태
        # When: 프로세스 재시작
        # Then: 이전 상태 정확히 복원
```

#### 테스트 데이터 관리

**픽스처 및 테스트 데이터**:
```python
# tests/integration/conftest.py
@pytest.fixture
def sample_project():
    """샘플 프로젝트 생성"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 기본 설정 파일들 생성
        create_sample_config(tmpdir)
        create_sample_sources(tmpdir)
        yield tmpdir

@pytest.fixture
def k8s_cluster():
    """테스트용 K8s 클러스터"""
    # Docker로 k3s 클러스터 시작
    cluster = start_test_cluster()
    yield cluster
    # 클러스터 정리
    cleanup_test_cluster(cluster)
```

### 3. E2E 테스트 (End-to-End Tests) - 5%

#### 목표
- 실제 사용자 시나리오 완전 재현
- 전체 시스템의 종합적 동작 검증
- 사용자 경험 품질 확인

#### E2E 테스트 시나리오

**핵심 사용자 여정**:
```python
# tests/e2e/test_user_journeys.py
class TestUserJourneys:
    def test_new_user_complete_journey(self):
        """신규 사용자 완전 여정"""
        # 1. 새 프로젝트 시작
        # 2. sbkube init으로 초기화
        # 3. .sbkuberc 설정
        # 4. sbkube run으로 배포
        # 5. 결과 확인
        
    def test_experienced_user_workflow(self):
        """숙련 사용자 워크플로우"""
        # 1. 기존 프로젝트에 새 앱 추가
        # 2. 프로파일별 설정
        # 3. 단계별 실행 및 확인
        # 4. 문제 발생 시 재시작
        
    def test_team_collaboration_scenario(self):
        """팀 협업 시나리오"""
        # 1. 공통 설정 공유
        # 2. 개발자별 로컬 설정
        # 3. 환경별 배포
        # 4. 설정 변경 및 동기화
```

**성능 및 안정성 테스트**:
```python
# tests/e2e/test_performance.py
class TestPerformance:
    def test_large_project_performance(self):
        """대규모 프로젝트 성능"""
        # Given: 100개 앱이 있는 프로젝트
        # When: sbkube run 실행
        # Then: 10분 이내 완료
        
    def test_memory_usage(self):
        """메모리 사용량"""
        # Given: 정상적인 프로젝트
        # When: 모든 기능 실행
        # Then: 메모리 사용량 500MB 이내
        
    def test_concurrent_executions(self):
        """동시 실행"""
        # Given: 동일 프로젝트
        # When: 여러 명령어 동시 실행
        # Then: 충돌 없이 정상 처리
```

## 🔄 테스트 자동화

### CI/CD 파이프라인

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=sbkube --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v3
      - name: Setup test environment
        run: |
          curl -sfL https://get.k3s.io | sh -
          curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
      - name: Run integration tests
        run: pytest tests/integration/ -v --timeout=300

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Setup full environment
        run: ./scripts/setup-e2e-env.sh
      - name: Run E2E tests
        run: pytest tests/e2e/ -v --timeout=900
```

### 테스트 환경 관리

**테스트 환경 자동화**:
```bash
#!/bin/bash
# scripts/setup-test-env.sh

# K3s 클러스터 시작
docker run -d --name k3s-test \
  --privileged \
  -p 6443:6443 \
  rancher/k3s:latest server --disable traefik

# Helm 설치
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 테스트 데이터 준비
kubectl create namespace test-ns
helm repo add bitnami https://charts.bitnami.com/bitnami
```

## 📈 테스트 메트릭 및 품질 게이트

### 코드 커버리지 기준

| 구분 | 목표 커버리지 | 최소 커버리지 |
|------|-------------|-------------|
| 전체 | 85% | 80% |
| 새 코드 | 95% | 90% |
| 핵심 로직 | 100% | 95% |
| UI 컴포넌트 | 70% | 60% |

### 성능 기준

| 메트릭 | 목표 | 임계값 |
|--------|------|--------|
| 단위 테스트 실행 시간 | < 30초 | < 60초 |
| 통합 테스트 실행 시간 | < 5분 | < 10분 |
| E2E 테스트 실행 시간 | < 15분 | < 30분 |
| 메모리 사용량 증가 | < 20% | < 30% |

### 품질 게이트

**PR 머지 조건**:
- [ ] 모든 단위 테스트 통과
- [ ] 코드 커버리지 80% 이상
- [ ] 관련 통합 테스트 통과
- [ ] 성능 저하 없음 (기준 대비 10% 이내)
- [ ] 메모리 누수 없음

**릴리스 조건**:
- [ ] 모든 테스트 통과 (단위/통합/E2E)
- [ ] 성능 벤치마크 통과
- [ ] 보안 스캔 통과
- [ ] 사용자 시나리오 테스트 완료

## 🛠️ 테스트 도구 및 프레임워크

### 기본 테스트 스택
```python
# requirements-test.txt
pytest>=7.0.0              # 테스트 프레임워크
pytest-cov>=4.0.0          # 커버리지 측정
pytest-xdist>=3.0.0        # 병렬 테스트 실행
pytest-timeout>=2.1.0      # 테스트 타임아웃
pytest-mock>=3.10.0        # 모킹 지원
pytest-benchmark>=4.0.0    # 성능 벤치마크
pytest-asyncio>=0.21.0     # 비동기 테스트 지원

# 추가 도구
testcontainers>=3.7.0      # 컨테이너 기반 테스트
faker>=18.0.0              # 테스트 데이터 생성
responses>=0.23.0          # HTTP 모킹
freezegun>=1.2.0           # 시간 모킹
```

### 테스트 유틸리티

**공통 테스트 헬퍼**:
```python
# tests/utils/helpers.py
class TestHelpers:
    @staticmethod
    def create_temp_project(apps=None):
        """임시 테스트 프로젝트 생성"""
        
    @staticmethod
    def mock_kubernetes_cluster():
        """Kubernetes 클러스터 모킹"""
        
    @staticmethod
    def assert_file_exists(path, content=None):
        """파일 존재 및 내용 검증"""
        
    @staticmethod
    def capture_output(command):
        """명령어 출력 캡처"""
```

## 📊 테스트 리포팅

### 테스트 결과 시각화

**커버리지 리포트**:
```bash
# HTML 커버리지 리포트 생성
pytest --cov=sbkube --cov-report=html tests/

# 터미널에서 누락된 라인 표시
pytest --cov=sbkube --cov-report=term-missing tests/
```

**성능 벤치마크 리포트**:
```python
# tests/performance/benchmark.py
def test_run_command_performance(benchmark):
    """run 명령어 성능 벤치마크"""
    result = benchmark(run_command_with_sample_project)
    assert result.elapsed_time < 10.0  # 10초 이내
```

### 지속적 모니터링

**일일 테스트 실행**:
```yaml
# .github/workflows/nightly-tests.yml
name: Nightly Tests
on:
  schedule:
    - cron: '0 2 * * *'  # 매일 오전 2시
jobs:
  comprehensive-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run full test suite
        run: |
          pytest tests/ -v --timeout=3600
          ./scripts/performance-test.sh
          ./scripts/security-scan.sh
```

## 🚀 테스트 실행 가이드

### 로컬 개발 환경

```bash
# 전체 테스트 실행
make test

# 단위 테스트만 실행
make test-unit

# 통합 테스트만 실행
make test-integration

# 특정 파일 테스트
pytest tests/unit/commands/test_run.py -v

# 커버리지와 함께 실행
make test-coverage

# 성능 테스트 실행
make test-performance
```

### CI 환경

```bash
# 빠른 피드백용 (PR 체크)
make test-quick

# 완전한 테스트 (릴리스 전)
make test-full

# 보안 및 품질 검사
make test-security
make test-quality
```

---

*이 테스트 전략은 프로젝트 진행에 따라 지속적으로 개선되며, 새로운 기능 추가 시 해당 테스트도 함께 확장됩니다.*