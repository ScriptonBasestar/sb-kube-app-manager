# 🧪 QA 시나리오: 프로파일 시스템 테스트

## 📌 테스트 대상
- **작업 ID**: 006, 007
- **기능**: 환경별 프로파일 시스템 및 로더
- **우선순위**: 🟡 High

## 🎯 테스트 목표
환경별 배포를 위한 프로파일 시스템이 올바르게 작동하고, 설정 병합 및 우선순위가 정확히 적용되는지 검증합니다.

---

## 📋 테스트 시나리오

### 1️⃣ 프로파일 발견 및 로드 테스트

#### 1.1 기본 프로파일 발견
```bash
# 프로파일 설정 생성
mkdir test-profiles && cd test-profiles
sbkube init --non-interactive

# 환경별 설정 파일 생성
cp config/config.yaml config/config-development.yaml
cp config/config.yaml config/config-staging.yaml
cp config/config.yaml config/config-production.yaml

# 프로파일 목록 확인
sbkube run --help | grep -A 20 "profile"
```

**예상 결과:**
- ✅ 3개 프로파일 자동 발견: development, staging, production
- ✅ --profile 옵션 도움말에 사용 가능한 프로파일 표시

#### 1.2 프로파일 로드 및 적용
```bash
# development 프로파일로 실행
sbkube run --profile development --dry-run

# production 프로파일로 실행
sbkube run --profile production --dry-run
```

**검증 항목:**
- ✅ 올바른 설정 파일 로드 (config-development.yaml)
- ✅ 네임스페이스 변경 확인
- ✅ 환경별 values 파일 사용

---

### 2️⃣ 설정 병합 및 우선순위 테스트

#### 2.1 기본 설정과 프로파일 병합
```bash
# 기본 설정에만 있는 항목 추가
cat >> config/config.yaml << EOF
custom_setting: base_value
common_apps:
  - name: common-app
    type: install-helm
EOF

# 프로파일에서 일부 오버라이드
cat >> config/config-development.yaml << EOF
custom_setting: dev_value
namespace: my-app-dev
EOF

# 실행 및 확인
sbkube run --profile development --only prepare --dry-run
```

**예상 결과:**
- ✅ custom_setting: dev_value (오버라이드됨)
- ✅ common_apps: 기본 설정에서 유지
- ✅ namespace: my-app-dev (프로파일에서 적용)

#### 2.2 딥 머지 동작 확인
```bash
# 중첩된 설정 구조 생성
cat > config/config.yaml << EOF
namespace: default
apps:
  - name: app1
    type: install-helm
    specs:
      values:
        - common-values.yaml
      settings:
        replicas: 1
        resources:
          cpu: 100m
          memory: 128Mi
EOF

# 프로파일에서 부분 오버라이드
cat > config/config-production.yaml << EOF
apps:
  - name: app1
    specs:
      values:
        - prod-values.yaml  # 추가됨
      settings:
        replicas: 3        # 변경됨
        # resources는 그대로 유지
EOF

sbkube run --profile production --only template
```

**예상 결과:**
- ✅ values: [common-values.yaml, prod-values.yaml] (병합)
- ✅ replicas: 3 (오버라이드)
- ✅ resources: 기본값 유지 (cpu: 100m, memory: 128Mi)

---

### 3️⃣ Values 파일 경로 해결 테스트

#### 3.1 환경별 values 디렉토리
```bash
# 환경별 values 구조 생성
mkdir -p values/{common,development,production}

# 각 환경별 values 파일 생성
echo "env: common" > values/common/base-values.yaml
echo "env: development" > values/development/app-values.yaml
echo "env: production" > values/production/app-values.yaml

# 설정에서 values 참조
cat > config/config.yaml << EOF
apps:
  - name: myapp
    type: install-helm
    specs:
      values:
        - common/base-values.yaml
        - app-values.yaml  # 환경별로 다른 파일
EOF

# 각 환경으로 실행
sbkube run --profile development --only template
sbkube run --profile production --only template
```

**예상 결과:**
- ✅ development: values/common/base-values.yaml + values/development/app-values.yaml
- ✅ production: values/common/base-values.yaml + values/production/app-values.yaml

#### 3.2 Values 파일 누락 처리
```bash
# 존재하지 않는 values 파일 참조
cat > config/config-staging.yaml << EOF
apps:
  - name: myapp
    specs:
      values:
        - missing-values.yaml
EOF

sbkube run --profile staging --only prepare
```

