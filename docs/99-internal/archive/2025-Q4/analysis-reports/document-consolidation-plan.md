# 문서 중복 제거 및 통합 계획

**작성일**: 2025-10-23 **대상**: SBKube 프로젝트 문서

---

## 📋 중복 분석 결과

### 1. 아키텍처 문서 중복

| 문서 경로 | 단어 수 | 줄 수 | 대상 독자 | 주요 목적 | |----------|---------|-------|----------|----------| |
`docs/02-features/architecture.md` | 1,037 | 357 | 사용자/운영자 | 시스템 이해 및 사용 가이드 | |
`docs/10-modules/sbkube/ARCHITECTURE.md` | 1,726 | 571 | 개발자 | 설계 상세 및 확장 가이드 |

#### 중복 콘텐츠 항목

1. **BaseCommand 패턴** (27회 언급)

   - `docs/02-features/architecture.md`: 섹션 1 (간단한 예제)
   - `docs/10-modules/sbkube/ARCHITECTURE.md`: 섹션 2.2 (상세 설명)

1. **Pydantic 모델 시스템**

   - `docs/02-features/architecture.md`: 섹션 2 (기본 예제)
   - `docs/10-modules/sbkube/ARCHITECTURE.md`: 섹션 3.3 (완전한 스키마)

1. **Rich Console 시스템**

   - `docs/02-features/architecture.md`: 섹션 3 (사용 예제)
   - `docs/10-modules/sbkube/ARCHITECTURE.md`: 포함 안 됨 (추가 필요)

1. **상태 관리 시스템**

   - `docs/02-features/architecture.md`: 섹션 4 (기본 소개)
   - `docs/10-modules/sbkube/ARCHITECTURE.md`: 섹션 4 (완전한 설계)

1. **명령어 실행 플로우**

   - `docs/02-features/architecture.md`: 섹션 5 (사용자 관점)
   - `docs/10-modules/sbkube/ARCHITECTURE.md`: 데이터 흐름 섹션 (개발자 관점)

#### 조치 사항

**✅ 이미 완료**:

- 양 문서 상단에 크로스 레퍼런스 추가 완료

**권장 추가 조치**:

1. **명확한 역할 분담**

   - 사용자 문서: "어떻게 동작하는가?" 중심
   - 개발자 문서: "왜 이렇게 설계했는가?" 중심

1. **중복 최소화 전략**

   - 기본 개념은 사용자 문서에만
   - 상세 구현은 개발자 문서에서 링크로 참조
   - 예시:
     ```markdown
     <!-- docs/02-features/architecture.md -->
     ## BaseCommand 패턴

     모든 명령어는 `BaseCommand`를 상속합니다.
     자세한 설계는 [개발자 가이드](../10-modules/sbkube/ARCHITECTURE.md#basecommand-패턴)를 참조하세요.
     ```

---

## 📁 문서 구조 개선 제안

### 현재 구조

```
docs/
├── 00-product/           # 제품 정의 (중복 없음, 양호)
├── 01-getting-started/   # 시작 가이드
├── 02-features/          # 기능 설명
│   ├── architecture.md   # 아키텍처 (사용자용)
│   ├── commands.md
│   └── ...
├── 03-configuration/     # 설정 가이드
├── 04-development/       # 개발자 가이드 (일반)
├── 10-modules/sbkube/    # 모듈 상세 (개발자용)
│   ├── ARCHITECTURE.md   # 아키텍처 (개발자용)
│   └── ...
└── ...
```

### 권장 구조 (변경 불필요, 현재 적절)

현재 구조는 Product-First 원칙을 잘 따르고 있습니다:

- Level 0-1: 제품 정의 (`00-product/`)
- Level 2: 기능 가이드 (`02-features/`)
- Level 3: 모듈 상세 (`10-modules/`)

---

## 🔍 기타 중복 가능성 분석

### 1. 명령어 문서

- `docs/02-features/commands.md`: 모든 명령어 요약
- 개별 명령어 문서: 없음 (현재 단일 파일에 통합)

**평가**: ✅ 적절 (명령어 수가 적어 분리 불필요)

### 2. 설정 문서

