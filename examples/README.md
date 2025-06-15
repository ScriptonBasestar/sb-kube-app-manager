# sbkube Examples

이 디렉토리는 sbkube의 각 명령어별 사용 예시를 포함합니다.

## 디렉토리 구조

```
examples/
├── README.md           # 이 파일
├── prepare/           # prepare 명령 예시
├── build/            # build 명령 예시  
├── deploy/           # deploy 명령 예시
├── template/         # template 명령 예시
├── upgrade/          # upgrade 명령 예시
├── delete/           # delete 명령 예시
└── complete-workflow/ # 전체 워크플로우 예시
```

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
- **[template/](./template/)**: Helm 차트를 YAML로 렌더링
- **[upgrade/](./upgrade/)**: 기존 배포 업그레이드
- **[delete/](./delete/)**: 배포된 리소스 삭제

## 설정 파일 형식

sbkube는 YAML, TOML 형식의 설정 파일을 지원합니다:

- `config.yaml` / `config.yml`
- `config.toml`

설정 파일 구조는 [schemas/](../schemas/) 디렉토리의 JSON Schema를 참조하세요. 