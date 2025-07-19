# 🧪 QA 시나리오: 고급 기능 테스트 (워크플로우 엔진 & AI 어시스턴트)

## 📌 테스트 대상
- **작업 ID**: 013, 014
- **기능**: 커스텀 워크플로우 엔진, 대화형 AI 어시스턴트
- **우선순위**: 🟢 Medium

## 🎯 테스트 목표
커스텀 워크플로우 정의 및 실행, AI 기반 대화형 도우미의 정확성과 유용성을 검증합니다.

---

## 📋 테스트 시나리오

### 1️⃣ 커스텀 워크플로우 기본 테스트

#### 1.1 워크플로우 정의 파일 생성
```bash
# 커스텀 워크플로우 정의
cat > .sbkube/workflows/deploy-with-backup.yaml << 'EOF'
name: deploy-with-backup
description: 백업을 포함한 안전한 배포
steps:
  - name: backup
    type: command
    command: kubectl create backup ${app_name}-${timestamp}
    condition: ${environment} == "production"
    
  - name: health-check-before
    type: health_check
    targets:
      - type: deployment
        name: ${app_name}
    timeout: 60
    
  - name: deploy
    type: sbkube_command
    command: deploy
    args:
      rolling_update: true
      
  - name: smoke-test
    type: http_check
    url: https://${app_name}.${domain}/health
    expected_status: 200
    retries: 5
    
  - name: rollback
    type: command
    command: kubectl rollback deployment/${app_name}
    on_failure_of: [deploy, smoke-test]
EOF

# 워크플로우 실행
sbkube workflow run deploy-with-backup --app myapp
```

**예상 결과:**
- ✅ 워크플로우 파일 검증 통과
- ✅ 조건부 단계 (backup) 올바르게 실행/건너뜀
- ✅ 각 단계 순차 실행
- ✅ 실패 시 rollback 자동 실행

#### 1.2 병렬 워크플로우 실행
```bash
cat > .sbkube/workflows/parallel-deploy.yaml << 'EOF'
name: parallel-deploy
steps:
  - name: prepare-all
    type: sbkube_command
    command: prepare
    
  - name: deploy-services
    type: parallel
    steps:
      - name: deploy-frontend
        type: sbkube_command
        command: deploy
        args:
          app: frontend
          
      - name: deploy-backend
        type: sbkube_command
        command: deploy
        args:
          app: backend
          
      - name: deploy-worker
        type: sbkube_command
        command: deploy
        args:
          app: worker
EOF

sbkube workflow run parallel-deploy
```

**예상 결과:**
- ✅ prepare-all 먼저 실행
- ✅ 3개 서비스 동시 배포
- ✅ 진행률 표시에 병렬 작업 반영
- ✅ 모든 병렬 작업 완료 대기

---

### 2️⃣ 워크플로우 고급 기능 테스트

#### 2.1 변수 및 템플릿 처리
```bash
# 변수를 사용하는 워크플로우
cat > .sbkube/workflows/templated-deploy.yaml << 'EOF'
name: templated-deploy
variables:
  region: ${REGION:-us-east-1}
  replicas: ${REPLICAS:-3}
  
steps:
  - name: configure
    type: template
    template: |
      Deploying to region: {{ region }}
      Replica count: {{ replicas }}
    output: deployment-config.txt
    
  - name: deploy
    type: sbkube_command
    command: deploy
    env:
      DEPLOYMENT_REGION: ${region}
      REPLICA_COUNT: ${replicas}
EOF

# 환경 변수와 함께 실행
REGION=eu-west-1 REPLICAS=5 sbkube workflow run templated-deploy
```

**예상 결과:**
- ✅ 환경 변수 올바르게 치환
- ✅ 기본값 적용 (변수 미설정 시)
- ✅ 템플릿 렌더링 정상 작동
- ✅ deployment-config.txt 파일 생성

#### 2.2 워크플로우 재사용 및 상속
```bash
# 기본 워크플로우
cat > .sbkube/workflows/base-deploy.yaml << 'EOF'
name: base-deploy
abstract: true
steps:
  - name: validate
    type: validation
  - name: deploy
    type: sbkube_command
    command: deploy
EOF

# 확장 워크플로우
cat > .sbkube/workflows/production-deploy.yaml << 'EOF'
name: production-deploy
extends: base-deploy
steps:
  - name: backup
    type: backup
    before: deploy
  - name: notify
    type: notification
    after: deploy
EOF

sbkube workflow run production-deploy
```

**예상 결과:**
- ✅ 실행 순서: validate → backup → deploy → notify
- ✅ 기본 워크플로우 단계 상속
- ✅ before/after로 순서 제어

---

### 3️⃣ AI 어시스턴트 기본 테스트

#### 3.1 대화형 도움말
```bash
sbkube assistant

# 대화 예시
> "배포가 실패했어요. 어떻게 해야 하나요?"
```

**예상 응답:**
```
배포 실패를 해결하도록 도와드리겠습니다. 먼저 몇 가지 확인해보겠습니다:

1. 현재 상태 확인:
   $ sbkube doctor
   
2. 최근 로그 확인:
   $ kubectl logs -n [namespace] deployment/[app-name]
   
3. 이벤트 확인:
   $ kubectl get events -n [namespace] --sort-by='.lastTimestamp'

어떤 오류 메시지가 표시되나요?
```

#### 3.2 컨텍스트 인식 도움말
```bash
# 특정 오류 상황에서
sbkube deploy
# Error: ImagePullBackOff

sbkube assistant --context-aware
```

