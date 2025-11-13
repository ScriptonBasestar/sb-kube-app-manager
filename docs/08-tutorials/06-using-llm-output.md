# LLM 친화적 출력 활용 가이드

> **대상**: AI 에이전트, 자동화 스크립트, CI/CD 파이프라인 **버전**: v0.7.0+ **난이도**: 쉬움 **소요 시간**: 10-15분

______________________________________________________________________

## 🎯 개요

v0.7.0부터 SBKube는 LLM(Large Language Model)이 이해하기 쉬운 출력 포맷을 지원합니다.

**주요 장점**:

- 토큰 사용량 **80-90% 절감**
- 구조화된 데이터 포맷 (파싱 용이)
- 일관된 출력 형식
- AI 에이전트 통합 최적화

______________________________________________________________________

## 📋 지원 포맷

### 1. Human Format (기본)

```bash
sbkube status
# 또는
sbkube status --format human
```

**특징**:

- Rich Console 출력 (색상, 테이블, 아이콘)
- 사람이 읽기 쉬운 형태
- 터미널 환경에 최적화

**예시 출력**:

```
✨ Deployment Status ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────┬─────────┬─────────┬─────────┐
│ App     │ Status  │ Version │ Updated │
├─────────┼─────────┼─────────┼─────────┤
│ redis   │ running │ 18.0.0  │ 2m ago  │
│ grafana │ running │ 6.50.0  │ 5m ago  │
└─────────┴─────────┴─────────┴─────────┘

🎉 All apps are healthy
```

**토큰 수**: ~500 tokens

______________________________________________________________________

### 2. LLM Format (AI 최적화)

```bash
sbkube status --format llm
```

**특징**:

- 불필요한 장식 제거
- 키-값 쌍 또는 YAML 형식
- 구조화된 데이터
- 토큰 사용량 최소화

**예시 출력**:

```
deployment_status:
  redis:
    status: running
    version: 18.0.0
    updated: 2025-11-13T10:00:00Z
  grafana:
    status: running
    version: 6.50.0
    updated: 2025-11-13T09:55:00Z

summary:
  total: 2
  healthy: 2
  failed: 0
```

**토큰 수**: ~100 tokens **(80% 절감!)**

______________________________________________________________________

### 3. JSON Format (프로그래밍)

```bash
sbkube status --format json
```

**특징**:

- 표준 JSON 출력
- 프로그래밍 언어에서 파싱 용이
- API 응답과 유사

**예시 출력**:

```json
{
  "deployment_status": {
    "redis": {
      "status": "running",
      "version": "18.0.0",
      "updated": "2025-11-13T10:00:00Z"
    },
    "grafana": {
      "status": "running",
      "version": "6.50.0",
      "updated": "2025-11-13T09:55:00Z"
    }
  },
  "summary": {
    "total": 2,
    "healthy": 2,
    "failed": 0
  }
}
```

**토큰 수**: ~120 tokens

______________________________________________________________________

### 4. YAML Format

```bash
sbkube status --format yaml
```

**특징**:

- 읽기 쉬운 YAML 형식
- 설정 파일과 일관성
- 주석 가능 (일부 명령어)

**예시 출력**:

```yaml
deployment_status:
  redis:
    status: running
    version: 18.0.0
    updated: 2025-11-13T10:00:00Z
  grafana:
    status: running
    version: 6.50.0
    updated: 2025-11-13T09:55:00Z

summary:
  total: 2
  healthy: 2
  failed: 0
```

**토큰 수**: ~110 tokens

______________________________________________________________________

## 🔧 명령어별 지원 상태

| 명령어 | human | llm | json | yaml | 비고 | |--------|-------|-----|------|------|------| | `status` | ✅ | ✅ | ✅ | ✅ | 완전
지원 | | `history` | ✅ | ✅ | ✅ | ✅ | 완전 지원 | | `rollback` | ✅ | ✅ | ✅ | ✅ | 완전 지원 | | `apply` | ✅ | ✅ | ⚠️ | ⚠️ | 부분 지원 |
| `validate` | ✅ | ✅ | ✅ | ✅ | 완전 지원 | | `prepare` | ✅ | ⚠️ | ❌ | ❌ | 프로그레스 제한 | | `build` | ✅ | ⚠️ | ❌ | ❌ | 프로그레스 제한 |
| `deploy` | ✅ | ⚠️ | ❌ | ❌ | 실시간 로그 |

