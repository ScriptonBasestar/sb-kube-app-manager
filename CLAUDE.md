______________________________________________________________________

## type: AI Agent Instructions audience: AI Agent topics: [navigation, routing, context, guidelines] llm_priority: critical entry_point: true always_load: true last_updated: 2025-01-04

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **AI-specific routing rules and context navigation for SBKube project**

______________________________________________________________________

## 📋 Quick Navigation

**New to this project?** → Start with these root documents:

1. **[PRODUCT.md](PRODUCT.md)** (무엇을, 왜) - Product overview, problems, solutions, users
2. **[SPEC.md](SPEC.md)** (어떻게) - Technical architecture, workflows, implementation details

**Query Type Routing**:

- **"무엇을" questions** (What/Why) → [PRODUCT.md](PRODUCT.md)
- **"어떻게" questions** (How/Implementation) → [SPEC.md](SPEC.md)
- Product planning → [docs/00-product/](docs/00-product/)
- Architecture questions → [SPEC.md](SPEC.md) Section 2, then [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)
- Workflow details → [SPEC.md](SPEC.md) Section 3
- Data models → [SPEC.md](SPEC.md) Section 4
- API specs → [SPEC.md](SPEC.md) Section 5
- Development setup → [docs/04-development/README.md](docs/04-development/README.md)
- Commands reference → [Makefile](Makefile) (`make help`) or [Quick Commands](docs/04-development/quick-commands.md)
- Coding standards → [docs/04-development/coding-standards.md](docs/04-development/coding-standards.md)
- Architecture patterns → [docs/04-development/architecture-patterns.md](docs/04-development/architecture-patterns.md)
- Hooks documentation → [docs/02-features/hooks-guide.md](docs/02-features/hooks-guide.md)
- Migration guide → [docs/03-configuration/migration-guide.md](docs/03-configuration/migration-guide.md)
- Deployment → [docs/06-deployment/deployment-guide.md](docs/06-deployment/deployment-guide.md)
- Troubleshooting → [docs/07-troubleshooting/common-dev-issues.md](docs/07-troubleshooting/common-dev-issues.md)
- **External AI Reference** → [LLM_GUIDE.md](LLM_GUIDE.md) (for using SBKube in other projects)

______________________________________________________________________

## 1. Essential Project Info

### Basic Information

- **Product**: SBKube - Kubernetes deployment automation CLI for k3s
- **Tech Stack**: Python 3.12+, Click, Pydantic, SQLAlchemy, Rich
- **Current Version**: v0.7.0 (개발 중 / Development)
- **Stable Version**: v0.6.0
- **Architecture**: Monolithic Python CLI application
- **Core Workflow**: `prepare → build → template → deploy` (or `sbkube apply`)

### Key Directories

```
sbkube/          # Core package
├── cli.py       # CLI entry point (Click)
├── commands/    # Command implementations
├── models/      # Pydantic models
├── state/       # SQLAlchemy state management
├── utils/       # Utilities (logger, helm_util, etc.)
└── validators/  # Validation logic

docs/            # Documentation (Product-First structure)
├── 00-product/  # Product definition (highest priority)
├── 04-development/  # Developer guides
└── 10-modules/sbkube/  # Architecture details

tests/           # Test suites (unit, integration, e2e, performance)
```

**For full details**: See [PRODUCT.md](PRODUCT.md) and [docs/INDEX.md](docs/INDEX.md)

______________________________________________________________________

## 2. AI Context Navigation

### 2.1 Context Hierarchy

```
Level 0 (Root Documents - Single Source of Truth):
  ├─ PRODUCT.md (무엇을, 왜)
  └─ SPEC.md (어떻게)

Level 1 (Product Definition):
  ├─ docs/00-product/product-definition.md
  ├─ docs/00-product/product-spec.md
  └─ docs/00-product/target-users.md

Level 2 (Module Architecture):
  ├─ docs/10-modules/sbkube/ARCHITECTURE.md (SPEC.md의 상세화)
  └─ docs/10-modules/sbkube/API_CONTRACT.md (SPEC.md의 상세화)

Level 3 (Features & Config):
  ├─ docs/02-features/commands.md
  └─ docs/03-configuration/config-schema.md

Level 4 (Implementation):
  └─ sbkube/ (source code)
```

**중요 원칙 (Important Principle)**:
- PRODUCT.md와 SPEC.md는 **근본 문서** (root documents)
- 모든 하위 문서는 이 두 문서를 따라야 함
- 하위 문서는 **상세화** 또는 **특화**만 제공

### 2.2 Query Type Routing

