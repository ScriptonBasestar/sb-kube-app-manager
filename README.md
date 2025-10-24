# 🧩 SBKube

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sbkube)](<>)
[![Repo](https://img.shields.io/badge/GitHub-kube--app--manaer-blue?logo=github)](https://github.com/ScriptonBasestar/kube-app-manaer)
[![Version](https://img.shields.io/badge/version-0.4.5-blue)](CHANGELOG.md)

**SBKube**는 `YAML`, `Helm`, `Git` 리소스를 로컬에서 정의하고 `k3s` 등 Kubernetes 환경에 일관되게 배포할 수 있는 CLI 도구입니다.

> k3s용 헬름+yaml+git 배포 자동화 CLI 도구

______________________________________________________________________

## 🚀 빠른 시작

```bash
# 설치
pip install sbkube

# 통합 워크플로우 (권장)
sbkube apply --app-dir config --namespace <namespace>

# 또는 단계별 실행
sbkube prepare --base-dir . --app-dir config
sbkube build --base-dir . --app-dir config
sbkube template --base-dir . --app-dir config --output-dir rendered/
sbkube deploy --base-dir . --app-dir config --namespace <namespace>
```

## 📚 문서 구조

### 제품 이해 (Product-First)

완전한 제품 정의 및 기능 명세는 \*\*[PRODUCT.md](PRODUCT.md)\*\*를 참조하세요.

- 📋 [제품 정의서](docs/00-product/product-definition.md) - 문제 정의 및 해결 방안
- 📖 [기능 명세서](docs/00-product/product-spec.md) - 전체 기능 및 사용자 시나리오
- 🗺️ [비전과 로드맵](docs/00-product/vision-roadmap.md) - 장기 비전 및 개발 계획
- 👥 [대상 사용자](docs/00-product/target-users.md) - 사용자 페르소나 및 여정

### 사용자 가이드

- 📖 [시작하기](docs/01-getting-started/) - 설치 및 빠른 시작
- ⚙️ [기능 가이드](docs/02-features/) - 명령어 및 기능 설명
- 🔧 [설정 가이드](docs/03-configuration/) - 설정 파일 작성법
- 📖 [사용 예제](examples/) - 다양한 배포 시나리오
- 🔍 [문제 해결](docs/07-troubleshooting/) - 일반적인 문제 및 해결책

### 개발자 리소스

- 👨‍💻 [개발자 가이드](docs/04-development/) - 개발 환경 구성
- 🤖 [AI 작업 가이드](CLAUDE.md) - AI 에이전트를 위한 통합 작업 가이드
- 🏗️ [모듈 아키텍처](docs/10-modules/sbkube/ARCHITECTURE.md) - 상세 아키텍처 설계

전체 문서 인덱스는 \*\*[docs/INDEX.md](docs/INDEX.md)\*\*에서 확인하세요.

## ⚙️ 주요 기능

### 다단계 워크플로우

```
prepare → build → template → deploy
```

또는 **통합 실행**: `sbkube apply` (4단계 자동 실행)

### 지원 애플리케이션 타입

- **helm** - Helm 차트 (원격/로컬)
- **yaml** - YAML 매니페스트
- **git** - Git 리포지토리
- **http** - HTTP 파일 다운로드
- **action** - 커스텀 액션 (apply/delete)
- **exec** - 커스텀 명령어 실행

### 설정 기반 관리

- **config.yaml** - 애플리케이션 정의 및 배포 스펙 (간소화된 현재 버전 형식)
- **sources.yaml** - 외부 소스 정의 (Helm repos, Git repos)
- **values/** - Helm 값 파일 디렉토리

### 차트 커스터마이징 (현재 버전)

- **overrides** - 차트 내 파일 교체
- **removes** - 차트 내 파일 삭제

### 설정 예제 (현재 버전)

**간단한 Helm 배포**:

```yaml
namespace: my-namespace

apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2
    values:
      - redis.yaml
```

**차트 커스터마이징**:

```yaml
apps:
  postgresql:
    type: helm
    chart: bitnami/postgresql
    overrides:
      templates/secret.yaml: my-custom-secret.yaml
    removes:
      - templates/serviceaccount.yaml
```

**의존성 관리**:

```yaml
apps:
  database:
    type: helm
    chart: bitnami/postgresql

  backend:
    type: helm
    chart: ./charts/backend
    depends_on:
      - database
```

더 많은 예제는 [examples/](examples/) 디렉토리를 참조하세요.

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
