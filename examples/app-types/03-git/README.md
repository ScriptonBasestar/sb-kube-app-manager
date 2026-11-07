# App Type: Git

Git 리포지토리의 Helm 차트를 가져오는 예제입니다. 제공된 `sbkube.yaml`의
저장소 URL과 차트 하위 경로를 실제 값으로 바꿔 사용하세요.

```yaml
apiVersion: sbkube/v1
settings:
  namespace: git-demo
  git_repos:
    my-charts:
      url: https://github.com/your-org/helm-charts.git
      branch: main
apps:
  chart-source:
    type: git
    repo: my-charts
    # 재현 가능한 배포에는 ref에 전체 커밋 SHA를 지정하세요.
  myapp:
    type: helm
    chart: ${repos.chart-source}/charts/myapp
    depends_on: [chart-source]
```

`prepare`는 `.sbkube/repos/chart-source`에 앱별 checkout을 준비합니다.
버전 선택은 `ref` → 앱의 명시적 `branch` → 별칭의 `branch` → `main` 순서입니다.
Git 앱의 `path`는 하위 디렉터리를 복사하지 않습니다. Helm 앱의 `chart`에서
`${repos.<Git 앱 이름>}/<차트 경로>`를 명시하세요.

```bash
sbkube prepare -f sbkube.yaml
sbkube build -f sbkube.yaml
sbkube template -f sbkube.yaml
```

위 명령은 차트 준비·빌드·렌더링 단계입니다. 실제 배포는 별도의 배포 권한과
프로젝트 게이트를 충족한 후 수행하세요. 인증은 Git 자체의 SSH 설정이나
credential helper를 사용하며 YAML에 토큰을 넣지 마세요.

기존 별칭 이름 캐시는 자동으로 지우지 않습니다. 알 수 없거나 수정된 캐시,
출처가 다른 build는 오류로 남깁니다. 자세한 보존·입력 제한은
[설정 스키마](../../../docs/03-configuration/config-schema.md#git--git-리포지토리)를 참고하세요.
