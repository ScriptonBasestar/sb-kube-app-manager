# 🧪 QA 시나리오: sbkube run 워크플로우 통합 테스트

## 📌 테스트 대상
- **작업 ID**: 001, 002, 003, 004
- **기능**: `sbkube run` 명령어 전체 워크플로우
- **우선순위**: 🔴 Critical

## 🎯 테스트 목표
`sbkube run` 명령어의 전체 워크플로우 동작을 검증하고, 단계별 제어 및 오류 처리가 올바르게 작동하는지 확인합니다.

---

## 📋 테스트 시나리오

### 1️⃣ 기본 워크플로우 실행 테스트

#### 사전 조건
- Kubernetes 클러스터 연결됨
- 유효한 설정 파일 존재 (`config/config.yaml`)
- Helm 설치됨

#### 테스트 단계
```bash
# 1. 테스트 프로젝트 생성
mkdir test-sbkube-run && cd test-sbkube-run
sbkube init --non-interactive

# 2. 전체 워크플로우 실행
sbkube run --dry-run

# 3. 실제 실행 (주의: 실제 리소스 생성)
sbkube run
```

#### 예상 결과
- ✅ 4단계 순차 실행: prepare → build → template → deploy
- ✅ 각 단계별 시작/완료 메시지 출력
- ✅ 종료 코드 0 반환

---

### 2️⃣ 단계별 실행 제어 테스트

#### 2.1 --from-step 옵션 테스트
```bash
# template 단계부터 실행
sbkube run --from-step template --dry-run
```

**예상 결과:**
- ✅ prepare, build 단계 건너뜀
- ✅ template, deploy 단계만 실행

#### 2.2 --to-step 옵션 테스트
```bash
# build 단계까지만 실행
sbkube run --to-step build --dry-run
```

**예상 결과:**
- ✅ prepare, build 단계만 실행
- ✅ template, deploy 단계 건너뜀

#### 2.3 --only 옵션 테스트
```bash
# template 단계만 실행
sbkube run --only template --dry-run
```

**예상 결과:**
- ✅ template 단계만 단독 실행
- ✅ 나머지 단계 모두 건너뜀

#### 2.4 옵션 충돌 테스트
```bash
# 충돌하는 옵션 조합
sbkube run --only template --from-step build
```

**예상 결과:**
- ❌ 오류 메시지: "--only 옵션은 --from-step, --to-step과 함께 사용할 수 없습니다"
- ❌ 종료 코드 1

---

### 3️⃣ 오류 처리 및 복구 테스트

#### 3.1 설정 파일 누락 테스트
```bash
# 설정 파일 임시 이동
mv config/config.yaml config/config.yaml.bak
sbkube run
```

**예상 결과:**
- ❌ 오류 메시지: "설정 파일을 찾을 수 없습니다"
- ❌ 종료 코드 1
- ✅ 스택 트레이스 없음

#### 3.2 중단 후 재시작 테스트
```bash
# 1. build 단계에서 Ctrl+C로 중단
sbkube run
# (build 단계에서 Ctrl+C)

# 2. 중단된 지점부터 재시작
sbkube run --from-step build
```

**예상 결과:**
- ✅ build 단계부터 정상 재개
- ✅ 이전 단계 상태 확인 메시지

#### 3.3 의존성 누락 테스트
```bash
# kubectl 없이 실행 (Docker 컨테이너에서 테스트)
docker run -it python:3.9 bash
pip install sbkube
sbkube run
```

**예상 결과:**
- ❌ 오류: "kubectl이 설치되지 않았습니다"
- ✅ 설치 가이드 제공

---

### 4️⃣ 병렬 실행 및 성능 테스트

#### 4.1 다중 앱 병렬 처리
```bash
# 여러 앱이 있는 설정으로 테스트
cat > config/config.yaml << EOF
namespace: test
apps:
  - name: app1
    type: install-helm
  - name: app2
    type: install-helm
  - name: app3
    type: install-yaml
EOF

time sbkube run
```

**예상 결과:**
- ✅ 여러 앱 병렬 처리
- ✅ 전체 실행 시간 < 개별 실행 시간의 합
- ✅ 진행률 표시 정상 작동

#### 4.2 대용량 템플릿 처리
```bash
# 대용량 values 파일 생성
python -c "
data = {'key' + str(i): 'value' + str(i) for i in range(10000)}
import yaml
with open('values/large-values.yaml', 'w') as f:
    yaml.dump(data, f)
"

sbkube run --only template
```

**예상 결과:**
- ✅ 메모리 오류 없이 정상 처리
- ✅ 실행 시간 < 30초

---

### 5️⃣ 환경별 실행 테스트

#### 5.1 프로파일 지정 실행
```bash
# production 환경으로 실행
sbkube run --profile production --dry-run
```

**예상 결과:**
- ✅ production 설정 파일 사용
- ✅ 네임스페이스: {project}-production

#### 5.2 설정 파일 지정 실행
```bash
# 커스텀 설정 파일 사용
sbkube run --config-file custom-config.yaml --dry-run
```

**예상 결과:**
- ✅ 지정된 설정 파일 로드
- ✅ 기본 설정 무시

---

## 🔍 검증 체크리스트

### 기능 검증
- [ ] 전체 워크플로우 정상 실행
- [ ] 단계별 제어 옵션 동작
- [ ] 오류 처리 및 메시지
- [ ] 병렬 처리 성능
- [ ] 환경별 실행

### 통합 검증
- [ ] Kubernetes API 호출
- [ ] Helm 명령어 실행
- [ ] 파일 시스템 작업
- [ ] 로깅 시스템

### 사용성 검증
- [ ] 명령어 도움말 (`--help`)
- [ ] 진행률 표시
- [ ] 오류 메시지 명확성
- [ ] 중단/재시작 지원

---

## 📊 테스트 결과 기록

| 테스트 항목 | 상태 | 실행일 | 담당자 | 비고 |
|-----------|------|--------|---------|------|
| 기본 워크플로우 | - | - | - | - |
| 단계별 제어 | - | - | - | - |
| 오류 처리 | - | - | - | - |
| 병렬 처리 | - | - | - | - |
| 환경별 실행 | - | - | - | - |

---

## 🐛 발견된 이슈

### 이슈 템플릿
```markdown
**이슈 ID**: BUG-001
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

1. **성능 개선**
   - 병렬 처리 최적화
   - 캐싱 메커니즘 추가

2. **사용성 개선**
   - 인터랙티브 모드 추가
   - 시각적 진행률 개선

3. **안정성 개선**
   - 재시도 로직 추가
   - 상태 체크포인트 저장