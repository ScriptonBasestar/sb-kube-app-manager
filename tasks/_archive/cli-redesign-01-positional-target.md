---
archived-at: 2026-02-25T16:05:01+09:00
verified-at: 2026-02-25T16:05:01+09:00
verification-summary: |
  - Verified: CLI redesign tasks functionality. Target and config parameters resolution.
  - Evidence: Validation of sbkube/commands/*.py implementation matching task requirements and docs updated to feature positional target args.
type: feature
priority: high
status: todo
assignee: unassigned
parent: cli-redesign-overview.md
order: 1
started-at: 2026-02-11T10:58:58+09:00
completed-at: 2026-02-11T10:59:07+09:00
completion-summary: "Added positional TARGET resolution for apply with upward sbkube.yaml discovery and scope-aware -f support."
---

# [1/5] `apply`에 positional TARGET 추가 + upward search

## Goal

`sbkube apply` 명령에 optional positional argument `TARGET`을 추가하여 `--app-dir` + `--base-dir` 조합을 대체한다.

## Current

```bash
sbkube apply --base-dir ~/ph3_kube --app-dir ph1_infra/app_010_infra_network
sbkube apply --app-dir ph1_infra/app_010_infra_network  # CWD가 ph3_kube일 때
sbkube apply                                             # 전체 workspace
```

## After

```bash
sbkube apply ~/ph3_kube/ph1_infra/app_010_infra_network  # full path
sbkube apply ph1_infra/app_010_infra_network              # CWD 기준 상대경로
sbkube apply ph1_infra                                    # phase 전체
sbkube apply                                              # workspace 전체
```

## Implementation

### 1. `apply.py` cmd 함수에 positional argument 추가

```python
@click.command(name="apply")
@click.argument("target", required=False, default=None,
                type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("-f", "--file", "config_file", ...)  # 기존 유지
# --app-dir, --base-dir 등 기존 옵션도 유지 (deprecated 경고만 추가)
```

### 2. TARGET 해석 로직 (새 유틸리티 함수)

파일: `sbkube/utils/target_resolver.py` (신규)

```
resolve_target(target, config_file) -> ResolvedTarget:
    1. target이 None이면 → CWD에서 sbkube.yaml 감지 (기존 detect_config_file)
    2. target이 있으면 → resolve to absolute path
    3. target 디렉토리에 sbkube.yaml이 있으면 → 해당 phase/workspace 배포
    4. 없으면 → 상위로 sbkube.yaml 탐색 (find_sources_file_upward 패턴 활용)
    5. 찾은 sbkube.yaml의 위치 = workspace root
    6. target과 workspace root의 relative path = scope filter
```

반환값:
```python
@dataclass
class ResolvedTarget:
    workspace_root: Path          # sbkube.yaml이 있는 디렉토리
    config_file: Path             # sbkube.yaml 경로
    scope_path: str | None        # workspace root 기준 상대경로 (None이면 전체)
```

### 3. 기존 옵션과의 병존

- `TARGET`이 있으면 → `--app-dir`, `--base-dir` 무시 (경고 출력)
- `TARGET`이 없고 `--app-dir` 있으면 → 기존 로직 (deprecated 경고)
- 둘 다 없으면 → CWD에서 auto-detect (기존 동작)

### 4. `-f`와의 조합

- `-f`만 → config 파일 위치 기준 동작
- `TARGET`만 → upward search로 config 찾기
- `-f` + `TARGET` → `-f`가 config, `TARGET`은 scope (상대경로는 config 파일 위치 기준)

## Files to Modify

- `sbkube/commands/apply.py` - TARGET argument 추가, 해석 로직
- `sbkube/utils/target_resolver.py` - 신규: resolve_target 유틸리티
- `tests/` - TARGET 해석 테스트

## Testing

```bash
# 프로젝트 안에서
cd ph3_kube && sbkube apply                                    # 전체
cd ph3_kube && sbkube apply ph1_infra                          # phase
cd ph3_kube && sbkube apply ph1_infra/app_010_infra_network    # leaf

# 프로젝트 밖에서
cd ~ && sbkube apply ~/ph3_kube                                # 전체
cd ~ && sbkube apply ~/ph3_kube/ph1_infra/app_010_infra_network  # leaf

# -f 조합
sbkube apply -f ~/ph3_kube/sbkube.yaml ph1_infra/app_010_infra_network

# 기존 옵션 호환 (deprecated 경고 출력 확인)
sbkube apply --app-dir ph1_infra/app_010_infra_network
sbkube apply --base-dir ~/ph3_kube --app-dir ph1_infra
```

## Execution Log

- Started: 2026-02-11T10:58:58+09:00
- Worker: AI (Codex)
- Scope summary: Added `TARGET` argument in `apply`, implemented reusable resolver for upward config detection, and integrated target/file scope precedence.

## Completion

- Work summary: Implemented `sbkube/utils/target_resolver.py`, wired positional `TARGET` and scope logic into `sbkube apply`, added phase-scope matching fallback for workspace configs, and added resolver/apply tests.
- Key files changed: `sbkube/commands/apply.py`, `sbkube/utils/target_resolver.py`, `tests/unit/utils/test_target_resolver.py`, `tests/commands/test_apply_cli.py`
- Verification method: `pytest -q tests/unit/utils/test_target_resolver.py tests/commands/test_apply_cli.py tests/unit/commands/test_apply.py` and `ruff check sbkube/commands/apply.py sbkube/utils/target_resolver.py tests/unit/utils/test_target_resolver.py tests/commands/test_apply_cli.py`
