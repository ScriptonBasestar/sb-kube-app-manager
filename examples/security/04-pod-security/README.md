# Security: Pod Security

Pod SecurityContext를 사용하여 컨테이너 보안을 강화하는 예제입니다.

## 📋 개요

**카테고리**: Security

**구성 요소**:
- **Secure Pod**: 보안 강화된 Pod (non-root, read-only FS)
- **Insecure Pod**: 기본 설정 Pod (비교용)
- **SecurityContext**: Pod/Container 보안 설정

**학습 목표**:
- 최소 권한 원칙 적용
- 읽기 전용 파일시스템
- Non-root 실행
- Capabilities 제한

## 🎯 보안 베스트 프랙티스

### 1. Non-root User

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
```

### 2. 읽기 전용 루트 파일시스템

```yaml
securityContext:
  readOnlyRootFilesystem: true
```

### 3. Capabilities 제거

```yaml
securityContext:
  capabilities:
    drop:
    - ALL
```

### 4. Privilege Escalation 방지

```yaml
securityContext:
  allowPrivilegeEscalation: false
```

## 🚀 빠른 시작

```bash
sbkube apply -f sbkube.yaml \
  --app-dir examples/security/04-pod-security \
  --namespace podsec-demo
```

## 📖 SecurityContext 레벨

### Pod 레벨

```yaml
spec:
  securityContext:  # 모든 컨테이너에 적용
    runAsUser: 1000
    fsGroup: 2000
```

### Container 레벨

```yaml
spec:
  containers:
  - name: app
    securityContext:  # 이 컨테이너만
      readOnlyRootFilesystem: true
```

## 💡 실전 패턴

### 최고 보안 설정

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 3000
  fsGroup: 2000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
  seccompProfile:
    type: RuntimeDefault
```

## 🔍 트러블슈팅

### 문제: 앱이 파일을 쓸 수 없음

**해결**: emptyDir 볼륨 마운트

```yaml
volumeMounts:
- name: tmp
  mountPath: /tmp
volumes:
- name: tmp
  emptyDir: {}
```

## 📚 참고 자료

- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [SecurityContext](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)

## 🧹 정리

```bash
kubectl delete namespace podsec-demo
```

---

**안전한 Pod 설정으로 공격 표면을 최소화하세요! 🔒**
