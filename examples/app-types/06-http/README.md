# App Type: HTTP

HTTP URL에서 파일을 다운로드하는 예제입니다.

## 사용 시나리오

- 공개 매니페스트 다운로드 (GitHub Raw, Gist 등)
- CRD 다운로드
- 설정 파일 다운로드
- 원격 YAML 파일 가져오기

## 예제 1: GitHub에서 매니페스트 다운로드

### config.yaml
```yaml
namespace: http-demo

apps:
  # 1. HTTP로 파일 다운로드
  download-manifest:
    type: http
    url: https://raw.githubusercontent.com/example/k8s-manifests/main/nginx.yaml
    dest: downloaded/nginx.yaml

  # 2. 다운로드한 파일 배포
  deploy-downloaded:
    type: yaml
    files:
      - downloaded/nginx.yaml
    depends_on:
      - download-manifest
```

## 예제 2: 여러 파일 다운로드

### config.yaml
```yaml
namespace: http-demo

apps:
  # CRD 다운로드
  download-crd:
    type: http
    url: https://example.com/crds/custom-resource.yaml
    dest: crds/custom-resource.yaml

  # ConfigMap 다운로드
  download-config:
    type: http
    url: https://example.com/configs/app-config.yaml
    dest: configs/app-config.yaml

  # 다운로드한 파일들 배포
  deploy-resources:
    type: yaml
    files:
      - crds/custom-resource.yaml
      - configs/app-config.yaml
    depends_on:
      - download-crd
      - download-config
```

## 예제 3: HTTP 헤더 사용

### config.yaml
```yaml
namespace: http-demo

apps:
  download-with-auth:
    type: http
    url: https://api.github.com/repos/example/repo/contents/manifest.yaml
    dest: manifest.yaml
    headers:
      Authorization: "token ghp_YourGitHubToken"
      Accept: "application/vnd.github.v3.raw"
```

## 실행

```bash
# prepare 단계에서 파일 다운로드
sbkube prepare --app-dir .

# 다운로드된 파일 확인
ls -la downloaded/

# 전체 워크플로우 실행
sbkube apply --app-dir .
```

## 주의사항

### 1. 네트워크 연결 필요
인터넷 연결이 필요합니다. 오프라인 환경에서는 사용할 수 없습니다.

### 2. 파일 검증
다운로드한 파일의 내용을 확인하세요:

```bash
# 다운로드 후 파일 확인
cat downloaded/nginx.yaml

# 또는 template로 렌더링 테스트
sbkube template --app-dir . --output-dir rendered/
```

### 3. HTTPS 사용 권장
보안을 위해 HTTPS URL을 사용하세요.

### 4. 인증
민감한 토큰은 환경 변수나 Secret으로 관리하세요.

## 고급 예제

### 동적 URL (환경 변수 사용)

```bash
# 환경 변수 설정
export MANIFEST_VERSION=v1.2.3

# config.yaml에서 사용 (템플릿 기능 필요시)
# 현재는 정적 URL만 지원
```

### 타임아웃 설정

현재 http 타입은 기본 타임아웃을 사용합니다.
필요시 curl 래퍼를 exec 타입으로 사용할 수 있습니다:

```yaml
apps:
  download-with-timeout:
    type: exec
    commands:
      - curl -L --max-time 30 -o downloaded/file.yaml https://example.com/file.yaml
```

## 일반적인 사용 예제

### Cert-Manager CRD 다운로드

```yaml
apps:
  cert-manager-crds:
    type: http
    url: https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.crds.yaml
    dest: cert-manager-crds.yaml

  apply-crds:
    type: yaml
    files:
      - cert-manager-crds.yaml
    depends_on:
      - cert-manager-crds
```

### Prometheus Operator CRD

```yaml
apps:
  prometheus-crds:
    type: http
    url: https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/example/prometheus-operator-crd/monitoring.coreos.com_prometheuses.yaml
    dest: prometheus-crds.yaml
```

## 정리

```bash
sbkube delete --app-dir .

# 다운로드한 파일도 삭제
rm -rf downloaded/ crds/ configs/
```

## 트러블슈팅

### 다운로드 실패
```bash
# URL 확인
curl -I https://example.com/manifest.yaml

# 수동 다운로드 테스트
curl -L -o test.yaml https://example.com/manifest.yaml
```

### 403 Forbidden
- 인증이 필요한 경우 headers에 토큰 추가
- GitHub API 사용 시 Accept 헤더 필요

### SSL 인증서 에러
- 신뢰할 수 있는 HTTPS URL 사용
- 자체 서명 인증서는 지원 안됨 (exec + curl -k 사용)

## 관련 예제

- [App Type: Git](../03-git/) - Git 리포지토리 클론
- [App Type: YAML](../02-yaml/) - YAML 매니페스트 배포