| Query Type | Primary Document | Secondary |
|------------|-----------------|-----------|
| **Product Overview (무엇을)** | [PRODUCT.md](PRODUCT.md) | [docs/00-product/product-definition.md](docs/00-product/product-definition.md) |
| **Technical Spec (어떻게)** | [SPEC.md](SPEC.md) | [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md) |
| **System Architecture** | [SPEC.md](SPEC.md) Section 2 | [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md) |
| **Workflow Details** | [SPEC.md](SPEC.md) Section 3 | [docs/02-features/commands.md](docs/02-features/commands.md) |
| **Data Models** | [SPEC.md](SPEC.md) Section 4 | [sbkube/models/](sbkube/models/) |
| **API Specifications** | [SPEC.md](SPEC.md) Section 5 | [docs/10-modules/sbkube/API_CONTRACT.md](docs/10-modules/sbkube/API_CONTRACT.md) |
| **Feature Specs** | [PRODUCT.md](PRODUCT.md) Section 6 | [docs/00-product/product-spec.md](docs/00-product/product-spec.md) |
| **Target Users** | [PRODUCT.md](PRODUCT.md) Section 3 | [docs/00-product/target-users.md](docs/00-product/target-users.md) |
| **Roadmap** | [docs/00-product/vision-roadmap.md](docs/00-product/vision-roadmap.md) | [CHANGELOG.md](CHANGELOG.md) |
| **Development Setup** | [docs/04-development/README.md](docs/04-development/README.md) | [Makefile](Makefile) |
| **Commands Reference** |
[docs/02-features/commands.md](docs/02-features/commands.md) |
[docs/04-development/quick-commands.md](docs/04-development/quick-commands.md) | | **Command Usage** |
[Makefile](Makefile) | [docs/04-development/quick-commands.md](docs/04-development/quick-commands.md) | | **Coding
Standards** | [docs/04-development/coding-standards.md](docs/04-development/coding-standards.md) |
[ruff.toml](ruff.toml), [mypy.ini](mypy.ini) | | **Testing** |
[docs/04-development/testing.md](docs/04-development/testing.md) | [Makefile](Makefile) | | **Configuration** |
[docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md) | [examples/](examples/) | | **App
Types** | [docs/02-features/application-types.md](docs/02-features/application-types.md) |
[docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md) | | **Helm Customization** |
[docs/03-configuration/chart-customization.md](docs/03-configuration/chart-customization.md) |
[docs/03-configuration/helm-chart-types.md](docs/03-configuration/helm-chart-types.md) | | **Helm Charts** |
[docs/03-configuration/helm-chart-types.md](docs/03-configuration/helm-chart-types.md) |
[docs/03-configuration/chart-customization.md](docs/03-configuration/chart-customization.md) | | **Hooks** |
[docs/02-features/hooks-guide.md](docs/02-features/hooks-guide.md) |
[docs/02-features/hooks-reference.md](docs/02-features/hooks-reference.md) | | **Migration** |
[docs/03-configuration/migration-guide.md](docs/03-configuration/migration-guide.md) | [CHANGELOG.md](CHANGELOG.md) | |
**Troubleshooting** | [docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md) |
[docs/07-troubleshooting/common-dev-issues.md](docs/07-troubleshooting/common-dev-issues.md) | | **Deployment Failures**
| [docs/07-troubleshooting/deployment-failures.md](docs/07-troubleshooting/deployment-failures.md) |
[docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md) | | **FAQ** |
[docs/07-troubleshooting/faq.md](docs/07-troubleshooting/faq.md) |
[docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md) | | **Deployment** |
[docs/06-deployment/deployment-guide.md](docs/06-deployment/deployment-guide.md) | [Makefile](Makefile) | | **Best
Practices** | [docs/05-best-practices/directory-structure.md](docs/05-best-practices/directory-structure.md) |
[docs/00-product/product-spec.md](docs/00-product/product-spec.md) | | **Directory Structure** |
[docs/05-best-practices/directory-structure.md](docs/05-best-practices/directory-structure.md) | [examples/](examples/)
| | **Tutorials** | [docs/08-tutorials/README.md](docs/08-tutorials/README.md) |
[docs/01-getting-started/README.md](docs/01-getting-started/README.md) | | **Multi-App Deployment** |
[docs/08-tutorials/02-multi-app-deployment.md](docs/08-tutorials/02-multi-app-deployment.md) |
[docs/02-features/application-types.md](docs/02-features/application-types.md) | | **Production Deployment** |
[docs/08-tutorials/03-production-deployment.md](docs/08-tutorials/03-production-deployment.md) |
[docs/06-deployment/deployment-guide.md](docs/06-deployment/deployment-guide.md) | | **Customization** |
[docs/08-tutorials/04-customization.md](docs/08-tutorials/04-customization.md) |
[docs/03-configuration/chart-customization.md](docs/03-configuration/chart-customization.md) | | **LLM Integration** |
[docs/02-features/llm-friendly-output.md](docs/02-features/llm-friendly-output.md) |
[sbkube/utils/output_formatter.py](sbkube/utils/output_formatter.py) | | **External AI Reference** |
[LLM_GUIDE.md](LLM_GUIDE.md) | For using SBKube in other projects | | **API Contract** |
[docs/10-modules/sbkube/API_CONTRACT.md](docs/10-modules/sbkube/API_CONTRACT.md) |
[docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md) | | **Dependencies** |
[docs/10-modules/sbkube/DEPENDENCIES.md](docs/10-modules/sbkube/DEPENDENCIES.md) |
[docs/10-modules/sbkube/MODULE.md](docs/10-modules/sbkube/MODULE.md) | | **Debugging** |
[docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md) |
[docs/07-troubleshooting/common-dev-issues.md](docs/07-troubleshooting/common-dev-issues.md) | | **Validation** |
[docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md) |
[docs/02-features/commands.md](docs/02-features/commands.md) (validate command) | | **State Management** |
[docs/02-features/commands.md](docs/02-features/commands.md) (status, history) |
[docs/00-product/product-spec.md](docs/00-product/product-spec.md) | | **Rollback** |
[docs/02-features/commands.md](docs/02-features/commands.md) (rollback command) |
[docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md) | | **App Group Dependencies** |
[examples/app-group-management/](examples/app-group-management/) |
[docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md) (deps field) | | **Kustomize** |
[docs/02-features/application-types.md](docs/02-features/application-types.md) |
[docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md) | | **Error Messages** |
[docs/07-troubleshooting/deployment-failures.md](docs/07-troubleshooting/deployment-failures.md) |
[docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md) | | **Performance** |
[docs/02-features/llm-friendly-output.md](docs/02-features/llm-friendly-output.md) (--quiet mode) |
[docs/05-best-practices/directory-structure.md](docs/05-best-practices/directory-structure.md) | | **Examples** |
[examples/](examples/) | [docs/08-tutorials/README.md](docs/08-tutorials/README.md) | | **Installation** |
[docs/01-getting-started/README.md](docs/01-getting-started/README.md) | [README.md](README.md) |