**범례**:

- ✅ 완전 지원: 모든 출력이 해당 포맷으로 제공
- ⚠️ 부분 지원: 일부 출력은 human 포맷으로 fallback
- ❌ 미지원: v0.9.0에서 지원 예정

______________________________________________________________________

## 💡 실전 활용 예시

### 예시 1: AI 에이전트 통합

```python
import subprocess
import json

def get_deployment_status() -> dict:
    """SBKube 배포 상태를 조회하여 AI 에이전트에 전달."""
    result = subprocess.run(
        ["sbkube", "status", "--format", "json"],
        capture_output=True,
        text=True,
        check=True
    )

    data = json.loads(result.stdout)
    return data

# AI 에이전트에 전달
status = get_deployment_status()
agent.analyze(status)

# 실패한 앱만 필터링
failed_apps = [
    app for app, info in status["deployment_status"].items()
    if info["status"] == "failed"
]

if failed_apps:
    agent.remediate(failed_apps)
```

______________________________________________________________________

### 예시 2: 자동화 스크립트 (Bash)

```bash
#!/bin/bash

# 배포 상태를 JSON으로 저장
sbkube status --format json > status.json

# jq로 파싱
FAILED_COUNT=$(jq '.summary.failed' status.json)

if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "❌ $FAILED_COUNT apps failed"

    # 실패한 앱 목록 추출
    jq -r '.deployment_status | to_entries[] | select(.value.status == "failed") | .key' status.json

    # 실패한 앱만 재배포
    while read -r app; do
        echo "Redeploying $app..."
        sbkube deploy --app "$app" --format llm
    done < <(jq -r '.deployment_status | to_entries[] | select(.value.status == "failed") | .key' status.json)
else
    echo "✅ All apps are healthy"
fi
```

______________________________________________________________________

### 예시 3: CI/CD 파이프라인 (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy to Kubernetes

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install SBKube
        run: |
          pip install sbkube

      - name: Deploy with LLM format
        run: |
          sbkube apply --format llm > deploy.log

      - name: Parse deployment result
        run: |
          # LLM format은 파싱하기 쉬움
          if grep -q "status: failed" deploy.log; then
            echo "❌ Deployment failed"
            cat deploy.log
            exit 1
          else
            echo "✅ Deployment succeeded"
          fi

      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: deployment-logs
          path: deploy.log
```

______________________________________________________________________

### 예시 4: Python 모니터링 스크립트

```python
import subprocess
import yaml
import time
from typing import Dict, List

def monitor_deployments(interval: int = 60) -> None:
    """주기적으로 배포 상태를 모니터링."""
    while True:
        result = subprocess.run(
            ["sbkube", "status", "--format", "yaml"],
            capture_output=True,
            text=True,
            check=True
        )

        status = yaml.safe_load(result.stdout)

        # 실패한 앱 감지
        failed_apps = [
            app for app, info in status["deployment_status"].items()
            if info["status"] == "failed"
        ]

        if failed_apps:
            send_alert(f"Apps failed: {', '.join(failed_apps)}")

        time.sleep(interval)

def send_alert(message: str) -> None:
    """Slack, Email 등으로 알림 전송."""
    print(f"🚨 ALERT: {message}")
    # 실제 알림 로직
```

______________________________________________________________________

### 예시 5: LLM 프롬프트 통합

```python
import anthropic
import subprocess
import json

def ask_llm_about_deployment() -> str:
    """Claude에게 배포 상태를 분석하도록 요청."""
    # SBKube 상태 조회 (LLM 포맷)
    result = subprocess.run(
        ["sbkube", "status", "--format", "llm"],
        capture_output=True,
        text=True,
        check=True
    )

    llm_output = result.stdout

    # Claude API 호출
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""
다음은 Kubernetes 배포 상태입니다:

