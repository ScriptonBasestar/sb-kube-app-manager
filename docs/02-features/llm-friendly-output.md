______________________________________________________________________

## type: Feature Guide audience: Developer, AI Agent topics: [output-formats, llm, json, yaml, automation] llm_priority: high last_updated: 2025-01-04

# LLM 친화적 출력 시스템

> **LLM 에이전트 친화적 CLI 출력 포맷 가이드**

## 개요

SBKube는 LLM(Large Language Model) 에이전트가 효율적으로 사용할 수 있도록 다양한 출력 포맷을 지원합니다. 인간 친화적인 Rich Console 출력 외에도 토큰을 절약하고 파싱이 쉬운
간결한 출력 포맷을 제공합니다.

## 지원 포맷

### 1. `human` (기본값)

인간 사용자를 위한 Rich Console 출력 (기존 방식)

**특징:**

- 색상, 박스, 테이블, Progress bar 등 시각적 요소
- 상세한 로그 메시지
- 가독성 최우선

**사용 사례:** 터미널에서 직접 실행

### 2. `llm` (LLM 최적화)

LLM이 이해하기 쉬운 구조화된 텍스트 출력

**특징:**

- 80-90% 토큰 절약
- KEY: VALUE 형식의 간결한 구조
- 불필요한 장식 요소 제거
- 파싱 가능한 일관된 형식

**사용 사례:** LLM 에이전트 자동화, AI 워크플로우

### 3. `json`

기계 파싱을 위한 구조화된 JSON 출력

**특징:**

- 완전한 구조화 데이터
- 파싱 가능
- 프로그래밍 방식 처리 용이

**사용 사례:** 스크립트 통합, API 응답 형식

### 4. `yaml`

YAML 형식 출력 (PyYAML 설치 필요)

**특징:**

- 사람이 읽기 쉬운 구조화 데이터
- 설정 파일 스타일
- 주석 지원 가능

**사용 사례:** 설정 파일 생성, 문서화

## 사용 방법

### CLI 옵션으로 지정

**중요**: `--format`은 글로벌 옵션이므로 서브커맨드 **앞**에 위치해야 합니다.

```bash
# ✅ 올바른 사용법 (글로벌 옵션은 서브커맨드 앞)
sbkube --format llm apply --app-dir config
sbkube --format json deploy
sbkube --format yaml status

# ❌ 잘못된 사용법 (에러 발생)
sbkube apply --format llm  # Error: No such option: --format

# 기본값 (human)
sbkube apply
```

### 환경변수로 지정

```bash
# 세션 전체에 적용
export SBKUBE_OUTPUT_FORMAT=llm
sbkube apply
sbkube status

# 한 번만 적용
SBKUBE_OUTPUT_FORMAT=json sbkube apply
```

### 우선순위

```
CLI 옵션 > 환경변수 > 기본값 (human)
```

**예시:**

```bash
# 환경변수 설정
export SBKUBE_OUTPUT_FORMAT=json

# CLI 옵션이 우선
sbkube --format llm apply  # → llm 사용 (CLI 우선)
sbkube status              # → json 사용 (환경변수)
```

## 출력 예시

### 배포 성공 (Deployment Success)

#### human 모드

```
╭──────────────────────────────────────────────────────────╮
│  🚀 SBKube Deployment Summary                            │
├──────────────────────────────────────────────────────────┤
│  Status: ✅ Success                                      │
│  Charts Deployed: 3                                      │
│  Total Duration: 12.5s                                   │
│  Working Dir: /home/user/project/.sbkube                 │
╰──────────────────────────────────────────────────────────╯

┏━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Application ┃ Namespace ┃ Status   ┃ Version ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ nginx-app   │ default   │ RUNNING  │ 1.25.0  │
│ postgres-db │ database  │ RUNNING  │ 15.0    │
│ redis-cache │ cache     │ RUNNING  │ 7.2     │
└─────────────┴───────────┴──────────┴─────────┘

[12:34:56] INFO     Preparing Helm charts...
[12:34:57] INFO     Downloaded chart: nginx from oci://...
[12:34:58] INFO     Building manifests...
...
(수십 줄의 로그)
```

**토큰:** ~500-1000 tokens

#### llm 모드

```
STATUS: success ✅
DEPLOYED: 3 charts in 12.5s

APPLICATIONS:
- nginx-app (default): RUNNING v1.25.0
- postgres-db (database): RUNNING v15.0
- redis-cache (cache): RUNNING v7.2

NEXT STEPS:
kubectl get pods -n default
kubectl get pods -n database
kubectl get pods -n cache

ERRORS: none
```

**토큰:** ~80-100 tokens (80-90% 절약)

#### json 모드

