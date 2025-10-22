# Local Helm Chart Example

이 예제는 로컬 Helm 차트를 사용하는 방법을 보여줍니다.

## 디렉토리 구조

```
local-chart/
├── config.yaml           # SBKube 설정
├── redis-values.yaml     # Redis values
├── myapp-values.yaml     # MyApp values
├── nginx-values.yaml     # Nginx values
└── charts/
    ├── myapp/            # 로컬 커스텀 차트
    │   ├── Chart.yaml
    │   ├── values.yaml
    │   └── templates/
    │       ├── deployment.yaml
    │       └── service.yaml
    └── nginx-custom/     # 또 다른 로컬 차트
        ├── Chart.yaml
        └── ...
```

## 로컬 차트 생성

```bash
# MyApp 차트 생성
cd charts/
helm create myapp

# 차트 커스터마이징
vim myapp/Chart.yaml
vim myapp/templates/deployment.yaml

# Nginx 차트 생성
helm create nginx-custom
vim nginx-custom/templates/deployment.yaml
```

## 실행

### 1. Prepare (Remote 차트만 pull)

```bash
sbkube prepare --app-dir .
```

**결과**:
- `redis`: Pull 수행 (remote chart)
- `myapp`: Skip (local chart)
- `nginx`: Skip (local chart)

### 2. Deploy (모두 배포)

```bash
sbkube deploy --app-dir .
```

**배포 순서** (depends_on 기준):
1. `redis` (먼저)
2. `myapp` (redis 의존)
3. `nginx` (의존성 없음)

### 3. Apply (한 번에)

```bash
sbkube apply --app-dir .
```

## 로컬 차트의 장점

1. **빠른 개발**: Pull 단계 불필요
2. **커스터마이징**: 차트를 자유롭게 수정 가능
3. **버전 관리**: Git으로 차트도 함께 관리
4. **재현성**: 외부 의존성 없이 독립적

## 워크플로우 예시

### 개발 중

```bash
# 1. 차트 수정
vim charts/myapp/templates/deployment.yaml

# 2. 바로 배포 (prepare 불필요)
sbkube deploy --app-dir . --app myapp

# 3. 반복 개발
# ... 수정 → 배포 → 테스트
```

### Pull 후 커스터마이징

```bash
# 1. Remote 차트 pull
sbkube prepare --app-dir .

# 2. Redis 차트 수정
vim charts/redis/redis/templates/configmap.yaml

# 3. config.yaml 변경 (remote → local)
# Before: chart: bitnami/redis
# After:  chart: ./charts/redis/redis

# 4. 수정된 차트로 배포
sbkube deploy --app-dir .
```

## values 파일 예시

### redis-values.yaml
```yaml
architecture: standalone
auth:
  enabled: false
master:
  persistence:
    enabled: false
```

### myapp-values.yaml
```yaml
replicaCount: 2
image:
  repository: myapp
  tag: latest
service:
  type: ClusterIP
  port: 8080
env:
  - name: REDIS_HOST
    value: redis-master
```

### nginx-values.yaml
```yaml
replicaCount: 1
image:
  repository: nginx
  tag: 1.21
service:
  type: LoadBalancer
  port: 80
```

## 참고

- [Helm Chart Types 문서](../../docs/03-configuration/helm-chart-types.md)
- [SBKube Configuration](../../docs/03-configuration/config-schema-v3.md)