**예상 응답:**
```
'ImagePullBackOff' 오류가 감지되었습니다. 이는 Docker 이미지를 가져올 수 없을 때 발생합니다.

가능한 원인:
1. 이미지 이름/태그 오류
2. 레지스트리 인증 문제
3. 네트워크 연결 문제

해결 방법:
1. 이미지 확인: kubectl describe pod [pod-name] -n [namespace]
2. 시크릿 확인: kubectl get secret -n [namespace]
3. 수동 풀 테스트: docker pull [image-name]

자세한 진단을 실행할까요? (Y/n)
```

---

### 4️⃣ AI 어시스턴트 고급 기능

#### 4.1 설정 파일 생성 도우미
```bash
sbkube assistant create-config

# 대화형 프롬프트
> "PostgreSQL 데이터베이스와 Redis를 사용하는 웹 애플리케이션 설정을 만들어주세요"
```

**예상 결과:**
- ✅ 요구사항 분석
- ✅ 적절한 Helm 차트 제안
- ✅ config.yaml 생성
- ✅ values 파일 템플릿 생성
- ✅ 모범 사례 적용

#### 4.2 트러블슈팅 가이드
```bash
# 문제 상황 시뮬레이션
kubectl scale deployment myapp --replicas=100  # 리소스 부족 유발

sbkube assistant troubleshoot
```

**예상 시나리오:**
```
시스템 상태를 분석 중입니다...

발견된 문제:
1. ⚠️ Pod 대기 중: 23/100 (Pending)
2. ❌ 노드 리소스 부족
3. ⚠️ HPA 한계 도달

권장 조치:
1. 노드 스케일링:
   $ kubectl scale nodes --replicas=5
   
2. 리소스 요청량 조정:
   $ sbkube tune resources --optimize
   
3. HPA 설정 검토:
   현재: min=1, max=10
   권장: min=3, max=50

단계별로 안내해드릴까요? (Y/n)
```

---

### 5️⃣ 워크플로우와 AI 통합 테스트

#### 5.1 AI 기반 워크플로우 생성
```bash
sbkube assistant create-workflow

> "블루-그린 배포 워크플로우를 만들어주세요"
```

**예상 결과:**
- ✅ 블루-그린 배포 단계 자동 생성
- ✅ 헬스체크 포함
- ✅ 트래픽 전환 단계
- ✅ 롤백 전략 포함

#### 5.2 워크플로우 실행 중 AI 지원
```bash
# 워크플로우 실행 중 오류 발생 시
sbkube workflow run complex-deploy

# 오류 발생 시 자동으로
# > "Step 'database-migration' failed. Would you like assistance?"

> "Yes"
```

**예상 AI 응답:**
```
데이터베이스 마이그레이션 실패를 분석했습니다.

오류: "relation already exists"

이는 마이그레이션이 이미 적용되었음을 의미합니다.

해결 옵션:
1. 마이그레이션 상태 확인 후 건너뛰기
2. 강제 재실행 (--force 옵션)
3. 마이그레이션 롤백 후 재실행

어떤 옵션을 선택하시겠습니까? (1/2/3)
```

---

### 6️⃣ 엣지 케이스 및 오류 처리

#### 6.1 순환 의존성 감지
```bash
cat > .sbkube/workflows/circular.yaml << 'EOF'
name: circular
steps:
  - name: step1
    depends_on: [step3]
  - name: step2
    depends_on: [step1]
  - name: step3
    depends_on: [step2]
EOF

sbkube workflow validate circular
```

**예상 결과:**
- ❌ 오류: "순환 의존성 감지"
- ✅ 순환 경로 표시: step1 → step3 → step2 → step1

#### 6.2 AI 한계 테스트
```bash
sbkube assistant

> "회사 매출을 늘리는 방법을 알려주세요"
```

**예상 응답:**
```
죄송합니다. 저는 SBKube 관련 기술 지원만 제공할 수 있습니다.

도움을 드릴 수 있는 주제:
- Kubernetes 배포 및 관리
- 설정 파일 작성
- 트러블슈팅
- 워크플로우 최적화

Kubernetes 관련 질문이 있으신가요?
```

---

## 🔍 검증 체크리스트

### 워크플로우 엔진
- [ ] 기본 워크플로우 실행
- [ ] 병렬/조건부 실행
- [ ] 변수 및 템플릿
- [ ] 오류 처리/롤백
- [ ] 워크플로우 검증

### AI 어시스턴트
- [ ] 컨텍스트 인식
- [ ] 도움말 정확성
- [ ] 설정 생성
- [ ] 트러블슈팅
- [ ] 범위 제한

### 통합 기능
- [ ] 워크플로우-AI 연동
- [ ] 실시간 지원
- [ ] 학습 및 개선
- [ ] 사용자 피드백

---

## 📊 테스트 결과 기록

| 테스트 항목 | 상태 | 실행일 | 담당자 | 비고 |
|-----------|------|--------|---------|------|
| 커스텀 워크플로우 | - | - | - | - |
| AI 기본 기능 | - | - | - | - |
| 고급 시나리오 | - | - | - | - |
| 통합 테스트 | - | - | - | - |
| 오류 처리 | - | - | - | - |

---

## 🐛 발견된 이슈

### 이슈 템플릿
```markdown
**이슈 ID**: ADV-001
**심각도**: High/Medium/Low
**기능**: 워크플로우/AI
**재현 단계**:
1. 
2. 

**예상 동작**:

**실제 동작**:

**관련 파일**:
```

---

## 📝 개선 제안

1. **워크플로우 확장**
   - 더 많은 내장 단계 타입
   - 워크플로우 마켓플레이스
   - 시각적 편집기

2. **AI 향상**
   - 학습 데이터 축적
   - 사용자별 맞춤화
   - 다국어 지원

3. **통합 강화**
   - CI/CD 파이프라인 연동
   - 모니터링 시스템 연동
   - 알림 채널 확대