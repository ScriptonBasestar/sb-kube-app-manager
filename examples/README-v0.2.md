# sbkube Examples

이 디렉토리는 sbkube의 각 명령어별 사용 예시를 포함합니다.

## 디렉토리 구조

```
examples/
├── README.md           # 이 파일
├── prepare/           # prepare 명령 예시
│   └── pull-helm-oci/ # OCI Helm 차트 pull 예시
├── build/            # build 명령 예시  
├── deploy/           # deploy 명령 예시
│   ├── install-yaml/ # YAML 매니페스트 배포 예시
│   ├── install-action/ # 커스텀 액션 배포 예시
│   └── exec/         # 명령 실행 예시
├── template/         # template 명령 예시
├── upgrade/          # upgrade 명령 예시
├── delete/           # delete 명령 예시
├── complete-workflow/ # 전체 워크플로우 예시
└── k3scode/          # 실제 프로젝트 예시
```

## 지원하는 앱 타입

### prepare 명령
- **pull-helm**: Helm 저장소에서 차트 다운로드
- **pull-helm-oci**: OCI 저장소에서 Helm 차트 다운로드
- **pull-git**: Git 저장소에서 소스 코드 다운로드

### build 명령
- **copy-app**: 로컬 파일/디렉토리 복사

### deploy 명령
- **install-helm**: Helm 차트 설치
- **install-yaml**: YAML 매니페스트 적용
- **install-action**: 커스텀 액션 실행 (CRD, Operator 등)
- **exec**: 임의 명령 실행

## 빠른 시작

### 1. 기본 워크플로우

```bash
# 1단계: 외부 리소스 준비
sbkube prepare --app-dir config

# 2단계: 빌드
sbkube build --app-dir config  

# 3단계: 배포
sbkube deploy --app-dir config
```

### 2. 개별 명령어 예시

각 디렉토리에서 더 자세한 예시를 확인할 수 있습니다:

- **[prepare/](./prepare/)**: Helm 차트, Git 저장소 등 외부 리소스 준비
- **[build/](./build/)**: 배포 가능한 형태로 리소스 빌드
- **[deploy/](./deploy/)**: Kubernetes 클러스터에 애플리케이션 배포
  - **[install-yaml/](./deploy/install-yaml/)**: YAML 매니페스트 배포
  - **[install-action/](./deploy/install-action/)**: 커스텀 액션 (CRD, Operator)
  - **[exec/](./deploy/exec/)**: 명령 실행
- **[template/](./template/)**: Helm 차트를 YAML로 렌더링
- **[upgrade/](./upgrade/)**: 기존 배포 업그레이드
- **[delete/](./delete/)**: 배포된 리소스 삭제
- **[complete-workflow/](./complete-workflow/)**: 모든 타입을 포함한 완전한 예시

### 3. 실제 프로젝트 예시

**[k3scode/](./k3scode/)** 디렉토리는 실제 운영 환경에서 사용할 수 있는 완전한 예시입니다:

```bash
# AI 도구 준비 및 배포
cd examples/k3scode
sbkube prepare --app-dir ai --sources-file sources.yaml
sbkube build --app-dir ai
sbkube deploy --app-dir ai

# DevOps 도구 배포
sbkube build --app-dir devops
sbkube deploy --app-dir devops
```

## 설정 파일 형식

sbkube는 YAML, TOML 형식의 설정 파일을 지원합니다:

- `config.yaml` / `config.yml`
- `config.toml`

설정 파일 구조는 [schemas/](../schemas/) 디렉토리의 JSON Schema를 참조하세요.

## 예상되는 오류 케이스

### 1. CLI 도구 누락
```bash
❌ helm 명령이 시스템에 설치되어 있지 않습니다.
❌ kubectl 명령이 시스템에 설치되어 있지 않습니다.
```
**해결**: 필요한 CLI 도구를 설치하세요.

### 2. 저장소 정보 누락
```bash
❌ sources.yaml에서 저장소 'example-repo'을 찾을 수 없습니다.
```
**해결**: `sources.yaml`에 필요한 저장소 정보를 추가하세요.

### 3. 빌드 결과물 누락
```bash
❌ 빌드된 Helm 차트 디렉토리를 찾을 수 없습니다
⚠️  'sbkube build' 명령을 먼저 실행했는지 확인하세요.
```
**해결**: `sbkube build` 명령을 먼저 실행하세요.

### 4. 네트워크 연결 문제
```bash
❌ Git 저장소 클론 실패: fatal: unable to access
❌ Helm 차트 다운로드 실패: failed to download
```
**해결**: 네트워크 연결과 저장소 접근 권한을 확인하세요. 