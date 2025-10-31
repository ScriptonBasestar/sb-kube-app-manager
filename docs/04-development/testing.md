# 수동테스트

## Prepare kind kube

```bash
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.22.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind


kind create cluster --name sbkube-test
# kind-sbkube-test 이게 생성됨
kubectl config get-contexts
kubectl config current-context
kubectl config use-context kind-sbkube-test

# kind create cluster --name sbkube-test --kubeconfig ~/.kube/test-kubeconfig
```

## CMD

sbkube prepare --app-dir config --source sources.yaml
sbkube build --app-dir config

python -m sbkube.cli

### prepare

```bash
uv run -m sbkube.cli prepare --base-dir examples/k3scode --app-dir memory
uv run -m sbkube.cli prepare --base-dir examples/k3scode --app-dir rdb
uv run -m sbkube.cli prepare --base-dir examples/k3scode --app-dir devops

python -m sbkube.cli prepare \
  --base-dir ./examples/k3scode \
  --apps config-memory.yml

sbkube prepare --base-dir . --app-dir memory
sbkube prepare --app-dir memory
```

### build

```bash
uv run -m sbkube.cli build --base-dir examples/k3scode --app-dir memory
uv run -m sbkube.cli build --base-dir examples/k3scode --app-dir rdb
uv run -m sbkube.cli build --base-dir examples/k3scode --app-dir devops
```

### template

```bash
uv run -m sbkube.cli template --base-dir examples/k3scode --app-dir memory --output-dir rendered/
uv run -m sbkube.cli template --base-dir examples/k3scode --app-dir rdb --output-dir rendered/
```

### deploy

```bash
uv run -m sbkube.cli deploy --base-dir examples/k3scode --app-dir memory --namespace data-memory
uv run -m sbkube.cli deploy --base-dir examples/k3scode --app-dir rdb --namespace data-rdb
```

### upgrade

```bash
# Helm 릴리스 업그레이드 테스트
uv run -m sbkube.cli upgrade --base-dir examples/basic --app-dir . --app-name redis --namespace test

# 전체 앱 업그레이드
uv run -m sbkube.cli upgrade --base-dir examples/k3scode --app-dir memory --namespace data-memory
```

### delete

```bash
# 특정 앱 삭제
uv run -m sbkube.cli delete --base-dir examples/basic --app-dir . --app-name redis --namespace test

# 전체 앱 삭제
uv run -m sbkube.cli delete --base-dir examples/k3scode --app-dir rdb --namespace data-rdb --all
```

### validate

#### sources.yaml 검증

```bash
# Explicit path
sbkube validate sources.yaml

# Using --app-dir with sources.yaml
sbkube validate --config-file sources.yaml
```

#### config.yaml 검증

```bash
# Explicit path (기존 방식)
sbkube validate a000_infra/config.yaml

# Using --app-dir (신규 방식)
sbkube validate --app-dir a000_infra

# 현재 디렉토리 검증
cd a000_infra
sbkube validate
```

#### 스키마 명시

```bash
sbkube validate somefile.yaml --schema-path schemas/custom.schema.json
sbkube validate --app-dir redis --schema-type config
```

## 자동화 테스트 (Automated Testing)

### 테스트 실행 방법

#### 전체 테스트

```bash
# 모든 테스트 실행 (단위 + 통합 + E2E)
make test

# 커버리지 포함 전체 테스트
make test-coverage
```

#### 단위 테스트 (Unit Tests)

```bash
# 모든 단위 테스트 (tests/unit/)
make test-unit

# 빠른 단위 테스트 (E2E 제외, slow 제외)
make test-quick

# E2E 제외 단위 테스트
make test-unit-only
```

#### E2E 테스트 (End-to-End Tests)

```bash
# E2E 테스트만 실행
make test-e2e
```

**참고**: E2E 테스트는 Kubernetes 클러스터와 네트워크 의존성이 필요하므로 로컬 개발 시에는 `make test-quick`을 사용하는 것을 권장합니다.

#### 특정 모듈 테스트

```bash
# 명령어 테스트
make test-commands

# 모델 테스트
make test-models

# State 테스트
make test-state

# Utils 테스트
make test-utils
```

#### 마커 기반 테스트

```bash
# Kubernetes 필요 테스트
make test-k8s

# Helm 필요 테스트
make test-helm

# 빠른 테스트 (slow 제외)
make test-fast
```

### 테스트 구조

```
tests/
├── unit/                 # 단위 테스트
│   ├── commands/        # 명령어 테스트
│   ├── models/          # 모델 검증 테스트
│   ├── state/           # 상태 관리 테스트
│   └── utils/           # 유틸리티 테스트
├── integration/          # 통합 테스트
└── e2e/                  # E2E 테스트 (네트워크/클러스터 필요)
```

### 테스트 마커

- `@pytest.mark.e2e`: E2E 테스트 (느림, 네트워크 필요)
- `@pytest.mark.slow`: 느린 테스트
- `@pytest.mark.requires_k8s`: Kubernetes 클러스터 필요
- `@pytest.mark.requires_helm`: Helm CLI 필요

### 로컬 개발 권장 워크플로우

```bash
# 1. 빠른 피드백 (코드 수정 후)
make test-quick

# 2. 전체 단위 테스트 (커밋 전)
make test-unit

# 3. 전체 테스트 (PR 전)
make test
```

### CI/CD에서의 테스트

```bash
# 린트 + 테스트 + 커버리지
make ci

# 자동 수정 + 테스트
make ci-fix
```

## 수동 테스트 (Manual Testing)

### prepare

pytest tests/test_prepare.py -v

### build

pytest tests/test_build.py -v

overrides/가 적용된 파일이 정상 복사되었는지 검사 removes:로 지정한 파일이 실제 삭제되었는지 확인 pull-git, copy-app 항목에 대한 테스트 분리o

### template

pytest tests/test_template.py -v

### deploy

pytest tests/test_deploy.py -v
