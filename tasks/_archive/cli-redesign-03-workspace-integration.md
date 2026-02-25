---
archived-at: 2026-02-25T16:05:01+09:00
verified-at: 2026-02-25T16:05:01+09:00
verification-summary: |
  - Verified: Workspace deploy integrated with apply.
  - Evidence: Verified in CLI `workspace deploy` deprecation logic redirecting to `apply`. Workspace integration validated.
type: feature
priority: medium
status: todo
assignee: unassigned
parent: cli-redesign-overview.md
order: 3
depends_on:
  - cli-redesign-01-positional-target.md
started-at: 2026-02-11T11:02:30+09:00
completed-at: 2026-02-11T11:05:13+09:00
completion-summary: "Integrated workspace deployment controls into apply and converted workspace deploy into a deprecated redirect."
---

# [3/5] `workspace deploy` → `apply`로 통합

## Goal

`sbkube workspace deploy`와 `sbkube apply`의 이중 진입점을 해소한다.
`workspace deploy`는 `apply`의 alias로 만들고 deprecated 경고를 출력한다.

## Current (이중 경로)

```bash
# 같은 결과를 내는 4가지 방법
sbkube apply                                              # auto-detect workspace
sbkube apply --app-dir ph1_infra                          # redirect to workspace
sbkube workspace deploy                                   # 명시적 workspace
sbkube workspace deploy --phase ph1-infra                 # phase 필터
```

## After

```bash
# apply가 유일한 배포 진입점
sbkube apply                                              # workspace 전체
sbkube apply ph1_infra                                    # phase 선택 (filesystem path)
sbkube apply --phase ph1-infra                            # phase 선택 (config name)

# workspace deploy는 apply로 redirect + deprecated 경고
sbkube workspace deploy                                   # → "Use 'sbkube apply' instead"
```

## Implementation

### 1. `apply`에 `--phase` 옵션 추가

```python
@click.option("--phase", "phase_name", default=None,
              help="특정 phase만 배포 (config name 기반, 의존성 phase 포함)")
```

`--phase`는 config name 기반 필터 (예: `ph1-infra`).
`TARGET`은 filesystem path 기반 (예: `ph1_infra`).
둘 다 같은 결과를 낼 수 있으나 접근 방식이 다름.

### 2. `workspace deploy` deprecated redirect

```python
@workspace_group.command(name="deploy")
def deploy_cmd(...):
    click.echo(
        "WARNING: 'sbkube workspace deploy' is deprecated. "
        "Use 'sbkube apply' instead.",
        err=True,
    )
    # apply cmd로 위임
    ctx.invoke(apply_cmd, ...)
```

### 3. workspace 전용 명령어는 유지

아래 명령어들은 `apply`와 다른 목적이므로 유지:

```bash
sbkube workspace graph      # 의존성 그래프 시각화
sbkube workspace validate   # workspace config 검증
sbkube workspace status     # workspace 배포 상태
sbkube workspace init       # workspace 초기화
sbkube workspace history    # workspace 배포 이력
sbkube workspace cleanup    # stale 리소스 정리
```

이 명령어들도 TARGET 패턴 적용 가능:
```bash
sbkube workspace graph ~/ph3_kube/sbkube.yaml     # 기존 positional 유지
sbkube workspace validate ~/ph3_kube/sbkube.yaml
```

## Files to Modify

- `sbkube/commands/apply.py` - `--phase` 옵션 추가, WorkspaceDeployCommand 호출 경로 정리
- `sbkube/commands/workspace.py` - `deploy_cmd`에 deprecated redirect 추가

## Notes

- `--phase`와 `TARGET`이 동시에 있으면 에러 (둘은 같은 목적의 다른 방식)
- `--parallel/--no-parallel`, `--max-workers` 등 workspace deploy 전용 옵션은 `apply`로 이동

## Execution Log

- Started: 2026-02-11T11:02:30+09:00
- Worker: AI (Codex)
- Scope summary: Added workspace-phase controls to `apply`, enforced `TARGET`/`--phase` exclusivity, and redirected `workspace deploy` to `apply` with deprecation warning.

## Completion

- Work summary: Added `--phase`, `--parallel`, `--parallel-apps`, `--max-workers`, `--force`, and `--skip-validation` passthrough in `apply` for workspace mode; updated workspace deployment branches to consume those options; replaced `workspace deploy` execution with `ctx.invoke(apply_cmd, ...)` and deprecation warning.
- Key files changed: `sbkube/commands/apply.py`, `sbkube/commands/workspace.py`, `tests/commands/test_apply_cli.py`
- Verification method: `pytest -q tests/commands/test_apply_cli.py tests/unit/commands/test_workspace.py tests/unit/commands/test_apply.py` and `ruff check sbkube/commands/apply.py sbkube/commands/workspace.py tests/commands/test_apply_cli.py tests/unit/commands/test_workspace.py tests/unit/commands/test_apply.py`
