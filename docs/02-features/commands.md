# 📋 SBKube 명령어 상세 가이드

SBKube의 모든 명령어에 대한 상세한 사용법과 옵션을 설명합니다.

______________________________________________________________________

## 🌐 전역 옵션

모든 명령어에서 사용할 수 있는 전역 옵션:

```bash
sbkube [전역옵션] <명령어> [명령어옵션]
```

### 전역 옵션

- `--kubeconfig <경로>` - Kubernetes 설정 파일 경로 (환경변수: `KUBECONFIG`)
- `--context <이름>` - 사용할 Kubernetes 컨텍스트 이름
- `--namespace <네임스페이스>` - 작업을 수행할 기본 네임스페이스 (환경변수: `KUBE_NAMESPACE`)
- `-v, --verbose` - 상세 로깅 활성화

### 기본 실행

```bash
# Kubernetes 설정 정보 표시
sbkube

# 특정 컨텍스트로 명령어 실행
sbkube --context prod-cluster --namespace monitoring deploy
```

______________________________________________________________________

## 🔧 prepare - 소스 준비

외부 소스(Helm 저장소, Git 저장소, OCI 차트)를 로컬 환경에 다운로드하고 준비합니다.

### 📋 사용법

```bash
sbkube prepare [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `config`)
- `--sources <파일>` - 소스 설정 파일 (기본값: `sources.yaml`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 사용할 설정 파일 이름 (app-dir 내부)
- `--sources-file <경로>` - 소스 설정 파일 경로 (--sources와 동일)
- `--app <앱이름>` - 준비할 특정 앱 이름 (미지정시 모든 앱)

### 📁 생성되는 디렉토리

- `charts/` - 다운로드된 Helm 차트
- `repos/` - 클론된 Git 저장소

### 💡 사용 예제

```bash
# 기본 소스 준비
sbkube prepare

# 특정 앱만 준비
sbkube prepare --app nginx-app

