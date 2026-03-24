---
type: Proposal Document
audience: Developer, Product Manager
topics: [migration, golang, architecture, vision]
llm_priority: medium
last_updated: 2026-03-24
---

# SBKube Go(Golang) 전환 제안서

> **요약**: 이 문서는 현재 Python 기반으로 구현된 `sbkube` CLI 도구를 Cloud Native 생태계의 표준 언어인 Go(Golang)로 전환하기 위한 전략적 장단점, 아키텍처 스케치, 그리고 마이그레이션 로드맵을 다룹니다.

---

## 1. 전환 배경

현재 `sbkube`는 v0.11.0에 이르기까지 Python을 기반으로 성공적인 프로토타이핑과 실무 적용을 이뤄냈습니다. 하지만 프로젝트가 점차 복잡해지고(다단계 Phase 배포, 병렬 실행 등) 대상 사용자가 넓어짐에 따라, **배포의 편의성(UX)과 K8s 네이티브 생태계와의 매끄러운 통합**이 주요 과제로 대두되었습니다.
Docker, Kubernetes, Helm, ArgoCD 등 대부분의 성공적인 인프라 도구들이 채택한 Go 언어로의 전환은 `sbkube`를 엔터프라이즈 레벨의 도구로 도약시키는 핵심 마일스톤이 될 것입니다.

---

## 2. Go 전환 시 얻을 수 있는 주요 장점

### 2.1. 단일 실행 파일(Single Binary) 배포 - 최고의 DevOps UX

- **현재 문제**: Python 런타임 설치, 가상 환경(`uv`/`pip`) 세팅, 패키지 의존성 문제, OS별 파편화가 발생합니다.
- **개선 효과**: Go로 컴파일된 `sbkube`는 종속성이 전혀 없는 단일 바이너리 파일(`sbkube-linux-amd64`)로 제공됩니다. 이는 `kubectl`이나 `helm`처럼 다운로드 후 즉시 실행 가능한 완벽한 사용자 경험을 제공합니다.

### 2.2. Kubernetes / Helm 네이티브 SDK 직접 통합

- **현재 문제**: 내부적으로 `subprocess`를 통해 `helm`, `kubectl` 바이너리를 호출하고, 그 텍스트 출력을 파싱하여 에러를 분류합니다.
- **개선 효과**: Helm Core SDK(`helm.sh/helm/v3/pkg/action`)와 Kubernetes `client-go`를 라이브러리로 직접 임포트하여 사용합니다.
  - `kubectl`이나 `helm` 바이너리가 호스트에 설치되어 있지 않아도 동작합니다.
  - 텍스트 파싱 오류가 제거되고, API 수준의 정교한 에러 핸들링이 가능해집니다.

### 2.3. 병렬 처리 및 성능 극대화

- **현재 문제**: 파이썬의 멀티프로세싱이나 `asyncio`는 메모리 점유율이 높고 GIL(Global Interpreter Lock)의 제약을 받습니다.
- **개선 효과**: 독립된 Workspace 및 Phase를 병렬로 실행할 때, Go의 **고루틴(Goroutine)**과 **채널(Channel)**을 사용하면 압도적으로 적은 리소스로 훨씬 안정적인 동시성 제어가 가능해집니다.

### 2.4. 정적 타입 시스템과 K8s API 호환성

- Kubernetes 리소스들은 이미 Go 구조체(Struct)로 완벽하게 정의되어 있으므로, K8s 리소스를 조작하거나 스키마를 검증할 때 Go 생태계를 활용하는 것이 유지보수에 절대적으로 유리합니다.

---

## 3. 아키텍처 스케치 (Go 기반)

