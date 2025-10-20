# SBKube AI 컨텍스트 네비게이션 맵

## 개요
이 문서는 AI 에이전트가 SBKube 프로젝트를 효율적으로 이해하고 작업할 수 있도록 컨텍스트 우선순위와 라우팅 규칙을 제공합니다.

## 컨텍스트 계층 구조

```
Level 0 (최우선): 제품 개요
  └─ PRODUCT.md (진입점)

Level 1 (제품 정의): 상세 제품 문서
  ├─ docs/00-product/product-definition.md
  ├─ docs/00-product/product-spec.md
  ├─ docs/00-product/vision-roadmap.md
  └─ docs/00-product/target-users.md

Level 2 (모듈 아키텍처): 구현 설계
  ├─ docs/10-modules/sbkube/MODULE.md
  ├─ docs/10-modules/sbkube/ARCHITECTURE.md
  └─ docs/10-modules/sbkube/API_CONTRACT.md

Level 3 (기능 문서): 사용자 가이드
  ├─ docs/02-features/commands.md
  ├─ docs/02-features/application-types.md
  └─ docs/03-configuration/config-schema.md

Level 4 (구현 코드): 소스 파일
  ├─ sbkube/commands/
  ├─ sbkube/models/
  └─ sbkube/utils/
```

## 질의 유형별 라우팅

### 1. 제품 관련 질의

**질의 패턴**:
- "SBKube가 뭔가요?"
- "이 프로젝트의 목적은?"
- "어떤 문제를 해결하나요?"
- "주요 기능은?"

**라우팅 경로**:
```
Primary: PRODUCT.md
Secondary: docs/00-product/product-definition.md
Fallback: docs/00-product/product-spec.md
```

**컨텍스트 로딩 순서**:
1. [PRODUCT.md](PRODUCT.md) (간결한 개요)
2. [docs/00-product/product-definition.md](docs/00-product/product-definition.md) (문제 정의, 솔루션)
3. [docs/00-product/target-users.md](docs/00-product/target-users.md) (사용자 페르소나)

### 2. 아키텍처 관련 질의

**질의 패턴**:
- "시스템 아키텍처는?"
- "모듈 구조는 어떻게 되나요?"
- "데이터 흐름은?"
- "설계 패턴은?"

**라우팅 경로**:
```
Primary: docs/10-modules/sbkube/ARCHITECTURE.md
Secondary: docs/02-features/architecture.md
Fallback: PRODUCT.md (Architecture 섹션)
```

**컨텍스트 로딩 순서**:
1. [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md) (전체 구조)
2. [docs/02-features/architecture.md](docs/02-features/architecture.md) (기능별 아키텍처)
3. 소스 코드 (sbkube/cli.py, sbkube/commands/)

### 3. 기능 및 사용법 질의

**질의 패턴**:
- "prepare 명령어는 어떻게 사용하나요?"
- "Helm 차트 배포 방법은?"
- "config.yaml 작성법은?"
- "어떤 앱 타입이 지원되나요?"

**라우팅 경로**:
```
Primary: docs/00-product/product-spec.md
Secondary: docs/02-features/commands.md
Fallback: docs/01-getting-started/README.md
```

**컨텍스트 로딩 순서**:
1. [docs/00-product/product-spec.md](docs/00-product/product-spec.md) (기능 명세)
2. [docs/02-features/commands.md](docs/02-features/commands.md) (명령어 상세)
3. [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md) (설정 예제)
4. [examples/](examples/) (실제 사용 예제)

### 4. 구현 및 개발 질의

**질의 패턴**:
- "새 명령어를 어떻게 추가하나요?"
- "Pydantic 모델은 어디 있나요?"
- "BaseCommand 패턴은?"
- "테스트는 어떻게 작성하나요?"

**라우팅 경로**:
```
Primary: docs/10-modules/sbkube/docs/20-implementation/
Secondary: docs/04-development/README.md
Fallback: 소스 코드 (sbkube/)
```

**컨텍스트 로딩 순서**:
1. [AGENTS.md](AGENTS.md) (개발 환경 및 규약)
2. [docs/04-development/README.md](docs/04-development/README.md) (개발자 가이드)
3. [docs/10-modules/sbkube/MODULE.md](docs/10-modules/sbkube/MODULE.md) (모듈 구조)
4. 소스 코드 (관련 모듈)

