# SBKube v0.3.0 Examples

이 디렉토리에는 SBKube v0.3.0의 다양한 사용 사례를 보여주는 예제들이 있습니다.

## 📁 디렉토리 구조

```
examples/
├── README.md                    # 이 파일
├── v3-overrides/               # 차트 커스터마이징 예제 (overrides/removes)
├── complete-workflow/          # 전체 워크플로우 예제
├── k3scode/                    # k3s 코드 서버 스택
│   ├── memory/                 # Redis, Memcached
│   ├── rdb/                    # PostgreSQL, MariaDB
│   ├── ai/                     # AI/ML tools
│   └── devops/                 # DevOps tools
└── deploy/                     # 배포 타입별 예제
    ├── exec/                   # 커스텀 명령어 실행
    ├── install-action/         # 커스텀 액션
    └── yaml/           # YAML 매니페스트
```

## 🚀 빠른 시작

### 1. 기본 사용 (Helm 차트)

```bash
cd examples/k3scode/memory
sbkube apply
```

**설정 파일** (`config.yaml`):
```yaml
namespace: data

apps:
  redis:
    type: helm
    chart: bitnami/redis
    values:
      - redis.yaml

  memcached:
    type: helm
    chart: bitnami/memcached
    values:
      - memcached.yaml
```

### 2. 차트 커스터마이징 (Overrides & Removes)

```bash
cd examples/v3-overrides
sbkube apply
```

**더 많은 예제와 상세 설명은 각 디렉토리의 README.md를 참조하세요.**

## 📚 예제 카탈로그

| 예제 | 설명 | 주요 기능 |
|------|------|----------|
| [v3-overrides](v3-overrides/) | 차트 커스터마이징 | overrides, removes |
| [complete-workflow](complete-workflow/) | 전체 워크플로우 | 모든 앱 타입, 의존성 |
| [k3scode/memory](k3scode/memory/) | 메모리 저장소 | Redis, Memcached |
| [k3scode/rdb](k3scode/rdb/) | 관계형 DB | PostgreSQL, MariaDB |
| [k3scode/ai](k3scode/ai/) | AI/ML 도구 | Git 리포지토리 |
| [k3scode/devops](k3scode/devops/) | DevOps 도구 | 로컬 차트 |
| [deploy/exec](deploy/exec/) | 커스텀 명령어 | exec 타입 |
| [deploy/install-action](deploy/install-action/) | 커스텀 액션 | action 타입 |
| [deploy/yaml](deploy/yaml/) | YAML 매니페스트 | yaml 타입 |

## 🔧 앱 타입별 예제

### Helm (Remote)
```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2
    values:
      - redis.yaml
```

### Helm (Local)
```yaml
apps:
  my-app:
    type: helm
    chart: ./charts/my-app
    values:
      - values.yaml
```

### YAML
```yaml
apps:
  nginx:
    type: yaml
    files:
      - deployment.yaml
      - service.yaml
```

### Git
```yaml
apps:
  source:
    type: git
    repo: my-repo
    path: charts/app
```

### HTTP
```yaml
apps:
  manifest:
    type: http
    url: https://example.com/manifest.yaml
    dest: downloaded.yaml
```

### Action
```yaml
apps:
  setup:
    type: action
    actions:
      - type: apply
        path: crd.yaml
```

### Exec
```yaml
apps:
  check:
    type: exec
    commands:
      - kubectl get pods
```

## 🆕 v0.2.x에서 마이그레이션

```bash
# 자동 마이그레이션
sbkube migrate old-config.yaml -o config.yaml
```

자세한 내용은 [Migration Guide](../docs/MIGRATION_V3.md)를 참조하세요.

## 📚 추가 자료

- [SBKube Documentation](../docs/)
- [Chart Customization Guide](../docs/03-configuration/chart-customization.md)
- [Configuration Schema](../docs/03-configuration/config-schema.md)
- [CHANGELOG](../CHANGELOG_V3.0.0.md)

---

**Happy deploying with SBKube v0.3.0! 🚀**
