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

---

## Core Workflow Commands

### ⭐ apply — 통합 배포

가장 많이 사용하는 명령어. `prepare → build → template → deploy`를 순차 실행합니다.

```bash
# 기본 사용 (현재 디렉토리의 sbkube.yaml 자동 탐지)
sbkube apply

# 설정 파일 지정
sbkube apply -f sbkube.yaml

# Dry-run
sbkube apply -f sbkube.yaml --dry-run

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
sbkube prepare -f sbkube.yaml
sbkube prepare -f sbkube.yaml --app grafana
```

### build — 차트 빌드

Overrides/Removes를 적용하여 배포 가능한 차트를 생성합니다.

```bash
sbkube build -f sbkube.yaml
sbkube build -f sbkube.yaml --app grafana
```

### template — 템플릿 렌더링

Helm template을 실행하여 최종 YAML을 생성합니다.

```bash
sbkube template -f sbkube.yaml
sbkube template -f sbkube.yaml --app grafana --output-dir rendered/
```

### deploy — 배포 실행

빌드된 차트/매니페스트를 클러스터에 배포합니다.

```bash
sbkube deploy -f sbkube.yaml
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
sbkube apply -f sbkube.yaml
```

### 단계별 디버깅

```bash
sbkube validate -f sbkube.yaml     # 1. 설정 검증
sbkube prepare -f sbkube.yaml      # 2. 소스 준비
sbkube build -f sbkube.yaml        # 3. 차트 빌드
sbkube template -f sbkube.yaml     # 4. 렌더링 확인
sbkube deploy -f sbkube.yaml --dry-run  # 5. Dry-run
sbkube deploy -f sbkube.yaml       # 6. 실제 배포
```

### 특정 앱만 재배포

```bash
sbkube apply -f sbkube.yaml --app grafana --skip-prepare
```

### Multi-Phase 배포

```bash
# 전체 Phase 순서대로
sbkube apply -f sbkube.yaml

# 특정 Phase만
sbkube apply -f sbkube.yaml --phase p1-infra
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
