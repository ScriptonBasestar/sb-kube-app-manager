# Override with Files & Removes Example

이 예제는 Helm 차트를 커스터마이징하는 두 가지 방법을 보여줍니다:

1. **overrides**: 차트에 새 파일 추가 또는 기존 파일 교체
2. **removes**: 차트의 불필요한 파일 삭제

## 📋 시나리오

Ingress Nginx 차트 커스터마이징:

### ✅ overrides 사용
1. 새 ConfigMap 템플릿 추가 (`templates/custom-configmap.yaml`)
2. 커스텀 index.html 파일 추가 (`files/index.html`)
3. ConfigMap에서 `.Files.Get`으로 파일 참조

### ❌ removes 사용
1. 테스트 파일 제거 (`templates/tests/`)
2. Helm 설치 메시지 제거 (`templates/NOTES.txt`)
3. 사용하지 않는 리소스 제거

## 📁 파일 구조

```
override-with-files/
├── README.md                          # 이 문서
├── config.yaml                        # SBKube 설정 (overrides 명시)
├── values/
│   └── nginx.yaml                     # Nginx values
├── overrides/
│   └── nginx/
│       ├── templates/
│       │   └── custom-configmap.yaml  # 새 템플릿 (차트에 없던 파일)
│       └── files/
│           └── index.html             # 커스텀 HTML (차트에 없던 파일)
└── .sbkube/                           # sbkube 작업 디렉토리
    └── build/                         # sbkube build 실행 후 생성
        └── nginx/
            ├── templates/
            │   ├── deployment.yaml        # (차트 원본)
            │   ├── service.yaml           # (차트 원본)
            │   └── custom-configmap.yaml  # ✅ 추가됨
            └── files/
            └── index.html             # ✅ 추가됨
```

## 🗺️ 경로 매핑 다이어그램

Override 파일이 어떻게 복사되는지 시각적으로 이해하기:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. 소스 파일 (작성하는 곳)                                         │
└─────────────────────────────────────────────────────────────────┘

  overrides/
    nginx/                           ← 앱 이름 (config.yaml의 apps.nginx)
      ├── templates/
      │   └── custom-configmap.yaml  ← 실제 파일 위치
      └── files/
          └── index.html             ← 실제 파일 위치

┌─────────────────────────────────────────────────────────────────┐
│ 2. config.yaml (설정하는 곳)                                      │
└─────────────────────────────────────────────────────────────────┘

  nginx:
    overrides:
      - templates/custom-configmap.yaml  ← "overrides/nginx/" 제외
      - files/index.html                 ← "overrides/nginx/" 제외

  📍 핵심 규칙:
     config.yaml 경로 = overrides/[앱이름]/ 이후 경로

┌─────────────────────────────────────────────────────────────────┐
│ 3. 빌드 결과 (sbkube build 후)                                   │
└─────────────────────────────────────────────────────────────────┘

  .sbkube/build/
    nginx/                           ← 앱 이름
      ├── Chart.yaml                 ← (차트 원본)
      ├── templates/
      │   ├── deployment.yaml        ← (차트 원본)
      │   ├── service.yaml           ← (차트 원본)
      │   └── custom-configmap.yaml  ← ✅ 복사됨
      └── files/
          └── index.html             ← ✅ 복사됨

  📍 결과 경로:
     .sbkube/build/[앱이름]/[config.yaml의 경로]
