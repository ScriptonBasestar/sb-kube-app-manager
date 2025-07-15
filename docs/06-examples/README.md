# 📖 SBKube 사용 예제

SBKube를 활용한 다양한 배포 시나리오와 실제 사용 예제를 제공합니다.

______________________________________________________________________

## 🎯 예제 구성

### 📁 examples/ 디렉토리 구조

```
examples/
├── README.md                    # 이 파일
├── complete-workflow/           # 🔄 전체 워크플로우 예제
├── prepare/                     # 📦 소스 준비 예제
├── deploy/                      # 🚀 배포 예제
├── template/                    # 📄 템플릿 예제
├── upgrade/                     # ⬆️ 업그레이드 예제
├── delete/                      # 🗑️ 삭제 예제
└── k3scode/                     # 🎮 실제 운영 환경 예제
```

### 🎓 난이도별 분류

- **🟢 초급**: 기본적인 단일 앱 배포
- **🟡 중급**: 여러 앱과 의존성 관리
- **🔴 고급**: 복잡한 워크플로우와 커스텀 스크립트

______________________________________________________________________

## 🚀 빠른 시작 예제

### 1. Hello World 배포 (🟢 초급)

가장 간단한 YAML 매니페스트 배포 예제입니다.

```bash
# 예제 디렉토리로 이동
cd examples/deploy/install-yaml

# 설정 파일 확인
cat config.yaml
```

```yaml
# config.yaml
namespace: default

apps:
  - name: nginx-simple
    type: install-yaml
    specs:
      actions:
        - type: apply
          path: manifests/nginx-deployment.yaml
        - type: apply
          path: manifests/nginx-service.yaml
```

```bash
# 배포 실행
sbkube build
sbkube deploy
```

### 2. Helm 차트 배포 (🟡 중급)

Helm 차트를 사용한 배포 예제입니다.

```bash
# 예제 디렉토리로 이동  
cd examples/complete-workflow

# 전체 워크플로우 실행
sbkube prepare    # Helm 차트 다운로드
sbkube build      # 앱 빌드
sbkube template   # 템플릿 미리보기
sbkube deploy     # 실제 배포
```

______________________________________________________________________

## 📦 소스 준비 예제

### Helm 저장소 차트 준비

```bash
cd examples/prepare/pull-helm-oci

# OCI 레지스트리에서 Helm 차트 가져오기
sbkube prepare
```

설정 예제:

```yaml
# sources.yaml
helm_repos:
  argo: https://argoproj.github.io/argo-helm

# config.yaml  
apps:
  - name: argocd-source
    type: pull-helm-oci
    specs:
      repo: ghcr.io/argoproj/argo-helm
      chart: argo-cd
      dest: argocd
```

______________________________________________________________________

## 🔄 완전한 워크플로우 예제

### 멀티 앱 배포 시나리오 (🟡 중급)

실제 운영 환경에서 사용하는 복합적인 배포 예제입니다.

```bash
cd examples/complete-workflow
```

#### 프로젝트 구조

```
complete-workflow/
├── sources.yaml          # 외부 소스 정의
├── config.yaml          # 앱 설정
├── values/              # Helm values 파일들
│   ├── nginx-values.yaml
│   └── monitoring-values.yaml
└── manifests/           # 추가 YAML 매니페스트
    └── namespace.yaml
```

#### 워크플로우 실행

```bash
# 1. 설정 검증
sbkube validate

# 2. 외부 소스 준비
sbkube prepare

# 3. 앱 빌드
sbkube build

# 4. 템플릿 렌더링 (미리보기)
sbkube template --output-dir rendered

# 5. Dry-run 테스트
sbkube deploy --dry-run

# 6. 실제 배포
sbkube deploy
```

______________________________________________________________________

## 🎮 실제 운영 환경 예제 (k3scode)

### K3s 클러스터 운영 예제 (🔴 고급)

실제 운영 중인 K3s 클러스터의 배포 설정입니다.

```bash
cd examples/k3scode
```

#### 환경별 구성

```
k3scode/
├── sources.yaml           # 공통 소스 정의
├── ai/                   # AI 도구 환경
│   ├── config.yaml
│   └── values/
├── devops/               # DevOps 도구 환경  
│   ├── config.yaml
│   ├── values/
│   └── proxynd-custom/   # 커스텀 Helm 차트
├── memory/               # 메모리 저장소 환경
│   ├── config.yml
│   └── values/
└── rdb/                  # 데이터베이스 환경
    └── config.yaml
```

#### AI 도구 스택 배포

```bash
# AI 환경 배포
sbkube --app-dir ai prepare
sbkube --app-dir ai build  
sbkube --app-dir ai deploy --namespace toolhive
```

