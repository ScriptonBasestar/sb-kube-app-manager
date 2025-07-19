# 🧪 QA 시나리오: sbkube doctor 진단 시스템 테스트

## 📌 테스트 대상
- **작업 ID**: 011, 012
- **기능**: `sbkube doctor` 시스템 진단 및 자동 수정
- **우선순위**: 🟡 High

## 🎯 테스트 목표
시스템 진단 기능의 정확성을 검증하고, 자동 수정 시스템이 안전하게 작동하는지 확인합니다.

---

## 📋 테스트 시나리오

### 1️⃣ 정상 시스템 진단 테스트

#### 1.1 모든 검사 통과 시나리오
```bash
# 정상 환경에서 실행
sbkube doctor
```

**예상 결과:**
```
🏥 시스템 진단을 시작합니다...

검사 중: Kubernetes 연결성 ✓
검사 중: Helm 설치 상태 ✓
검사 중: 설정 파일 유효성 ✓
검사 중: 네트워크 접근성 ✓
검사 중: 권한 확인 ✓
검사 중: 리소스 가용성 ✓

📊 진단 결과 요약:
🟢 성공: 6
🟡 경고: 0
🔴 오류: 0
🔵 정보: 0

✅ 시스템이 정상 상태입니다!
```

#### 1.2 상세 모드 테스트
```bash
sbkube doctor --detailed
```

**추가 검증 항목:**
- ✅ 각 검사의 상세 정보 표시
- ✅ 시스템 버전 정보
- ✅ 클러스터 정보
- ✅ 실행 시간 표시

---

### 2️⃣ 문제 감지 시나리오

#### 2.1 Kubernetes 연결 실패
```bash
# kubeconfig 임시 변경
export KUBECONFIG=/tmp/invalid-config
sbkube doctor
```

**예상 결과:**
- 🔴 오류: "Kubernetes 클러스터에 연결할 수 없습니다"
- ✅ 수정 제안: "kubectl cluster-info 실행하여 연결 확인"
- ✅ 상세 오류 정보 제공

#### 2.2 Helm 미설치
```bash
# Helm 경로에서 제거 (Docker 컨테이너에서 테스트)
docker run -it python:3.9 bash
pip install sbkube
sbkube doctor
```

**예상 결과:**
- 🔴 오류: "Helm이 설치되지 않았습니다"
- ✅ 수정 제안: 설치 명령어 제공
- ✅ 공식 문서 링크

#### 2.3 설정 파일 문제
```bash
# 잘못된 YAML 생성
cat > config/config.yaml << 'EOF'
namespace: test
apps:
  - name: app1
    type: invalid-type
  invalid-yaml: [
EOF

sbkube doctor
```

**예상 결과:**
- 🔴 오류: "설정 파일 파싱 오류"
- ✅ 오류 위치 표시 (라인 번호)
- ✅ YAML 문법 가이드

#### 2.4 권한 부족
```bash
# 제한된 권한으로 테스트
kubectl create serviceaccount test-limited
kubectl create rolebinding test-limited --serviceaccount=default:test-limited --clusterrole=view
kubectl --as=system:serviceaccount:default:test-limited auth can-i create deployments

sbkube doctor
```

**예상 결과:**
- 🟡 경고: "배포 생성 권한이 없습니다"
- ✅ 필요한 권한 목록
- ✅ RBAC 설정 가이드

---

### 3️⃣ 자동 수정 테스트

#### 3.1 수정 가능한 문제
```bash
# sources.yaml 파일 삭제
rm config/sources.yaml
sbkube doctor --fix
```

**상호작용 시퀀스:**
1. 문제 감지: "sources.yaml 파일이 없습니다"
2. 수정 제안: "기본 sources.yaml 생성"
3. 확인 프롬프트: "'sources.yaml 파일이 없습니다' 문제를 수정하시겠습니까? [y/N]"
4. Y 입력

**예상 결과:**
- ✅ sources.yaml 파일 자동 생성
- ✅ 수정 성공 메시지
- ✅ 재검사 시 문제 해결됨

#### 3.2 수정 불가능한 문제
```bash
# 클러스터 연결 끊김 상태에서
unset KUBECONFIG
sbkube doctor --fix
```

