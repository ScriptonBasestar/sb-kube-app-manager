# SBKube Examples 커버리지 분석

**분석 날짜**: 2025-10-23
**SBKube 버전**: v0.4.0

---

## 📊 현황 요약

### 지원 앱 타입 vs 예제 매핑

| 앱 타입 | 지원 여부 | 예제 존재 | 예제 위치 | 충분성 | 비고 |
|---------|----------|----------|-----------|--------|------|
| **helm** (원격) | ✅ | ✅ | basic/, k3scode/ | ⭐⭐⭐ 충분 | 여러 시나리오 |
| **helm** (로컬) | ✅ | ✅ | basic/local-chart/ | ⭐⭐ 보통 | 1개만 존재 |
| **helm** (overrides) | ✅ | ✅ | overrides/advanced-example/ | ⭐⭐ 보통 | 고급 기능 |
| **yaml** | ✅ | ✅ | deploy/yaml-example/ | ⭐⭐ 보통 | 단순 예제만 |
| **action** | ✅ | ✅ | deploy/action-example/ | ⭐⭐ 보통 | 기본 시나리오 |
| **exec** | ✅ | ✅ | deploy/exec/ | ⭐ 부족 | 문서 없음 |
| **git** | ✅ | ✅ | k3scode/ai/, complete-workflow/ | ⭐ 부족 | 단독 예제 없음 |
| **http** | ✅ | ✅ | deploy/http-example/ | ⭐⭐ 보통 | README 있음 |
| **kustomize** | ❓ | ❌ | - | ❌ 없음 | 문서에만 언급 |

### 워크플로우 시나리오 커버리지

| 시나리오 | 예제 존재 | 예제 위치 | 품질 |
|----------|----------|-----------|------|
| **prepare only** | ❌ | - | - |
| **prepare + build** | ❌ | - | - |
| **prepare + build + template** | ❌ | - | - |
| **전체 워크플로우** | ✅ | complete-workflow/ | ⭐⭐⭐ |
| **apply (통합 명령)** | ❌ | - | - |
| **rollback** | ❌ | - | - |
| **state 관리** | ❌ | - | - |

### 고급 기능 시나리오

| 기능 | 예제 존재 | 예제 위치 | 품질 |
|------|----------|-----------|------|
| **의존성 순서** | ✅ | complete-workflow/ | ⭐⭐ |
| **다중 values 파일** | ✅ | k3scode/ | ⭐⭐⭐ |
| **overrides** | ✅ | overrides/advanced-example/ | ⭐⭐⭐ |
| **removes** | ✅ | overrides/advanced-example/ | ⭐⭐⭐ |
| **labels/annotations** | ❌ | - | - |
| **--force 옵션** | ❌ | - | - |
| **--dry-run** | ❌ | - | - |
| **namespace 지정** | ✅ | k3scode/ | ⭐⭐ |
| **kubeconfig/context** | ❌ | - | - |

---

## ❌ 누락된 예제

### 1. 필수 예제 (Priority: High)

#### 1.1 kustomize 타입
- **현황**: 문서에 언급되지만 예제 없음
- **필요성**: product-spec.md에서 지원 명시
- **제안**:
```
examples/kustomize-example/
├── config.yaml
├── kustomization.yaml
├── base/
│   └── deployment.yaml
└── overlays/
    └── production/
        └── kustomization.yaml
```

#### 1.2 git 단독 사용 예제
- **현황**: git은 항상 다른 타입과 함께 사용됨
- **필요성**: Git 리포지토리 직접 배포 시나리오
- **제안**:
```
examples/git-manifests/
├── config.yaml  (type: git)
├── sources.yaml
└── README.md
```

#### 1.3 apply 명령어 예제 (통합 워크플로우)
- **현황**: apply는 v0.3.0의 주요 기능이지만 예제 없음
- **필요성**: 사용자 편의성 향상
- **제안**:
```
examples/apply-workflow/
├── config.yaml
├── sources.yaml
└── README.md  (sbkube apply 사용법)
```

### 2. 권장 예제 (Priority: Medium)

#### 2.1 --force 옵션 사용
- **현황**: v0.4.0 신규 기능이지만 예제 없음
- **필요성**: 새 기능 홍보 및 사용법 안내
- **제안**:
```
examples/force-update/
├── config.yaml
├── sources.yaml
└── README.md  (--force 사용 시나리오)
```