### 5. 문제 해결 질의

**질의 패턴**:
- "{오류 메시지}"
- "배포가 실패했어요"
- "Helm 릴리스가 생성되지 않아요"
- "설정 검증 오류가 나요"

**라우팅 경로**:
```
Primary: docs/07-troubleshooting/README.md
Secondary: docs/10-modules/sbkube/docs/40-maintenance/troubleshooting.md
Fallback: GitHub Issues
```

**컨텍스트 로딩 순서**:
1. [docs/07-troubleshooting/README.md](docs/07-troubleshooting/README.md) (일반 문제)
2. 오류 메시지 기반 검색 (코드베이스)
3. 관련 명령어 구현 (sbkube/commands/)
4. 검증 로직 (sbkube/validators/)

## 컨텍스트 우선순위 규칙

### Rule 1: 제품 우선 (Product-First)
모든 질의는 제품 컨텍스트부터 시작합니다.
```
질의 → PRODUCT.md → docs/00-product/ → 구체적 문서
```

### Rule 2: 모듈 경계 준수
모듈별 질의는 해당 모듈 문서를 우선 참조합니다.
```
SBKube 구현 질의 → docs/10-modules/sbkube/ → sbkube/ 소스
```

### Rule 3: 의미 단위 청킹
긴 문서는 섹션 단위로 로딩합니다.
```
product-spec.md → 섹션별 4000 토큰 이하로 분할
```

### Rule 4: 크로스 레퍼런스 활용
관련 문서는 자동으로 연결합니다.
```
product-definition.md → product-spec.md (기능 상세)
ARCHITECTURE.md → commands/ (구현 코드)
```

## 의미 기반 인덱스

### 핵심 개념 → 문서 매핑

#### 제품 비전
**키워드**: 제품, 비전, 목표, 가치, 문제 해결
**문서**:
- [docs/00-product/product-definition.md](docs/00-product/product-definition.md)
- [docs/00-product/vision-roadmap.md](docs/00-product/vision-roadmap.md)

#### 워크플로우
**키워드**: prepare, build, template, deploy, 워크플로우, 배포
**문서**:
- [docs/00-product/product-spec.md](docs/00-product/product-spec.md) (섹션 1)
- [docs/02-features/commands.md](docs/02-features/commands.md)
- [SPEC.md](SPEC.md) (섹션 4)

#### 설정 관리
**키워드**: config.yaml, sources.yaml, Pydantic, 검증
**문서**:
- [docs/03-configuration/config-schema.md](docs/03-configuration/config-schema.md)
- [docs/00-product/product-spec.md](docs/00-product/product-spec.md) (섹션 3)
- [sbkube/models/config_model.py](sbkube/models/config_model.py)

#### 상태 관리
**키워드**: history, rollback, SQLAlchemy, 배포 상태
**문서**:
- [docs/00-product/product-spec.md](docs/00-product/product-spec.md) (섹션 4)
- [sbkube/state/](sbkube/state/)

#### 앱 타입
**키워드**: pull-helm, install-yaml, copy-app, exec
**문서**:
- [docs/02-features/application-types.md](docs/02-features/application-types.md)
- [docs/00-product/product-spec.md](docs/00-product/product-spec.md) (섹션 2)

## 컨텍스트 로딩 전략

### 시나리오 1: 첫 질의 (Cold Start)
```
1. PRODUCT.md 로딩 (간결한 개요)
2. 질의 분류 (제품/아키텍처/기능/구현)
3. 관련 Level 1 문서 로딩
4. 필요 시 Level 2-3 문서 추가
```

### 시나리오 2: 후속 질의 (Warm Context)
```
1. 이전 컨텍스트 유지
2. 새 질의 관련 섹션만 추가
3. 토큰 제한 시 오래된 컨텍스트 압축
```

### 시나리오 3: 구현 작업 (Implementation)
```
1. AGENTS.md 로딩 (개발 규약)
2. 관련 모듈 ARCHITECTURE.md 로딩
3. 소스 코드 직접 참조
4. 테스트 코드 확인
```

## 토큰 효율성 가이드

### 최소 컨텍스트 (< 10K 토큰)
**간단한 질의**: "SBKube가 뭔가요?"
```
- PRODUCT.md (전체)
- docs/00-product/product-definition.md (개요 섹션)
```

