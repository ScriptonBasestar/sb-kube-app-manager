# SBKube 모듈 목적

## 핵심 목적 (Core Purpose)

SBKube 모듈은 **Kubernetes 배포 자동화를 위한 통합 CLI 도구**로서, 다양한 배포 소스(Helm, YAML, Git)를 하나의 일관된 워크플로우로 통합합니다.

## 해결하는 문제 (Problems Solved)

### 1. 배포 소스의 파편화
**문제**: Helm 차트, YAML 매니페스트, Git 리포지토리 등 다양한 소스를 각각 다른 방식으로 관리

**해결**: 단일 설정 파일(config.yaml)로 모든 소스 통합 정의

### 2. 수동 작업의 반복
**문제**: 매번 helm pull, git clone, kubectl apply 등 수동 명령어 실행

**해결**: prepare-build-template-deploy 4단계 자동화 워크플로우

### 3. 배포 상태 추적 부재
**문제**: 어떤 버전이 어느 환경에 배포되었는지 추적 곤란

**해결**: SQLAlchemy 기반 배포 히스토리 및 롤백 시스템

## 제공하는 가치 (Value Proposition)

### 1. 일관성 (Consistency)
- 모든 환경(개발/스테이징/프로덕션)에서 동일한 배포 절차
- 팀원 간 배포 방식 통일
- 재현 가능한 배포 (설정 파일 기반)

### 2. 자동화 (Automation)
- 4단계 워크플로우로 수동 작업 최소화
- Dry-run 모드로 사전 검증
- 배포 후 자동 상태 기록

### 3. 안정성 (Reliability)
- Pydantic 기반 설정 검증으로 오류 사전 방지
- 롤백 기능으로 빠른 복구
- 명확한 에러 메시지

### 4. 사용자 경험 (User Experience)
- Rich 콘솔 UI로 시각적 피드백
- 실시간 진행 상태 표시
- 직관적인 명령어 체계

## 사용 사례 (Use Cases)

### 1. 로컬 개발 환경 셋업
개발자가 프로젝트 의존성(DB, 캐시 등)을 로컬 k3s에 빠르게 배포

```bash
sbkube prepare --app-dir dev-config
sbkube deploy --namespace dev-local
```

### 2. 스테이징 환경 배포
DevOps 엔지니어가 스테이징 환경에 전체 스택 배포

```bash
sbkube prepare --app-dir config/staging
sbkube build
sbkube template --output-dir rendered/staging
sbkube deploy --namespace staging
```

### 3. 프로덕션 배포 및 롤백
SRE가 프로덕션 배포 후 문제 발생 시 롤백

```bash
# 배포
sbkube deploy --namespace production

# 문제 발생 시
sbkube state history --namespace production
sbkube state rollback --deployment-id 12345
```

### 4. 멀티 앱 배포
시스템 관리자가 여러 애플리케이션을 순차적으로 배포

```bash
# 전체 앱 배포
sbkube prepare
sbkube deploy

# 특정 앱만 업그레이드
sbkube upgrade --app database
```

## 설계 목표 (Design Goals)

### 1. 단순성 (Simplicity)
- 복잡한 Helm/kubectl 명령어를 간단한 CLI로 추상화
- 선언적 설정으로 의도 명확히 표현
- 학습 곡선 최소화

### 2. 확장성 (Extensibility)
- 새로운 앱 타입 쉽게 추가
- 플러그인 시스템 (향후)
- 커스텀 검증 로직 확장 가능

### 3. 운영성 (Operability)
- 배포 히스토리 추적
- 롤백 지원
- 상세 로깅 및 디버깅

### 4. 호환성 (Compatibility)
- 표준 Helm 차트 지원
- 일반 YAML 매니페스트 지원
- Kubernetes 표준 API 사용

## 비교 분석 (Comparison)

| 측면 | SBKube | Helm만 사용 | kubectl만 사용 | Helmfile |
|------|---------|------------|---------------|----------|
| **통합 워크플로우** | ✅ 4단계 자동화 | ❌ 수동 단계 | ❌ 수동 단계 | ⚠️ 부분 자동화 |
| **다중 소스** | ✅ Helm+YAML+Git | ❌ Helm만 | ❌ YAML만 | ⚠️ Helm 중심 |
| **상태 관리** | ✅ SQLAlchemy DB | ⚠️ Helm secrets | ❌ 없음 | ⚠️ Helm 의존 |
| **설정 검증** | ✅ Pydantic | ❌ 없음 | ❌ 없음 | ⚠️ 기본 검증 |
| **k3s 최적화** | ✅ 최적화됨 | ⚠️ 일반 K8s | ⚠️ 일반 K8s | ⚠️ 일반 K8s |
| **사용자 경험** | ✅ Rich UI | ⚠️ 기본 CLI | ⚠️ 기본 CLI | ⚠️ 기본 CLI |

## 제약사항 및 한계 (Constraints & Limitations)

### 현재 제약사항
- 단일 클러스터 대상 (멀티 클러스터 미지원)
- SQLite 기반 로컬 상태 관리 (분산 환경 제한)
- Python 3.12+ 필수
- Helm v3.x 호환성 (v2 미지원)

### 의도적 제한
- Kubernetes 클러스터 프로비저닝은 책임 범위 밖
- 컨테이너 이미지 빌드는 외부 도구 사용
- CI/CD 파이프라인 오케스트레이션은 다른 도구에 위임

## 향후 방향 (Future Direction)

### 단기 (v0.3.x)
- 병렬 처리로 성능 개선
- 플러그인 시스템 베타
- 웹 UI 프로토타입

### 중기 (v0.4.x - v0.6.x)
- 멀티 클러스터 지원
- GitOps 통합 (Flux, ArgoCD)
- 고급 상태 관리 (분산 잠금)

### 장기 (v1.0.x)
- Kubernetes Operator
- 엔터프라이즈 기능 (HA, Multi-tenancy)
- API 서버 모드

---

**문서 버전**: 1.0
**마지막 업데이트**: 2025-10-20
**관련 문서**:
- [../MODULE.md](../../MODULE.md) - 모듈 정의
- [../ARCHITECTURE.md](../../ARCHITECTURE.md) - 아키텍처 설계
- [../../../../00-product/product-definition.md](../../../../00-product/product-definition.md) - 제품 정의