#### 2.2 state 관리 예제
- **현황**: history, rollback 명령어 예제 없음
- **필요성**: 상태 관리 기능 활용
- **제안**:
```
examples/state-management/
├── config.yaml
├── README.md  (state list, history, rollback)
└── scenarios.md
```

#### 2.3 validate 명령어 예제
- **현황**: validate 명령어 사용 예제 없음
- **필요성**: 설정 검증 워크플로우
- **제안**:
```
examples/validation/
├── valid-config.yaml
├── invalid-config.yaml
├── README.md
└── fix-guide.md
```

#### 2.4 다중 환경 예제
- **현황**: dev/staging/prod 환경별 예제 없음
- **필요성**: 실전 시나리오
- **제안**:
```
examples/multi-environment/
├── config.yaml
├── values/
│   ├── dev.yaml
│   ├── staging.yaml
│   └── production.yaml
└── README.md
```

### 3. 고급 예제 (Priority: Low)

#### 3.1 labels/annotations 활용
- **현황**: 메타데이터 관리 예제 없음
- **제안**: overrides/advanced-example에 추가

#### 3.2 kubeconfig/context 전환
- **현황**: 다중 클러스터 관리 예제 없음
- **제안**:
```
examples/multi-cluster/
├── config.yaml
├── README.md  (--kubeconfig, --context 사용법)
└── clusters.md
```

#### 3.3 http 타입 고급 사용
- **현황**: 기본 예제만 존재
- **필요성**: headers, 인증 등 고급 기능
- **제안**: deploy/http-example에 추가

---

## ✅ 잘 만들어진 예제

### 1. complete-workflow/
- **평가**: ⭐⭐⭐⭐⭐ 우수
- **강점**:
  - 전체 워크플로우 완벽 커버
  - 모든 앱 타입 포함 (helm, git, yaml, action, exec)
  - README.md 충실
- **개선점**: 없음

### 2. overrides/advanced-example/
- **평가**: ⭐⭐⭐⭐ 양호
- **강점**:
  - overrides, removes 기능 명확히 설명
  - 실전 시나리오 (커스터마이징)
- **개선점**: labels/annotations 추가

### 3. k3scode/
- **평가**: ⭐⭐⭐⭐ 양호
- **강점**:
  - 실전 배포 시나리오
  - 모듈별 분리 (ai, devops, memory, rdb)
- **개선점**: 통합 README

### 4. deploy/http-example/
- **평가**: ⭐⭐⭐ 보통
- **강점**: README.md 존재
- **개선점**: headers, 인증 예제 추가

---

## 📋 개선이 필요한 예제

### 1. deploy/exec/
- **문제**: README.md 없음
- **개선**:
  - README.md 추가
  - 사용 시나리오 설명
  - 주의사항 (보안, 권한 등)

### 2. deploy/action-example/
- **문제**: 기본 시나리오만
- **개선**:
  - create, delete 타입 예제 추가
  - 실패 처리 예제
  - dry-run 예제

### 3. deploy/yaml-example/
- **문제**: 너무 단순
- **개선**:
  - 다중 YAML 파일 예제
  - namespace 리소스 포함
  - ConfigMap, Secret 예제

### 4. basic/local-chart/
- **문제**: 설명 부족
- **개선**:
  - Chart.yaml, values.yaml 구조 설명
  - 로컬 차트 개발 워크플로우

---

## 📖 문서화 상태

### README.md 존재하는 디렉토리

✅ examples/README.md
✅ examples/basic/README.md
✅ examples/basic/local-chart/README.md
✅ examples/complete-workflow/README.md
✅ examples/deploy/README.md
✅ examples/deploy/http-example/README.md
✅ examples/k3scode/devops/README.md
✅ examples/overrides/advanced-example/README.md

### README.md 누락된 디렉토리

❌ examples/deploy/action-example/
❌ examples/deploy/exec/
❌ examples/deploy/yaml-example/
❌ examples/k3scode/ (통합 README)
❌ examples/k3scode/ai/
❌ examples/k3scode/memory/
❌ examples/k3scode/rdb/

---

## 🎯 우선순위 개선 계획

### Phase 1: 필수 예제 추가 (1-2주)

