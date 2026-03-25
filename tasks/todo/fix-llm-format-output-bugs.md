---
title: "fix: --format llm 출력 버그 수정 (6건)"
type: bug
priority: P1
effort: medium
status: todo
related_files:
  - sbkube/commands/apply.py
  - sbkube/utils/output_formatter.py
  - sbkube/utils/output_manager.py
  - sbkube/utils/app_dir_resolver.py
  - sbkube/commands/deploy.py
---

# fix: --format llm 출력 버그 수정

## 배경

`sbkube apply --format llm` 실행 시, LLM 최적화 출력이 전혀 동작하지 않고 human 포맷 그대로 출력됨.
이모지, 프로그레스바, 중복 경고가 모두 포함되어 LLM이 파싱하기에 비효율적.

## 발견된 버그 목록

### Bug 1: format_type 전파 실패 (근본 원인)

- **위치**: `sbkube/commands/apply.py:189`
- **증상**: `--format llm` 지정해도 모든 출력이 human 모드로 나옴
- **원인**: `ApplyCommand.execute()` 내부에서 하위 명령 실행용 `ctx.obj`를 생성할 때 format이 `"human"`으로 하드코딩됨
- **영향**: prepare/build/deploy 모든 하위 단계에서 format_type이 무시됨
- **수정 방향**: `self.format_type` 또는 부모 context에서 전달받은 format 값을 사용하도록 변경. `ApplyCommand.__init__`의 `format_type` 파라미터(line 53)가 이미 존재하므로 이를 활용

### Bug 2: sbkube.yaml을 SourceScheme으로 파싱 시도 → "Extra inputs" 경고

- **위치**: `sbkube/utils/app_dir_resolver.py:75-80`
- **증상**: build/deploy 단계마다 아래 경고가 반복 출력:
  ```
  Warning: Could not load sbkube.yaml: Configuration validation failed:
    - apiVersion: Extra inputs are not permitted
    - metadata: Extra inputs are not permitted
    - settings: Extra inputs are not permitted
    - apps: Extra inputs are not permitted
  ```
- **원인**: `resolve_app_dirs()` 함수에서 `sources_file_name`으로 전달된 `sbkube.yaml`을 `SourceScheme(**sources_data)`로 파싱 시도. unified format(`apiVersion: sbkube/v1`)은 `SourceScheme`과 구조가 다르므로 Pydantic `extra="forbid"` 검증에서 실패
- **핵심 이해**: prepare 단계는 자체 unified format 감지 로직이 있어 정상. build/deploy는 `resolve_app_dirs()`를 거치면서 SourceScheme 파싱을 먼저 시도하기 때문에 경고 발생
- **수정 방향**: `resolve_app_dirs()`에서 unified format 여부를 먼저 체크 (`apiVersion` 필드 존재 확인). unified format이면 SourceScheme 파싱을 스킵하거나, unified config에서 sources 정보를 추출하는 별도 경로 추가

### Bug 3: _format_llm_deployment 에러 출력 로직 버그

- **위치**: `sbkube/utils/output_formatter.py:203-208`
- **증상**: 에러가 있어도 `ERRORS: none`이 항상 추가됨. 에러가 없으면 for 루프만 스킵되고 `ERRORS: none`이 출력됨 (이것은 의도대로). 에러가 있으면 `ERRORS:` + 에러 목록 + `ERRORS: none`이 모두 출력됨 (버그)
- **현재 로직**:
  ```
  if errors:           # 에러가 있으면 "ERRORS:" 헤더 추가
      lines.append("ERRORS:")
  for error in errors: # 에러 목록 추가 (errors가 None이면 TypeError 위험)
      lines.append(f"- {error}")
  lines.append("ERRORS: none")  # 무조건 추가 ← 버그
  ```
- **수정 방향**: if/else 구조로 변경. 에러가 있으면 `ERRORS:` + 목록, 없으면 `ERRORS: none`. `errors` 파라미터가 None일 수 있으므로 `errors or []` 방어 필요
- **참고**: `_format_llm_history`(line 394-401)는 동일 패턴이 if/else로 올바르게 구현되어 있음. `_format_llm_deployment`만 수정 필요

### Bug 4: LLM 포맷에 이모지 포함

