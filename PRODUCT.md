______________________________________________________________________

## type: Product Overview audience: End User, Developer, Product Manager topics: [product, vision, users, value-proposition] llm_priority: high entry_point: true last_updated: 2025-01-06

# SBKube - Kubernetes 배포 자동화 CLI 도구

> **무엇을 만들 것인가**: k3s 환경에서 Helm/YAML/Git 배포를 하나의 선언적 설정으로 통합하는 실용적 자동화 도구

______________________________________________________________________

## 📌 목차

1. [제품 개요](#1-%EC%A0%9C%ED%92%88-%EA%B0%9C%EC%9A%94)
1. [왜 만드는가 (문제 정의)](#2-%EC%99%9C-%EB%A7%8C%EB%93%9C%EB%8A%94%EA%B0%80-%EB%AC%B8%EC%A0%9C-%EC%A0%95%EC%9D%98)
1. [누구를 위한가 (대상 사용자)](#3-%EB%88%84%EA%B5%AC%EB%A5%BC-%EC%9C%84%ED%95%9C%EA%B0%80-%EB%8C%80%EC%83%81-%EC%82%AC%EC%9A%A9%EC%9E%90)
1. [무엇을 해결하는가 (가치 제안)](#4-%EB%AC%B4%EC%97%87%EC%9D%84-%ED%95%B4%EA%B2%B0%ED%95%98%EB%8A%94%EA%B0%80-%EA%B0%80%EC%B9%98-%EC%A0%9C%EC%95%88)
1. [어떻게 사용하는가 (사용자 시나리오)](#5-%EC%96%B4%EB%96%BB%EA%B2%8C-%EC%82%AC%EC%9A%A9%ED%95%98%EB%8A%94%EA%B0%80-%EC%82%AC%EC%9A%A9%EC%9E%90-%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4)
1. [주요 기능](#6-%EC%A3%BC%EC%9A%94-%EA%B8%B0%EB%8A%A5)
1. [UI/UX 구상](#7-uiux-%EA%B5%AC%EC%83%81)
1. [경쟁 비교](#8-%EA%B2%BD%EC%9F%81-%EB%B9%84%EA%B5%90)
1. [기술 스택 (요약)](#9-%EA%B8%B0%EC%88%A0-%EC%8A%A4%ED%83%9D-%EC%9A%94%EC%95%BD)
1. [프로젝트 정보](#10-%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8-%EC%A0%95%EB%B3%B4)

______________________________________________________________________

## 1. 제품 개요

### 제품명

**SBKube** - Kubernetes Deployment Automation CLI for k3s

### 한 문장 정의

중소규모 DevOps 팀을 위해 Helm 차트, YAML 매니페스트, Git 리포지토리를 하나의 선언적 설정(YAML)으로 통합하여 4단계
워크플로우(`prepare → build → template → deploy`)로 자동 배포하는 Python CLI 도구

### 핵심 가치

**"하나의 설정 파일로 모든 배포 소스를 통합하고, 4단계로 일관되게 자동화"**

______________________________________________________________________

## 2. 왜 만드는가 (문제 정의)

### 해결하려는 핵심 문제

Kubernetes 환경(특히 k3s)에서 애플리케이션을 배포할 때 직면하는 실무 문제:

#### 2.1 배포 소스의 파편화

- **현상**: Helm 차트, YAML 매니페스트, Git 리포지토리, OCI 레지스트리 등 다양한 소스 분산
- **고충**: 각 소스마다 다른 다운로드/설치 절차와 도구 사용 필요
- **결과**: 배포 스크립트 난립, 팀원 간 절차 불일치, 유지보수 어려움

#### 2.2 수동 작업의 반복

- **현상**: `helm repo add` → `helm pull` → `helm install` → `kubectl apply` 등 수동 명령어 반복
- **고충**: 환경별(dev/staging/prod) 설정 값 수동 변경, 배포 순서 수동 관리
- **결과**: 휴먼 에러 빈발, 배포 시간 지연, 자동화 어려움

#### 2.3 배포 상태 추적의 어려움

- **현상**: 어떤 버전이 어느 환경에 배포되었는지 추적 곤란
- **고충**: 배포 히스토리 부재, 롤백 정보 없음, 실패 시 디버깅 정보 부족
- **결과**: 장애 시 복구 지연, 변경 이력 관리 실패

#### 2.4 일관성 보장의 한계

- **현상**: 개발/스테이징/프로덕션 환경 간 배포 방식 불일치
- **고충**: 설정 파일 검증 부재, 런타임 오류 빈발
- **결과**: 프로덕션 배포 실패, 환경 간 동작 차이 발생

### 대상 환경

- **주요 환경**: k3s (경량 Kubernetes 배포판)
- **보조 환경**: 표준 Kubernetes 클러스터
- **사용 사례**: 웹호스팅, 서버호스팅, DevOps 인프라 자동화

______________________________________________________________________

## 3. 누구를 위한가 (대상 사용자)

### 주요 페르소나

#### 페르소나 1: DevOps 엔지니어 (주요 타겟) ⭐

**프로필**:

- 30대 중반, 경력 5-8년, 중소규모 IT 스타트업
- k3s 클러스터 운영, Helm/kubectl 숙련도 중상

**니즈**:

- Helm 차트와 커스텀 YAML을 함께 배포
- 개발/스테이징/프로덕션 환경 일관성 유지
- 배포 자동화 및 시간 절감 (수동 작업 70% 감소)

**사용 패턴**:

```bash
# 일일 워크플로우
sbkube apply --app-dir config/staging  # 통합 실행
sbkube status --namespace staging      # 상태 확인

# 주간 작업
sbkube history --namespace staging
sbkube validate --app-dir config/production
```

#### 페르소나 2: 백엔드 개발자 (보조 타겟)

**프로필**:

- 20대 후반, 경력 3-5년, 웹 서비스 개발
- Kubernetes 전문 지식 부족, 로컬 k3s로 테스트

**니즈**:

- 로컬 개발 환경에 빠르게 의존성 배포 (Redis, PostgreSQL 등)
- Kubernetes/Helm 명령어 몰라도 배포 가능
- 설정 파일 기반으로 재현 가능

**사용 패턴**:

```bash
# 로컬 개발 환경 셋업
git clone <프로젝트>
sbkube apply --app-dir dev-config --namespace dev-local
```

> **상세 페르소나**: [대상 사용자 분석](docs/00-product/target-users.md) 참조 (SRE, 시스템 관리자 등)

______________________________________________________________________

## 4. 무엇을 해결하는가 (가치 제안)

### 핵심 해결 방안

#### 4.1 통합 배포 워크플로우

```
prepare → build → template → deploy
   ↓        ↓         ↓         ↓
소스준비  커스터마이징 템플릿화  클러스터배포
```

**또는 통합 실행**: `sbkube apply` (4단계 자동 실행)

- **prepare**: 모든 소스(Helm, Git, OCI, HTTP) 다운로드 및 준비
- **build**: 배포 가능한 형태로 변환 및 패키징 (차트 커스터마이징)
- **template**: 환경별 설정 적용 및 매니페스트 렌더링
- **deploy**: Kubernetes 클러스터에 일관된 방식으로 배포

#### 4.2 선언적 설정 기반 관리

**config.yaml**: 모든 애플리케이션 정의 및 배포 스펙 통합

```yaml
namespace: production
deps: ["a000_infra"]  # 앱 그룹 의존성

apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: "18.0.0"
    values: ["values/production.yaml"]
    hooks:  # 배포 전후 자동화
      pre_deploy: ["./backup-db.sh"]
      post_deploy: ["./notify-slack.sh"]
```

**sources.yaml**: Helm 저장소, Git 리포지토리 및 클러스터 설정 중앙 관리

```yaml
kubeconfig: ~/.kube/config
kubeconfig_context: production-cluster

helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
  grafana: https://grafana.github.io/helm-charts
```

**Pydantic 검증**: 런타임 설정 검증 및 명확한 오류 메시지

#### 4.3 강력한 상태 관리

- **SQLAlchemy 기반**: 배포 상태 영구 저장 (`.sbkube/deployments.db`)
- **히스토리 추적**: 시간순 배포 기록 보존 (언제, 누가, 무엇을)
- **롤백 지원**: 이전 상태로 안전한 복원

#### 4.4 사용자 친화적 인터페이스

- **Rich 콘솔**: 색상별 로깅 (INFO/WARNING/ERROR) 및 테이블 형태 출력
- **LLM 친화적 출력**: `--format llm` 옵션으로 토큰 사용량 80-90% 절감
- **진행 상태 표시**: 실시간 작업 진행도 시각화

______________________________________________________________________

## 5. 어떻게 사용하는가 (사용자 시나리오)

### 시나리오 1: 빠른 Helm 차트 배포 (DevOps 엔지니어 Alice)

**목표**: Grafana 차트를 프로덕션에 배포

**흐름**:

```
1. sources.yaml에 Grafana Helm 저장소 추가
2. config.yaml에 helm 타입 앱 정의
3. sbkube apply --namespace production
   → 자동으로 prepare → build → template → deploy 실행
4. sbkube status --namespace production
   → 배포 성공 확인
```

**결과**: 수동 명령어 10회 → 1회로 단축

### 시나리오 2: 환경별 설정 관리 (SRE Carol)

**목표**: 동일한 설정으로 dev/staging/prod 배포

**흐름**:

```
1. 환경별 values 파일 작성
   - values/dev.yaml
   - values/staging.yaml
   - values/prod.yaml
2. config.yaml에서 values 파일 참조
3. 환경별 배포:
   sbkube apply --app-dir config --namespace dev
   sbkube apply --app-dir config --namespace staging
   sbkube apply --app-dir config --namespace production
4. 히스토리 조회:
   sbkube history --namespace production
```

**결과**: 환경 간 일관성 95% 이상 보장

### 시나리오 3: 배포 롤백 (SRE Carol)

**목표**: 프로덕션 배포 실패 시 빠른 복구

**흐름**:

```
1. 문제 발견: 모니터링 알림 수신
2. 히스토리 조회:
   sbkube history --namespace production
3. 이전 배포 ID 확인
4. 롤백 실행:
   sbkube rollback --deployment-id 12345
5. 상태 확인:
   sbkube status --namespace production
```

**결과**: 롤백 시간 30분 → 5분으로 단축

> **더 많은 시나리오**: [튜토리얼](docs/08-tutorials/README.md) 참조

______________________________________________________________________

## 6. 주요 기능

### 6.1 핵심 기능 (v0.6.0 안정 버전)

| 기능 | 설명 | 사용자 가치 | |------|------|------------| | **통합 워크플로우** | `sbkube apply` 한 번에 전체 배포 | 배포 시간 70% 절감 | | **다중 소스
통합** | Helm, YAML, Git, HTTP, Kustomize 지원 | 도구 파편화 해소 | | **설정 검증** | Pydantic 기반 런타임 검증 | 배포 오류 90% 사전 감지 | | **상태
관리** | SQLAlchemy DB 기반 히스토리 추적 | 배포 추적 및 감사 | | **Hooks 시스템** | 배포 전후 자동 스크립트 실행 | 백업/알림 자동화 | | **앱 그룹 의존성** | `deps`
필드로 배포 순서 관리 | 의존성 기반 자동 검증 |

### 6.1.1 개발 중 기능 (v0.7.0)

| 기능 | 설명 | 상태 | |------|------|------| | **LLM 친화적 출력** | `--format llm/json/yaml` 옵션 | 🟡 Phase 1-3 완료 | | **향상된 에러
처리** | 자동 에러 분류 및 수정 제안 | 🟡 개발 중 |

### 6.2 Phase별 기능 계획

**Phase 1 (v0.7.x - v0.8.x)**: Hooks 고도화

- Manifests Hooks: YAML 자동 배포
- Task 시스템: Inline YAML, 타입 시스템

**Phase 2 (v0.9.x - v1.0.x)**: 엔터프라이즈 기능

- 멀티 클러스터 지원
- 웹 UI 대시보드
- GitOps 통합 (Flux, ArgoCD)

> **상세 기능**: [기능 명세서](docs/00-product/product-spec.md) 참조

______________________________________________________________________

## 7. UI/UX 구상

### 7.1 CLI 인터페이스 (현재)

**명령어 구조**:

```bash
sbkube [전역옵션] <명령어> [명령어옵션]

전역 옵션:
  --kubeconfig <경로>     # Kubernetes 설정 파일
  --context <이름>        # Kubernetes 컨텍스트
  --namespace <이름>      # 기본 네임스페이스
  --format <형식>         # 출력 형식 (human/llm/json/yaml)
  -v, --verbose          # 상세 로깅
```

**주요 명령어**:

- `apply`: 통합 워크플로우 실행 (prepare → build → template → deploy)
- `prepare`: 소스 준비
- `build`: 앱 빌드
- `template`: 템플릿 렌더링
- `deploy`: 배포 실행
- `status`: 배포 상태 조회
- `history`: 배포 히스토리 조회
- `rollback`: 이전 배포로 복원
- `validate`: 설정 파일 검증

### 7.2 Rich 콘솔 출력

**로그 레벨별 색상**:

```
🔵 INFO: 일반 정보 (파란색)
🟡 WARNING: 경고 (노란색)
🔴 ERROR: 오류 (빨간색)
🟢 SUCCESS: 성공 (초록색)
🟣 DEBUG: 디버깅 정보 (보라색, --verbose 시)
```

**진행 상태 표시**:

```
[apply] Processing apps... ━━━━━━━━━━━━━━━━━━━━━━ 3/5 (60%)
  ✅ redis-deploy
  ✅ postgres-deploy
  ⏳ nginx-deploy (deploying...)
```

### 7.3 웹 UI (향후 계획)

- 배포 상태 대시보드
- 히스토리 타임라인
- 설정 파일 편집기 (YAML 검증 통합)
- 실시간 로그 스트리밍

______________________________________________________________________

## 8. 경쟁 비교

### 8.1 기존 솔루션 대비 차별점

| 기능/특징 | SBKube | Helm만 사용 | kubectl만 사용 | Helmfile | |----------|---------|------------|---------------|----------| |
**통합 워크플로우** | ✅ prepare-build-template-deploy | ❌ 수동 단계 필요 | ❌ 수동 단계 필요 | ⚠️ 부분 지원 | | **다중 소스 통합** | ✅
Helm+YAML+Git+HTTP | ❌ Helm만 | ❌ YAML만 | ⚠️ Helm 중심 | | **상태 관리** | ✅ SQLAlchemy DB | ⚠️ Helm secrets | ❌ 없음 | ⚠️ Helm
의존 | | **설정 검증** | ✅ Pydantic | ❌ 없음 | ❌ 없음 | ⚠️ 기본 검증 | | **Hooks 시스템** | ✅ 앱별/명령별 | ❌ 없음 | ✅ 가능 | ⚠️ 제한적 | | **k3s
최적화** | ✅ 최적화됨 | ⚠️ 일반 K8s | ⚠️ 일반 K8s | ⚠️ 일반 K8s | | **학습 곡선** | 🟢 낮음 (선언적 설정) | 🟡 중간 | 🟡 중간 | 🔴 높음 | | **LLM 통합** | ✅
네이티브 지원 | ❌ 없음 | ❌없음 | ❌ 없음 |

### 8.2 포지셔닝

**SBKube는 중소규모 DevOps 팀을 위한 실용적이고 통합된 Kubernetes 배포 자동화 도구**

- **Helm/kubectl 대체가 아닌 보완**: 기존 도구를 활용하면서 워크플로우 자동화
- **Helmfile보다 단순**: 복잡한 환경 관리보다 명확한 4단계 워크플로우 중심
- **k3s 환경 특화**: 경량 클러스터 환경에서의 실용성 강조
- **실무 기반 개발**: ScriptonBasestar의 실제 웹호스팅 인프라에서 검증

______________________________________________________________________

## 9. 기술 스택 (요약)

> ⚠️ **주의**: 이 섹션은 간단한 기술 개요만 제공합니다. 상세 기술 사양은 [SPEC.md](SPEC.md)를 참조하세요.

### 9.1 핵심 기술

- **언어**: Python 3.12+
- **CLI 프레임워크**: Click 8.1+
- **데이터 검증**: Pydantic 2.7+
- **상태 관리**: SQLAlchemy 2.0+
- **콘솔 UI**: Rich

### 9.2 외부 의존성

- **Helm**: v3.x (차트 관리)
- **kubectl**: Kubernetes API 통신
- **Git**: Git 리포지토리 클론

> **상세 아키텍처**: [기술 명세서](SPEC.md) 참조

______________________________________________________________________

## 10. 프로젝트 정보

### 버전 및 저장소

- **현재 버전**: v0.7.0 (개발 중)
- **안정 버전**: v0.6.0
- **라이선스**: MIT
- **저장소**: [github.com/ScriptonBasestar/sb-kube-app-manager](https://github.com/ScriptonBasestar/sb-kube-app-manager)
- **PyPI**: [pypi.org/project/sbkube](https://pypi.org/project/sbkube/)

### 개발자 정보

- **개발자**: ScriptonBasestar (archmagece@users.noreply.github.com)
- **용도**: 웹호스팅/서버호스팅 기반 DevOps 인프라 실무 활용

### 비전과 로드맵

**장기 비전**: "DevOps 생태계를 위한 통합 배포 플랫폼"

- sbkube, sbproxy, sbrelease 등 도구 간 연동
- 오픈소스 커뮤니티 확대
- 클라우드 네이티브 에코시스템 통합

> **상세 로드맵**: [비전과 로드맵](docs/00-product/vision-roadmap.md) 참조

### 변경 이력

- **v0.7.0** (Unreleased): LLM 친화적 출력 시스템 (Phase 1-3 완료), 향상된 에러 처리
- **v0.6.0** (2024-10-30): 앱 그룹 의존성 검증, 네임스페이스 자동 감지, 라벨 기반 분류
- **v0.5.0** (2024-08-01): 통합 워크플로우 (`apply` 명령어), Hooks 시스템 기초

> **전체 변경 이력**: [CHANGELOG.md](CHANGELOG.md) 참조

______________________________________________________________________

## 📚 상세 문서 링크

### 제품 정의 (최우선)

- **[제품 정의서](docs/00-product/product-definition.md)** - 완전한 제품 정의와 문제 해결 방안
- **[기능 명세서](docs/00-product/product-spec.md)** - 전체 기능 목록 및 사용자 시나리오
- **[비전과 로드맵](docs/00-product/vision-roadmap.md)** - 장기 비전 및 개발 계획
- **[대상 사용자](docs/00-product/target-users.md)** - 사용자 페르소나 및 사용 패턴

### 사용자 가이드

- **[빠른 시작](docs/01-getting-started/README.md)** - 설치 및 기본 사용법
- **[명령어 참조](docs/02-features/commands.md)** - 전체 명령어 상세 가이드
- **[설정 가이드](docs/03-configuration/README.md)** - config.yaml, sources.yaml 작성법
- **[튜토리얼](docs/08-tutorials/README.md)** - 실전 사용 예제

### 기술 문서

- **[SPEC.md](SPEC.md)** - 기술 명세서 (아키텍처, API, 구현 상세)
- **[아키텍처](docs/10-modules/sbkube/ARCHITECTURE.md)** - 시스템 설계 및 모듈 구조
- **[개발자 가이드](docs/04-development/README.md)** - 개발 환경 구성 및 기여 방법

______________________________________________________________________

**🎯 문서 유형**: 제품 문서 (Product Document) **독자**: 기획자, 디자이너, 경영진, 일반 사용자 **초점**: 제품의 의도와 사용자 가치

**💡 기술 구현 상세는 [SPEC.md](SPEC.md)를 참조하세요**
