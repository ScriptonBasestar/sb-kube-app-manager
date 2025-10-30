# 📚 SBKube 문서 가이드

> k3s용 헬름+yaml+git 배포 자동화 CLI 도구

**SBKube**는 YAML, Helm, Git 리소스를 로컬에서 정의하고 Kubernetes 환경에 일관되게 배포할 수 있는 CLI 도구입니다.

---

## 📋 문서 구조

### 🚀 [시작하기](01-getting-started/)

- 설치 및 환경 설정
- 빠른 시작 가이드
- 기본 사용 예제

### ⚙️ [기능 설명](02-features/)

- [전체 기능 개요](02-features/README.md)
- 명령어별 상세 가이드
- 지원 애플리케이션 타입 설명

### 🔧 [설정 가이드](03-configuration/)

- 설정 파일 스키마 (config.yaml, sources.yaml)
- [설정 마이그레이션](03-configuration/migration.md)
- JSON 스키마 검증

### 👨‍💻 [개발자 가이드](04-development/)

- [개발 환경 구성](04-development/README.md)
- [테스트 가이드](04-development/testing.md)
- 기여 방법 및 코드 스타일

### 🚀 [배포 가이드](05-deployment/)

- PyPI 패키지 배포
- 로컬 개발 환경 설치
- 프로덕션 배포 방법

### 🔍 [문제 해결](07-troubleshooting/)

- [일반적인 문제 및 해결책](07-troubleshooting/README.md)
- [자주 묻는 질문 (FAQ)](07-troubleshooting/faq.md)
- 디버깅 가이드

### 📚 [튜토리얼](08-tutorials/)

- [첫 번째 배포](08-tutorials/01-getting-started.md)
- [다중 앱 배포](08-tutorials/02-multi-app-deployment.md)
- [프로덕션 배포](08-tutorials/03-production-deployment.md)
- [고급 커스터마이징](08-tutorials/04-customization.md)
- [문제 해결 실습](08-tutorials/05-troubleshooting.md)

---

## 🎯 주요 특징

### 다단계 워크플로우

```
prepare → build → template → deploy
```

### 지원 애플리케이션 타입

- **helm** / **git** / **http** - 소스 준비

- **helm** / **yaml** / **action** / **exec** - 배포 방법

### 설정 파일

- **config.yaml** - 애플리케이션 정의 및 배포 스펙
- **sources.yaml** - 외부 소스 정의 (Helm repos, Git repos)
- **values/** - Helm 값 파일 디렉토리

---

## 🚀 빠른 시작

```bash
# 설치
pip install sbkube

# 기본 워크플로우
sbkube prepare --base-dir . --app-dir config
sbkube build --base-dir . --app-dir config  
sbkube template --base-dir . --app-dir config --output-dir rendered/
sbkube deploy --base-dir . --app-dir config --namespace <namespace>
```

---

## 🏗️ 아키텍처 개요

### 핵심 구조

- **sbkube/** - 메인 Python 패키지
  - **cli.py** - Click 기반 CLI 엔트리포인트
  - **commands/** - 개별 명령어 구현
  - **models/** - Pydantic 데이터 모델
  - **utils/** - 공통 유틸리티

### 실행 중 디렉토리 구조

- **charts/** - 다운로드된 Helm 차트 (prepare 단계)
- **repos/** - 클론된 Git 저장소 (prepare 단계)
- **build/** - 빌드된 애플리케이션 아티팩트 (build 단계)
- **rendered/** - 템플릿된 YAML 출력 (template 단계)

---

## 📚 관련 자료

### 공식 저장소

- 🏠 [GitHub Repository](https://github.com/ScriptonBasestar/kube-app-manaer)
- 📦 [PyPI Package](https://pypi.org/project/sbkube/)

### 개발 정보

- 🏢 **개발**: [ScriptonBasestar](https://github.com/ScriptonBasestar)
- 📄 **라이선스**: MIT License
- 🐍 **Python**: 3.12 이상 required
- 🛠️ **의존성**: Click, Pydantic, PyYAML, GitPython

---

## 💬 지원 및 기여

- 📋 [이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)
- 📧 **문의**: archmagece@users.noreply.github.com
- 🤝 **기여**: [개발자 가이드](04-development/README.md) 참조

---

## 🔗 내부 문서 (개발팀용)

### [99-internal/](99-internal/)

- [백로그](99-internal/backlog.md) - 향후 구현 예정 기능
- [문서 수정 사항](99-internal/doc-fixes.md) - 문서 업데이트 필요 항목

### AI 작업 가이드

- [CLAUDE.md](../CLAUDE.md) - AI 에이전트를 위한 통합 작업 가이드

---

*📅 마지막 업데이트: 2025-10-30 | 📋 문서 버전: v1.1*
*🎯 SBKube v0.4.10 기준 | 🇰🇷 한국어 우선 지원*
