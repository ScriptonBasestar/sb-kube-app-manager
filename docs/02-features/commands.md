---
type: API Reference
audience: End User
topics: [cli, commands, reference]
llm_priority: high
last_updated: 2026-02-25
---

# ⌨️ SBKube Commands Reference

> SBKube CLI 명령어 전체 참조 문서입니다.

## TL;DR

- **Version**: v0.11.0
- **Core Workflow**: `sbkube apply -f sbkube.yaml` (prepare → build → template → deploy)
- **Config Format**: `sbkube.yaml` (unified format)
- **Output Formats**: `--format human|llm|json|yaml`
- **Related**:
  - **Config Schema**: [config-schema.md](../03-configuration/config-schema.md)
  - **App Types**: [application-types.md](application-types.md)

---

## Common Options

모든 명령어에 사용 가능한 옵션:

| Option | Description | Default |
|--------|-------------|---------|
| `--format` | 출력 형식: `human`, `llm`, `json`, `yaml` | `human` |
| `--verbose` / `-v` | 상세 로깅 | `false` |
| `--kubeconfig` | kubeconfig 경로 | 설정 파일 값 |
| `--context` | kubectl 컨텍스트 | 설정 파일 값 |
| `--help` / `-h` | 도움말 | - |

### 워크스페이스 설정 상속

중첩된 `sbkube.yaml`에서 `prepare`, `deploy`, `apply`는 상위 경로에
`.sbkube-workspace` marker가 있을 때만 클러스터·저장소 설정을 상속합니다.
우선순위는 **CLI > 앱 로컬 > phase > 워크스페이스 루트**입니다. marker 없는
앱 그룹은 임의의 상위 디렉터리를 더 이상 탐색하지 않습니다. 의도한 루트에
marker를 추가하고 공용 `settings`를 옮기거나, 앱 파일에 `kubeconfig`와
`kubeconfig_context`를 지정하세요(또는 두 CLI 옵션을 함께 전달하세요).
이 marker 조건은 **암묵적 상위 탐색**에 적용됩니다. `apply TARGET -f <root>/sbkube.yaml`
처럼 루트 파일을 명시하면 그 파일의 디렉터리가 상속 경계가 되며, 중간
문서는 그 경계 안에 있고 유효한 SBKube API 문서일 때만 읽힙니다.
`~/.kube/config`와 `default`는 더 이상 암묵 기본값이 아니므로, 클러스터가
필요한 명령은 두 값을 명시적으로 제공하지 않으면 실패합니다.

---

## Core Workflow Commands

### ⭐ apply — 통합 배포

가장 많이 사용하는 명령어. `prepare → build → template → deploy`를 순차 실행합니다.

```bash
# 옵션 1: 특정 타겟 지정 (가장 권장됨)
sbkube apply ./my-app
sbkube apply ~/project/app-group

# 옵션 2: 현재 디렉토리의 sbkube.yaml 자동 탐지
sbkube apply

# 옵션 3: 설정 파일 직접 지정
sbkube apply -f sbkube.yaml
sbkube apply -f ~/project/sbkube.yaml ./my-app

# 특정 앱만
sbkube apply -f sbkube.yaml --app grafana

# 특정 Phase만
sbkube apply -f sbkube.yaml --phase p1-infra
```

**Options**:
- `-f, --file` — 설정 파일 경로
- `--app` — 특정 앱만 실행
- `--phase` — 특정 Phase만 실행
- `--dry-run` — 실제 배포 없이 검증
- `--skip-prepare` — prepare 단계 건너뜀
- `--skip-build` — build 단계 건너뜀

### prepare — 소스 준비

Helm 차트 pull, Git clone, HTTP 다운로드를 실행합니다.

```bash
sbkube prepare [TARGET]
sbkube prepare -f sbkube.yaml --app grafana
```

### build — 차트 빌드

Overrides/Removes를 적용하여 배포 가능한 차트를 생성합니다.

```bash
sbkube build [TARGET]
sbkube build -f sbkube.yaml --app grafana
```

### template — 템플릿 렌더링

Helm template을 실행하여 최종 YAML을 생성합니다.

```bash
sbkube template [TARGET]
sbkube template -f sbkube.yaml --app grafana --output-dir rendered/
```

### deploy — 배포 실행

빌드된 차트/매니페스트를 클러스터에 배포합니다.

```bash
sbkube deploy [TARGET]
sbkube deploy -f sbkube.yaml --app grafana --dry-run
```

---

## Status & Management Commands

### status — 배포 상태

현재 배포 상태를 확인합니다.

```bash
sbkube status -f sbkube.yaml
sbkube status -f sbkube.yaml --app grafana
```

### history — 배포 이력

배포 이력을 조회합니다.

```bash
sbkube history -f sbkube.yaml
sbkube history -f sbkube.yaml --limit 10
```

### rollback — 롤백

