# Pre-Deploy Tasks - 배포 전 검증 예제

> **목적**: pre_deploy_tasks를 사용한 배포 전 검증 시나리오
> **Phase**: Phase 2/3 Tasks
> **난이도**: ⭐⭐ 중급

## 📚 배울 수 있는 것

- ✅ `pre_deploy_tasks` 사용법 (배포 전 실행)
- ✅ 배포 전 필수 리소스 확인
- ✅ 배포 전 환경 검증
- ✅ Secret/ConfigMap 사전 생성

## 🎯 시나리오

애플리케이션 배포 전에 다음을 확인하고 준비합니다:

1. Namespace 존재 확인 (없으면 생성)
2. 필수 Secret 생성 (DB 접속 정보)
3. ConfigMap 사전 배포
4. 환경 검증 (Storage Class, Ingress Controller 등)

## 🏗️ 구조

```
hooks-pre-deploy-tasks/
├── README.md
├── config.yaml
├── manifests/
│   ├── namespace.yaml
│   ├── secret.yaml
│   └── app-config.yaml
└── scripts/
    └── verify-environment.sh
```

## 🚀 실행 방법

```bash
# 배포 실행
sbkube deploy --app-dir examples/hooks-pre-deploy-tasks --namespace pre-deploy-test

# 결과 확인
kubectl get all -n pre-deploy-test
kubectl get secret -n pre-deploy-test db-credentials
kubectl get configmap -n pre-deploy-test app-config

# 정리
kubectl delete namespace pre-deploy-test
```

## 📖 실행 순서

```
1. pre_deploy_tasks 실행 (메인 배포 전)
   ├─ Task 1: Namespace 확인/생성
   ├─ Task 2: Secret 생성
   ├─ Task 3: ConfigMap 배포
   └─ Task 4: 환경 검증

2. ── MAIN DEPLOYMENT (PostgreSQL Helm) ──

3. post_deploy_tasks 실행
   └─ Task: 배포 검증
```

## 🔗 다음 단계

- **[hooks-error-handling/](../hooks-error-handling/)** - 에러 처리 학습
- **[hooks-phase3/](../hooks-phase3/)** - Validation/Rollback 학습
