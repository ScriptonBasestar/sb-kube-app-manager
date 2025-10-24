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
sbkube apply --app-dir . --apps mysql
```

### 2. MySQL이 Ready 상태인지 확인
```bash
kubectl get pods -n wiki-stack -l app.kubernetes.io/name=mysql -w
```

### 3. MediaWiki 배포
```bash
sbkube apply --app-dir . --apps mediawiki
```

### 4. Ingress 배포
```bash
sbkube apply --app-dir . --apps wiki-ingress
```

### 또는 전체 한번에 배포 (depends_on 사용)
```bash
sbkube apply --app-dir .
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
sbkube delete --app-dir .

# 또는
kubectl delete namespace wiki-stack
```

## 프로덕션 체크리스트

- [ ] MySQL persistence 활성화
- [ ] 강력한 비밀번호 사용
- [ ] HTTPS 인증서 설정
- [ ] 리소스 제한 적절히 조정
- [ ] 백업 정책 수립
- [ ] 모니터링 설정
- [ ] 로그 수집 설정
- [ ] NetworkPolicy 적용

## 관련 예제

- [Use Case 01: Development Environment](../01-dev-environment/)
- [Use Case 03: Monitoring Stack](../03-monitoring/)
- [App Type: YAML](../../app-types/03-yaml/)