```json
{
  "status": "success",
  "summary": {
    "charts_deployed": 3,
    "duration_seconds": 12.5,
    "timestamp": "2025-01-03T12:34:56Z"
  },
  "applications": [
    {
      "name": "nginx-app",
      "namespace": "default",
      "status": "running",
      "version": "1.25.0"
    },
    {
      "name": "postgres-db",
      "namespace": "database",
      "status": "running",
      "version": "15.0"
    },
    {
      "name": "redis-cache",
      "namespace": "cache",
      "status": "running",
      "version": "7.2"
    }
  ],
  "next_steps": [
    "kubectl get pods -n default",
    "kubectl get pods -n database",
    "kubectl get pods -n cache"
  ],
  "errors": []
}
```

**토큰:** ~150-200 tokens (구조화, 파싱 가능)

### 배포 실패 (Deployment Failure)

#### llm 모드

```
STATUS: failed ❌
DEPLOYED: 1 charts in 5.2s

APPLICATIONS:
- nginx-app (default): RUNNING v1.25.0
- postgres-db (database): FAILED
- redis-cache (cache): PENDING

ERRORS:
- postgres-db: Database connection timeout (30s)
- postgres-db: PVC claim pending (storage class not found)

NEXT STEPS:
kubectl describe pod postgres-db -n database
kubectl get pvc -n database
kubectl get storageclass
```

## LLM 에이전트 통합 가이드

### Claude Code / ChatGPT Code Interpreter

```python
import subprocess
import json

# LLM 친화적 포맷으로 실행
result = subprocess.run(
    ["sbkube", "--format", "llm", "apply"],
    capture_output=True,
    text=True
)

# 간결한 출력 파싱
if "STATUS: success" in result.stdout:
    print("배포 성공!")
    # 추가 처리...
```

### JSON 파싱 예시

```python
import subprocess
import json

# JSON 포맷으로 실행
result = subprocess.run(
    ["sbkube", "--format", "json", "status"],
    capture_output=True,
    text=True
)

# 구조화된 데이터 파싱
data = json.loads(result.stdout)
for app in data["applications"]:
    print(f"{app['name']}: {app['status']}")
```

### 환경변수 설정 (권장)

```python
import os
import subprocess

# LLM 세션 전체에 적용
os.environ["SBKUBE_OUTPUT_FORMAT"] = "llm"

# 이후 모든 sbkube 명령이 LLM 포맷으로 출력
subprocess.run(["sbkube", "apply"])
subprocess.run(["sbkube", "status"])
```

## 토큰 사용량 비교

| 작업 | human 모드 | llm 모드 | json 모드 | 절약률 (human 대비) | |------|------------|----------|-----------|---------------------|
| **간단한 배포 (3 apps)** | 500-1000 | 80-100 | 150-200 | 80-90% | | **복잡한 배포 (10 apps)** | 2000-3000 | 200-300 | 400-600 |
85-90% | | **상태 확인** | 300-500 | 50-80 | 100-150 | 80-85% | | **에러 보고** | 800-1200 | 120-180 | 200-300 | 80-85% |

## 구현 세부사항

### OutputFormatter 클래스

**위치:** `sbkube/utils/output_formatter.py`

**주요 메서드:**

```python
from sbkube.utils.output_formatter import OutputFormatter, OutputFormat

# 초기화
formatter = OutputFormatter(format_type=OutputFormat.LLM)

# 환경변수/CLI 옵션에서 자동 선택
formatter = OutputFormatter.from_env_or_cli(
    cli_format="llm",
    env_var="SBKUBE_OUTPUT_FORMAT"
)

# 배포 결과 포맷팅
result = formatter.format_deployment_result(
    status="success",
    summary={"charts_deployed": 3, "duration_seconds": 12.5},
    deployments=[...],
    next_steps=[...],
    errors=[]
)

# 출력
formatter.print_output(result)
```

### EnhancedBaseCommand 통합

모든 명령어는 Click 명령어이며, 일부는 상속하지 않는 헬퍼 클래스에 위임합니다. `EnhancedBaseCommand`(`BaseCommand`)를 상속하는 것은 현재 `init`뿐이며, 상속 시 자동으로 `output_format`을 지원합니다:

```python
from sbkube.utils.base_command import EnhancedBaseCommand

class MyCommand(EnhancedBaseCommand):
    def __init__(self, output_format="human"):
        super().__init__(output_format=output_format)

    def run(self):
        # self.formatter 사용 가능
        result = self.formatter.format_deployment_result(...)
        self.formatter.print_output(result)
```

## FAQ

### Q1: 기본 출력이 변경되나요?

**A:** 아니요. 기본값은 `human` 모드로 기존과 동일합니다.

### Q2: 모든 명령어가 지원되나요?

**A:** 현재는 `OutputFormatter` 인프라만 구축되었습니다. 개별 명령어는 점진적으로 통합될 예정입니다.

### Q3: YAML 모드가 작동하지 않아요.

**A:** PyYAML이 설치되지 않았을 수 있습니다:

