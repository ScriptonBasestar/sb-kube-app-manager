# 📚 SBKube 튜토리얼

> SBKube를 처음 사용하는 분들을 위한 단계별 학습 가이드입니다.

---

## 🎯 학습 경로

튜토리얼은 난이도별로 구성되어 있으며, 순서대로 진행하는 것을 권장합니다.

```
01. 시작하기 (초급)
    ↓
02. 멀티 앱 배포 (중급)
    ↓
03. 프로덕션 배포 (고급)
    ↓
04. 커스터마이징 (고급)
    ↓
05. 문제 해결 (중급, 참조용)
```

---

## 📖 튜토리얼 목록

### 1. 🚀 시작하기 - 첫 번째 배포

**파일**: [01-getting-started.md](01-getting-started.md)

**난이도**: ⭐ 초급

**소요 시간**: 10-15분

**학습 목표**:

- SBKube 프로젝트 초기화
- 첫 번째 애플리케이션 배포 (Redis)
- 배포 상태 확인 및 히스토리 조회
- 애플리케이션 업그레이드 및 삭제

**사전 요구사항**:

- Kubernetes 클러스터 (Kind/Minikube/K3s)
- Helm v3 설치
- kubectl 설치

**핵심 개념**:

- `sbkube init` - 프로젝트 초기화
- `sbkube apply` - 통합 배포 워크플로우
- `config.yaml`, `sources.yaml` 설정 파일 구조
- `sbkube state` - 배포 상태 관리

**시작하기**:

```bash
# 튜토리얼 디렉토리 생성
mkdir my-first-sbkube-project
cd my-first-sbkube-project

# 튜토리얼 파일 열기
cat docs/08-tutorials/01-getting-started.md
```

---

### 2. 🏗️ 멀티 앱 배포 - 여러 앱 동시 관리

**파일**: [02-multi-app-deployment.md](02-multi-app-deployment.md)

**난이도**: ⭐⭐ 중급

**소요 시간**: 15-20분

**학습 목표**:

- 여러 애플리케이션을 하나의 설정으로 관리
- 앱 간 의존성 설정 (`depends_on`)
- 선택적 배포 (특정 앱만 배포)
- 통합 모니터링 및 관리

**사전 요구사항**:

- [01-getting-started.md](01-getting-started.md) 완료
- Kubernetes 기본 개념 이해

**핵심 개념**:

- Multi-app `config.yaml` 구조
- `depends_on` - 앱 의존성 관리
- `--app` 옵션 - 선택적 배포
- 배포 순서 자동 결정

**시나리오**: 4-Tier 웹 애플리케이션 스택 배포

- PostgreSQL (데이터베이스)
- Redis (캐시)
- Backend API (PostgreSQL, Redis 의존)
- Frontend (Backend API 의존)

---

### 3. 🏭 프로덕션 배포 - Best Practices

**파일**: [03-production-deployment.md](03-production-deployment.md)

**난이도**: ⭐⭐⭐ 고급

**소요 시간**: 30분

**학습 목표**:

- 프로덕션 환경 설정 관리 (dev/prod 분리)
- 고가용성 (HA) 구성
- 리소스 제한 및 요청 설정
- 안전한 배포 워크플로우
- 시크릿 및 보안 관리
- 모니터링 및 롤백 전략

**사전 요구사항**:

- [02-multi-app-deployment.md](02-multi-app-deployment.md) 완료
- 프로덕션 Kubernetes 경험

**핵심 개념**:

- 환경별 설정 디렉토리 (`values/dev/`, `values/prod/`)
- HA 구성 (replicaCount: 3, PodDisruptionBudget)
- 리소스 제한 (requests, limits)
- 보안 (RBAC, runAsNonRoot, Secret 관리)
- 롤링 업데이트 전략
- CI/CD 통합 (GitHub Actions 예제)

**체크리스트**:

- 배포 전 검증
- 배포 중 모니터링
- 배포 후 검증

---

### 4. 🎨 Helm 차트 커스터마이징

**파일**: [04-customization.md](04-customization.md)

