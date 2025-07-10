# ✅ SBKube 프로젝트 문서 정리 실행 프롬프트

## 프로젝트 분석 결과

### 📋 프로젝트 특성
- **유형**: Python CLI 라이브러리 (Kubernetes 배포 자동화 도구)
- **기술 스택**: Python 3.12, Click CLI, Pydantic, Helm, Kubernetes
- **대상 사용자**: DevOps 엔지니어, Kubernetes 개발자
- **라이선스**: MIT (오픈소스)
- **언어**: 한국어 중심 (한국 k3s 환경 특화)

### 📁 현재 문서 현황 (총 18개 문서)

#### 루트 레벨 (8개)
- `README.md` - 메인 프로젝트 소개 (한국어)
- `FEATURES.md` - 주요 기능 명세 (한국어)
- `Developer.md` - 간단한 개발 가이드 (English)
- `Deploy.md` - 배포 가이드 (English)
- `TEST.md` - 수동 테스트 가이드 (한국어)
- `BACKLOG.md` - 백로그 관리 (한국어)
- `DOC_FIX.md` - 문서 수정 필요 항목 (한국어)
- `CLAUDE.md` - Claude Code 지침 (한국어)

#### docs/ 하위 (1개)
- `docs/CONFIG_VALIDATION_MIGRATION.md` - 설정 검증 마이그레이션 가이드

#### examples/ 하위 (9개)
- 각 기능별 예제 디렉토리마다 README.md 존재

### 🎯 문제점 분석

#### 1. **언어 불일치**
- 프로젝트는 한국어 중심이지만 Developer.md, Deploy.md는 영어
- 일관성 없는 언어 사용

#### 2. **중복 가능성**
- `Developer.md`와 `CLAUDE.md`의 개발 가이드 중복
- `Deploy.md`와 `CLAUDE.md`의 배포 정보 중복

#### 3. **구조적 분산**
- 메인 문서들이 루트에 분산
- docs/ 디렉토리 활용도 낮음

#### 4. **메타 문서 혼재**
- `BACKLOG.md`, `DOC_FIX.md` 같은 개발 메타 문서가 사용자 대상 문서와 혼재

## 🎯 맞춤형 문서 정리 전략

### 1. 디렉토리 구조 설계

```
docs/
├── INDEX.md                    # 종합 네비게이션 가이드 (한국어)
├── 01-getting-started/         # 시작하기
│   ├── README.md              # 설치 및 빠른 시작
│   └── examples.md            # 기본 사용 예제
├── 02-features/               # 기능 설명
│   ├── README.md              # 전체 기능 개요
│   ├── commands.md            # 명령어별 상세 가이드
│   └── application-types.md   # 지원 앱 타입 설명
├── 03-configuration/          # 설정 가이드
│   ├── README.md              # 설정 개요
│   ├── config-schema.md       # config.yaml 스키마
│   ├── sources-schema.md      # sources.yaml 스키마
│   └── migration.md           # 설정 마이그레이션
├── 04-development/            # 개발자 가이드
│   ├── README.md              # 개발 환경 구성
│   ├── testing.md             # 테스트 가이드
│   ├── contributing.md        # 기여 가이드
│   └── release.md             # 릴리스 절차
├── 05-deployment/             # 배포 가이드
│   ├── README.md              # 배포 개요
│   ├── pypi.md                # PyPI 배포
│   └── local.md               # 로컬 설치
├── 06-examples/               # 사용 예제 (기존 examples/ 통합)
│   ├── README.md              # 예제 가이드
│   ├── basic-workflow/        
│   ├── helm-deployment/       
│   ├── yaml-deployment/       
│   └── advanced-scenarios/    
├── 07-troubleshooting/        # 문제 해결
│   ├── README.md              # 일반적인 문제들
│   └── faq.md                 # 자주 묻는 질문
└── 99-internal/               # 내부 문서 (개발팀용)
    ├── backlog.md             # 백로그
    ├── doc-fixes.md           # 문서 수정 사항
    └── claude-instructions.md # Claude 지침
```

