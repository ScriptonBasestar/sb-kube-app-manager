# sbkube 테스트 전략

## 📊 테스트 현황 (Phase 1-2 완료)

- **총 테스트 수**: 132개 (전체 통과 ✅)
- **테스트 구조**: E2E (13개) + 단위 테스트 (116개) + imports (3개)

### 테스트 파일 구조
```
tests/
├── e2e/                                  # 13 tests (examples/ 기반)
│   ├── conftest.py                       # Helper 함수
│   ├── test_k3scode_workflows.py         # 6 tests
│   ├── test_prepare_examples.py          # 1 test
│   ├── test_deploy_examples.py           # 3 tests
│   └── test_complete_workflow.py         # 3 tests
├── unit/
│   ├── models/                           # 16 tests (설정 파싱/검증)
│   │   ├── test_config_model.py          # 11 tests
│   │   └── test_validation_errors.py     # 5 tests
│   └── utils/                            # 100 tests (핵심 유틸리티만)
│       ├── test_exceptions.py
│       ├── test_profile_loader.py
│       ├── test_profile_manager.py
│       ├── test_progress_manager.py
│       ├── test_resource_limits.py
│       └── test_retry.py
└── test_imports.py                       # 3 tests (의존성 검증)
```

### Phase 2에서 제거된 과잉 테스트
- ❌ **tests/integration/** (2,741 lines): E2E 테스트로 대체
- ❌ **tests/unit/commands/** (4,653 lines): Mock 기반, E2E로 커버
- ❌ **tests/unit/fixes/**: 기능별 테스트 불필요
- ❌ **tests/unit/state/**: E2E로 커버
- ❌ **tests/unit/utils/** 일부: 복잡한 feature 관련 테스트 제거
  - test_auto_fix_system.py
  - test_interactive_assistant.py
  - test_execution_tracker.py
  - test_workflow_engine.py
  - test_common_patterns.py (낡은 테스트)
  - test_network_errors.py (낡은 테스트)
- ❌ **tests/performance/**: CLI 도구에 불필요

## 핵심 원칙

### 1. CLI 도구는 examples/ 기반 테스트가 우선이다

sbkube는 CLI 도구이므로, **실제 사용자가 사용할 예제 파일**로 테스트하는 것이 가장 중요합니다.

**좋은 예시 (examples/ 기반)**:
```python
def test_prepare_with_real_example(tmp_path):
    """examples/k3scode/ai 디렉토리를 사용한 실제 시나리오 테스트"""
    example_dir = Path("examples/k3scode/ai")
    runner = CliRunner()
    result = runner.invoke(main, ["prepare", "--app-dir", str(example_dir)])
    assert result.exit_code == 0
```

**나쁜 예시 (과도한 mock)**:
```python
@patch('sbkube.commands.prepare.helm_pull')
@patch('sbkube.commands.prepare.git_clone')
def test_prepare_with_mocks(mock_git, mock_helm):
    """실제 동작과 무관한 mock 기반 테스트"""
    mock_helm.return_value = True
    mock_git.return_value = True
    # ... 실제 sbkube 동작과 다를 수 있음
```

### 2. Mock 사용은 최소화한다

Mock은 다음 경우에만 사용:
- 외부 API 호출 (Kubernetes API, Helm repository, Git remote)
- 시스템 리소스 제약 (대용량 파일, 네트워크 의존성)
- CI/CD 환경 제약 (Docker, K8s cluster 없음)

**Mock 사용 금지 사례**:
- 파일 시스템 읽기/쓰기 (실제 파일 사용)
- 설정 파일 파싱 (examples/ 의 실제 config.yaml 사용)
- CLI 인자 처리 (실제 Click runner 사용)

### 3. 테스트 우선순위

#### 🥇 최우선: E2E 테스트 (examples/ 기반)
```
tests/e2e/
├── test_k3scode_workflows.py      # examples/k3scode/* 전체 워크플로우
├── test_prepare_examples.py       # examples/prepare/* 시나리오
├── test_deploy_examples.py        # examples/deploy/* 시나리오
└── test_complete_workflow.py      # examples/complete-workflow
```

**커버리지**: 사용자가 실제로 사용하는 전체 시나리오
**현재 상태**: ✅ 13개 테스트 모두 통과

#### 🥈 높은 우선순위: Unit 테스트 (models + 핵심 utils)
```python
# Models: 설정 파싱/검증 (16 tests)
def test_config_loading_from_example():
    """examples/k3scode/ai/config.yaml 로딩 테스트"""
    config_path = Path("examples/k3scode/ai/config.yaml")
    config = Config.from_file(config_path)
    assert config.apps is not None

# Utils: 핵심 유틸리티만 (101 tests)
def test_retry_decorator():
    """재시도 로직 테스트"""
    @retry(max_attempts=3)
    def flaky_function():
        # ...
```

**커버리지**: 설정 파싱, 검증, 핵심 유틸리티 (retry, exceptions, progress 등)
**현재 상태**: ✅ 117개 테스트 모두 통과

#### ❌ 제거된 테스트 유형
- **Integration 테스트**: E2E 테스트로 완전히 대체
- **Commands 단위 테스트**: Mock 기반이며 E2E로 커버됨
- **Performance 테스트**: CLI 도구에는 불필요

---

## 테스트 작성 가이드

### E2E 테스트 작성

**실제 구현 예시** (tests/e2e/test_k3scode_workflows.py):

```python
@pytest.mark.e2e
class TestK3scodeAIWorkflow:
    """Test k3scode AI application workflow."""

    def test_ai_prepare(self, runner, examples_dir, tmp_path, list_directory_contents):
        """
        Test k3scode AI prepare phase.

        This test verifies that the prepare command correctly downloads
        Helm charts and Git repositories specified in examples/k3scode/ai/config.yaml.
        """
        # Verify example files exist
        ai_dir = examples_dir / "k3scode" / "ai"
        sources_file = examples_dir / "k3scode" / "sources.yaml"

        verify_example_exists(ai_dir)
        assert sources_file.exists(), f"sources.yaml not found: {sources_file}"

        # Get project root (examples/ parent directory)
        project_root = examples_dir.parent

        # Run prepare command
        # Note: --app-dir is relative to --base-dir
        result = run_sbkube_command(
            runner,
            [
                "prepare",
                "--app-dir",
                str(ai_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--sources-file",
                str(sources_file.relative_to(project_root)),
            ],
            debug_info={
                "ai_dir": ai_dir,
                "sources_file": sources_file,
                "project_root": project_root,
            },
        )

        # Verify output
        assert "prepare" in result.output.lower() or "준비" in result.output

        # Verify charts/repos were downloaded
        charts_dir = project_root / "charts"
        repos_dir = project_root / "repos"

        # At least one of charts or repos should exist
        assert (
            charts_dir.exists() or repos_dir.exists()
        ), f"Neither charts nor repos directory created in {project_root}"
```

**핵심 포인트**:
- ✅ 실제 examples/ 파일 사용 (Mock 없음)
- ✅ `verify_example_exists()` helper로 예제 파일 검증
- ✅ `run_sbkube_command()` helper로 상세 에러 리포팅
- ✅ debug_info로 실패 시 컨텍스트 제공

### 단위 테스트 작성 (models, utils)

**Models 테스트** - 설정 파일 파싱/검증:
```python
def test_config_loading_from_example():
    """examples/k3scode/ai/config.yaml 로딩 테스트"""
    config_path = Path("examples/k3scode/ai/config.yaml")
    config = Config.from_file(config_path)

    assert config.apps is not None
    assert len(config.apps) > 0
```

**Utils 테스트** - 핵심 유틸리티만:
```python
def test_retry_with_exponential_backoff():
    """재시도 로직 테스트"""
    call_count = 0

    @retry(max_attempts=3, backoff_factor=2)
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Simulated error")
        return "success"

    result = flaky_function()
    assert result == "success"
    assert call_count == 3
```


---

## examples/ 디렉토리 관리

### 1. 예제는 실제 사용 가능해야 함

examples/ 의 모든 파일은:
- 문서에 설명된 대로 동작해야 함
- sbkube CLI로 실행 가능해야 함
- 테스트에서 참조되어야 함

### 2. 예제 변경 시 테스트도 업데이트

```bash
# 예제 파일 변경
vim examples/k3scode/ai/config.yaml

# 관련 테스트 실행
pytest tests/e2e/test_k3scode_ai.py -v

# 테스트 실패 시 수정
vim tests/e2e/test_k3scode_ai.py
```

### 3. 새 기능 추가 시 예제 먼저 작성

```bash
# 1. 예제 디렉토리 생성
mkdir -p examples/new-feature

# 2. 예제 파일 작성
vim examples/new-feature/config.yaml
vim examples/new-feature/README.md

# 3. E2E 테스트 작성
vim tests/e2e/test_new_feature.py

# 4. 기능 구현
vim sbkube/commands/new_feature.py

# 5. 테스트 실행
pytest tests/e2e/test_new_feature.py -v
```

---

## CI/CD에서 테스트 실행

### GitHub Actions 예시 (간소화)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Run all tests
        run: uv run pytest tests/ -v

  e2e-with-tools:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install helm
        run: curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
      - name: Run E2E tests
        run: uv run pytest tests/e2e/ -v -m requires_helm
```

---

## 테스트 마커 활용

```python
# E2E 테스트
@pytest.mark.e2e
def test_k3scode_ai_workflow(): ...

# E2E + 외부 도구 필요
@pytest.mark.e2e
@pytest.mark.requires_helm
def test_prepare_pull_helm_oci(): ...

# 느린 E2E 테스트
@pytest.mark.e2e
@pytest.mark.slow
def test_complete_workflow(): ...
```

### 선택적 실행

```bash
# 전체 테스트
uv run pytest tests/ -v

# E2E만
uv run pytest tests/e2e/ -v

# 단위 테스트만
uv run pytest tests/unit/ -v

# 빠른 테스트만 (slow 제외)
uv run pytest -m "not slow" -v

# Helm 필요한 테스트만
uv run pytest -m requires_helm -v
```

---

## 테스트 커버리지 목표

- **E2E 커버리지**: examples/ 의 모든 디렉토리는 E2E 테스트 필수
- **Unit 커버리지**: models (설정 파싱/검증) + utils (핵심 유틸리티)만
- **전체 커버리지**: 실제 사용 시나리오 중심, 불필요한 Mock 테스트 제거

### 커버리지 확인

```bash
# 전체 커버리지
uv run pytest --cov=sbkube --cov-report=html
open htmlcov/index.html

# E2E 테스트만으로 커버리지 확인
uv run pytest tests/e2e/ --cov=sbkube --cov-report=term
```

---

## 체크리스트

### 새 기능 추가 시
- [ ] examples/ 에 사용 예시 추가
- [ ] examples/*/README.md 업데이트
- [ ] E2E 테스트 작성 (examples/ 기반, tests/e2e/)
- [ ] Unit 테스트 작성 (models/utils 핵심 로직만)
- [ ] 모든 테스트 통과 확인
- [ ] Mock 사용 최소화 확인

### 기존 기능 수정 시
- [ ] 관련 examples/ 파일 업데이트 확인
- [ ] E2E 테스트 실행 및 업데이트
- [ ] Unit 테스트 실행 및 업데이트 (필요시)
- [ ] 회귀 테스트 확인

### PR 제출 전
- [ ] `uv run pytest tests/ -v` 전체 테스트 통과
- [ ] examples/ 기반 E2E 테스트 우선 작성 확인
- [ ] Mock 기반 테스트 추가하지 않았는지 확인
- [ ] 불필요한 테스트 파일 생성하지 않았는지 확인
