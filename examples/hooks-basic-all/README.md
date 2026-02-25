# Hooks 기본 - 모든 타입 종합 예제

> **목적**: 모든 Hook 타입을 한눈에 보여주는 종합 예제
> **Phase**: 기본 Shell + Phase 1 Manifests + Phase 2 Tasks
> **난이도**: ⭐ 입문

## 📚 이 예제에서 배울 수 있는 것

- ✅ **Command-Level Hooks**: 전역 훅 (deploy.pre, deploy.post)
- ✅ **App-Level Shell Hooks**: 앱별 훅 (pre_deploy, post_deploy)
- ✅ **Phase 1 Manifests**: YAML 파일 자동 배포
- ✅ **Phase 2 Tasks**: manifests/inline/command 타입
- ✅ **네이밍 컨벤션**: 하이픈 vs 언더스코어 사용법

## 🏗️ 구조

```
hooks-basic-all/
├── README.md                    # 이 파일
├── sbkube.yaml                  # 모든 Hook 타입 포함
└── manifests/
    ├── configmap-phase1.yaml    # Phase 1용 ConfigMap
    └── configmap-phase2.yaml    # Phase 2용 ConfigMap
```

## 🎯 실행 방법

### 1. Dry-run으로 확인

```bash
sbkube deploy --app-dir examples/hooks-basic-all --dry-run
```

### 2. 실제 배포

```bash
# 테스트 네임스페이스 생성
kubectl create namespace hooks-test

# 배포 실행
sbkube deploy --app-dir examples/hooks-basic-all --namespace hooks-test
```

### 3. 결과 확인

```bash
# ConfigMap 확인 (Phase 1 Manifests로 생성)
kubectl get configmap -n hooks-test basic-phase1-cm

# ConfigMap 확인 (Phase 2 Manifests Task로 생성)
kubectl get configmap -n hooks-test basic-phase2-cm

# ConfigMap 확인 (Phase 2 Inline Task로 생성)
kubectl get configmap -n hooks-test basic-inline-cm
```

### 4. 정리

```bash
kubectl delete namespace hooks-test
```

## 📖 Hook 실행 순서

### 전체 플로우

```
1. Command-Level Pre Hook
   └─ "Starting deployment for ALL apps"

2. Redis App
   A. pre_deploy (Shell)
      └─ "Redis: App-level pre-deploy hook"

   B. pre_deploy_manifests (Phase 1)
      └─ manifests/configmap-phase1.yaml 배포

   C. ── MAIN DEPLOYMENT (Redis Helm Chart) ──

   D. post_deploy_manifests (Phase 1)
      └─ (없음)

   E. post_deploy (Shell)
      └─ "Redis: App-level post-deploy hook"

   F. post_deploy_tasks (Phase 2)
      └─ Task 1: manifests → configmap-phase2.yaml 배포
      └─ Task 2: inline → ConfigMap 인라인 생성
      └─ Task 3: command → Echo 명령어 실행

3. Command-Level Post Hook
   └─ "Deployment completed for ALL apps"
```

## 🔍 sbkube.yaml 상세 설명

### Command-Level Hooks (객체 표기법)

```yaml
hooks:
  deploy:
    pre: ["echo 'Starting deployment'"]  # 전역 pre hook
    post: ["echo 'Completed'"]           # 전역 post hook
```

**특징**:
- YAML 객체 표기법 사용 (점 표기법 아님)
- 모든 앱 배포에 적용
- 알림, 로깅, 전역 설정에 유용

### App-Level Shell Hooks (언더스코어)

```yaml
apps:
  - name: redis
    hooks:
      pre_deploy: ["echo 'App pre-deploy'"]   # snake_case
      post_deploy: ["echo 'App post-deploy'"] # snake_case
```

**특징**:
- `snake_case` (언더스코어) 사용
- 특정 앱에만 적용
- 간단한 Shell 명령어 실행

### Phase 1: Manifests (언더스코어)

```yaml
hooks:
  pre_deploy_manifests:  # snake_case
    - path: manifests/configmap-phase1.yaml
```