### 2. 파일 이동 및 통합 계획

#### Phase 1: 디렉토리 구조 생성
```bash
mkdir -p docs/{01-getting-started,02-features,03-configuration,04-development,05-deployment,06-examples,07-troubleshooting,99-internal}
```

#### Phase 2: 메인 문서 이동 및 통합
```bash
# 1. README.md 내용을 docs/01-getting-started/README.md로 통합
# 새 README.md는 간단한 프로젝트 소개 + docs/INDEX.md 링크

# 2. FEATURES.md -> docs/02-features/README.md
mv FEATURES.md docs/02-features/README.md

# 3. Developer.md + Deploy.md 통합 -> docs/04-development/README.md
# Developer.md와 Deploy.md 내용을 한국어로 통합

# 4. TEST.md -> docs/04-development/testing.md  
mv TEST.md docs/04-development/testing.md

# 5. 설정 관련 문서 정리
mv docs/CONFIG_VALIDATION_MIGRATION.md docs/03-configuration/migration.md

# 6. 내부 문서 이동
mv BACKLOG.md docs/99-internal/backlog.md
mv DOC_FIX.md docs/99-internal/doc-fixes.md
mv CLAUDE.md docs/99-internal/claude-instructions.md
```

#### Phase 3: examples/ 디렉토리 통합
```bash
# examples/ 내용을 docs/06-examples/로 이동
cp -r examples/* docs/06-examples/
# 필요에 따라 examples/ 유지 또는 제거 결정
```

### 3. 새 문서 생성 계획

#### 필수 생성 문서
1. **docs/INDEX.md** - 전체 문서 네비게이션
2. **새 README.md** - 간결한 프로젝트 소개
3. **docs/02-features/commands.md** - 명령어별 상세 가이드
4. **docs/03-configuration/config-schema.md** - 설정 스키마 상세
5. **docs/04-development/contributing.md** - 기여 가이드
6. **docs/07-troubleshooting/README.md** - 문제 해결 가이드

### 4. 중복 제거 전략

#### 개발 가이드 통합
- `Developer.md` (영어) + `CLAUDE.md` 개발 섹션 → `docs/04-development/README.md` (한국어)
- 중복 내용 제거하고 한국어로 통일

#### 배포 가이드 통합  
- `Deploy.md` (영어) + `CLAUDE.md` 배포 섹션 → `docs/05-deployment/` (한국어)

### 5. 명명 규칙

#### 파일명 규칙
- **디렉토리**: `kebab-case` (예: `getting-started`)
- **문서 파일**: `kebab-case.md` (예: `config-schema.md`)
- **README.md**: 각 디렉토리의 메인 문서

#### 언어 규칙
- **메인 사용자 문서**: 한국어 (프로젝트 특성상)
- **개발자 문서**: 한국어 (한국 개발팀)
- **코드 주석/변수명**: 영어 유지

### 6. 우선순위별 실행 계획

#### 🔥 최우선 (즉시 실행)
1. 디렉토리 구조 생성
2. `docs/INDEX.md` 생성 (전체 네비게이션)
3. 메인 README.md 간소화
4. 내부 문서 이동 (`BACKLOG.md`, `DOC_FIX.md`, `CLAUDE.md`)

#### 🚀 고우선 (1단계)
1. `FEATURES.md` → `docs/02-features/README.md` 이동
2. `Developer.md` + `Deploy.md` 통합 → `docs/04-development/README.md`
3. `TEST.md` → `docs/04-development/testing.md` 이동

#### ⚡ 중우선 (2단계)
1. 설정 관련 문서 정리 (`docs/03-configuration/`)
2. examples/ 통합 또는 정리
3. 새 가이드 문서 생성

#### 📝 저우선 (3단계)
1. 문제 해결 가이드 작성
2. 기여 가이드 작성
3. 최종 검토 및 링크 정리

## 🚀 즉시 실행 명령어