**난이도**: ⭐⭐⭐ 고급

**소요 시간**: 25분

**학습 목표**:

- `overrides`를 사용한 차트 수정
- `removes`를 사용한 리소스 제거
- 복잡한 YAML 경로 탐색
- 커스터마이징 검증 및 디버깅

**사전 요구사항**:

- [01-getting-started.md](01-getting-started.md) 완료
- Helm 차트 구조 이해
- YAML 문법 숙지

**핵심 개념**:

- `overrides` - 기존 템플릿 파일 수정/추가
- `removes` - 불필요한 리소스 제거
- Helm 템플릿 문법 (`{{ }}`, `{{- }}`)
- `sbkube build` - 커스터마이징 적용
- `sbkube template` - 최종 결과 확인

**실습 예제**:

- ServiceMonitor 리소스 추가 (Prometheus)
- Deployment에 리소스 제한 추가
- ConfigMap 제거
- 공통 라벨 수정 (`_helpers.tpl` 오버라이드)

---

### 5. 🔧 문제 해결 가이드

**파일**: [05-troubleshooting.md](05-troubleshooting.md)

**난이도**: ⭐⭐ 중급 (참조용)

**소요 시간**: 문제별 5-15분

**학습 목표**:

- 일반적인 문제 진단 및 해결
- 명령어별 오류 처리
- 디버깅 도구 활용
- 체계적인 문제 해결 프로세스

**사전 요구사항**:

- [01-getting-started.md](01-getting-started.md) 완료
- 기본적인 Kubernetes 디버깅 경험

**주요 섹션**:

1. **일반적인 문제**

   - 명령어를 찾을 수 없음
   - Permission Denied
   - Kubernetes 클러스터 연결 실패

1. **prepare 명령어 오류**

   - Helm 리포지토리 추가 실패
   - Chart Pull 실패
   - Git Clone 실패

1. **build 명령어 오류**

   - Overrides 적용 실패
   - Removes 경로 오류

1. **deploy 명령어 오류**

   - Namespace가 없음
   - Helm 릴리스 충돌
   - Pod가 Pending 상태
   - ImagePullBackOff
   - CrashLoopBackOff

1. **설정 파일 오류**

   - Pydantic 검증 오류
   - sources.yaml을 찾을 수 없음
   - 순환 의존성

1. **Kubernetes 리소스 오류**

   - Service 연결 실패
   - PVC Bound 실패
   - Ingress 404

1. **디버깅 도구**

   - `sbkube --verbose`
   - `sbkube template`
   - `helm template`
   - `kubectl debug`

**사용 방법**: 문제 발생 시 해당 섹션을 찾아 단계별 해결 방법을 따라하세요.

---

## 🛠️ 사전 준비

모든 튜토리얼을 진행하기 전에 다음을 준비하세요:

### 1. SBKube 설치

```bash
# pip로 설치
pip install sbkube

# 또는 uv로 설치 (권장)
uv tool install sbkube

# 설치 확인
sbkube --version
# sbkube, version 0.4.7
```

### 2. Kubernetes 클러스터

**Kind 사용 (권장)**:

```bash
# Kind 설치
# https://kind.sigs.k8s.io/docs/user/quick-start/#installation

# 클러스터 생성
kind create cluster --name sbkube-tutorial

# 클러스터 확인
kubectl cluster-info
kubectl get nodes
```

**Minikube 사용**:

```bash
# Minikube 설치
# https://minikube.sigs.k8s.io/docs/start/

# 클러스터 시작
minikube start --profile sbkube-tutorial

# 컨텍스트 전환
kubectl config use-context sbkube-tutorial
```

### 3. 필수 도구 확인

```bash
# Helm 확인
helm version
# version.BuildInfo{Version:"v3.x.x", ...}

# kubectl 확인
kubectl version --client

# Git 확인
git --version
```

---

## 📂 디렉토리 구조 예시

튜토리얼 완료 후 예상 디렉토리 구조:

