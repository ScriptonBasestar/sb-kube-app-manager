# SBKube 모듈 트러블슈팅 가이드

## 일반적인 문제

### 1. 설정 파일 관련

#### Pydantic ValidationError

**증상**:

```
ValidationError: 2 validation errors for SBKubeConfig
apps.0.specs.repo
  field required (type=value_error.missing)
```

**원인**: config.yaml의 필수 필드 누락 또는 타입 불일치

**해결**:

1. 오류 메시지에서 필드 경로 확인 (`apps.0.specs.repo`)
1. 해당 앱 설정 검토
1. [config-schema.md](../../../../03-configuration/config-schema.md) 참조하여 수정

**예시**:

```yaml
# 잘못된 설정
apps:
  - name: redis
    type: helm
```
