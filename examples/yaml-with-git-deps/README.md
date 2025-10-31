# YAML 타입 앱의 Git 리포지토리 파일 참조 예제

이 예제는 YAML 타입 앱이 Git 리포지토리 내부의 파일을 참조하는 방법을 보여줍니다.

## 시나리오

OLM(Operator Lifecycle Manager)을 설치합니다:

1. **olm** 앱: Git 리포지토리를 `.sbkube/repos/olm`에 클론
2. **olm-operator** 앱: 클론된 리포지토리의 YAML 파일을 `kubectl apply`로 배포

## 주요 기능

### `${repos.app-name}` 변수 치환

```yaml
olm-operator:
  type: yaml
  manifests:
    - ${repos.olm}/deploy/upstream/quickstart/crds.yaml
    - ${repos.olm}/deploy/upstream/quickstart/olm.yaml
  depends_on:
    - olm
```

- **변수**: `${repos.olm}`
- **확장 결과**: `.sbkube/repos/olm`
- **최종 경로**: `.sbkube/repos/olm/deploy/upstream/quickstart/crds.yaml`

### 장점

기존 상대경로 방식:
```yaml
manifests:
  - ../repos/olm/deploy/upstream/quickstart/crds.yaml  # 취약함
```

새로운 변수 방식:
```yaml
manifests:
  - ${repos.olm}/deploy/upstream/quickstart/crds.yaml  # 명시적이고 안전함
```

**비교**:

| 방식 | 상대경로 | 변수 치환 |
|------|----------|-----------|
| **가독성** | ❌ 경로 복잡 | ✅ 의도 명확 |
| **안전성** | ❌ 쉽게 깨짐 | ✅ 검증됨 |
| **유지보수** | ❌ 어려움 | ✅ 쉬움 |

## 사용 방법

### 1. 소스 준비 (prepare)

Git 리포지토리를 클론합니다:

```bash
sbkube prepare --app-dir examples/yaml-with-git-deps
```

**결과**:
```
.sbkube/repos/olm/  (Git 리포지토리 클론됨)
├── deploy/
│   └── upstream/
│       └── quickstart/
│           ├── crds.yaml
│           └── olm.yaml
└── ...
```

### 2. 배포 (deploy)

변수가 확장되어 YAML 파일이 배포됩니다:

```bash
sbkube deploy --app-dir examples/yaml-with-git-deps --namespace infra
```

**실행 과정**:

1. `olm` 앱 건너뜀 (git 타입은 배포 대상 아님)
2. `olm-operator` 앱 배포:
   - `${repos.olm}` → `.sbkube/repos/olm` 확장
   - `kubectl apply -f .sbkube/repos/olm/deploy/upstream/quickstart/crds.yaml`
   - `kubectl apply -f .sbkube/repos/olm/deploy/upstream/quickstart/olm.yaml`

### 3. 통합 실행 (apply)

모든 단계를 한 번에 실행:

```bash
sbkube apply --app-dir examples/yaml-with-git-deps --namespace infra
```

## 검증

변수 구문 검증은 설정 로드 시 자동으로 수행됩니다:

```bash
sbkube validate --app-dir examples/yaml-with-git-deps
```

**검증 항목**:

- ✅ 변수 구문 올바른지 (`${repos.app-name}` 형식)
- ✅ 참조된 앱(`olm`)이 존재하는지
- ✅ 참조된 앱이 `git` 타입인지
- ✅ 의존성(`depends_on`)이 올바른지

## 요구사항

- SBKube v0.6.0+
- Git
- kubectl (Kubernetes 클러스터 접근)

## 참고

### 하위 호환성

기존 상대경로 방식도 계속 작동합니다:

```yaml
manifests:
  - ../repos/olm/deploy/upstream/quickstart/crds.yaml
```

하지만 새 프로젝트에서는 변수 치환 방식을 권장합니다.

### 여러 Git 리포지토리 참조

한 YAML 앱이 여러 Git 리포지토리를 참조할 수 있습니다:

```yaml
apps:
  combined:
    type: yaml
    manifests:
      - ${repos.repo1}/file1.yaml
      - ${repos.repo2}/file2.yaml
      - manifests/local-file.yaml  # 로컬 파일과 혼합 가능
    depends_on:
      - repo1
      - repo2
```
