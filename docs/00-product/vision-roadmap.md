______________________________________________________________________

## type: Product Strategy audience: Product Manager, Developer topics: [vision, roadmap, future, milestones] llm_priority: medium last_updated: 2025-01-06

# SBKube 비전과 로드맵

> **주의**: 이 문서는 [PRODUCT.md](../../PRODUCT.md) Section 10 (프로젝트 정보)의 상세 버전입니다. 핵심 로드맵은 PRODUCT.md를 우선 참조하세요.

## 장기 비전

**"DevOps 생태계를 위한 통합 배포 플랫폼"**

SBKube는 단순한 Kubernetes 배포 도구를 넘어, DevOps 팀이 모든 배포 소스를 통합 관리하고 자동화할 수 있는 생태계를 구축합니다.

### 핵심 가치

- **통합성**: 모든 배포 소스(Helm, YAML, Git, OCI)를 하나의 워크플로우로
- **자동화**: 수동 작업 최소화 및 일관된 배포 절차
- **신뢰성**: 상태 관리 및 롤백을 통한 안정적 운영
- **확장성**: 플러그인 시스템을 통한 무한 확장

## 완료된 마일스톤

### v0.4.x (2024)

**목표**: 핵심 기능 안정화 및 필수 요구사항 정립

- ✅ 4단계 워크플로우 (prepare-build-template-deploy)
- ✅ Helm, YAML, Git 소스 통합
- ✅ Pydantic 기반 설정 검증
- ✅ SQLAlchemy 상태 관리
- ✅ Rich 콘솔 UI
- ✅ sources.yaml 클러스터 설정 필수화 (v0.4.10)
- ✅ 앱 의존성 deps 필드 지원 (v0.4.9)

### v0.5.x (2024년 8월)

**목표**: 통합 워크플로우 및 Hooks 시스템

- ✅ `apply` 명령어: 통합 워크플로우 (prepare → build → template → deploy)
- ✅ Hooks 시스템 기초 (pre_deploy, post_deploy)

### v0.6.0 (2024년 10월 - 현재 안정 버전)

**목표**: 앱 그룹 관리 및 상태 추적 강화

- ✅ 앱 그룹 의존성 검증 (deps 필드)
- ✅ 네임스페이스 자동 감지
- ✅ 라벨 기반 분류 시스템
- ✅ `status`, `history`, `rollback` 명령어 통합

## 단기 로드맵 (v0.7.x - v0.8.x)

### v0.7.0 (2025 Q1 - 진행 중) 🟡

**목표**: LLM 친화적 출력 및 에러 처리 개선

- 🟡 LLM 친화적 출력 시스템 (Phase 1-3 완료)
  - ✅ `--format llm/json/yaml` 옵션
  - ✅ 토큰 사용량 80-90% 절감
  - 🔄 Phase 4-5: 고급 출력 포맷
- 🔄 향상된 에러 처리 및 수정 제안
- 🔄 사전/사후 배포 검증 시스템 강화
- 🔄 문서 개선 및 튜토리얼 추가

### v0.8.0 (2025-01-13 - 릴리즈 완료) ✅

**목표**: Chart Path Collision Prevention 및 Storage 개선

- ✅ Chart path structure 개선 (`.sbkube/charts/{repo}/{chart-name}-{version}/`)
- ✅ PV/PVC validation for manual provisioning (`kubernetes.io/no-provisioner`)
- ✅ 차트 충돌 방지 (같은 이름, 다른 repo 지원)
- ✅ 버전별 차트 관리 (같은 차트, 다른 버전 공존)
- ✅ 레거시 경로 자동 감지 및 마이그레이션 가이드

**Breaking Changes**: Chart path 구조 변경 (마이그레이션 필수)

### v0.8.x (2025 Q2-Q3)

**목표**: Hooks 고도화 및 성능 최적화

- [ ] Manifests Hooks (YAML 자동 배포)
- [ ] Task 시스템 (Inline YAML, 타입 시스템)
- [ ] 플러그인 인터페이스 설계
- [ ] 병렬 처리 최적화 (앱 동시 다운로드/배포)
- [ ] 캐싱 메커니즘 고도화

## 중기 로드맵 (v0.9.x - v1.0.x)

### v0.9.0 (2025 Q2 - 계획 중) 🟡

**목표**: Workspace 기능 (Multi-Phase Deployment)

- ✅ Workspace 설계 완료 (2025-01-13)
  - ✅ 파일명: workspace.yaml
  - ✅ Phase-level sources 참조 (Override 방식)
  - ✅ 단일 클러스터 순차 배포
  - ✅ Repository 우선순위: App > Phase > Workspace
