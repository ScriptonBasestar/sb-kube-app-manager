# sbkube prepare 명령 예시

`prepare` 명령은 애플리케이션 배포에 필요한 외부 리소스를 로컬 환경에 준비합니다.

## 기본 사용법

```bash
sbkube prepare --app-dir config --sources sources.yaml
```

## 옵션

- `--app-dir`: 앱 설정 디렉토리 (기본값: 현재 디렉토리)
- `--sources`: 소스 저장소 설정 파일 (기본값: sources.yaml)
- `--base-dir`: 프로젝트 루트 디렉토리 (기본값: 현재 디렉토리)

## 설정 파일 예시

### 1. sources.yaml - 외부 리소스 정의

```yaml
# Helm 리포지토리
helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
  prometheus: https://prometheus-community.github.io/helm-charts
  grafana: https://grafana.github.io/helm-charts

# OCI 레지스트리
oci_repos:
  dockerhub:
    nginx: oci://registry-1.docker.io/bitnamicharts/nginx

# Git 리포지토리  
git_repos:
  my-charts:
    url: https://github.com/myorg/helm-charts.git
    branch: main
  
  kustomize-base:
    url: https://github.com/myorg/k8s-base.git
    branch: v1.0.0
```

### 2. config.yaml - 앱 구성

```yaml
namespace: default

apps:
  # Helm 차트 준비
  - name: redis
    type: pull-helm
    specs:
      repo: bitnami
      chart: redis
      chart_version: 17.11.3
      dest: redis-cache

  # OCI 차트 준비
  - name: nginx
    type: pull-helm-oci
    specs:
      repo: dockerhub
      chart: nginx
      dest: nginx-web

  # Git 저장소 준비
  - name: custom-app
    type: pull-git
    specs:
      repo: my-charts
      paths:
        - src: charts/webapp
          dest: webapp
        - src: charts/backend
          dest: backend
```

## 실행 예시

### 1. 전체 리소스 준비

```bash
# 모든 앱의 리소스 준비
sbkube prepare --app-dir config --sources sources.yaml

# 실행 결과:
# ✅ Helm repo 추가: bitnami
# ✅ Helm repo 업데이트: bitnami
# 📥 Helm pull: helm pull bitnami/redis -d charts/bitnami --untar --version 17.11.3
# ✅ Git clone: https://github.com/myorg/helm-charts.git → repos/my-charts
```

### 2. 특정 소스만 사용

```bash
# 개발 환경용 소스 사용
sbkube prepare --sources sources-dev.yaml

# 프로덕션 환경용 소스 사용  
sbkube prepare --sources sources-prod.yaml
```

## 주요 기능

### 1. Helm 차트 다운로드
- 공개 Helm 리포지토리에서 차트 다운로드
- 특정 버전 지정 가능
- 자동으로 압축 해제

### 2. OCI 레지스트리 지원
- Docker Hub, ECR, GCR 등 OCI 호환 레지스트리 지원
- 인증이 필요한 경우 사전에 `docker login` 필요

### 3. Git 저장소 클론
- 지정된 브랜치/태그로 체크아웃
- 기존 저장소가 있으면 pull 수행
- 여러 경로를 선택적으로 사용 가능

## 디렉토리 구조

prepare 실행 후 생성되는 디렉토리 구조:

```
project/
├── charts/           # Helm 차트 저장
│   ├── bitnami/
│   │   └── redis/
│   └── dockerhub/
│       └── nginx/
├── repos/            # Git 저장소
│   └── my-charts/
│       ├── charts/
│       │   ├── webapp/
│       │   └── backend/
│       └── README.md
├── config/
│   └── config.yaml
└── sources.yaml
```

## 문제 해결

### 1. Helm repo 접근 실패
```bash
# 리포지토리 URL 확인
helm repo list

# 수동으로 추가
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 2. Git 인증 오류
```bash
# SSH 키 사용
git_repos:
  private-repo:
    url: git@github.com:myorg/private-charts.git
    branch: main

# 또는 Personal Access Token 사용
git_repos:
  private-repo:
    url: https://TOKEN@github.com/myorg/private-charts.git
    branch: main
```

### 3. 디스크 공간 부족
```bash
# 기존 다운로드 정리
rm -rf charts/ repos/

# 필요한 것만 선택적으로 prepare
sbkube prepare --app-dir specific-app
``` 