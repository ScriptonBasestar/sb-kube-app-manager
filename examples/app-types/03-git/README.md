# App Type: Git

Git 리포지토리에서 Helm 차트나 매니페스트를 가져오는 예제입니다.

## 사용 시나리오

- Private Git 리포지토리의 차트
- 버전 관리되는 커스텀 차트
- 팀 내부 공유 차트

## 예제: Git 리포지토리에서 차트 가져오기

### sbkube.yaml
```yaml
namespace: git-demo

apps:
  # 1. Git 리포지토리 클론
  chart-source:
    type: git
    repo: my-charts
    path: charts/myapp

  # 2. 클론된 차트 배포
  myapp:
    type: helm
    chart: ./repos/my-charts/charts/myapp
    values:
      - myapp-values.yaml
    depends_on:
      - chart-source
```

### sbkube.yaml
```yaml
git_repos:
  my-charts:
    url: https://github.com/your-org/helm-charts.git
    branch: main
    # 인증이 필요한 경우 (SSH 키 사용)
    # auth:
    #   type: ssh
    #   private_key_path: ~/.ssh/id_rsa
```

## Private 리포지토리 인증

### SSH 키 사용
```yaml
git_repos:
  my-private-charts:
    url: git@github.com:your-org/private-charts.git
    branch: main
    auth:
      type: ssh
      private_key_path: ~/.ssh/id_rsa
```

### Personal Access Token 사용
```yaml
git_repos:
  my-private-charts:
    url: https://github.com/your-org/private-charts.git
    branch: main
    auth:
      type: token
      token: ghp_YourPersonalAccessToken
```

## 실행

```bash
# prepare 단계에서 Git 리포지토리 클론
sbkube prepare -f sbkube.yaml

# 클론된 리포지토리 확인
ls -la repos/my-charts/

# 전체 워크플로우 실행
sbkube apply -f sbkube.yaml
```

## 정리

```bash
sbkube delete -f sbkube.yaml

# 클론된 리포지토리도 삭제 (선택사항)
rm -rf repos/
```

## 주의사항

- Git 인증 정보는 안전하게 관리하세요 (Kubernetes Secret 활용 권장)
- `depends_on`을 사용하여 Git 클론 후 차트 배포 순서 보장
- 네트워크 연결 필요 (리포지토리 접근)
