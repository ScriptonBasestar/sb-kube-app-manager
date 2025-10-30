# Use Case: CI/CD Stack

GitLab Runner와 Docker Registry를 포함한 완전한 CI/CD 스택 구축 예제입니다.

## 📋 개요

**카테고리**: Use Cases

**구성 요소**:
- **GitLab Runner**: Kubernetes 기반 CI/CD 실행기
- **Docker Registry**: 프라이빗 컨테이너 이미지 저장소
- **MinIO**: Registry 백엔드 스토리지 (S3 호환)

**학습 목표**:
- CI/CD 인프라 구축
- Docker Registry + S3 백엔드 연동
- GitLab Runner 설정 및 등록
- 복잡한 의존성 체인 관리

## 🎯 사용 사례

### 1. 완전한 CI/CD 환경

- GitLab 프로젝트에서 자동 빌드/테스트
- 빌드된 이미지를 프라이빗 Registry에 푸시
- 동일 클러스터에서 배포 테스트

### 2. Air-gapped 환경

- 외부 인터넷 없이 자체 Registry 운영
- 모든 이미지를 로컬에서 관리
- 보안 요구사항 준수

### 3. 멀티 프로젝트 빌드

- 여러 GitLab 프로젝트 동시 빌드
- 공용 Runner Pool 사용
- 리소스 효율적 활용

## 🚀 빠른 시작

### 전제조건

1. **GitLab 인스턴스** (GitLab.com 또는 Self-hosted)
2. **GitLab Runner 등록 토큰**

토큰 확인 방법:
```
GitLab 프로젝트 → Settings → CI/CD → Runners → Registration token
```

### 1. 설정 파일 준비

```bash
# config.yaml 복사 및 수정
cp examples/use-cases/04-cicd-stack/config.yaml my-cicd/config.yaml

# GitLab Runner 토큰 설정
# values/gitlab-runner-values.yaml 편집:
# runnerRegistrationToken: "YOUR_GITLAB_TOKEN"
```

### 2. 전체 스택 배포

```bash
sbkube apply \
  --app-dir examples/use-cases/04-cicd-stack \
  --namespace cicd
```

### 3. 배포 확인

```bash
# 모든 Pod 확인
kubectl get pods -n cicd

# 예상 출력:
# minio-xxxxx                   1/1   Running
# docker-registry-xxxxx         1/1   Running
# gitlab-runner-xxxxx           1/1   Running

# Registry 접근 확인
kubectl port-forward -n cicd svc/docker-registry 5000:5000

# 다른 터미널에서:
curl http://localhost:5000/v2/_catalog
# {"repositories":[]}
```

### 4. GitLab Runner 등록 확인

```bash
# Runner Pod 로그 확인
kubectl logs -n cicd -l app=gitlab-runner

# GitLab에서 확인:
# 프로젝트 → Settings → CI/CD → Runners
# "Available specific runners" 섹션에 표시되어야 함
```

## 📖 설정 파일 설명

### config.yaml

```yaml
namespace: cicd

apps:
  # 1단계: MinIO (S3 스토리지)
  minio:
    type: helm
    chart: prometheus-community/prometheus
    values:
      - values/minio-values.yaml
    enabled: true

  # 2단계: Docker Registry (MinIO 의존)
  docker-registry:
    type: helm
    chart: twuni/docker-registry
    values:
      - values/registry-values.yaml
    depends_on:
      - minio

  # 3단계: GitLab Runner (Registry 의존)
  gitlab-runner:
    type: helm
    chart: gitlab/gitlab-runner
    values:
      - values/gitlab-runner-values.yaml
    depends_on:
      - docker-registry
```

### 의존성 체인

```
MinIO (S3 Backend)
    ↓
Docker Registry (이미지 저장소)
    ↓
GitLab Runner (CI/CD 실행기)
```

## 🔧 주요 구성 요소

### 1. MinIO (S3 Compatible Storage)

**역할**: Docker Registry의 백엔드 스토리지

**주요 설정** (`values/minio-values.yaml`):
```yaml
auth:
  rootUser: admin
  rootPassword: minio-secret-password

defaultBuckets: "registry"  # Docker Registry용 버킷

persistence:
  enabled: true
  size: 10Gi
  storageClass: "local-path"  # k3s 기본 스토리지

resources:
  requests:
    memory: 256Mi
  limits:
    memory: 512Mi
```

**접근**:
```bash
# MinIO Console 접근
kubectl port-forward -n cicd svc/minio 9001:9001

# 브라우저에서: http://localhost:9001
# 로그인: admin / minio-secret-password
```

### 2. Docker Registry

**역할**: 컨테이너 이미지 저장 및 배포

**주요 설정** (`values/registry-values.yaml`):
```yaml
storage: s3
s3:
  region: us-east-1
  bucket: registry
  encrypt: false
  secure: false
  v4auth: true
  regionEndpoint: http://minio:9000
  accessKey: admin
  secretKey: minio-secret-password

persistence:
  enabled: false  # MinIO가 백엔드이므로 불필요

service:
  type: ClusterIP
  port: 5000
```