# 커스텀 설정으로 준비
sbkube prepare --app-dir my-config --sources my-sources.yaml
```

______________________________________________________________________

## 🔨 build - 앱 빌드

준비된 소스를 기반으로 배포 가능한 형태로 빌드합니다.

### 📋 사용법

```bash
sbkube build [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `config`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 사용할 설정 파일 이름
- `--app <앱이름>` - 빌드할 특정 앱 이름

### 📁 생성되는 디렉토리

- `build/` - 빌드된 애플리케이션 아티팩트

### 🎯 지원 앱 타입

- **`pull-helm`** - Helm 차트 준비
- **`pull-helm-oci`** - OCI 차트 준비
- **`pull-git`** - Git 소스 준비
- **`copy-app`** - 로컬 파일 복사
- **`install-yaml`** - YAML 매니페스트 준비

### 💡 사용 예제

```bash
# 모든 앱 빌드
sbkube build

# 특정 앱만 빌드
sbkube build --app database

# 커스텀 설정으로 빌드
sbkube build --app-dir production --config-file prod-config.yaml
```

______________________________________________________________________

## 📄 template - 템플릿 렌더링

빌드된 Helm 차트 및 YAML 파일들을 최종 매니페스트로 렌더링합니다.

### 📋 사용법

```bash
sbkube template [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `config`)
- `--output-dir <디렉토리>` - 렌더링된 YAML 저장 디렉토리 (기본값: `rendered`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--namespace <네임스페이스>` - 템플릿 생성 시 적용할 기본 네임스페이스
- `--config-file <파일>` - 사용할 설정 파일 이름
- `--app <앱이름>` - 템플릿을 생성할 특정 앱 이름

### 📁 생성되는 디렉토리

- `rendered/` - 렌더링된 YAML 매니페스트 파일

### 🎯 지원 앱 타입

- **`install-helm`** - Helm 차트 템플릿
- **`install-yaml`** - YAML 매니페스트 템플릿

### 💡 사용 예제

```bash
# 모든 앱 템플릿 생성
sbkube template

# 특정 네임스페이스로 템플릿 생성
sbkube template --namespace production

# 커스텀 출력 디렉토리
sbkube template --output-dir /tmp/manifests
```

______________________________________________________________________

## 🚀 deploy - 애플리케이션 배포

Kubernetes 클러스터에 애플리케이션을 배포합니다.

### 📋 사용법

```bash
sbkube deploy [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `config`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--dry-run` - 실제로 적용하지 않고 dry-run 실행
- `--app <앱이름>` - 배포할 특정 앱 이름
- `--config-file <파일>` - 사용할 설정 파일 이름

### 🎯 지원 앱 타입

- **`install-helm`** - Helm 차트 설치
- **`install-yaml`** - YAML 매니페스트 적용
- **`install-action`** - 사용자 정의 스크립트 실행
- **`exec`** - 임의 명령어 실행

### 💡 사용 예제

```bash
# 모든 앱 배포
sbkube deploy

# Dry-run으로 확인
sbkube deploy --dry-run

# 특정 앱만 배포
sbkube deploy --app web-frontend

# 특정 네임스페이스에 배포
sbkube --namespace staging deploy
```

______________________________________________________________________

## ⬆️ upgrade - 릴리스 업그레이드

이미 배포된 Helm 릴리스를 업그레이드하거나 존재하지 않을 경우 새로 설치합니다.

### 📋 사용법

```bash
sbkube upgrade [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `config`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 사용할 설정 파일 이름
- `--app <앱이름>` - 업그레이드할 특정 앱 이름

### 🎯 지원 앱 타입

- **`install-helm`** - Helm 릴리스 업그레이드

### 💡 사용 예제

```bash
# 모든 Helm 릴리스 업그레이드
sbkube upgrade

# 특정 앱 업그레이드
sbkube upgrade --app database
```

______________________________________________________________________

## 🗑️ delete - 리소스 삭제

배포된 애플리케이션 및 리소스를 클러스터에서 삭제합니다.

### 📋 사용법

```bash
sbkube delete [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `config`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 사용할 설정 파일 이름
- `--app <앱이름>` - 삭제할 특정 앱 이름

### 🎯 지원 앱 타입

- **`install-helm`** - Helm 릴리스 삭제
- **`install-yaml`** - YAML 리소스 삭제
- **`install-action`** - 사용자 정의 삭제 스크립트 실행

### 💡 사용 예제

```bash
# 모든 앱 삭제
sbkube delete

# 특정 앱만 삭제
sbkube delete --app nginx-app
```

______________________________________________________________________

## ✅ validate - 설정 파일 검증

설정 파일의 유효성을 JSON 스키마 및 Pydantic 데이터 모델을 기반으로 검증합니다.

### 📋 사용법

```bash
sbkube validate [옵션]
```

### 🎛️ 옵션

- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `config`)
- `--base-dir <경로>` - 프로젝트 루트 디렉토리 (기본값: `.`)
- `--config-file <파일>` - 검증할 설정 파일 이름

### 🔍 검증 항목

- **JSON 스키마** 준수 여부
- **Pydantic 모델** 유효성
- **필수 필드** 존재 여부
- **타입 검증** 및 제약사항

### 💡 사용 예제

```bash
# 기본 설정 파일 검증
sbkube validate

# 특정 설정 파일 검증
sbkube validate --config-file staging-config.yaml
```

______________________________________________________________________

## 📊 state - 배포 상태 관리

배포 상태를 추적하고 롤백 기능을 제공합니다. *(신규 기능)*

### 📋 사용법

```bash
sbkube state <하위명령어> [옵션]
```

### 🎛️ 하위 명령어

- `list` - 배포 상태 목록 조회
- `rollback` - 특정 배포로 롤백
- `history` - 배포 히스토리 조회

### 🎛️ 옵션

- `--cluster <이름>` - 클러스터별 필터링
- `--deployment-id <ID>` - 특정 배포 ID 지정

### 💡 사용 예제

```bash
# 배포 상태 목록 확인
sbkube state list

# 특정 클러스터 상태 확인
sbkube state list --cluster production

# 롤백 실행
sbkube state rollback --deployment-id <id>
```

______________________________________________________________________

## ℹ️ version - 버전 정보

SBKube CLI의 현재 버전을 표시합니다.

### 📋 사용법

```bash
sbkube version
```

### 💡 출력 예제

```
SBKube CLI v0.1.10
```

______________________________________________________________________

## 🔄 일반적인 워크플로우

### 기본 배포 워크플로우

```bash
# 1. 소스 준비
sbkube prepare

# 2. 앱 빌드
sbkube build

# 3. 템플릿 렌더링 (선택사항)
sbkube template --output-dir ./manifests

# 4. 배포 실행
sbkube deploy
```

### 부분 배포 워크플로우

```bash
# 특정 앱만 처리
sbkube prepare --app database
sbkube build --app database
sbkube deploy --app database
```

### 검증 및 Dry-run 워크플로우

```bash
# 설정 파일 검증
sbkube validate

# Dry-run으로 확인
sbkube deploy --dry-run

# 실제 배포
sbkube deploy
```

______________________________________________________________________

*각 명령어의 더 자세한 사용법은 `sbkube <명령어> --help`를 통해 확인할 수 있습니다.*
