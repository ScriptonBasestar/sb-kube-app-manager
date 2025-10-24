# SBKube - Kubernetes 배포 자동화 도구

## What (무엇을)

**SBKube**는 Kubernetes(k3s) 환경에서 Helm 차트, YAML 매니페스트, Git 리포지토리를 통합하여 일관되고 자동화된 배포 워크플로우를 제공하는 Python 기반 CLI 도구입니다.

## Value (핵심 가치)

다양한 배포 소스(Helm, YAML, Git, HTTP)를 하나의 선언적 설정으로 통합하여, 수동 작업을 최소화하고 배포 일관성과 안정성을 보장합니다.

### 주요 기능

- **간소화된 설정**: Apps는 dict 구조, `specs` 필드 제거
- **통합된 타입**: 단일 `helm` 타입으로 원격/로컬 차트 지원
- **차트 커스터마이징**: `overrides` 및 `removes`로 차트 파일 수정
- **통합 워크플로우**: `sbkube apply` 명령어로 전체 워크플로우 자동 실행

## Architecture (아키텍처 개요)

### 고수준 구조

```
┌─────────────────────────────────────────────────────────┐
│                    SBKube CLI                           │
│  (Click Framework + Rich Console)                       │
└────────────┬────────────────────────────────────────────┘
             │
             ├─► Commands Layer (prepare/build/template/deploy)
             ├─► Models Layer (Pydantic validation)
             ├─► State Management (SQLAlchemy)
             └─► Utils & Validators
                      │
                      ▼
         ┌──────────────────────────┐
         │  External Dependencies   │
         ├──────────────────────────┤
         │ • Helm CLI               │
         │ • kubectl                │
         │ • Git                    │
         │ • Kubernetes API         │
         └──────────────────────────┘
```

### 핵심 워크플로우

```
prepare → build → template → deploy
   │        │         │         │
   ▼        ▼         ▼         ▼
소스준비  커스터마이징 템플릿화  클러스터배포
```

또는 **통합 실행**: `sbkube apply`

### 주요 모듈

- **sbkube**: 단일 Python 패키지로 구성된 모놀리식 CLI 도구
  - **commands/**: 워크플로우 단계별 명령어 구현
  - **models/**: Pydantic 기반 설정 모델 및 검증
  - **state/**: SQLAlchemy 기반 배포 상태 관리
  - **utils/**: Helm, kubectl, Git 연동 유틸리티
  - **validators/**: 사전/사후 배포 검증 시스템

## Quick Links (상세 문서)

### 제품 정의 (최우선)

- [제품 정의서](docs/00-product/product-definition.md) - 완전한 제품 정의와 문제 해결 방안
- [기능 명세서](docs/00-product/product-spec.md) - 전체 기능 목록 및 사용자 시나리오
- [비전과 로드맵](docs/00-product/vision-roadmap.md) - 장기 비전 및 개발 계획
- [대상 사용자](docs/00-product/target-users.md) - 사용자 페르소나 및 사용 패턴

### 모듈 문서

- [SBKube 모듈 문서](docs/10-modules/sbkube/MODULE.md) - 핵심 모듈 아키텍처 및 구현

### 사용자 가이드

- [빠른 시작](docs/01-getting-started/README.md) - 설치 및 기본 사용법
- [명령어 참조](docs/02-features/commands.md) - 전체 명령어 상세 가이드
- [설정 가이드](docs/03-configuration/README.md) - config.yaml, sources.yaml 작성법

### 개발자 리소스

- [개발자 가이드](docs/04-development/README.md) - 개발 환경 구성 및 기여 방법
- [AI 작업 가이드](CLAUDE.md) - AI 에이전트를 위한 통합 작업 가이드

## 기술 스택

- **언어**: Python 3.12+
- **CLI 프레임워크**: Click 8.1+
- **데이터 검증**: Pydantic 2.7+
- **상태 관리**: SQLAlchemy 2.0+
- **콘솔 UI**: Rich
- **외부 도구**: Helm v3.x, kubectl, Git

## 프로젝트 정보

- **버전**: 0.4.1
- **라이선스**: MIT
- **저장소**: [github.com/ScriptonBasestar/kube-app-manaer](https://github.com/ScriptonBasestar/kube-app-manaer)
- **PyPI**: [pypi.org/project/sbkube](https://pypi.org/project/sbkube/)
- **개발자**: ScriptonBasestar
- **용도**: 웹호스팅/서버호스팅 기반 DevOps 인프라 실무 활용

## 변경 이력

- **현재 버전**: 0.4.1
  - [CHANGELOG.md](CHANGELOG.md) - 전체 변경 이력
  - [Migration Guide](docs/MIGRATION.md) - v0.2.x에서 마이그레이션 가이드

______________________________________________________________________

**🎯 AI Context Entry Point**: 이 문서는 AI 에이전트가 SBKube 프로젝트를 이해하기 위한 진입점입니다. 상세 내용은 [docs/00-product/](docs/00-product/)
디렉토리를 참조하세요.
