# sbkube 테스트 전략

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
├── test_k3scode_ai.py          # examples/k3scode/ai 전체 워크플로우
├── test_k3scode_devops.py      # examples/k3scode/devops 전체 워크플로우
└── test_prepare_examples.py    # examples/prepare/* 시나리오
```

**커버리지**: 사용자가 실제로 사용하는 전체 시나리오

#### 🥈 높은 우선순위: Integration 테스트 (examples/ + 실제 도구)
```python
@pytest.mark.integration
@pytest.mark.requires_helm
def test_prepare_helm_with_example(helm_binary):
    """examples/prepare/pull-helm-oci 사용"""
    example = Path("examples/prepare/pull-helm-oci")
    # 실제 helm 명령어와 실제 예제 파일 사용
```

**커버리지**: 실제 helm/kubectl/git 도구와의 통합

#### 🥉 중간 우선순위: Unit 테스트
```python
def test_config_validation():
    """개별 함수/클래스 로직 검증"""
    config = Config.from_file("examples/k3scode/ai/config.yaml")
    assert config.validate() is True
```

**커버리지**: 개별 함수/클래스의 로직

#### 📊 낮은 우선순위: Performance 테스트
```python
def test_large_config_performance(benchmark):
    """성능 벤치마크"""
    benchmark(load_config, "examples/complete-workflow/config.yaml")
```

**커버리지**: 성능 기준선

---

## 테스트 작성 가이드

### E2E 테스트 작성

```python
@pytest.mark.e2e
@pytest.mark.requires_k8s
def test_full_k3scode_ai_deployment(k8s_cluster):
    """
    examples/k3scode/ai 전체 워크플로우 테스트

    Scenario:
    1. prepare: Helm 차트 다운로드
    2. build: 차트 빌드
    3. deploy: K8s 클러스터에 배포
    4. 검증: 리소스 확인
    """
    runner = CliRunner()

    # 1. Prepare
    result = runner.invoke(main, [
        "prepare",
        "--app-dir", "examples/k3scode/ai",
        "--sources-file", "examples/k3scode/sources.yaml"
    ])
    assert result.exit_code == 0

    # 2. Build
    result = runner.invoke(main, [
        "build",
        "--app-dir", "examples/k3scode/ai"
    ])
    assert result.exit_code == 0

    # 3. Deploy
    result = runner.invoke(main, [
        "deploy",
        "--app-dir", "examples/k3scode/ai",
        "--namespace", "test-ai"
    ])
    assert result.exit_code == 0

    # 4. 검증
    pods = k8s_cluster.list_pods("test-ai")
    assert len(pods) > 0
```

### Integration 테스트 작성

```python
@pytest.mark.integration
@pytest.mark.requires_helm
def test_prepare_pull_helm_oci(tmp_path):
    """
    examples/prepare/pull-helm-oci 시나리오
    실제 helm 명령어 사용
    """
    example_dir = Path("examples/prepare/pull-helm-oci")

    runner = CliRunner()
    result = runner.invoke(main, [
        "prepare",
        "--app-dir", str(example_dir),
        "--base-dir", str(tmp_path)
    ])

    assert result.exit_code == 0
    assert (tmp_path / "charts").exists()
```

### Unit 테스트 작성

```python
@pytest.mark.unit
def test_config_loading_from_example():
    """examples/k3scode/ai/config.yaml 로딩 테스트"""
    config_path = Path("examples/k3scode/ai/config.yaml")
    config = Config.from_file(config_path)

    assert config.apps is not None
    assert len(config.apps) > 0
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

### GitHub Actions 예시

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: pytest tests/unit/ -v

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install helm
        run: curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
      - name: Run integration tests
        run: pytest tests/integration/ -v -m requires_helm

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup k3s
        run: |
          curl -sfL https://get.k3s.io | sh -
          mkdir -p ~/.kube
          sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
      - name: Run E2E tests
        run: pytest tests/e2e/ -v -m requires_k8s
```

---

## 테스트 마커 활용

```python
# E2E 테스트
@pytest.mark.e2e
@pytest.mark.requires_k8s
def test_full_workflow(): ...

# Integration 테스트
@pytest.mark.integration
@pytest.mark.requires_helm
def test_helm_integration(): ...

# Unit 테스트
@pytest.mark.unit
def test_config_model(): ...

# Performance 테스트
@pytest.mark.performance
@pytest.mark.benchmark
def test_performance(): ...

# 느린 테스트
@pytest.mark.slow
def test_large_deployment(): ...
```

### 선택적 실행

```bash
# E2E만
pytest -m e2e

# Integration만
pytest -m integration

# 빠른 테스트만
pytest -m "not slow"

# Helm 필요한 테스트
pytest -m requires_helm

# Kubernetes 필요한 테스트
pytest -m requires_k8s
```

---

## 테스트 커버리지 목표

- **E2E 커버리지**: examples/ 의 모든 디렉토리는 E2E 테스트 필수
- **Integration 커버리지**: 모든 CLI 명령어는 integration 테스트 필수
- **Unit 커버리지**: 핵심 로직 함수는 unit 테스트 필수
- **전체 커버리지**: ≥ 90%

### 커버리지 확인

```bash
# 전체 커버리지
pytest --cov=sbkube --cov-report=html
open htmlcov/index.html

# examples/ 기반 테스트만으로 커버리지 확인
pytest tests/e2e/ tests/integration/ --cov=sbkube --cov-report=term
```

---

## 체크리스트

### 새 기능 추가 시
- [ ] examples/ 에 사용 예시 추가
- [ ] examples/*/README.md 업데이트
- [ ] E2E 테스트 작성 (examples/ 기반)
- [ ] Integration 테스트 작성 (필요시)
- [ ] Unit 테스트 작성 (핵심 로직)
- [ ] 모든 테스트 통과 확인
- [ ] 커버리지 90% 이상 확인

### 기존 기능 수정 시
- [ ] 관련 examples/ 파일 업데이트 확인
- [ ] E2E 테스트 실행 및 업데이트
- [ ] Integration 테스트 실행 및 업데이트
- [ ] Unit 테스트 실행 및 업데이트
- [ ] 회귀 테스트 확인

### PR 제출 전
- [ ] `pytest -v` 전체 테스트 통과
- [ ] `pytest --cov=sbkube --cov-report=term` 커버리지 확인
- [ ] examples/ 기반 테스트 우선 작성 여부 확인
- [ ] Mock 사용이 최소화되었는지 확인
