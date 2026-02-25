______________________________________________________________________

## type: Project Overview audience: End User, Developer topics: [introduction, features, installation, documentation] llm_priority: high entry_point: true last_updated: 2025-11-13

# 🧩 SBKube

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sbkube)](<>)
[![Repo](https://img.shields.io/badge/GitHub-sb--kube--app--manager-blue?logo=github)](https://github.com/ScriptonBasestar/sb-kube-app-manager)
[![Version](https://img.shields.io/badge/version-0.11.0-green)](CHANGELOG.md)
[![Stable](https://img.shields.io/badge/stable-0.11.0-blue)](CHANGELOG.md)

**SBKube** is a CLI tool for automating Kubernetes deployments on k3s clusters. It integrates Helm charts, YAML
manifests, and Git repositories into a unified declarative configuration.

**SBKube**는 `YAML`, `Helm`, `Git` 리소스를 로컬에서 정의하고 `k3s` 등 Kubernetes 환경에 일관되게 배포할 수 있는 CLI 도구입니다.

> Kubernetes deployment automation CLI tool for k3s with Helm, YAML, and Git integration k3s용 헬름+yaml+git 배포 자동화 CLI 도구

______________________________________________________________________

## 🚀 Quick Start

### Installation

```bash
# Using uv (recommended)
uv add sbkube

# Or using pip
pip install sbkube

# Verify installation
sbkube version
# Expected: 0.11.0
```

### Basic Usage

```bash
# Unified workflow (recommended - v0.8.0+)
sbkube validate --app-dir config   # 🆕 Validate config and check PVs
sbkube apply --app-dir config --namespace production

# Or step-by-step execution
sbkube prepare --app-dir config    # Download Helm charts and Git repos
sbkube build --app-dir config      # Build custom images (if needed)
sbkube template --app-dir config   # Render Kubernetes manifests
sbkube validate --app-dir config   # 🆕 Validate before deployment (v0.8.0+)
sbkube deploy --app-dir config --namespace production  # Deploy to cluster
```

### Configuration Example

Create a `config.yaml` file:

```yaml
namespace: production

apps:
  grafana:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    values:
      - grafana.yaml

  backend:
    type: helm
    chart: ./charts/backend
    depends_on:
      - grafana
```

Then deploy:

```bash
sbkube apply --app-dir . --namespace production
```

## 🎉 What's New in v0.9.1

### Update Management System 🔄

**Easy Chart Update Checking**: Automatically detect available Helm chart updates and optionally update your config.

```bash
# Check for updates
sbkube check-updates

# Example output:
# 📊 Available Updates:
#
# grafana        6.50.0 → 7.0.0   🔴 major
# redis          18.0.0 → 18.5.1  🟡 minor
# nginx          1.2.3  → 1.2.4   🟢 patch

# Interactive config.yaml update
sbkube check-updates --update-config

# Integrated with status command
sbkube status --check-updates
```

**Key Features**:
- 🔍 Semantic version comparison (major/minor/patch)
- 🎨 Visual update indicators (🔴 🟡 🟢)
- 🤖 LLM-friendly output support
- ⚡ Interactive config.yaml updates
- 📦 Check all Helm releases with `--all`

## 🎉 What's New in v0.11.0

### Unified Multi-Phase Workflow

Use unified config (`sbkube.yaml`) with `apply` workflow.

```bash
sbkube apply -f sbkube.yaml
sbkube apply -f sbkube.yaml --phase p2-data
```

**See**: [Unified Config Schema](docs/03-configuration/unified-config-schema.md)

**Full Release Notes**: [CHANGELOG.md](CHANGELOG.md)

______________________________________________________________________

## 📋 Previous Release: v0.8.0

<details>
<summary>Chart Path Collision Prevention & PV/PVC Validation</summary>

### Chart Path Collision Prevention ⚠️ Breaking Change

Charts from different repos with the same name no longer collide:

```bash
# New structure
.sbkube/charts/grafana/loki-5.0.0/        # Clear and unique
.sbkube/charts/my-company/redis-1.0.0/    # Different repo
```

### PV/PVC Validation for Manual Provisioning

Early detection of missing PersistentVolumes:

```bash
sbkube validate
# ❌ 스토리지 검증 실패: postgresql PV 없음
# 💡 PV 생성 방법 안내 제공
```

**See**: [v0.8.0 Release Notes](docs/RELEASE_v0.8.0.md)

</details>

______________________________________________________________________

## 📚 Documentation

### 📘 Core Documentation (Start Here)

- **[PRODUCT.md](PRODUCT.md)** - 제품 개요 (무엇을, 왜): 문제 정의, 사용자 시나리오, 핵심 기능
- **[SPEC.md](SPEC.md)** - 기술 명세 (어떻게): 시스템 아키텍처, 워크플로우, API 명세

> 💡 PRODUCT.md는 "무엇을 만들고 왜 만드는가"를, SPEC.md는 "어떻게 구현하는가"를 설명합니다.

### 📖 Product & Planning

- 📋 [Product Definition](docs/00-product/product-definition.md) - 제품 정의 및 해결 과제
- 📖 [Feature Specification](docs/00-product/product-spec.md) - 전체 기능 및 사용자 시나리오
- 🗺️ [Vision & Roadmap](docs/00-product/vision-roadmap.md) - 장기 비전 및 개발 계획
- 👥 [Target Users](docs/00-product/target-users.md) - 사용자 페르소나 및 여정

### 👤 User Guides

- 📖 [Getting Started](docs/01-getting-started/) - 설치 및 빠른 시작
- ⚙️ [Features](docs/02-features/) - 명령어 및 기능 설명
- 🔧 [Configuration](docs/03-configuration/) - 설정 파일 가이드
- 📖 [Examples](examples/) - 다양한 배포 시나리오
- 🔍 [Troubleshooting](docs/07-troubleshooting/) - 일반적인 문제 및 해결책

### 👨‍💻 Developer Resources

- 👨‍💻 [Developer Guide](docs/04-development/) - 개발 환경 설정
- 🤖 [AI Agent Guide](CLAUDE.md) - AI 에이전트 통합 가이드
- 🏗️ [Architecture](docs/10-modules/sbkube/ARCHITECTURE.md) - 상세 아키텍처 설계 (SPEC.md 기반)
- 📄 [API Contract](docs/10-modules/sbkube/API_CONTRACT.md) - API 참조 (SPEC.md 기반)

### 🤖 AI Integration

- 🤖 [LLM Guide](LLM_GUIDE.md) - AI 최적화 참조 (다른 프로젝트에서 SBKube 사용 시)
  - 빠른 명령어 참조
  - 설정 예제
  - 일반 패턴 및 문제 해결
  - AI 어시스턴트용 설계 (Claude, ChatGPT 등)

**전체 문서 인덱스**: [docs/INDEX.md](docs/INDEX.md)

## ⚙️ Key Features

### LLM-Friendly Output 🤖

SBKube supports multiple output formats optimized for LLM agents and automation:

```bash
# Human-friendly (default)
sbkube apply

# LLM-optimized (80-90% token savings)
sbkube --format llm apply

# Machine-parseable JSON
sbkube --format json apply

# Environment variable support (recommended for LLM agents)
export SBKUBE_OUTPUT_FORMAT=llm
sbkube apply
```

**See:** [LLM-Friendly Output Guide](docs/02-features/llm-friendly-output.md)

### Multi-Stage Workflow

```
prepare → build → template → deploy
```

Or **unified execution**: `sbkube apply` (runs all 4 stages automatically)

**Stage descriptions:**

- `prepare`: Download Helm charts and clone Git repositories
- `build`: Build Docker images (if needed)
- `template`: Render Kubernetes manifests from Helm charts
- `deploy`: Apply manifests to Kubernetes cluster

### Supported Application Types

SBKube supports various deployment sources:

| Type | Description | Example | |------|-------------|---------| | **helm** | Helm charts (remote/local) |
`chart: grafana/grafana` | | **yaml** | Raw YAML manifests | `chart: ./manifests/` | | **git** | Git repositories |
`git_url: https://github.com/...` | | **http** | HTTP file downloads | `url: https://example.com/manifest.yaml` | |
**action** | Custom actions (apply/delete) | `action: apply` | | **exec** | Custom command execution |
`exec: ./scripts/deploy.sh` |

### Configuration-Based Management

SBKube uses declarative YAML files for all configurations:

- **config.yaml** - Application definitions and deployment specs
- **sources.yaml** - External sources (Helm repos, Git repos)
- **values/** - Helm values files directory

### Helm Chart Customization

Advanced chart customization without forking:

- **overrides** - Replace files in chart templates
- **removes** - Remove files from chart templates

### Configuration Examples

**Simple Helm Deployment**:

```yaml
namespace: my-namespace

apps:
  grafana:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    values:
      - grafana.yaml
```

**Chart Customization**:

```yaml
apps:
  cnpg:
    type: helm
    chart: cloudnative-pg/cloudnative-pg
    overrides:
      templates/secret.yaml: my-custom-secret.yaml  # Replace chart file
    removes:
      - templates/serviceaccount.yaml               # Remove chart file
```

**Dependency Management**:

```yaml
apps:
  database:
    type: helm
    chart: cloudnative-pg/cloudnative-pg

  backend:
    type: helm
    chart: ./charts/backend
    depends_on:
      - database  # Deploy backend after database
```

More examples: [examples/](examples/) directory

## 📊 상태 관리 및 모니터링

### 새로운 통합 명령어 (v0.6.0+)

SBKube는 배포 상태 관리를 위한 직관적인 명령어를 제공합니다:

```bash
# 클러스터 상태 확인
sbkube status

# App-group별 그룹핑
sbkube status --by-group

# 특정 app-group 상세 조회
sbkube status app_000_infra_network

# 의존성 트리 시각화
sbkube status --deps

# Pod 헬스체크 상세 정보
sbkube status --health-check

# 배포 히스토리
sbkube history

# 두 배포 비교
sbkube history --diff dep_123,dep_456

# Helm values 비교
sbkube history --values-diff dep_123,dep_456

# 롤백
sbkube rollback dep_123
```

### App-Group 기반 관리

애플리케이션을 논리적 그룹으로 관리할 수 있습니다:

```yaml
apps:
  - name: app_000_infra_network  # 인프라 네트워크 그룹
    type: helm
    chart: cilium/cilium

  - name: app_010_data_postgresql  # 데이터 스토리지 그룹
    type: helm
    chart: cloudnative-pg/cloudnative-pg
    deps:
      - app_000_infra_network

  - name: app_020_app_backend  # 애플리케이션 그룹
    type: helm
    chart: ./charts/backend
    deps:
      - app_010_data_postgresql
```

**App-group 네이밍 컨벤션**: `app_{priority}_{category}_{name}`

- `priority`: 000-999 (배포 우선순위)
- `category`: infra, data, app 등
- `name`: 구체적인 애플리케이션 이름

### Deprecated 명령어 마이그레이션

v1.0.0에서 제거될 예정인 명령어:

```bash
# 이전 (deprecated)          # 새로운 (권장)
sbkube cluster status      → sbkube status
sbkube state list          → sbkube history
sbkube state show <id>     → sbkube history --show <id>
sbkube state rollback <id> → sbkube rollback <id>
```

자세한 내용은 [CHANGELOG.md](CHANGELOG.md#unreleased)를 참조하세요.

## 🔄 마이그레이션

### v0.7.x → v0.8.0 업그레이드 (5분 소요)

**⚠️ Breaking Change**: Chart 경로 구조 변경

```bash
# 1. 기존 charts 제거
rm -rf .sbkube/charts

# 2. 새 구조로 재다운로드
sbkube prepare --force

# 3. 배포
sbkube apply
```

**상세 가이드**: [v0.8.0 Migration Guide](docs/MIGRATION_v0.8.0.md)

### v0.2.x → v0.4.10+ 업그레이드

자동 마이그레이션 도구를 사용하세요:

```bash
sbkube migrate old-config.yaml -o config.yaml
```

**상세 내용**: [CHANGELOG.md](CHANGELOG.md) 및 [Migration Guide](docs/03-configuration/migration-guide.md)

## 💬 지원

- 📋 [이슈 트래커](https://github.com/ScriptonBasestar/sb-kube-app-manager/issues)
- 📧 문의: archmagece@users.noreply.github.com

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

______________________________________________________________________

*🇰🇷 한국 k3s 환경에 특화된 Kubernetes 배포 자동화 도구*
