______________________________________________________________________

## type: Product Documentation audience: Product Manager, Developer topics: [users, personas, use-cases, market] llm_priority: medium last_updated: 2025-01-04

# SBKube 대상 사용자 분석

## 주요 사용자 페르소나

### 페르소나 1: DevOps 엔지니어 (주요 타겟)

**프로필**:

- **이름**: Alice (30대 중반)
- **직함**: DevOps 엔지니어
- **경력**: 5-8년
- **환경**: 중소규모 IT 스타트업, k3s 클러스터 운영

**니즈**:

- Helm 차트와 커스텀 YAML을 함께 배포
- 개발/스테이징/프로덕션 환경 일관성 유지
- 배포 자동화 및 시간 절감
- 배포 히스토리 추적 및 롤백

**고충**:

- Helm, kubectl, git 명령어를 매번 수동 실행
- 환경별 values 파일 관리 복잡
- 배포 실패 시 원인 파악 어려움
- 팀원 간 배포 절차 불일치

**사용 패턴**:

```bash
# 일일 워크플로우
sbkube prepare --app-dir config/staging
sbkube build
sbkube deploy --namespace staging --dry-run
sbkube deploy --namespace staging

# 주간 작업
sbkube history --namespace staging
sbkube validate --app-dir config/production
```

**성공 지표**:

- 배포 시간 70% 단축
- 배포 오류 90% 감소
- 팀 배포 절차 통일

### 페르소나 2: 백엔드 개발자 (보조 타겟)

**프로필**:

- **이름**: Bob (20대 후반)
- **직함**: Backend Developer
- **경력**: 3-5년
- **환경**: 웹 서비스 개발, 로컬 k3s로 테스트

**니즈**:

- 로컬 개발 환경에 빠르게 의존성 배포
- Kubernetes 전문 지식 없이 배포
- Git 리포지토리의 YAML을 쉽게 적용
- 설정 파일 기반으로 재현 가능

**고충**:

- Kubernetes/Helm 명령어 익숙하지 않음
- 매번 설치 문서 참조 필요
- 로컬 환경 설정 복잡
- 팀원 환경과 동기화 어려움

**사용 패턴**:

```bash
# 로컬 개발 환경 셋업
git clone <프로젝트 리포지토리>
sbkube prepare --app-dir dev-config
sbkube deploy --namespace dev-local

# 의존성 업데이트
sbkube upgrade --app database
```

**성공 지표**:

- 로컬 환경 셋업 시간 10분 → 2분
- Kubernetes 학습 곡선 완화
- 팀 환경 일관성 확보

### 페르소나 3: SRE (Site Reliability Engineer)

**프로필**:

- **이름**: Carol (30대 후반)
- **직함**: SRE / Platform Engineer
- **경력**: 8-12년
- **환경**: 대규모 프로덕션 클러스터, 멀티 클러스터 관리

**니즈**:

- 배포 상태 추적 및 감사
- 안전한 롤백 메커니즘
- 배포 전 검증 자동화
- 여러 클러스터에 일관된 배포

**고충**:

- 수동 배포 시 휴먼 에러 위험
- 배포 히스토리 추적 시스템 부재
- 롤백 절차 복잡
- 클러스터 간 설정 불일치

**사용 패턴**:

```bash
# 프로덕션 배포 (주의)
sbkube validate --app-dir config/prod
sbkube deploy --namespace production --dry-run
# 검토 후
sbkube deploy --namespace production

# 배포 모니터링
sbkube history --namespace production
sbkube history --app critical-service

# 문제 발생 시 롤백
sbkube rollback --deployment-id 12345
```

**성공 지표**:

- 배포 안정성 99.9% 이상
- 롤백 시간 30분 → 5분
- 배포 감사 로그 완전성

### 페르소나 4: 시스템 관리자 (보조 타겟)

**프로필**:

- **이름**: Dave (40대 초반)
- **직함**: System Administrator
- **경력**: 15+ 년 (전통적 인프라 배경)
- **환경**: 온프레미스 k3s, 웹호스팅 서비스

**니즈**:

- 간단한 CLI 인터페이스
- 명확한 문서 및 예제
- 기존 스크립트 통합
- 안정성 및 예측 가능성

**고충**:

- Kubernetes 생태계 복잡성
- YAML 파일 관리 어려움
- 새로운 도구 학습 부담
- 레거시 시스템과 통합

**사용 패턴**:

```bash
# 정기 배포 (cron 작업)
sbkube prepare --app-dir /etc/sbkube/apps
sbkube build
sbkube deploy --namespace hosting

# 상태 확인
sbkube history
```

**성공 지표**:

- 배포 절차 표준화
- 문서만으로 작업 가능
- 안정적 운영 (장애 최소화)

## 사용 사례 매트릭스

