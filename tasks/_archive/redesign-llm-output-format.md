---
title: "feat: LLM 출력 포맷 리디자인"
type: feature
priority: P2
effort: large
status: archived
completed-at: "2026-03-25"
archived-at: "2026-03-25"
verified-at: "2026-03-25"
verification-summary: |
  All acceptance criteria met:
  - First line shows overall status for quick LLM branching (output_formatter.py:185)
  - Per-app blocks ≤5 lines on success (lines 196-207)
  - Failure diagnostics: error/stderr/suggestion (lines 209-217)
  - Warning deduplication via set (lines 225-230)
  - USAGE.md updated with new LLM format example (lines 328-342)
  Tests: 42 passed (test_output_formatter.py, test_output_manager.py)
depends_on:
  - fix-llm-format-output-bugs
related_files:
  - sbkube/utils/output_formatter.py
  - sbkube/utils/output_manager.py
  - sbkube/commands/apply.py
---

# feat: LLM 출력 포맷 리디자인

## 전제 조건

`fix-llm-format-output-bugs` 태스크가 완료되어야 함.
버그가 수정된 상태에서 LLM 포맷의 정보 구조와 효율을 개선하는 작업.

## 현재 문제

현재 LLM 포맷은 human 포맷의 텍스트에서 Rich 마크업만 제거한 수준.
LLM에게 실제로 유용한 정보 구조가 아님:

1. **정보 중복**: 매 phase(prepare/build/deploy)마다 동일한 config 로딩 메시지 반복
2. **중간 과정 과다**: LLM은 최종 결과와 실행 가능한 정보만 필요
3. **구조 부재**: 자유 텍스트 형태라 파싱 불가
4. **토큰 비효율**: 불필요한 장식적 텍스트가 context window 소비

## 설계 원칙

### LLM이 필요로 하는 정보

LLM은 이 출력을 받아서 **다음 행동을 결정**해야 함. 따라서:

- **성공/실패 여부**: 즉시 판단 가능한 상태
- **실패 시 원인**: 디버깅에 필요한 최소 정보
- **경고 사항**: 사용자에게 전달해야 할 주의점
- **결과 요약**: 무엇이 어디에 배포되었는지
- **다음 단계**: 필요한 후속 작업

### 불필요한 정보 (제거 대상)

- Config 파일 로딩 경로 (성공 시)
- Helm repo add/update 중간 과정
- Chart 복사 경로
- Phase 시작/종료 장식 메시지
- 동일 경고의 반복

## 제안 출력 구조

### 성공 케이스 (compact)

```
SBKUBE APPLY: success
DURATION: 12.3s
APPS: 2/2 deployed

APP coredns: deployed
  namespace: kube-system
  chart: coredns/coredns
  version: latest
  release: coredns

APP haproxy: deployed
  namespace: default
  chart: haproxytech/haproxy
  version: latest
  release: haproxy

WARNINGS:
- coredns: override directory exists but not configured (overrides/coredns, 10 files)
```

### 실패 케이스 (diagnostic)

```
SBKUBE APPLY: failed
DURATION: 8.1s
APPS: 1/2 deployed

APP coredns: deployed
  namespace: kube-system

APP haproxy: failed
  namespace: default
  error: helm upgrade --install failed (exit 1)
  stderr: Error: UPGRADE FAILED: release haproxy is in a broken state
  suggestion: helm rollback haproxy 0

ERRORS:
- haproxy deployment failed: helm upgrade exit 1
```

### 핵심 설계 포인트

1. **첫 줄이 전체 상태**: `SBKUBE APPLY: success/failed/partial` → LLM이 첫 줄만 보고 분기 가능
2. **APP별 블록**: 각 앱의 결과를 독립 블록으로 구성 → 특정 앱 문제 탐색 용이
3. **실패 시에만 상세 정보**: 성공한 앱은 최소 정보, 실패한 앱은 stderr/suggestion 포함
4. **경고 통합**: 중복 제거 후 하단에 한번만 표시
5. **토큰 예산**: 성공 시 앱당 3-5줄, 실패 시 앱당 5-8줄 목표

## 구현 방향

### OutputManager 변경

현재 `OutputManager`는 human 모드에서는 실시간 출력, LLM 모드에서는 이벤트 수집 후 `finalize()`에서 출력.
이 구조 자체는 유지하되:

- **이벤트 수집 단계**: 중간 과정 메시지를 level로 필터링 (info 이하 제거 또는 별도 카테고리)
- **finalize 단계**: 수집된 이벤트를 위 구조로 재조합

### OutputFormatter 변경

`_format_llm_deployment()` 메서드를 위 구조에 맞게 재설계:

- deployment 결과 dict에 `error`, `stderr`, `suggestion` 필드 추가 지원
- 경고 메시지 deduplication 로직
- 성공/실패에 따른 정보량 동적 조절

### apply 명령 변경

- 각 phase(prepare/build/deploy)의 중간 출력을 LLM 모드에서 억제
- 최종 결과만 수집하여 한번에 출력
- phase별 타이밍 정보 수집 (선택적)

## 고려 사항

### JSON/YAML 포맷과의 관계

- JSON/YAML은 기계 파싱용 → 모든 필드를 구조화된 형태로 제공
- LLM은 자연어 파싱 → 토큰 효율적인 key-value 텍스트가 최적
- 세 포맷 간 정보의 상위집합/하위집합 관계를 명확히 정의해야 함

### 하위 호환성

- `--format human` 동작은 변경 없음
- `--format llm` 출력 구조가 변경되므로, 이를 파싱하는 외부 도구가 있는지 확인 필요
- USAGE.md에 LLM 포맷 예시 업데이트 필요

### 단계별 접근

1단계: 기본 구조 변경 (위 제안 포맷 적용)
2단계: 실패 진단 정보 강화 (stderr, suggestion)
3단계: 경고 deduplication 및 통합
4단계: USAGE.md 문서 갱신

## 테스트 방법

```bash
# 성공 케이스
sbkube apply --format llm -f sbkube.yaml

# 실패 케이스 (잘못된 chart 이름 등으로 유도)
# → 에러 정보가 진단에 충분한지 확인

# 토큰 카운트 비교 (tiktoken 등으로)
# 리디자인 전후 토큰 수 비교
```

## 수락 기준

- [ ] 성공 시 출력이 앱당 5줄 이내
- [ ] 첫 줄에 전체 상태 포함
- [ ] 실패 시 디버깅에 충분한 정보 포함 (error + stderr)
- [ ] 동일 경고 중복 없음
- [ ] human/json/yaml 포맷 동작 미영향
- [ ] USAGE.md 예시 갱신
