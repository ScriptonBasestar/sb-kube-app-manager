# 🔧 문제 해결 가이드

> **난이도**: ⭐⭐ 중급 **소요 시간**: 참조용 (문제별 5-15분) **사전 요구사항**: [01-getting-started.md](01-getting-started.md) 완료

---

## 📋 목차

1. [일반적인 문제](#%EC%9D%BC%EB%B0%98%EC%A0%81%EC%9D%B8-%EB%AC%B8%EC%A0%9C)
1. [prepare 명령어 오류](#prepare-%EB%AA%85%EB%A0%B9%EC%96%B4-%EC%98%A4%EB%A5%98)
1. [build 명령어 오류](#build-%EB%AA%85%EB%A0%B9%EC%96%B4-%EC%98%A4%EB%A5%98)
1. [deploy 명령어 오류](#deploy-%EB%AA%85%EB%A0%B9%EC%96%B4-%EC%98%A4%EB%A5%98)
1. [설정 파일 오류](#%EC%84%A4%EC%A0%95-%ED%8C%8C%EC%9D%BC-%EC%98%A4%EB%A5%98)
1. [Kubernetes 리소스 오류](#kubernetes-%EB%A6%AC%EC%86%8C%EC%8A%A4-%EC%98%A4%EB%A5%98)
1. [디버깅 도구](#%EB%94%94%EB%B2%84%EA%B9%85-%EB%8F%84%EA%B5%AC)

---

## 일반적인 문제

### 문제 1: 명령어를 찾을 수 없음

**증상**:

```bash
$ sbkube --version
bash: sbkube: command not found
```

**원인**: SBKube가 설치되지 않았거나 PATH에 없음

**해결**:

```bash
# 설치 확인
pip show sbkube

# 미설치 시 설치
pip install sbkube

# 또는 uv 사용
uv tool install sbkube

# PATH 확인 (uv 사용 시)
which sbkube
# ~/.local/bin/sbkube
```

### 문제 2: Permission Denied

**증상**:

```bash
$ sbkube apply
Error: Permission denied: '/home/user/.sbkube/state.db'
```

**원인**: SBKube 상태 디렉토리 권한 문제

**해결**:

```bash
# 권한 확인
ls -la ~/.sbkube/

# 소유권 변경
sudo chown -R $USER:$USER ~/.sbkube/

# 또는 디렉토리 재생성
rm -rf ~/.sbkube/
sbkube state list  # 자동으로 디렉토리 생성
```

### 문제 3: Kubernetes 클러스터 연결 실패

**증상**:

```bash
$ sbkube deploy
Error: Unable to connect to Kubernetes cluster
```

**원인**: kubeconfig 설정 문제

**해결**:

```bash
# kubeconfig 파일 확인
echo $KUBECONFIG
ls ~/.kube/config

# 클러스터 접근 테스트
kubectl cluster-info
kubectl get nodes

# Context 확인
kubectl config current-context

# Context 변경
kubectl config use-context <context-name>

# kubeconfig 파일 지정
export KUBECONFIG=~/.kube/config
```

---

## prepare 명령어 오류

### 문제 1: Helm 리포지토리 추가 실패

**증상**:

```bash
$ sbkube prepare
Error: failed to add Helm repo 'grafana': context deadline exceeded
```

**원인**: 네트워크 문제 또는 잘못된 URL

**해결**:

```bash
# 네트워크 확인
curl -I https://grafana.github.io/helm-charts/index.yaml

# Helm 리포지토리 수동 추가
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update grafana

# sources.yaml 확인
cat sources.yaml
# kubeconfig: ~/.kube/config
# kubeconfig_context: my-cluster
# cluster: production
# helm_repos:
#   grafana:
#     url: https://grafana.github.io/helm-charts

# 다시 시도
sbkube prepare
```

### 문제 2: Chart Pull 실패

**증상**:

```bash
$ sbkube prepare
Error: chart 'grafana/grafana' version '6.50.0' not found
```

**원인**: 존재하지 않는 차트 버전

**해결**:

```bash
# 사용 가능한 버전 확인
helm search repo grafana/grafana --versions | head -20

# config.yaml 수정 (최신 버전 사용)
# apps:
#   grafana:
#     chart: grafana/grafana
#     version: 6.60.0  # 올바른 버전으로 수정

# 또는 버전 생략 (최신 버전 사용)
# apps:
#   grafana:
#     chart: grafana/grafana
#     # version 필드 제거
```

### 문제 3: Git Clone 실패

**증상**:

```bash
$ sbkube prepare
Error: failed to clone repository 'https://github.com/user/repo.git': Authentication required
```

**원인**: Private 리포지토리 인증 필요

**해결**:

```bash
# 1. SSH 키 사용
# sources.yaml에 SSH URL 사용
# git_repos:
#   my-repo:
#     url: git@github.com:user/repo.git

# SSH 키 확인
ls ~/.ssh/id_rsa*
ssh -T git@github.com

# 2. Personal Access Token 사용 (HTTPS)
# sources.yaml
# git_repos:
#   my-repo:
#     url: https://oauth2:TOKEN@github.com/user/repo.git

# 3. Git credential helper 설정
git config --global credential.helper store
```

### 문제 4: 차트가 이미 존재함 (v0.4.6 이전)

**증상**:

```bash
$ sbkube prepare
Error: destination path 'charts/grafana' already exists and is not an empty directory
```

**원인**: 이전에 다운로드한 차트가 남아있음

**해결 (v0.4.6 이후)**:

```bash
# 자동으로 스킵됨 (멱등성 지원)
sbkube prepare
# ⏭️  Chart already exists, skipping: grafana
#     Use --force to re-download

# 강제 재다운로드
sbkube prepare --force
```

**해결 (v0.4.5 이하)**:

```bash
# 차트 디렉토리 삭제 후 재실행
rm -rf charts/grafana
sbkube prepare
```

---

## build 명령어 오류

### 문제 1: YAML 파일을 찾을 수 없음

**증상**:

```bash
$ sbkube build
Error: No such file: 'charts/grafana/grafana/templates/deployment.yaml'
```

**원인**: prepare 단계를 건너뜀

**해결**:

```bash
# prepare 먼저 실행
sbkube prepare

# 또는 apply로 전체 실행
sbkube apply
```

### 문제 2: Overrides 적용 실패

**증상**:

```bash
$ sbkube build
Error: Invalid YAML in override for 'templates/servicemonitor.yaml'
```

**원인**: Overrides 내용의 YAML 문법 오류

**해결**:

```bash
# YAML 문법 검증
# config.yaml의 overrides 섹션을 별도 파일로 저장
cat > /tmp/test.yaml << 'EOF'
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: test
EOF

# Python으로 검증
python3 -c "import yaml; yaml.safe_load(open('/tmp/test.yaml'))"

# 또는 yamllint 사용
yamllint /tmp/test.yaml

# config.yaml의 들여쓰기 확인
# overrides:
#   - path: templates/servicemonitor.yaml
#     content: |
#       apiVersion: monitoring.coreos.com/v1  # 들여쓰기 정확히
```

### 문제 3: Removes 경로 오류

**증상**:

```bash
$ sbkube build
Warning: File to remove not found: 'templates/master/configmap.yaml'
```

**원인**: 존재하지 않는 파일 경로

**해결**:

```bash
# 차트의 실제 파일 목록 확인
ls -R charts/grafana/grafana/templates/

# 정확한 경로로 수정
# removes:
#   - templates/configmap.yaml  # 서브디렉토리 없이 직접 경로 사용
```

---

## deploy 명령어 오류

### 문제 1: Namespace가 없음

**증상**:

```bash
$ sbkube deploy
Error: namespaces "test-namespace" not found
```

**원인**: 네임스페이스가 생성되지 않음

**해결**:

```bash
# 네임스페이스 생성
kubectl create namespace test-namespace

# 또는 YAML로
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: test-namespace
EOF

# 네임스페이스 확인
kubectl get namespaces
```

### 문제 2: Helm 릴리스 충돌

**증상**:

```bash
$ sbkube deploy
Error: cannot re-use a name that is still in use
```

**원인**: 동일한 이름의 Helm 릴리스가 이미 존재

**해결**:

```bash
# 기존 릴리스 확인
helm list -n test-namespace

# 릴리스 삭제
helm uninstall grafana-test-namespace -n test-namespace

# 또는 sbkube delete 사용
sbkube delete --namespace test-namespace

# 다시 배포
sbkube deploy
```

### 문제 3: Pod가 Pending 상태

**증상**:

```bash
$ kubectl get pods -n test-namespace
NAME                       READY   STATUS    RESTARTS   AGE
grafana-5f7b4c5d9-abcde    0/1     Pending   0          2m
```

**원인**: 리소스 부족, PVC 마운트 실패, 노드 선택자 불일치

**해결**:

```bash
# Pod 이벤트 확인
kubectl describe pod grafana-5f7b4c5d9-abcde -n test-namespace

# 일반적인 원인:
# 1. 노드 리소스 부족
kubectl top nodes
kubectl describe nodes

# 2. PVC 마운트 실패
kubectl get pvc -n test-namespace
kubectl describe pvc <pvc-name> -n test-namespace

# 3. 노드 선택자 불일치
kubectl get nodes --show-labels
# grafana-values.yaml에서 nodeSelector 확인

# 임시 해결: 리소스 요청 줄이기
# grafana-values.yaml
# resources:
#   requests:
#     cpu: 50m  # 기본값보다 낮춤
#     memory: 64Mi
```

### 문제 4: ImagePullBackOff

**증상**:

```bash
$ kubectl get pods -n test-namespace
NAME                       READY   STATUS             RESTARTS   AGE
grafana-5f7b4c5d9-abcde    0/1     ImagePullBackOff   0          1m
```

**원인**: 이미지를 Pull할 수 없음 (레지스트리 인증, 이미지 없음)

**해결**:

```bash
# Pod 이벤트 확인
kubectl describe pod grafana-5f7b4c5d9-abcde -n test-namespace
# Events:
#   Warning  Failed     10s   kubelet  Failed to pull image "grafana/grafana:9.5.3": rpc error: code = Unknown desc = Error response from daemon: pull access denied for grafana/grafana

# 1. 이미지 이름/태그 확인
# grafana-values.yaml
# image:
#   registry: docker.io
#   repository: grafana/grafana
#   tag: 9.5.3  # 올바른 태그 확인

# 2. Private 레지스트리 인증
kubectl create secret docker-registry regcred \
  --docker-server=<registry-url> \
  --docker-username=<username> \
  --docker-password=<password> \
  -n test-namespace

# grafana-values.yaml
# imagePullSecrets:
#   - name: regcred

# 3. 네트워크 확인 (클러스터에서 외부 접근 가능한지)
kubectl run test --rm -it --image=busybox -- sh
# 컨테이너 안에서
nslookup docker.io
wget -O- https://docker.io
```

### 문제 5: CrashLoopBackOff

**증상**:

```bash
$ kubectl get pods -n test-namespace
NAME                       READY   STATUS             RESTARTS   AGE
grafana-5f7b4c5d9-abcde    0/1     CrashLoopBackOff   5          3m
```

**원인**: 컨테이너 시작 실패 (잘못된 설정, 환경 변수 누락)

**해결**:

```bash
# 로그 확인
kubectl logs grafana-5f7b4c5d9-abcde -n test-namespace

# 이전 로그 확인 (재시작된 경우)
kubectl logs grafana-5f7b4c5d9-abcde -n test-namespace --previous

# 일반적인 원인:
# 1. 환경 변수 누락
kubectl describe pod grafana-5f7b4c5d9-abcde -n test-namespace | grep -A 10 "Environment:"

# 2. Secret/ConfigMap 참조 오류
kubectl get secrets -n test-namespace
kubectl get configmaps -n test-namespace

# 3. 잘못된 명령어 인자
kubectl get pod grafana-5f7b4c5d9-abcde -n test-namespace -o yaml | grep -A 5 "command:"

# 디버깅: 컨테이너 안으로 들어가기
kubectl exec -it grafana-5f7b4c5d9-abcde -n test-namespace -- /bin/bash
# (CrashLoopBackOff 시에는 안 됨 - 다른 디버그 컨테이너 사용)
kubectl debug grafana-5f7b4c5d9-abcde -n test-namespace -it --image=busybox
```

---

## 설정 파일 오류

### 문제 1: Pydantic 검증 오류

**증상**:

```bash
$ sbkube validate
Error: 1 validation error for SBKubeConfig
apps -> redis -> type
  field required (type=value_error.missing)
```

**원인**: 필수 필드 누락

**해결**:

```yaml
# config.yaml
apps:
  grafana:
    type: helm  # 필수 필드 추가
    chart: grafana/grafana
    enabled: true
```

### 문제 2: sources.yaml을 찾을 수 없음

**증상**:

```bash
$ sbkube prepare
Error: sources.yaml not found in: ./sources.yaml, ../sources.yaml, ./sources.yaml
```

**원인**: sources.yaml 파일이 없거나 잘못된 위치

**해결 (v0.4.7 이후)**:

```bash
# sources.yaml 검색 순서 (자동)
# 1. 현재 디렉토리 (.)
# 2. 상위 디렉토리 (..)
# 3. base-dir (--base-dir 옵션)

# sources.yaml 생성
cat > sources.yaml << 'EOF'
kubeconfig: ~/.kube/config
kubeconfig_context: my-cluster
cluster: production

helm_repos:
  grafana:
    url: https://grafana.github.io/helm-charts
EOF

# 또는 상위 디렉토리에 생성
cd ..
cat > sources.yaml << 'EOF'
kubeconfig: ~/.kube/config
kubeconfig_context: my-cluster
cluster: production

helm_repos:
  grafana:
    url: https://grafana.github.io/helm-charts
EOF
cd app1
```

### 문제 3: 순환 의존성

**증상**:

```bash
$ sbkube apply
Error: Circular dependency detected: app-a → app-b → app-a
```

**원인**: depends_on 설정의 순환 참조

**해결**:

```yaml
# 잘못된 예
apps:
  app-a:
    depends_on:
      - app-b
  app-b:
    depends_on:
      - app-a  # 순환 참조!

# 올바른 예
apps:
  app-a:
    # depends_on 제거 또는 수정
  app-b:
    depends_on:
      - app-a
```

---

## Kubernetes 리소스 오류

### 문제 1: Service 연결 실패

**증상**:

```bash
$ kubectl get svc -n test-namespace
NAME      TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
grafana   ClusterIP   10.43.123.45    <none>        80/TCP    5m

# 그러나 연결 실패
$ kubectl exec -it test-pod -n test-namespace -- curl http://grafana
Could not connect to grafana:80: Name or service not known
```

**원인**: DNS 문제, 잘못된 서비스 이름

**해결**:

```bash
# 1. 서비스 이름 확인
kubectl get svc -n test-namespace

# 2. FQDN 사용
curl http://grafana.test-namespace.svc.cluster.local

# 3. DNS 테스트
kubectl run busybox --rm -it --image=busybox -n test-namespace -- sh
nslookup grafana
nslookup grafana.test-namespace.svc.cluster.local

# 4. Endpoints 확인
kubectl get endpoints grafana -n test-namespace
# 백엔드 Pod IP가 있어야 함
```

### 문제 2: PVC Bound 실패

**증상**:

```bash
$ kubectl get pvc -n test-namespace
NAME             STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   AGE
grafana-storage  Pending                                      standard       2m
```

**원인**: StorageClass 없음, 용량 부족

**해결**:

```bash
# StorageClass 확인
kubectl get storageclass

# 없으면 생성 (예: local-path)
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
EOF

# PVC 이벤트 확인
kubectl describe pvc grafana-storage -n test-namespace

# 또는 PVC 비활성화 (테스트용)
# grafana-values.yaml
# persistence:
#   enabled: false
```

### 문제 3: Ingress 404

**증상**:

```bash
$ curl http://app.example.com
404 Not Found
```

**원인**: Ingress 설정 오류, 백엔드 서비스 문제

**해결**:

```bash
# Ingress 확인
kubectl get ingress -n test-namespace
kubectl describe ingress <ingress-name> -n test-namespace

# Ingress Controller 확인
kubectl get pods -n ingress-nginx
# 또는
kubectl get pods -n kube-system | grep traefik

# 백엔드 서비스 확인
kubectl get svc -n test-namespace
kubectl get endpoints <service-name> -n test-namespace

# Ingress 로그 확인
kubectl logs -n ingress-nginx <ingress-controller-pod>

# /etc/hosts 확인 (로컬 테스트 시)
echo "127.0.0.1 app.example.com" | sudo tee -a /etc/hosts
```

---

## 디버깅 도구

### 1. sbkube --verbose

```bash
# 상세 로그 활성화
sbkube --verbose prepare
sbkube --verbose apply
```

### 2. sbkube template

```bash
# 최종 렌더링 결과 확인
sbkube template --output-dir /tmp/rendered

# 특정 앱만
sbkube template --app redis --output-dir /tmp/rendered
```

### 3. helm template (직접)

```bash
# Helm 차트 직접 렌더링
helm template test-release charts-built/redis \
  --namespace test-namespace \
  --values redis-values.yaml \
  --debug
```

### 4. kubectl dry-run

```bash
# Kubernetes 리소스 생성 테스트
kubectl apply -f manifest.yaml --dry-run=client
kubectl apply -f manifest.yaml --dry-run=server
```

### 5. kubectl events

```bash
# 네임스페이스 이벤트 확인
kubectl get events -n test-namespace --sort-by='.lastTimestamp'

# 특정 리소스 이벤트
kubectl describe pod <pod-name> -n test-namespace
```

### 6. kubectl logs

```bash
# 실시간 로그
kubectl logs -f <pod-name> -n test-namespace

# 이전 로그 (재시작된 경우)
kubectl logs --previous <pod-name> -n test-namespace

# 모든 컨테이너 로그
kubectl logs <pod-name> -n test-namespace --all-containers

# 특정 컨테이너 로그
kubectl logs <pod-name> -c <container-name> -n test-namespace
```

### 7. kubectl debug

```bash
# 디버그 컨테이너 실행
kubectl debug <pod-name> -n test-namespace -it --image=busybox

# 노드 디버깅
kubectl debug node/<node-name> -it --image=busybox
```

---

## 일반적인 해결 순서

### Step 1: 정보 수집

```bash
# SBKube 버전
sbkube --version

# Kubernetes 클러스터
kubectl cluster-info
kubectl get nodes

# Helm 버전
helm version

# 현재 상태
sbkube state list
kubectl get all -n <namespace>
```

### Step 2: 로그 확인

```bash
# SBKube 로그
sbkube --verbose <command>

# Kubernetes 리소스 로그
kubectl logs <pod-name> -n <namespace>
kubectl describe <resource-type> <resource-name> -n <namespace>
```

### Step 3: 설정 검증

```bash
# SBKube 설정
sbkube validate

# YAML 문법
yamllint config.yaml

# Helm 차트
helm lint charts-built/<chart-name>
```

### Step 4: 단계별 테스트

```bash
# 각 단계를 개별 실행
sbkube prepare
sbkube build
sbkube template --output-dir /tmp/test
sbkube deploy --dry-run
sbkube deploy
```

---

**작성자**: SBKube Documentation Team **버전**: v0.5.0 **최종 업데이트**: 2025-10-31
