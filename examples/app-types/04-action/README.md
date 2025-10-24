# App Type: Action

커스텀 액션을 순차적으로 실행하는 예제입니다.

## 사용 시나리오

- CRD (CustomResourceDefinition) 설치
- 순서가 중요한 리소스 배포
- 네임스페이스, ConfigMap 등 선행 리소스 생성
- 복잡한 배포 시퀀스

## 예제: Prometheus Operator 설치

이 예제는 Prometheus Operator를 설치하는 과정을 보여줍니다:
1. Namespace 생성
2. CRD 설치
3. Operator 배포

### 디렉토리 구조
```
.
├── config.yaml
├── manifests/
│   ├── 01-namespace.yaml
│   ├── 02-crds.yaml
│   └── 03-operator.yaml
└── README.md
```

### config.yaml
```yaml
namespace: monitoring

apps:
  # 1. 순차적으로 리소스 생성
  prometheus-operator-setup:
    type: action
    actions:
      # Step 1: Namespace
      - type: apply
        path: manifests/01-namespace.yaml

      # Step 2: CRDs
      - type: apply
        path: manifests/02-crds.yaml

      # Step 3: Operator
      - type: apply
        path: manifests/03-operator.yaml

  # 2. 정리 작업 (선택적)
  cleanup-old-resources:
    type: action
    enabled: false  # 필요시 활성화
    actions:
      - type: delete
        path: manifests/old-configmap.yaml
```

## 실행

```bash
# 배포
sbkube apply --app-dir .

# 확인
kubectl get crd | grep monitoring
kubectl get pods -n monitoring
```

## Action 타입

### apply
파일을 `kubectl apply -f` 로 배포합니다.

```yaml
actions:
  - type: apply
    path: manifest.yaml
```

### create
파일을 `kubectl create -f` 로 생성합니다 (이미 존재하면 에러).

```yaml
actions:
  - type: create
    path: manifest.yaml
```

### delete
파일을 `kubectl delete -f` 로 삭제합니다.

```yaml
actions:
  - type: delete
    path: manifest.yaml
```

## 주의사항

1. **순서 보장**: 액션은 정의된 순서대로 실행됩니다
2. **에러 처리**: 중간에 실패하면 멈춥니다
3. **멱등성**: `apply`는 멱등성이 있지만, `create`는 없습니다
4. **네임스페이스**: config.yaml의 namespace 설정이 우선 적용됩니다

## 정리

```bash
sbkube delete --app-dir .
```

## 관련 예제

- [App Type: YAML](../02-yaml/) - 단순 YAML 배포
- [App Type: Exec](../05-exec/) - 명령어 실행