**사용**:
```bash
# 이미지 푸시 (클러스터 내부)
docker tag myapp:latest docker-registry.cicd.svc.cluster.local:5000/myapp:latest
docker push docker-registry.cicd.svc.cluster.local:5000/myapp:latest

# 이미지 풀
docker pull docker-registry.cicd.svc.cluster.local:5000/myapp:latest
```

### 3. GitLab Runner

**역할**: GitLab CI/CD 파이프라인 실행

**주요 설정** (`values/gitlab-runner-values.yaml`):
```yaml
runnerRegistrationToken: "YOUR_GITLAB_TOKEN"  # 필수 변경!

gitlabUrl: https://gitlab.com/  # 또는 Self-hosted GitLab URL

concurrent: 10  # 동시 실행 작업 수

rbac:
  create: true  # Kubernetes RBAC 생성

runners:
  config: |
    [[runners]]
      [runners.kubernetes]
        namespace = "cicd"
        image = "alpine:latest"
        privileged = true  # Docker-in-Docker 지원

        # Registry 연동
        [[runners.kubernetes.volumes.empty_dir]]
          name = "docker-certs"
          mount_path = "/certs/client"
          medium = "Memory"
```

**Pipeline 예시** (`.gitlab-ci.yml`):
```yaml
stages:
  - build
  - push

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .

push:
  stage: push
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA \
        docker-registry.cicd.svc.cluster.local:5000/myapp:latest
    - docker push docker-registry.cicd.svc.cluster.local:5000/myapp:latest
```

## 🎓 학습 포인트

### 1. 의존성 체인의 중요성

```
MinIO 없음 → Registry 실패 (S3 백엔드 부재)
Registry 없음 → Runner는 동작하지만 이미지 푸시 불가
```

SBKube의 `depends_on`으로 올바른 순서 보장:
```yaml
apps:
  minio:
    type: helm
    # 의존성 없음 (최우선)

  registry:
    type: helm
    depends_on: [minio]  # MinIO 후 배포

  runner:
    type: helm
    depends_on: [registry]  # Registry 후 배포
```

### 2. S3 Compatible Storage

MinIO는 AWS S3 API와 호환:
- Docker Registry는 S3 백엔드 지원
- 온프레미스 환경에서도 S3 사용 가능
- 다른 S3 호환 스토리지도 가능 (Ceph, etc.)

### 3. GitLab Runner 모드

**Executor 타입**:
- `docker`: Docker를 사용한 빌드 (단순)
- `kubernetes`: Kubernetes Pod 기반 빌드 (확장성)

이 예제는 **Kubernetes Executor** 사용:
- 각 작업마다 새 Pod 생성
- 리소스 효율적
- 확장성 우수

### 4. Privileged Mode

```yaml
privileged: true  # Docker-in-Docker 필요
```

**주의사항**:
- 보안 위험 증가
- 프로덕션에서는 Kaniko, Buildah 등 대안 고려

## 🧪 테스트 시나리오

### 시나리오 1: Registry 동작 확인

```bash
# Port-forward
kubectl port-forward -n cicd svc/docker-registry 5000:5000

# 다른 터미널에서
# 빈 Registry 확인
curl http://localhost:5000/v2/_catalog
# {"repositories":[]}

# 이미지 푸시 (insecure registry 설정 필요)
# /etc/docker/daemon.json에 추가:
# {
#   "insecure-registries": ["localhost:5000"]
# }

docker pull alpine:latest
docker tag alpine:latest localhost:5000/test-alpine:latest
docker push localhost:5000/test-alpine:latest

# 재확인
curl http://localhost:5000/v2/_catalog
# {"repositories":["test-alpine"]}
```

### 시나리오 2: GitLab 파이프라인 실행

1. GitLab 프로젝트에 `.gitlab-ci.yml` 추가:
```yaml
test-job:
  script:
    - echo "Running on Kubernetes GitLab Runner"
    - cat /etc/os-release
```

2. Commit & Push
3. GitLab에서 파이프라인 확인
4. Runner Pod 로그 확인:
```bash
kubectl logs -n cicd -l app=gitlab-runner -f
```

### 시나리오 3: MinIO 백엔드 확인

```bash
# MinIO Console 접근
kubectl port-forward -n cicd svc/minio 9001:9001

# 브라우저: http://localhost:9001
# 로그인 후 "registry" 버킷 확인
# Docker Registry에 푸시된 이미지 레이어 확인 가능
```

## 🔍 트러블슈팅

### 문제 1: "GitLab Runner가 등록되지 않음"

**증상**:
```bash
kubectl logs -n cicd -l app=gitlab-runner
# ERROR: Registering runner... failed
```

**원인**: 잘못된 Registration Token

