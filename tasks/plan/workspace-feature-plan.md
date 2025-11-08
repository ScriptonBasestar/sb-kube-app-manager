# Workspace Feature Implementation Plan

**Status**: On Hold - 설계 재검토 필요
**Created**: 2025-01-08
**Last Updated**: 2025-01-08

---

## 📋 목표

Phase 기반 다단계 배포를 지원하는 Workspace 개념 도입 (v0.8.0 목표)

**Use Case**: p1-kube, p2-kube, p3-kube처럼 단계별로 나뉜 프로젝트 구조 지원

---

## 🎯 핵심 요구사항

### 계층 구조 (4단계)

```
Workspace (workspace.yaml)
├─ Phase 1 (infra)
│  ├─ App Group: a000_network/
│  │  ├─ App: cilium
│  │  └─ App: coredns
│  └─ App Group: a001_storage/
│     └─ App: nfs-provisioner
├─ Phase 2 (data)
│  └─ App Group: a100_postgres/
│     └─ App: postgres
└─ Phase 3 (app)
   └─ App Group: a200_backend/
      └─ App: api-server
```

### 의존성 관리 (3단계)

1. **Phase-level**: Phase 간 순서 보장
2. **App-group-level**: 앱 그룹 간 의존성 (기존 `deps`)
3. **App-level**: 앱 간 의존성 (기존 `depends_on`)

---

## 🚨 설계 이슈 (롤백 사유)

### Issue #1: Phase별 Sources 참조

**문제**:
- 초기 설계: workspace가 단일 `sources.yaml`만 참조
- 실제 요구사항: 각 Phase가 독립적인 `sources.yaml` 가질 수 있음

```yaml
# 현재 설계 (불충분)
workspace.yaml:
  source: sources.yaml  # 단일 sources만

# 필요한 설계
workspace.yaml:
  phases:
    p1:
      source: p1-kube/sources.yaml  # Phase별 sources
    p2:
      source: p2-kube/sources.yaml
```

**해결 방안 (검토 필요)**:

**옵션 A: Phase-level Source Override**
```yaml
# Workspace-level 기본값 + Phase-level override
source: sources.yaml  # 기본값 (optional)

phases:
  p1:
    source: p1-kube/sources.yaml  # override
  p2:
    # source 생략 → workspace의 sources.yaml 사용
```

**장점**:
- 단순한 경우와 복잡한 경우 모두 지원
- 후방 호환성 유지

**단점**:
- 복잡도 증가
- 검증 로직 추가 필요

**옵션 B: Phase별 Inline Config**
```yaml
phases:
  p1:
    kubeconfig: ~/.kube/config
    kubeconfig_context: prod
    helm_repos: {...}
```

**장점**:
- 명시적

**단점**:
- 설정 중복 가능성

### Issue #2: Cluster Targeting 복잡도

**질문**:
- 각 Phase가 **다른 클러스터**를 타겟팅할 수 있는가?
- 대부분의 use case는 **동일 클러스터, 순차 배포**인가?

**일반적 시나리오**:
1. **동일 클러스터, 순차 배포** (90% 케이스)
   - Phase 1, 2, 3 모두 같은 prod 클러스터
   - 순서만 다름 (infra → data → app)

2. **다중 클러스터, 순차 배포** (10% 케이스)
   - Phase 1: dev 클러스터
   - Phase 2: staging 클러스터
   - Phase 3: prod 클러스터

**설계 결정 필요**:
- 대다수 케이스를 위한 단순성 vs 소수 케이스를 위한 유연성

### Issue #3: Repository 관리

**문제**:
- Phase별로 **다른 Helm/OCI 리포지토리** 필요할 수 있음

**예시**:
```
Phase 1 (infra): cilium, coredns 리포지토리
Phase 2 (data): bitnami 리포지토리
Phase 3 (app): custom OCI registry
```

**해결 방안**:
1. Workspace-level 글로벌 리포지토리 (공통)
2. Phase-level 리포지토리 추가 (선택적)
3. App-level 리포지토리 (sources.yaml에서)

---

## 📝 Phase 1 완료 사항

### 완성된 코드
1. ✅ [sbkube/models/workspace_model.py](../../sbkube/models/workspace_model.py) - 197 lines, 78% coverage
   - `WorkspacePhase`: Phase 정의
   - `WorkspaceConfig`: Workspace 전체 설정
   - `get_phase_order()`: Kahn's algorithm으로 위상 정렬
   - `validate_phase_dependencies()`: 순환 의존성 검출 (DFS)

2. ✅ [sbkube/utils/workspace_manager.py](../../sbkube/utils/workspace_manager.py)
   - `WorkspaceManager`: Workspace 로드/검증/관리
   - `load_workspace()`: workspace.yaml 로딩
   - `get_sources_config()`: sources 설정 반환
   - `get_execution_order()`: Phase 실행 순서
   - `validate_workspace()`: 전체 검증