| 사용 사례 | DevOps | 개발자 | SRE | 관리자 | |----------|--------|--------|-----|--------| | **로컬 개발 환경** | ⚠️ 가끔 | ✅ 매일 | ❌ 없음
| ❌ 없음 | | **스테이징 배포** | ✅ 매일 | ⚠️ 가끔 | ✅ 매일 | ⚠️ 가끔 | | **프로덕션 배포** | ✅ 주간 | ❌ 없음 | ✅ 주간 | ⚠️ 월간 | | **롤백** | ⚠️ 가끔 | ❌
드물게 | ✅ 자주 | ⚠️ 가끔 | | **히스토리 조회** | ⚠️ 가끔 | ❌ 드물게 | ✅ 매일 | ⚠️ 가끔 | | **설정 검증** | ✅ 매일 | ⚠️ 가끔 | ✅ 매일 | ❌ 드물게 |

## 사용자 여정 (User Journey)

### 여정 1: 첫 번째 배포 (DevOps 엔지니어)

**목표**: SBKube를 사용하여 Helm 차트를 처음 배포

**단계**:

1. **인지**: 팀원 추천, GitHub 발견
1. **설치**: `pip install sbkube`
1. **학습**: README 및 빠른 시작 가이드 읽기
1. **설정**: config.yaml, sources.yaml 작성
1. **검증**: `sbkube validate`
1. **테스트**: `sbkube deploy --dry-run`
1. **배포**: `sbkube deploy --namespace staging`
1. **확인**: `sbkube history`

**터치포인트**:

- PyPI 패키지 페이지
- GitHub README
- 문서 사이트 (docs/)
- 예제 파일 (examples/)

**고객 감정**:

- 🟢 설치 쉬움: "pip 한 줄로 끝"
- 🟡 설정 복잡: "YAML 파일 많네..."
- 🟢 검증 유용: "오류를 미리 잡아줘서 좋다"
- 🟢 배포 성공: "정말 간단하네!"

### 여정 2: 프로덕션 롤백 (SRE)

**목표**: 프로덕션 배포 후 문제 발생, 이전 버전으로 롤백

**단계**:

1. **문제 발견**: 모니터링 알림 수신
1. **히스토리 조회**: `sbkube history --namespace production`
1. **이전 배포 ID 확인**: 가장 최근 성공 배포
1. **롤백 실행**: `sbkube rollback --deployment-id 12345`
1. **상태 확인**: `kubectl get pods -n production`
1. **근본 원인 분석**: 배포 로그 검토

**터치포인트**:

- CLI 도구
- 배포 히스토리 DB
- 문제 해결 문서 (docs/07-troubleshooting/)

**고객 감정**:

- 🔴 긴장: "빨리 복구해야 해"
- 🟢 안심: "히스토리가 명확하게 보여"
- 🟢 신속: "롤백이 빠르다"
- 🟢 만족: "다시 정상 운영"

## 사용자 니즈 우선순위

### 높은 우선순위 (Must Have)

1. **일관된 배포 워크플로우**: 모든 페르소나 공통
1. **명확한 오류 메시지**: 학습 곡선 완화
1. **배포 히스토리 추적**: SRE 및 DevOps 필수
1. **설정 파일 검증**: 배포 오류 사전 방지
1. **Dry-run 모드**: 안전한 배포 테스트

### 중간 우선순위 (Should Have)

6. **롤백 기능**: SRE 긴급 상황 대응
1. **진행 상태 표시**: 사용자 경험 개선
1. **다중 소스 통합**: Helm + YAML + Git
1. **환경별 설정**: 개발/스테이징/프로덕션
1. **상세 로깅**: 디버깅 지원

### 낮은 우선순위 (Nice to Have)

11. **병렬 처리**: 성능 최적화
01. **웹 UI**: 비기술 사용자 접근성
01. **플러그인 시스템**: 확장성
01. **멀티 클러스터**: 대규모 환경

## 사용자 온보딩 전략

### 1단계: 빠른 시작 (Quick Start)

- 5분 이내 첫 배포 성공
- 최소한의 설정 파일 예제
- 단계별 명령어 가이드

### 2단계: 기본 학습 (Learn Basics)

- 주요 개념 이해 (워크플로우, 앱 타입)
- 설정 파일 작성법
- 일반적인 사용 사례

### 3단계: 고급 활용 (Advanced Usage)

- 롤백 및 히스토리 관리
- 환경별 배포 전략
- 커스텀 검증 로직

### 4단계: 마스터 (Expert)

- 플러그인 개발
- CI/CD 통합
- 멀티 클러스터 관리

## 피드백 수집 계획

### 방법

- GitHub Issues/Discussions
- 사용자 설문조사 (분기별)
- 실사용 사례 인터뷰
- 커뮤니티 포럼 모니터링

### 주요 질문

1. 어떤 사용 사례로 SBKube를 사용하나요?
1. 가장 유용한 기능은 무엇인가요?
1. 가장 큰 불편함은 무엇인가요?
1. 추가로 원하는 기능은?
1. 다른 도구 대비 장단점은?

______________________________________________________________________

**문서 버전**: 1.0 **마지막 업데이트**: 2025-10-20 **관련 문서**:

- [제품 정의서](product-definition.md)
- [기능 명세서](product-spec.md)
- [빠른 시작 가이드](../01-getting-started/README.md)
