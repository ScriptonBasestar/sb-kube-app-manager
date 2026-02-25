# CLAUDE.md

AI navigation hub for SBKube project. **Always load this file first.**

---

## Quick Navigation

| Query | Primary → Secondary |
|-------|---------------------|
| **What/Why** | [PRODUCT.md](PRODUCT.md) → [docs/00-product/](docs/00-product/) |
| **How/Implementation** | [ARCHITECTURE.md](ARCHITECTURE.md) → [docs/10-modules/sbkube/](docs/10-modules/sbkube/) |
| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) → [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md) |
| Commands | [docs/02-features/commands.md](docs/02-features/commands.md) → `make help` |
| Config schema | [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md) |
| Migration | [docs/03-configuration/migration-guide.md](docs/03-configuration/migration-guide.md) |
| Testing | [docs/04-development/testing.md](docs/04-development/testing.md) |
| Troubleshooting | [docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md) |
| Dev setup | [docs/04-development/README.md](docs/04-development/README.md) |
| External AI ref | [USAGE.md](USAGE.md) + `--format llm` |

**SSOT**: PRODUCT.md (무엇을/왜) + ARCHITECTURE.md (어떻게) → 하위 문서는 상세화만

---

## 1. Essential Project Info

- **Product**: SBKube - Kubernetes deployment automation CLI (k3s)
- **Tech Stack**: Python 3.14+, Click, Pydantic, SQLAlchemy, Rich
- **Version**: v0.11.0
- **Core Workflow**: `prepare → build → template → deploy` (또는 `sbkube apply -f sbkube.yaml`)

```
sbkube/
├── cli.py          # Click entry point
├── commands/       # Command implementations
├── models/         # Pydantic models (config_model, sources_model, unified_config_model)
├── state/          # SQLAlchemy state management
├── utils/          # Utilities (base_command, output_manager, hook_executor)
└── validators/     # Validation logic

tests/              # unit/, integration/, e2e/, performance/
docs/               # Product-First: 00-product/ > 04-development/ > 10-modules/
```

---

## 2. Development Environment

### Package Management (Critical)

```bash
uv add package_name          # ✅ correct
uv add --group dev pkg       # ✅ dev dependency
uv run pytest tests/         # ✅ run with uv
pip install package_name     # ❌ PROHIBITED
```

### Key Commands

```bash
# Setup
uv sync && uv pip install -e .

# Daily workflow
make check              # syntax + mypy (fast)
make lint-fix           # ruff + mypy + bandit auto-fix
make test-quick         # fast unit tests only
make test               # all tests
make ci                 # full CI (lint + test)
```

### Testing

```bash
# Categories
make test-unit          # tests/unit/ (fast, no external deps)
make test-integration   # requires infra
make test-e2e           # requires Kubernetes cluster

# Markers
pytest tests/ -m "not integration and not slow"
pytest tests/ -m integration
```

### .sbkube Working Directory

- Location: **same dir as `sources.yaml`** (NOT project root)
- Contents: `charts/`, `repos/`, `build/`, `rendered/`
- Git: never commit (`.gitignore`)

---

## 3. Architecture Patterns

### Config Format (v0.11.0+)

Unified `sbkube.yaml` replaces legacy `sources.yaml` + `config.yaml`:

```yaml
apiVersion: sbkube/v1
metadata:
  name: my-deployment
settings:
  kubeconfig: ~/.kube/config
  kubeconfig_context: prod
  namespace: production
  helm_repos:
    grafana: https://grafana.github.io/helm-charts
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    version: "10.1.2"
```

### Key Models

| File | Models |
|------|--------|
| `sbkube/models/unified_config_model.py` | `UnifiedConfig`, `UnifiedSettings`, `PhaseReference` |
| `sbkube/models/config_model.py` | `SBKubeConfig`, `AppConfig` |
| `sbkube/models/sources_model.py` | `SourceScheme`, `HelmRepoScheme` |

**Pydantic `extra="forbid"`**: 모든 모델은 불명확한 필드 거부 → 정확한 필드명 사용 필수

### Command Pattern

All commands inherit from `EnhancedBaseCommand` (`sbkube/utils/base_command.py`):
- `self.formatter` → `OutputFormatter` (human/llm/json/yaml)
- `self.hook_executor` → `HookExecutor`
- `self.config_manager` → `ConfigManager`

### Output Format

```bash
sbkube --format human apply   # Rich console (default)
sbkube --format llm apply     # Token-optimized (80-90% reduction)
sbkube --format json status   # Structured JSON
```

### Exception Hierarchy

```
SbkubeError → ConfigValidationError | CliToolNotFoundError | HelmExecutionError
```

---

## 4. AI Agent Guidelines

### Starting Work

1. **PRODUCT.md** → what/why overview
2. **ARCHITECTURE.md** → how/implementation
3. **Source code** → specific implementation

### Code Change Checklist

1. `make test-quick` - run unit tests
2. `make check` - type check
3. Update docs if behavior changed
4. Pydantic model changes → update tests + JSON schema

### New Feature

1. Inherit `EnhancedBaseCommand`
2. Use `self.formatter` for output
3. Register in `cli.py` + `SbkubeGroup.COMMAND_CATEGORIES`
4. Write tests (success + error cases)
5. Document in `docs/02-features/commands.md`

### Test Patterns

```python
# OutputManager mocking
from sbkube.utils.output_manager import OutputManager
output = MagicMock(spec=OutputManager)

# Integration test marking
@pytest.mark.integration
def test_deploy_with_cluster(): ...

# Flexible assertions (Korean/English)
assert ("App directory not found" in result.output
        or "설정 파일을 찾을 수 없습니다" in result.output)

# Modern Helm format (v0.6.0+)
chart: grafana/grafana    # ✅ correct
# repo: grafana + chart: grafana  ❌ deprecated
```

### AI Response Style

- **즉시 실행**: "적용할까요?" 금지 → 바로 실행
- **자동 테스트 갱신**: 코드 수정 시 관련 테스트도 함께 수정
- **Python 문법**: indent/syntax 오류 절대 금지

---

## 5. Critical Rules

| Rule | Requirement |
|------|-------------|
| Package manager | `uv` only (no `pip`, no `requirements.txt`) |
| Python version | 3.14+ strict |
| Temp files | `tmp/` or `tmp/scripts/` only |
| Build artifacts | `build/`, `tmp/bin/`, `dist/` only |
| Auto-push | ❌ PROHIBITED |
| Auto-commit | ✅ allowed |
| Docs language | AI context: English / User-facing: Korean |

---

## 6. Recent Lessons (2025-01)

- Integration tests: must use `@pytest.mark.integration`
- Build functions (v0.7.1+): require `output: OutputManager` parameter
- Error messages: bilingual (Korean + English) - use flexible assertions
- `get_error_suggestions()`: returns default guide (not None) as fallback
- Config format: unified `sbkube.yaml` (v0.10.0+) replaces legacy files

---

## 7. Version

- **CLAUDE.md**: v3.0 (2026-02-25)
- **SBKube**: v0.11.0
- **Prev CLAUDE.md**: 929 lines → 180 lines (81% reduction)