3. ✅ [tests/unit/models/test_workspace_model.py](../../tests/unit/models/test_workspace_model.py)
   - 22개 단위 테스트 (모두 통과)
   - Phase 검증, 의존성 순환 검출, 위상 정렬 테스트

### 현재 기능
- ✅ Phase 의존성 기반 위상 정렬
- ✅ 순환 의존성 검출
- ✅ Reference mode (sources.yaml) / Inline mode 지원
- ✅ Pydantic 검증 (empty fields, duplicates, invalid paths)

### 한계점
- ❌ Phase별 sources 참조 미지원 (workspace-level source만)
- ❌ CLI 명령어 미구현
- ❌ 실제 배포 로직 미구현
- ❌ 상태 관리 미구현

---

## 🛠️ 향후 구현 계획 (보류)

### Phase 1: 모델 개선 (설계 재검토 후)
- [ ] `WorkspacePhase`에 `source: str | None` 추가
- [ ] Workspace 검증 로직 강화
- [ ] Phase별 sources 우선순위 규칙 정의
- [ ] 테스트 추가 (phase-level source override)

### Phase 2: CLI 명령어 (모델 확정 후)
- [ ] `workspace init`: workspace.yaml 템플릿 생성
- [ ] `workspace validate`: workspace.yaml 검증
- [ ] `workspace graph`: Phase 의존성 시각화
- [ ] CLI 통합 (cli.py)

### Phase 3: 배포 로직 (2-3일)
- [ ] `workspace apply`: 전체 또는 특정 Phase 배포
- [ ] Phase 순차 실행
- [ ] Hook 통합 (workspace-level, phase-level)
- [ ] 에러 핸들링

### Phase 4: 상태 관리 (2-3일)
- [ ] `PhaseState`, `WorkspaceState` 모델
- [ ] `workspace status`: 배포 상태 조회
- [ ] `workspace history`: 배포 히스토리
- [ ] 데이터베이스 스키마 추가

### Phase 5: 문서 및 예제 (1-2일)
- [ ] `docs/02-features/workspace-guide.md`
- [ ] `docs/03-configuration/workspace-schema.md`
- [ ] `examples/workspace-example/`
- [ ] PRODUCT.md, SPEC.md 업데이트

**총 예상 기간**: 9-14일 (설계 확정 후)

---

## 🤔 해결해야 할 질문

1. **Phase별 Sources 참조**:
   - 옵션 A (Override) vs 옵션 B (Inline) 중 선택?
   - 검증 규칙은 어떻게?

2. **Cluster Targeting**:
   - 동일 클러스터 순차 배포를 기본으로 가정?
   - 다중 클러스터 지원 필요성?

3. **Repository 관리**:
   - Workspace-level vs Phase-level vs App-level?
   - 우선순위 규칙?

4. **후방 호환성**:
   - 기존 sources.yaml 구조 유지?
   - Breaking change 허용 범위?

5. **사용자 경험**:
   - `sbkube workspace apply` vs `sbkube apply --workspace`?
   - 기존 명령어와의 관계?

---

## 📚 참고 자료

- [PRODUCT.md](../../PRODUCT.md): 제품 철학 (단순성, Convention over Configuration)
- [SPEC.md](../../SPEC.md): 기술 스펙
- [sources_model.py](../../sbkube/models/sources_model.py): 현재 SourceScheme 구조
- [config_model.py](../../sbkube/models/config_model.py): 현재 SBKubeConfig 구조

---

## 🎯 다음 단계

1. **설계 재검토 회의**:
   - Phase별 sources 참조 방식 결정
   - Cluster targeting 전략 결정
   - Repository 관리 우선순위 결정

2. **프로토타입 테스트**:
   - p1-kube, p2-kube, p3-kube 실제 케이스로 검증
   - 여러 시나리오 테스트 (단순 → 복잡)

3. **구현 재개**:
   - 설계 확정 후 Phase 1부터 재시작
   - 점진적 기능 추가 (단순 → 복잡)

---

## 💭 교훈

1. **복잡도 관리**:
   - 초기 설계에서 모든 케이스를 커버하려 하면 복잡도 폭발
   - 80% 케이스를 먼저 지원하고 점진적 확장 필요

2. **실제 사용 패턴 파악**:
   - p1-kube, p2-kube, p3-kube 구조의 실제 의도 확인 필요
   - 사용자 인터뷰 또는 실제 케이스 분석 필요

3. **단순성 우선**:
   - SBKube의 핵심 철학은 "단순성"
   - 기능 추가 전에 "정말 필요한가?" 질문 필수

---

**상태**: 설계 재검토 대기 중
**블로커**: Phase별 sources 참조 방식 미결정
**다음 액션**: 실제 사용 케이스 조사 및 설계 재검토