이전 배포 상태로 롤백합니다.

```bash
sbkube rollback -f sbkube.yaml --app grafana
sbkube rollback -f sbkube.yaml --app grafana --revision 3
```

### destroy — 리소스 삭제

배포된 리소스를 삭제합니다.

```bash
sbkube destroy -f sbkube.yaml
sbkube destroy -f sbkube.yaml --app grafana
sbkube destroy -f sbkube.yaml --yes  # 확인 없이 삭제
```

### deploy gate 건너뛰기

`sbkube-gate.yaml`로 배포 게이트를 켠 저장소에서는 클러스터를 바꾸는 명령(`deploy`, `apply`,
`upgrade`, `delete`, `rollback`, `migrate`)이 게이트 명령을 먼저 돌린다
([config-schema.md](../03-configuration/config-schema.md#deploy-gate-sbkube-gateyaml)).
사람이 긴급하게 건너뛸 때만 사유와 함께 옵션을 준다.

```bash
sbkube apply --skip-deploy-gate="incident 42 hotfix"
```

- 사유가 비어 있거나 `-`로 시작하면 거부한다(`=` 형식으로 준다).
- stdin과 stderr가 모두 터미널일 때만 받는다(스크립트·CI·에이전트 셸에서는 거부).
- 작업·대상·게이트 파일·사유·사용자를 상태 DB(`~/.sbkube/deployments.db`의 `deploy_gate_skips`)에 남긴다.
- 환경변수로 게이트를 끄는 방법은 없다.

### gate grant — 에이전트 세션 허용

전역 `sbkube-gate.yaml`에 `agent_grant`를 둔 저장소에서는 사람이 에이전트 세션 하나에 게이트
통과를 허용할 수 있다. 허용은 그 세션 프로세스에서 파생된 명령에만 적용된다.

```bash
sbkube gate grant --pid 93755 --reason "TASK-123 배포"
```

- `--pid`는 에이전트 세션 프로세스다(Claude Code는 `CLAUDE_PID`). 환경변수나 세션 ID가 아니라
  프로세스 조상 관계(PID와 시작 시각)로 판정하므로 다른 세션이나 재사용된 PID에는 적용되지 않는다.
- 기간은 `agent_grant.ttl`(기본 `1h`)이다. `unlimited`면 그 프로세스가 끝날 때까지다.
- stdin과 stderr가 모두 터미널일 때만 받고, 이 터미널의 조상 프로세스(자기 셸)는 거부한다.
- 허용 기록은 상태 DB `deploy_gate_grants`에 남고, 허용으로 통과할 때마다 남은 기간을 경고로 찍는다.

---

## Utility Commands

### validate — 설정 검증

설정 파일의 문법/스키마를 검증합니다.

```bash
sbkube validate
sbkube validate -f sbkube.yaml
```

### version — 버전 정보

```bash
sbkube version
# sbkube, version 0.11.0
```

### doctor — 환경 진단

시스템 요구사항(kubectl, helm, git 등)을 확인합니다.

```bash
sbkube doctor
```

---

## Output Formats

```bash
# Rich console (기본)
sbkube --format human apply -f sbkube.yaml

# LLM에 최적화된 간결 출력 (토큰 80-90% 절감)
sbkube --format llm apply -f sbkube.yaml

# 구조화된 JSON
sbkube --format json status -f sbkube.yaml

# YAML
sbkube --format yaml status -f sbkube.yaml
```

> 상세 LLM 출력 가이드: [llm-friendly-output.md](llm-friendly-output.md)

---

## Workflow Patterns

### 표준 배포 (권장)

```bash
sbkube apply [TARGET]
# 예: sbkube apply ./ph1-infra
```

### 단계별 디버깅

```bash
sbkube validate [TARGET]           # 1. 설정 검증
sbkube prepare [TARGET]            # 2. 소스 준비
sbkube build [TARGET]              # 3. 차트 빌드
sbkube template [TARGET]           # 4. 렌더링 확인
sbkube deploy [TARGET] --dry-run   # 5. Dry-run
sbkube deploy [TARGET]             # 6. 실제 배포
```

### 특정 앱만 재배포

```bash
sbkube apply [TARGET] --app grafana --skip-prepare
```

### Multi-Phase 배포

```bash
# 전체 Phase 순서대로
sbkube apply [TARGET]

# 특정 Phase만
sbkube apply [TARGET] --phase p1-infra
```

---

## Related Documentation

- **Config Schema**: [config-schema.md](../03-configuration/config-schema.md)
- **App Types**: [application-types.md](application-types.md)
- **Hooks**: [hooks-guide.md](hooks-guide.md)
- **Troubleshooting**: [../07-troubleshooting/README.md](../07-troubleshooting/README.md)

---

**Document Version**: 3.0
**Last Updated**: 2026-02-25
**SBKube Version**: 0.11.0
