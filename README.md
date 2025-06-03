# 🧩 kube-app-manaer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sbkube)]()
[![Repo](https://img.shields.io/badge/GitHub-kube--app--manaer-blue?logo=github)](https://github.com/ScriptonBasestar/kube-app-manaer)

**kube-app-manaer**는 `yaml`, `Helm`, `git` 리소스를 로커로에서 정의하고 `k3s` 등 Kubernetes 환경에 일관되게 배포할 수 있는 CLI 도구입니다.

> 개발자, DevOps 엔지니어, SaaS 환경 구축을 위한 **u53c8가화된 Helm 배포 관리자**

---

## 🔮 Anticipated Usage

`kube-app-manaer`는 [ScriptonBasestar](https://github.com/ScriptonBasestar)가 운영하는 **웹호스팅 / 서버호스팅 기반 DevOps 인프라**에서 실무적으로 활용되며, 다음과 같은 용도로 발전될 예정입니다:

- 내부 SaaS 플랫폼의 Helm 기반 배포 자동화
- 사용자 정의 YAML 템플릿과 Git 소스 통합 배포
- 오픈소스 DevOps 도구 및 라이브러리의 테스트 베드
- 향후 여러 배포 도구(`sbkube`, `sbproxy`, `sbrelease` 등)의 공통 기반

`sbkube`는 ScriptonBasestar의 전체 인프라 자동화 계획의 핵심 도구로, 점차 라이브러리 및 CLI 도구 형태로 오픈소스 커뮤니티에 공개될 예정입니다.

---

## ✨ 주요 기능

- 로커 YAML 설정 기반 앱 정의 및 분류
- Helm chart / OCI chart / Git chart / 파일 복사 기반 배포
- `prepare → build → template → deploy` 구조
- `exec`, `yaml`, `helm` 기반 설치 명령 지원
- `--dry-run`, `--base-dir`, `--app-dir` 기반 명령 범위 지원
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

## ⚙️ GitHub Actions 배포 자동화

`sbkube`는 PyPI로 자동 배포되도록 [GitHub Actions](https://docs.github.com/en/actions) CI 워크플로를 제공합니다.

`.github/workflows/publish.yml` 예시:

```yaml
ame: Publish to PyPI

on:
  push:
    tags:
      - "v*"

permissions:
  id-token: write
  contents: read

jobs:
  publish:
    name: Build and publish to PyPI
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        uses: yezz123/setup-uv@v4

      - name: Build wheel
        run: uv build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

### 🔐 설정 방법

1. [PyPI API 토큰 생성](https://pypi.org/manage/account/token/)
2. GitHub 저장소 → Settings → Secrets → Actions → `PYPI_API_TOKEN` 추가
3. 태그 푸시 시 자동 배포:

```bash
git tag v0.1.0
git push origin v0.1.0
```

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

## 🚀 CLI 일반 사용법

### 0. Kubernetes 설정 확인 (선택 사항)
`sbkube`를 인수 없이 실행하여 현재 kubeconfig 설정 및 사용 가능한 컨텍스트를 확인합니다.
이 정보는 `python-kubernetes` 라이브러리를 통해 `~/.kube/config` (또는 `KUBECONFIG` 환경 변수 경로)에서 읽어옵니다.

```bash
sbkube
```
결과를 보고 필요시 `kubectl config use-context <context_name>`으로 활성 컨텍스트를 변경하거나, `sbkube` 명령어 실행 시 전역 옵션을 사용합니다.

### 전역 옵션
모든 `sbkube` 명령어는 다음과 같은 전역 옵션을 지원하여 실행 환경을 제어할 수 있습니다:
*   `--kubeconfig FILE_PATH`: 사용할 kubeconfig 파일 경로를 지정합니다. (기본값: `KUBECONFIG` 환경 변수 또는 `~/.kube/config`)
*   `--context CONTEXT_NAME`: 사용할 Kubernetes 컨텍스트 이름을 지정합니다. (기본값: 현재 활성 컨텍스트)
*   `-v`, `--verbose`: 상세 로깅을 활성화하여 더 많은 내부 처리 과정을 보여줍니다.

예시:
```bash
sbkube --kubeconfig /path/to/my.config --context staging-cluster deploy --app my-app
```

### 일반적인 배포 워크플로우

다음은 `sbkube`를 사용한 일반적인 애플리케이션 배포 단계입니다.

1.  **소스 준비 (`prepare`)**:
    애플리케이션 배포에 필요한 외부 소스(Helm 저장소, Git 저장소, Helm 차트)를 로컬 환경에 준비합니다.
    *   **대상**: `config.[yaml|toml]` 파일 내 `pull-helm`, `pull-helm-oci`, `pull-git` 타입 앱.
    *   **설정**: `<base_dir>/<app_dir>/sources.[yaml|toml]` 파일의 소스 정의 참조.
    *   **작업**: Helm 저장소 추가/업데이트, Git 저장소 클론/업데이트, Helm 차트 다운로드.
    *   **결과물**:
        *   Helm 차트: `<base_dir>/charts/<chart_name_or_dest>/`
        *   Git 저장소: `<base_dir>/repos/<repo_name>/`

    ```bash
    sbkube prepare --base-dir . --app-dir config
    ```
    (옵션: `--sources <file_name>`)

2.  **애플리케이션 빌드 (`build`)**:
    `prepare` 단계의 결과물과 로컬 소스를 사용하여 배포 가능한 애플리케이션 빌드 결과물을 생성합니다.
    *   **대상**: `config.[yaml|toml]` 파일 내 `pull-helm`, `pull-helm-oci`, `pull-git`, `copy-app` 타입 앱.
    *   **작업**: 소스 복사, Helm 차트 overrides/removes 적용 등.
    *   **결과물**: `<base_dir>/<app_dir>/build/<app_name>/` (이 디렉토리는 빌드 시작 시 초기화됨)

    ```bash
    sbkube build --base-dir . --app-dir config
    ```

3.  **템플릿 렌더링 (`template`, 선택 사항)**:
    빌드된 Helm 차트를 Kubernetes YAML 매니페스트로 렌더링하여 확인합니다.
    *   **대상**: `build` 단계에서 생성된 Helm 차트.
    *   **결과물**: 지정된 출력 디렉토리 (예: `<app_dir>/<output_dir>/<app_name>.yaml`)

    ```bash
    sbkube template --base-dir . --app-dir config --output-dir rendered_yamls
    ```
    (옵션: `--namespace <ns>`)

4.  **클러스터 배포 (`deploy`)**:
    빌드된 애플리케이션을 Kubernetes 클러스터에 배포합니다.
    *   **대상**: `config.[yaml|toml]` 파일 내 `install-helm`, `install-kubectl`, `install-action` 타입 앱.
    *   **작업**: `helm install/upgrade`, `kubectl apply`, 사용자 정의 스크립트 실행.

    ```bash
    sbkube deploy --base-dir . --app-dir config
    ```
    (옵션: `--namespace <ns>`, `--app <app_name>`, `--dry-run` (Helm 전용))

### 애플리케이션 관리 명령어

*   **업그레이드 (`upgrade`)**:
    설치된 Helm 애플리케이션을 업그레이드하거나, 존재하지 않으면 새로 설치합니다 (`--install` 플래그 기본 사용).
    *   **대상**: `install-helm` 타입 앱.

    ```bash
    sbkube upgrade --base-dir . --app-dir config --app my-helm-app
    ```
    (옵션: `--namespace <ns>`, `--dry-run`, `--no-install`)

*   **삭제 (`delete`)**:
    클러스터에서 애플리케이션을 삭제합니다.
    *   **대상**: `install-helm`, `install-kubectl`, `install-action` 타입 앱.

    ```bash
    sbkube delete --base-dir . --app-dir config --app my-app-to-delete
    ```
    (옵션: `--namespace <ns>`, `--skip-not-found`)

*   **설정 검증 (`validate`)**:
    `config.[yaml|toml]` 또는 `sources.[yaml|toml]` 파일의 구조와 내용을 JSON 스키마 및 내부 데이터 모델 기준으로 검증합니다.

    ```bash
    sbkube validate path/to/your/config.yaml
    sbkube validate path/to/your/sources.yaml --schema-type sources
    ```
    (옵션: `--schema-type <type>`, `--schema-path <file_path>`)

### 공통 옵션
대부분의 명령어는 다음 옵션들을 지원합니다:
*   `--base-dir <path>`: 프로젝트의 루트 디렉토리 (기본값: 현재 디렉토리 ".").
*   `--app-dir <name>`: `config.yaml`, `sources.yaml`, `values/` 등이 위치한 디렉토리 이름. `--base-dir` 기준 상대 경로 (기본값: "config").
*   `--app <app_name>`: 특정 애플리케이션만 대상으로 작업 (예: `deploy`, `upgrade`, `delete`, `build`, `template`).

---

## 🥪 테스트

```bash
pytest tests/
```

또는 예제 config 보기:

```bash
python -m sbkube.cli deploy --app-dir config-memory.yaml --base-dir ./samples/k3scode
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
