# 🧩 kube-app-manaer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sbkube)]()
[![Repo](https://img.shields.io/badge/GitHub-kube--app--manaer-blue?logo=github)](https://github.com/ScriptonBasestar/kube-app-manaer)

**kube-app-manaer**는 `yaml`, `Helm`, `git` 리소스를 로커로에서 정의하고 `k3s` 등 Kubernetes 환경에 일관되게 배포할 수 있는 CLI 도구입니다.

> 개발자, DevOps 엔지니어, SaaS 환경 구축을 위한 **u53c8가화된 Helm 배포 관리자**

---

## ✨ 주요 기능

- 로커 YAML 설정 기반 앱 정의 및 분류
- Helm chart / OCI chart / Git chart / 파일 복사 기반 배포
- `prepare → build → template → deploy` 구조
- `exec`, `yaml`, `helm` 기반 설치 명령 지원
- `--dry-run`, `--base-dir`, `--apps` 기반 명령 범위 지원
- `upgrade`, `delete` 명령 분리

---

## 📦 설치

### 🔧 추천 방법 (로컬 개발자용)

```bash
uv pip install sbkube
```

또는 소스 설치:

```bash
git clone https://github.com/ScriptonBasestar/kube-app-manaer.git
cd kube-app-manaer
uv pip install -e .
```

### 🚀 향후 계획
- [ ] PyPI 공개 패키지 (`pip install sbkube`)
- [ ] Homebrew 탭 배포 (`brew install scriptonbasestar/sbkube`)

```bash
git clone https://github.com/ScriptonBasestar/kube-app-manaer.git
cd kube-app-manaer
uv pip install -e .
```

> `Python 3.12+` 환경 권장  
> [uv](https://github.com/astral-sh/uv) 기반 패키지 관리 지원

---

## 📂 디렉토리 구조

```
kube-app-manaer/
├── sbkube/                # CLI 구현
│   ├── cli.py             # main entry
│   ├── commands/          # prepare/build/deploy 등 명령어 정의
│   └── utils/             # 공통 유틸리티
├── samples/k3scode/       # 테스트 config/sources 예제
│   ├── config-memory.yaml
│   ├── sources.yaml
│   └── values/
├── build/                 # build 결과물 저장
├── charts/                # helm pull 다운로드 디렉토리
├── repos/                 # git clone 저장 디렉토리
├── tests/                 # pytest 테스트 코드
└── README.md
```

---

## 🚀 CLI 사용법

### 준비 (Helm repo 추가, Git clone, OCI pull 등)

```bash
sbkube prepare --apps config-memory --base-dir ./samples/k3scode
```

### 빌드 (chart 복사, override, remove 등)

```bash
sbkube build --apps config-memory --base-dir ./samples/k3scode
```

### Helm 템플리트 출력

```bash
sbkube template --apps config-memory --base-dir ./samples/k3scode --output-dir ./rendered
```

### 실제 배포

```bash
sbkube deploy --apps config-memory --base-dir ./samples/k3scode
```

### 리리스 삭제

```bash
sbkube delete --apps config-memory --base-dir ./samples/k3scode
```

### 업그레이드

```bash
sbkube upgrade --apps config-memory --base-dir ./samples/k3scode
```

---

## 🥪 테스트

```bash
pytest tests/
```

또는 예제 config 보기:

```bash
python -m sbkube.cli deploy --apps config-memory --base-dir ./samples/k3scode
```

---

## 📄 설정 파일 예제

### `config-memory.yaml`

```yaml
namespace: default
apps:
  - name: redis
    type: install-helm
    specs:
      repo: bitnami
      chart: redis
      values:
        - redis-values.yaml
  - name: memcached
    type: install-helm
    specs:
      repo: bitnami
      chart: memcached
```

### `sources.yaml`

```yaml
helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
```

---

## 🧙 개발 중 기능

- [ ] hook 실행: `before`, `after`
- [ ] Helm chart test
- [ ] Git repo를 통한 chart 경로 자동 지정 및 지원
- [ ] ArgoCD-like UI

---

## 📄 라이센스

MIT License © [ScriptonBasestar](https://github.com/ScriptonBasestar)

---

## 🤝 기억하기

PR, 이슈, 피드래프 허용합니다!
