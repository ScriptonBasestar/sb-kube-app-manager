# Helm Chart Customization

SBKube은 Helm 차트를 배포 전에 커스터마이징할 수 있는 강력한 기능을 제공합니다.

## 개요

차트 커스터마이징 워크플로우:

```
prepare → build → deploy
   ↓         ↓        ↓
다운로드  커스터마이징  배포
```

- **prepare**: Remote 차트를 `charts/` 디렉토리로 다운로드
- **build**: 차트를 `build/` 디렉토리로 복사하고 overrides/removes 적용
- **deploy**: `build/` 디렉토리의 커스터마이즈된 차트를 배포

## Overrides (파일 교체)

### 기본 사용법

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    overrides:
      - values.yaml           # values.yaml 교체
      - templates/service.yaml # service.yaml 교체
```

### 디렉토리 구조

```
project/
├── config.yaml
├── overrides/
│   └── redis/                    # 앱 이름과 동일
│       ├── values.yaml           # 교체할 파일
│       └── templates/
│           └── service.yaml      # 교체할 파일
└── charts/
    └── redis/
        └── redis/                # 원본 차트
            ├── values.yaml       # 원본
            └── templates/
                └── service.yaml  # 원본
```

### 처리 과정

1. **prepare 단계**: 원본 차트를 `charts/redis/redis/`로 다운로드
2. **build 단계**:
   - `charts/redis/redis/` → `build/redis/` 복사
   - `overrides/redis/values.yaml` → `build/redis/values.yaml` 교체
   - `overrides/redis/templates/service.yaml` → `build/redis/templates/service.yaml` 교체
3. **deploy 단계**: `build/redis/` 디렉토리의 차트로 배포

### 사용 사례

#### 1. values.yaml 커스터마이징

**원본** (`charts/redis/redis/values.yaml`):
```yaml
replicaCount: 1
resources:
  limits:
    memory: 256Mi
```

**오버라이드** (`overrides/redis/values.yaml`):
```yaml
replicaCount: 3
resources:
  limits:
    memory: 512Mi
```

**결과** (`build/redis/values.yaml`):
```yaml
replicaCount: 3
resources:
  limits:
    memory: 512Mi
```

#### 2. Service 타입 변경

**원본** (`charts/myapp/myapp/templates/service.yaml`):
```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  type: LoadBalancer
  ports:
    - port: 80
```

**오버라이드** (`overrides/myapp/templates/service.yaml`):
```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  type: ClusterIP  # LoadBalancer → ClusterIP 변경
  ports:
    - port: 80
```

## Removes (파일 삭제)

### 기본 사용법

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    removes:
      - README.md                # 파일 삭제
      - templates/ingress.yaml   # 특정 템플릿 삭제
      - tests/                   # 디렉토리 삭제
```

### 처리 과정

1. **build 단계**:
   - 차트를 `build/redis/`로 복사
   - `build/redis/README.md` 삭제
   - `build/redis/templates/ingress.yaml` 삭제
   - `build/redis/tests/` 디렉토리 전체 삭제

### 사용 사례

#### 1. 불필요한 리소스 제거

```yaml
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
    removes:
      - templates/ingress.yaml     # Ingress 사용 안 함
      - templates/servicemonitor.yaml # Prometheus 사용 안 함
```

#### 2. 문서/테스트 파일 제거

```yaml
apps:
  postgres:
    type: helm
    chart: bitnami/postgresql
    removes:
      - README.md
      - NOTES.txt
      - tests/
```

## 조합 사용

Overrides와 Removes를 함께 사용할 수 있습니다:

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2
    values:
      - redis.yaml

    # 파일 교체
    overrides:
      - values.yaml
      - templates/service.yaml
      - templates/configmap.yaml

    # 파일 삭제
    removes:
      - README.md
      - templates/ingress.yaml
      - templates/tests/
      - docs/
```

**처리 순서**:
1. 차트 복사: `charts/redis/redis/` → `build/redis/`
2. Overrides 적용: 파일 교체
3. Removes 적용: 파일 삭제

## 로컬 차트 커스터마이징

로컬 차트도 동일하게 커스터마이징 가능합니다:

```yaml
apps:
  my-app:
    type: helm
    chart: ./charts/my-app  # 로컬 차트
    overrides:
      - values.yaml
    removes:
      - templates/ingress.yaml
