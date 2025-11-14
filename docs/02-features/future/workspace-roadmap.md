______________________________________________________________________

## type: Implementation Plan
audience: Developer
topics: [workspace, roadmap, implementation, multi-phase]
llm_priority: medium
last_updated: 2025-01-13

# Workspace Feature Implementation Plan

**Status**: ✅ DESIGN RESOLVED - 구현 준비 완료
**Created**: 2025-01-08
**Last Updated**: 2025-01-13
**Design Review Completed**: 2025-01-13

**관련 문서**:
- [workspace-design.md](workspace-design.md) - 설계 결정 문서
- [workspace-schema.md](../../03-configuration/workspace-schema.md) - 스키마 사용자 가이드
- [workspace-schema.yaml](../../03-configuration/workspace-schema.yaml) - 스키마 예제

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

## ✅ 설계 결정 (2025-01-13 해결됨)

### Issue #1: Phase별 Sources 참조 ✅ RESOLVED

**문제**:
- 초기 설계: workspace가 단일 `sources.yaml`만 참조
- 실제 요구사항: 각 Phase가 독립적인 `sources.yaml` 가질 수 있음

**최종 결정: 옵션 A (Override Approach)** ✅

```yaml
# workspace.yaml
phases:
  p1-infra:
    source: p1-kube/sources.yaml  # Required: 각 phase는 sources.yaml 참조
    app_groups: [...]
  p2-data:
    source: p2-kube/sources.yaml
    app_groups: [...]
```

**선택 근거**:
- ✅ 관심사 분리 (Orchestration vs Targeting)
- ✅ Sources 파일 재사용 가능
- ✅ 다중 클러스터/단일 클러스터 모두 지원
- ✅ 기존 SBKube 아키텍처 패턴과 일관성

**우선순위 규칙**:
1. App-level (config.yaml) - 최우선
2. Phase-level (sources.yaml)
3. Workspace-level (global section) - 최하위

### Issue #2: Cluster Targeting 복잡도 ✅ RESOLVED

**질문**:
- 각 Phase가 **다른 클러스터**를 타겟팅할 수 있는가?
- 대부분의 use case는 **동일 클러스터, 순차 배포**인가?

**최종 결정: v1.0은 단일 클러스터 순차 배포 집중** ✅

**선택 근거 (80/20 Rule)**:
- ✅ 90% 사용 사례: 동일 클러스터, 순차 배포 (infra → data → app)
- ✅ 10% 사용 사례: 다중 클러스터 (향후 v1.1+에서 지원)
- ✅ 단순성 우선: 대다수를 위한 최적화
- ✅ 점진적 확장: 다중 클러스터는 breaking change 없이 추가 가능

**v1.0 구현**:
- 같은 클러스터에 순차 배포
- 각 phase는 다른 namespace 사용 가능
- Phase 의존성 해결 (Kahn's algorithm)

**v1.1+ 향후 개선**:
- 다중 클러스터 병렬 배포
- 클러스터 간 의존성 검증

### Issue #3: Repository 관리 ✅ RESOLVED

**문제**:
- Phase별로 **다른 Helm/OCI 리포지토리** 필요할 수 있음

**예시**:
```
Phase 1 (infra): cilium, coredns 리포지토리
Phase 2 (data): grafana 리포지토리
Phase 3 (app): custom OCI registry
```

**최종 결정: App > Phase > Workspace 우선순위** ✅

**3단계 우선순위**:
1. **App-level** (config.yaml) - 최우선
   ```yaml
   apps:
     nginx:
       chart: custom-repo/nginx  # 명시적 리포지토리 참조
   ```

2. **Phase-level** (sources.yaml)
   ```yaml
   helm_repos:
     custom-repo:
       url: https://charts.internal.com
   ```

3. **Workspace-level** (workspace.yaml global)
   ```yaml
   global:
     helm_repos:
       grafana:
         url: https://grafana.github.io/helm-charts
   ```

**선택 근거**:
- ✅ 가장 구체적인 설정이 우선
- ✅ 기존 SBKube 상속 패턴과 일관성
- ✅ Global 기본값 + 명시적 override 지원

### Issue #4: 파일 네이밍 ✅ RESOLVED

**최종 결정: workspace.yaml** ✅

**선택 근거**:
- ✅ sources.yaml, config.yaml과 일관된 네이밍 패턴
- ✅ "workspace"가 top-level orchestration 범위를 명확히 표현
- ✅ 향후 확장성 (workspace-level hooks, validation 등)

**거부된 대안**:
- ❌ phases.yaml: 너무 좁은 범위 (phase만 함축)
- ❌ deployment-plan.yaml: 너무 일반적

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