**예상 결과:**
- 🔴 수정 불가: "수동으로 kubeconfig 설정 필요"
- ✅ 상세한 수동 해결 가이드
- ✅ 수정 시도하지 않음

#### 3.3 부분 수정 성공
```bash
# 여러 문제가 있는 상황
rm config/sources.yaml
echo "invalid yaml" > config/config.yaml
sbkube doctor --fix
```

**예상 결과:**
- ✅ sources.yaml: 수정 성공
- ❌ config.yaml: 수정 실패 (수동 개입 필요)
- 📊 수정 통계: "2개 중 1개 수정됨"

---

### 4️⃣ 특정 검사 실행

#### 4.1 개별 검사 실행
```bash
# Kubernetes 연결성만 검사
sbkube doctor --check k8s_connectivity

# 네트워크만 검사
sbkube doctor --check network_access
```

**예상 결과:**
- ✅ 지정된 검사만 실행
- ✅ 다른 검사 건너뜀
- ✅ 실행 시간 단축

#### 4.2 잘못된 검사명
```bash
sbkube doctor --check invalid_check
```

**예상 결과:**
- ❌ 오류: "알 수 없는 검사: invalid_check"
- ✅ 사용 가능한 검사 목록 표시

---

### 5️⃣ 환경별 진단

#### 5.1 다른 설정 디렉토리
```bash
sbkube doctor --config-dir ./custom-config
```

**예상 결과:**
- ✅ 지정된 디렉토리에서 설정 검사
- ✅ 기본 디렉토리 무시

#### 5.2 프로파일별 진단
```bash
sbkube doctor --profile production
```

**예상 결과:**
- ✅ production 설정 파일 검사
- ✅ 환경별 특수 검사 수행

---

### 6️⃣ 성능 및 타임아웃 테스트

#### 6.1 네트워크 지연
```bash
# 네트워크 지연 시뮬레이션
tc qdisc add dev eth0 root netem delay 5000ms
sbkube doctor
```

**예상 결과:**
- ⏱️ 각 검사 타임아웃 (10초)
- ✅ 다른 검사는 계속 진행
- 🟡 경고: "네트워크 응답 지연"

#### 6.2 동시 실행
```bash
# 여러 터미널에서 동시 실행
sbkube doctor &
sbkube doctor &
sbkube doctor &
```

**예상 결과:**
- ✅ 각 인스턴스 독립적 실행
- ✅ 리소스 경합 없음
- ✅ 일관된 결과

---

## 🔍 검증 체크리스트

### 진단 정확성
- [ ] 모든 검사 항목 동작
- [ ] 문제 정확히 감지
- [ ] 거짓 양성/음성 없음
- [ ] 상세 정보 정확성

### 자동 수정
- [ ] 안전한 수정만 시도
- [ ] 사용자 확인 필수
- [ ] 롤백 가능성
- [ ] 수정 결과 검증

### 사용자 경험
- [ ] 명확한 문제 설명
- [ ] 실행 가능한 해결책
- [ ] 진행률 표시
- [ ] 색상/아이콘 활용

---

## 📊 테스트 결과 기록

| 테스트 항목 | 상태 | 실행일 | 담당자 | 비고 |
|-----------|------|--------|---------|------|
| 정상 시스템 진단 | - | - | - | - |
| 문제 감지 | - | - | - | - |
| 자동 수정 | - | - | - | - |
| 특정 검사 | - | - | - | - |
| 성능 테스트 | - | - | - | - |

---

## 🐛 발견된 이슈

### 이슈 템플릿
```markdown
**이슈 ID**: DOCTOR-001
**심각도**: High/Medium/Low
**검사 항목**: 
**재현 단계**:
1. 
2. 

**예상 진단**:

**실제 진단**:

**로그/스크린샷**:
```

---

## 📝 개선 제안

1. **진단 확장**
   - 더 많은 검사 항목 추가
   - 플러그인 시스템
   - 커스텀 검사 정의

2. **자동 수정 강화**
   - 더 많은 자동 수정 시나리오
   - 수정 이력 관리
   - 되돌리기 기능

3. **리포팅 개선**
   - HTML/PDF 리포트 생성
   - 시간별 추세 분석
   - 권장사항 우선순위