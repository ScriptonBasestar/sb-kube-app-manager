# 🧪 QA 시나리오: sbkube init 템플릿 시스템 테스트

## 📌 테스트 대상
- **작업 ID**: 005
- **기능**: `sbkube init` 프로젝트 초기화 명령어
- **우선순위**: 🔴 Critical

## 🎯 테스트 목표
`sbkube init` 명령어를 통한 프로젝트 초기화 기능을 검증하고, 템플릿 시스템의 정확성과 사용성을 확인합니다.

---

## 📋 테스트 시나리오

### 1️⃣ 기본 프로젝트 초기화 테스트

#### 1.1 대화형 초기화
```bash
# 새 디렉토리에서 테스트
mkdir test-init-interactive && cd test-init-interactive
sbkube init
```

**입력 시퀀스:**
1. 프로젝트 이름: `my-test-app` (Enter)
2. 기본 네임스페이스: (Enter로 기본값 사용)
3. 앱 이름: (Enter로 기본값 사용)
4. 애플리케이션 타입: `install-helm` (Enter)
5. 환경별 설정 생성: `Y` (Enter)
6. Bitnami Helm 저장소: `Y` (Enter)
7. Prometheus 모니터링: `N` (Enter)

**예상 결과:**
- ✅ 각 단계별 프롬프트 표시
- ✅ 기본값이 제안됨
- ✅ 다음 파일들이 생성됨:
  - `config/config.yaml`
  - `config/sources.yaml`
  - `config/config-development.yaml`
  - `config/config-staging.yaml`
  - `config/config-production.yaml`
  - `values/my-test-app-values.yaml`
  - `README.md`

#### 1.2 비대화형 초기화
```bash
mkdir test-init-batch && cd test-init-batch
sbkube init --non-interactive --name batch-app
```

**예상 결과:**
- ✅ 사용자 입력 없이 자동 생성
- ✅ 모든 기본값 적용
- ✅ 프로젝트명: `batch-app`

---

### 2️⃣ 템플릿 선택 테스트

#### 2.1 Basic 템플릿
```bash
sbkube init --template basic --non-interactive
```

**검증 항목:**
- ✅ 최소한의 설정 파일 생성
- ✅ 단순한 구조

#### 2.2 Web-app 템플릿
```bash
sbkube init --template web-app --non-interactive
```

**검증 항목:**
- ✅ 웹 애플리케이션 특화 설정
- ✅ Ingress 설정 포함
- ✅ 서비스 노출 설정

#### 2.3 Microservice 템플릿
```bash
sbkube init --template microservice --non-interactive
```

**검증 항목:**
- ✅ 마이크로서비스 패턴 설정
- ✅ 서비스 메시 설정
- ✅ 분산 추적 설정

---

### 3️⃣ 기존 파일 처리 테스트

#### 3.1 기존 파일 덮어쓰기 확인
```bash
# 기존 프로젝트에서 재실행
cd existing-project
sbkube init
```

**예상 동작:**
- ⚠️ 경고 메시지: "다음 파일들이 이미 존재합니다"
- ❓ 확인 프롬프트: "기존 파일을 덮어쓰시겠습니까?"
- ✅ N 선택시: 초기화 취소
- ✅ Y 선택시: 파일 덮어쓰기

#### 3.2 강제 덮어쓰기
```bash
sbkube init --force --non-interactive
```

**예상 결과:**
- ✅ 확인 없이 기존 파일 덮어쓰기
- ✅ 백업 파일 생성 없음

---

### 4️⃣ 템플릿 렌더링 검증

#### 4.1 변수 치환 확인
```bash
sbkube init --name "test-{{app}}" --non-interactive
cat config/config.yaml | grep namespace
```

**검증 항목:**
- ✅ 프로젝트명이 올바르게 치환됨
- ✅ 특수문자 이스케이프 처리
- ✅ Jinja2 문법 오류 없음

