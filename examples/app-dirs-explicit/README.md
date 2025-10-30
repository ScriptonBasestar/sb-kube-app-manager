# App Dirs Explicit List Example

이 예제는 `sources.yaml`의 `app_dirs` 필드를 사용하여 배포할 앱 그룹을 명시적으로 지정하는 방법을 보여줍니다.

## 프로젝트 구조

```
examples/app-dirs-explicit/
├── sources.yaml          # app_dirs 목록 포함
├── redis/config.yaml     # ✅ 배포됨 (app_dirs에 포함)
├── postgres/config.yaml  # ✅ 배포됨 (app_dirs에 포함)
└── nginx/config.yaml     # ❌ 배포 제외 (app_dirs에 미포함)
```

## sources.yaml 설정

```yaml
kubeconfig: "~/.kube/config"
kubeconfig_context: "minikube"

# 명시적으로 배포할 앱 디렉토리 지정
app_dirs:
  - redis
  - postgres
  # nginx는 의도적으로 제외

helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami
```

## 사용 방법

### 1. 명시적 목록에 따라 배포

```bash
# redis, postgres만 배포 (nginx 제외)
sbkube deploy --base-dir examples/app-dirs-explicit
```

**출력:**
```
📂 Using app_dirs from sources.yaml (2 group(s)):
  - postgres/
  - redis/
```

### 2. 특정 앱 그룹만 배포

```bash
# 특정 앱 그룹만 배포 (app_dirs 설정 무시)
sbkube deploy --base-dir examples/app-dirs-explicit --app-dir redis
```

## 주요 특징

### ✅ 장점

1. **선택적 배포**: 필요한 앱만 배포 가능
2. **실수 방지**: 의도하지 않은 앱 배포 방지
3. **명확한 제어**: 배포 대상이 명확히 문서화됨
4. **환경별 분리**: 개발/스테이징/프로덕션 환경별 설정 가능

### 📋 비교: 명시적 목록 vs 자동 탐색

| 기능 | 명시적 목록 (`app_dirs` 지정) | 자동 탐색 (`app_dirs` 미지정) |
|------|-------------------------------|-------------------------------|
| 배포 대상 | `app_dirs`에 명시된 것만 | `config.yaml` 있는 모든 디렉토리 |
| 제어 수준 | 높음 (명시적) | 낮음 (자동) |
| 실수 위험 | 낮음 | 높음 (의도치 않은 배포 가능) |
| 유지보수 | 수동 업데이트 필요 | 자동 |

## 실전 활용 사례

### 1. 환경별 분리

```yaml
# sources-dev.yaml
app_dirs:
  - redis      # 개발용만
  - postgres

# sources-prd.yaml
app_dirs:
  - redis
  - postgres
  - nginx      # 프로덕션에만 추가
```

### 2. 단계적 롤아웃

```yaml
# 1단계: 핵심 서비스만
app_dirs:
  - postgres

# 2단계: 캐시 추가
app_dirs:
  - postgres
  - redis

# 3단계: 전체
app_dirs:
  - postgres
  - redis
  - nginx
```

## 검증

### app_dirs 목록 확인

```bash
# sources.yaml 로드 및 app_dirs 확인
yq '.app_dirs' examples/app-dirs-explicit/sources.yaml
```

**출력:**
```yaml
- redis
- postgres
```

### 실제 배포 확인 (dry-run)

```bash
sbkube deploy --base-dir examples/app-dirs-explicit --dry-run
```

## 문제 해결

### 오류: 존재하지 않는 디렉토리

**증상:**
```
❌ Invalid app_dirs in sources.yaml:
  - Directory not found: nonexistent
```

**해결:**
- `app_dirs` 목록에서 해당 디렉토리 제거
- 또는 실제 디렉토리 생성

### 오류: config.yaml 없음

**증상:**
```
❌ Invalid app_dirs in sources.yaml:
  - Config file not found: redis/config.yaml
```

**해결:**
- 해당 디렉토리에 `config.yaml` 생성
- 또는 `app_dirs`에서 제거

## 참고

- **app_dirs 미지정**: 자동 탐색 모드로 동작 (기존 동작 유지)
- **빈 리스트 금지**: `app_dirs: []`는 오류 (필드 자체를 제거해야 함)
- **중복 금지**: `app_dirs: [redis, redis]`는 검증 오류
- **경로 금지**: `app_dirs: [apps/redis]`는 디렉토리 이름만 허용
