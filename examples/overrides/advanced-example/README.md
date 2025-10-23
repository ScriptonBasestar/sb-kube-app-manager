# SBKube v0.3.0 Overrides 및 Removes 예제

이 예제는 SBKube v0.3.0의 차트 커스터마이징 기능을 보여줍니다.

## 디렉토리 구조

```
v3-overrides/
├── config.yaml                # SBKube 설정
├── redis.yaml                 # Redis values
├── overrides/
│   └── redis/
│       ├── values.yaml        # 오버라이드할 values.yaml
│       └── templates/
│           └── service.yaml   # 오버라이드할 service.yaml
└── README.md
```

## 워크플로우

### 1. Prepare (차트 다운로드)

```bash
sbkube prepare --app-dir examples/v3-overrides
```

**결과**:
```
charts/
└── redis/
    └── redis/               # bitnami/redis 차트
        ├── Chart.yaml
        ├── values.yaml      # 원본 values
        ├── templates/
        │   ├── deployment.yaml
        │   ├── service.yaml # 원본 service
        │   ├── ingress.yaml # 나중에 제거될 파일
        │   └── ...
        └── README.md        # 나중에 제거될 파일
```

### 2. Build (차트 커스터마이징)

```bash
sbkube build --app-dir examples/v3-overrides
```

**처리 과정**:
1. `charts/redis/redis/` → `build/redis/` 복사
2. `overrides/redis/values.yaml` → `build/redis/values.yaml` 교체
3. `overrides/redis/templates/service.yaml` → `build/redis/templates/service.yaml` 교체
4. `build/redis/README.md` 삭제
5. `build/redis/templates/ingress.yaml` 삭제

**결과**:
```
build/
└── redis/
    ├── Chart.yaml
    ├── values.yaml          # ✅ 오버라이드됨
    └── templates/
        ├── deployment.yaml
        ├── service.yaml     # ✅ 오버라이드됨
        └── ...              # ✅ ingress.yaml 제거됨
                            # ✅ README.md 제거됨
```

### 3. Template (YAML 렌더링, 선택 사항)

```bash
sbkube template --app-dir examples/v3-overrides
```

**결과**:
```
rendered/
└── redis.yaml               # 렌더링된 최종 매니페스트
```

### 4. Deploy (클러스터 배포)

```bash
sbkube deploy --app-dir examples/v3-overrides
```

**처리 과정**:
- `build/redis/` 디렉토리의 차트를 사용하여 Helm install/upgrade 실행
- Labels 및 Annotations 적용
- 커스터마이즈된 차트가 배포됨

### 또는 통합 실행

```bash
sbkube apply --app-dir examples/v3-overrides
```

prepare → build → deploy를 한 번에 실행합니다.

## Overrides vs Removes

### Overrides
- **목적**: 차트의 특정 파일을 커스텀 버전으로 교체
- **사용 예**:
  - `values.yaml`: 기본값 변경
  - `templates/service.yaml`: Service 타입 변경 (LoadBalancer → ClusterIP)
  - `templates/configmap.yaml`: ConfigMap 내용 수정

### Removes
- **목적**: 불필요한 파일/디렉토리 제거
- **사용 예**:
  - `README.md`: 문서 파일 제거
  - `templates/ingress.yaml`: Ingress 리소스 제거
  - `templates/tests/`: 테스트 파일 디렉토리 제거

## 주의사항

1. **Overrides 디렉토리 구조**
   - `overrides/<app-name>/` 디렉토리 아래에 차트와 동일한 구조로 파일 배치
   - 예: `overrides/redis/templates/service.yaml`

2. **Removes 패턴**
   - 상대 경로로 지정 (차트 루트 기준)
   - 파일 또는 디렉토리 모두 가능
   - 예: `templates/ingress.yaml`, `tests/`

3. **빌드 순서**
   - Prepare → Build 순서로 실행 필요
   - Overrides는 build 단계에서 적용됨

## v0.2.x와의 차이점

### v0.2.x
```yaml
apps:
  - name: redis-pull
    type: helm
    specs:
      repo: bitnami
      chart: redis
      dest: redis

  - name: redis
    type: helm
    specs:
      path: redis
      overrides:
        - values.yaml
      removes:
        - README.md
```

### v0.3.0
```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    overrides:
      - values.yaml
    removes:
      - README.md
```

**개선 사항**:
- pull과 install이 하나의 `helm` 타입으로 통합
- 앱 이름이 딕셔너리 키로 이동
- `specs` 제거로 설정 평탄화