```
my-sbkube-projects/
├── 01-getting-started/
│   ├── config.yaml
│   ├── sources.yaml
│   ├── redis-values.yaml
│   ├── charts/
│   │   └── redis/
│   └── charts-built/  # build 후 생성
│       └── redis/
│
├── 02-multi-app/
│   ├── config.yaml
│   ├── sources.yaml
│   ├── values/
│   │   ├── postgres.yaml
│   │   ├── redis.yaml
│   │   ├── backend.yaml
│   │   └── frontend.yaml
│   └── charts/
│       ├── postgresql/
│       ├── redis/
│       ├── nginx/
│       └── nginx/
│
├── 03-production/
│   ├── config.yaml
│   ├── sources.yaml
│   ├── values/
│   │   ├── common/
│   │   │   └── app.yaml
│   │   ├── dev/
│   │   │   └── app.yaml
│   │   └── prod/
│   │       └── app.yaml
│   └── secrets/  # .gitignore에 추가
│       └── prod-secrets.yaml
│
└── 04-customization/
    ├── config.yaml  # overrides, removes 포함
    ├── sources.yaml
    ├── redis-values.yaml
    ├── charts/
    │   └── redis/  # 원본 차트
    └── charts-built/
        └── redis/  # 커스터마이징 적용된 차트
            └── templates/
                ├── servicemonitor.yaml  # 새로 추가된 파일
                └── master/
                    └── application.yaml  # 수정된 파일
```

---

## 🎓 학습 팁

### 초급자 (Kubernetes 경험 < 6개월)

1. **01-getting-started.md**부터 순서대로 진행
1. 각 명령어를 직접 실행하면서 출력 확인
1. `kubectl get pods -w`로 Pod 상태 변화 관찰
1. 문제 발생 시 **05-troubleshooting.md** 참조

### 중급자 (Kubernetes 경험 6개월-1년)

1. **01-getting-started.md**는 빠르게 훑어보기
1. **02-multi-app-deployment.md**에 집중
1. **03-production-deployment.md**의 Best Practice 학습
1. **04-customization.md**로 고급 기능 익히기

### 고급자 (Kubernetes 경험 > 1년)

1. **03-production-deployment.md**부터 시작
1. **04-customization.md**의 고급 패턴 학습
1. 실제 프로젝트에 적용하며 **05-troubleshooting.md** 참조
1. 추가 기능은 [메인 문서](../README.md) 참조

---

## 🔗 추가 자료

### 공식 문서

- [SBKube 개요](../../PRODUCT.md)
- [명령어 참조](../02-features/commands.md)
- [설정 스키마](../03-configuration/config-schema.md)
- [개발자 가이드](../04-development/README.md)

### 예제 코드

- [기본 예제](../../examples/basic/)
- [K3s 코드 서버 예제](../../examples/k3scode/)
- [고급 예제](../../examples/advanced-example/)

### 외부 자료

- [Helm 문서](https://helm.sh/docs/)
- [Kubernetes 문서](https://kubernetes.io/docs/)
- [kubectl 치트시트](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

---

## 💡 다음 단계

튜토리얼을 모두 완료했다면:

1. **실제 프로젝트에 적용**: 개발/스테이징 환경에서 SBKube 사용
1. **고급 기능 탐색**: [전체 문서](../README.md) 읽기
1. **커뮤니티 참여**: [GitHub Issues](https://github.com/your-org/sbkube/issues)에서 피드백 공유
1. **기여하기**: [CONTRIBUTING.md](../../CONTRIBUTING.md)를 읽고 기여 방법 확인

---

## 📝 피드백

튜토리얼에 대한 피드백이나 개선 제안은 [GitHub Issues](https://github.com/your-org/sbkube/issues)에 남겨주세요.

- 🐛 **버그 리포트**: 튜토리얼의 오류나 작동하지 않는 예제
- 💡 **개선 제안**: 더 나은 설명이나 추가 예제
- 📖 **새 튜토리얼 요청**: 다루지 않은 주제나 시나리오

---

**작성자**: SBKube Documentation Team **버전**: v0.4.10 **최종 업데이트**: 2025-10-30
