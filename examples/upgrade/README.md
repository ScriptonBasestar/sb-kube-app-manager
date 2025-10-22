# sbkube upgrade 명령 예시

> **⚠️ LEGACY (v0.2.x)**: 이 예제는 v0.2.x 형식입니다.
>
> v0.3.0 예제는 [examples/](../) 디렉토리의 다른 예제들을 참조하세요.

`upgrade` 명령은 Helm 릴리스를 업그레이드하거나 새로 설치합니다.

## 기본 사용법

```bash
sbkube upgrade --app-dir config
```

## 옵션

- `--app-dir`: 앱 설정 디렉토리 이름 (기본값: config)
- `--base-dir`: 프로젝트 루트 디렉토리 (기본값: 현재 디렉토리)
- `--namespace`: 기본 네임스페이스 (없으면 앱별 설정 또는 전역 설정)
- `--app`: 특정 앱만 업그레이드 (install-helm 타입)
- `--dry-run`: 실제 적용 없이 명령어만 출력
- `--no-install`: 릴리스가 없을 경우 설치하지 않음
- `--config-file`: 사용할 설정 파일 이름
- `-v, --verbose`: 상세 로그 출력
- `--debug`: 디버그 로그 출력

## 실행 예시

### 전체 앱 업그레이드

```bash
sbkube upgrade --app-dir config
```

### 특정 앱 dry-run

```bash
sbkube upgrade --app webapp --dry-run
```

#### 예상 출력 (dry-run)

```
✨ Upgrade 시작 - app-dir: config
➡️ 앱 'webapp' (릴리스명: 'webapp') 업그레이드/설치 시도...
$ helm upgrade webapp config/build/webapp --install --namespace default --create-namespace --dry-run
✅ 앱 'webapp' 업그레이드/설치 성공
✨ `upgrade` 작업 완료
```

## 오류 해결

### 릴리스 존재 여부 확인

```bash
helm list --namespace default
```

### 네임스페이스 권한 문제

```bash
kubectl auth can-i update deploy --namespace default
``` 