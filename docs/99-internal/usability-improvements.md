# SBKube 사용성 개선 방안

## 📋 현재 상황 분석

SBKube는 Kubernetes 애플리케이션 배포 자동화의 핵심 기능이 잘 구현되어 있지만, 사용자 편의성 측면에서 다음과 같은 개선이 필요합니다:

### 🔍 주요 불편사항

1. **반복 작업의 번거로움**

   - 매번 `prepare → build → template → deploy` 4단계를 순차 실행
   - 전체 워크플로우를 한 번에 실행할 수 있는 방법 부재

1. **공통 옵션 반복 입력**

   - `--app-dir`, `--base-dir`, `--namespace` 등을 매번 타이핑
   - 프로젝트별 기본값 설정 불가

1. **환경별 설정 관리 복잡성**

   - 개발/스테이징/프로덕션 환경 구분 어려움
   - 환경별 설정을 별도로 관리해야 함

1. **초기 설정의 어려움**

   - 새 프로젝트 시작 시 설정 파일 작성 복잡
   - 설정 파일 구조 및 옵션 파악 어려움

1. **오류 복구의 비효율성**

   - 실패 시 처음부터 다시 시작해야 함
   - 어느 단계에서 실패했는지 파악 어려움

## 🎯 제안하는 편의성 개선 기능

### 1단계: 즉시 구현 가능 (높은 우선순위)

#### 1.1 통합 실행 명령어 `sbkube run`

**현재 사용법:**

```bash
sbkube prepare --app-dir config --namespace production
sbkube build --app-dir config
sbkube template --app-dir config --output-dir rendered/
sbkube deploy --app-dir config --namespace production
```

**개선된 사용법:**

```bash
# 전체 워크플로우 한 번에 실행
sbkube run --app-dir config --namespace production

# 특정 앱만 실행
sbkube run --app web-frontend --namespace staging

# 특정 단계부터 실행
sbkube run --from template --namespace production
```

**구현 방안:**

- 기존 명령어들을 순차적으로 실행하는 wrapper 명령어
- 각 단계 실행 전 검증 및 의존성 확인
- 실패 시 중단점 저장 및 재시작 지원

#### 1.2 프로젝트 초기화 도구 `sbkube init`

**기능:**

```bash
# 대화형 설정 생성
sbkube init

# 템플릿 기반 생성
sbkube init --template web-app --name my-project
sbkube init --template microservice --name api-service
sbkube init --template database --name postgres-db
```

**생성되는 파일:**

- `config/config.yaml` - 기본 애플리케이션 설정
- `config/sources.yaml` - 소스 저장소 설정
- `values/` - Helm values 파일 디렉토리
- `.sbkuberc` - 프로젝트 기본값 설정
- `README.md` - 프로젝트 사용법 가이드

#### 1.3 설정 파일 기본값 지원 `.sbkuberc`

**프로젝트 루트의 `.sbkuberc` 파일:**

```yaml
# 기본 설정
app_dir: config
base_dir: .
namespace: default
kubeconfig: ~/.kube/config
context: local-cluster

# 환경별 설정
profiles:
  development:
    namespace: dev
    kubeconfig: ~/.kube/dev-config
  staging:
    namespace: staging
    kubeconfig: ~/.kube/staging-config
  production:
    namespace: prod
    kubeconfig: ~/.kube/prod-config
```

**사용 효과:**

```bash
# 기본값 적용되어 옵션 생략 가능
sbkube run

# 특정 환경으로 실행
sbkube run --profile production
```

### 2단계: 중간 구현 (중간 우선순위)

#### 2.1 환경별 프로파일 지원

**설정 파일 구조:**

```
config/
├── config.yaml              # 기본 설정
├── config-development.yaml  # 개발 환경 설정
├── config-staging.yaml      # 스테이징 환경 설정
├── config-production.yaml   # 프로덕션 환경 설정
└── values/
    ├── common/              # 공통 values
    ├── development/         # 개발 환경 values
    ├── staging/             # 스테이징 환경 values
    └── production/          # 프로덕션 환경 values
```

**사용법:**

```bash
# 환경별 배포
sbkube run --profile development
sbkube run --profile staging  
sbkube run --profile production

# 환경별 검증
sbkube validate --profile production
```

#### 2.2 스마트 재시작 기능

**실패 지점 추적:**

- 각 단계 실행 상태를 `.sbkube/state.json`에 저장
- 실패 시 마지막 성공한 단계부터 재시작 가능

**사용법:**

```bash
# 실패 지점부터 재시작
sbkube run --continue-from build
sbkube run --retry-failed

# 특정 단계만 재실행
sbkube run --only template
```

