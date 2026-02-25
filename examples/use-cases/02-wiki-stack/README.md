# Use Case 02: MediaWiki Stack with Traefik Ingress

k3s 클러스터에 MediaWiki를 Traefik Ingress와 MySQL로 구축하는 완전한 예제입니다.

## 시나리오

프로덕션급 Wiki 시스템을 k3s에 배포합니다:

1. **Traefik** - k3s 기본 Ingress Controller (이미 설치됨)
2. **MySQL** - MediaWiki 데이터베이스
3. **MediaWiki** - Wiki 애플리케이션
4. **Ingress** - Traefik을 통한 외부 접근

## 아키텍처

```
                    ┌──────────────┐
                    │   Internet   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   Traefik    │
                    │  (k3s 기본)   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  MediaWiki   │
                    │   Service    │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼───────┐        ┌───────▼──────┐
       │  MediaWiki   │        │    MySQL     │
       │     Pod      │───────▶│   Service    │
       └──────────────┘        └──────────────┘
```

## 사전 준비

### 1. k3s 클러스터 확인
```bash
# k3s가 실행 중인지 확인
kubectl get nodes

# Traefik이 설치되어 있는지 확인
kubectl get pods -n kube-system | grep traefik
```

### 2. 도메인 설정 (로컬 테스트용)
```bash
# /etc/hosts에 추가
sudo bash -c 'echo "127.0.0.1 wiki.local" >> /etc/hosts'
```

## 배포 순서

### 1. MySQL 먼저 배포
```bash
sbkube apply -f sbkube.yaml --apps mysql
```

### 2. MySQL이 Ready 상태인지 확인
```bash
kubectl get pods -n wiki-stack -l app.kubernetes.io/name=mysql -w
```

### 3. MediaWiki 배포
```bash
sbkube apply -f sbkube.yaml --apps mediawiki
```

### 4. Ingress 배포
```bash
sbkube apply -f sbkube.yaml --apps wiki-ingress
```

### 또는 전체 한번에 배포 (depends_on 사용)
```bash
sbkube apply -f sbkube.yaml
```

## 접근

### 웹 브라우저로 접근
```
http://wiki.local
```

### MediaWiki 초기 설정

1. 브라우저에서 `http://wiki.local` 접속
2. "Set up the wiki" 클릭
3. 데이터베이스 설정:
   - Database host: `mysql.wiki-stack.svc.cluster.local`
   - Database name: `mediawiki`
   - Database username: `mediawiki`
   - Database password: `wiki-password`
4. 나머지 설정 완료

### MySQL 직접 접근 (디버깅용)
```bash
# MySQL Pod에 접속
MYSQL_POD=$(kubectl get pods -n wiki-stack -l app.kubernetes.io/name=mysql -o jsonpath="{.items[0].metadata.name}")
kubectl exec -it $MYSQL_POD -n wiki-stack -- mysql -u mediawiki -p
# Password: wiki-password

# 데이터베이스 확인
SHOW DATABASES;
USE mediawiki;
SHOW TABLES;
```

## 고급 설정

### HTTPS 활성화 (cert-manager 사용)

1. cert-manager 설치:
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

2. `wiki-ingress-values.yaml` 수정:
```yaml
ingress:
  enabled: true
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  tls:
    - secretName: wiki-tls
      hosts:
        - wiki.yourdomain.com
```

### 프로덕션 환경 설정

#### MySQL 고가용성
```yaml
architecture: replication
auth:
  replicationPassword: "replication-password"
secondary:
  replicaCount: 2
```

#### MediaWiki 스케일링
```yaml
replicaCount: 3
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 80
```

#### 데이터 백업
```bash
# MySQL 백업
kubectl exec -n wiki-stack mysql-0 -- mysqldump -u mediawiki -pwiki-password mediawiki > wiki-backup.sql

# 복원
kubectl exec -i -n wiki-stack mysql-0 -- mysql -u mediawiki -pwiki-password mediawiki < wiki-backup.sql
```

## 모니터링

### Pod 상태 확인
```bash
# 모든 리소스 확인
kubectl get all -n wiki-stack

# Pod 상세 정보
kubectl describe pod -n wiki-stack <pod-name>

# 로그 확인
kubectl logs -n wiki-stack <pod-name> -f
```

### Traefik Dashboard 접근
```bash
# Traefik 대시보드 포트포워딩
kubectl port-forward -n kube-system $(kubectl get pods -n kube-system -l app.kubernetes.io/name=traefik -o name) 9000:9000

# 브라우저에서 http://localhost:9000/dashboard/ 접속
```

