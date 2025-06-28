# 📝 DOC_FIX 항목들

이 문서는 코드 구현은 정상이지만 문서 업데이트가 필요한 항목들을 관리합니다.

---

## 🚨 CLAUDE.md에 install-yaml 타입 정보 누락

- 📌 관련 기능: 앱 타입 지원 확장 - install-yaml 타입
- 📁 관련 파일/모듈: `CLAUDE.md`
- 📎 문제 요약: CLAUDE.md의 "Application Types" 섹션(라인 64-67)에 새로 추가된 `install-yaml` 타입이 누락되어 있음. `install-kubectl`이 언급되어 있지만 실제로는 `install-yaml`이 정확한 타입명임
- 🛠️ 액션: CLAUDE.md 라인 64-67 업데이트 - `install-kubectl`을 `install-yaml`로 수정

---

## 🚨 README.md의 build 명령어 설명에 install-yaml 타입 누락

- 📌 관련 기능: build 명령어 - install-yaml 타입 지원
- 📁 관련 파일/모듈: `README.md`
- 📎 문제 요약: README.md 라인 187에서 build 명령어 대상 타입 설명에 `install-yaml` 타입이 누락됨. 현재 `pull-helm`, `pull-helm-oci`, `pull-git`, `copy-app`만 언급되어 있음
- 🛠️ 액션: README.md 라인 187 업데이트 - build 명령어 대상 타입에 `install-yaml` 추가

---

## 🚨 README.md의 deploy 명령어 설명에서 타입명 불일치

- 📌 관련 기능: deploy 명령어 - 지원 타입 정보
- 📁 관련 파일/모듈: `README.md`
- 📎 문제 요약: README.md 라인 207에서 deploy 명령어 대상으로 `install-kubectl`이 언급되어 있으나, 실제 구현에서는 `install-yaml` 타입을 사용함
- 🛠️ 액션: README.md 라인 207 업데이트 - `install-kubectl`을 `install-yaml`로 수정

---

## 🚨 README.md 예제 설정에서 최신 타입 미반영

- 📌 관련 기능: 설정 파일 예제 - 새로운 앱 타입
- 📁 관련 파일/모듈: `README.md`
- 📎 문제 요약: README.md의 config-memory.yaml 예제(라인 268-285)에 `copy-app`이나 `install-yaml` 같은 새로 지원되는 타입의 예제가 없음. 사용자들이 새로운 기능을 어떻게 사용해야 하는지 알기 어려움
- 🛠️ 액션: README.md 예제 섹션에 copy-app과 install-yaml 타입 사용 예제 추가

---

## 🚨 README.md 설치 섹션에 중복된 설치 명령어

- 📌 관련 기능: 설치 가이드
- 📁 관련 파일/모듈: `README.md`
- 📎 문제 요약: README.md 라인 57-61에 git clone과 uv pip install 명령어가 라인 47-51과 중복됨
- 🛠️ 액션: README.md에서 중복된 설치 명령어 제거 (라인 57-61 삭제)

---

## 📊 DOC_FIX 요약

총 5개 문서 수정 사항:
- CLAUDE.md: 1개 (타입명 수정)
- README.md: 4개 (타입 추가, 타입명 수정, 예제 추가, 중복 제거)