# sbkube delete 명령 예시

> **⚠️ LEGACY (v0.2.x)**: 이 예제는 v0.2.x 형식입니다.
>
> v0.3.0 예제는 [examples/](../) 디렉토리의 다른 예제들을 참조하세요.

`delete` 명령은 설치된 Helm 릴리스 및 YAML 리소스를 삭제합니다.

## 기본 사용법

```bash
sbkube delete --app-dir config
```

## 옵션

- `--app-dir`: 앱 설정 디렉토리 (기본값: config)
- `--base-dir`: 프로젝트 루트 디렉토리 (기본값: 현재 디렉토리)
- `--namespace`: 네임스페이스 (없으면 앱별 설정 또는 전역 설정)
- `--app`: 특정 앱만 삭제
- `--skip-not-found`: 리소스가 없을 경우 오류 대신 건너뜁니다.
- `--config-file`: 사용할 설정 파일 이름
- `-v, --verbose`: 상세 로그 출력
- `--debug`: 디버그 로그 출력

## 실행 예시

### 전체 앱 삭제

```bash
sbkube delete --app-dir config
```

#### 예상 출력

```
✨ Delete 시작 - app-dir: config
➡️ 앱 'webapp' (타입: install-helm) 삭제 시도...
$ helm uninstall webapp --namespace default
✅ Helm 릴리스 'webapp' 삭제 완료
✨ `delete` 작업 완료
```

### 특정 앱만 삭제

```bash
sbkube delete --app webapp
```

## 오류 해결

### 리소스 없음 건너뛰기

```bash
sbkube delete --skip-not-found --app webapp
```

### 네임스페이스 권한 문제

```bash
kubectl auth can-i delete pods --namespace default
``` 