새로운 아키텍처는 외부 프로세스 호출(`subprocess.run`)을 완전히 제거하고 모든 동작을 메모리 내 API 통신으로 처리합니다.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLI Layer (Cobra + Charm/Pterm)                │
│  - 명령어 라우팅, 전역 옵션 파싱, 터미널 UI(Rich 대체), LLM/JSON 포맷팅 │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Workflow Engine (Goroutines & Channels)             │
│  - Workspace / Phase 단위 병렬 실행, 의존성(Kahn's Algorithm) 평가      │
│  - Prepare ➔ Build ➔ Template ─(Dry-Run)─➔ Deploy                       │
└────────────────┬───────────────────┬───────────────────┬────────────────┘
                 │                   │                   │
        ┌────────▼───────┐  ┌────────▼───────┐  ┌────────▼───────┐
        │  Config Model  │  │   App Handlers │  │ State Manager  │
        │(Viper+Validator)│  │  (Helm, Yaml)  │  │ (GORM+SQLite)  │
        └────────┬───────┘  └────────┬───────┘  └────────┬───────┘
                 │                   │                   │
                 └─────────┬─────────┴─────────┬─────────┘
                           ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  🔥 Core SDK Wrappers (Provider Layer)                  │
├───────────────────────────────────┬─────────────────────────────────────┤
│         Helm Core SDK Wrapper     │      Kubernetes Client Wrapper      │
│  (helm.sh/helm/v3/pkg/action)     │           (k8s.io/client-go)        │
│                                   │                                     │
│ - action.Install / action.Upgrade │ - kubernetes.Clientset (Typed)      │
│ - chart.Loader (로컬/원격 차트)   │ - dynamic.Interface (YAML 매니페스트) │
│ - action.Template (렌더링)        │ - Server-Side Apply (SSA) 로직      │
└─────────────────┬─────────────────┴──────────────────┬──────────────────┘
                  │                                    │
                  ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  Cluster Configuration (RESTClientGetter)               │
│               - kubeconfig 로드, Context 설정, 인증 토큰 주입             │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
                      🌐 Kubernetes API Server (k3s)
```

---

## 4. 라이브러리 마이그레이션 매핑 (Python ➡️ Go)

Python의 강력한 라이브러리들을 Go 생태계의 표준 도구들로 대체합니다.

| 분류               | Python (현재) | Go (대안)                                   | 비고                                 |
| ------------------ | ------------- | ------------------------------------------- | ------------------------------------ |
| **CLI 프레임워크** | `Click`       | `spf13/cobra`                               | K8s 표준 CLI 프레임워크              |
| **설정 파싱**      | `PyYAML`      | `spf13/viper`                               | 다양한 포맷 및 환경변수 바인딩       |
| **데이터 검증**    | `Pydantic`    | `go-playground/validator`                   | 구조체 태그(`struct tags`) 기반 검증 |
| **콘솔 UI**        | `Rich`        | `pterm/pterm` 또는 `charmbracelet/lipgloss` | 화려한 색상, 진행률 바, 테이블 출력  |
| **DB / 상태 관리** | `SQLAlchemy`  | `gorm.io/gorm` 또는 `entgo.io/ent`          | SQLite 드라이버 연동 배포 이력 관리  |
| **Git 조작**       | `subprocess`  | `go-git/go-git`                             | 메모리 내 Git Clone/Pull 처리        |

---

## 5. 전환 시 고려사항 (Trade-offs)

1. **초기 개발 리소스 집중**: 기존에 잘 작성된 Pydantic 모델과 검증 로직, 단위 테스트를 Go로 재작성해야 하므로 초기 포팅 기간 동안 신규 기능 추가가 지연될 수 있습니다.
2. **동적 언어의 유연성 상실**: 파이썬의 `**kwargs`나 동적 타입 할당을 통한 설정 오버라이딩을 Go의 정적 타입 시스템(Interface{}, Type Assertion)으로 우아하게 풀어내기 위한 설계 고민이 필요합니다.
3. **Hook 시스템**: 기존의 Shell 스크립트 실행(Subprocess) 기반 Hook 시스템은 Go에서도 `os/exec`를 통해 동일하게 유지 가능합니다.

---

## 6. 마이그레이션 로드맵 (추천 전략)

빅뱅 방식(한 번에 전체 재작성)을 지양하고, 명확한 마일스톤에 따른 점진적 전환을 권장합니다.

### Phase 1: 스펙 문서화 및 준비

- 현재 Python `v0.11.0`을 안정화시키고, 기존 YAML 설정 모델(`sbkube.yaml`)과 API Contract를 Go 버전의 '요구사항 명세서'로 동결합니다.
- Go 프로젝트 리포지토리(`sbkube-go`)를 초기화합니다.

### Phase 2: 핵심 코어 PoC (Proof of Concept)

- Cobra CLI 구조를 잡습니다.
- `client-go`와 `helm.sh/helm`을 연동하여 `subprocess` 없이 클러스터에 접속하고 차트를 설치하는 초소형 모듈을 작성합니다.

### Phase 3: 워크플로우 엔진 구현

- Viper/Validator를 통해 설정을 파싱합니다.
- Goroutine을 활용하여 의존성 없는 App 그룹들의 병렬 처리 로직을 구현합니다.
- 기존 `examples/` 디렉토리의 시나리오들을 Go 버전에 주입하여 E2E 테스트 통과 여부를 점검합니다.

### Phase 4: 부가 기능 및 UI 고도화

- SQLite 연동 및 배포 이력(`history`, `rollback`)을 구현합니다.
- Pterm을 활용하여 Rich 수준의 콘솔 UI와 실시간 진행률(Progress Bar)을 구축합니다.
- LLM 친화적 포맷(`--format llm`)을 위한 JSON/YAML 렌더링을 연동합니다.

---

## 결론

`sbkube`가 "k3s 환경을 위한 실용적인 중소규모 DevOps 배포 플랫폼"이라는 비전을 달성하려면, 설치와 실행이 극도로 단순해야 합니다. **Go 언어로의 전환은 종속성을 없애고 속도와 안정성을 극대화함으로써 프로젝트의 완성도와 생태계 기여도를 한 차원 높여줄 최선의 진화 방향**입니다.