1. **kustomize 예제 생성**
   - examples/kustomize-example/ 디렉토리
   - 완전한 kustomize 워크플로우
   - README.md 포함

2. **git 단독 예제 생성**
   - examples/git-manifests/ 디렉토리
   - Git 리포지토리 직접 배포
   - sources.yaml 설정 예제

3. **apply 명령어 예제 생성**
   - examples/apply-workflow/ 디렉토리
   - sbkube apply 사용법
   - 모든 옵션 커버

### Phase 2: README 보완 (1주)

1. **누락된 README.md 추가**
   - deploy/action-example/README.md
   - deploy/exec/README.md
   - deploy/yaml-example/README.md
   - k3scode/README.md (통합)

2. **기존 README 개선**
   - basic/local-chart/README.md (구조 설명)
   - k3scode/devops/README.md (시나리오 추가)

### Phase 3: 권장 예제 추가 (2-3주)

1. **--force 옵션 예제**
2. **state 관리 예제**
3. **validate 명령어 예제**
4. **다중 환경 예제**

### Phase 4: 고급 예제 추가 (선택)

1. **multi-cluster 예제**
2. **labels/annotations 예제**
3. **http 고급 사용 예제**

---

## 📊 개선 후 예상 결과

### 현재 커버리지

- **앱 타입**: 7/8 (87.5%) - kustomize 미지원
- **워크플로우**: 1/7 (14.3%)
- **고급 기능**: 4/10 (40%)
- **README 완성도**: 8/16 (50%)

### 개선 후 커버리지

- **앱 타입**: 8/8 (100%)
- **워크플로우**: 5/7 (71.4%)
- **고급 기능**: 8/10 (80%)
- **README 완성도**: 16/20 (80%)

---

## 💡 추가 제안

### 1. examples/ 구조 개선

**현재 구조**:
```
examples/
├── basic/           (기본)
├── complete-workflow/  (통합)
├── deploy/          (배포별)
├── k3scode/         (실전)
└── overrides/       (기능별)
```

**제안 구조**:
```
examples/
├── 01-getting-started/   (basic 이름 변경)
├── 02-app-types/         (타입별 예제)
│   ├── helm/
│   ├── yaml/
│   ├── git/
│   ├── http/
│   ├── kustomize/
│   ├── action/
│   └── exec/
├── 03-workflows/         (워크플로우별)
│   ├── prepare-only/
│   ├── complete/
│   ├── apply/
│   └── rollback/
├── 04-features/          (기능별)
│   ├── overrides/
│   ├── multi-environment/
│   ├── force-update/
│   └── state-management/
└── 05-real-world/        (k3scode 이름 변경)
    ├── microservices/
    ├── data-stack/
    └── ai-stack/
```

### 2. 예제 인덱스 생성

`examples/INDEX.md` 파일:
```markdown
# SBKube 예제 인덱스

## 📚 카테고리별 예제

### 시작하기
- [기본 사용법](01-getting-started/)
- [완전한 워크플로우](03-workflows/complete/)

### 앱 타입별
- [Helm 차트](02-app-types/helm/)
- [YAML 매니페스트](02-app-types/yaml/)
...
```

### 3. 예제 테스트 자동화

각 예제에 `test.sh` 추가:
```bash
#!/bin/bash
# examples/basic/test.sh

set -e

echo "Testing basic example..."
sbkube validate --app-dir .
sbkube prepare --app-dir .
sbkube build --app-dir .
echo "✅ Basic example test passed"
```

---

## 🔍 결론

### 현재 상태: ⭐⭐⭐ 보통

**강점**:
- complete-workflow 예제가 우수함
- 주요 앱 타입 커버
- 실전 예제 (k3scode) 존재

**약점**:
- kustomize 예제 없음
- 워크플로우별 예제 부족
- README 누락 많음
- 신규 기능 (--force, apply) 예제 없음

### 권장 조치

**즉시 (1-2주)**:
1. kustomize 예제 추가
2. git 단독 예제 추가
3. 누락된 README 작성

**단기 (1개월)**:
4. apply, validate, state 예제 추가
5. --force 옵션 예제
6. 다중 환경 예제

**중기 (2-3개월)**:
7. examples 구조 개선
8. 예제 인덱스 생성
9. 테스트 자동화

---

**작성자**: Claude Code
**검토 필요**: examples 디렉토리 실제 사용 패턴 분석
