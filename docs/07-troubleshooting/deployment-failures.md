______________________________________________________________________

## type: Troubleshooting Guide audience: End User, Developer topics: [errors, deployment-failures, debugging] llm_priority: high last_updated: 2025-01-04

# 배포 실패 트러블슈팅 가이드

SBKube 배포 중 발생할 수 있는 다양한 에러 상황과 해결 방법을 안내합니다.

______________________________________________________________________

## 📋 목차

1. [에러 메시지 이해하기](#%EC%97%90%EB%9F%AC-%EB%A9%94%EC%8B%9C%EC%A7%80-%EC%9D%B4%ED%95%B4%ED%95%98%EA%B8%B0)
1. [데이터베이스 에러](#%EB%8D%B0%EC%9D%B4%ED%84%B0%EB%B2%A0%EC%9D%B4%EC%8A%A4-%EC%97%90%EB%9F%AC)
1. [Helm 릴리스 에러](#helm-%EB%A6%B4%EB%A6%AC%EC%8A%A4-%EC%97%90%EB%9F%AC)
1. [Kubernetes 연결 에러](#kubernetes-%EC%97%B0%EA%B2%B0-%EC%97%90%EB%9F%AC)
1. [네임스페이스 에러](#%EB%84%A4%EC%9E%84%EC%8A%A4%ED%8E%98%EC%9D%B4%EC%8A%A4-%EC%97%90%EB%9F%AC)
1. [일반적인 해결 전략](#%EC%9D%BC%EB%B0%98%EC%A0%81%EC%9D%B8-%ED%95%B4%EA%B2%B0-%EC%A0%84%EB%9E%B5)

______________________________________________________________________

## 에러 메시지 이해하기

SBKube v0.6.1부터 개선된 에러 메시지 형식을 제공합니다:

```
❌ 배포 실패: airflow
(3/3 단계에서 실패)

📍 실패 단계: 🚀 Deploy
🔍 에러 타입: DatabaseAuthenticationError
💬 상세 내용: password authentication failed for user "airflow_user"

🗄️ 데이터베이스 정보:
  • DB 종류: postgresql
  • 사용자: airflow_user
  • 호스트: postgresql.data.svc.cluster.local
  • 포트: 5432

💡 해결 방법:
  • DB 사용자/비밀번호 확인 → kubectl get secret -n <namespace>
  • Secret 내용 확인 → kubectl get secret <secret-name> -o jsonpath='{.data}'
  • config.yaml의 database 설정 확인
  ...
```

### 에러 메시지 구성 요소

- **실패 단계**: prepare (📦), build (🔨), deploy (🚀) 중 어디서 실패했는지
- **에러 타입**: 자동 분류된 에러 카테고리
- **상세 내용**: 원본 에러 메시지
- **추가 정보**: DB 정보, Helm 정보 등 컨텍스트별 상세 정보
- **해결 방법**: 자동으로 제안되는 해결 방법 목록

______________________________________________________________________

## 데이터베이스 에러

### DatabaseAuthenticationError

**증상**: 데이터베이스 인증 실패

```
FATAL: password authentication failed for user "airflow_user"
```

**원인**:

- 잘못된 사용자명 또는 비밀번호
- Secret이 존재하지 않음
- Secret이 잘못된 네임스페이스에 생성됨

**해결 방법**:

1. **Secret 존재 여부 확인**:

   ```bash
   kubectl get secret -n <namespace>
   ```

1. **Secret 내용 확인**:

   ```bash
   kubectl get secret <secret-name> -n <namespace> -o jsonpath='{.data}'
   ```

   Base64 디코딩:

   ```bash
   echo "<base64-string>" | base64 -d
   ```

1. **config.yaml 설정 확인**:

   ```yaml
   apps:
     airflow:
       specs:
         values:
           postgresql:
             auth:
               username: airflow_user
               password: "{{ .Secrets.postgresql.password }}"
               database: airflow_db
   ```

1. **데이터베이스 직접 연결 테스트**:

   ```bash
   # PostgreSQL
   kubectl run -it --rm psql-test --image=postgres:15 --restart=Never -- \
     psql -h postgresql.data.svc.cluster.local -U airflow_user -d airflow_db

   # MySQL
   kubectl run -it --rm mysql-test --image=mysql:8 --restart=Never -- \
     mysql -h mysql.data.svc.cluster.local -u airflow_user -p
   ```

1. **Secret 재생성** (필요시):

   ```bash
   kubectl delete secret <secret-name> -n <namespace>
   kubectl create secret generic <secret-name> \
     --from-literal=username=airflow_user \
     --from-literal=password=<new-password> \
     -n <namespace>
   ```

### DatabaseConnectionError

**증상**: 데이터베이스 연결 실패

```
connection to server at "postgresql.data.svc.cluster.local", port 5432 failed: connection refused
```

**원인**:

- 데이터베이스 Pod가 실행 중이 아님
- 서비스가 존재하지 않음
- 네트워크 정책으로 차단됨
- 잘못된 호스트명/포트

**해결 방법**:

1. **DB 서비스 상태 확인**:

   ```bash
   kubectl get svc -n <namespace>
   kubectl describe svc <db-service-name> -n <namespace>
   ```

1. **DB Pod 상태 확인**:

   ```bash
   kubectl get pods -n <namespace>
   kubectl logs <db-pod-name> -n <namespace>
   kubectl describe pod <db-pod-name> -n <namespace>
   ```

1. **네트워크 정책 확인**:

   ```bash
   kubectl get networkpolicy -n <namespace>
   ```

1. **DB 엔드포인트 확인**:

   ```bash
   kubectl get endpoints <db-service-name> -n <namespace>
   ```

1. **config.yaml 호스트명/포트 확인**:

   ```yaml
   postgresql:
     host: postgresql.data.svc.cluster.local  # 올바른 서비스명
     port: 5432
   ```

______________________________________________________________________

## Helm 릴리스 에러

### HelmReleaseError

**증상**: Helm 배포 실패 또는 pending-install 상태

```
Error: INSTALLATION FAILED: release airflow failed
Error: another operation (install/upgrade/rollback) is in progress
```

**원인**:

- 이전 배포가 실패하고 릴리스가 pending 상태로 남아있음
- Helm 차트 값 오류
- 리소스 충돌 (이미 존재하는 리소스)
- Init container 실패

**해결 방법**:

1. **Helm 릴리스 상태 확인**:

   ```bash
   helm list -n <namespace> --all
   helm status <release-name> -n <namespace>
   ```

1. **릴리스 히스토리 확인**:

   ```bash
   helm history <release-name> -n <namespace>
   ```

1. **Pending 릴리스 정리**:

   **방법 1: Rollback (권장)**

   ```bash
   helm rollback <release-name> -n <namespace>
   ```

   **방법 2: Uninstall**

   ```bash
   helm uninstall <release-name> -n <namespace>
   ```

1. **Pod 이벤트 확인** (실패 원인 파악):

   ```bash
   kubectl get events -n <namespace> --sort-by='.lastTimestamp'
   kubectl describe pod <pod-name> -n <namespace>
   ```

1. **Pod 로그 확인** (Init container 포함):

   ```bash
   # Init container 로그
   kubectl logs <pod-name> -c <init-container-name> -n <namespace>

   # 메인 container 로그
   kubectl logs <pod-name> -n <namespace>
   ```

1. **재배포**:

   ```bash
   sbkube apply --app-dir <app-dir> --app <app-name>
   ```

### 예시: Airflow pending-install 해결

```bash
# 1. 현재 상태 확인
helm list -n airflow --all

# 출력:
# NAME     NAMESPACE  REVISION  STATUS         CHART           APP VERSION
# airflow  airflow    1         pending-install apache-airflow  2.x.x

# 2. Pending 릴리스 삭제
helm uninstall airflow -n airflow

# 3. 네임스페이스 정리 (선택)
kubectl delete all --all -n airflow

# 4. 재배포
sbkube apply --app-dir app_220_orchestration_airflow --app airflow
```

______________________________________________________________________

## Kubernetes 연결 에러

### KubernetesConnectionError

**증상**: Kubernetes API 서버 연결 실패

```
Unable to connect to the server: dial tcp 127.0.0.1:6443: connection refused
```

**해결 방법**:

1. **클러스터 상태 확인**:

   ```bash
   kubectl cluster-info
   ```

1. **현재 컨텍스트 확인**:

   ```bash
   kubectl config current-context
   kubectl config get-contexts
   ```

1. **kubeconfig 경로 확인**:

   ```bash
   echo $KUBECONFIG
   ```

1. **SBKube doctor 실행**:

   ```bash
   sbkube doctor
   ```

______________________________________________________________________

## 네임스페이스 에러

### NamespaceNotFoundError

**증상**: 네임스페이스가 존재하지 않음

```
Error from server (NotFound): namespaces "airflow" not found
```

**해결 방법**:

1. **네임스페이스 목록 확인**:

   ```bash
   kubectl get namespaces
   ```

1. **네임스페이스 생성**:

   ```bash
   kubectl create namespace <namespace>
   ```

   또는 config.yaml에서:

   ```yaml
   namespace: airflow
   create_namespace: true  # 자동 생성
   ```

1. **재배포**:

   ```bash
   sbkube apply --app-dir <app-dir>
   ```

______________________________________________________________________

## 일반적인 해결 전략

### 1. 진단 도구 사용

```bash
# 시스템 전반 진단
sbkube doctor

# 배포 히스토리 확인
sbkube history --namespace <namespace>

# 배포 상태 확인
sbkube state list
```

### 2. 로그 및 이벤트 확인

```bash
# Pod 로그
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -c <container-name> -n <namespace>

# 이벤트
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Pod 상세 정보
kubectl describe pod <pod-name> -n <namespace>
```

### 3. 리소스 상태 확인

```bash
# 전체 리소스
kubectl get all -n <namespace>

# 특정 리소스
kubectl get pods,svc,secrets,configmaps -n <namespace>
```

### 4. 설정 검증

```bash
# config.yaml 검증
sbkube validate --app-dir <app-dir>

# Dry-run 테스트
sbkube apply --app-dir <app-dir> --dry-run
```

### 5. 단계별 실행 (디버깅)

```bash
# 각 단계를 개별적으로 실행
sbkube prepare --app-dir <app-dir> --app <app-name>
sbkube build --app-dir <app-dir> --app <app-name>
sbkube deploy --app-dir <app-dir> --app <app-name>
```

______________________________________________________________________

## 자주 묻는 질문 (FAQ)

### Q: "Init:CrashLoopBackOff" 상태는 무엇인가요?

**A**: Init container가 반복적으로 실패하고 있습니다. 주로 다음 원인:

- 데이터베이스 연결 실패
- Secret 누락
- 네트워크 문제

**해결**: Init container 로그 확인

```bash
kubectl logs <pod-name> -c <init-container-name> -n <namespace>
```

### Q: 배포는 성공했지만 Pod가 Running이 되지 않아요

**A**: Pod 이벤트와 로그를 확인하세요:

```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
```

### Q: "already exists" 에러가 발생해요

**A**: 리소스가 이미 존재합니다. 기존 리소스 삭제 후 재배포:

```bash
sbkube delete --app-dir <app-dir> --app <app-name>
sbkube apply --app-dir <app-dir> --app <app-name>
```

______________________________________________________________________

## 추가 리소스

- [SBKube 명령어 레퍼런스](../02-features/commands.md)
- [설정 스키마](../03-configuration/config-schema.md)
- [일반 트러블슈팅](README.md)
- [개발 환경 이슈](common-dev-issues.md)

______________________________________________________________________

**문서 버전**: 1.0 **최종 업데이트**: 2025-01-04 **SBKube 버전**: v0.6.1+
