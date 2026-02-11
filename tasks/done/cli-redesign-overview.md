---
type: epic
priority: high
status: todo
assignee: unassigned
related:
  - cli-redesign-01-positional-target.md
  - cli-redesign-02-unified-config-support.md
  - cli-redesign-03-workspace-integration.md
  - cli-redesign-04-deprecate-legacy-options.md
  - cli-redesign-05-delete-upgrade-alignment.md
started-at: 2026-02-11T11:12:20+09:00
completed-at: 2026-02-11T11:12:43+09:00
completion-summary: "All 5 CLI redesign child tasks completed and merged; TARGET-first CLI flow is now implemented across core commands."
---

# CLI Redesign: `--app-dir` 제거 및 positional TARGET 도입

## Background

sbkube의 config 모델은 `phases:` 재귀 구조로 통일되어 있으나, CLI 옵션은 이를 반영하지 못하고 있다.

현행 문제:
1. `--app-dir`은 "filesystem path to a phase"인데 이름이 모호 (app? dir?)
2. `apply`만 `-f` unified config 지원, `prepare/build/template/deploy`는 legacy만
3. `sbkube apply`와 `sbkube workspace deploy`가 이중 진입점
4. `--base-dir` + `--app-dir` + `--config-file` + `--source` 4개 옵션 조합이 복잡
5. 프로젝트 외부에서 실행 시 `--base-dir` 필수 → 긴 명령어

## Design Decisions

### 1. positional TARGET으로 통일

```bash
# 현행
sbkube apply --base-dir ~/ph3_kube --app-dir ph1_infra/app_010

# 재설계
sbkube apply ph1_infra/app_010                     # 프로젝트 안
sbkube apply ~/ph3_kube/ph1_infra/app_010          # 프로젝트 밖
```

TARGET은 filesystem path. sbkube.yaml을 upward search로 찾는다.

### 2. config 구조와 CLI 일치

config는 재귀적 `phases:`이므로 CLI도 "phase"와 "group"을 구분하지 않는다.
TARGET의 depth가 자연스럽게 scope를 결정한다.

```
sbkube apply                    → workspace 전체
sbkube apply ph1_infra          → phase 전체
sbkube apply ph1_infra/app_010  → leaf phase
```

### 3. `-f`는 보조 수단

```bash
sbkube apply -f ~/ph3_kube/sbkube.yaml                          # config만
sbkube apply -f ~/ph3_kube/sbkube.yaml ph1_infra/app_010        # config + scope
```

### 4. `--base-dir` 불필요

TARGET이 full path를 허용하고 upward search가 sbkube.yaml을 찾으므로 `--base-dir`은 deprecated 대상.

## Non-Goals

- config model (PhaseReference, UnifiedConfig) 변경 없음
- workspace 전용 명령어 (graph, status, validate, init) 구조는 유지
- `--app` (특정 앱 필터) 옵션은 그대로 유지

## Implementation Order

| 순서 | Task | Breaking |
|:----:|------|:--------:|
| 1 | `apply`에 positional TARGET + upward search | No |
| 2 | `prepare/build/template/deploy`에 `-f` + TARGET | No |
| 3 | `workspace deploy` → `apply`로 redirect + deprecated | No |
| 4 | `--app-dir`, `--base-dir`, `--config-file`, `--source` deprecated 경고 | No |
| 5 | `delete/upgrade`에 TARGET 패턴 적용 | No |

모든 단계는 기존 옵션과 병존하므로 비파괴적 점진 적용.

## Execution Log

- Started: 2026-02-11T11:12:20+09:00
- Worker: AI (Codex)
- Scope summary: Verified all linked redesign tasks were completed and aligned in `tasks/done/`, then closed the epic.

## Completion

- Work summary: Confirmed completion of all related tasks (`01`-`05`), including positional TARGET adoption, workspace integration, and legacy deprecation rollout.
- Key files changed: `tasks/done/cli-redesign-overview.md` (moved from todo)
- Verification method: Checked presence of all child task files in `tasks/done/`.