**특징**:
- SBKube가 자동으로 `kubectl apply` 실행
- 파일 경로만 지정하면 됨
- Phase 2보다 간단하지만 기능 제한적

### Phase 2: Tasks (언더스코어 + 타입 구조화)

```yaml
hooks:
  post_deploy_tasks:  # snake_case
    - type: manifests  # 소문자 문자열
      name: deploy-phase2-cm
      paths: ["manifests/configmap-phase2.yaml"]

    - type: inline
      name: create-inline-cm
      yaml: |
        apiVersion: v1
        kind: ConfigMap
        ...

    - type: command
      name: verify-deployment
      command: ["echo", "Verification complete"]
```

**특징**:
- 타입별 작업 구조화 (`manifests`, `inline`, `command`)
- Task 이름으로 명확한 식별
- Inline YAML 지원
- 더 강력한 기능 (retry, validation 등)

## 🎓 학습 포인트

### 1. 네이밍 컨벤션 차이

| Hook 레벨 | 네이밍 | 예시 |
|-----------|--------|------|
| Command-Level | 객체 표기법 | `hooks.deploy.pre` |
| App-Level | `snake_case` | `pre_deploy`, `post_deploy_tasks` |
| Task Type | 소문자 문자열 | `"manifests"`, `"inline"`, `"command"` |

### 2. Phase 1 vs Phase 2

| 항목 | Phase 1 Manifests | Phase 2 Tasks |
|------|------------------|--------------|
| YAML 파일 배포 | ✅ | ✅ |
| Inline YAML | ❌ | ✅ |
| Shell 명령어 | ❌ | ✅ |
| 타입 구조화 | ❌ | ✅ |
| Retry 지원 | ❌ | ✅ |
| Validation | ❌ | ✅ (Phase 3) |

**권장 사항**:
- 간단한 YAML 파일 배포: Phase 1
- 복잡한 워크플로우: Phase 2
- 검증 필요: Phase 3

### 3. 실행 순서 이해

```
Command pre → App pre → Phase 1 pre → MAIN → Phase 1 post → App post → Phase 2 post → Command post
```

## 🔗 다음 단계

### 더 알아보기

- **[Hooks Guide & Reference](../../docs/02-features/hooks-guide.md)** - 전체 Hook 타입, 환경 변수, Best Practices

### 다른 예제

- **[hooks-pre-deploy-tasks/](../hooks-pre-deploy-tasks/)** - 배포 전 검증
- **[hooks-command-level/](../hooks-command-level/)** - 전역 알림 및 로깅
- **[hooks-error-handling/](../hooks-error-handling/)** - 에러 처리 및 롤백
- **[hooks-phase3/](../hooks-phase3/)** - Validation/Dependency/Rollback
- **[hooks-hookapp-simple/](../hooks-hookapp-simple/)** - HookApp 입문

## ❓ FAQ

### Q1. Command-Level vs App-Level 언제 사용하나요?

**Command-Level**:
- 모든 앱에 공통 적용 (알림, 로깅)
- 전역 환경 설정

**App-Level**:
- 특정 앱에만 필요한 작업
- 앱별 검증, 백업

### Q2. Phase 1 vs Phase 2 어떻게 선택하나요?

**Phase 1** (`*_manifests`):
- YAML 파일만 배포
- 간단한 사용 사례
- 빠른 설정

**Phase 2** (`*_tasks`):
- YAML + Shell 명령어 혼합
- Inline YAML 필요
- Retry/Validation 필요

### Q3. 왜 하이픈과 언더스코어가 혼재되어 있나요?

**역사적 이유**:
- Command-Level: YAML 객체 구조 (`deploy.pre`)
- App-Level: Python 변수명 규칙 (`pre_deploy`)

**규칙**:
- Command-Level: 객체 표기법
- App-Level: `snake_case` (언더스코어)
- Task Type: 소문자 문자열

---

**피드백**: [GitHub Issues](https://github.com/archmagece/sbkube/issues)