### 2.3 Context Priority Rules

#### Rule 0: Root Documents First (NEW)

**ALWAYS start with root documents for authoritative information**:

```
"무엇을/왜" queries → PRODUCT.md → docs/00-product/ → Specific docs
"어떻게" queries → SPEC.md → docs/10-modules/ → Source code
```

**중요**: PRODUCT.md와 SPEC.md는 Single Source of Truth (SSOT)
- 하위 문서와 충돌 시 → 항상 PRODUCT.md/SPEC.md 우선
- 하위 문서는 상세화 또는 특화 목적만

#### Rule 1: Product-First

All queries start with product context:

```
Query → PRODUCT.md → docs/00-product/ → Specific docs
```

#### Rule 2: Module Boundaries

Module-specific queries reference SPEC.md first, then module docs:

```
Implementation queries → SPEC.md → docs/10-modules/sbkube/ → sbkube/ source
```

#### Rule 3: Semantic Chunking

Load long documents section by section (\<4000 tokens per chunk)

#### Rule 4: Cross-References

Use automatic document linking from root documents:

```
PRODUCT.md → SPEC.md (implementation details)
SPEC.md → ARCHITECTURE.md (detailed design)
SPEC.md → commands/ (implementation code)
```

### 2.4 Token Efficiency Guide

**Minimal Context (< 10K tokens)** - Simple queries:

- PRODUCT.md (full) or SPEC.md (relevant sections)
- docs/00-product/product-definition.md (overview section)

**Medium Context (10K-50K tokens)** - Feature queries:

- PRODUCT.md + SPEC.md (relevant sections)
- docs/00-product/product-spec.md (relevant sections)
- docs/02-features/commands.md (specific commands)
- examples/ (usage examples)

**Large Context (50K-100K tokens)** - Implementation work:

- PRODUCT.md + SPEC.md (full)
- CLAUDE.md
- docs/10-modules/sbkube/ARCHITECTURE.md
- sbkube/ source files (specific modules)
- tests/ (relevant tests)

### 2.5 Semantic Index

