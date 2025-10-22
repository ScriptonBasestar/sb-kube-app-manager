# sbkube template 명령 예시

> **⚠️ LEGACY (v0.2.x)**: 이 예제는 v0.2.x 형식입니다.
>
> v0.3.0 예제는 [examples/](../) 디렉토리의 다른 예제들을 참조하세요.

`template` 명령은 빌드된 Helm 차트를 YAML 매니페스트로 렌더링합니다.

## 기본 사용법

```bash
sbkube template --app-dir config --output-dir rendered
```

## 옵션

- `--app-dir`: 앱 설정 디렉토리 (기본값: config)
- `--output-dir`: 렌더링된 YAML을 저장할 디렉토리 (기본값: rendered)
- `--base-dir`: 프로젝트 루트 디렉토리 (기본값: 현재 디렉토리)
- `--namespace`: CLI로 지정된 기본 네임스페이스 (앱별 설정 우선)
- `--config-file`: 사용할 설정 파일 이름
- `--app`: 특정 앱만 처리

## 실행 예시

### 전체 앱 렌더링

```bash
sbkube template --app-dir config
```

#### 예상 출력

```
✨ Template 시작 - app-dir: config
ℹ️ 출력 디렉토리 준비: config/rendered
➡️ 앱 'webapp' (타입: install-helm) 템플릿 생성 시작...
$ helm template webapp config/build/webapp --namespace default
✅ 앱 'webapp' 템플릿 생성 완료: config/rendered/webapp.yaml
✨ `template` 작업 완료 (결과물 위치: config/rendered)
```

## 오류 해결

### 출력 디렉토리 권한 문제

```bash
chmod -R u+rw config/rendered
```

### Helm template 실패

- Helm 버전 확인: `helm version`
- 빌드 결과물 확인: `ls config/build` 