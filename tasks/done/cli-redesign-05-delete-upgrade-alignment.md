---
type: feature
priority: low
status: todo
assignee: unassigned
parent: cli-redesign-overview.md
order: 5
depends_on:
  - cli-redesign-01-positional-target.md
  - cli-redesign-04-deprecate-legacy-options.md
started-at: 2026-02-11T11:09:10+09:00
completed-at: 2026-02-11T11:11:55+09:00
completion-summary: "Applied TARGET/-f pattern to delete and upgrade with unified sbkube.yaml compatibility."
---

# [5/5] `delete/upgrade`에 TARGET 패턴 적용

## Goal

`delete`와 `upgrade` 명령어도 동일한 positional TARGET 패턴으로 통일한다.
이 두 명령어는 현재 `--app-dir`이 사실상 필수이므로 마이그레이션 우선순위가 낮다.

## Current

```bash
# delete: --app-dir 필수
sbkube delete --app-dir ph1_infra/app_010_infra_network
sbkube delete --app-dir ph1_infra/app_010_infra_network --app traefik

# upgrade: --app-dir 필수
sbkube upgrade --app-dir ph1_infra/app_010_infra_network
sbkube upgrade --app-dir ph1_infra/app_010_infra_network --app traefik
```

## After

```bash
# delete
sbkube delete ph1_infra/app_010_infra_network
sbkube delete ph1_infra/app_010_infra_network --app traefik

# upgrade
sbkube upgrade ph1_infra/app_010_infra_network
sbkube upgrade ph1_infra/app_010_infra_network --app traefik
```

## Implementation

### 1. delete.py

현재 시그니처:
```python
def cmd(ctx, app_config_dir_name: str, base_dir: str, target_app_name, ...)
```

변경:
```python
def cmd(ctx, target: str | None, config_file: str | None,
        app_config_dir_name: str | None, target_app_name, ...)
```

- `target` positional 추가
- `--app-dir`은 유지하되 deprecated
- `resolve_target()` 활용

### 2. upgrade.py

현재 시그니처:
```python
def cmd(ctx, app_config_dir_name: str, base_dir: str, target_app_name, ...)
```

동일한 패턴으로 변경.

### 3. delete/upgrade에서 unified config 지원

현재 이 두 명령어는 legacy config만 지원.
unified config에서 delete/upgrade 시:
1. TARGET 경로에서 sbkube.yaml 로드
2. apps 목록에서 대상 식별
3. helm uninstall / helm upgrade 실행

이 부분은 별도 구현 필요할 수 있음 (현재 delete.py는 config.yaml 기반).

## Files to Modify

- `sbkube/commands/delete.py` - TARGET argument 추가
- `sbkube/commands/upgrade.py` - TARGET argument 추가
- `tests/` - delete/upgrade TARGET 테스트

## Notes

- delete/upgrade는 파괴적 명령어이므로 TARGET 해석 시 확인 단계 권장
- `--app` 옵션은 `delete`에서는 `target_app_name`, `upgrade`에서도 `target_app_name`으로 명명되어 있음 → 다른 명령어의 `app_name`과 통일 검토 (별도 task)

## Execution Log

- Started: 2026-02-11T11:09:10+09:00
- Worker: AI (Codex)
- Scope summary: Added positional TARGET and `-f` path resolution to `delete` and `upgrade`, while preserving legacy behavior and adding unified config parsing support.

## Completion

- Work summary: Integrated shared target resolution into destructive commands, added unified `sbkube.yaml` parsing branches, kept legacy options with deprecation warnings, and added/updated tests for TARGET-based invocation.
- Key files changed: `sbkube/commands/delete.py`, `sbkube/commands/upgrade.py`, `sbkube/utils/common_options.py`, `tests/unit/commands/test_delete.py`, `tests/unit/commands/test_upgrade.py`
- Verification method: `pytest -q tests/unit/commands/test_delete.py tests/unit/commands/test_upgrade.py tests/unit/utils/test_common_options.py` and `ruff check sbkube/commands/delete.py sbkube/commands/upgrade.py sbkube/utils/common_options.py tests/unit/commands/test_delete.py tests/unit/commands/test_upgrade.py tests/unit/utils/test_common_options.py`
