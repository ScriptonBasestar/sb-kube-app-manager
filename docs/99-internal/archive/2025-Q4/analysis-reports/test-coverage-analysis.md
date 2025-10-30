# SBKube 테스트 커버리지 분석 리포트

**생성일**: 2025-10-23
**테스트 실행**: pytest with coverage
**전체 커버리지**: 22%

---

## 📊 종합 요약

| 항목 | 값 |
|------|-----|
| 전체 코드 라인 | 8,180 |
| 테스트된 라인 | 2,094 (8,180 - 6,086) |
| 미테스트 라인 | 6,086 |
| 전체 커버리지 | **22%** |
| 테스트 결과 | 128 passed, 23 failed, 1 skipped |

---

## ⚠️ 심각한 문제: Validators 0% 커버리지

### 영향도 분석

| 모듈 | 라인 수 | 커버리지 | 미테스트 라인 | 우선순위 |
|------|---------|----------|---------------|----------|
| `validators/pre_deployment_validators.py` | 656 | **0%** | 656 | 🔴 긴급 |
| `validators/dependency_validators.py` | 567 | **0%** | 567 | 🔴 긴급 |
| `validators/configuration_validators.py` | 435 | **0%** | 435 | 🔴 긴급 |
| `validators/environment_validators.py` | 389 | **0%** | 389 | 🔴 긴급 |
| `validators/basic_validators.py` | 65 | **0%** | 65 | 🔴 긴급 |
| **Validators 합계** | **2,112** | **0%** | **2,112** | |

### 문제 평가

- **전체 코드의 25.8%가 Validators**
- **Validators가 전혀 테스트되지 않음**
- 이는 **시스템 안정성에 치명적 위험**

**즉각 조치 필요**: Validators는 배포 전 안전성 검증의 핵심 컴포넌트

---

## 📈 모듈별 커버리지 상세

### ✅ 우수한 커버리지 (80% 이상)

| 모듈 | 커버리지 | 평가 |
|------|----------|------|
| `utils/profile_loader.py` | 98% | ✅ 우수 |
| `utils/profile_manager.py` | 93% | ✅ 우수 |
| `utils/retry.py` | 92% | ✅ 우수 |

### ⚠️ 양호한 커버리지 (50-80%)

| 모듈 | 커버리지 | 평가 |
|------|----------|------|
| `utils/progress_manager.py` | 72% | ⚠️ 양호 |
| `utils/logger.py` | 61% | ⚠️ 양호 |
| `utils/file_loader.py` | 57% | ⚠️ 양호 |

### 🔴 심각한 부족 (50% 미만)