#### 4.2 조건부 렌더링
```bash
# Prometheus 비활성화 상태에서
sbkube init --non-interactive
grep prometheus config/sources.yaml
```

**예상 결과:**
- ✅ Prometheus 저장소 미포함
- ✅ 조건부 블록 정상 작동

---

### 5️⃣ 엣지 케이스 테스트

#### 5.1 특수문자 프로젝트명
```bash
sbkube init --name "my@special#app!" --non-interactive
```

**예상 결과:**
- ❌ 오류: "유효하지 않은 프로젝트명"
- ✅ 유효한 문자 안내

#### 5.2 긴 프로젝트명
```bash
sbkube init --name "this-is-a-very-long-project-name-that-exceeds-kubernetes-limits" --non-interactive
```

**예상 결과:**
- ⚠️ 경고: "프로젝트명이 너무 깁니다"
- ✅ 자동 축약 또는 오류

#### 5.3 권한 없는 디렉토리
```bash
sudo mkdir /root/test-init
cd /root/test-init
sbkube init --non-interactive
```

**예상 결과:**
- ❌ 오류: "파일 생성 권한이 없습니다"
- ✅ 권한 문제 해결 가이드

---

### 6️⃣ 생성된 파일 유효성 검증

#### 6.1 YAML 문법 검증
```bash
sbkube init --non-interactive
yamllint config/*.yaml values/*.yaml
```

**예상 결과:**
- ✅ 모든 YAML 파일 문법 정상
- ✅ 들여쓰기 일관성
- ✅ 따옴표 사용 일관성

#### 6.2 설정 파일 검증
```bash
sbkube validate
```

**예상 결과:**
- ✅ 생성된 설정으로 validate 통과
- ✅ 필수 필드 모두 포함
- ✅ 참조 무결성 확인

#### 6.3 README 링크 검증
```bash
# README의 링크들이 유효한지 확인
grep -oP 'https?://[^\s]+' README.md | xargs -I {} curl -Is {} | head -n 1
```

**예상 결과:**
- ✅ 모든 링크 접근 가능
- ✅ 404 오류 없음

---

## 🔍 검증 체크리스트

### 기능 검증
- [ ] 대화형/비대화형 모드
- [ ] 모든 템플릿 타입
- [ ] 파일 덮어쓰기 처리
- [ ] 변수 치환 정확성
- [ ] 조건부 렌더링

### 품질 검증
- [ ] 생성된 파일 문법
- [ ] 설정 파일 유효성
- [ ] 문서 정확성
- [ ] 디렉토리 구조

### 사용성 검증
- [ ] 프롬프트 명확성
- [ ] 기본값 적절성
- [ ] 오류 메시지
- [ ] 다음 단계 안내

---

## 📊 테스트 결과 기록

| 테스트 항목 | 상태 | 실행일 | 담당자 | 비고 |
|-----------|------|--------|---------|------|
| 대화형 초기화 | - | - | - | - |
| 템플릿 선택 | - | - | - | - |
| 파일 덮어쓰기 | - | - | - | - |
| 변수 치환 | - | - | - | - |
| 엣지 케이스 | - | - | - | - |

---

## 🐛 발견된 이슈

### 이슈 템플릿
```markdown
**이슈 ID**: INIT-001
**심각도**: High/Medium/Low
**재현 단계**:
1. 
2. 

**예상 동작**:

**실제 동작**:

**스크린샷/로그**:
```

---

## 📝 개선 제안

1. **템플릿 확장**
   - 더 많은 프리셋 템플릿 추가
   - 커스텀 템플릿 지원
   - 템플릿 마켓플레이스

2. **사용성 개선**
   - 프로젝트 타입 자동 감지
   - 기존 프로젝트 마이그레이션 지원
   - 설정 마법사 UI

3. **검증 강화**
   - 실시간 입력 검증
   - 네이밍 컨벤션 가이드
   - 모범 사례 제안