**예상 결과:**
- ❌ 오류: "Values 파일을 찾을 수 없습니다: missing-values.yaml"
- ✅ 검색 경로 표시: values/, values/staging/, values/common/

---

### 4️⃣ 프로파일 상속 테스트

#### 4.1 기본 상속
```bash
# base 프로파일 생성
cat > config/config-base.yaml << EOF
namespace: base-namespace
common_settings:
  log_level: info
  timeout: 30
EOF

# development이 base를 상속
cat > config/config-development.yaml << EOF
extends: base
namespace: dev-namespace
common_settings:
  log_level: debug  # 오버라이드
EOF

sbkube run --profile development --dry-run
```

**예상 결과:**
- ✅ namespace: dev-namespace (오버라이드)
- ✅ log_level: debug (오버라이드)
- ✅ timeout: 30 (상속됨)

#### 4.2 순환 상속 감지
```bash
# 순환 상속 구성
cat > config/config-a.yaml << EOF
extends: b
EOF

cat > config/config-b.yaml << EOF
extends: a
EOF

sbkube run --profile a
```

**예상 결과:**
- ❌ 오류: "순환 상속이 감지되었습니다: a → b → a"
- ✅ 상속 체인 표시

---

### 5️⃣ CLI 옵션 우선순위 테스트

#### 5.1 명령행 인수 최우선
```bash
# 프로파일에서 app 지정
cat > config/config-production.yaml << EOF
target_app_name: prod-app
EOF

# CLI에서 다른 app 지정
sbkube run --profile production --app cli-app --dry-run
```

**예상 결과:**
- ✅ 실행되는 앱: cli-app (CLI 인수 우선)
- ✅ 프로파일 설정은 무시됨

#### 5.2 환경 변수 우선순위
```bash
# 환경 변수 설정
export SBKUBE_NAMESPACE=env-namespace

# 프로파일 실행
sbkube run --profile development --dry-run
```

**예상 결과:**
- ✅ namespace: env-namespace (환경 변수 우선)
- ✅ 프로파일의 namespace 설정 무시

---

### 6️⃣ 프로파일 검증 테스트

#### 6.1 유효성 검사
```bash
# 잘못된 프로파일 생성
cat > config/config-invalid.yaml << EOF
# 필수 필드 누락
apps:
  - name: app1
    # type 누락
EOF

sbkube run --profile invalid
```

**예상 결과:**
- ❌ 오류: "프로파일 검증 실패"
- ✅ 구체적 오류: "app1: 'type' 필드가 필요합니다"

#### 6.2 프로파일 정보 표시
```bash
# 프로파일 정보 확인 (가상의 명령어)
sbkube profile list
sbkube profile show production
```

**예상 결과:**
- ✅ 사용 가능한 프로파일 목록
- ✅ 각 프로파일의 주요 설정 표시
- ✅ 검증 상태 표시

---

## 🔍 검증 체크리스트

### 핵심 기능
- [ ] 프로파일 자동 발견
- [ ] 설정 파일 병합
- [ ] Values 경로 해결
- [ ] 프로파일 상속
- [ ] 우선순위 시스템

### 오류 처리
- [ ] 누락된 프로파일
- [ ] 잘못된 설정
- [ ] 순환 상속
- [ ] 파일 접근 권한

### 통합 테스트
- [ ] Run 명령어 통합
- [ ] 다른 옵션과 조합
- [ ] 환경 변수 처리
- [ ] 재시작 기능 호환

---

## 📊 테스트 결과 기록

| 테스트 항목 | 상태 | 실행일 | 담당자 | 비고 |
|-----------|------|--------|---------|------|
| 프로파일 발견 | - | - | - | - |
| 설정 병합 | - | - | - | - |
| Values 해결 | - | - | - | - |
| 프로파일 상속 | - | - | - | - |
| 우선순위 | - | - | - | - |

---

## 🐛 발견된 이슈

### 이슈 템플릿
```markdown
**이슈 ID**: PROFILE-001
**심각도**: High/Medium/Low
**프로파일**: 
**재현 단계**:
1. 
2. 

**예상 동작**:

**실제 동작**:

**설정 파일**:
```

---

## 📝 개선 제안

1. **프로파일 관리**
   - 프로파일 생성 마법사
   - 프로파일 간 차이점 비교
   - 프로파일 검증 도구

2. **설정 병합 개선**
   - 병합 전략 선택 옵션
   - 병합 결과 미리보기
   - 충돌 해결 가이드

3. **개발자 경험**
   - 프로파일별 자동 완성
   - 설정 스키마 검증
   - 마이그레이션 도구