| 모듈 | 커버리지 | 미테스트 라인 | 영향도 |
|------|----------|---------------|--------|
| **validators/* (모든 파일)** | **0%** | **2,112** | 🔴 높음 |
| `commands/fix.py` | 0% | 162 | 🔴 높음 |
| `commands/doctor.py` | 0% | 135 | 🔴 높음 |
| `commands/assistant.py` | 0% | 109 | 🔴 중간 |
| `commands/init.py` | 0% | 114 | 🔴 중간 |
| `commands/validate.py` | 0% | 68 | 🔴 중간 |
| `commands/profiles.py` | 0% | 50 | 🔴 중간 |
| `fixes/namespace_fixes.py` | 0% | 182 | 🔴 높음 |
| `diagnostics/kubernetes_checks.py` | 1% | 174 | 🔴 높음 |
| `utils/diagnostic_system.py` | 28% | 73 | ⚠️ 중간 |
| `utils/helm_util.py` | 29% | 15 | ⚠️ 낮음 |
| `utils/interactive_assistant.py` | 18% | 148 | 🔴 중간 |
| `utils/base_command.py` | 10% | 177 | 🔴 높음 |
| `utils/common.py` | 11% | 65 | 🔴 중간 |
| `utils/cli_check.py` | 17% | 101 | 🔴 중간 |

---

## 🧪 테스트 실패 분석

### E2E 테스트 실패 (12건)

**원인**: 외부 의존성 (Helm 리포지토리, 네트워크)

```
FAILED tests/e2e/test_complete_workflow.py::...
FAILED tests/e2e/test_deploy_examples.py::...
FAILED tests/e2e/test_k3scode_workflows.py::...
FAILED tests/e2e/test_prepare_examples.py::...
```

**권장 조치**:
- E2E 테스트는 선택적 실행 (CI/CD에서만)
- 로컬 개발 시 단위 테스트에 집중

### 단위 테스트 실패 (11건)

**원인**: `config_model.py`의 앱 타입 관련 테스트

```
FAILED tests/unit/models/test_config_model.py::TestAppInfoScheme::...
FAILED tests/unit/models/test_config_model.py::TestGetSpecModel::...
FAILED tests/unit/models/test_config_model.py::TestSpecModels::...
```

**문제점**:
- 실험적 앱 타입 (copy, install-yaml, install-action) 테스트
- Spec 모델 미구현 또는 불일치

**권장 조치**:
- 실험적 앱 타입 제거 또는 구현 완료
- 테스트와 코드 동기화

---

## 🎯 우선순위별 개선 계획

### Phase 1: Validators 테스트 긴급 추가 (2-3일)

**목표**: Validators 커버리지 0% → 60% 이상

#### Step 1: 기본 검증기 테스트 (0.5일)
```python
# tests/unit/validators/test_basic_validators.py
def test_file_existence_validator():
    validator = FileExistenceValidator()
    context = create_test_context(config_file="config.yaml")
    result = await validator.run_validation(context)
    assert result.severity == ValidationSeverity.INFO
```

#### Step 2: 설정 검증기 테스트 (1일)
- ConfigStructureValidator
- ConfigContentValidator
- SourcesIntegrityValidator
- CrossReferenceValidator

#### Step 3: 환경 검증기 테스트 (1일)
- ClusterResourceValidator (Mock kubectl)
- NamespacePermissionValidator
- NetworkPolicyValidator
- SecurityContextValidator

#### Step 4: 의존성 검증기 테스트 (1일)
- HelmChartValidator (Mock Helm CLI)
- ValuesCompatibilityValidator
- DependencyResolutionValidator
- NetworkConnectivityValidator

#### Step 5: 배포 전 검증기 테스트 (0.5일)
- DeploymentSimulator (Mock kubectl dry-run)
- RiskAssessmentValidator
- RollbackPlanValidator
- ImpactAnalysisValidator

### Phase 2: Commands 테스트 강화 (1-2일)

**목표**: Commands 커버리지 15% → 50%

- [ ] `fix.py` (0% → 50%)
- [ ] `doctor.py` (0% → 50%)
- [ ] `validate.py` (0% → 60%)
- [ ] `assistant.py` (0% → 40%)

### Phase 3: Utils 테스트 보완 (1일)

**목표**: Utils 평균 커버리지 40% → 70%

- [ ] `base_command.py` (10% → 60%)
- [ ] `cli_check.py` (17% → 70%)
- [ ] `common.py` (11% → 60%)
- [ ] `diagnostic_system.py` (28% → 60%)

---

## 📋 테스트 작성 가이드

### Mock 전략

#### Kubernetes API Mock
```python
from unittest.mock import patch, MagicMock

@patch('subprocess.run')
def test_kubectl_command(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="namespace/test created",
        stderr=""
    )
    # 테스트 로직
```

#### Helm CLI Mock
```python
@patch('sbkube.utils.helm_util.run_command')
def test_helm_chart_validator(mock_helm):
    mock_helm.return_value = (0, "chart downloaded", "")
    validator = HelmChartValidator()
    result = await validator.run_validation(context)
    assert result.severity == ValidationSeverity.INFO
```

### Fixture 활용

```python
# conftest.py
@pytest.fixture
def validation_context(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("""
    namespace: test
    apps:
      - name: nginx
        type: helm
        specs:
          repo: bitnami
          chart: nginx
    """)
    return ValidationContext(
        base_dir=str(tmp_path),
        config_dir="config"
    )
```

---

## 🚨 즉시 수정 필요 항목

### 1. 실험적 코드 테스트 실패

**파일**: `tests/unit/models/test_config_model.py`

```python
# 11개 테스트 실패 원인
# - copy, install-yaml, install-action 앱 타입 미구현
# - Spec 모델 누락
```

**조치**:
- 옵션 A: 실험 코드 제거 (실제 사용 안 하는 경우)
- 옵션 B: Spec 모델 구현 완료

### 2. E2E 테스트 안정화

**원인**: 외부 네트워크 의존성

**조치**:
```python
# pytest.ini
[pytest]
markers =
    e2e: End-to-end tests (deselect with '-m "not e2e"')
    network: Tests requiring network access
```

**사용법**:
```bash
# 로컬: 단위 테스트만
pytest -m "not e2e"

# CI/CD: 전체 테스트
pytest
```

---

## 📈 목표 커버리지

| 단계 | 기간 | 목표 커버리지 | 현재 | 차이 |
|------|------|---------------|------|------|
| **Phase 1** | 3일 | 40% | 22% | +18% |
| **Phase 2** | 2일 | 55% | 40% | +15% |
| **Phase 3** | 1일 | 65% | 55% | +10% |
| **Phase 4** | 지속 | 80% | 65% | +15% |

---

## ✅ 체크리스트

### Validators 테스트
- [ ] `basic_validators.py` (3개 클래스)
- [ ] `configuration_validators.py` (4개 클래스)
- [ ] `environment_validators.py` (4개 클래스)
- [ ] `dependency_validators.py` (4개 클래스)
- [ ] `pre_deployment_validators.py` (4개 클래스)

### Commands 테스트
- [ ] `fix.py`
- [ ] `doctor.py`
- [ ] `validate.py`
- [ ] `assistant.py`
- [ ] `init.py`

### Utils 테스트
- [ ] `base_command.py`
- [ ] `cli_check.py`
- [ ] `common.py`
- [ ] `diagnostic_system.py`

### 테스트 실패 수정
- [ ] config_model 실험 코드 정리
- [ ] E2E 테스트 마커 추가

---

## 📚 참고 리소스

- [pytest-cov 문서](https://pytest-cov.readthedocs.io/)
- [unittest.mock 가이드](https://docs.python.org/3/library/unittest.mock.html)
- [pytest fixtures](https://docs.pytest.org/en/latest/fixture.html)

---

**작성자**: Claude (claude-sonnet-4-5)
**긴급도**: 🔴 높음 (Validators 0% 커버리지)
**다음 조치**: Phase 1 Validators 테스트 작성 착수
