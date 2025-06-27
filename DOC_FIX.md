# 문서 수정 항목

- `CLAUDE.md`에 테스트 실행 전 필수 의존성 설치 가이드 추가
  - 대상 문서: `CLAUDE.md`
  - 관련 ISSUE: 테스트 의존성 패키지 누락 (psutil, faker, pytest-cov)

- `README.md` 또는 `CLAUDE.md`에 지원하는 앱 타입 목록 명시
  - 대상 문서: `README.md` 또는 `CLAUDE.md`
  - 관련 ISSUE: 지원되지 않는 앱 타입으로 인한 빌드 테스트 실패

- 테스트 실행 가이드에 sources.yaml 파일 요구사항 설명 추가
  - 대상 문서: `CLAUDE.md` 또는 `TEST.md`
  - 관련 ISSUE: prepare 테스트 실패 - sources.yaml 파일 누락

- `examples/` 디렉토리 사용법 및 제약사항 문서화
  - 대상 문서: `examples/README.md` (신규 생성)
  - 관련 ISSUE: devops 예제에서 지원되지 않는 copy-app 타입 사용

- SQLAlchemy 모델 개발 시 주의사항 문서화
  - 대상 문서: `docs/development.md` (신규 생성)
  - 관련 ISSUE: SQLAlchemy 모델에서 metadata 속성명 충돌

- 에러 핸들링 및 예외 처리 가이드라인 문서화
  - 대상 문서: `docs/error-handling.md` (신규 생성)
  - 관련 ISSUE: DeploymentError, RollbackError 예외 클래스 누락

- `FEATURES.md`에 현재 구현된 기능과 미구현 기능 명확히 구분
  - 대상 문서: `FEATURES.md`
  - 관련 ISSUE: 지원되지 않는 앱 타입들이 테스트에서 사용됨

- 타입 import 관련 개발 가이드라인 추가
  - 대상 문서: `CLAUDE.md` 또는 `docs/development.md`
  - 관련 ISSUE: sources_model_v2.py에서 Any 타입 import 누락