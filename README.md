# 🧩 SBKube

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sbkube)](<>)
[![Repo](https://img.shields.io/badge/GitHub-kube--app--manaer-blue?logo=github)](https://github.com/archmagece/sb-kube-app-manager)
[![Version](https://img.shields.io/badge/version-0.6.0-blue)](CHANGELOG.md)

**SBKube** is a CLI tool for automating Kubernetes deployments on k3s clusters. It integrates Helm charts, YAML manifests, and Git repositories into a unified declarative configuration.

**SBKube**는 `YAML`, `Helm`, `Git` 리소스를 로컬에서 정의하고 `k3s` 등 Kubernetes 환경에 일관되게 배포할 수 있는 CLI 도구입니다.

> Kubernetes deployment automation CLI tool for k3s with Helm, YAML, and Git integration
> k3s용 헬름+yaml+git 배포 자동화 CLI 도구

______________________________________________________________________

## 🚀 Quick Start

### Installation

```bash
pip install sbkube
```

### Basic Usage

```bash
# Unified workflow (recommended)
sbkube apply --app-dir config --namespace production

# Or step-by-step execution
sbkube prepare --app-dir config    # Download Helm charts and Git repos
sbkube build --app-dir config      # Build custom images (if needed)
sbkube template --app-dir config   # Render Kubernetes manifests
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

## 📚 Documentation

### Product Understanding

Complete product definition and specifications: **[PRODUCT.md](PRODUCT.md)**

- 📋 [Product Definition](docs/00-product/product-definition.md) - Problem statement and solutions
- 📖 [Feature Specification](docs/00-product/product-spec.md) - Complete features and user scenarios
- 🗺️ [Vision & Roadmap](docs/00-product/vision-roadmap.md) - Long-term vision and development plan
- 👥 [Target Users](docs/00-product/target-users.md) - User personas and journeys

### User Guides

- 📖 [Getting Started](docs/01-getting-started/) - Installation and quick start
- ⚙️ [Features](docs/02-features/) - Commands and feature descriptions
- 🔧 [Configuration](docs/03-configuration/) - Configuration file guide
- 📖 [Examples](examples/) - Various deployment scenarios
- 🔍 [Troubleshooting](docs/07-troubleshooting/) - Common issues and solutions

### Developer Resources

- 👨‍💻 [Developer Guide](docs/04-development/) - Development environment setup
- 🤖 [AI Agent Guide](CLAUDE.md) - Integrated guide for AI agents
- 🏗️ [Architecture](docs/10-modules/sbkube/ARCHITECTURE.md) - Detailed architecture design
- 📄 [API Contract](docs/10-modules/sbkube/API_CONTRACT.md) - API reference

Full documentation index: **[docs/INDEX.md](docs/INDEX.md)**

## ⚙️ Key Features

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

| Type | Description | Example |
|------|-------------|---------|
| **helm** | Helm charts (remote/local) | `chart: grafana/grafana` |
| **yaml** | Raw YAML manifests | `chart: ./manifests/` |
| **git** | Git repositories | `git_url: https://github.com/...` |
| **http** | HTTP file downloads | `url: https://example.com/manifest.yaml` |
| **action** | Custom actions (apply/delete) | `action: apply` |
| **exec** | Custom command execution | `exec: ./scripts/deploy.sh` |

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

v0.2.x에서 현재 버전으로 업그레이드하는 경우, 자동 마이그레이션 도구를 사용하세요:

```bash
sbkube migrate old-config.yaml -o config.yaml
```

자세한 내용은 [CHANGELOG.md](CHANGELOG.md) 및 [Migration Guide](docs/MIGRATION.md)를 참조하세요.

## 💬 지원

- 📋 [이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)
- 📧 문의: archmagece@users.noreply.github.com

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

______________________________________________________________________

*🇰🇷 한국 k3s 환경에 특화된 Kubernetes 배포 자동화 도구*