**Key Concepts → Document Mapping**:

- **Product Overview (무엇을, 왜)**: [PRODUCT.md](PRODUCT.md) → [docs/00-product/product-definition.md](docs/00-product/product-definition.md)
- **Technical Implementation (어떻게)**: [SPEC.md](SPEC.md) → [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)
- **Product Vision**: [PRODUCT.md](PRODUCT.md) Section 1, [docs/00-product/vision-roadmap.md](docs/00-product/vision-roadmap.md)
- **System Architecture**: [SPEC.md](SPEC.md) Section 2, [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)
- **Workflow**: [SPEC.md](SPEC.md) Section 3, [docs/02-features/commands.md](docs/02-features/commands.md)
- **Data Models**: [SPEC.md](SPEC.md) Section 4, [sbkube/models/config_model.py](sbkube/models/config_model.py)
- **API Specifications**: [SPEC.md](SPEC.md) Section 5, [docs/10-modules/sbkube/API_CONTRACT.md](docs/10-modules/sbkube/API_CONTRACT.md)
- **Configuration**: [SPEC.md](SPEC.md) Section 4, [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md)
- **State Management**: [SPEC.md](SPEC.md) Section 6, [sbkube/state/](sbkube/state/)
- **Hooks System**: [SPEC.md](SPEC.md) Section 7, [docs/02-features/hooks-guide.md](docs/02-features/hooks-guide.md)
- **App Types**: [PRODUCT.md](PRODUCT.md) Section 6, [docs/02-features/application-types.md](docs/02-features/application-types.md)
- **LLM Integration**: [docs/02-features/llm-friendly-output.md](docs/02-features/llm-friendly-output.md),
  [sbkube/utils/output_formatter.py](sbkube/utils/output_formatter.py)

______________________________________________________________________

## 3. Development Environment

### Package Management (Critical)

**MUST use `uv`**, NOT `pip`:

```bash
# ✅ Correct
uv add package_name
uv add --group dev package_name
uv add --group test package_name
uv run script.py

# ❌ WRONG - Absolutely prohibited
pip install package_name
pip freeze > requirements.txt
```

### Quick Setup

```bash
# Complete environment setup
uv venv && source .venv/bin/activate
uv sync
uv pip install -e .

# Quick test
make test-quick

# Code quality
make lint-fix
```

**For all commands**: See [Makefile](Makefile) (`make help`) or [Quick Commands](docs/04-development/quick-commands.md)

### Working Directory (.sbkube)

- **Location**: Determined by `sources.yaml` location
- **Contents**: `charts/`, `repos/`, `build/`, `rendered/`
- **Git**: NEVER commit (`.gitignore` rule)
- **Auto-created**: During workflow execution

______________________________________________________________________

## 4. AI Agent Guidelines

### 4.1 Context Priority

When starting work:

1. **[PRODUCT.md](PRODUCT.md)** → Product overview
1. **[docs/00-product/](docs/00-product/)** → Product definition & specs
1. **[docs/10-modules/sbkube/MODULE.md](docs/10-modules/sbkube/MODULE.md)** → Module structure
1. **Source code** → Specific implementation

### 4.2 Code Change Checklist

**All code changes**:

1. Run tests: `uv run pytest tests/`
1. Update documentation (especially [product-spec.md](docs/00-product/product-spec.md))
1. Type check: `uv run mypy sbkube/`
1. Pydantic model changes: regenerate JSON schema, update tests

### 4.3 New Feature Development

1. Check [product-spec.md](docs/00-product/product-spec.md) for alignment
1. Follow BaseCommand/EnhancedBaseCommand pattern
1. Use Rich Console for output (or OutputFormatter for LLM-friendly output)
1. Add Pydantic model validation
1. Document in [docs/02-features/commands.md](docs/02-features/commands.md)
1. Write tests (success + error cases)

**LLM-Friendly Output**:

- All commands inherit `self.formatter` from `EnhancedBaseCommand`
- Support `--format` option: `human` (default), `llm`, `json`, `yaml`
- Use `OutputFormatter` for structured output when appropriate
- See [llm-friendly-output.md](docs/02-features/llm-friendly-output.md)

### 4.4 New Command Addition

1. Create command in `sbkube/commands/`
1. Inherit from `EnhancedBaseCommand`
1. Register in [cli.py](sbkube/cli.py)
1. Add to `SbkubeGroup.COMMAND_CATEGORIES`
1. Document usage and examples
1. Write unit tests

### 4.5 Bug Fix Workflow

