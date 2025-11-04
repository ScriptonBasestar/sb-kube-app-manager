# 📚 SBKube Documentation Index

> Kubernetes deployment automation CLI tool for k3s with Helm, YAML, and Git integration

**SBKube** is a CLI tool for automating Kubernetes deployments on k3s clusters. It integrates Helm charts, YAML manifests, and Git repositories into a unified declarative configuration.

**SBKube**는 YAML, Helm, Git 리소스를 로컬에서 정의하고 Kubernetes 환경에 일관되게 배포할 수 있는 CLI 도구입니다.

---

## 🔍 Quick Navigation

| I want to... | Go to |
|--------------|-------|
| **Understand SBKube** | [PRODUCT.md](../PRODUCT.md) |
| **Install and use** | [Getting Started](01-getting-started/README.md) |
| **Configure deployments** | [Configuration Guide](03-configuration/config-schema.md) |
| **Learn commands** | [Commands Reference](02-features/commands.md) |
| **Troubleshoot** | [Troubleshooting](07-troubleshooting/README.md) |
| **Contribute code** | [Developer Guide](04-development/README.md) |
| **Understand architecture** | [Architecture](10-modules/sbkube/ARCHITECTURE.md) |

---

## 📋 문서 구조

### 🚀 [시작하기](01-getting-started/)

- 설치 및 환경 설정
- 빠른 시작 가이드
- 기본 사용 예제

### ⚙️ [기능 설명](02-features/)

- [전체 기능 개요](02-features/README.md)
- [명령어 참조](02-features/commands.md)
- [Hooks 가이드](02-features/hooks-guide.md)
- [Hooks 참조](02-features/hooks-reference.md)
- [LLM-Friendly Output](02-features/llm-friendly-output.md)
- 지원 애플리케이션 타입 설명

### 🔧 [설정 가이드](03-configuration/)

- 설정 파일 스키마 (config.yaml, sources.yaml)
- [설정 마이그레이션](03-configuration/migration-guide.md)
- JSON 스키마 검증

### 👨‍💻 [개발자 가이드](04-development/)

- [개발 환경 구성](04-development/README.md)
- [테스트 가이드](04-development/testing.md)
- 기여 방법 및 코드 스타일

### 🚀 [배포 가이드](06-deployment/)

- [배포 가이드](06-deployment/deployment-guide.md)
- PyPI 패키지 배포
- 로컬 개발 환경 설치
- 프로덕션 배포 방법

### 🔍 [문제 해결](07-troubleshooting/)

- [일반적인 문제 및 해결책](07-troubleshooting/README.md)
- [자주 묻는 질문 (FAQ)](07-troubleshooting/faq.md)
- 디버깅 가이드

### 📚 [튜토리얼](08-tutorials/)

- [첫 번째 배포](08-tutorials/01-getting-started.md)
- [다중 앱 배포](08-tutorials/02-multi-app-deployment.md)
- [프로덕션 배포](08-tutorials/03-production-deployment.md)
- [고급 커스터마이징](08-tutorials/04-customization.md)
- [문제 해결 실습](08-tutorials/05-troubleshooting.md)

---

## 🎯 주요 특징

### 다단계 워크플로우

```
prepare → build → template → deploy
```

### 지원 애플리케이션 타입

- **helm** / **git** / **http** - 소스 준비

- **helm** / **yaml** / **action** / **exec** - 배포 방법

### 설정 파일