### 1단계: 기본 구조 생성
```bash
# 디렉토리 구조 생성
mkdir -p docs/{01-getting-started,02-features,03-configuration,04-development,05-deployment,06-examples,07-troubleshooting,99-internal}

# INDEX.md 생성 (네비게이션)
cat > docs/INDEX.md << 'EOF'
# 📚 SBKube 문서 가이드

> k3s용 헬름+yaml+git 배포 자동화 CLI 도구

## 📋 문서 구조

### 🚀 [시작하기](01-getting-started/)
- 설치 및 빠른 시작
- 기본 사용 예제

### ⚙️ [기능 설명](02-features/)  
- 전체 기능 개요
- 명령어별 상세 가이드
- 지원 앱 타입 설명

### 🔧 [설정 가이드](03-configuration/)
- 설정 파일 스키마
- 마이그레이션 가이드

### 👨‍💻 [개발자 가이드](04-development/)
- 개발 환경 구성
- 테스트 가이드
- 기여 방법

### 🚀 [배포 가이드](05-deployment/)
- PyPI 배포
- 로컬 설치

### 📖 [사용 예제](06-examples/)
- 워크플로우 예제
- 배포 시나리오

### 🔍 [문제 해결](07-troubleshooting/)
- 일반적인 문제
- FAQ

---
*SBKube v0.1.10 | [GitHub](https://github.com/ScriptonBasestar/kube-app-manaer)*
EOF
```

### 2단계: 내부 문서 이동
```bash
# 내부 개발 문서들을 99-internal/로 이동
mv BACKLOG.md docs/99-internal/backlog.md
mv DOC_FIX.md docs/99-internal/doc-fixes.md  
mv CLAUDE.md docs/99-internal/claude-instructions.md
```

### 3단계: 메인 문서 이동
```bash
# 기능 문서 이동
mv FEATURES.md docs/02-features/README.md

# 테스트 문서 이동  
mv TEST.md docs/04-development/testing.md

# 설정 마이그레이션 문서 이동
mv docs/CONFIG_VALIDATION_MIGRATION.md docs/03-configuration/migration.md
```

### 4단계: 새 README.md 생성
```bash
# 기존 README.md 백업
cp README.md README.md.backup

# 새 간소화된 README.md 생성
cat > README.md << 'EOF'
# 🧩 SBKube

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sbkube)]()

**SBKube**는 `yaml`, `Helm`, `git` 리소스를 로컬에서 정의하고 `k3s` 등 Kubernetes 환경에 일관되게 배포할 수 있는 CLI 도구입니다.

> k3s용 헬름+yaml+git 배포 자동화 CLI 도구

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

## 📚 문서

전체 문서는 **[docs/INDEX.md](docs/INDEX.md)**에서 확인하세요.

- 📖 [시작하기](docs/01-getting-started/) - 설치 및 빠른 시작
- ⚙️ [기능 가이드](docs/02-features/) - 명령어 및 기능 설명  
- 🔧 [설정 가이드](docs/03-configuration/) - 설정 파일 작성법
- 👨‍💻 [개발자 가이드](docs/04-development/) - 개발 환경 구성
- 📖 [사용 예제](docs/06-examples/) - 다양한 배포 시나리오

## 💬 지원

- 📋 [이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)
- 📧 문의: archmagece@users.noreply.github.com

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.
EOF
```

## ✅ 검증 사항

실행 후 다음을 확인하세요:

1. **디렉토리 구조**: `tree docs/` 명령어로 구조 확인
2. **파일 이동**: 이동된 파일들이 올바른 위치에 있는지 확인
3. **링크 검증**: INDEX.md의 링크들이 올바르게 작동하는지 확인
4. **언어 일관성**: 한국어 문서들의 언어 일관성 확인

## 🎯 다음 단계

이 프롬프트 실행 후:
1. 통합된 개발자 가이드 작성 (`docs/04-development/README.md`)
2. 설정 스키마 문서 작성 (`docs/03-configuration/`)
3. 문제 해결 가이드 작성 (`docs/07-troubleshooting/`)
4. examples/ 디렉토리 정리 여부 결정

---
*📅 생성일: 2025-07-10 | 🎯 대상: SBKube v0.1.10*