{llm_output}

문제가 있는지 분석하고 개선 방안을 제시해주세요.
"""
        }]
    )

    return message.content[0].text

# 실행
analysis = ask_llm_about_deployment()
print(analysis)
```

______________________________________________________________________

## 📊 토큰 절감 효과

### 명령어별 토큰 비교

| 명령어 | Human 포맷 | LLM 포맷 | 절감율 | JSON 포맷 | |--------|-----------|---------|--------|-----------| | `status` | 500 | 100
| 80% | 120 | | `history` | 1200 | 200 | 83% | 250 | | `validate` | 800 | 150 | 81% | 180 | | `rollback` | 600 | 120 |
80% | 140 |

### 실제 시나리오

**시나리오**: 10개 앱 배포 상태 조회 (1시간에 1회, 24시간)

```
Human 포맷:
- 1회 조회: 500 tokens
- 24시간: 500 × 24 = 12,000 tokens

LLM 포맷:
- 1회 조회: 100 tokens
- 24시간: 100 × 24 = 2,400 tokens

절감: 9,600 tokens (80%)
비용 절감 (GPT-4 기준): ~$0.29/일
```

______________________________________________________________________

## ⚙️ 고급 사용법

### 1. 환경 변수로 기본 포맷 설정

```bash
# .bashrc 또는 .zshrc
export SBKUBE_OUTPUT_FORMAT=llm

# 이후 모든 명령어에서 --format 생략 가능
sbkube status  # 자동으로 LLM 포맷 사용
```

______________________________________________________________________

### 2. 조용한 모드 (`--quiet`)

```bash
# 경고 및 정보 메시지 생략, 결과만 출력
sbkube status --format json --quiet

# 파이프라인에 유용
sbkube status --format json --quiet | jq '.summary.failed'
```

______________________________________________________________________

### 3. 포맷 변환 스크립트

```python
import subprocess
import json
import yaml

def convert_format(from_format: str, to_format: str) -> str:
    """SBKube 출력을 다른 포맷으로 변환."""
    result = subprocess.run(
        ["sbkube", "status", "--format", from_format],
        capture_output=True,
        text=True,
        check=True
    )

    if from_format == "json":
        data = json.loads(result.stdout)
    elif from_format == "yaml":
        data = yaml.safe_load(result.stdout)
    else:
        raise ValueError(f"Unsupported format: {from_format}")

    if to_format == "json":
        return json.dumps(data, indent=2)
    elif to_format == "yaml":
        return yaml.dump(data, default_flow_style=False)
    else:
        raise ValueError(f"Unsupported format: {to_format}")

# JSON → YAML 변환
yaml_output = convert_format("json", "yaml")
print(yaml_output)
```

______________________________________________________________________

## 🚧 제한사항 (v0.7.0)

### 1. 프로그레스 바 제한

**현재**:

```bash
sbkube prepare --format llm
# 프로그레스 바는 human 포맷으로 표시됨
```

**이유**: 실시간 스트리밍 출력은 Phase 5에서 지원 예정

______________________________________________________________________

### 2. 일부 명령어 미지원

**미지원 명령어**:

- `prepare`, `build`: 프로그레스 바가 핵심
- `deploy`: 실시간 로그 스트리밍

**대안**:

```bash
# 로그를 파일로 저장 후 파싱
sbkube deploy --app redis 2>&1 | tee deploy.log

# 또는 --quiet 모드 사용
sbkube deploy --app redis --quiet
```

______________________________________________________________________

### 3. 컬러 출력 제거

**LLM/JSON/YAML 포맷**:

- ANSI 컬러 코드 제거
- 순수 텍스트 출력

**필요 시 컬러 유지**:

```bash
# 컬러를 유지하려면 human 포맷 사용
sbkube status --format human
```

______________________________________________________________________

## 🔮 향후 개선 계획 (v0.9.0)

### Phase 4: 고급 포맷 최적화 (진행 중)

- 테이블 출력 → CSV-like 포맷
- 차트/그래프 → 구조화된 데이터
- 에러 메시지 → JSON 스키마

**예시 (예정)**:

```bash
sbkube status --format llm

# 현재 (v0.7.0)
deployment_status:
  redis:
    status: running

# v0.9.0 (예정)
NAME    STATUS   VERSION  UPTIME
redis   running  18.0.0   2h15m
---
```

______________________________________________________________________

### Phase 5: 스트리밍 출력 (계획)

- JSONL (JSON Lines) 포맷 지원
- 실시간 프로그레스 업데이트
- 병렬 작업 출력 구조화

**예시 (예정)**:

```bash
sbkube deploy --format jsonl --all

# 출력 (실시간 스트리밍)
{"type":"log","level":"info","message":"Starting deployment"}
{"type":"progress","app":"redis","status":"running","progress":50}
{"type":"progress","app":"grafana","status":"completed","progress":100}
{"type":"result","status":"success","apps":["redis","grafana"]}
```

______________________________________________________________________

## 🎓 모범 사례

### 1. CI/CD에서는 LLM 또는 JSON 사용

```yaml
# ✅ Good - 파싱 가능
- run: sbkube apply --format llm

# ❌ Bad - 파싱 어려움
- run: sbkube apply
```

______________________________________________________________________

### 2. 사람이 보는 로그는 Human 유지

```bash
# ✅ Good - 개발 중
sbkube status

# ❌ Bad - 읽기 어려움
sbkube status --format json
```

______________________________________________________________________

### 3. 에러 처리 시 상세 로그 활성화

```bash
# ✅ Good - 디버깅 가능
sbkube apply --format llm --log-level DEBUG 2>&1 | tee deploy.log

# ❌ Bad - 에러 원인 파악 어려움
sbkube apply --format llm --quiet
```

______________________________________________________________________

### 4. 대용량 출력은 파일로 저장

```bash
# ✅ Good - 메모리 효율적
sbkube history --format json > history.json

# ❌ Bad - 터미널 출력 넘침
sbkube history --format json
```

______________________________________________________________________

## 📚 관련 문서

- [LLM 친화적 출력 기능](../02-features/llm-friendly-output.md) - 기술 세부사항
- [Commands Reference](../02-features/commands.md) - 명령어별 옵션
- [API Contract](../10-modules/sbkube/API_CONTRACT.md) - 출력 스키마
- [OutputFormatter 구현](../../sbkube/utils/output_formatter.py) - 소스 코드

______________________________________________________________________

## 🆘 문제 해결

### Q: LLM 포맷이 적용 안됨

**증상**:

```bash
sbkube status --format llm
# 여전히 Rich Console 출력
```

**원인**: 환경 변수가 우선

**해결**:

```bash
unset SBKUBE_OUTPUT_FORMAT
sbkube status --format llm
```

______________________________________________________________________

### Q: JSON 파싱 에러

**증상**:

```python
json.loads(result.stdout)
# JSONDecodeError
```

**원인**: 에러 메시지가 섞임

**해결**:

```python
result = subprocess.run(
    ["sbkube", "status", "--format", "json"],
    capture_output=True,
    text=True,
    check=True  # 에러 시 예외 발생
)

try:
    data = json.loads(result.stdout)
except json.JSONDecodeError:
    # stderr 확인
    print(result.stderr)
    raise
```

______________________________________________________________________

### Q: 토큰 절감 효과가 적음

**원인**: 데이터 자체가 적음

**해설**:

- 소규모 배포 (1-2개 앱): 절감 효과 미미
- 대규모 배포 (10+ 앱): 절감 효과 명확
- 반복 조회: 누적 절감 효과 증가

______________________________________________________________________

**마지막 업데이트**: 2025-11-13 **적용 버전**: v0.7.0+ **다음 업데이트**: v0.9.0 (Phase 4-5)
