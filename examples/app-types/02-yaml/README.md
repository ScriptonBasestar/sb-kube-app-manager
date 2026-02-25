# App Type: YAML

Kubernetes YAML 매니페스트를 직접 배포하는 예제입니다.

## 사용 시나리오

- Helm 차트가 없는 애플리케이션
- 직접 작성한 Kubernetes 매니페스트
- 간단한 배포 (Deployment, Service 등)

## 예제: Nginx 배포

### 디렉토리 구조
```
.
├── sbkube.yaml
└── manifests/
    ├── deployment.yaml
    ├── service.yaml
    └── configmap.yaml
```

### sbkube.yaml
```yaml
namespace: yaml-demo

apps:
  nginx:
    type: yaml
    files:
      - manifests/deployment.yaml
      - manifests/service.yaml
      - manifests/configmap.yaml
```

### 실행
```bash
sbkube apply -f sbkube.yaml
```

## 배포 확인

```bash
# Pod 확인
kubectl get pods -n yaml-demo

# 서비스 확인
kubectl get svc -n yaml-demo

# Nginx 테스트
kubectl port-forward -n yaml-demo svc/nginx 8080:80
curl http://localhost:8080
```

## 정리

```bash
sbkube delete -f sbkube.yaml
```

## 주의사항

- YAML 파일은 유효한 Kubernetes 리소스여야 합니다
- 네임스페이스는 sbkube.yaml에서 지정하지만, YAML 파일에도 명시할 수 있습니다
- 여러 리소스를 `---`로 구분하여 하나의 파일에 작성 가능합니다
