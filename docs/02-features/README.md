# 🚀 SBKube CLI 주요 기능

SBKube는 Kubernetes 애플리케이션의 배포 및 관리를 자동화하는 CLI 도구입니다. Helm 차트, YAML 매니페스트, Git 저장소 등을 활용하여 애플리케이션의 생명주기를 효율적으로 관리할 수 있도록
돕습니다.

______________________________________________________________________

## 📋 핵심 명령어 (9개)

### 🔧 소스 준비 및 빌드

- **`prepare`** - 외부 소스(Helm 저장소, Git 저장소, OCI 차트)를 로컬 환경에 준비
- **`build`** - 준비된 소스를 기반으로 배포 가능한 형태로 빌드
- **`template`** - Helm 차트 및 YAML 파일들을 최종 매니페스트로 렌더링

### 🚀 배포 및 관리

- **`deploy`** - Kubernetes 클러스터에 애플리케이션 배포
- **`upgrade`** - 배포된 Helm 릴리스 업그레이드 또는 신규 설치
- **`delete`** - 배포된 애플리케이션 및 리소스 삭제

### 🔍 검증 및 정보

- **`validate`** - 설정 파일 유효성 검증 (JSON 스키마 및 Pydantic 기반)
- **`version`** - CLI 현재 버전 표시
- **`state`** - 배포 상태 관리 및 추적 *(신규)*

### 💡 기본 사용법

```bash
# 인수 없이 실행 시 Kubernetes 설정 정보 표시
sbkube

# 기본 워크플로우
sbkube prepare --base-dir . --app-dir config
sbkube build --base-dir . --app-dir config  
sbkube template --base-dir . --app-dir config --output-dir rendered/
sbkube deploy --base-dir . --app-dir config --namespace <namespace>
```

______________________________________________________________________

## 🎯 지원 애플리케이션 타입 (10개)

### 📦 소스 준비 타입

- **`helm`** - Helm 저장소에서 차트 다운로드
- **`git`** - Git 저장소 클론
- **`pull-http`** - HTTP URL에서 파일 다운로드
- **`http`** - 로컬 파일/디렉토리 복사

### 🚀 배포 실행 타입

- **`helm`** - Helm 차트를 사용한 설치
- **`yaml`** - 직접 YAML 매니페스트 배포
- **`action`** - 사용자 정의 액션 스크립트 실행
- **`install-kustomize`** - Kustomize 기반 배포
- **`exec`** - 임의 명령어 실행

______________________________________________________________________

## 🏗️ 주요 아키텍처 특징

### 🔄 다단계 워크플로우

```
prepare → build → template → deploy
```

각 단계는 독립적으로 실행 가능하며, 이전 단계의 결과를 다음 단계에서 활용합니다.

### 📊 배포 상태 관리 *(신규)*

- **SQLAlchemy 기반** 배포 상태 데이터베이스
- **자동 상태 추적** 및 배포 히스토리 관리
- **롤백 기능** 지원

### 🎨 Rich 콘솔 출력

- **컬러풀한 로깅** 및 진행 상황 표시
- **테이블 형태** Kubernetes 설정 정보 출력
- **상세/간단 모드** 지원 (`-v, --verbose`)

### 🔧 강력한 에러 처리

- **체계적인 예외 시스템** (`SbkubeError` 기반)
- **명령어 도구 검증** (Helm, kubectl 자동 확인)
- **타임아웃 처리** 및 재시도 로직

______________________________________________________________________

## ⚙️ 설정 시스템

### 📄 설정 파일

- **`config.yaml`** - 애플리케이션 정의 및 배포 스펙
- **`sources.yaml`** - 외부 소스 정의 (Helm repos, Git repos)
- **`values/`** - Helm 값 파일 디렉토리

### 🔗 Pydantic 기반 검증

- **강력한 타입 검증** 및 데이터 모델링
- **JSON 스키마** 자동 생성 및 검증
- **명확한 에러 메시지** 제공

### 🌐 전역 옵션 지원

```bash
sbkube --kubeconfig ~/.kube/custom-config --context prod-cluster deploy
sbkube --namespace monitoring --verbose template
```

______________________________________________________________________

## 🔍 고급 기능

### 🎯 BaseCommand 패턴

모든 명령어가 공통 기반 클래스를 상속하여 일관된 동작을 제공합니다:

- 설정 파일 로딩
- 전역 옵션 처리
- 에러 핸들링
- 로깅 시스템

### 🔄 유연한 확장성

- **새로운 앱 타입** 쉽게 추가 가능
- **커스텀 명령어** 개발 지원
- **플러그인 아키텍처** 준비

### 📈 개발자 친화적

- **명확한 코드 구조** (commands/, models/, utils/)
- **포괄적인 테스트 커버리지**
- **상세한 로깅** 및 디버깅 지원

______________________________________________________________________

## 🚀 실전 활용 시나리오

### 📦 Helm 차트 배포

```bash
# Helm 저장소에서 차트 가져와서 배포
sbkube prepare && sbkube build && sbkube deploy
```

### 📝 직접 YAML 배포

```bash
# 커스텀 YAML 매니페스트 직접 배포
sbkube build --app nginx-app && sbkube deploy --app nginx-app
```

### 🔄 Git 기반 배포

```bash
# Git 저장소에서 소스 가져와서 빌드 후 배포  
sbkube prepare && sbkube build && sbkube template --output-dir ./rendered
```

### 📊 상태 관리

```bash
# 배포 상태 확인
sbkube history

# 특정 배포 롤백
sbkube rollback --deployment-id <id>
```

______________________________________________________________________

*자세한 명령어 사용법은 [commands.md](commands.md)를 참조하세요.*\
*애플리케이션 타입별 상세 설명은 [application-types.md](application-types.md)를 확인하세요.*