```

### 경로 매핑 예시

| 소스 파일 | config.yaml | 빌드 결과 | |-----------|-------------|-----------| |
`overrides/nginx/templates/custom-configmap.yaml` | `templates/custom-configmap.yaml` |
`.sbkube/build/nginx/templates/custom-configmap.yaml` | | `overrides/nginx/files/index.html` | `files/index.html` |
`.sbkube/build/nginx/files/index.html` | | `overrides/nginx/templates/subdir/secret.yaml` | `templates/subdir/secret.yaml` |
`.sbkube/build/nginx/templates/subdir/secret.yaml` |

**핵심**: `overrides/[앱이름]/`을 제외한 나머지 경로가 그대로 유지됩니다.

______________________________________________________________________

## 📄 파일 설명

### config.yaml

메인 설정 파일입니다. **중요**: `overrides` 필드에 모든 override 파일을 명시해야 합니다.

```yaml
apps:
  nginx:
    type: helm
    chart: ingress-nginx/ingress-nginx
    version: "4.0.0"
    values:
      - values/nginx.yaml
    overrides:
      - templates/custom-configmap.yaml  # 새 템플릿 추가
      - files/index.html                 # 새 파일 추가
    namespace: default
```

**핵심 포인트**:

- `templates/custom-configmap.yaml` - 차트에 없던 새 템플릿
- `files/index.html` - `.Files.Get`에서 참조할 파일

### overrides/nginx/templates/custom-configmap.yaml

차트에 **없던 새 리소스**를 추가하는 템플릿입니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "nginx.fullname" . }}-custom
  labels:
    {{- include "nginx.labels" . | nindent 4 }}
data:
  # .Files.Get을 사용하여 files/index.html 내용 삽입
  index.html: |-
{{ .Files.Get "files/index.html" | indent 4}}
```

**핵심 기능**:

- `{{ .Files.Get "files/index.html" }}` - files 디렉토리의 파일 내용을 가져옴
- 경로는 차트 루트 기준 (.sbkube/build/nginx/)

### overrides/nginx/files/index.html