```

**처리 과정**:
1. **build 단계**:
   - `./charts/my-app/` → `build/my-app/` 복사
   - Overrides 적용
   - Removes 적용
2. **deploy 단계**: `build/my-app/` 디렉토리로 배포

## 명령어 사용법

### 개별 실행

```bash
# 1. 차트 다운로드
sbkube prepare --app-dir my-project

# 2. 차트 커스터마이징
sbkube build --app-dir my-project

# 3. 배포
sbkube deploy --app-dir my-project
```

### 통합 실행

```bash
# prepare + build + deploy 한 번에
sbkube apply --app-dir my-project
```

### 특정 앱만 처리

```bash
sbkube build --app-dir my-project --app redis
sbkube deploy --app-dir my-project --app redis
```

## 검증

### Template 명령어로 미리보기

배포 전에 렌더링된 YAML을 확인할 수 있습니다:

```bash
# prepare + build 후
sbkube template --app-dir my-project

# 결과 확인
cat my-project/rendered/redis.yaml
```

### Dry-run 모드

```bash
sbkube deploy --app-dir my-project --dry-run
```

## 고급 사용 사례

### 1. 환경별 커스터마이징

**Production 환경**:
```yaml
# config-prod.yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    overrides:
      - values-prod.yaml  # 프로덕션 설정
    removes:
      - templates/tests/
```

**Staging 환경**:
```yaml
# config-staging.yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    overrides:
      - values-staging.yaml  # 스테이징 설정
```

### 2. 멀티 파일 오버라이드

```yaml
apps:
  myapp:
    type: helm
    chart: myorg/myapp
    overrides:
      - values.yaml
      - templates/deployment.yaml
      - templates/service.yaml
      - templates/configmap.yaml
      - templates/hpa.yaml
```

### 3. 보안 강화

```yaml
apps:
  postgres:
    type: helm
    chart: bitnami/postgresql
    overrides:
      - templates/secret.yaml  # 커스텀 Secret 사용
    removes:
      - templates/networkpolicy.yaml  # 자체 NetworkPolicy 사용
```

## 주의사항

### 1. Overrides 파일 경로

- 반드시 `overrides/<app-name>/` 디렉토리 아래에 위치
- 차트 내 경로와 동일한 구조 유지

**올바른 예**:
```
overrides/redis/templates/service.yaml  # ✅
```

**잘못된 예**:
```
overrides/service.yaml  # ❌ (앱 이름 디렉토리 없음)
overrides/redis/service.yaml  # ❌ (templates 디렉토리 누락)
```

### 2. Removes 패턴

- 차트 루트 기준 상대 경로
- 파일 및 디렉토리 모두 가능
- 와일드카드(`*`) 미지원 (향후 추가 예정)

### 3. 빌드 순서

- `prepare` → `build` → `deploy` 순서 준수
- Overrides는 `build` 단계에서만 적용됨
- `deploy`는 항상 `build/` 디렉토리 우선 사용

### 4. 버전 관리

- `overrides/` 디렉토리는 Git에 포함 권장
- `build/` 디렉토리는 `.gitignore`에 추가 권장
- 환경별 오버라이드 파일 분리 권장

## 트러블슈팅

### 오버라이드 파일이 적용되지 않음

```bash
# build 디렉토리 확인
ls -la build/redis/

# overrides 디렉토리 구조 확인
tree overrides/redis/
```

### 잘못된 경로

```
[yellow]⚠️ Override file not found: overrides/redis/values.yaml[/yellow]
```

**해결**:
- 파일 경로 확인: `overrides/<app-name>/<file-path>`
- 앱 이름이 config.yaml의 키와 일치하는지 확인

### 파일이 삭제되지 않음

```bash
# build 디렉토리에 파일이 있는지 확인
ls build/redis/README.md

# config.yaml의 removes 패턴 확인
```

## 참고 자료

- [Configuration Schema](config-schema-v3.md) - 설정 파일 전체 구조
- [Application Types](../02-features/application-types.md) - 앱 타입 설명
- [Commands Reference](../02-features/commands.md) - 명령어 상세
- [Examples](../../examples/overrides/advanced-example/) - 실제 사용 예제