```bash
uv add pyyaml
```

### Q4: LLM 모드와 JSON 모드 중 무엇을 선택해야 하나요?

**A:**

- **LLM 모드**: LLM이 직접 읽고 이해해야 하는 경우 (최대 토큰 절약)
- **JSON 모드**: 프로그래밍 방식으로 파싱해야 하는 경우

### Q5: 환경변수가 적용되지 않아요.

**A:** 대소문자 확인:

```bash
# 올바름
export SBKUBE_OUTPUT_FORMAT=llm

# 잘못됨
export sbkube_output_format=llm
```

## 로드맵

### Phase 1 (완료) ✅

- OutputFormatter 유틸리티 클래스
- CLI `--format` 옵션 추가
- 환경변수 `SBKUBE_OUTPUT_FORMAT` 지원
- EnhancedBaseCommand 통합
- 테스트 코드

### Phase 2 (완료) ✅

- ✅ `prepare` 명령어 LLM 출력 통합
- ✅ `build` 명령어 LLM 출력 통합
- ✅ `deploy` 명령어 LLM 출력 통합
- ✅ `apply` 명령어 LLM 출력 통합
- ✅ `template` 명령어 LLM 출력 통합

### Phase 3 (완료) ✅

- ✅ `status` 명령어 LLM 출력 통합 (2025-01-03 완료)
  - 클러스터 및 노드 정보
  - Helm 릴리스 상태 (앱그룹별, 네임스페이스별)
  - 구조화된 배포 목록
  - 80-85% 토큰 절약
- ✅ `history` 명령어 LLM 출력 통합
- ⏳ 나머지 명령어 통합 (`rollback`, `delete`, `upgrade` 등)

### Phase 4 (완료) ✅ - 2025-11-13

**고급 출력 포맷 최적화**

- ✅ 테이블 출력 최적화 (CSV-like format with --- separator)
  - `formatter.table()` 메서드 추가
  - LLM/JSON/YAML 포맷 지원
  - 50% 추가 토큰 절감
- ✅ 차트/그래프 데이터 최적화
  - `formatter.tree()` 메서드 추가
  - 들여쓰기 기반 구조화
  - 히스토리/의존성 트리 지원
- ✅ 에러 메시지 구조화
  - `formatter.error()` 메서드 추가
  - 에러 타입별 JSON 스키마
  - suggestions/references 배열 지원

**구현 파일:**

- `sbkube/utils/output_formatter.py` (368줄 → 794줄)
- `tests/unit/utils/test_output_formatter_phase4.py` (34 테스트)

### Phase 5 (완료) ✅ - 2025-11-13

**스트리밍 출력 지원**

- ✅ 프로그레스 바 대체
  - `formatter.progress()` 메서드 추가
  - JSONL 포맷 이벤트 스트리밍
  - 주기적 상태 업데이트
- ✅ 실시간 로그 스트리밍
  - `formatter.stream()` 메서드 추가
  - JSONL (JSON Lines) 포맷
  - 각 라인이 독립적인 JSON 객체
- ✅ 병렬 작업 출력
  - `formatter.parallel_tasks()` 메서드 추가
  - 여러 앱 동시 배포 시 구조화된 출력
  - 앱별 상태 및 진행률 표시

**구현 예시:**

```python
# Table output (LLM format)
formatter.table(
    data=[{"name": "app1", "status": "running"}],
    headers=["name", "status"],
    title="Applications"
)
# Output:
# # Applications
# NAME  STATUS
# ---
# app1  running

# Tree output (dependency structure)
formatter.tree(
    data={"apps": {"app1": "running", "app2": "pending"}},
    root_label="Deployment Status"
)

# Error with suggestions
formatter.error(
    error_type="ValidationError",
    message="Invalid config",
    code="CONFIG_001",
    suggestions=["Check YAML syntax"],
    references=["docs/config-schema.md"]
)

# Streaming progress
formatter.stream({"type": "progress", "task": "deploy", "percentage": 50})
# Output (JSONL): {"type":"progress","task":"deploy","percentage":50}

# Parallel tasks status
formatter.parallel_tasks({
    "app1": {"status": "completed", "progress": 100},
    "app2": {"status": "running", "progress": 50}
})
```

### Phase 6 (예정)

- `--format compact` 추가 (더 간결한 human 모드)
- 필드 선택 옵션 (`--fields`)
- LLM 친화적 dependency tree 출력 통합
- LLM 친화적 health check 출력 통합

## 관련 문서

- [Commands Reference](commands.md)
- [CLI Usage](../04-development/README.md)
- [Product Spec](../00-product/product-spec.md)

______________________________________________________________________

**작성일:** 2025-01-03 **버전:** v0.8.0+ **마지막 업데이트:** 2025-11-13 (Phase 4-5 완료: 고급 포맷 최적화 및 스트리밍 출력)