ConfigMap에 포함될 커스텀 HTML 파일입니다.

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Custom Nginx Page</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 20px;
        }
        p {
            font-size: 1.2em;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎉 Hello from Override!</h1>
        <p>This page is served from a ConfigMap created by sbkube override mechanism.</p>
        <p>The HTML content was added to the Helm chart using the <code>files/</code> directory feature.</p>
        <hr>
        <p><strong>Powered by</strong>: SBKube + Ingress Nginx Chart</p>
    </div>
</body>
</html>
```

### values/nginx.yaml

Nginx 차트의 values 파일입니다.

```yaml
# Nginx 설정
replicaCount: 1

service:
  type: ClusterIP
  port: 80

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 50m
    memory: 64Mi
```

## 🚀 실행 방법

### 1. 준비 (Helm 저장소 및 차트 다운로드)

```bash
sbkube prepare --app-dir examples/override-with-files
```

**결과**:

```
✨ SBKube `prepare` 시작 ✨
📄 Loading config: examples/override-with-files/config.yaml
📦 Preparing Helm app: nginx
  Adding Helm repo: ingress-nginx (https://kubernetes.github.io/ingress-nginx)
  Pulling chart: ingress-nginx/ingress-nginx:4.0.0
✅ Helm app prepared: nginx
✅ Prepare completed: 1/1 apps
```

### 2. 빌드 (Override 적용)

```bash
sbkube build --app-dir examples/override-with-files
```

**결과**:

```
✨ SBKube `build` 시작 ✨
📄 Loading config: examples/override-with-files/config.yaml
🔨 Building Helm app: nginx
  Copying chart: .sbkube/charts/nginx/nginx → .sbkube/build/nginx
  Applying 2 overrides...
    ✓ Override: templates/custom-configmap.yaml
    ✓ Override: files/index.html
✅ Helm app built: nginx
✅ Build completed: 1/1 apps
```

### 3. 검증 (빌드 결과 확인)

```bash
# Override 파일들이 .sbkube/build/ 디렉토리에 복사되었는지 확인
ls -la .sbkube/build/nginx/templates/custom-configmap.yaml
ls -la .sbkube/build/nginx/files/index.html

# 템플릿 렌더링 테스트
sbkube template --app-dir examples/override-with-files --output-dir /tmp/rendered

# ConfigMap 내용 확인 (.Files.Get이 제대로 작동하는지 확인)
cat /tmp/rendered/nginx/custom-configmap.yaml
```

**예상 출력** (`custom-configmap.yaml`):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-custom
  labels:
    app.kubernetes.io/name: nginx
    ...
data:
  index.html: |-
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        ...
    </head>
    <body>
        <div class="container">
            <h1>🎉 Hello from Override!</h1>
            ...
```

### 4. 배포 (선택 사항)

```bash
# Dry-run으로 먼저 확인
sbkube deploy --app-dir examples/override-with-files --dry-run

# 실제 배포
sbkube deploy --app-dir examples/override-with-files
```

### 5. 결과 확인 (배포 후)

```bash
# ConfigMap 생성 확인
kubectl get configmap -n default | grep nginx-custom

# ConfigMap 내용 확인
kubectl describe configmap nginx-custom -n default

# Pod 확인
kubectl get pods -n default -l app.kubernetes.io/name=nginx
```

## 🎯 핵심 포인트

### ✅ Overrides: 파일 추가/교체

**두 가지 역할**:

1. **기존 파일 덮어쓰기**

   ```yaml
   overrides:
     - templates/deployment.yaml  # 차트의 기본 템플릿 교체
   ```

2. **새 파일 추가**

   ```yaml
   overrides:
     - templates/custom-configmap.yaml  # 차트에 없던 새 템플릿
     - files/index.html                 # 차트에 없던 새 파일
   ```

### ❌ Removes: 불필요한 파일 삭제 (v0.4.0+)

**주요 사용 사례**:

```yaml
removes:
  # 1. 테스트 파일 제거 (프로덕션 배포 시)
  - templates/tests/test-connection.yaml
  - templates/tests/

  # 2. 데모/예제 리소스 제거
  - templates/demo-*.yaml
  - templates/examples/

  # 3. 사용하지 않는 CRD 제거
  - crds/example-crd.yaml

  # 4. Helm 설치 메시지 제거
  - templates/NOTES.txt

  # 5. 보안상 불필요한 ServiceAccount 제거
  - templates/serviceaccount.yaml
```

**overrides vs removes 비교**:

| 기능 | overrides | removes |
|------|-----------|---------|
| 목적 | 파일 추가/교체 | 파일 삭제 |
| 실행 시점 | `sbkube build` | `sbkube build` |
| 소스 필요 | 필요 (`overrides/` 디렉토리) | 불필요 (경로만 지정) |
| Glob 패턴 | 지원 (v0.4.9+) | 지원 (v0.4.9+) |
| Use case | 커스텀 템플릿 추가 | 불필요한 파일 제거 |

**실전 예시**:

```yaml
apps:
  nginx:
    type: helm
    chart: nginx
    repo: grafana

    # 커스텀 템플릿 추가
    overrides:
      - templates/custom-ingress.yaml

    # 불필요한 테스트 제거
    removes:
      - templates/tests/
      - templates/NOTES.txt
```

### ⚠️ .Files.Get 사용 시 주의사항

**1. files 디렉토리도 override에 포함 필수**

```yaml
# ❌ 잘못된 설정 (templates만 추가)
overrides:
  - templates/custom-configmap.yaml
  # files/index.html 누락! → .Files.Get 실패

# ✅ 올바른 설정 (files도 추가)
overrides:
  - templates/custom-configmap.yaml
  - files/index.html             # 필수!
```

**2. 경로는 차트 루트 기준**

```
.sbkube/build/nginx/       # ← 차트 루트 (.Files.Get의 기준)
  ├── Chart.yaml
  ├── templates/
  │   └── custom-configmap.yaml  # .Files.Get "files/index.html" 호출
  └── files/
      └── index.html       # ← .Files.Get이 찾는 위치
```

### 🚫 자동 발견 없음

sbkube는 `overrides/` 디렉토리를 자동으로 감지하지 않습니다.

```bash
# ❌ 이렇게 해도 적용 안 됨
mkdir -p overrides/nginx/templates
cat > overrides/nginx/templates/configmap.yaml << EOF
...
EOF
# config.yaml에 명시하지 않으면 무시됨!

# ✅ config.yaml에 명시 필수
# config.yaml:
#   nginx:
#     overrides:
#       - templates/configmap.yaml
```

**v0.4.8+**: Override 디렉토리가 있지만 config.yaml에 설정되지 않은 경우 경고 메시지 표시:

```
⚠️  Override directory found but not configured: nginx
    Location: overrides/nginx
    Files:
      - templates/custom-configmap.yaml
      - files/index.html
    💡 To apply these overrides, add to config.yaml:
       nginx:
         overrides:
           - templates/custom-configmap.yaml
           - files/index.html
```

## 📚 학습 목표

이 예제를 통해 다음을 학습할 수 있습니다:

1. ✅ Helm 차트에 **새 파일 추가** 방법
1. ✅ `.Files.Get`을 사용하는 템플릿 작성 방법
1. ✅ `files/` 디렉토리와 `templates/` 디렉토리의 관계
1. ✅ Override 메커니즘의 **명시적 설정** 철학
1. ✅ 빌드 → 템플릿 → 배포 워크플로우

## 🔗 관련 문서

- [commands.md](../../docs/02-features/commands.md#-override-%EB%94%94%EB%A0%89%ED%86%A0%EB%A6%AC-%EC%82%AC%EC%9A%A9-%EC%8B%9C-%EC%A3%BC%EC%9D%98%EC%82%AC%ED%95%AD)
  \- Override 사용법 상세
- [config-schema.md](../../docs/03-configuration/config-schema.md) - overrides 필드 스키마
- [troubleshooting.md](../../docs/07-troubleshooting/README.md#-%EB%B9%8C%EB%93%9C-%EB%B0%8F-override-%EB%AC%B8%EC%A0%9C)
  \- Override 문제 해결

## ❓ FAQ

**Q: files 디렉토리를 자동으로 복사할 수 없나요?**

A: 의도적으로 자동 복사를 지원하지 않습니다. **명시적 설정 (Explicit over Implicit)** 철학을 따르기 때문입니다. 사용자가 어떤 파일이 적용되는지 명확히 알 수 있어야 합니다.

**Q: override 디렉토리가 있는데 왜 무시되나요?**

A: `config.yaml`의 `overrides` 필드에 명시해야 적용됩니다. v0.4.8+에서는 경고 메시지를 통해 알려줍니다.

**Q: .Files.Get이 빈 문자열을 반환해요.**

A: `files/` 디렉토리의 파일도 `overrides` 필드에 명시해야 합니다. 자세한 내용은
[troubleshooting.md](../../docs/07-troubleshooting/README.md#-filesget-%ED%8C%8C%EC%9D%BC%EC%9D%84-%EC%B0%BE%EC%9D%84-%EC%88%98-%EC%97%86%EC%9D%8C)를
참조하세요.

**Q: 여러 개의 files를 한 번에 추가할 수 있나요?**

A: 네, 두 가지 방법이 있습니다:

방법 1: 명시적 나열

```yaml
overrides:
  - templates/configmap.yaml
  - files/config1.txt
  - files/config2.toml
  - files/scripts/init.sh
```

방법 2: Glob 패턴 사용 (v0.4.9+)

```yaml
overrides:
  - templates/*.yaml        # templates/의 모든 .yaml
  - files/*                 # files/의 모든 파일
  - files/scripts/*         # files/scripts/의 모든 파일
```

**Q: Glob 패턴과 명시적 파일을 같이 쓸 수 있나요?**

A: 네, 혼합해서 사용할 수 있습니다:

```yaml
overrides:
  - Chart.yaml              # 차트 메타데이터 교체
  - templates/*.yaml        # 모든 템플릿 추가
  - files/important.txt     # 특정 파일만
  - files/scripts/*         # 스크립트 디렉토리 전체
```

______________________________________________________________________

**이 예제를 실행해보고 sbkube의 override 메커니즘을 이해해보세요!** 🚀
