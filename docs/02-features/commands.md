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

상태 DB(`~/.sbkube/deployments.db`)에 기록된 배포를 이전 Helm revision으로 되돌린다.
`deploy`·`apply`가 Helm 앱을 성공적으로 배포할 때마다 롤백 지점(chart, chart version,
values digest, Helm revision, 앱 설정 저장소의 source commit)을 기록한다.

```bash
sbkube rollback --list --cluster production          # 롤백 지점 목록
sbkube rollback <deployment-id> --app grafana        # 앱 하나 롤백
sbkube rollback <deployment-id> --scope all --dry-run  # 비교만 출력
sbkube rollback <deployment-id> --scope all --confirm-digest 3f9a0c1d2e4b
```

**클러스터**: `helm`·`kubectl`은 현재 kube context가 아니라 배포 기록에 저장된
`kubeconfig`·`kubeconfig_context`(배포 때 실제로 쓴 값)로 실행한다. 전역 `sbkube
--kubeconfig <path> --context <name> rollback ...`은 context 이름과 그 context의 API server가
기록과 같을 때만 대신 쓰이고 다르면 거부한다. 클러스터 기록이 없는 배포는 두 옵션이 필요하다. `--scope phase`가 앱을 하나도 찾지 못하면 전체 롤백 대신 거부한다.

**되돌리는 대상**: 롤백은 항상 기록된 Helm revision - 1로 되돌린다. `--target`은 되돌릴
상태와 비교할 기록을 고르는 기준일 뿐이며, 그 기록의 revision이 revision - 1이 아니면
명령을 거부한다.

**코드 변경 확인**: 실행 전에 현재 배포와 되돌릴 상태의 chart, chart version, values
digest, source commit을 앱마다 비교한다. 되돌릴 상태는 같은 release·namespace의
revision - 1 기록이다.

- 모두 같으면 확인 없이 진행한다.
- 하나라도 다르거나 비교할 수 없으면 차이 요약과 12자리 difference digest를 출력하고,
  대화형 터미널에서 그 digest를 입력해야 진행한다. 비교할 수 없는 경우: 기록 없음, source
  commit 없음, 커밋되지 않은 변경(무시되지 않은 untracked 파일 포함)으로 배포됨, 지정한
  배포가 그 release의 최신 기록이 아님, `helm status`의 live revision이 기록과 다르거나
  읽을 수 없음, `--target`에 같은 release·namespace 기록이 없음.
- digest 입력은 요약을 읽었다는 증거일 뿐 사람의 승인이 아니다. 승인은 두 번째 방어선인
  deploy gate가 맡는다.
- 터미널이 아니면 `--confirm-digest <digest>`로만 진행한다. 틀린 digest·빈 입력·비대화형
  실행은 0이 아닌 종료 코드로 거부한다. `--force`는 이 확인을 건너뛰지 않는다.
- `--dry-run`은 비교와 digest만 보여 주고 확인을 묻지 않는다. 비교를 위해 `helm status`로
  클러스터를 읽기 전용으로 조회한다(`helm status`는 60초 제한). 클러스터에 접근할 수 없으면
  dry-run은 live revision을 "could not be read"로 표시할 뿐 확인을 묻지 않고, 실제 롤백을
  실행할 때 확인을 요구한다.
- helm이 계속 실패하는 동안 digest는 시간이 지나도 바뀌지 않는다. 이때 digest를 입력하면
  알 수 없는 live 상태를 받아들이는 것이다.
- `git status`는 앱 디렉토리가 아니라 저장소 전체를 검사한다. 저장소 어디에든 무시되지 않은
  untracked 파일이 있으면 배포가 `-dirty`로 기록된다. sbkube 작업 디렉토리(예: `.sbkube/`)를
  `.gitignore`에 넣지 않으면 모든 롤백이 확인을 요구한다.
- 롤백 지점 기록이 실패하면(상태 DB 쓰기 오류) 배포는 성공으로 두고 경고만 출력한다.
  그 배포로는 비교할 수 없으므로 이후 롤백은 확인을 요구한다.

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
- 허용은 세션 프로세스의 하위 트리 전체(그 세션의 subagent·백그라운드 작업·훅 포함)에 적용된다.
  `unlimited`는 같은 프로세스 안에서 새 대화를 시작해도 이어진다.