### 리소스 사용량 확인
```bash
kubectl top pods -n wiki-stack
kubectl top nodes
```

## 트러블슈팅

### MediaWiki가 MySQL에 연결 못함
```bash
# MySQL 서비스 확인
kubectl get svc -n wiki-stack mysql

# DNS 확인
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup mysql.wiki-stack.svc.cluster.local
```

### Ingress가 작동 안함
```bash
# Ingress 리소스 확인
kubectl get ingress -n wiki-stack
kubectl describe ingress -n wiki-stack wiki-ingress

# Traefik 로그 확인
kubectl logs -n kube-system -l app.kubernetes.io/name=traefik
```

### Pod가 CrashLoopBackOff 상태
```bash
# Pod 이벤트 확인
kubectl describe pod -n wiki-stack <pod-name>

# Pod 로그 확인
kubectl logs -n wiki-stack <pod-name> --previous
```

## 정리

```bash
# 전체 스택 삭제
sbkube delete -f sbkube.yaml

# 또는
kubectl delete namespace wiki-stack
```

## ⚠️ 보안 경고 (Security Warning)

**이 Wiki 스택 예제는 데모 목적으로 하드코딩된 인증 정보를 사용합니다.**

**프로덕션 환경에서는 절대 사용하지 마세요!**

### 예제에 포함된 하드코딩된 인증 정보

**MySQL** (`manifests/mysql.yaml`):
- Root Password: `rootpassword`
- Database: `wikidb`
- User: `wikiuser`
- Password: `wikipassword`

**MediaWiki** (`manifests/mediawiki.yaml`):
- DB Connection: MySQL 인증 정보 환경 변수로 주입
- Admin 계정: 초기 설정 시 생성

### 프로덕션 환경 필수 보안 조치

1. **Kubernetes Secrets 사용**:
   ```bash
   # MySQL 인증 정보를 Secret으로 생성
   kubectl create secret generic mysql-credentials \
     --namespace wiki-stack \
     --from-literal=root-password=$(openssl rand -base64 32) \
     --from-literal=username=wikiuser \
     --from-literal=password=$(openssl rand -base64 32) \
     --from-literal=database=wikidb

   # MediaWiki에서 Secret 참조
   env:
   - name: MEDIAWIKI_DB_PASSWORD
     valueFrom:
       secretKeyRef:
         name: mysql-credentials
         key: password
   ```

2. **External Secrets Operator 사용**:
   - AWS Secrets Manager
   - GCP Secret Manager
   - Azure Key Vault
   - HashiCorp Vault

3. **HTTPS 필수 적용**:
   ```bash
   # cert-manager 설치
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

   # Let's Encrypt 자동 인증서 발급
   ```

4. **네트워크 보안**:
   ```yaml
   # NetworkPolicy로 MySQL 접근 제한
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: mysql-policy
     namespace: wiki-stack
   spec:
     podSelector:
       matchLabels:
         app: mysql
     policyTypes:
     - Ingress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: mediawiki
       ports:
       - protocol: TCP
         port: 3306
   ```

5. **정기 보안 업데이트**:
   - MediaWiki 버전 업데이트
   - MySQL 보안 패치 적용
   - 취약점 스캔 정기 실행

6. **백업 및 복구 전략**:
   ```bash
   # 정기 백업 CronJob 설정
   # 백업 암호화
   # 외부 스토리지 저장
   ```

자세한 내용은 다음 문서를 참조하세요:
- [Kubernetes Secrets 문서](https://kubernetes.io/docs/concepts/configuration/secret/)
- [MediaWiki Security](https://www.mediawiki.org/wiki/Manual:Security)
- [MySQL Security Best Practices](https://dev.mysql.com/doc/refman/8.0/en/security-guidelines.html)

## 프로덕션 체크리스트

- [ ] **보안**: Kubernetes Secrets로 인증 정보 관리
- [ ] **보안**: 강력한 비밀번호 생성 (최소 32자)
- [ ] **보안**: HTTPS 인증서 설정 (Let's Encrypt)
- [ ] **보안**: NetworkPolicy 적용
- [ ] MySQL persistence 활성화 (최소 20Gi)
- [ ] 리소스 제한 적절히 조정
- [ ] 백업 정책 수립 (일 1회 이상)
- [ ] 모니터링 설정 (Prometheus, Grafana)
- [ ] 로그 수집 설정 (ELK Stack)
- [ ] 정기 보안 업데이트 계획

## 관련 예제

- [Use Case 01: Development Environment](../01-dev-environment/)
- [Use Case 03: Monitoring Stack](../03-monitoring/)
- [App Type: YAML](../../app-types/03-yaml/)
