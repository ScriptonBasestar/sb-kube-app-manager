# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **AI-specific routing rules and context navigation for SBKube project**

______________________________________________________________________

## 📋 Quick Navigation

**New to this project?**
→ Read [PRODUCT.md](PRODUCT.md) first (2-minute overview)

**Query Type Routing**:
- Product questions → [docs/00-product/](docs/00-product/)
- Architecture questions → [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)
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
- **Version**: v0.6.1
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
Level 0 (Entry Point):
  └─ PRODUCT.md

Level 1 (Product Definition):
  ├─ docs/00-product/product-definition.md
  ├─ docs/00-product/product-spec.md
  └─ docs/00-product/target-users.md

Level 2 (Module Architecture):
  ├─ docs/10-modules/sbkube/ARCHITECTURE.md
  └─ docs/10-modules/sbkube/API_CONTRACT.md

Level 3 (Features & Config):
  ├─ docs/02-features/commands.md
  └─ docs/03-configuration/config-schema.md

Level 4 (Implementation):
  └─ sbkube/ (source code)
```

### 2.2 Query Type Routing

| Query Type | Primary Document | Secondary |
|------------|-----------------|-----------|
| **Product Overview** | [PRODUCT.md](PRODUCT.md) | [docs/00-product/product-definition.md](docs/00-product/product-definition.md) |
| **Feature Specs** | [docs/00-product/product-spec.md](docs/00-product/product-spec.md) | [docs/02-features/commands.md](docs/02-features/commands.md) |
| **Architecture** | [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md) | [docs/04-development/architecture-patterns.md](docs/04-development/architecture-patterns.md) |
| **Development Setup** | [docs/04-development/README.md](docs/04-development/README.md) | [Makefile](Makefile) |
| **Commands** | [Makefile](Makefile) | [docs/04-development/quick-commands.md](docs/04-development/quick-commands.md) |
| **Coding Standards** | [docs/04-development/coding-standards.md](docs/04-development/coding-standards.md) | [ruff.toml](ruff.toml), [mypy.ini](mypy.ini) |
| **Testing** | [docs/04-development/testing.md](docs/04-development/testing.md) | [Makefile](Makefile) |
| **Troubleshooting** | [docs/07-troubleshooting/common-dev-issues.md](docs/07-troubleshooting/common-dev-issues.md) | [docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md) |
| **Configuration** | [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md) | [examples/](examples/) |
| **Migration** | [docs/03-configuration/migration-guide.md](docs/03-configuration/migration-guide.md) | [CHANGELOG.md](CHANGELOG.md) |
| **Hooks** | [docs/02-features/hooks-guide.md](docs/02-features/hooks-guide.md) | [docs/02-features/hooks-reference.md](docs/02-features/hooks-reference.md) |
| **LLM Integration** | [docs/02-features/llm-friendly-output.md](docs/02-features/llm-friendly-output.md) | [sbkube/utils/output_formatter.py](sbkube/utils/output_formatter.py) |
| **Deployment** | [docs/06-deployment/deployment-guide.md](docs/06-deployment/deployment-guide.md) | [Makefile](Makefile) |
| **External AI Reference** | [LLM_GUIDE.md](LLM_GUIDE.md) | For using SBKube in other projects |

### 2.3 Context Priority Rules

#### Rule 1: Product-First
All queries start with product context:
```
Query → PRODUCT.md → docs/00-product/ → Specific docs
```

#### Rule 2: Module Boundaries
Module-specific queries reference module docs first:
```
SBKube implementation → docs/10-modules/sbkube/ → sbkube/ source
```

#### Rule 3: Semantic Chunking
Load long documents section by section (<4000 tokens per chunk)

#### Rule 4: Cross-References
Use automatic document linking:
```
product-definition.md → product-spec.md (feature details)
ARCHITECTURE.md → commands/ (implementation code)
```

### 2.4 Token Efficiency Guide

**Minimal Context (< 10K tokens)** - Simple queries:
- PRODUCT.md (full)
- docs/00-product/product-definition.md (overview section)

**Medium Context (10K-50K tokens)** - Feature queries:
- PRODUCT.md
- docs/00-product/product-spec.md (relevant sections)
- docs/02-features/commands.md (specific commands)
- examples/ (usage examples)

**Large Context (50K-100K tokens)** - Implementation work:
- CLAUDE.md
- docs/10-modules/sbkube/ARCHITECTURE.md
- sbkube/ source files (specific modules)
- tests/ (relevant tests)

### 2.5 Semantic Index

**Key Concepts → Document Mapping**:

- **Product Vision**: [docs/00-product/product-definition.md](docs/00-product/product-definition.md), [docs/00-product/vision-roadmap.md](docs/00-product/vision-roadmap.md)
- **Workflow**: [docs/00-product/product-spec.md](docs/00-product/product-spec.md) (Section 1), [docs/02-features/commands.md](docs/02-features/commands.md)
- **Configuration**: [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md), [sbkube/models/config_model.py](sbkube/models/config_model.py)
- **State Management**: [docs/00-product/product-spec.md](docs/00-product/product-spec.md) (Section 4), [sbkube/state/](sbkube/state/)
- **App Types**: [docs/02-features/application-types.md](docs/02-features/application-types.md)
- **LLM Integration**: [docs/02-features/llm-friendly-output.md](docs/02-features/llm-friendly-output.md), [sbkube/utils/output_formatter.py](sbkube/utils/output_formatter.py)

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
2. **[docs/00-product/](docs/00-product/)** → Product definition & specs
3. **[docs/10-modules/sbkube/MODULE.md](docs/10-modules/sbkube/MODULE.md)** → Module structure
4. **Source code** → Specific implementation

### 4.2 Code Change Checklist

**All code changes**:
1. Run tests: `uv run pytest tests/`
2. Update documentation (especially [product-spec.md](docs/00-product/product-spec.md))
3. Type check: `uv run mypy sbkube/`
4. Pydantic model changes: regenerate JSON schema, update tests

### 4.3 New Feature Development

1. Check [product-spec.md](docs/00-product/product-spec.md) for alignment
2. Follow BaseCommand/EnhancedBaseCommand pattern
3. Use Rich Console for output (or OutputFormatter for LLM-friendly output)
4. Add Pydantic model validation
5. Document in [docs/02-features/commands.md](docs/02-features/commands.md)
6. Write tests (success + error cases)

**LLM-Friendly Output**:
- All commands inherit `self.formatter` from `EnhancedBaseCommand`
- Support `--format` option: `human` (default), `llm`, `json`, `yaml`
- Use `OutputFormatter` for structured output when appropriate
- See [llm-friendly-output.md](docs/02-features/llm-friendly-output.md)

### 4.4 New Command Addition

1. Create command in `sbkube/commands/`
2. Inherit from `EnhancedBaseCommand`
3. Register in [cli.py](sbkube/cli.py)
4. Add to `SbkubeGroup.COMMAND_CATEGORIES`
5. Document usage and examples
6. Write unit tests

### 4.5 Bug Fix Workflow

1. Write reproduction test
2. Fix root cause (not symptoms)
3. Add example to `examples/` directory
4. Add edge case tests
5. Update [docs/07-troubleshooting/common-dev-issues.md](docs/07-troubleshooting/common-dev-issues.md) if needed

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
2. **Auto-update tests**: When fixing code, update related tests automatically
3. **Python syntax**: Zero tolerance for indent/syntax errors
4. **Request efficiency**: Maximize work per request

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

- **Document Version**: 1.4
- **Last Updated**: 2025-01-03
- **Target SBKube Version**: v0.6.1+
- **Author**: archmagece@users.noreply.github.com

### Change History

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
2. **Feature queries**: Reference Section 2.2 (Query Type Routing table)
3. **Code writing**: Follow Section 4 (AI Agent Guidelines)
4. **Problem solving**: Check [docs/07-troubleshooting/common-dev-issues.md](docs/07-troubleshooting/common-dev-issues.md)
5. **Detailed info**: Use Section 2 routing to find specialized docs

### Update Policy

- Update this document when adding major features
- Keep navigation table (Section 2.2) current
- Update version number and change history

______________________________________________________________________

**🎯 This document is the AI navigation hub for SBKube project.**

For detailed product information, see [PRODUCT.md](PRODUCT.md). For technical specifications, see [SPEC.md](SPEC.md).