- 취소 명령은 없다. 끊으려면 전역 파일에서 `agent_grant`를 빼거나(모든 허용이 꺼짐) TTL을 기다린다.
- Linux에서 시스템 시계가 크게 조정되면 `ps`의 시작 시각이 달라져 기존 허용이 더 이상 맞지 않을 수
  있다. 이때는 다시 허용한다.

**위협 모델**: 이 허용은 에이전트의 실수로 게이트를 지나치는 일을 막기 위한 것이지, 적대적인
에이전트를 막지 못한다. 같은 사용자 권한의 프로세스는 상태 DB(`~/.sbkube/deployments.db`)에 허용
행을 직접 쓰거나, 가상 터미널과 분리된 프로세스로 `gate grant`를 실행할 수 있다. TTY 검사는 사람임을
증명하지 않는다. 에이전트가 이 DB와 명령에 손대지 못하게 하는 것은 에이전트 실행 환경(권한 훅 등)의
몫이다.

### access verify — 읽기 전용 자격증명 확인

에이전트에게 줄 읽기 전용 kubeconfig(`settings.access.readonly.kubeconfig`)가 기대한 권한만 갖는지
`kubectl auth can-i`로 확인합니다. 클러스터를 바꾸지 않으므로 deploy gate 대상이 아닙니다
([config-schema.md](../03-configuration/config-schema.md#access-에이전트-접근-경계)).

```bash
sbkube access verify
sbkube access verify -f sbkube.yaml
```

- 먼저 클러스터 없이 검사한다: 읽기 전용 kubeconfig 파일이 있고, `settings.kubeconfig_context`
  (전역 `--context`가 우선)가 들어 있으며, 그 context의 API server가 관리자 kubeconfig
  (`settings.kubeconfig`, 전역 `--kubeconfig`가 우선)의 같은 context와 같아야 한다. 어긋나면
  `kubectl`을 부르지 않고 실패한다.
- 클러스터 범위(`-A`) 기대값: `get`·`list`·`watch secrets` 거부, `list pods`·`list nodes`·
  `list customresourcedefinitions` 허용, `create deployments`·`delete pods` 거부,
  `create serviceaccounts --subresource=token -n <access.namespace>` 거부(토큰 발급 불가).
  `extra_rules`의 verb × resource는 모두 허용이어야 한다(`apiGroups`가 있으면 `resource.group` 형식).
  `resourceNames`가 있는 대상(`resource/name`)도 같은 이유로 `-A`로 묻는다. `extra_rules`는 클러스터
  범위 읽기 규칙이기 때문이다.
- 네임스페이스별 검사: `-A`는 네임스페이스를 비운 채 묻기 때문에 ClusterRoleBinding만 평가한다. 한 네임스페이스에
  묶인 RoleBinding은 보이지 않으므로, 거부해야 하는 항목(`get`·`list`·`watch secrets`, `create deployments`,
  `delete pods`)을 읽기 전용 자격증명이 `kubectl get namespaces -o name`으로 찾은 모든 네임스페이스(그리고
  `access.namespace`)에 `-n <ns>`로 다시 묻는다. 동시에 최대 8개씩 실행하며 결과 순서는 고정이다. 통과하면
  항목당 한 줄(`all N namespaces`)로 보이고, 실패하면 허용된 네임스페이스를 앞 10개와 나머지 개수로 적는다.
  네임스페이스 목록을 얻지 못하면 건너뛰지 않고 `ERROR`다.
- 남는 한계: 검사는 실행 시점에 있는 네임스페이스만 본다. 그 뒤에 만든 네임스페이스나 RoleBinding은 다시 실행할
  때까지 확인되지 않는다(주기적으로 돌리거나 변경 직후에 돌린다).
- `kubectl`의 `no`와 오류를 구분한다. 연결 실패·`Unauthorized`·토큰 만료·`kubectl` 없음·시간 초과는
  `ERROR`로 표시하고 `no`로 세지 않는다. TLS 오류(`x509:`, `certificate signed by`, `certificate has expired`)도
  오류이고, `resource type 'certificates'` 같은 일반 경고는 오류가 아니다.
- 결과는 check / expected / actual / result 표로 출력한다. 모두 맞을 때만 종료 코드 0이다.
- 토큰·인증서·키 값은 읽어 출력하지 않는다.

### access audit — 관리자 자격증명 경로 점검

관리자 수준 자격증명이 닿는 경로를 클러스터 호출 없이 보고합니다. `sbkube.yaml`이 없어도 동작합니다
(그 경우 설정 검사는 건너뜀).

```bash
sbkube access audit
sbkube access audit --strict
```

- 대상: `KUBECONFIG`의 각 파일(없으면 `~/.kube/config`), `settings.kubeconfig`,
  `settings.access.readonly.kubeconfig`.
- 사용자를 자격증명 종류로 분류하고 참조하는 context를 보인다: 클라이언트 인증서 =
  `client-cert (admin-like)`, `token`/`tokenFile` = `token`, `exec`/`auth-provider` = `exec`.
  이름·경로·종류만 출력한다.
- 발견 사항: `KUBECONFIG`가 client-cert 사용자에 닿음, `access`가 설정됐는데 `settings.kubeconfig`가
  client-cert 사용자를 씀(에이전트가 관리자로 돎), 읽기 전용 kubeconfig에 client-cert 사용자가 있음.
- 읽을 수 없거나 YAML이 깨진 파일은 보고만 하고 계속한다.
- 발견 사항이 있어도 종료 코드는 0이다. `--strict`면 하나라도 있을 때 1이다.

### access issue — 배포 토큰 발급과 deployer kubeconfig 생성

관리자 자격증명으로 deployer ServiceAccount의 짧은 수명 토큰을 발급하고, 그 토큰만 쓰는 kubeconfig를
만듭니다. **사람만 실행할 수 있습니다**: stdin과 stderr가 모두 TTY여야 하며(`gate grant`와 같은 검사),
에이전트의 비대화형 실행은 거부됩니다.

```bash
sbkube access issue
sbkube access issue --ttl 30m -f sbkube.yaml
```

- 관리자 kubeconfig·context는 전역 `--kubeconfig`/`--context`, 없으면 `settings.kubeconfig`/
  `kubeconfig_context`다. `settings.access`와 `access.deployer.kubeconfig`가 필요하다.
  `access.admin.ssh_host`가 있으면 아래 노드 실행 경로를 쓰고 로컬 관리자 파일은 요구하지 않는다.
  deployer kubeconfig와 토큰 파일은 관리자·읽기 전용 kubeconfig, 그리고 그 사용자들이 참조하는 `tokenFile`·
  `client-certificate`·`client-key`·클러스터 `certificate-authority` 파일(상대 경로는 해당 kubeconfig 기준,
  `~`도 문자 그대로 상대 경로로 처리, 심링크·하드링크 포함)과 같으면
  거부하고, 서로 같아도 거부한다. 존재하는 읽기 전용 kubeconfig를 읽을 수 없으면 건너뛰지 않고 거부한다.
  모든 거부는 kubectl 호출 전에 일어난다.
- `--ttl`은 `deployer.token_ttl`을 덮어쓴다(같은 파서, 최소 `10m`). 값은 그대로 kubectl `--duration`에 간다.
- 실행: `kubectl create token <deployer.service_account> -n <access.namespace> --duration <ttl>`.
  토큰은 메모리와 토큰 파일에만 있고, 출력·로그·예외·argv·환경 변수에는 나오지 않는다. 실패하면 kubectl
  stderr 첫 줄만 보이고 아무 파일도 쓰지 않는다.
- 쓰는 파일:
  - `<access.token_dir>/deploy.token` (0600). 디렉토리는 없으면 0700으로 만든다. 이미 있는 디렉토리는
    chmod하지 않는다: 내가 소유한 디렉토리이고 group/other 권한이 없어야 하며, 아니면 `chmod 700`하거나
    전용 디렉토리를 쓰라는 안내와 함께 거부한다. 토큰 발급 전에 두 파일의 위치가 쓸 수 있는지 미리 확인하며,
    토큰을 쓴 뒤 kubeconfig 쓰기가 실패하면 토큰은 썼고 kubeconfig는 못 썼다고 알린다.
  - `access.deployer.kubeconfig` (0600): 관리자 cluster의 `server`, CA, `tls-server-name`, `proxy-url`,
    `insecure-skip-tls-verify`를 복사하고 context 하나, 사용자 `deploy`(절대 경로 `tokenFile`)만 담는다.
    관리자 사용자 자격증명은 복사하지 않는다.
  - 둘 다 같은 디렉토리의 임시 파일(O_EXCL, 0600)에 쓰고 fsync 후 `os.replace`하므로 실패해도 기존 파일이 남는다.
- 덮어쓰기 규칙: deployer kubeconfig가 이미 있으면 생성물 형태일 때만 덮어쓴다. 사용자가 정확히 하나이고
  이름이 `deploy`이며 키가 `tokenFile` 하나뿐이고 그 경로가 이번 토큰 파일과 같은 파일이어야 한다(예전 수동
  인계 형태 `~/.kube/agent-access/deploy.token`도 같은 경로면 허용). 그 외(client-cert, token, exec,
  auth-provider, 다른 경로, 파싱 불가)는 거부한다.
- 쓴 뒤 `kubectl auth can-i create deployments.apps -A`를 deployer kubeconfig로 실행한다. `yes`만 성공이며
  `no`나 오류(연결, 만료, TLS)면 안내와 함께 종료 코드 1이다.
- 출력: 쓴 경로, 만료 시각(로컬·UTC; 요청한 값이며 API server가 `--service-account-max-token-expiration`으로 줄일 수 있음), can-i 결과, 토큰이 만료된다는 안내. 토큰 값은 출력하지 않는다.
- 토큰은 만료되며 갱신은 `issue`를 다시 실행하는 것이다. 만료 후 deployer kubeconfig는 `Unauthorized`가 된다.
- `audit`·`verify`·`issue`는 RBAC을 바꾸지 않는다. `init`·`revoke`는 아래와 같이 별도로 배포 게이트를 거친다.

#### 노드 전용 관리자 경로

`access.admin.ssh_host`와 `expected_hostname`을 함께 설정하면 사람의 SSH 접근으로 노드의
`sudo -n k3s kubectl --kubeconfig /etc/rancher/k3s/k3s.yaml`을 실행한다. 로컬 관리자 kubeconfig를
복사하거나 다운로드하지 않는다. `access.readonly.kubeconfig`에 해당 context와 서버 CA가 있어야 하며,
deployer kubeconfig의 server·CA는 이 읽기 전용 파일에서 가져온다.

- 호스트는 기존 SSH alias 또는 `user@host`다. 운영자가 소유한 SSH 설정에서 직접 LAN 경로와 프록시 경로를
  선택하고, 실행 전에 실제 목적지와 호스트 키를 확인한다. sbkube는 라우팅을 재작성하지 않는다.
- SSH는 TTY 없이 BatchMode와 StrictHostKeyChecking을 켠다. 기존 known_hosts와 비대화형 `sudo -n` 권한이
  필요하며, 인증 대화나 자동 호스트 키 등록은 하지 않는다.
- agent 파일의 API URL이 HTTPS인지 확인한다. 먼저 `hostname`이 `expected_hostname`과 같은지 확인하고, 노드 관리자 kubeconfig에서 공개 서버 CA만
  읽어 agent 파일의 CA와 대조한다. hostname·CA가 다르거나 TLS 검증이 꺼져 있으면 발급 전에 중단한다.
- 그다음 노드에서 TokenRequest를 실행해 토큰만 받아 로컬 0600 파일에 쓴다. SSH 실패 시 원격 stdout·stderr를
  노출하지 않고 종료 코드와 점검할 항목을 알린다. 발급 후 deployer 권한 검사는 기존과 같다.
- 이 경로는 자격증명을 자동 격리하지 않는다. 같은 uid의 에이전트도 관리자 SSH 권한을 사용할 수 있으면
  관리자 접근은 여전히 가능하다. 관리자 SSH 인증의 잠금 해제·권한 관리는 운영자의 책임이다.

K3s 관리자 파일과 내장 kubectl 동작은 [K3s CLI 문서](https://docs.k3s.io/cli)를 따른다.

### access init — RBAC과 kubeconfig 초기화

`sbkube access init --print -f sbkube.yaml`은 내장 매니페스트 8개만 YAML로 출력한다. TTY나 관리자
파일을 요구하지 않고, 클러스터에 접속하거나 로컬 자격증명 파일을 쓰지 않는다.

`--print` 없이 실행하면 사람용 TTY 검사와 `access-init` 배포 게이트를 통과해야 한다.
노드 실행 설정이 있으면 기존 SSH hostname·서버 CA 검사를 사용하고, 없으면 로컬 관리자 kubeconfig를 쓴다.
읽기 전용·deployer kubeconfig 경로와 context, HTTPS 서버 CA를 모두 준비해야 한다.

- 템플릿은 Namespace, readonly SA·토큰 Secret·view 바인딩·클러스터 읽기 Role와 바인딩,
  deployer SA·cluster-admin 바인딩이다. 기본 이름은 기존 polypia 리소스와 같고 `kubectl apply`로 재적용한다.
- `readonly.extra_rules`는 읽기 동사 `get`·`list`·`watch`만 허용한다. Secret·Secret 하위 리소스와
  와일드카드 리소스는 거부한다. readonly와 deployer의 ServiceAccount 이름은 달라야 한다.
- 기존 readonly Secret은 타입·이름·namespace·ServiceAccount annotation이 맞아야 한다. 다른 Secret을
  인수하거나 소유자를 바꾸지 않는다. 컨트롤러가 토큰을 채울 때까지 제한된 시간 동안 기다린다.
- `<token_dir>/readonly.token`과 readonly kubeconfig를 0600으로 쓴다. readonly 사용자는 `tokenFile`만 참조한다.
  deployer kubeconfig도 만들지만 **배포 토큰은 발급하지 않는다**. 단기 토큰은 사람이 `access issue`로 발급한다.
- kubeconfig·토큰 파일 네 경로는 서로 달라야 한다. 관리자 자격증명·CA 파일과의 충돌도 발급·적용 전에 거부한다.
  디렉토리 권한·원자적 쓰기는 `issue`와 같은 규칙이다. 기존 deployer 토큰 파일은 변경하지 않는다.
- 기존 생성물 형태의 파일만 갱신한다. 수동 kubeconfig(특히 inline token·인증서)는 보존하고 오류로 중단한다.
  기존 polypia 수동 파일을 유지하려면 먼저 `--print`로 RBAC을 검토하고, 파일 전환은 별도 경로로 준비한다.
- 노드에서 처음 초기화할 때는 readonly 경로에 신뢰한 server·CA와 해당 context 하나를 가진 공개 bootstrap
  kubeconfig(`users: []`)를 미리 둘 수 있다. 이 파일만 생성된 readonly kubeconfig로 전환한다.
- 일부 RBAC 적용이나 파일 쓰기 뒤에 실패하면 진행 상태를 오류에 남긴다. 성공 후 `access verify`로 실제
  읽기 권한과 Secret·쓰기 거부를 확인한다. 기본 `view`나 기존 클러스터 정책의 변경까지 자동 검증한 것은 아니다.

### access revoke — 자격증명 회수

`sbkube access revoke --profile readonly|deployer|all -f sbkube.yaml`에서 프로필은 필수다.
실제 실행은 사람용 TTY 검사와 `access-revoke` 배포 게이트를 거치며, 초기화와 같은 관리자 경로를 쓴다.

- `readonly`: 소유자가 일치하는 `<readonly.service_account>-token` Secret만 삭제한다.
- `deployer`: ServiceAccount를 삭제하고 새 UID로 재생성한다. 기존 labels·annotations·imagePullSecrets는
  보존하고, 이전 UID·resourceVersion·자동 생성된 Secret 참조는 가져오지 않는다. RoleBinding은 유지한다.
- `all`: readonly 회수 후 deployer를 회수한다. 중간에 실패하면 완료한 단계와 재생성 실패 여부를 알린다.
- 로컬 파일은 삭제하지 않는다. readonly 복구는 `init`, deployer 갱신은 `issue`로 한다.
  Secret 삭제는 그 Secret의 장기 토큰을, SA 재생성은 해당 SA의 기존 토큰을 회수한다. 캐시가 있는 검증자는
  무효화를 즉시 반영하지 않을 수 있다. 다른 이름의 readonly 토큰 Secret은 이 명령의 대상이 아니다.

토큰 생성·회수 방식은 [Kubernetes ServiceAccount 관리 문서](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/)를 따른다.

### 명령별 자격증명 자동 선택

루트 `settings.access.auto_profile`의 기본값은 `true`다. 설정이 없거나 `false`이면 기존 CLI·설정의
kubeconfig 해석을 유지한다. 켜져 있으면 다음 자격증명을 선택하고, 누락·만료 시 관리자 파일로 돌아가지 않는다.

| 명령 | 선택 |
| --- | --- |
| `apply`, `deploy`, `delete`, `upgrade` | deployer (`--dry-run`도 동일) |
| `rollback` | 기록된 앱 디렉토리의 설정에서 deployer 선택 후 기록된 클러스터와 대조 |
| `status` | readonly; unified 설정으로 조회하고 관리자 모드와 분리된 캐시 사용 |
| `history`, `rollback --list` | 로컬 기록만 조회하므로 프로파일 토큰을 요구하지 않음 |

- `.sbkube-workspace`는 설정 탐색의 경계이며 앵커만 정의할 수도 있다. 대상 파일에서 이 경계까지의
  실제 `sbkube.yaml`/`sbkube.yml` 상위 문서 중 가장 바깥 문서가 해당 클러스터 설정의 소유자다.
  따라서 infra-ops처럼 저장소 루트에는 앵커만 있고 환경별 `ph4_kube/sbkube.yaml`이 있는 구조도 지원한다.
  표식이 없으면 기존 `TARGET`·`-f` 해석 결과의 문서를 루트로 삼고, 별도의 상위 설정 병합은 하지 않는다.
- 하위 phase·앱의 `access`는 루트 선택을 덮어쓰지 않는다. 다른 `context`나 클러스터를 선언한 하위 설정은
  훅·prune 실행 전에 거부한다. 한 자동 프로파일 범위는 한 클러스터를 대상으로 한다.
- CLI의 `--kubeconfig`·`--context`가 선택된 프로파일과 충돌하면 오류다. 수동으로 다른 자격증명을 쓰려면
  해당 루트의 `auto_profile`을 명시적으로 끈다. `KUBECONFIG` 환경 변수나 사용자 기본 파일은 대체 경로가 아니다.
- 선택한 kubeconfig는 HTTPS·서버 CA를 제공해야 한다. readonly와 deployer는 context·API URL·CA 지문이 같아야
  한다. 사용자 인증은 토큰 또는 tokenFile만 허용하고 관리자 인증서·exec 플러그인은 거부한다.
- 토큰의 ServiceAccount 주체와 만료 시각을 로컬에서 확인한다. deployer는 만료 시각이 있는 단기 토큰이어야
  하며 갱신 안내는 `access issue`다. readonly의 장기 토큰은 만료 항목이 없어도 되며 복구 안내는 `access init`이다.
  이 사전 검사는 서명·audience·서버의 회수 상태까지 인증하는 것이 아니며 실제 API 서버가 최종 판정한다.
- 병렬 앱 실행에서도 선택을 유지하고 완료·실패 후에는 호출 전 선택으로 복원한다. `apply --prune-disabled`의
  Helm·YAML 삭제도 동일 프로파일을 사용한다. 임의의 exec 명령·셸 훅 문자열은 재작성하지 않으므로,
  그 안에 직접 적은 관리자 경로나 외부 프로그램의 자격증명은 작성자가 별도로 전환해야 한다.

자동 선택으로 배포한 새 기록에는 context·API URL·공개 서버 CA의 SHA-256을 저장한다(토큰·개인키 제외).
rollback은 선택한 deployer의 식별 정보가 이 기록과 일치해야 하므로 이전 관리자 파일이 없어도 검증할 수 있다.
기존 지문 없는 기록은 이전 kubeconfig의 공개 클러스터 정보로 비교하는 동작을 유지하며, 그 파일까지 없으면
대상을 증명할 수 없어 거부한다. 기존 기록을 자동으로 수정하거나 검사를 건너뛰지 않는다.

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