**해결**:
1. GitLab에서 올바른 토큰 복사
2. `values/gitlab-runner-values.yaml` 수정:
```yaml
runnerRegistrationToken: "CORRECT_TOKEN"
```
3. 재배포:
```bash
sbkube apply --app-dir . --namespace cicd
```

### 문제 2: "Registry에 이미지 푸시 실패"

**증상**:
```
Error: denied: requested access to the resource is denied
```

**원인**: Registry 인증 설정 누락

**해결**:
```yaml
# values/registry-values.yaml에 인증 추가 (선택)
secrets:
  htpasswd: |
    user:$apr1$...  # htpasswd로 생성
```

또는 인증 없이 사용 (내부 네트워크만):
```yaml
# 기본 설정 (인증 없음)
```

### 문제 3: "MinIO 접근 불가"

**증상**:
```
Registry 로그: s3aws: AccessDenied
```

**원인**: MinIO 자격 증명 불일치

**해결**:
```yaml
# minio-values.yaml
auth:
  rootUser: admin
  rootPassword: minio-secret-password

# registry-values.yaml
s3:
  accessKey: admin  # minio-values와 일치
  secretKey: minio-secret-password  # 일치
```

### 문제 4: "Runner Pod가 이미지를 풀 수 없음"

**증상**:
```
Error: Failed to pull image "docker-registry.cicd.svc.cluster.local:5000/myapp"
```

**원인**: imagePullSecrets 누락

**해결**:
```bash
# Registry 인증 Secret 생성
kubectl create secret docker-registry regcred \
  --docker-server=docker-registry.cicd.svc.cluster.local:5000 \
  --docker-username=user \
  --docker-password=password \
  -n cicd

# Deployment에 추가
spec:
  template:
    spec:
      imagePullSecrets:
      - name: regcred
```

## 💡 실전 패턴

### 패턴 1: 외부 GitLab.com 사용

```yaml
# values/gitlab-runner-values.yaml
gitlabUrl: https://gitlab.com/

runnerRegistrationToken: "glrt-xxx"  # GitLab.com 토큰

runners:
  config: |
    [[runners]]
      [runners.kubernetes]
        namespace = "cicd"
        image = "alpine:latest"
```

### 패턴 2: Self-hosted GitLab 연동

```yaml
# values/gitlab-runner-values.yaml
gitlabUrl: https://gitlab.mycompany.com/

# GitLab TLS 인증서 검증 비활성화 (자체 인증서 사용 시)
certsSecretName: gitlab-certs

runners:
  config: |
    [[runners]]
      environment = ["DOCKER_TLS_CERTDIR=/certs"]
      tls-ca-file = "/home/gitlab-runner/.gitlab-runner/certs/ca.crt"
```

### 패턴 3: 고급 Registry 설정

```yaml
# values/registry-values.yaml
# HTTPS 활성화
ingress:
  enabled: true
  hosts:
    - registry.example.com
  tls:
    - secretName: registry-tls
      hosts:
        - registry.example.com

# 이미지 삭제 활성화
configData:
  storage:
    delete:
      enabled: true
```

### 패턴 4: 리소스 제한

```yaml
# values/gitlab-runner-values.yaml
runners:
  config: |
    [[runners]]
      [runners.kubernetes]
        cpu_request = "100m"
        memory_request = "128Mi"
        cpu_limit = "1000m"
        memory_limit = "1Gi"

        helper_cpu_request = "5m"
        helper_memory_request = "32Mi"
```

## 📚 추가 학습 자료

### 공식 문서
- [GitLab Runner Kubernetes Executor](https://docs.gitlab.com/runner/executors/kubernetes.html)
- [Docker Registry Configuration](https://docs.docker.com/registry/configuration/)
- [MinIO S3 API](https://min.io/docs/minio/linux/developers/minio-drivers.html)

### SBKube 관련
- [Dependency Management](../../docs/02-features/commands.md#의존성-관리)
- [Helm App Type](../../docs/02-features/application-types.md#1-helm)

### 관련 예제
- [Complex Dependencies](../../advanced-features/02-complex-dependencies/)
- [Wiki Stack](../02-wiki-stack/) - 다른 의존성 패턴

## 🎯 다음 단계

1. **보안 강화**:
   - Registry에 TLS/인증 추가
   - Sealed Secrets로 자격 증명 암호화

2. **고급 Runner 설정**:
   - Cache 설정으로 빌드 속도 향상
   - 여러 Runner Pool (dev/prod)

3. **모니터링 통합**:
   - Prometheus로 Runner 메트릭 수집
   - Grafana 대시보드 추가

## 🧹 정리

```bash
# 전체 스택 삭제
kubectl delete namespace cicd

# 또는 개별 삭제
helm uninstall gitlab-runner docker-registry minio -n cicd
```

---

**완전한 CI/CD 인프라를 단 하나의 명령으로 배포하세요! 🚀**
