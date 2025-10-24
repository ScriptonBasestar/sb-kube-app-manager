# K3sCode Project - 통합 k3s 클러스터 배포 예제

SBKube를 사용한 실제 k3s 클러스터 배포 예제 모음입니다. 이 디렉토리는 다양한 애플리케이션 카테고리별로 구조화된 실전 배포 설정을 제공합니다.

## 📋 목차

- [프로젝트 개요](#-프로젝트-개요)
- [디렉토리 구조](#-디렉토리-구조)
- [공통 설정](#-공통-설정)
- [사용 시나리오](#-사용-시나리오)
- [의존성 관계](#-의존성-관계)
- [빠른 시작](#-빠른-시작)

---

## 🎯 프로젝트 개요

k3scode는 k3s 클러스터에 배포할 수 있는 다양한 애플리케이션 스택을 카테고리별로 구성한 프로젝트입니다.

### 특징

- **카테고리별 구성**: DevOps, Data, AI/ML 도구를 각각 관리
- **공통 소스 관리**: 모든 카테고리가 `sources.yaml` 공유
- **실전 사용 패턴**: 실제 프로덕션 환경을 고려한 설정 예제
- **다양한 앱 타입**: Helm 차트(원격/로컬), Git 리포지토리 활용

### 지원 카테고리

| 카테고리 | 네임스페이스 | 주요 애플리케이션 |
|---------|-------------|-----------------|
| **devops** | devops | Nexus, ProxyND (로컬 차트) |
| **memory** | data | Redis, Memcached |
| **rdb** | data | PostgreSQL, MariaDB |
| **ai** | toolhive | Toolhive Operator (Git 타입) |

---

## 📁 디렉토리 구조

```
k3scode/
├── sources.yaml              # 공통 소스 정의 (Helm/OCI/Git 리포지토리)
├── devops/                   # DevOps 도구
│   ├── config.yaml          # 네임스페이스: devops
│   ├── proxynd-custom/      # 로컬 Helm 차트
│   └── values/              # Values 파일
├── memory/                   # 인메모리 스토어
│   ├── config.yaml          # 네임스페이스: data
│   └── values/              # Redis, Memcached values
├── rdb/                      # 관계형 데이터베이스
│   └── config.yaml          # 네임스페이스: data
└── ai/                       # AI/ML 도구
    ├── config.yaml          # 네임스페이스: toolhive
    └── values/              # Toolhive values
```

---

## ⚙️ 공통 설정

### sources.yaml

모든 카테고리가 공유하는 리포지토리 정의 파일입니다.

**주요 구성**:

1. **Helm 리포지토리** (60+ 리포지토리):
   ```yaml
   helm_repos:
     bitnami: https://charts.bitnami.com/bitnami
     sonatype: https://sonatype.github.io/helm3-charts/
     prometheus-community: https://prometheus-community.github.io/helm-charts
     # ... 더 많은 리포지토리
   ```

2. **OCI 리포지토리**:
   ```yaml
   oci_repos:
     8gears:
       n8n: oci://8gears.container-registry.com/library/n8n
     gabe565:
       rsshub: oci://ghcr.io/gabe565/charts/rsshub
   ```

3. **Git 리포지토리** (10+ 리포지토리):
   ```yaml
   git_repos:
     stacklok-toolhive:
       url: "https://github.com/stacklok/toolhive.git"
       branch: "main"
     strimzi:
       url: "https://github.com/strimzi/strimzi-kafka-operator.git"
       branch: "release-0.44.x"
   ```

**클러스터 설정**:
```yaml
cluster: tst-cluster
kubeconfig: ~/.kube/tst-cluster
```

---

## 🚀 사용 시나리오

### 시나리오 1: DevOps 도구 전체 배포

```bash
cd examples/k3scode

# 1. 소스 준비 (Helm 리포지토리 추가 등)
sbkube prepare --base-dir . --app-dir devops

# 2. 차트 빌드 (로컬 차트는 복사만)
sbkube build --base-dir . --app-dir devops

# 3. 템플릿 렌더링
sbkube template --base-dir . --app-dir devops --output-dir /tmp/devops

# 4. 배포
sbkube deploy --base-dir . --app-dir devops --namespace devops
```

**결과**:
- `proxynd-custom` Helm 릴리스가 `devops` 네임스페이스에 배포됨
- 로컬 차트 `./devops/proxynd-custom/` 사용

### 시나리오 2: 데이터 레이어 통합 배포

```bash
# Memory + RDB 순차 배포
sbkube deploy --base-dir . --app-dir memory --namespace data
sbkube deploy --base-dir . --app-dir rdb --namespace data
```

**결과**:
- `data` 네임스페이스에 4개 애플리케이션 배포:
  - Redis
  - Memcached
  - PostgreSQL
  - MariaDB

### 시나리오 3: AI/ML 인프라 배포

```bash
# Git 리포지토리 기반 배포
sbkube deploy --base-dir . --app-dir ai --namespace toolhive
```

**결과**:
- Git 리포지토리 클론: `stacklok-toolhive`
- Helm 차트 경로: `deploy/charts/operator`
- `toolhive` 네임스페이스에 Operator 배포

### 시나리오 4: 전체 스택 배포 (통합)

```bash
# 모든 카테고리를 순차적으로 배포
for app_dir in devops memory rdb ai; do
  sbkube apply --base-dir . --app-dir $app_dir
done
```

**결과**:
- 4개 카테고리 모두 배포 완료
- 3개 네임스페이스 생성: `devops`, `data`, `toolhive`

---

## 🔗 의존성 관계

### 네임스페이스 의존성

```
devops (독립)
  └─ proxynd-custom

data
  ├─ memory (독립)
  │   ├─ Redis
  │   └─ Memcached
  └─ rdb (독립)
      ├─ PostgreSQL
      └─ MariaDB

toolhive (독립)
  └─ toolhive-operator
```

### 배포 순서 권장사항

1. **DevOps 인프라**: `devops/` (Nexus, ProxyND)
2. **데이터 레이어**: `memory/`, `rdb/` (병렬 가능)
3. **AI/ML 인프라**: `ai/` (Toolhive)

**이유**:
- DevOps 도구(Nexus, ProxyND)가 다른 애플리케이션의 빌드/배포를 지원할 수 있음
- 데이터 레이어는 독립적이므로 병렬 배포 가능
- AI/ML 인프라는 데이터 레이어에 의존할 수 있음

---

## ⚡ 빠른 시작

### 1. 사전 요구사항

- k3s 클러스터 실행 중
- `~/.kube/tst-cluster` kubeconfig 파일 존재
- Helm v3.x 설치
- SBKube 설치

### 2. 단일 카테고리 배포

```bash
# Memory 스토어만 배포
cd examples/k3scode
sbkube apply --base-dir . --app-dir memory
```

### 3. 배포 상태 확인

```bash
# Helm 릴리스 확인
helm list -n data

# Pod 상태 확인
kubectl get pods -n data

# SBKube 상태 확인
sbkube state list
sbkube state history --namespace data
```

### 4. 롤백

```bash
# 특정 배포 롤백
sbkube rollback --namespace data --app redis --revision 1
```

---

## 📝 각 카테고리 상세 정보

각 카테고리별 상세 사용법은 하위 디렉토리의 README.md를 참조하세요:

- **[devops/README.md](devops/README.md)** - DevOps 도구 배포 (Nexus, ProxyND)
- **[memory/README.md](memory/README.md)** - 인메모리 스토어 배포 (Redis, Memcached)
- **[rdb/README.md](rdb/README.md)** - 관계형 데이터베이스 배포 (PostgreSQL, MariaDB)
- **[ai/README.md](ai/README.md)** - AI/ML 인프라 배포 (Toolhive)

---

## 🔧 트러블슈팅

### 문제 1: Helm 리포지토리 추가 실패

**증상**:
```
Error: failed to add Helm repository
```

**해결**:
```bash
# 수동으로 리포지토리 추가
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# 또는 prepare 재실행
sbkube prepare --base-dir . --app-dir memory
```

### 문제 2: Git 리포지토리 클론 실패

**증상**:
```
Error: failed to clone git repository
```

**해결**:
```bash
# Git 인증 설정 확인
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# 또는 수동 클론
cd repos/
git clone https://github.com/stacklok/toolhive.git stacklok-toolhive
```

### 문제 3: 네임스페이스 충돌

**증상**:
```
Error: namespace "data" already exists
```

**해결**:
```bash
# 기존 리소스 확인
kubectl get all -n data

# 기존 배포 삭제 후 재배포
sbkube delete --base-dir . --app-dir memory --namespace data
sbkube apply --base-dir . --app-dir memory
```

---

## 📚 참고 자료

- [SBKube 명령어 참조](../../docs/02-features/commands.md)
- [애플리케이션 타입 가이드](../../docs/02-features/application-types.md)
- [설정 파일 스키마](../../docs/03-configuration/config-schema.md)
- [sources.yaml 작성 가이드](../../docs/03-configuration/sources-yaml.md)

---

**💡 팁**: 각 카테고리를 독립적으로 관리하면서도 공통 소스(`sources.yaml`)를 공유하여 일관성을 유지할 수 있습니다.