- `docs/03-configuration/config-schema.md`: 전체 스키마
- `docs/03-configuration/helm-chart-types.md`: Helm 차트 타입
- `docs/03-configuration/chart-customization.md`: 차트 커스터마이징

**평가**: ✅ 적절 (주제별 분리, 중복 없음)

### 3. 개발자 가이드

- `docs/04-development/README.md`: 개발 환경 설정
- `docs/04-development/testing.md`: 테스트 가이드
- `docs/10-modules/sbkube/ARCHITECTURE.md`: 아키텍처 설계

**평가**: ✅ 적절 (역할 분담 명확)

---

## 📊 BaseCommand 언급 위치 분석

전체 27개 언급 중:

| 위치 | 횟수 | 용도 | |------|------|------| | `docs/02-features/architecture.md` | 8 | 개념 소개 및 기본 예제 | |
`docs/10-modules/sbkube/ARCHITECTURE.md` | 12 | 상세 설계 및 확장 가이드 | | `CLAUDE.md` | 5 | AI 컨텍스트 (적절) | | 기타 문서 | 2 | 참조
(적절) |

**평가**: ✅ 적절 (각 문서의 목적에 맞게 사용)

---

## ✅ 완료된 개선 사항

### 1. 빈 디렉토리 처리 (2025-10-23)

- ✅ `docs/10-modules/sbkube/docs/10-architecture/README.md` 생성
- ✅ `docs/10-modules/sbkube/docs/20-implementation/README.md` 생성
- ✅ `docs/10-modules/sbkube/docs/30-integration/README.md` 생성

### 2. 크로스 레퍼런스 추가 (2025-10-23)

- ✅ `docs/02-features/architecture.md` 상단에 개발자 문서 링크 추가
- ✅ `docs/10-modules/sbkube/ARCHITECTURE.md`에 이미 사용자 문서 링크 존재

---

## 🎯 향후 추가 개선 제안

### Phase 1: 콘텐츠 재구성 (선택적)

**우선순위**: 낮음 (현재 구조도 충분히 양호)

1. **사용자 아키텍처 문서 간소화**

   - 현재 357줄 → 200줄 목표
   - 상세 내용은 개발자 문서로 링크

1. **개발자 문서 확장**

   - Rich Console 시스템 상세 설명 추가
   - 성능 최적화 섹션 확대

### Phase 2: 검색성 개선 (선택적)

**우선순위**: 낮음

1. **태그 시스템 도입**

   ```markdown
   ---
   tags: [architecture, design, user-guide]
   audience: users
   related: [ARCHITECTURE.md, commands.md]
   ---
   ```

1. **문서 인덱스 자동화**

   - `docs/INDEX.md` 자동 생성 스크립트
   - 태그 기반 문서 탐색

---

## 📈 현재 상태 평가

| 항목 | 평가 | 점수 | |------|------|------| | 문서 구조 | ✅ 우수 | 9/10 | | 중복 제거 | ✅ 양호 | 8/10 | | 크로스 레퍼런스 | ✅ 양호 | 8/10 | | 빈
디렉토리 처리 | ✅ 완료 | 10/10 | | AI 친화성 | ✅ 우수 | 9/10 |

**종합 평가**: ✅ 우수 (8.8/10)

---

## 🔚 결론

### 핵심 요약

1. **중복은 최소한으로 관리됨**:

   - 사용자 vs 개발자 문서 역할 분담 명확
   - 각 문서의 목적에 맞는 상세도 유지

1. **개선 사항 완료**:

   - 빈 디렉토리에 README.md 추가
   - 크로스 레퍼런스 강화

1. **추가 개선 불필요**:

   - 현재 구조가 Product-First 원칙 준수
   - 과도한 재구성은 오히려 혼란 유발 가능

### 권장 사항

- ✅ **현재 상태 유지**: 문서 구조 양호
- ⚠️ **선택적 개선**: BaseCommand 설명 통합 (필요 시)
- 📝 **지속적 관리**: 새 기능 추가 시 적절한 문서 위치 선택

---

**작성자**: Claude (claude-sonnet-4-5) **승인 상태**: 검토 필요