- **config.yaml** - 애플리케이션 정의 및 배포 스펙
- **sources.yaml** - 외부 소스 정의 (Helm repos, Git repos)
- **values/** - Helm 값 파일 디렉토리

---

## 🚀 빠른 시작

```bash
# 설치
pip install sbkube

# 기본 워크플로우
sbkube prepare --base-dir . --app-dir config
sbkube build --base-dir . --app-dir config  
sbkube template --base-dir . --app-dir config --output-dir rendered/
sbkube deploy --base-dir . --app-dir config --namespace <namespace>
```

---

## 🏗️ 아키텍처 개요

### 핵심 구조

- **sbkube/** - 메인 Python 패키지
  - **cli.py** - Click 기반 CLI 엔트리포인트
  - **commands/** - 개별 명령어 구현
  - **models/** - Pydantic 데이터 모델
  - **utils/** - 공통 유틸리티

### 실행 중 디렉토리 구조

- **charts/** - 다운로드된 Helm 차트 (prepare 단계)
- **repos/** - 클론된 Git 저장소 (prepare 단계)
- **build/** - 빌드된 애플리케이션 아티팩트 (build 단계)
- **rendered/** - 템플릿된 YAML 출력 (template 단계)

---

## 📚 관련 자료

### 공식 저장소

- 🏠 [GitHub Repository](https://github.com/ScriptonBasestar/kube-app-manaer)
- 📦 [PyPI Package](https://pypi.org/project/sbkube/)

### 개발 정보

- 🏢 **개발**: [ScriptonBasestar](https://github.com/ScriptonBasestar)
- 📄 **라이선스**: MIT License
- 🐍 **Python**: 3.12 이상 required
- 🛠️ **의존성**: Click, Pydantic, PyYAML, GitPython

---

## 💬 지원 및 기여

- 📋 [이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)
- 📧 **문의**: archmagece@users.noreply.github.com
- 🤝 **기여**: [개발자 가이드](04-development/README.md) 참조

---

## 🔗 내부 문서 (개발팀용)

### [99-internal/](99-internal/) *(메인 인덱스에서 제외)*

> 💡 **Note**: 99-internal 디렉토리는 내부 작업 문서로, 공식 문서에서 제외됩니다.
> 개발 중 임시 노트, 백로그, 작업 메모 등을 포함합니다.

- 개발 백로그 및 향후 구현 예정 기능
- 문서 업데이트 필요 항목 추적
- 임시 작업 노트 및 메모

### AI 작업 가이드

- [CLAUDE.md](../CLAUDE.md) - AI 에이전트를 위한 통합 작업 가이드

---

## 🤖 Context7 Integration (For LLMs)

This documentation is optimized for Context7 and AI agent access:

### Library Information
- **Library ID**: `/archmagece/sbkube` (registration pending)
- **Repository**: https://github.com/archmagece/sb-kube-app-manager
- **Documentation URL**: https://github.com/archmagece/sb-kube-app-manager/tree/main/docs
- **Primary Language**: English (with Korean translations)
- **Code Examples**: 100+ snippets across documentation

### Key Topics for LLM Queries

**Commands**:
- `prepare` - Download Helm charts and Git repositories
- `build` - Build Docker images
- `template` - Render Kubernetes manifests
- `deploy` - Apply manifests to cluster
- `apply` - Unified workflow (all stages)
- `status` - Check deployment status
- `history` - View deployment history
- `rollback` - Rollback to previous version

**Configuration**:
- `config.yaml` - Application definitions and deployment specs
- `sources.yaml` - External sources (Helm repos, Git repos)
- Helm chart customization - `overrides` and `removes`
- Dependency management - `depends_on` configuration

**Architecture**:
- Multi-stage workflow: prepare → build → template → deploy
- Pydantic-based validation
- SQLAlchemy state management
- Click CLI framework

### Document Priority for AI Agents

1. **Product Understanding**: [PRODUCT.md](../PRODUCT.md) → [product-spec.md](00-product/product-spec.md)
2. **Implementation**: [ARCHITECTURE.md](10-modules/sbkube/ARCHITECTURE.md) → [API_CONTRACT.md](10-modules/sbkube/API_CONTRACT.md)
3. **Usage**: [commands.md](02-features/commands.md) → [config-schema.md](03-configuration/config-schema.md)
4. **Troubleshooting**: [troubleshooting/](07-troubleshooting/)

See [CLAUDE.md](../CLAUDE.md) for complete AI agent guidelines.

---

*📅 Last Updated: 2025-10-31 | 📋 Documentation Version: v1.2*
*🎯 SBKube v0.6.0 | 🌐 English + Korean*
