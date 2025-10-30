# Examples Directory Updates (v0.5.0+)

이 문서는 2025-10-31에 수행된 examples 디렉토리 대대적인 업데이트 내역을 기록합니다.

## 📋 업데이트 목표

sbkube v0.5.0+의 새로운 기능들을 반영하고, 실제 사용 가능한 예제들로 재편성:
- ✅ 새로운 기능 시연
- ✅ 실전 사용 패턴 제공
- ✅ 엣지 케이스 및 버그 수정 시나리오 추가
- ✅ 일관된 문서화 표준 적용

## 🎯 업데이트 범위

### Priority 1: 핵심 기능 강화

#### 1.1 removes 기능 예제 추가 (override-with-files)

**위치**: `examples/override-with-files/`

**변경 사항**:
- ✅ 완전히 재작성된 `config.yaml` (이전 파일 손상됨)
- ✅ `removes` 기능 시연 추가
  - `templates/tests/` 전체 삭제
  - `templates/NOTES.txt` 제거
  - `templates/ingress.yaml` 제거
- ✅ 상세한 README.md 작성

**시연 기능**:
- `overrides/`: Helm 차트 템플릿 오버라이드
- `removes/`: 불필요한 차트 파일 제거

#### 1.2 OCI Registry 완성 (prepare/helm-oci)

**위치**: `examples/prepare/helm-oci/`

**변경 사항**:
- ✅ `config.yaml` 수정 (잘못된 포맷 수정)
  - Before: `chart: browserless/browserless-chrome` (잘못됨)
  - After: `repo: browserless`, `chart: browserless-chrome` (올바름)
- ✅ `sources.yaml`에 OCI 리포지토리 설정 추가
- ✅ 상세한 README.md 작성 (OCI vs Helm repo 비교)

**배운 교훈**:
- OCI 레지스트리는 별도 `oci_repos` 섹션 필요
- chart 필드에 repo/chart 형식 사용 불가 (별도 필드로 분리)

#### 1.3 기본 Helm 예제 강화 (app-types/01-helm)

**위치**: `examples/app-types/01-helm/`

**변경 사항**:
- ✅ `set_values` 기능 시연
- ✅ `release_name` 커스터마이징
- ✅ 다중 values 파일 병합 (`prometheus-values-base.yaml`, `prometheus-values-override.yaml`)
- ✅ 앱별 namespace 오버라이드 (주석 처리로 설명)
- ✅ 완전히 재작성된 README.md (30개 섹션, 300줄)

**시연 기능**:
- CLI 값 오버라이드 (`set_values`)
- 커스텀 릴리스 이름 (`release_name`)
- Values 파일 병합 우선순위
- 환경별 설정 전략

### Priority 2: 고급 기능 예제

#### 2.1 Multi-App Groups 예제 생성

**위치**: `examples/multi-app-groups/`

**새로 생성**:
- ✅ `frontend/config.yaml` - Nginx 프론트엔드
- ✅ `backend/config.yaml` - API 서버 (YAML 매니페스트)
- ✅ `database/config.yaml` - PostgreSQL + Redis (Helm)
- ✅ `sources.yaml` - 자동 탐색 (app_dirs 미지정)
- ✅ `sources-selective.yaml` - 선택적 배포 (app_dirs 지정)
- ✅ README.md (200줄+)

**시연 기능**:
- 자동 앱 그룹 탐색 (모든 `config.yaml` 발견)
- `app_dirs`로 특정 그룹만 배포
- 티어별 그룹화 (frontend, backend, database)
- 배포 순서 제어

**사용 사례**:
- 마이크로서비스 아키텍처
- 환경별 배포 (dev: 전체, prod: 일부만)
- 점진적 롤아웃

#### 2.2 의존성 체인 강화 (dependency-chain)

**위치**: `examples/dependency-chain/`

**새로 생성**:
- ✅ 9단계 배포 파이프라인
- ✅ `config.yaml` - 복잡한 depends_on 체인
- ✅ `manifests/` - 스토리지, 백엔드, 프론트엔드, Ingress
- ✅ README.md (250줄+, 배포 시간 분석 포함)

**시연 기능**:
- 병렬 실행 (postgresql + redis)
- 다중 의존성 (backend-api → postgresql, redis, init-database)
- 초기화 작업 (init-database exec)
- 단계별 검증 (verify-cluster, verify-deployment)

**배포 순서**:
```
Phase 1: verify-cluster (exec)
Phase 2: setup-storage (action)
Phase 3-4: postgresql + redis (helm, 병렬)
Phase 5: init-database (exec)
Phase 6: backend-api (yaml)
Phase 7: frontend (yaml)
Phase 8: ingress (yaml)
Phase 9: verify-deployment (exec)
```

#### 2.3 Multi-Source 설정 예제

**위치**: `examples/multi-source/`

**새로 생성**:
- ✅ `sources-dev.yaml` - 개발 환경 (Minikube)
- ✅ `sources-staging.yaml` - 스테이징 환경
- ✅ `sources-prod.yaml` - 프로덕션 환경
- ✅ `config.yaml` - 환경 독립적 앱 설정
- ✅ README.md (200줄+, 환경별 비교표 포함)

**시연 기능**:
- 환경별 kubeconfig 분리
- 리포지토리 설정 재사용
- 환경별 values 오버라이드
- CI/CD 통합 스크립트

**환경별 차이**:
| 항목 | Dev | Staging | Production |
|------|-----|---------|------------|
| 클러스터 | Minikube | 전용 k3s | HA k3s |
| 영속성 | ❌ | ✅ | ✅ |
| 모니터링 | ❌ | ✅ | ✅ |

### Priority 3: 고급 커스터마이징

#### 3.1 Chart Patches 예제 생성

