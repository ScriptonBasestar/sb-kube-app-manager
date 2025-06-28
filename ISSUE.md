# 🚨 프로젝트 기능 검토 - 발견된 이슈들

이 문서는 FEATURES.md와 실제 구현 및 문서 간의 불일치나 누락 사항을 기록합니다.

---

### 🚨 ISSUE: CLAUDE.md에 install-yaml 타입 정보 누락

- 📌 관련 기능: 앱 타입 지원 확장 - install-yaml 타입
- 📁 관련 파일/모듈: `CLAUDE.md`
- 📎 문제 요약: CLAUDE.md의 "Application Types" 섹션(라인 64-67)에 새로 추가된 `install-yaml` 타입이 누락되어 있음. `install-kubectl`이 언급되어 있지만 실제로는 `install-yaml`이 정확한 타입명임
- 🛠️ 제안: DOC_FIX - CLAUDE.md 업데이트 필요

### 🚨 ISSUE: README.md의 build 명령어 설명에 install-yaml 타입 누락

- 📌 관련 기능: build 명령어 - install-yaml 타입 지원
- 📁 관련 파일/모듈: `README.md`
- 📎 문제 요약: README.md 라인 187에서 build 명령어 대상 타입 설명에 `install-yaml` 타입이 누락됨. 현재 `pull-helm`, `pull-helm-oci`, `pull-git`, `copy-app`만 언급되어 있음
- 🛠️ 제안: DOC_FIX - README.md의 build 명령어 설명 업데이트 필요

### 🚨 ISSUE: README.md의 deploy 명령어 설명에서 타입명 불일치

- 📌 관련 기능: deploy 명령어 - 지원 타입 정보
- 📁 관련 파일/모듈: `README.md`
- 📎 문제 요약: README.md 라인 207에서 deploy 명령어 대상으로 `install-kubectl`이 언급되어 있으나, 실제 구현에서는 `install-yaml` 타입을 사용함
- 🛠️ 제안: DOC_FIX - README.md의 deploy 명령어 설명에서 정확한 타입명 사용 필요

### 🚨 ISSUE: README.md 예제 설정에서 최신 타입 미반영

- 📌 관련 기능: 설정 파일 예제 - 새로운 앱 타입
- 📁 관련 파일/모듈: `README.md`
- 📎 문제 요약: README.md의 config-memory.yaml 예제(라인 268-285)에 `copy-app`이나 `install-yaml` 같은 새로 지원되는 타입의 예제가 없음. 사용자들이 새로운 기능을 어떻게 사용해야 하는지 알기 어려움
- 🛠️ 제안: DOC_FIX - README.md에 copy-app과 install-yaml 타입 사용 예제 추가 필요

### 🚨 ISSUE: README.md 설치 섹션에 중복된 설치 명령어

- 📌 관련 기능: 설치 가이드
- 📁 관련 파일/모듈: `README.md`
- 📎 문제 요약: README.md 라인 57-61에 git clone과 uv pip install 명령어가 라인 47-51과 중복됨
- 🛠️ 제안: DOC_FIX - 중복된 설치 명령어 제거 필요

### 🚨 ISSUE: template 명령어의 지원 타입 범위 불일치

- 📌 관련 기능: template 명령어 - 지원 타입
- 📁 관련 파일/모듈: `FEATURES.md` vs 실제 구현
- 📎 문제 요약: FEATURES.md에는 template 명령어가 `install-helm`과 `install-yaml` 타입만 지원한다고 명시되어 있으나, 실제 template.py 구현을 보면 빌드된 Helm 차트를 처리하므로 `pull-helm`, `pull-helm-oci` 등도 지원할 수 있음
- 🛠️ 제안: 구현 검토 후 FEATURES.md 또는 구현 조정 필요

---

## 📊 이슈 요약

- **DOC_FIX 필요**: 6개 (문서 불일치 및 누락)
- **구현 검토 필요**: 1개 (기능 범위 확인)

대부분의 이슈는 새로 구현된 `copy-app`과 `install-yaml` 기능이 문서에 완전히 반영되지 않은 것으로 보입니다.