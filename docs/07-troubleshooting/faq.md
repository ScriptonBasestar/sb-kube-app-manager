______________________________________________________________________

## type: FAQ audience: End User topics: [faq, common-questions, quick-answers] llm_priority: medium last_updated: 2025-01-04

# 자주 묻는 질문 (FAQ)

## 설정 관련

### Q1. cluster와 kubeconfig_context의 차이는 무엇인가요?

**A**: 두 필드는 완전히 다른 목적을 가집니다:

- **cluster** (선택사항): 사람이 읽을 수 있는 클러스터 식별자

  - 로그와 캐시 디렉토리에만 사용됨
  - kubeconfig의 cluster 이름과 일치할 필요 없음
  - 예: `production-eks`, `dev-k3s`, `staging-gke`

- **kubeconfig_context** (필수): kubectl context 이름

  - `kubectl config get-contexts`의 NAME 컬럼 값
  - `helm --kube-context`와 `kubectl --context`에 전달됨
  - kubeconfig 파일에 실제로 존재해야 함

**예시**:

```yaml
# sources.yaml
cluster: my-production-cluster      # ← 사람용 레이블
kubeconfig: ~/.kube/config
kubeconfig_context: arn:aws:eks:... # ← 실제 kubectl context
```

______________________________________________________________________

### Q2. context를 찾을 수 없다는 오류가 나요

**오류 메시지**:

```
❌ Kubernetes context 'my-context' not found in kubeconfig
```

**해결 방법**:

1. **사용 가능한 contexts 확인**:

   ```bash
   kubectl config get-contexts
   ```

1. **sources.yaml 수정**:

   ```yaml
   kubeconfig_context: <위에서 확인한 NAME 값>
   ```

1. **특정 kubeconfig 파일 사용 시**:

   ```bash
   kubectl config get-contexts --kubeconfig ~/.kube/my-config
   ```

______________________________________________________________________

### Q3. 여러 클러스터를 관리하려면 어떻게 하나요?

**A**: 환경별로 sources.yaml을 분리합니다:

```
config/
├── sources-dev.yaml        # 개발 환경
├── sources-staging.yaml    # 스테이징 환경
└── sources-prod.yaml       # 프로덕션 환경
```

각 파일에 다른 context 설정:

```yaml
# sources-dev.yaml
cluster: dev-k3s
kubeconfig: ~/.kube/config
kubeconfig_context: dev-cluster

# sources-prod.yaml
cluster: production-eks
kubeconfig: ~/.kube/prod-config
kubeconfig_context: production-cluster
```

배포 시 선택 방법:

**방법 1: --profile 단축 옵션 사용 (권장)**

```bash
# sources-dev.yaml 자동 사용
sbkube deploy --profile dev

# sources-prod.yaml 자동 사용
sbkube deploy --profile prod

# sources-staging.yaml 자동 사용
sbkube deploy --profile staging
```

**방법 2: --source 명시적 경로 지정**

```bash
sbkube deploy --source config/sources-prod.yaml
```

> 💡 **Tip**: `--profile` 옵션은 `sources-{profile}.yaml` 파일명 패턴을 따를 때 편리합니다.

______________________________________________________________________

## 클러스터 연결 관련

### Q4. kubeconfig 파일이 여러 개인데 어떻게 선택하나요?

**A**: `kubeconfig` 필드에 절대 경로 또는 `~` 확장 경로 지정:

```yaml
# sources.yaml
kubeconfig: ~/.kube/my-cluster-config  # ← 특정 파일 지정
kubeconfig_context: my-context
```

또는 CLI 옵션으로 오버라이드:

```bash
sbkube deploy --kubeconfig ~/.kube/prod-config --context prod-context
```

______________________________________________________________________

### Q5. KUBECONFIG 환경변수는 사용되나요?

**A**: **아니오**. SBKube는 명시적 설정만 사용합니다:

1. CLI 옵션 (`--kubeconfig`, `--context`)
1. sources.yaml 설정

**이유**: 실수로 잘못된 클러스터에 배포하는 것을 방지하기 위함

______________________________________________________________________

## 배포 관련

### Q6. dry-run으로 배포를 미리 확인할 수 있나요?

**A**: 네, `--dry-run` 옵션을 사용하세요:

```bash
sbkube deploy --app-dir config --namespace test --dry-run
```

템플릿 결과만 확인하려면:

```bash
sbkube template --app-dir config --output-dir /tmp/preview
cat /tmp/preview/myapp/manifests.yaml
```

______________________________________________________________________

### Q7. 특정 단계만 실행할 수 있나요?

**A**: 네, `apply` 명령어에 `--only` 옵션을 사용하세요:

```bash
# template 단계만 실행
sbkube apply --only template

# prepare와 build만 실행
sbkube apply --only prepare,build
```

또는 개별 명령어 사용:

```bash
sbkube prepare
sbkube build
sbkube template
sbkube deploy
```

______________________________________________________________________

## 기타

### Q8. 로그가 너무 많이 나옵니다

**A**: 기본 로그 레벨 변경:

```bash
# 간결한 로그
sbkube deploy --quiet

# 상세 로그 (디버깅 시)
sbkube deploy --verbose
```

______________________________________________________________________

### Q9. 설정 파일 위치를 변경하고 싶어요

**A**: 모든 명령어에서 경로 지정 가능:

```bash
sbkube deploy \
  --base-dir /path/to/project \
  --app-dir custom-config \
  --source custom-config/sources.yaml
```

______________________________________________________________________

### Q10. 배포 상태를 확인하려면?

**A**: `state` 명령어를 사용하세요:

```bash
# 전체 배포 히스토리
sbkube history

# 특정 네임스페이스
sbkube history --namespace production

# 상세 정보
sbkube history --show <deployment-id>
```

______________________________________________________________________

## 참고 자료

- [트러블슈팅 가이드](README.md)
- [설정 스키마](../03-configuration/config-schema.md)
- [명령어 참조](../02-features/commands.md)