### 중간 컨텍스트 (10K-50K 토큰)
**기능 질의**: "Helm 차트 배포 방법은?"
```
- PRODUCT.md
- docs/00-product/product-spec.md (섹션 1.1, 1.4, 2.1)
- docs/02-features/commands.md (prepare, deploy 섹션)
- examples/basic/config.yaml
```

### 대규모 컨텍스트 (50K-100K 토큰)
**구현 작업**: "새 명령어 추가"
```
- AGENTS.md
- docs/10-modules/sbkube/ARCHITECTURE.md
- sbkube/cli.py
- sbkube/commands/ (전체 또는 샘플)
- sbkube/utils/base_command.py
- tests/commands/ (샘플)
```

## 문서 간 관계 그래프

```
PRODUCT.md
  ├─ docs/00-product/product-definition.md
  │   ├─ docs/00-product/product-spec.md
  │   └─ docs/00-product/target-users.md
  ├─ docs/00-product/vision-roadmap.md
  └─ AGENTS.md
      ├─ docs/04-development/README.md
      └─ docs/10-modules/sbkube/MODULE.md
          ├─ docs/10-modules/sbkube/ARCHITECTURE.md
          └─ docs/10-modules/sbkube/docs/20-implementation/

docs/00-product/product-spec.md
  ├─ docs/02-features/commands.md
  ├─ docs/02-features/application-types.md
  └─ docs/03-configuration/config-schema.md

docs/10-modules/sbkube/ARCHITECTURE.md
  ├─ sbkube/cli.py
  ├─ sbkube/commands/
  ├─ sbkube/models/
  └─ sbkube/utils/
```

## AI 에이전트 질의 예제

### 예제 1: 제품 이해
**질의**: "SBKube의 핵심 가치는 무엇인가요?"
**로딩 순서**:
1. PRODUCT.md (Value 섹션)
2. docs/00-product/product-definition.md (핵심 가치 제안)
**예상 응답 토큰**: 2,000

### 예제 2: 기능 사용
**질의**: "Helm 차트를 배포하려면 어떻게 하나요?"
**로딩 순서**:
1. docs/00-product/product-spec.md (섹션 1.1, 1.4, 2.1)
2. docs/02-features/commands.md (prepare, deploy)
3. docs/03-configuration/config-schema.md (Helm 예제)
4. examples/basic/config.yaml
**예상 응답 토큰**: 8,000

### 예제 3: 구현
**질의**: "새 검증 로직을 추가하려면?"
**로딩 순서**:
1. AGENTS.md (개발 규약)
2. docs/10-modules/sbkube/ARCHITECTURE.md (검증 시스템)
3. sbkube/validators/ (기존 검증 로직)
4. docs/00-product/product-spec.md (섹션 5 - 검증 요구사항)
**예상 응답 토큰**: 15,000

### 예제 4: 문제 해결
**질의**: "ValidationError: field required 오류가 발생해요"
**로딩 순서**:
1. docs/07-troubleshooting/README.md (Pydantic 오류)
2. sbkube/models/config_model.py (모델 정의)
3. docs/03-configuration/config-schema.md (올바른 설정 예제)
**예상 응답 토큰**: 5,000

## 동적 컨텍스트 관리

### 컨텍스트 캐싱
자주 참조되는 문서는 세션 내에서 캐시:
- PRODUCT.md (항상 캐시)
- AGENTS.md (개발 작업 시 캐시)
- docs/00-product/product-spec.md (기능 질의 시 캐시)

### 컨텍스트 압축
토큰 제한 도달 시:
1. 가장 오래된 컨텍스트 요약
2. 현재 질의와 관련 없는 섹션 제거
3. 코드 블록 → 함수 시그니처만 유지

### 컨텍스트 확장
더 많은 정보 필요 시:
1. 현재 문서의 관련 섹션 추가
2. 크로스 레퍼런스 문서 로딩
3. 소스 코드 직접 참조

---

**문서 버전**: 1.0
**마지막 업데이트**: 2025-10-20
**관련 메타데이터**: [.ai/context.yaml](.ai/context.yaml), [.ai/semantic_index.yaml](.ai/semantic_index.yaml)