**위치**: `examples/chart-patches/`

**새로 생성**:
- ✅ `config.yaml` - 3개 앱 (Grafana, Prometheus, Redis)
- ✅ `patches/` - 7개 패치 파일
  - Strategic Merge: 사이드카, 포트, 보안
  - JSON Patch: 환경 변수
  - Merge Patch: ConfigMap
  - Create Patch: ServiceMonitor
- ✅ README.md (300줄+, 패치 타입별 설명)

**시연 기능**:
- Strategic Merge Patch (사이드카 컨테이너 추가)
- JSON Patch (정밀한 경로 지정)
- Merge Patch (간단한 병합)
- Create Patch (새 파일 생성)

**사용 사례**:
- 로그 수집 사이드카 추가
- 보안 설정 강화 (SecurityContext)
- 모니터링 통합 (ServiceMonitor)
- 커스텀 리소스 추가

## 📊 업데이트 통계

### 새로 추가된 예제

| 예제 | 파일 수 | README 크기 | 주요 기능 |
|------|---------|-------------|-----------|
| **multi-app-groups** | 7 | 200줄 | 자동 탐색, app_dirs |
| **dependency-chain** | 15+ | 250줄 | 9단계 파이프라인, 병렬 실행 |
| **multi-source** | 10 | 200줄 | 환경별 sources.yaml |
| **chart-patches** | 12+ | 300줄 | 4가지 패치 타입 |

### 강화된 기존 예제

| 예제 | 변경 사항 | README 크기 |
|------|-----------|-------------|
| **override-with-files** | removes 추가, 재작성 | 150줄 |
| **prepare/helm-oci** | 포맷 수정, OCI 설정 | 120줄 |
| **app-types/01-helm** | 고급 기능 4개 추가 | 300줄 |

### 총합

- **새 예제**: 4개
- **강화된 예제**: 3개
- **새 README 줄 수**: 약 1,700줄
- **패치 파일**: 7개
- **매니페스트 파일**: 10+개

## 🎯 적용된 원칙

### 1. Product-First Documentation

모든 README는 다음 구조를 따름:
1. **간단한 소개** - 한 줄 설명
2. **시연 기능** - 무엇을 보여주는가
3. **파일 구조** - 디렉토리 트리
4. **실행 방법** - 즉시 사용 가능한 명령어
5. **검증** - 성공 확인 방법
6. **사용 사례** - 실전 적용 예시
7. **Troubleshooting** - 일반적인 문제

### 2. 실전 중심 예제

- ❌ 이론적 설명보다
- ✅ 복사-붙여넣기 가능한 코드
- ✅ 실행 가능한 명령어
- ✅ 검증 가능한 결과

### 3. 엣지 케이스 포함

버그 수정 시 예제로 추가:
- OCI 레지스트리 포맷 오류
- Deprecated 저장소
- 레포 이름 오타

### 4. 일관된 문서 스타일

모든 README는:
- 📋 이모지 섹션 헤더
- 코드 블록 하이라이팅
- 표 형식 비교
- 명확한 예시/안티패턴

## 🔍 검증 체크리스트

### 파일 존재 확인

- [x] 모든 예제에 `config.yaml` 존재
- [x] 모든 예제에 `sources.yaml` 존재
- [x] 모든 예제에 `README.md` 존재
- [x] 참조된 values 파일 모두 존재
- [x] 참조된 매니페스트 파일 모두 존재
- [x] 참조된 패치 파일 모두 존재

### 내용 검증

- [x] YAML 문법 유효성
- [x] Helm 차트 이름/버전 정확성
- [x] 리포지토리 URL 유효성
- [x] 의존성 체인 순환 없음
- [x] 패치 파일 대상 경로 정확성

### 문서 품질

- [x] 복사-붙여넣기 가능한 명령어
- [x] 예상 출력 결과 포함
- [x] Troubleshooting 섹션 존재
- [x] 관련 예제 링크
- [x] 사용 사례 설명

## 📚 관련 문서

### 업데이트된 예제들

1. [override-with-files](override-with-files/) - removes 기능
2. [prepare/helm-oci](prepare/helm-oci/) - OCI 레지스트리
3. [app-types/01-helm](app-types/01-helm/) - Helm 고급 기능

### 새로 추가된 예제들

1. [multi-app-groups](multi-app-groups/) - 멀티 앱 그룹 관리
2. [dependency-chain](dependency-chain/) - 복잡한 의존성 체인
3. [multi-source](multi-source/) - 환경별 소스 설정
4. [chart-patches](chart-patches/) - Helm 차트 패치

## 🚀 다음 단계

### 향후 추가 예정

- [ ] Kustomize 통합 예제
- [ ] ArgoCD 연동 예제
- [ ] Secret 관리 (Sealed Secrets, External Secrets)
- [ ] Multi-Cluster 배포

### 개선 사항

- [ ] E2E 테스트 자동화
- [ ] CI/CD 파이프라인 템플릿
- [ ] Video 튜토리얼
- [ ] Interactive Demo

## 📝 변경 이력

| 날짜 | 버전 | 변경 사항 |
|------|------|-----------|
| 2025-10-31 | v1.0 | 초기 대대적 업데이트 |
| | | - 7개 예제 추가/강화 |
| | | - 1,700줄+ 문서 작성 |
| | | - v0.5.0 기능 반영 |

## 🤝 기여 가이드

새 예제 추가 시:
1. 이 문서의 원칙 준수
2. README.md 템플릿 사용
3. 실행 가능한 명령어 포함
4. Troubleshooting 섹션 작성
5. 관련 예제 링크 추가

## 📧 연락처

- **Author**: Claude (Anthropic)
- **Date**: 2025-10-31
- **sbkube Version**: v0.5.0+