#### DevOps 도구 스택 배포

```bash
# DevOps 환경 배포 (커스텀 차트 포함)
sbkube --app-dir devops prepare
sbkube --app-dir devops build
sbkube --app-dir devops deploy --namespace devops
```

______________________________________________________________________

## 🛠️ 고급 사용 패턴

### 1. 커스텀 액션 스크립트 (🔴 고급)

```bash
cd examples/deploy/install-action
```

```yaml
# config.yaml
apps:
  - name: custom-setup
    type: install-action
    specs:
      actions:
        - type: apply
          path: setup-script.sh
    uninstall:
      script: cleanup-script.sh
```

### 2. Git 소스 통합 배포 (🟡 중급)

```yaml
# 복잡한 Git 통합 예제
apps:
  # 1단계: Git에서 소스 가져오기
  - name: fetch-helm-charts
    type: pull-git
    specs:
      repo: company-charts
      paths:
        - src: charts/backend
          dest: backend-chart
        - src: charts/frontend  
          dest: frontend-chart
          
  # 2단계: 백엔드 배포
  - name: backend-app
    type: install-helm
    specs:
      path: backend-chart
      values: [backend-values.yaml]
    namespace: backend
    
  # 3단계: 프론트엔드 배포  
  - name: frontend-app
    type: install-helm
    specs:
      path: frontend-chart
      values: [frontend-values.yaml]
    namespace: frontend
```

### 3. 환경별 배포 전략

```bash
# 개발 환경
sbkube --app-dir environments/dev --namespace dev-apps deploy

# 스테이징 환경
sbkube --app-dir environments/staging --namespace staging-apps deploy

# 프로덕션 환경 (수동 승인 후)
sbkube --app-dir environments/prod --namespace prod-apps deploy
```

______________________________________________________________________

## 🔍 상태 관리 예제

### 배포 상태 추적

```bash
# 현재 배포 상태 확인
sbkube state list

# 특정 클러스터 상태
sbkube state list --cluster production

# 배포 히스토리 조회
sbkube state history --app nginx-app

# 롤백 실행
sbkube state rollback --deployment-id <deployment-id>
```

______________________________________________________________________

## 🎯 실용적인 사용 팁

### 1. 개발 워크플로우 최적화

```bash
# 특정 앱만 빠르게 테스트
sbkube build --app my-app
sbkube deploy --app my-app --dry-run
sbkube deploy --app my-app

# 설정 변경 후 빠른 재배포
sbkube validate && sbkube deploy --app my-app
```

### 2. 디버깅 및 트러블슈팅

```bash
# 상세 로그로 디버깅
sbkube --verbose deploy

# 템플릿 결과 확인
sbkube template --output-dir debug-output
cat debug-output/*/manifests.yaml

# 설정 검증
sbkube validate --config-file problematic-config.yaml
```

### 3. CI/CD 통합

```bash
# 파이프라인에서 사용
#!/bin/bash
set -e

echo "Validating configuration..."
sbkube validate

echo "Preparing sources..."
sbkube prepare

echo "Building applications..."
sbkube build

echo "Dry-run deployment..."
sbkube deploy --dry-run

echo "Deploying to ${ENVIRONMENT}..."
sbkube --namespace ${ENVIRONMENT} deploy

echo "Checking deployment status..."
sbkube state list --cluster ${CLUSTER_NAME}
```

______________________________________________________________________

## 📚 추가 학습 자료

### 관련 문서

- **[명령어 가이드](../02-features/commands.md)** - 각 명령어 상세 사용법
- **[앱 타입 가이드](../02-features/application-types.md)** - 10가지 앱 타입 완전 가이드
- **[설정 가이드](../03-configuration/)** - 설정 파일 작성법

### 실습 가이드

1. **[기본 워크플로우](basic-workflow.md)** - 단계별 실습
1. **[Helm 배포](helm-deployment.md)** - Helm 차트 배포 마스터
1. **[YAML 배포](yaml-deployment.md)** - 직접 매니페스트 배포
1. **[Git 통합](git-integration.md)** - Git 소스 활용법

### 문제 해결

- **[일반적인 문제들](../07-troubleshooting/common-issues.md)**
- **[FAQ](../07-troubleshooting/faq.md)**

______________________________________________________________________

## 🤝 커뮤니티 예제 기여

새로운 예제를 기여하고 싶으시다면:

1. **[기여 가이드](../04-development/contributing.md)** 확인
1. `examples/` 디렉토리에 새 예제 추가
1. README.md 및 설명 문서 작성
1. Pull Request 제출

______________________________________________________________________

*예제에 대한 질문이나 개선 제안이 있으시면 [이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)에 알려주세요!*