- **위치**: `sbkube/utils/output_formatter.py:173-176` (`_format_llm_deployment`), `222-231` (`_format_llm_history`)
- **증상**: LLM 포맷 출력에 `✅`, `❌`, `⚠️`, `🔄`, `⏳`, `↩️` 이모지가 포함
- **문제**: LLM은 이모지를 토큰으로 소비하며, 구조화된 파싱에 방해. `OutputManager.print()`에서 emoji 파라미터를 "human 모드에서만 사용"이라고 명시(line 107)했으나, formatter 레벨에서는 여전히 이모지 삽입
- **수정 방향**: LLM 포맷에서는 이모지 대신 텍스트 상태 표기 사용 (`SUCCESS`, `FAILED`, `WARNING` 등)
- **범위 주의**: `_format_llm_deployment`(line 173-176)의 직접 이모지 + `_format_llm_history`의 `icon_for_state()`(line 222-231) 및 이를 사용하는 line 274, 283, 300, 305 모두 수정 대상

### Bug 5: 프로그레스바 텍스트 출력 혼입 (경미, Bug 1 수정 후 자동 해결 예상)

- **증상**: 터미널 프로그레스바 렌더링 문자가 텍스트에 섞임 (`⠙ 📦 Prepare coredns ━━━...`)
- **원인**: Bug 1(format_type 미전파)이 해결되면 대부분 해결됨. `apply.py:400`에서 이미 `output.format_type != "human"` 체크 존재
- **확인 필요**: deploy 명령의 프로그레스 트래커도 동일하게 format_type 체크하는지 확인 (deploy.py:1351에서 확인됨 — 이미 체크 존재)
- **수정 방향**: Bug 1 수정 후 자동 해결 예상. 수정 후 실제 테스트로 확인

### Bug 6: apply.py의 Rich markup + 이모지 직접 하드코딩 (18건+)

- **위치**: `sbkube/commands/apply.py` 전역 (line 152, 279, 410, 437, 441, 893, 896, 1003, 1077, 1123, 1129, 1189, 1360, 1398, 1402, 1582, 1595 등)
- **증상**: `output.print("[bold blue]✨ SBKube apply 시작 ✨[/bold blue]")` 식으로 Rich markup과 이모지가 직접 포함되어 있어, Bug 1 수정 후에도 LLM 출력에 `[bold blue]`, `[yellow]` 등의 markup 태그와 이모지가 노출
- **원인**: 표현(presentation)과 로직(logic)이 분리되지 않고, 각 command에서 Rich markup을 직접 사용
- **수정 방향**: 두 가지 접근 가능
  - (A) `OutputManager.print()`에서 `format_type != "human"`일 때 Rich markup을 자동 strip + 이모지 제거 (영향 범위 최소)
  - (B) `output.print()`에 `plain_text` 파라미터를 추가하여 LLM 모드용 대체 텍스트 전달 (더 깨끗하지만 수정 범위 큼)
- **권장**: (A) 방식으로 `OutputManager` 레벨에서 일괄 처리. 향후 (B)로 점진 리팩토링

## 수정 순서

1. **Bug 1** (format_type 전파) → 근본 원인이므로 최우선
2. **Bug 2** (SourceScheme 파싱) → 경고 메시지 제거
3. **Bug 3** (에러 출력 로직) → 간단한 로직 수정
4. **Bug 4** (이모지 제거) → LLM 토큰 효율화
5. **Bug 5** (프로그레스바) → Bug 1 수정 후 검증
6. **Bug 6** (Rich markup strip) → OutputManager 레벨 일괄 처리

## 테스트 방법

```bash
# 수정 전후 출력 비교
sbkube apply --format llm -f sbkube.yaml

# 각 phase 개별 테스트
sbkube prepare --format llm -f sbkube.yaml
sbkube build --format llm -f sbkube.yaml
sbkube deploy --format llm -f sbkube.yaml

# 유닛 테스트
make test-quick
```

## 수락 기준

- [ ] `--format llm` 지정 시 human 포맷이 아닌 구조화된 텍스트 출력
- [ ] "Extra inputs are not permitted" 경고 미출력
- [ ] 에러 유/무에 따른 정확한 ERRORS 섹션 출력 (`errors=None` 시 TypeError 미발생)
- [ ] LLM 포맷에 이모지 미포함 (formatter + history icon_for_state 포함)
- [ ] 프로그레스바 문자 미포함
- [ ] LLM 포맷에 Rich markup 태그(`[bold ...]`, `[yellow]` 등) 미포함
- [ ] 기존 human/json/yaml 포맷 동작 미영향