#### 2.3 향상된 진행 상황 표시

**개선된 출력:**

```
🚀 SBKube 배포 시작
├── [✓] Prepare (2/4) ━━━━━━━━━━━━━━━━ 100% 완료 (15s)
├── [✓] Build   (3/4) ━━━━━━━━━━━━━━━━ 100% 완료 (30s)
├── [▶] Template (4/4) ━━━━━━━━━━━━━━━━ 45% 진행 중...
└── [ ] Deploy  (0/4) ━━━━━━━━━━━━━━━━ 0% 대기 중

예상 완료 시간: 약 2분 후
```

**기능:**

- 실시간 진행률 바
- 각 단계별 성공/실패 상태
- 예상 완료 시간 표시
- 다음 권장 액션 안내

### 3단계: 고급 기능 (낮은 우선순위)

#### 3.1 설정 검증 및 자동 수정

**진단 도구:**

```bash
# 설정 문제 진단
sbkube doctor

# 출력 예시:
❌ config.yaml에서 필수 필드 'namespace' 누락
❌ sources.yaml에서 참조하는 저장소 'bitnami'가 정의되지 않음  
⚠️  values/redis.yaml 파일이 존재하지 않음
✅ Kubernetes 연결 정상
✅ Helm 설치 확인됨

💡 수정 제안:
   1. config.yaml에 'namespace: default' 추가
   2. sources.yaml에 bitnami 저장소 추가
   3. values/redis.yaml 템플릿 파일 생성
```

**자동 수정:**

```bash
# 일반적인 문제 자동 수정
sbkube fix

# 누락된 파일 자동 생성
sbkube fix --create-missing
```


## 📅 구현 계획 및 로드맵

### Phase 1: 기본 편의성 개선 (2-3주)

- [x] 사용성 분석 및 개선 방안 문서화
- [ ] `sbkube run` 명령어 구현
- [ ] `sbkube init` 명령어 구현
- [ ] `.sbkuberc` 설정 파일 지원
- [ ] 기본 테스트 및 문서 작성

### Phase 2: 고급 편의성 개선 (3-4주)

- [ ] 환경별 프로파일 지원 (`--profile` 옵션)
- [ ] 스마트 재시작 기능 (`--continue-from` 옵션)
- [ ] 향상된 로깅 및 진행률 표시
- [ ] 상태 관리 개선 및 통합

### Phase 3: 인텔리전트 기능 (4-6주)

- [ ] 설정 검증 및 진단 도구 (`sbkube doctor`)
- [ ] 자동 문제 해결 (`sbkube fix`)
- [ ] 성능 최적화 및 안정성 개선

### Phase 4: 고급 사용성 기능 (6-8주)

- [ ] 대화형 설정 마법사
- [ ] 설정 템플릿 시스템 확장
- [ ] 배포 시뮬레이션 및 미리보기
- [ ] 통합 모니터링 및 알림

## 🎯 기대 효과

### 즉시 효과 (Phase 1)

- **명령어 입력 횟수 75% 감소**: 4개 명령어 → 1개 명령어
- **프로젝트 초기 설정 시간 80% 단축**: 수동 설정 → 자동 생성
- **옵션 입력 오류 90% 감소**: 기본값 설정으로 오타 방지

### 중장기 효과 (Phase 2-3)

- **환경별 배포 실수 방지**: 프로파일 시스템으로 안전한 배포
- **디버깅 시간 60% 단축**: 스마트 재시작 및 진단 도구
- **새로운 사용자 온보딩 시간 70% 단축**: 직관적인 UX

### 전체 효과

- **개발자 생산성 3배 향상**: 반복 작업 자동화 및 오류 방지
- **도구 도입 장벽 80% 감소**: 쉬운 초기 설정 및 사용법
- **운영 안정성 크게 향상**: 환경별 관리 및 검증 도구

## 📝 기술적 고려사항

### 하위 호환성

- 모든 기존 명령어와 옵션 완전 지원
- 기존 설정 파일 구조 유지
- 점진적 마이그레이션 지원

### 성능 최적화

- 병렬 처리 가능한 작업 식별
- 캐시 시스템 활용
- 불필요한 중복 작업 제거

### 확장성

- 플러그인 시스템 고려
- 외부 도구 연동 지원

______________________________________________________________________

*이 문서는 SBKube의 사용성 개선을 위한 종합적인 방안을 제시합니다. 사용자 피드백과 실제 사용 패턴을 반영하여 지속적으로 업데이트될 예정입니다.*
