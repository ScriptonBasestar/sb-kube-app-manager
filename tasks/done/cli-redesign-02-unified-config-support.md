---
type: feature
priority: high
status: todo
assignee: unassigned
parent: cli-redesign-overview.md
order: 2
depends_on:
  - cli-redesign-01-positional-target.md
started-at: 2026-02-11T11:00:05+09:00
completed-at: 2026-02-11T11:02:07+09:00
completion-summary: "Added shared TARGET/-f option handling and integrated unified target resolution into prepare/build/template/deploy."
---

# [2/5] `prepare/build/template/deploy`에 `-f` + TARGET 추가

## Goal

핵심 워크플로우 명령어들이 unified config (`sbkube.yaml`)를 직접 지원하도록 한다.
현재는 `apply`만 `-f` 지원하고, 개별 단계 명령어는 legacy 옵션만 사용 가능.

## Current

```bash
# 개별 단계 실행 시 legacy 옵션 필수
sbkube prepare --app-dir ph1_infra/app_010 --config-file config.yaml --source sources.yaml
sbkube build --app-dir ph1_infra/app_010 --config-file config.yaml
sbkube deploy --app-dir ph1_infra/app_010 --config-file config.yaml

# unified config로는 apply만 가능
sbkube apply -f sbkube.yaml  # OK
sbkube prepare -f sbkube.yaml  # ERROR: no such option
```

## After

```bash
# 모든 명령어에서 동일 패턴
sbkube prepare ph1_infra/app_010_infra_network
sbkube build ph1_infra/app_010_infra_network
sbkube template ph1_infra/app_010_infra_network
sbkube deploy ph1_infra/app_010_infra_network

# -f도 가능
sbkube prepare -f ph1_infra/app_010_infra_network/sbkube.yaml
```

## Implementation

### 1. 공통 옵션 데코레이터

task-01의 `target_resolver.py`에서 만든 `ResolvedTarget`을 활용하여 공통 데코레이터 생성.

파일: `sbkube/utils/common_options.py` (신규)

```python
def target_options(f):
    """공통 TARGET + -f 옵션 데코레이터."""
    f = click.argument("target", required=False, default=None,
                       type=click.Path(exists=True, file_okay=False, dir_okay=True))(f)
    f = click.option("-f", "--file", "config_file", default=None,
                     type=click.Path(exists=True, file_okay=True, dir_okay=False),
                     help="Unified config file (sbkube.yaml)")(f)
    f = click.option("--app", "app_name", default=None,
                     help="적용할 특정 앱 이름")(f)
    f = click.option("--dry-run", is_flag=True, default=False)(f)
    return f
```

### 2. 각 명령어에 TARGET 경로 지원 추가

각 명령어의 `cmd` 함수에서:
1. `target` + `config_file` → `resolve_target()` 호출
2. unified config이면 → `sbkube.yaml`에서 settings + apps 로드
3. legacy이면 → 기존 로직 유지 (deprecated 경고)

### 3. unified config에서 개별 단계 실행 시 동작

`sbkube prepare ph1_infra/app_010_infra_network` 실행 시:
1. `app_010_infra_network/sbkube.yaml` 로드
2. `settings`에서 helm_repos, git_repos 등 추출 (+ 상위 상속)
3. `apps`에서 prepare 대상 추출
4. prepare 실행

상위 settings 상속은 이미 `prepare.py`에 구현되어 있음 (inherited_settings 패턴).

## Files to Modify

- `sbkube/utils/common_options.py` - 신규: 공통 데코레이터
- `sbkube/commands/prepare.py` - TARGET + `-f` 지원
- `sbkube/commands/build.py` - TARGET + `-f` 지원
- `sbkube/commands/template.py` - TARGET + `-f` 지원
- `sbkube/commands/deploy.py` - TARGET + `-f` 지원
- `tests/` - 각 명령어 TARGET 테스트

## Notes

- 기존 `--app-dir`, `--config-file`, `--source` 옵션은 유지 (task-04에서 deprecated)
- TARGET이 있으면 legacy 옵션 무시하는 우선순위 로직은 task-01의 resolve_target과 동일

## Execution Log

- Started: 2026-02-11T11:00:05+09:00
- Worker: AI (Codex)
- Scope summary: Added shared CLI target option helpers and applied them across `prepare`, `build`, `template`, and `deploy` while preserving legacy flags.

## Completion

- Work summary: Created `sbkube/utils/common_options.py` with `target_options` and `resolve_command_paths`, updated command signatures and decorators for TARGET/`-f` support, and ensured unified config path precedence is consistently applied.
- Key files changed: `sbkube/utils/common_options.py`, `sbkube/commands/prepare.py`, `sbkube/commands/build.py`, `sbkube/commands/template.py`, `sbkube/commands/deploy.py`, `tests/unit/utils/test_common_options.py`, `tests/unit/commands/test_prepare_cmd.py`, `tests/unit/commands/test_build_cmd.py`, `tests/unit/commands/test_template_cmd.py`, `tests/unit/commands/test_deploy_cmd.py`
- Verification method: `pytest -q tests/unit/utils/test_common_options.py tests/unit/commands/test_prepare_cmd.py tests/unit/commands/test_build_cmd.py tests/unit/commands/test_template_cmd.py tests/unit/commands/test_deploy_cmd.py` and `ruff check sbkube/utils/common_options.py sbkube/commands/prepare.py sbkube/commands/build.py sbkube/commands/template.py sbkube/commands/deploy.py tests/unit/utils/test_common_options.py tests/unit/commands/test_prepare_cmd.py tests/unit/commands/test_build_cmd.py tests/unit/commands/test_template_cmd.py tests/unit/commands/test_deploy_cmd.py`