1. Write reproduction test
1. Fix root cause (not symptoms)
1. Add example to `examples/` directory
1. Add edge case tests
1. Update [docs/07-troubleshooting/common-dev-issues.md](docs/07-troubleshooting/common-dev-issues.md) if needed

### 4.6 Documentation Requirements

**Must update**:

- New features → [docs/00-product/product-spec.md](docs/00-product/product-spec.md)
- Command changes → [docs/02-features/commands.md](docs/02-features/commands.md)
- Architecture changes → [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)
- Config schema changes → [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md)

**Docstring required**:

- All public functions
- All classes
- Complex logic blocks

### 4.7 AI Response Style (Critical)

**MUST follow**:

1. **Immediate execution**: No unnecessary confirmation questions
   - ❌ Bad: "위 변경사항을 적용할까요?"
   - ✅ Good: "변경사항을 적용했습니다. 다음으로 {작업}을 진행하시겠습니까?"
1. **Auto-update tests**: When fixing code, update related tests automatically
1. **Python syntax**: Zero tolerance for indent/syntax errors
1. **Request efficiency**: Maximize work per request

______________________________________________________________________

## 5. Critical Rules from Global CLAUDE.md

### Package Management

- **uv only**: NEVER use `pip` directly or create `requirements.txt`
- **Python 3.12**: Strict requirement, no exceptions

### File Operations

- **Temporary files**: Only in `tmp/` or `tmp/scripts/`
- **Build artifacts**: Only in `build/`, `tmp/bin/`, `dist/` (NEVER in project root)

### Git Policy

- **Auto-commit**: ✅ Allowed
- **Auto-push**: ❌ ABSOLUTELY PROHIBITED (user must manually `git push`)

### Documentation Policy

- **AI context docs**: English recommended
- **User-facing docs**: Korean
- **Schema-based**: Use `~/.claude/schemas/docs/` templates when creating docs

______________________________________________________________________

## 6. Version Info

- **Document Version**: 1.5
- **Last Updated**: 2025-01-06
- **Target SBKube Version**: v0.7.0+ (dev), v0.6.0 (stable)
- **Author**: archmagece@users.noreply.github.com

### Change History

- **v1.5 (2025-01-06)**:

  - **Major Update**: Integrated PRODUCT.md and SPEC.md as root documents
  - Added "Root Documents First" rule (Rule 0) in Context Priority Rules
  - Updated Quick Navigation to emphasize PRODUCT.md (무엇을/왜) and SPEC.md (어떻게) distinction
  - Expanded Query Type Routing table with SPEC.md section references
  - Updated Context Hierarchy to show PRODUCT.md and SPEC.md as Level 0 (SSOT)
  - Updated Semantic Index with PRODUCT.md and SPEC.md mappings
  - Updated version information to v0.7.0 (development) and v0.6.0 (stable)
  - Added principle: "하위 문서는 상세화 또는 특화만 제공"

- **v1.4 (2025-01-03)**:

  - Added LLM Integration to Query Type Routing table
  - Added LLM-Friendly Output section to New Feature Development
  - Updated Semantic Index with LLM integration references
  - Documented `--format` option and OutputFormatter usage

- **v1.3 (2025-01-03)**:

  - Reduced from 1,542 lines to ~470 lines (70% reduction)
  - Converted to smart navigation hub (removed redundant content)
  - Created 4 new specialized docs (coding-standards, architecture-patterns, quick-commands, common-dev-issues)
  - Strengthened cross-reference system
  - Improved token efficiency (15K → 4.5K tokens)

- **v1.2 (2025-01-03)**:

  - Integrated Cursor rules (uv package management, AI response style)
  - Clarified .sbkube working directory rules
  - Detailed test structure (unit/integration/e2e/performance/legacy)
  - Added core architecture patterns summary
  - Strengthened package management rules

______________________________________________________________________

## 7. Document Usage Guide

### For AI Agents

1. **First time**: Read this entire document to understand project structure
1. **Feature queries**: Reference Section 2.2 (Query Type Routing table)
1. **Code writing**: Follow Section 4 (AI Agent Guidelines)
1. **Problem solving**: Check
   [docs/07-troubleshooting/common-dev-issues.md](docs/07-troubleshooting/common-dev-issues.md)
1. **Detailed info**: Use Section 2 routing to find specialized docs

### Update Policy

- Update this document when adding major features
- Keep navigation table (Section 2.2) current
- Update version number and change history

______________________________________________________________________

**🎯 This document is the AI navigation hub for SBKube project.**

For detailed product information, see [PRODUCT.md](PRODUCT.md). For technical specifications, see [SPEC.md](SPEC.md).
