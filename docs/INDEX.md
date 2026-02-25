---
type: Index
audience: All
topics: [documentation, index, navigation]
llm_priority: critical
last_updated: 2026-02-25
---

# 📚 SBKube Documentation Index

> SBKube v0.11.0 문서 탐색 허브입니다.

## Quick Navigation

| 목적 | 문서 |
|------|------|
| **프로젝트 개요** | [PRODUCT.md](../PRODUCT.md) |
| **아키텍처** | [ARCHITECTURE.md](../ARCHITECTURE.md) |
| **기술 스택** | [TECH_STACK.md](../TECH_STACK.md) |
| **설정 스키마** | [03-configuration/config-schema.md](03-configuration/config-schema.md) |
| **명령어 참조** | [02-features/commands.md](02-features/commands.md) |
| **앱 타입** | [02-features/application-types.md](02-features/application-types.md) |
| **Hooks** | [02-features/hooks-guide.md](02-features/hooks-guide.md) |
| **마이그레이션** | [03-configuration/migration-guide.md](03-configuration/migration-guide.md) |
| **문제 해결** | [07-troubleshooting/README.md](07-troubleshooting/README.md) |
| **개발 가이드** | [04-development/README.md](04-development/README.md) |
| **AI 작업 가이드** | [CLAUDE.md](../CLAUDE.md) |

---

## 문서 구조

```
docs/
├── INDEX.md                          ← 현재 문서
│
├── 00-product/                       # 제품 정의
│   ├── product-spec.md               # 제품 사양
│   ├── target-users.md               # 대상 사용자
│   └── vision-roadmap.md             # 비전/로드맵
│
├── 01-getting-started/               # 시작하기
│   └── README.md
│
├── 02-features/                      # 기능 참조
│   ├── README.md
│   ├── commands.md                   # CLI 명령어 참조
│   ├── application-types.md          # 9가지 앱 타입
│   ├── hooks-guide.md                # Hooks 통합 가이드
│   └── llm-friendly-output.md        # LLM 출력 형식
│
├── 03-configuration/                 # 설정
│   ├── config-schema.md              # sbkube.yaml 스키마 (Primary)
│   └── migration-guide.md            # 버전별 마이그레이션
│
├── 04-development/                   # 개발
│   ├── README.md
│   ├── coding-standards.md
│   ├── quick-commands.md
│   └── testing.md
│
├── 05-best-practices/                # 모범 사례
│   ├── directory-structure.md
│   └── storage-management.md
│
├── 06-deployment/                    # 배포
│   └── deployment-guide.md
│
├── 07-troubleshooting/               # 문제 해결
│   ├── README.md                     # Quick reference
│   ├── error-reference.md            # 에러 전체 목록
│   ├── common-dev-issues.md          # 개발 환경 이슈
│   ├── deployment-failures.md        # 배포 실패
│   ├── chart-collision-issues.md     # 차트 충돌
│   ├── storage-issues.md             # 스토리지 이슈
│   └── faq.md
│
├── 08-tutorials/                     # 튜토리얼
│   ├── README.md                     # 학습 경로
│   ├── 02-multi-app-deployment.md
│   ├── 03-production-deployment.md
│   ├── 04-customization.md
│   ├── 05-version-migration.md
│   └── 06-using-llm-output.md
│
├── 10-modules/sbkube/                # 모듈 기술 문서
│   ├── ARCHITECTURE.md               # 내부 아키텍처
│   ├── MODULE.md                     # 모듈 개요
│   └── API_CONTRACT.md               # API 계약
│
└── 99-internal/                      # 내부 문서
    ├── documentation-guidelines.md
    └── archive/                      # 아카이브
        ├── hooks-improvement-phase1-3.md
        ├── unified-config-design-v0.10.md
        └── registry-design-future.md
```

---

## Core Concepts

### SBKube란?

k3s 기반 Kubernetes 클러스터에 애플리케이션을 선언적으로 배포하는 CLI 도구입니다.

### Core Workflow

```
sbkube apply -f sbkube.yaml
  └─ prepare → build → template → deploy
```

### Config Format

단일 `sbkube.yaml` 파일로 모든 설정을 관리합니다:

```yaml
apiVersion: sbkube/v1
metadata:
  name: my-cluster
settings:
  kubeconfig: ~/.kube/config
  namespace: production
  helm_repos:
    grafana: https://grafana.github.io/helm-charts
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    version: "10.1.2"
phases:
  p1-infra:
    source: p1-infra/sbkube.yaml
```

### 9 App Types

`helm` · `yaml` · `git` · `http` · `action` · `exec` · `kustomize` · `noop` · `hook`

### Installation

```bash
uv tool install sbkube
sbkube version
```

---

## LLM Priority Guide

AI/LLM이 참조할 때 우선순위:

1. **Critical**: 이 INDEX.md, config-schema.md, commands.md
2. **High**: application-types.md, ARCHITECTURE.md
3. **Medium**: hooks-guide.md, migration-guide.md
4. **Low**: tutorials, troubleshooting (필요 시 참조)

---

**Document Version**: 3.0
**Last Updated**: 2026-02-25
**SBKube Version**: 0.11.0
