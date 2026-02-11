---
type: feature
priority: medium
status: todo
assignee: unassigned
parent: cli-redesign-overview.md
order: 4
depends_on:
  - cli-redesign-01-positional-target.md
  - cli-redesign-02-unified-config-support.md
started-at: 2026-02-11T11:05:40+09:00
completed-at: 2026-02-11T11:08:52+09:00
completion-summary: "Added centralized deprecated-option warnings and applied them across apply/prepare/build/template/deploy/validate."
---

# [4/5] legacy 옵션 deprecated 경고 강화

## Goal

TARGET + `-f` 도입 이후 불필요해진 legacy 옵션들에 deprecated 경고를 추가한다.
기능은 유지하되 사용자를 새 패턴으로 안내한다.

## Deprecated 대상

| 옵션 | 대체 | 영향 명령어 |
|------|------|------------|
| `--app-dir` | positional `TARGET` | apply, prepare, build, deploy, template, validate |
| `--base-dir` | TARGET full path 또는 `-f` | apply, prepare, build, deploy, template, validate |
| `--config-file` | unified sbkube.yaml (auto-detect) | apply, prepare, build, deploy, template, validate |
| `--source` (명령어 레벨) | unified sbkube.yaml의 settings | apply, prepare, build, deploy, template |

**유지 대상** (deprecated 아님):
- `--app` : 특정 앱 필터, TARGET과 다른 차원
- `--dry-run` : 그대로
- `-f/--file` : 신규 추가, 유지
- 글로벌 `--source` : profile 기반 sources 파일 선택, 용도가 다름

## Implementation

### 1. deprecated 경고 유틸리티

파일: `sbkube/utils/deprecation.py` (신규)

```python
def warn_deprecated_option(option_name: str, alternative: str) -> None:
    """deprecated 옵션 사용 시 stderr 경고."""
    click.echo(
        f"WARNING: '{option_name}' is deprecated and will be removed in v1.0. "
        f"Use '{alternative}' instead.",
        err=True,
    )
```

### 2. 각 명령어에 경고 삽입

```python
def cmd(ctx, target, config_file, app_config_dir_name, base_dir, ...):
    if app_config_dir_name:
        warn_deprecated_option("--app-dir", "positional TARGET argument")
    if base_dir != ".":
        warn_deprecated_option("--base-dir", "full path in TARGET or -f")
    if config_file_name != "config.yaml":
        warn_deprecated_option("--config-file", "-f with sbkube.yaml")
```

### 3. help 텍스트 업데이트

```python
@click.option(
    "--app-dir",
    "app_config_dir_name",
    default=None,
    help="[DEPRECATED: use positional TARGET] 앱 설정 디렉토리",
)
```

### 4. 향후 제거 계획 (이 task 범위 밖)

- 다음 마이너: `hidden=True`로 help에서 숨김
- 다음 메이저 (v1.0): 옵션 제거

## Files to Modify

- `sbkube/utils/deprecation.py` - 신규: 경고 유틸리티
- `sbkube/commands/apply.py` - 경고 삽입 (이미 일부 DEPRECATED 표시됨)
- `sbkube/commands/prepare.py` - 경고 삽입
- `sbkube/commands/build.py` - 경고 삽입
- `sbkube/commands/deploy.py` - 경고 삽입
- `sbkube/commands/template.py` - 경고 삽입
- `sbkube/commands/validate.py` - 경고 삽입

## Notes

- `apply.py`는 이미 `--app-dir`, `--config-file`, `--source`에 `[DEPRECATED]` help 텍스트가 있음
- 다른 명령어들은 아직 deprecated 표시 없음 → 이 task에서 통일

## Execution Log

- Started: 2026-02-11T11:05:40+09:00
- Worker: AI (Codex)
- Scope summary: Added unified deprecation warning utility and applied runtime/help deprecation handling to legacy options in workflow commands and validate.

## Completion

- Work summary: Created `sbkube/utils/deprecation.py` with warning and option-source detection, integrated warnings into command callbacks (only when options are explicitly set), updated help text across target commands, and added apply CLI coverage for deprecation warnings. Also fixed a pre-existing `logger` import bug in `sbkube/utils/file_loader.py` discovered during validation runs.
- Key files changed: `sbkube/utils/deprecation.py`, `sbkube/commands/apply.py`, `sbkube/commands/prepare.py`, `sbkube/commands/build.py`, `sbkube/commands/template.py`, `sbkube/commands/deploy.py`, `sbkube/commands/validate.py`, `sbkube/utils/file_loader.py`, `tests/commands/test_apply_cli.py`
- Verification method: `pytest -q tests/commands/test_apply_cli.py tests/unit/commands/test_prepare_cmd.py tests/unit/commands/test_build_cmd.py tests/unit/commands/test_template_cmd.py tests/unit/commands/test_deploy_cmd.py tests/unit/commands/test_validate_cmd.py tests/commands/test_validate_cli.py` and `ruff check sbkube/utils/deprecation.py sbkube/utils/file_loader.py sbkube/commands/apply.py sbkube/commands/prepare.py sbkube/commands/build.py sbkube/commands/template.py sbkube/commands/deploy.py sbkube/commands/validate.py tests/commands/test_apply_cli.py`
