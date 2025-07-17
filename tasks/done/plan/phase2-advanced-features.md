# Phase 2: 고급 편의성 개선 (3-4주)

---
**변환 상태**: ✅ 변환 완료  
**변환 일시**: 2025-01-16  
**변환된 ToDo 파일**: 
- 006-profile-system-design.md
- 007-profile-loader-implementation.md  
- 008-smart-restart-execution-tracker.md
- 009-smart-restart-history-management.md
- 010-progress-manager-implementation.md

**변환 범위**: 환경별 프로파일, 스마트 재시작, 진행률 표시 시스템 구현
---

## 🎯 목표

1단계에서 구현한 기본 편의성 기능을 바탕으로 더욱 고급스러운 사용자 경험을 제공합니다.

**예상 효과**: 환경별 배포 실수 방지, 디버깅 시간 60% 단축, 사용자 온보딩 시간 70% 단축

## 📋 작업 목록

### 1. 환경별 프로파일 지원 (7-10일)

#### 1.1 프로파일 시스템 설계 (2-3일)
- [ ] 프로파일 설정 구조 정의
- [ ] 환경별 설정 파일 지원 (`config-{env}.yaml`)
- [ ] 설정 오버라이드 우선순위 정의
- [ ] 프로파일 상속 및 확장 기능

**프로파일 구조:**
```
config/
├── config.yaml              # 기본 설정
├── config-development.yaml  # 개발 환경
├── config-staging.yaml      # 스테이징 환경
├── config-production.yaml   # 프로덕션 환경
└── values/
    ├── common/              # 공통 values
    ├── development/         # 개발 환경 values
    ├── staging/             # 스테이징 환경 values
    └── production/          # 프로덕션 환경 values
```

#### 1.2 프로파일 로더 구현 (3-4일)
- [ ] `sbkube/utils/profile_manager.py` 파일 생성
- [ ] 환경별 설정 파일 병합 로직
- [ ] Values 파일 경로 자동 해결
- [ ] 프로파일 검증 및 오류 처리

**구현 예시:**
```python
class ProfileManager:
    def load_profile(self, profile_name: str) -> ConfigModel:
        base_config = self.load_base_config()
        profile_config = self.load_profile_config(profile_name)
        return self.merge_configs(base_config, profile_config)
```

#### 1.3 CLI 통합 (2-3일)
- [ ] 모든 명령어에 `--profile` 옵션 추가
- [ ] 프로파일 목록 조회 기능 (`sbkube profiles list`)
- [ ] 프로파일 검증 기능 (`sbkube profiles validate`)
- [ ] 기본 프로파일 설정 지원

**사용 예시:**
```bash
sbkube run --profile production
sbkube deploy --profile staging
sbkube profiles list
sbkube profiles validate production
```

### 2. 스마트 재시작 기능 (7-10일)

#### 2.1 실행 상태 추적 시스템 (3-4일)
- [ ] `sbkube/utils/execution_tracker.py` 파일 생성
- [ ] 실행 상태 저장 구조 정의 (JSON 형태)
- [ ] 단계별 실행 시간 및 결과 기록
- [ ] 실패 지점 및 오류 정보 저장

**상태 파일 구조:**
```json
{
  "run_id": "uuid-string",
  "started_at": "2024-01-01T10:00:00Z",
  "profile": "production",
  "steps": {
    "prepare": {
      "status": "completed",
      "started_at": "2024-01-01T10:00:00Z",
      "completed_at": "2024-01-01T10:01:30Z",
      "duration": 90
    },
    "build": {
      "status": "failed",
      "started_at": "2024-01-01T10:01:30Z",
      "error": "Helm chart not found"
    }
  }
}
```

#### 2.2 재시작 로직 구현 (2-3일)
- [ ] `--continue-from` 옵션 구현
- [ ] `--retry-failed` 옵션 구현
- [ ] 실패한 단계부터 자동 재시작
- [ ] 상태 파일 기반 복원 로직

**사용 예시:**
```bash
sbkube run --continue-from build      # build부터 재시작
sbkube run --retry-failed            # 마지막 실패 단계부터
sbkube run --resume                   # 자동으로 재시작 지점 탐지
```

#### 2.3 실행 히스토리 관리 (2-3일)
- [ ] 실행 히스토리 저장 및 조회
- [ ] 성공/실패 통계 제공
- [ ] 오래된 히스토리 자동 정리
- [ ] 히스토리 기반 문제 패턴 분석

**히스토리 명령어:**
```bash
sbkube history                        # 최근 실행 히스토리
sbkube history --detailed             # 상세 실행 정보
sbkube history --failures             # 실패한 실행만 표시
sbkube history --clean                # 오래된 히스토리 정리
```

### 3. 향상된 로깅 및 진행 상황 표시 (5-7일)

#### 3.1 실시간 진행률 표시 (3-4일)
- [ ] `sbkube/utils/progress_manager.py` 파일 생성
- [ ] Rich Progress Bar 통합
- [ ] 단계별 진행률 계산 로직
- [ ] 예상 완료 시간 표시

**진행률 표시 예시:**
```
🚀 SBKube 배포 진행 중 (production)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
├── [✓] Prepare  ━━━━━━━━━━━━━━━━ 100% (1m 30s)
├── [✓] Build    ━━━━━━━━━━━━━━━━ 100% (2m 15s)  
├── [▶] Template ━━━━━━━━━━━━━░░░  75% (45s) 
└── [ ] Deploy   ━━━━━━━━━━━━━░░░   0% (대기중)

전체 진행률: 68% | 예상 완료: 약 1분 후
```

#### 3.2 실시간 로그 스트리밍 (2-3일)
- [ ] 각 단계별 실시간 로그 표시
- [ ] 로그 레벨별 색상 구분
- [ ] 중요 이벤트 하이라이트
- [ ] 로그 파일 자동 저장