- [ ] Pydantic 모델 구현 (WorkspaceConfig, PhaseConfig)
- [ ] CLI 명령어 구현 (workspace validate/deploy/status)
- [ ] Phase 의존성 해결 (Kahn's algorithm)
- [ ] Workspace-level 상태 관리

**Use Case**: p1-kube, p2-kube, p3-kube처럼 단계별로 나뉜 프로젝트 구조 지원

**설계 문서**:
- [workspace-design.md](../02-features/future/workspace-design.md) - Design decisions
- [workspace-schema.md](../03-configuration/workspace-schema.md) - Schema guide
- [workspace-schema.yaml](../03-configuration/workspace-schema.yaml) - Example schema
- [workspace-roadmap.md](../02-features/future/workspace-roadmap.md) - Implementation plan

### v0.9.x (2025 Q3-Q4)

**목표**: 엔터프라이즈 기능 확장

- [ ] 멀티 클러스터 동시 배포 (Workspace v1.1)
- [ ] 웹 UI 프로토타입 (배포 상태 대시보드)
- [ ] 분산 잠금 (동시 배포 충돌 방지)
- [ ] 고급 롤백 (스냅샷 기반)

### v1.0.x (2026 Q2 - 안정 버전)

**목표**: GitOps 통합 및 프로덕션 레디

- [ ] GitOps 워크플로우 (Flux, ArgoCD 연동)
- [ ] CI/CD 파이프라인 통합 (GitHub Actions, GitLab CI)
- [ ] 웹 대시보드 정식 버전
- [ ] 팀 관리 및 권한 제어 (RBAC)
- [ ] 엔터프라이즈 지원 (SLA, 지원 계약)

## 장기 로드맵 (v1.1+ / 2026+)

### 생태계 확장

**목표**: DevOps 도구 통합 플랫폼

- [ ] sbproxy, sbrelease 등 도구 간 연동
- [ ] API 서버 모드 (원격 관리)
- [ ] Kubernetes Operator 개발
- [ ] 클라우드 네이티브 에코시스템 통합

### 엔터프라이즈 기능

**목표**: 대규모 프로덕션 환경 지원

- [ ] 고가용성 (HA) 아키텍처
- [ ] 멀티 테넌시 지원
- [ ] 규정 준수 (컴플라이언스 리포트)
- [ ] 성능 벤치마크 (1000+ 앱 배포)

### 보안 및 모니터링

**목표**: 엔터프라이즈 보안 강화

- [ ] Secrets 관리 통합 (Sealed Secrets, Vault)
- [ ] 고급 RBAC 및 Audit 로그
- [ ] Prometheus/Grafana 네이티브 통합
- [ ] 비용 최적화 (리소스 사용량 추적)

## 마일스톤

### 2024 (완료)

- ✅ Q2-Q3: v0.4.x 핵심 기능 안정화
- ✅ Q3: v0.5.0 통합 워크플로우 및 Hooks
- ✅ Q4: v0.6.0 앱 그룹 관리 및 상태 추적

### 2025

- 🟡 Q1: v0.7.0 LLM 친화적 출력 (진행 중)
- Q2-Q3: v0.8.x Hooks 고도화 및 성능 최적화
- Q4: v0.9.x 엔터프라이즈 기능 시작

### 2026

- Q1: v0.9.x 멀티 클러스터 및 웹 UI
- Q2: v1.0.x 안정 버전 릴리스 (GitOps 통합)
- Q3-Q4: v1.1.x 생태계 확장

## 의존성 및 전제조건

### 기술적 의존성

- Python 생태계 발전 (3.12+)
- Helm v3.x 호환성 유지
- Kubernetes API 안정성
- SQLAlchemy, Pydantic 최신 버전 지원

### 커뮤니티 의존성

- 오픈소스 기여자 확보
- 사용자 피드백 수집
- 문서 및 튜토리얼 확충
- 에코시스템 파트너십

## 성공 지표

### 정량적 지표

- PyPI 월간 다운로드: 1,000+ (v0.5.x), 10,000+ (v1.0.x)
- GitHub Stars: 100+ (v0.5.x), 500+ (v1.0.x)
- 활성 기여자: 10+ (v1.0.x)
- 프로덕션 사용 사례: 50+ (v1.0.x)

### 정성적 지표

- 사용자 만족도: 4.5/5.0 이상
- 문서 완성도: 90% 이상
- 커뮤니티 활동: 월 10+ 이슈/PR
- 기업 채택: 3+ 주요 기업

## 위험 요소 및 대응

### 기술적 위험

- **Kubernetes API 변경**: 버전별 호환성 테스트 자동화
- **Helm v4 출시**: 마이그레이션 계획 수립
- **성능 병목**: 프로파일링 및 최적화 지속

### 비즈니스 위험

- **경쟁 도구 출현**: 차별화 포인트 강화 (k3s 특화)
- **사용자 채택 저조**: 마케팅 및 튜토리얼 투자
- **유지보수 부담**: 커뮤니티 기여 활성화

______________________________________________________________________

## 관련 문서

- **상위 문서**: [PRODUCT.md](../../PRODUCT.md) - 제품 개요 (무엇을, 왜)
- **제품 정의**: [product-definition.md](product-definition.md) - 완전한 제품 정의
- **기능 명세**: [product-spec.md](product-spec.md) - 전체 기능 목록
- **변경 이력**: [../../CHANGELOG.md](../../CHANGELOG.md) - 버전별 변경사항

______________________________________________________________________

**문서 버전**: 1.2 **마지막 업데이트**: 2025-01-06 **담당자**: archmagece@users.noreply.github.com
