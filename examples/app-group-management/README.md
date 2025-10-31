# App-Group Management Example

이 예제는 SBKube의 App-Group 기반 애플리케이션 관리 기능을 시연합니다 (Phase 1-7).

## 개요

3개의 app-group으로 구성된 마이크로서비스 애플리케이션:

1. **app_000_infra_network** - 네트워크 인프라 (Cilium)
2. **app_010_data_postgresql** - 데이터 스토리지 (CloudNativePG)
3. **app_020_app_backend** - 백엔드 애플리케이션

## 의존성 구조

```
app_000_infra_network (root)
└── app_010_data_postgresql
    └── app_020_app_backend
```

## 파일 구조

```
app-group-management/
├── README.md                 # 이 파일
├── sources.yaml              # 외부 소스 정의
├── config.yaml               # 애플리케이션 정의
├── values/                   # Helm values 파일
│   ├── cilium.yaml
│   ├── postgresql.yaml
│   └── backend.yaml
├── test-status.sh            # status 명령어 시연
└── test-history.sh           # history 명령어 시연
```

## 빠른 시작

### 1. 배포

```bash
# 전체 배포
sbkube apply --app-dir . --namespace demo

# 또는 단계별
sbkube prepare --app-dir .
sbkube build --app-dir .
sbkube template --app-dir . --output-dir /tmp/rendered
sbkube deploy --app-dir . --namespace demo
```

### 2. 상태 확인

```bash
# 기본 상태 요약
sbkube status

# App-group별 그룹핑
sbkube status --by-group

# 특정 app-group 상세
sbkube status app_010_data_postgresql

# 의존성 트리 시각화
sbkube status --deps

# Pod 헬스체크
sbkube status --health-check
```

### 3. 히스토리 및 비교

```bash
# 배포 히스토리
sbkube history

# App-group별 히스토리
sbkube history app_010_data_postgresql

# 두 배포 비교
sbkube history --diff dep_old,dep_new

# Helm values 비교
sbkube history --values-diff dep_old,dep_new
```

### 4. 롤백

```bash
# 롤백 가능한 배포 목록
sbkube rollback --list

# 롤백 계획 확인
sbkube rollback dep_previous --dry-run

# 실제 롤백
sbkube rollback dep_previous
```

## Phase별 기능 시연

### Phase 1-2: 기본 명령어 및 App-Group 추적

```bash
# 새 명령어 사용
sbkube status
sbkube history
sbkube rollback --list
```

### Phase 4: App-Group 그룹핑

```bash
# 그룹별 표시
sbkube status --by-group

# 특정 그룹 상세
sbkube status app_010_data_postgresql

# 관리 앱만 표시
sbkube status --managed

# 문제있는 리소스만
sbkube status --unhealthy
```

### Phase 5: History 개선

```bash
# App-group 필터링
sbkube history app_000_infra_network

# 배포 비교
sbkube history --diff dep_123,dep_456

# Helm values 비교
sbkube history --values-diff dep_123,dep_456
```

### Phase 6: Dependency Tree

```bash
# 의존성 트리 표시
sbkube status --deps

# 특정 그룹의 의존성
sbkube status app_020_app_backend --deps
```

### Phase 7: Health Check

```bash
# Pod 헬스체크 상세
sbkube status --health-check

# 그룹핑 + 헬스체크
sbkube status --by-group --health-check
```

## 실전 시나리오

### 시나리오 1: 새 환경 구축

```bash
# 1. 초기화
sbkube init

# 2. 설정 검증
sbkube validate --app-dir .

# 3. 배포
sbkube apply --app-dir . --namespace demo

# 4. 상태 확인
sbkube status --by-group
sbkube status --deps
```

### 시나리오 2: 문제 해결

```bash
# 1. 문제있는 리소스 확인
sbkube status --unhealthy

# 2. 특정 그룹 헬스체크
sbkube status app_020_app_backend --health-check

# 3. 최근 변경사항 확인
sbkube history --limit 5

# 4. 이전 버전과 비교
sbkube history --diff dep_current,dep_previous

# 5. 필요시 롤백
sbkube rollback dep_previous
```

### 시나리오 3: 업그레이드

```bash
# 1. 현재 상태 기록
sbkube history --show current > /tmp/before.txt

# 2. 설정 변경 후 배포
sbkube apply --app-dir . --namespace demo

# 3. 변경사항 비교
sbkube history --diff dep_before,dep_after

# 4. Helm values 변경사항 확인
sbkube history --values-diff dep_before,dep_after
```

## 자동화 스크립트

### test-status.sh

모든 status 명령어 옵션을 시연하는 스크립트

```bash
./test-status.sh
```

### test-history.sh

History 및 비교 기능을 시연하는 스크립트

```bash
./test-history.sh
```

## 예상 출력

### Status --by-group

```
Managed App-Groups

  app_000_infra_network (1 app)
    ✅ cilium (deployed, rev: 1)

  app_010_data_postgresql (1 app)
    ✅ cloudnative-pg (deployed, rev: 1)

  app_020_app_backend (1 app)
    ✅ backend (deployed, rev: 1)
```

### Status --deps

```
🔗 Dependency Tree

📦 Applications
├── app_000_infra_network (no deps)
├── app_010_data_postgresql → 1 deps
│   └── app_000_infra_network
└── app_020_app_backend → 1 deps
    └── app_010_data_postgresql

Total: 3 apps, 2 with dependencies
```

### Status --health-check

```
💊 Health Check Details

Namespace: demo
┌─────────────────┬─────────┬───────┬──────────┬────────────┐
│ Pod             │ Phase   │ Ready │ Restarts │ Health     │
├─────────────────┼─────────┼───────┼──────────┼────────────┤
│ cilium-abc123   │ Running │ 1/1   │ 0        │ ✅ Healthy │
│ postgres-0      │ Running │ 1/1   │ 0        │ ✅ Healthy │
│ backend-xyz789  │ Running │ 1/1   │ 0        │ ✅ Healthy │
└─────────────────┴─────────┴───────┴──────────┴────────────┘
```

## 정리

```bash
# 리소스 삭제
sbkube delete --app-dir . --namespace demo

# 확인
sbkube status
```

## 참고

- [CHANGELOG.md](../../CHANGELOG.md) - Phase 1-7 상세 내역
- [docs/02-features/commands.md](../../docs/02-features/commands.md) - 명령어 상세 가이드
- [README.md](../../README.md) - 프로젝트 개요