**로그 표시 개선:**
```
[10:30:15] 🔄 Prepare | Downloading helm chart redis:18.0.0...
[10:30:16] 📥 Prepare | Chart downloaded successfully (2.3MB)
[10:30:17] ⚙️  Build   | Processing redis configuration...
[10:30:18] ✅ Build   | Redis values applied successfully
```

#### 3.3 상황별 안내 메시지 (1-2일)
- [ ] 단계별 완료 메시지 개선
- [ ] 다음 단계 예고 메시지
- [ ] 문제 발생 시 해결 방법 제시
- [ ] 성공 시 다음 권장 액션 안내

### 4. 설정 검증 및 사전 확인 (3-5일)

#### 4.1 사전 검증 시스템 (2-3일)
- [ ] 실행 전 전체 설정 검증
- [ ] 필수 의존성 확인 (kubectl, helm 등)
- [ ] 네트워크 연결 상태 확인
- [ ] 권한 및 접근성 검증

**검증 항목:**
```
🔍 사전 검증 실행 중...
├── [✓] Kubernetes 연결 확인
├── [✓] Helm 설치 확인  
├── [⚠] 네임스페이스 'prod' 존재하지 않음 (자동 생성 예정)
├── [✓] 설정 파일 유효성 확인
└── [✓] 필요한 권한 확인

⚠️  1개 경고가 있지만 진행 가능합니다.
```

#### 4.2 의존성 자동 해결 (1-2일)
- [ ] 누락된 네임스페이스 자동 생성 제안
- [ ] 필요한 Helm 리포지토리 자동 추가
- [ ] 권한 문제 해결 방법 제시
- [ ] 설정 오류 자동 수정 제안

## 🧪 테스트 계획

### 프로파일 시스템 테스트
- [ ] 다양한 환경 설정 조합 테스트
- [ ] 설정 오버라이드 우선순위 테스트
- [ ] 프로파일 검증 로직 테스트
- [ ] 잘못된 프로파일 처리 테스트

### 재시작 기능 테스트
- [ ] 각 단계별 실패 시나리오 테스트
- [ ] 상태 저장/복원 정확성 테스트
- [ ] 동시 실행 시 상태 충돌 테스트
- [ ] 히스토리 관리 기능 테스트

### 사용자 인터페이스 테스트
- [ ] 다양한 터미널 환경에서 UI 테스트
- [ ] 진행률 표시 정확성 테스트
- [ ] 로그 출력 성능 테스트
- [ ] 사용자 중단 시 정리 동작 테스트

## 📚 문서 작성

### 사용자 가이드
- [ ] `docs/02-features/profiles.md` - 프로파일 시스템 가이드
- [ ] `docs/02-features/smart-restart.md` - 재시작 기능 가이드
- [ ] `docs/02-features/progress-tracking.md` - 진행 추적 가이드

### 설정 가이드
- [ ] `docs/03-configuration/profile-configuration.md` - 프로파일 설정법
- [ ] `docs/03-configuration/environment-management.md` - 환경 관리 가이드

### 문제 해결 가이드
- [ ] `docs/07-troubleshooting/restart-issues.md` - 재시작 관련 문제
- [ ] `docs/07-troubleshooting/profile-issues.md` - 프로파일 관련 문제

## ✅ 완료 기준

### 기능 완료 기준
- [ ] 프로파일을 사용한 환경별 배포가 정상 작동
- [ ] 실패 시 재시작 기능이 안정적으로 동작
- [ ] 진행 상황이 실시간으로 정확하게 표시
- [ ] 사전 검증이 주요 문제를 사전에 탐지

### 성능 기준
- [ ] 프로파일 로딩 시간 500ms 이내
- [ ] 상태 저장/복원 시간 100ms 이내
- [ ] UI 업데이트 지연 50ms 이내
- [ ] 메모리 사용량 증가 20% 이내

### 사용성 기준
- [ ] 환경별 배포 실수가 90% 감소
- [ ] 재시작 시간이 기존 대비 70% 단축
- [ ] 사용자가 현재 상태를 명확히 파악 가능
- [ ] 문제 발생 시 해결 방법을 쉽게 찾을 수 있음

## 🚀 다음 단계 준비

2단계 완료 후 3단계 진행을 위한 준비사항:
- [ ] 사용자 행동 데이터 수집 및 분석
- [ ] 자주 발생하는 문제 패턴 식별
- [ ] AI/ML 기반 자동화 가능 영역 조사
- [ ] 외부 도구 통합 필요성 평가

## 📅 일정 관리

### 주차별 목표
- **1주차**: 프로파일 시스템 설계 및 기본 구현
- **2주차**: 스마트 재시작 기능 완전 구현
- **3주차**: 향상된 UI 및 사전 검증 시스템
- **4주차**: 통합 테스트, 문서화, 성능 최적화

### 마일스톤
- **Day 7**: 프로파일 시스템 기본 동작
- **Day 14**: 재시작 기능 완전 동작
- **Day 21**: 모든 UI 개선 완료
- **Day 28**: 전체 2단계 기능 완료 및 릴리스

## 🔧 구현 팁

### 성능 최적화
- 프로파일 정보는 첫 로딩 후 캐시
- 상태 파일은 변경사항만 증분 저장
- UI 업데이트는 배치 처리로 성능 향상

### 안정성 확보
- 상태 파일 손상 시 복구 메커니즘
- 네트워크 장애 시 우아한 실패 처리
- 사용자 중단(Ctrl+C) 시 정리 작업 보장

### 확장성 고려
- 플러그인 시스템을 고려한 인터페이스 설계
- 외부 모니터링 시스템과의 연동 준비
- 다국어 지원을 위한 메시지 구조화